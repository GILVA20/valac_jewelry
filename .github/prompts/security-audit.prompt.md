---
description: "Auditoría de seguridad express para VALAC Joyas. Use when: revisar seguridad, pre-deploy check, revisar ruta nueva, auditar pagos, buscar vulnerabilidades."
agent: "valac-security-reviewer"
model: ["Claude Sonnet 4.6", "Claude Opus 4.6"]
tools: [read, search]
---

Ejecuta una auditoría de seguridad del archivo o área indicada por el usuario.

## Checklist rápido

1. **Secrets** — Buscar tokens/keys hardcodeados o logueados
2. **Input validation** — Verificar que inputs se validan antes de procesar
3. **Auth** — Rutas admin con `@login_required`
4. **Money** — Todo cálculo monetario usa `Decimal`, nunca `float`
5. **Supabase** — Queries parametrizadas, no concatenación
6. **Templates** — Sin `|safe` con input de usuario
7. **Logs** — Sin tokens/keys en logging.debug/info/error
8. **Errors** — No exponer tracebacks o datos internos al usuario

Si no se indica archivo, auditar los archivos de alto riesgo:
- `routes/webhook.py`
- `routes/mercadopago_checkout.py`
- `routes/checkout.py`
- `routes/coupons_api.py`
- `services/pricing.py`

Formato de salida: tabla con severidad (CRITICAL/HIGH/MEDIUM), hallazgo, archivo:línea, y fix concreto.
