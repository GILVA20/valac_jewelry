---
description: "Referencia del flujo de pagos MercadoPago de VALAC Joyas. Use when: modificar checkout, webhook, debugging de pagos, crear preferencia, estados de pago, order tracking."
agent: "ask"
model: ["Claude Sonnet 4.6", "Claude Haiku 4.5"]
tools: [read, search]
---

Responde sobre el flujo de pagos MercadoPago de VALAC Joyas usando esta referencia.

## Flujo completo de pago

```
Cliente llena checkout form
        ↓
POST /checkout → crea order en Supabase (estado_pago="Pendiente")
        ↓
POST /create_preference → crea preferencia MercadoPago con external_reference=order_id
        ↓
Redirect a MercadoPago → cliente paga
        ↓
MP redirige a /success, /failure, o /pending (back_urls)
        ↓ (en paralelo)
MP POST /webhook/mercadopago → consulta API MP → actualiza estado_pago
        ↓
/success → envía email SMTP de confirmación
```

## Archivos involucrados

| Archivo | Endpoint | Responsabilidad |
|---------|----------|-----------------|
| `routes/checkout.py` | GET/POST `/checkout` | Form de checkout, creación de orden en Supabase |
| `routes/mercadopago_checkout.py` | POST `/create_preference` | Crea preferencia MP (SDK), POST `/webhook` (webhook duplicado) |
| `routes/webhook.py` | POST `/webhook/mercadopago` | Webhook principal: consulta API MP, actualiza orden |
| `routes/success.py` | GET/POST `/success` | Página post-pago exitoso + email SMTP |
| `routes/failure.py` | GET `/failure` | Página de pago fallido |
| `routes/pending.py` | GET `/pending` | Página de pago pendiente |
| `routes/mock_checkout.py` | GET/POST `/mock-checkout` | Simulación de pago (dev, `SIMULAR_PAGO=True`) |
| `routes/orders.py` | GET `/orders/track/<id>` | Tracking público de orden |

## Configuración MercadoPago

### Tokens (dual-mode)

| Variable | Usado cuando |
|----------|------|
| `MP_ACCESS_TOKEN` | `FLASK_ENV=production` |
| `MP_ACCESS_TOKEN_TEST` | `FLASK_ENV=development` |
| `MP_PUBLIC_KEY` | Frontend prod |
| `MP_PUBLIC_KEY_TEST` | Frontend dev |

La selección se hace en `mercadopago_checkout.py` al inicio del módulo.

### Preferencia MP

```python
preference_data = {
    "items": [{"title": "...", "unit_price": float, "quantity": int}],
    "back_urls": {
        "success": "https://valacjoyas.com/success",
        "failure": "https://valacjoyas.com/failure",
        "pending": "https://valacjoyas.com/pending"
    },
    "notification_url": "https://valacjoyas.com/webhook",
    "payment_methods": {"installments": 12},
    "external_reference": str(order_id)
}
```

## Webhook MercadoPago

### Flujo del webhook (`routes/webhook.py`)

1. Recibe POST con `{"type": "payment", "data": {"id": payment_id}}`
2. Si `type != "payment"` → ignora (HTTP 200)
3. Consulta API de MP: `mp_sdk.payment().get(payment_id)`
4. Obtiene `external_reference` (= `order_id`) del response
5. Mapea status MP → status VALAC:

| MP status | VALAC estado_pago |
|-----------|-------------------|
| `approved` | Completado |
| `authorized` | Completado |
| `pending` | Pendiente |
| `in_process` | Pendiente |
| `rejected` | Rechazado |
| `cancelled` | Cancelado |

6. Actualiza `orders.estado_pago` + `transaction_id` en Supabase
7. Siempre retorna HTTP 200 (MP necesita 200 para no reintentar)

### ⚠️ Issues conocidos

1. **Webhook duplicado** — Hay un webhook en `webhook.py` (ruta `/webhook/mercadopago`) Y otro en `mercadopago_checkout.py` (ruta `/webhook`). La `notification_url` apunta a `/webhook`. Verificar cuál se usa realmente.
2. **Sin HMAC en webhook principal** — `webhook.py` no verifica `X-Signature` HMAC-SHA256 (el import de `hmac`/`hashlib` existe pero no se usa). La verificación se hace confiando en la consulta a la API de MP.
3. **Token logueado** — `mercadopago_checkout.py` tiene `logging.debug(...MP_ACCESS_TOKEN...)` y `logging.debug(...SUPABASE_KEY...)`.
4. **SDK instanciada dos veces** — `mercadopago_checkout.py` crea `mp = mercadopago.SDK(token)` a nivel de módulo Y otra vez dentro de `create_preference()` con `current_app.config["MP_ACCESS_TOKEN"]`.

## Mock checkout (`SIMULAR_PAGO=True`)

Cuando esta variable existe, se habilita `/mock-checkout` que simula el flujo de pago sin MercadoPago. Útil para desarrollo local en Windows con Waitress.

## Estados de orden

```
estado_pago: Pendiente → Completado | Fallido | Rechazado | Cancelado
estado_envio: sin_enviar → en_proceso → enviado → entregado | cancelado
```

`status_history` (JSONB) guarda el historial de cambios de estado con timestamps.
