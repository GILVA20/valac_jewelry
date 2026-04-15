---
description: "Referencia de operaciones admin de VALAC Joyas. Use when: modificar admin, Flask-Admin, bulk upload, gestión de órdenes, gestión de cupones, analytics, reports."
agent: "ask"
model: ["Claude Sonnet 4.6", "Claude Haiku 4.5"]
tools: [read, search]
---

Responde sobre el sistema admin de VALAC Joyas usando esta referencia.

## Arquitectura admin

### Stack
- **Flask-Admin** con Bootstrap 3 theme
- **Sin Flask-SQLAlchemy** — las vistas heredan `BaseView` e interactúan directo con `current_app.supabase`
- **Auth**: `@login_required` + verificar `current_user.is_admin` en cada vista
- **Un solo admin user**: `AdminUser(id=1)` contra `ADMIN_USERNAME`/`ADMIN_PASSWORD` env vars

### Vistas Flask-Admin

| Vista | Archivo | URL | Función |
|-------|---------|-----|---------|
| `SupabaseProductAdmin` | `routes/admin.py` | `/admin/products` | CRUD de productos (Supabase) |
| `BulkUploadAdminView` | `routes/admin_bulk_upload.py` | `/admin/bulk-upload` | Importación CSV masiva |
| `CouponsAdminView` | `routes/admin_coupons.py` | `/admin/coupons` | CRUD de cupones |
| `OrderService` | `routes/admin_orders.py` | `/admin/orders` | Gestión de órdenes + state machine |
| `SalesAdmin` | `routes/admin.py` | `/admin/sales` | Reporte de ventas |
| `PaymentsAdmin` | `routes/admin.py` | `/admin/payments` | Reporte de pagos |
| `ReportsAdmin` | `routes/admin.py` | `/admin/reports` | Reportes generales |
| `AnalyticsView` | `routes/analytics.py` | `/admin/analytics` | Dashboard de analytics |

## Gestión de productos

### CRUD individual
- **Crear**: Form con campos de producto + upload de imagen a Supabase Storage
- **Editar**: Inline edit (AJAX) vía `static/js/inline-edit.js`
- **Eliminar**: Soft delete o hard delete según implementación
- **Imágenes**: Upload a `CatalogoJoyasValacJoyas/products/` → URL via `CDN_BASE_URL`

### Bulk upload CSV
- Archivo: `routes/admin_bulk_upload.py`
- Usa `pandas` para parsear CSV
- Columnas esperadas: nombre, descripcion, precio, tipo_producto, genero, tipo_oro, stock_total, imagen
- Validación de datos antes de insertar
- Reporta filas exitosas y fallidas

### Galería de imágenes
- Archivo: `routers/product_images.py`
- Tabla `product_images`: product_id, imagen, orden
- Drag-and-drop para reordenar (frontend)

## Gestión de órdenes

### State machine de órdenes
```
estado_pago:
  Pendiente → Completado (webhook MP aprueba)
            → Rechazado (webhook MP rechaza)
            → Cancelado (admin cancela)
            → Fallido (error)

estado_envio:
  sin_enviar → en_proceso (admin marca como en preparación)
             → enviado (admin agrega tracking)
             → entregado (admin confirma recepción)
             → cancelado (admin cancela envío)
```

### Archivo: `routes/admin_orders.py`
- Lista de órdenes con filtros por estado
- Cambio de estado con validación de transiciones permitidas
- `status_history` (JSONB) registra cada cambio con timestamp
- Nota: las transiciones son lineales, no se puede volver atrás

## Gestión de cupones

### Archivo: `routes/admin_coupons.py`
- CRUD completo de cupones
- Campos configurables: type, value, caps, MSI caps, dates, limits
- Preview de cómo se aplicaría el cupón antes de guardar
- Ver `/coupon-system` para la lógica completa de aplicación

## Analytics y reports

### Archivo: `routes/analytics.py`
- Dashboard con métricas: ventas del periodo, órdenes por estado, productos más vendidos
- Filtros por rango de fechas
- Datos desde queries directas a Supabase

## Patrones de código admin

```python
# Vista Flask-Admin correcta
class MyAdminView(BaseView):
    @expose("/")
    @login_required
    def index(self):
        if not current_user.is_admin:
            abort(403)
        # Query Supabase directamente
        data = current_app.supabase.table("products").select("*").execute()
        return self.render("admin/my_view.html", items=data.data)
```

### Reglas para cambios en admin
1. Siempre `@login_required` + `current_user.is_admin`
2. Usar `current_app.supabase` — nunca instanciar nuevo cliente
3. Templates admin en `templates/admin/`
4. CSS admin en `static/css/admin-orders.css`
5. Imágenes via `CDN_BASE_URL + filename` — nunca URL directa de Supabase Storage
