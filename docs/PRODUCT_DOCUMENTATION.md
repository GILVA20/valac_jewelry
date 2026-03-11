# VALAC Joyas — Documentación Completa del Producto

> Última actualización: 2026-03-11
> Generado automáticamente a partir de análisis exhaustivo del código fuente.

---

## Tabla de Contenidos

1. [Visión General](#1-visión-general)
2. [Stack Técnico](#2-stack-técnico)
3. [Arquitectura de la Aplicación](#3-arquitectura-de-la-aplicación)
4. [Flujo del Usuario (Customer Journey)](#4-flujo-del-usuario)
5. [Rutas — Detalle Completo](#5-rutas--detalle-completo)
6. [Servicios (Business Logic)](#6-servicios)
7. [Templates — Mapa Completo](#7-templates--mapa-completo)
8. [JavaScript Frontend](#8-javascript-frontend)
9. [Scripts y Utilidades](#9-scripts-y-utilidades)
10. [Archivos de Configuración](#10-archivos-de-configuración)
11. [Modelos de Datos](#11-modelos-de-datos)
12. [Integraciones Externas](#12-integraciones-externas)
13. [Clasificación: Crítico vs No Crítico](#13-clasificación-crítico-vs-no-crítico)
14. [Auditoría: Código Muerto, Duplicado y Problemas](#14-auditoría-código-muerto-duplicado-y-problemas)
15. [Dependencias](#15-dependencias)

---

## 1. Visión General

**VALAC Joyas** es una tienda e-commerce de joyería de lujo mexicana. Permite a los clientes:
- Explorar un catálogo filtrable de productos (por categoría, género, tipo de oro, precio)
- Agregar productos al carrito (sesión del servidor)
- Aplicar cupones de descuento con reglas de negocio complejas (topes, MSI, límites de uso)
- Pagar con MercadoPago (producción) o simulador (desarrollo)
- Recibir confirmación de pedido por email
- Rastrear su pedido públicamente

El **administrador** puede:
- Gestionar productos (CRUD, carga masiva CSV, galería de imágenes)
- Gestionar órdenes (estado de pago y envío con máquina de estados)
- Crear/editar cupones de descuento
- Ver analytics (vistas de producto, navegación, funnel, KPIs)
- Ver reportes de ventas y cobranza

---

## 2. Stack Técnico

| Capa | Tecnología | Detalle |
|------|-----------|---------|
| **Backend** | Flask 3.1.0 | App factory en `valac_jewelry/__init__.py` |
| **Base de datos** | Supabase (PostgreSQL) | Cliente global: `app.supabase` vía supabase-py v2 |
| **Almacenamiento** | Supabase Storage | Bucket: `CatalogoJoyasValacJoyas/products` |
| **CDN** | Cloudflare Worker | `CDN_BASE_URL` proxy sobre Supabase Storage |
| **Pagos** | MercadoPago SDK v2 | Dual-token: producción + test |
| **Email** | smtplib SMTP/TLS | Gmail con app password |
| **Auth** | Flask-Login | Un solo `AdminUser(id=1)` contra env vars |
| **WSGI (prod)** | Gunicorn | Via Procfile en Heroku |
| **WSGI (dev)** | Waitress | `run_waitress.py` en Windows, puerto 5000 |
| **CSS** | TailwindCSS 3.4 | Compilado a `static/css/output.css` |
| **Frontend** | Jinja2 + jQuery 3.6 | + Slick Carousel + AOS animations + FontAwesome 6 |
| **Supabase JS** | ESM CDN | `esm.sh/@supabase/supabase-js@2.12` inyectado en `base.html` |

---

## 3. Arquitectura de la Aplicación

### 3.1 App Factory (`valac_jewelry/__init__.py`)

```
create_app()
├── Registra tipo MIME .mjs
├── Configura carpeta static/ (raíz del repo)
├── before_request: enforce HTTPS + www redirect
├── Carga Config (Production/Development según FLASK_ENV)
├── Crea cliente Supabase → app.supabase
├── Context processor: inyecta SUPABASE_STORAGE_URL y CDN_BASE_URL
├── Configura Flask-Login (user_loader → AdminUser)
├── Registra 15 Blueprints
└── Configura Flask-Admin con 8 vistas
```

### 3.2 Blueprints Registrados

| # | Blueprint | Prefijo URL | Archivo |
|---|-----------|-------------|---------|
| 1 | `auth` | — | `auth.py` |
| 2 | `main` | — | `routes/main.py` |
| 3 | `collection` | `/collection` | `routes/collection.py` |
| 4 | `products` | `/producto` | `routes/products.py` |
| 5 | `cart` | `/cart` | `routes/cart.py` |
| 6 | `contact` | `/contact` | `routes/contact.py` |
| 7 | `orders` | `/orders` | `routes/orders.py` |
| 8 | `success` | — | `routes/success.py` |
| 9 | `failure` | — | `routes/failure.py` |
| 10 | `pending` | — | `routes/pending.py` |
| 11 | `webhook` | `/webhook` | `routes/webhook.py` |
| 12 | `checkout` | — | `routes/checkout.py` |
| 13 | `mp_checkout` | — | `routes/mercadopago_checkout.py` |
| 14 | `mock_checkout` | `/mock-checkout` | `routes/mock_checkout.py` |
| 15 | `coupons_api` | `/api/coupons` | `routes/coupons_api.py` |

### 3.3 Vistas Flask-Admin

| Vista | Endpoint | Archivo |
|-------|----------|---------|
| Productos Supabase | `supabase_products` | `routes/admin.py` |
| Carga Masiva | `bulk_upload` | `routes/admin_bulk_upload.py` |
| Órdenes | `admin_orders` | `routes/admin_orders.py` |
| Ventas | `sales` | `routes/admin.py` |
| Pagos / Cobranza | `payments` | `routes/admin.py` |
| Reportes | `reports` | `routes/admin.py` |
| Analytics | `analytics` | `routes/analytics.py` |
| Cupones | `admin_coupons` | `routes/admin_coupons.py` |

---

## 4. Flujo del Usuario

### 4.1 Customer Journey (Compra)

```
HOME (/)
  └─ Ver catálogo → /collection/ (con filtros)
       └─ Ver producto → /producto/<id> (detalle + galería)
            └─ Agregar al carrito → POST /cart/add/<id>
                 └─ Ver carrito → /cart/ (aplicar cupón aquí)
                      └─ Checkout → /checkout (formulario de envío)
                           ├─ MercadoPago → /create_preference → pago externo
                           ├─ Mock (dev) → /mock-checkout/ → simula resultado
                           └─ Resultado:
                                ├─ /success (email + confirmación)
                                ├─ /pending (pago en espera)
                                └─ /failure (pago fallido)
```

### 4.2 Flujo de Cupones

```
Cliente ingresa código
  → POST /api/coupons/validate
    → is_coupon_active(coupon) — ¿activo + en rango de fechas?
    → can_use_coupon(coupon, user_id, email) — ¿dentro de límites?
    → _compute_discount(subtotal, coupon, msi) — calcula monto
  → Respuesta JSON: {valid, discount_amount, reason}
```

### 4.3 Flujo Admin

```
/login → Credenciales vs env ADMIN_USERNAME/PASSWORD
  └─ /admin/
       ├─ Productos: listar, crear, editar, eliminar, galería, inline-edit
       ├─ Carga Masiva: CSV upload
       ├─ Órdenes: listar, detalle, cambiar estado pago/envío
       ├─ Cupones: CRUD + toggle activo/inactivo
       ├─ Analytics: vistas, navegación, funnel, KPIs por fecha
       ├─ Ventas: dashboard de ventas
       ├─ Pagos: cobranza pendiente
       └─ Reportes: reportes generales
```

---

## 5. Rutas — Detalle Completo

### 5.1 Rutas Públicas (sin autenticación)

#### `routes/main.py` — Blueprint: `main`

| Ruta | Método | Función | Qué hace | API externa |
|------|--------|---------|----------|-------------|
| `/` | GET | `home()` | Renderiza home con top 3 productos destacados (stock > 0, orden por destacado + precio) | Supabase |
| `/about` | GET | `about()` | Página "Sobre nosotros" estática | — |
| `/contact` | GET | `contact()` | Página de contacto estática | — |

#### `routes/collection.py` — Blueprint: `collection`, prefix: `/collection`

| Ruta | Método | Función | Qué hace | API externa |
|------|--------|---------|----------|-------------|
| `/` | GET | `collection_home()` | Catálogo con filtros dinámicos (category, genero, tipo_oro, precio_min/max), búsqueda, ordenamiento, paginación (36/página). Construye query Supabase con múltiples `.eq()` | Supabase |

#### `routes/products.py` — Blueprint: `products`, prefix: `/producto`

| Ruta | Método | Función | Qué hace | API externa |
|------|--------|---------|----------|-------------|
| `/<int:product_id>` | GET | `product_detail()` | Detalle de producto con galería (product_images ordenada) y 4 productos relacionados del mismo tipo_producto. 404 si no existe | Supabase |

#### `routes/cart.py` — Blueprint: `cart`, prefix: `/cart`

| Ruta | Método | Función | Qué hace | API externa |
|------|--------|---------|----------|-------------|
| `/` | GET | `view_cart()` | Muestra carrito con totales calculados server-side (subtotal, envío, descuento, total). Carga precios actuales de Supabase y aplica cupón activo de sesión | Supabase |
| `/add/<int:product_id>` | POST | `add_to_cart()` | Agrega producto a sesión. Valida existencia en Supabase | Supabase |
| `/remove/<int:product_id>` | POST | `remove_from_cart()` | Elimina producto de la sesión del carrito | — |
| `/update_quantity/<int:product_id>` | POST | `update_quantity()` | Actualiza cantidad. Elimina si qty ≤ 0 | — |
| `/coupon/apply` | POST | `cart_apply_coupon()` | Valida cupón contra Supabase, guarda en sesión si válido. Retorna JSON | Supabase |
| `/coupon/remove` | POST | `cart_remove_coupon()` | Elimina cupón aplicado de la sesión. Retorna JSON | — |
| `/wishlist` | GET | `view_wishlist()` | Muestra wishlist de sesión con detalles de Supabase | Supabase |
| `/wishlist/add/<int:product_id>` | POST | `add_to_wishlist()` | Agrega a wishlist de sesión. Valida existencia | Supabase |
| `/wishlist/remove/<int:product_id>` | POST | `remove_from_wishlist()` | Elimina de wishlist de sesión | — |

#### `routes/contact.py` — Blueprint: `contact`, prefix: `/contact`

| Ruta | Método | Función | Qué hace | API externa |
|------|--------|---------|----------|-------------|
| `/` | GET | `contact()` | Renderiza formulario de contacto | — |
| `/send` | POST | `send()` | **STUB** — Solo muestra flash "Mensaje enviado", no envía email real | — |

#### `routes/checkout.py` — Blueprint: `checkout`

| Ruta | Método | Función | Qué hace | API externa |
|------|--------|---------|----------|-------------|
| `/checkout` | GET | `checkout()` | Formulario de checkout con resumen de orden y preferencia MercadoPago (init_point) | Supabase, MercadoPago |
| `/checkout` | POST | `checkout()` | Procesa formulario, crea orden en Supabase, redirige a método de pago (MP, aplazo, o mock) | Supabase, MercadoPago |
| `/api/create-preference` | POST | `create_preference()` | API para crear preferencia MP desde frontend. Espera JSON con datos de cliente | Supabase, MercadoPago |

#### `routes/mercadopago_checkout.py` — Blueprint: `mp_checkout`

| Ruta | Método | Función | Qué hace | API externa |
|------|--------|---------|----------|-------------|
| `/create_preference` | POST | `create_preference()` | Crea preferencia MP desde JSON con items y order_id. Retorna preference_id | MercadoPago |
| `/webhook` | POST | `webhook()` | Recibe notificaciones MP, verifica estado, actualiza order | Supabase, MercadoPago |

#### `routes/webhook.py` — Blueprint: `webhook`, prefix: `/webhook`

| Ruta | Método | Función | Qué hace | API externa |
|------|--------|---------|----------|-------------|
| `/mercadopago` | POST | `mercadopago_webhook()` | Webhook alternativo para MP. Query MP API con payment_id, actualiza estado de orden | Supabase, MercadoPago |

#### Páginas de Resultado de Pago

| Blueprint | Ruta | Función | Qué hace |
|-----------|------|---------|----------|
| `success` | `/success` GET | `success()` | Confirmación de pago exitoso. Envía email SMTP con plantilla HTML. Muestra resumen con descuento proporcional |
| `failure` | `/failure` GET | `failure()` | Página de pago fallido. Usa snapshot de sesión |
| `pending` | `/pending` GET | `pending()` | Página de pago pendiente. Usa snapshot de sesión |

#### `routes/mock_checkout.py` — Blueprint: `mock_checkout`, prefix: `/mock-checkout`

| Ruta | Método | Función | Qué hace | API externa |
|------|--------|---------|----------|-------------|
| `/` | GET | `index()` | Formulario de simulación con botones success/pending/failure | — |
| `/simulate` | POST | `simulate()` | Actualiza estado de orden y redirige al resultado simulado | Supabase |

#### `routes/orders.py` — Blueprint: `orders`, prefix: `/orders`

| Ruta | Método | Función | Qué hace | API externa |
|------|--------|---------|----------|-------------|
| `/track/<int:order_id>` | GET | `track()` | Tracking público de orden. Sin autenticación requerida | Supabase |

#### `routes/coupons_api.py` — Blueprint: `coupons_api`, prefix: `/api/coupons`

| Ruta | Método | Función | Qué hace | API externa |
|------|--------|---------|----------|-------------|
| `/validate` | POST | `validate_coupon()` | Valida cupón: activo, fechas, min_order, límites de uso. Retorna JSON con discount_amount o reason | Supabase |

---

### 5.2 Rutas Admin (requieren @login_required + is_admin)

#### `routes/admin.py` — `SupabaseProductAdmin` (Flask-Admin BaseView)

| Ruta | Método | Función | Qué hace |
|------|--------|---------|----------|
| `/admin/` | GET | `index()` | Lista todos los productos con galería pre-cargada |
| `/admin/storage/upload` | POST | `storage_upload()` | Sube imagen: optimiza a WebP, comprime, sube a Supabase Storage. Retorna URL vía CDN |
| `/admin/update-stock/<id>` | POST | `update_stock()` | Actualiza stock_total. Valida >= 0 |
| `/admin/toggle-destacado/<id>` | POST | `toggle_destacado()` | Toggle del flag `destacado` |
| `/admin/api/quick-update/<id>` | PATCH | `quick_update()` | AJAX inline edit (precio, stock, descuento, nombre). Recalcula precio_descuento |
| `/admin/apply_discount` | POST | `apply_discount()` | Aplica descuento % a múltiples productos (bulk) |
| `/admin/remove_discount` | POST | `remove_discount()` | Quita descuento (0%) a múltiples productos |
| `/admin/new` | GET/POST | `new()` | Formulario crear producto con imágenes múltiples |
| `/admin/delete/<id>` | POST | `delete_product()` | Elimina producto + product_images + product_views |
| `/admin/edit/<id>` | GET/POST | `edit_product()` | Formulario editar producto con galería |
| `/admin/update_gallery_order` | POST | `update_gallery_order()` | AJAX reordenar galería (lista de {id, orden}) |
| `/admin/delete_gallery_image/<id>` | POST | `delete_gallery_image()` | Elimina imagen de galería |
| `/admin/set_primary/<id>` | POST | `set_primary()` | Establece imagen de galería como imagen principal del producto |
| `/admin/gallery` | GET | `gallery()` | Vista de galería general |

#### `routes/admin_bulk_upload.py` — `BulkUploadAdminView`

| Ruta | Método | Función | Qué hace |
|------|--------|---------|----------|
| `/admin/bulk-upload/` | GET/POST | `index()` | Upload de CSV. Valida columnas, reglas de stock/precio, normaliza género. Hasta 50 productos. Retorna resumen válidos/errores |

#### `routes/admin_coupons.py` — `CouponsAdminView`

| Ruta | Método | Función | Qué hace |
|------|--------|---------|----------|
| `/admin/coupons/` | GET | `index()` | Lista cupones ordenados por created_at DESC |
| `/admin/coupons/new` | GET/POST | `new()` | Crear cupón (type, caps, fechas con conversión timezone→UTC, límites) |
| `/admin/coupons/edit/<id>` | GET/POST | `edit()` | Editar cupón existente |
| `/admin/coupons/toggle/<id>` | POST | `toggle()` | Toggle activo/inactivo |

#### `routes/admin_orders.py` — `OrderAdminView` (usa `OrderService`)

| Ruta | Método | Función | Qué hace |
|------|--------|---------|----------|
| `/admin/orders/` | GET | `index()` | Lista órdenes con estadísticas (total, pendientes, pagadas, reembolsadas, sin enviar, en proceso, enviadas, entregadas) |
| `/admin/orders/<id>` | GET/POST | `detail()` | Detalle de orden. POST actualiza estado pago/envío con validación de transiciones + status_history JSONB |
| `/admin/orders/transition/<id>/<action>` | POST | `transition()` | Actualiza estado principal via ORDER_STATES |
| `/admin/orders/json` | GET | `json()` | Órdenes como JSON con filtros opcionales (fechas, estado_pago, estado_envio). Para DataTable |

#### `routes/analytics.py` — `AnalyticsAdmin`

| Ruta | Método | Función | Qué hace | Login? |
|------|--------|---------|----------|--------|
| `/admin/analytics/` | GET | `index()` | Dashboard: vistas de producto, rutas de navegación, funnel, KPIs, top ciudades/regiones. Filtro por fecha | Sí |
| `/admin/analytics/track_view/<id>` | POST | `track_view()` | Registra vista de producto con session_id, referrer, geolocalización (IP). Tabla product_views | **No** |
| `/admin/analytics/track_navigation` | POST | `track_navigation()` | Registra navegación de página. Tabla user_navigation | **No** |
| `/admin/analytics/track_buy_click/<id>` | POST | `track_buy_click()` | Registra click en "Comprar". Tabla user_navigation | **No** |

---

### 5.3 Rutas NO Registradas (CÓDIGO MUERTO)

| Archivo | Blueprint | Ruta definida | Por qué está muerto |
|---------|-----------|---------------|---------------------|
| `routers/bulk_upload.py` | `bulk_upload_bp` | POST `/bulk-upload` | **No se registra** en `__init__.py`. Supersedido por `admin_bulk_upload.py` |
| `routers/product_images.py` | `bulk_upload_bp` (conflicto de nombre) | POST `/bulk-upload` | **No se registra** en `__init__.py`. Conflicto de namespace con el anterior |

---

## 6. Servicios

### 6.1 `services/pricing.py` — Motor de Precios

| Función | Firma | Descripción |
|---------|-------|-------------|
| `_dec(x)` | `_dec(x) → Decimal` | Convierte a Decimal de forma segura. None → "0" |
| `_round2(x)` | `_round2(x) → Decimal` | Redondea a 2 decimales con ROUND_HALF_UP |
| `is_coupon_active(coupon, now_utc=None)` | `→ bool` | Valida que el cupón esté `active=True` Y dentro del rango `starts_at`/`ends_at`. Parsea ISO datetime, maneja tzinfo |
| `apply_coupon(base_amount, coupon, msi_selected)` | `→ Decimal` | Calcula descuento respetando: type (percent/fixed), cap_mode (amount/percent/both), caps MSI. Nunca excede base_amount |
| `compute_totals(items, shipping_base, free_shipping_threshold, coupon, msi_selected, coupon_percent_base)` | `→ Dict` | **Motor principal**: items → subtotalProducts, shipping (gratis si ≥ threshold), preCoupon, discount_total, total |

### 6.2 `services/discounts_service.py` — Capa de Descuentos

| Función | Estado | Nota |
|---------|--------|------|
| `is_coupon_active()` | **⚠️ SIN USO** | Duplicado de `pricing.py`. 0 imports detectados |
| `apply_coupon()` | **⚠️ SIN USO** | Duplicado de `pricing.py`. 0 imports detectados |

### 6.3 `services/limits_service.py` — Límites de Uso de Cupones

| Función | Firma | Descripción |
|---------|-------|-------------|
| `_count(sb, table, **eq)` | `→ int` | Helper: cuenta filas con `count="exact"`. Fallback a `len(data)` si el gateway no envía header |
| `can_use_coupon(sb, coupon, user_id, email)` | `→ Tuple[bool, str]` | Verifica `max_uses` (global) y `max_uses_per_user` (por user_id o email normalizado). Retorna `(True, "ok")` o `(False, "limit_reached_global"|"limit_reached_user")` |

---

## 7. Templates — Mapa Completo

### 7.1 Layout y Partials

| Template | Propósito | Estado |
|----------|-----------|--------|
| `base.html` | Layout maestro. Carga TailwindCSS, FontAwesome, Slick, AOS, Google Fonts. Inyecta `SUPABASE_URL`/`ANON_KEY` en `globalThis` | ✅ ACTIVO |
| `partials/header.html` | Banner promo fijo con marquee (6 MSI, oro, envío) + botón cerrar | ✅ ACTIVO |
| `partials/footer.html` | Footer simple (© 2025 VALAC Joyas) | ✅ ACTIVO |
| `partials/tracking.html` | Snippet JS de analytics: fetch a `trackView()` y `trackNavigation()` | ✅ ACTIVO |

### 7.2 Páginas de Cliente

| Template | Renderizado por | Propósito | Estado |
|----------|----------------|-----------|--------|
| `home.html` | `main.home()` | Homepage con cards de género, estilo lujo, animaciones | ✅ ACTIVO |
| `collection.html` | `collection.collection_home()` | Lista de productos con filtros, paginación, chips UI | ✅ ACTIVO |
| `product.html` | `products.product_detail()` | Detalle: imagen hero, badge descuento, galería, add-to-cart, relacionados | ✅ ACTIVO |
| `cart.html` | `cart.view_cart()` | Carrito: eliminación, cupón, totales con lógica de envío | ✅ ACTIVO |
| `checkout.html` | `checkout.checkout()` | Formulario de envío + resumen + link MercadoPago | ✅ ACTIVO |
| `checkout_luxury.html` | `checkout.checkout()` (variante) | UI de checkout alternativa (lujo) | ✅ ACTIVO |
| `mercadopago_checkout.html` | Usado en checkout flow | Pago MP con progress steps, terms | ✅ ACTIVO |
| `mock_checkout.html` | `mock_checkout.index()` | Simulador dev: botones success/pending/failure | ✅ ACTIVO |
| `about.html` | `main.about()` | Misión, Visión, Valores de la empresa | ✅ ACTIVO |
| `contact.html` | `contact.contact()` | Formulario de contacto + ubicación | ✅ ACTIVO |
| `login.html` | `auth.login()` | Login admin (username/password) | ✅ ACTIVO |

### 7.3 Páginas de Resultado de Pago

| Template | Renderizado por | Estado |
|----------|----------------|--------|
| `success.html` | `success.success()` | ✅ ACTIVO |
| `pending.html` | `pending.pending()` | ✅ ACTIVO |
| `failure.html` | `failure.failure()` | ✅ ACTIVO |
| `pago_en_proceso.html` | **NINGUNO** | ⚠️ **SIN USO** — nunca se llama `render_template("pago_en_proceso.html")` |

### 7.4 Tracking de Órdenes

| Template | Renderizado por | Estado |
|----------|----------------|--------|
| `order_success.html` | `success.success()` (alternativo) | ✅ ACTIVO |
| `order_track.html` | `orders.track()` | ✅ ACTIVO |
| `order_summary.html` | **NINGUNO** | ⚠️ **SIN USO** — nunca se llama `render_template("order_summary.html")` |

### 7.5 Templates Admin

| Template | Vista | Estado |
|----------|-------|--------|
| `admin/supabase_products.html` | `SupabaseProductAdmin.index()` | ✅ ACTIVO |
| `admin/supabase_new_product.html` | `SupabaseProductAdmin.new()` | ✅ ACTIVO |
| `admin/supabase_edit_product.html` | `SupabaseProductAdmin.edit_product()` | ✅ ACTIVO |
| `admin/supabase_gallery.html` | `SupabaseProductAdmin.gallery()` | ✅ ACTIVO |
| `admin/orders_list.html` | `OrderAdminView.index()` | ✅ ACTIVO |
| `admin/admin_order_detail.html` | `OrderAdminView.detail()` | ✅ ACTIVO |
| `admin/bulk_upload.html` | `BulkUploadAdminView.index()` | ✅ ACTIVO |
| `admin/coupons_list.html` | `CouponsAdminView.index()` | ✅ ACTIVO |
| `admin/coupons_form.html` | `CouponsAdminView.new()/edit()` | ✅ ACTIVO |
| `admin/analytics.html` | `AnalyticsAdmin.index()` | ✅ ACTIVO |

### 7.6 Email

| Template | Usado por | Estado |
|----------|-----------|--------|
| `templates/email/order_success_email.html` | `success.success()` vía SMTP | ✅ ACTIVO |
| `email/order_success_email.html` (raíz de valac_jewelry) | ¿Duplicado? | ⚠️ **DUPLICADO** |

### 7.7 Template Faltante

| Template esperado | Referenciado en | Estado |
|-------------------|-----------------|--------|
| `wishlist.html` | `cart.py` líneas ~377, ~391 | 🔴 **NO EXISTE** — causará error 500 si se accede |

---

## 8. JavaScript Frontend

### 8.1 `static/js/supabase-client.js`
- **Tipo**: ES Module
- **Qué hace**: Exporta singleton `supabase = createClient(url, key)` usando credenciales de `globalThis.SUPABASE_URL` + `globalThis.SUPABASE_ANON_KEY` (inyectadas desde `base.html`)
- **CDN**: `esm.sh/@supabase/supabase-js@2.12.0`
- **Usado por**: `collection.html`, `home.html`, `bulk_upload.html`
- **Estado**: ✅ ACTIVO

### 8.2 `static/js/supabase-client.mjs`
- **Contenido**: Idéntico a `supabase-client.js`
- **Importado por**: Ningún archivo
- **Estado**: ⚠️ **SIN USO** — duplicado innecesario

### 8.3 `static/js/inline-edit.js`
- **Qué hace**: Editor inline para tabla de productos en admin
- **Funcionalidad**:
  - Auto-attach a celdas con `data-editable="true"` (columna nombre)
  - Click → convierte celda en input (text para nombre, number para precio/stock)
  - Enter/blur → PATCH `/admin/supabase_products/api/quick-update/{id}` con `{field, value}`
  - Escape → cancela
  - Validación de tipo: nombre (no vacío), numbers (≥ 0)
  - Feedback visual: verde = éxito, rojo + restore = error
- **Estado**: ✅ ACTIVO

### 8.4 CSS

| Archivo | Propósito |
|---------|-----------|
| `static/css/output.css` | TailwindCSS compilado (producción) |
| `static/css/styles.css` | Input source de Tailwind (`@tailwind base/components/utilities`) |
| `static/css/admin-orders.css` | Estilos específicos para la vista de órdenes en admin |

---

## 9. Scripts y Utilidades

| Archivo | Propósito | Cuándo usar |
|---------|-----------|-------------|
| `run_waitress.py` | Servidor dev en Windows (0.0.0.0:5000 con Waitress) | Desarrollo local |
| `diagram.py` | Divide el repo en chunks de ~230 KB (`repo_part_01.txt`, etc.) para compartir código con LLMs | Análisis / debugging |
| `show_structure.py` | Imprime árbol de directorios (filtra `node_modules, __pycache__, .git, venv`) | Documentación rápida |
| `scripts/migrate_images_webp.py` | Convierte imágenes de Supabase Storage a WebP optimizado (≤1200px, q80). Actualiza URLs en DB. Modo dry-run por default (`--apply` para ejecutar) | Migración única |
| `setup.bat` | Setup inicial Windows: crea venv, instala deps, Git init, primer commit | Setup de ambiente |
| `check_env.bat` | Valida pre-requisitos: `.git/`, remote `origin`, `venv/` | Verificación rápida |

---

## 10. Archivos de Configuración

| Archivo | Propósito |
|---------|-----------|
| `Procfile` | Deploy en Heroku: `web: gunicorn valac_jewelry.app:app` |
| `requirements.txt` (raíz) | Dependencias Python principales (58 paquetes) |
| `valac_jewelry/requirements.txt` | **⚠️ OBSOLETO** — Subconjunto de 23 paquetes, le faltan deps clave (supabase, pandas, mercadopago) |
| `package.json` | Node.js: TailwindCSS tooling (`build-css`, `watch-css`) |
| `tailwind.config.js` | Config Tailwind: escanea `templates/**/*.html` + `static/**/*.js`. Colores custom: `cartier-gold (#A67C00)` |
| `.env` | Variables de entorno (Supabase, MP, SMTP, Admin creds) |
| `valac_jewelry/config.py` | `Config` (base), `DevelopmentConfig` (DEBUG=True), `ProductionConfig` (DEBUG=False) |

---

## 11. Modelos de Datos

### 11.1 Tabla `products`

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | int (PK) | ID autoincremental |
| `nombre` | text | Nombre del producto |
| `descripcion` | text | Descripción larga |
| `precio` | numeric | Precio base en MXN |
| `descuento_pct` | numeric | Porcentaje de descuento del producto (0-100) |
| `precio_descuento` | numeric | Precio calculado con descuento (precio × (1 - descuento_pct/100)) |
| `tipo_producto` | text | Categoría: anillo, collar, pulsera, arete, etc. |
| `genero` | text | Género: Mujer, Hombre, Unisex |
| `tipo_oro` | text | Tipo de oro: 10k, 14k, 18k, plata, etc. |
| `imagen` | text | Nombre de archivo de imagen principal |
| `destacado` | boolean | ¿Mostrar en homepage? |
| `stock_total` | int | Inventario disponible |
| `created_at` | timestamp | Fecha de creación |

### 11.2 Tabla `product_images`

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | int (PK) | ID autoincremental |
| `product_id` | int (FK) | Referencia a products.id |
| `imagen` | text | Nombre de archivo de imagen |
| `orden` | int | Posición en la galería (drag & drop) |

### 11.3 Tabla `orders`

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | int (PK) | ID autoincremental |
| `fecha_pedido` | timestamp | Fecha del pedido |
| `estado_pago` | text | `Completado` \| `Pendiente` \| `Fallido` \| `Rechazado` \| `Cancelado` |
| `estado_envio` | text | `sin_enviar` → `en_proceso` → `enviado` → `entregado` \| `cancelado` |
| `user_id` | text | Identificador del usuario (email o ID) |
| `direccion_envio` | text | Dirección de envío completa |
| `ciudad` | text | Ciudad de envío |
| `status_history` | jsonb | Historial de cambios de estado `[{estado, fecha, nota}]` |
| `external_reference` | text | Referencia de MercadoPago |

### 11.4 Tabla `coupons`

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | int (PK) | ID autoincremental |
| `code` | text | Código del cupón (e.g., "VALAC20") |
| `type` | text | `percent` (%) \| `fixed` (monto fijo MXN) |
| `value` | numeric | Valor del descuento (20 = 20% o $20) |
| `active` | boolean | ¿Habilitado? |
| `starts_at` | timestamp | Inicio de vigencia (UTC) |
| `ends_at` | timestamp | Fin de vigencia (UTC) |
| `cap_mode` | text | Modo de tope: `amount` \| `percent` \| `both` |
| `cap_amount` | numeric | Tope de descuento en MXN (pago normal) |
| `cap_percent` | numeric | Tope de descuento en % (pago normal) |
| `cap_amount_msi` | numeric | Tope en MXN para pago a MSI |
| `cap_percent_msi` | numeric | Tope en % para pago a MSI |
| `min_order_amount` | numeric | Monto mínimo de orden para aplicar |
| `max_uses` | int | Límite global de usos (NULL = ilimitado) |
| `max_uses_per_user` | int | Límite por usuario/email (NULL = ilimitado) |
| `notes` | text | Notas internas del admin |

### 11.5 Tabla `coupon_redemptions`

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | int (PK) | ID autoincremental |
| `coupon_id` | int (FK) | Referencia a coupons.id |
| `user_id` | text | ID del usuario que redimió |
| `email` | text | Email del usuario (normalizado a lowercase) |

### 11.6 Tablas de Analytics

| Tabla | Columnas clave | Propósito |
|-------|---------------|-----------|
| `product_views` | product_id, session_id, referrer, city, region, country | Vistas de producto |
| `user_navigation` | path, session_id, city, region, country | Navegación de usuario |

### 11.7 Carrito (sin persistencia en DB)

```
Flask session:
  session["cart"] = {"<product_id>": quantity, ...}
  session["cart_snapshot"] = {
    "subtotal": Decimal,
    "shipping": Decimal,
    "discount": Decimal,
    "total": Decimal,
    "coupon_code": str | None
  }
  session["coupon_code"] = str | None

Regla de envío:
  - Gratis si subtotal ≥ $8,500 MXN
  - $260 MXN flat si menor
```

---

## 12. Integraciones Externas

### 12.1 Supabase
- **Usado en**: Prácticamente todos los archivos
- **Cliente**: `current_app.supabase` (creado una vez en `create_app()`)
- **Operaciones**: SELECT, INSERT, UPDATE, DELETE en tablas + Upload/Delete en Storage
- **Frontend**: Supabase JS client inyectado en `base.html` via `globalThis`

### 12.2 MercadoPago
- **SDK**: `mercadopago` Python v2
- **Dual-token**: `MP_ACCESS_TOKEN` (producción) / `MP_ACCESS_TOKEN_TEST` (test)
- **Flujo**: Crear preferencia → redirect a MP → webhook de vuelta
- **Webhook**: `/webhook/mercadopago` (verifica estado real con API de MP)
- **Instalments**: Configurable via `MP_MAX_INSTALLMENTS` env var

### 12.3 SMTP Email (Gmail)
- **Usado en**: `routes/success.py`
- **Config**: `MAIL_SERVER` (smtp.gmail.com), `MAIL_PORT` (587), TLS
- **Template**: `templates/email/order_success_email.html`
- **Trigger**: Después de pago exitoso

### 12.4 Cloudflare Workers CDN
- **URL**: `CDN_BASE_URL` → `valac-image-proxy.valacjoyas.workers.dev/products/`
- **Propósito**: Proxy sobre Supabase Storage para cache + edge delivery
- **Uso**: Todas las URLs de imagen de producto = `CDN_BASE_URL + nombre_archivo`

### 12.5 ipapi.co (Geolocalización)
- **Usado en**: `routes/analytics.py`
- **Propósito**: Resolver IP → ciudad/región/país para analytics
- **Endpoints que lo usan**: `track_view`, `track_navigation`, `track_buy_click`

### 12.6 WhatsApp Business
- **Config**: `WHATSAPP_NUMBER` (env, default `527718574647`)
- **Uso**: Link de soporte en templates

---

## 13. Clasificación: Crítico vs No Crítico

### 🔴 CRÍTICO (si falla, el negocio se detiene)

| Componente | Archivo(s) | Por qué es crítico |
|------------|-----------|-------------------|
| **Home** | `routes/main.py`, `home.html` | Primera impresión, SEO, entrada al funnel |
| **Catálogo** | `routes/collection.py`, `collection.html` | Sin catálogo no hay venta |
| **Detalle de producto** | `routes/products.py`, `product.html` | Información necesaria para decidir compra |
| **Carrito** | `routes/cart.py`, `cart.html` | Core del e-commerce |
| **Checkout** | `routes/checkout.py`, `checkout.html` | Flujo de pago |
| **MercadoPago** | `routes/mercadopago_checkout.py`, `routes/checkout.py` | Procesamiento de pagos reales |
| **Webhook MP** | `routes/webhook.py` | Actualización automática de estado de pago |
| **Email confirmación** | `routes/success.py`, `email/order_success_email.html` | Confianza del cliente |
| **Supabase client** | `__init__.py` (create_client) | Sin DB no hay nada |
| **Config/Auth** | `config.py`, `auth.py` | Seguridad del admin |
| **CDN images** | Cloudflare Worker | Sin imágenes no hay venta visual |

### 🟡 IMPORTANTE (afecta operaciones pero no detiene ventas)

| Componente | Archivo(s) | Por qué importa |
|------------|-----------|-----------------|
| **Admin Productos** | `routes/admin.py`, templates admin/ | Gestión de inventario |
| **Admin Órdenes** | `routes/admin_orders.py` | Seguimiento de fulfillment |
| **Cupones** | `routes/admin_coupons.py`, `routes/coupons_api.py`, `services/` | Marketing + conversión |
| **Carga masiva** | `routes/admin_bulk_upload.py` | Eficiencia operativa |
| **Tracking público** | `routes/orders.py`, `order_track.html` | Experiencia post-compra |
| **Inline edit** | `static/js/inline-edit.js` | Productividad admin |

### 🟢 NICE-TO-HAVE (mejoran experiencia pero son prescindibles)

| Componente | Archivo(s) | Nota |
|------------|-----------|------|
| **Analytics** | `routes/analytics.py`, `admin/analytics.html` | Insights, no bloquea ventas |
| **Ventas/Pagos/Reportes** | `admin.py` (SalesAdmin, PaymentsAdmin, ReportsAdmin) | Dashboards informativos |
| **Mock checkout** | `routes/mock_checkout.py` | Solo desarrollo |
| **About** | `about.html` | Branding |
| **Contact** | `routes/contact.py`, `contact.html` | El form ni siquiera envía email (stub) |
| **Wishlist** | Rutas en `cart.py` | Template faltante → actualmente roto |
| **WebP migration** | `scripts/migrate_images_webp.py` | Script de una sola ejecución |
| **Diagram/Show structure** | `diagram.py`, `show_structure.py` | Utilidades de desarrollo |

---

## 14. Auditoría: Código Muerto, Duplicado y Problemas

### 🔴 Problemas Críticos

| # | Problema | Archivos | Acción recomendada |
|---|---------|----------|-------------------|
| 1 | **Template `wishlist.html` no existe** pero se llama en `cart.py` | `routes/cart.py` ~L377, ~L391 | Crear template o eliminar rutas de wishlist |
| 2 | **Webhook duplicado**: dos handlers de MP activos en rutas diferentes | `routes/webhook.py` + `routes/mercadopago_checkout.py` | Consolidar en uno solo |

### 🟡 Código Muerto / Duplicado

| # | Problema | Archivos | Acción recomendada |
|---|---------|----------|-------------------|
| 3 | **Routers no registrados**: `bulk_upload_bp` definido dos veces pero nunca importado | `routers/bulk_upload.py`, `routers/product_images.py` | Eliminar ambos archivos |
| 4 | **Service sin uso**: `discounts_service.py` tiene 0 imports | `services/discounts_service.py` | Eliminar archivo |
| 5 | **Firebase comentado**: 43 líneas de código legacy en app.py | `app.py` líneas 1-43 | Eliminar código comentado |
| 6 | **JS duplicado**: `supabase-client.mjs` es copia exacta sin importadores | `static/js/supabase-client.mjs` | Eliminar archivo |
| 7 | **Email template duplicado**: mismo HTML en dos rutas | `email/order_success_email.html` (×2) | Mantener solo `templates/email/` |
| 8 | **Templates sin uso**: nunca se renderizan | `pago_en_proceso.html`, `order_summary.html` | Eliminar o implementar |

### 🟡 Dependencias Innecesarias

| # | Problema | Archivo | Acción |
|---|---------|---------|--------|
| 9 | **Flask-SQLAlchemy** en requirements pero sin imports en el código | `requirements.txt` | Eliminar de requirements |
| 10 | **requirements.txt local** obsoleto e incompleto | `valac_jewelry/requirements.txt` | Eliminar (usar solo el de raíz) |

### 🟡 Funcionalidad Incompleta

| # | Problema | Archivo | Acción |
|---|---------|---------|--------|
| 11 | **Contact `/send` es stub**: no envía email, solo flash | `routes/contact.py` | Implementar envío real o documentar como intencional |
| 12 | **Lógica de cupón triplicada**: `pricing.py`, `discounts_service.py`, y `cart.py` cada uno define su propia versión | Múltiples | Centralizar en `pricing.py`, importar en los demás |

---

## 15. Dependencias

### 15.1 Python (key packages de `requirements.txt` raíz)

| Paquete | Versión | Propósito |
|---------|---------|-----------|
| Flask | 3.1.0 | Web framework |
| Flask-Admin | 1.6.1 | Panel admin |
| Flask-Login | 0.6.3 | Autenticación por sesión |
| Flask-SQLAlchemy | 3.1.1 | **⚠️ NO USADO — candidato a eliminar** |
| gunicorn | 23.0.0 | WSGI producción |
| supabase | (latest) | Cliente de DB |
| mercadopago | 2.2.3 | SDK de pagos |
| Pillow | (latest) | Procesamiento de imágenes (WebP) |
| python-dotenv | (latest) | Carga de .env |
| waitress | (latest) | WSGI desarrollo Windows |

### 15.2 Node.js (de `package.json`)

| Paquete | Versión | Propósito |
|---------|---------|-----------|
| tailwindcss | ^3.4.19 | Compilación CSS |
| postcss | ^8.5.6 | Post-procesamiento CSS |
| autoprefixer | ^10.4.23 | Prefijos de browser |

### 15.3 CDN Frontend (cargados en `base.html`)

| Librería | Versión | Propósito |
|----------|---------|-----------|
| jQuery | 3.6.0 | DOM manipulation |
| Slick Carousel | 1.8.1 | Carruseles de producto |
| AOS | 2.3.4 | Animaciones on-scroll |
| FontAwesome | 6.0 | Iconos |
| Lucide | latest (unpkg) | Iconos adicionales |
| Google Fonts | — | Playfair Display, Cormorant Garamond, Inter, Roboto |
| Supabase JS | 2.12.0 | Cliente Supabase frontend (via esm.sh) |

---

## Resumen Ejecutivo

| Métrica | Valor |
|---------|-------|
| **Blueprints registrados** | 15 |
| **Vistas Flask-Admin** | 8 |
| **Rutas totales** | ~65 |
| **Rutas públicas** | ~22 |
| **Rutas admin** | ~43 |
| **Templates** | 30 |
| **Templates en uso** | 27 |
| **Templates sin uso** | 2 (+1 faltante) |
| **Servicios** | 3 (1 sin uso) |
| **Scripts utility** | 6 |
| **Archivos JS** | 3 (1 sin uso) |
| **Tablas Supabase** | 6 + 2 analytics |
| **Issues de código** | 12 identificados |
| **Código muerto estimado** | ~200 líneas |
