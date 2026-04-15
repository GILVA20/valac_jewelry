---
description: "Referencia completa del sistema de cupones de VALAC Joyas. Use when: modificar cupones, entender descuentos, debugging de pricing, agregar nuevo tipo de cupón, cap_mode, MSI, limits."
agent: "ask"
model: ["Claude Sonnet 4.6", "Claude Haiku 4.5"]
tools: [read, search]
---

Responde sobre el sistema de cupones de VALAC Joyas usando esta referencia. Si el usuario pide un cambio, planea o ejecuta según el triage de copilot-instructions.

## Arquitectura de cupones

### Flujo de validación (orden OBLIGATORIO)

```
is_coupon_active(coupon)     →  ¿cupón vigente?
        ↓ True
can_use_coupon(sb, coupon, user_id, email)  →  ¿límites OK?
        ↓ (True, "ok")
apply_coupon(base_amount, coupon, msi_selected)  →  monto de descuento
```

### Archivos involucrados

| Archivo | Funciones | Responsabilidad |
|---------|-----------|-----------------|
| `services/pricing.py` | `is_coupon_active()`, `apply_coupon()`, `compute_totals()` | Cálculo de precios y descuentos |
| `services/limits_service.py` | `can_use_coupon()`, `_count()` | Límites de uso (global + per-user) |
| `services/discounts_service.py` | `is_coupon_active()`, `apply_coupon()` | ⚠️ **DUPLICADO** de pricing.py — consolidar |
| `routes/coupons_api.py` | POST `/api/coupons/validate` | Endpoint público de validación |

### Tabla `coupons` (campos clave)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `code` | string | Código que ingresa el cliente |
| `type` | `percent` \| `fixed` | Tipo de descuento |
| `value` | number | Monto o porcentaje del descuento |
| `active` | bool | On/off manual |
| `starts_at` / `ends_at` | timestamp | Vigencia por fecha |
| `cap_mode` | `amount` \| `percent` \| `both` | Qué topes aplican |
| `cap_amount` | number | Tope fijo en MXN |
| `cap_percent` | number | Tope como % de la base |
| `cap_amount_msi` | number | Tope fijo para compras a meses (MSI) |
| `cap_percent_msi` | number | Tope % para MSI |
| `min_order_amount` | number | Mínimo de compra para aplicar |
| `max_uses` | number | Límite global de usos |
| `max_uses_per_user` | number | Límite por usuario/email |

### Lógica de `apply_coupon(base_amount, coupon, msi_selected)`

1. **Descuento bruto**: 
   - `percent` → `base × (value / 100)`
   - `fixed` → `value`

2. **Selección de topes** (si `msi_selected=True` y hay variantes MSI, usa esas):
   - `cap_amount` → se usa `cap_amount_msi` si disponible
   - `cap_percent` → se usa `cap_percent_msi` si disponible

3. **Aplicación de topes** según `cap_mode`:
   - `amount` → `min(descuento, cap_amount)`
   - `percent` → `min(descuento, base × cap_percent/100)`
   - `both` → `min(descuento, cap_amount, base × cap_percent/100)`

4. **Resultado**: `max(0, min(monto_calculado, base))` → redondeado a 2 decimales

### Lógica de `can_use_coupon(sb, coupon, user_id, email)`

1. Si `max_uses` definido → contar `coupon_redemptions` globales. Si ≥ max_uses → `(False, "limit_reached_global")`
2. Si `max_uses_per_user` definido:
   - Si hay `user_id` → contar por user_id
   - Si no → contar por `email.lower()` (normalizado)
   - Si ≥ max_uses_per_user → `(False, "limit_reached_user")`
3. Si pasa todo → `(True, "ok")`

### Lógica de `compute_totals(items, shipping_base, free_shipping_threshold, ...)`

1. `subtotalProducts` = Σ(unit_price × quantity)
2. `shipping` = `0` si subtotal ≥ threshold (default $8,500 MXN), else `shipping_base` ($260 MXN)
3. Base para cupón según `coupon_percent_base`:
   - `"products"` → solo subtotal
   - `"products_plus_shipping"` → subtotal + envío
4. `discount_total` = `apply_coupon(base, coupon, msi)` si cupón activo
5. `total` = preCoupon - discount_total

### ⚠️ Deuda técnica

`discounts_service.py` duplica `is_coupon_active()` y `apply_coupon()` de `pricing.py` con parsing de fechas menos robusto. **Consolidar en `pricing.py`** y eliminar duplicados.
