# Plan de Migración: Supabase Storage → Cloudflare (Worker Proxy → R2)

> **Rama**: `CloudFaremigration`  
> **Objetivo**: Servir imágenes vía Cloudflare Worker (proxy a Supabase) sin downtime, como paso previo a R2.  
> **Principio**: Supabase sigue siendo el storage real. Cloudflare Worker actúa como proxy/caché. Flask apunta al Worker.

---

## 1. Pre-requisitos

| # | Requisito | Cómo verificar |
|---|-----------|----------------|
| 1 | **Cuenta Cloudflare** con plan Free o superior | Dashboard → `dash.cloudflare.com` |
| 2 | **Dominio propio** apuntado a Cloudflare DNS (o usar subdomain `.workers.dev`) | DNS → verificar NS |
| 3 | **Wrangler CLI** instalado | `npm install -g wrangler` → `wrangler --version` |
| 4 | **Autenticado en Wrangler** | `wrangler login` (abre browser) |
| 5 | **Acceso a Supabase Dashboard** (para queries SQL) | `supabase.com/dashboard` |
| 6 | **Variables de entorno actuales documentadas** | `.env` ya leído |
| 7 | **Backup de BD antes de tocar datos** | Ver Fase 4 — Rollback |

### Variables que necesitarás crear:

```
# Nuevas en .env (Flask)
CDN_BASE_URL=https://images.valacjoyas.com   # ← tu Worker (o subdominio workers.dev)

# En Cloudflare Worker (env vars del Worker)
SUPABASE_ORIGIN=https://fqxiyrvhwadydqlnswzb.supabase.co/storage/v1/object/public/CatalogoJoyasValacJoyas
```

---

## 2. Fase 1 — Cloudflare Worker como Proxy

### 2.1 Crear el proyecto Worker

```powershell
cd c:\Repos\Personal
npx wrangler init valac-image-proxy --type javascript
cd valac-image-proxy
```

### 2.2 Código del Worker — `src/index.js`

```javascript
/**
 * Cloudflare Worker: Proxy de imágenes Supabase → Cloudflare Edge
 * 
 * Ruta esperada:  GET /products/<filename>
 * Ejemplo:        https://images.valacjoyas.com/products/my-image.webp
 * Origen real:    https://xxx.supabase.co/storage/v1/object/public/CatalogoJoyasValacJoyas/products/my-image.webp
 */

const SUPABASE_ORIGIN =
  "https://fqxiyrvhwadydqlnswzb.supabase.co/storage/v1/object/public/CatalogoJoyasValacJoyas";

// Caché: 30 días en edge, 7 días en browser
const CACHE_CONTROL = "public, max-age=604800, s-maxage=2592000, immutable";

// Tipos MIME permitidos (seguridad)
const ALLOWED_EXTENSIONS = new Set([
  ".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg", ".avif",
]);

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // Solo GET
    if (request.method !== "GET") {
      return new Response("Method Not Allowed", { status: 405 });
    }

    // Health check
    if (url.pathname === "/" || url.pathname === "/health") {
      return new Response(JSON.stringify({ status: "ok", ts: Date.now() }), {
        headers: { "Content-Type": "application/json" },
      });
    }

    // Validar extensión
    const ext = url.pathname.substring(url.pathname.lastIndexOf(".")).toLowerCase();
    if (!ALLOWED_EXTENSIONS.has(ext)) {
      return new Response("Forbidden: file type not allowed", { status: 403 });
    }

    // Sanitizar path (prevenir directory traversal)
    const cleanPath = url.pathname.replace(/\.\./g, "").replace(/\/\//g, "/");

    // Construir URL de origen
    const origin = env.SUPABASE_ORIGIN || SUPABASE_ORIGIN;
    const originUrl = `${origin}${cleanPath}`;

    // Intentar desde Cloudflare Cache API primero
    const cache = caches.default;
    const cacheKey = new Request(url.toString(), request);

    let response = await cache.match(cacheKey);
    if (response) {
      return response; // Cache HIT
    }

    // Fetch desde Supabase
    const originResponse = await fetch(originUrl, {
      headers: {
        "User-Agent": "ValacJoyas-CDN-Worker/1.0",
      },
    });

    if (!originResponse.ok) {
      // No cachear errores
      return new Response("Image not found", {
        status: originResponse.status,
        headers: { "Cache-Control": "no-store" },
      });
    }

    // Construir response con headers de caché optimizados
    response = new Response(originResponse.body, {
      status: 200,
      headers: {
        "Content-Type": originResponse.headers.get("Content-Type") || "application/octet-stream",
        "Cache-Control": CACHE_CONTROL,
        "CDN-Cache-Control": CACHE_CONTROL,
        "Access-Control-Allow-Origin": "*",
        "X-Served-By": "valac-cdn-worker",
        "Vary": "Accept",
      },
    });

    // Guardar en Cache API (no bloquear respuesta)
    ctx.waitUntil(cache.put(cacheKey, response.clone()));

    return response;
  },
};
```

### 2.3 `wrangler.toml`

```toml
name = "valac-image-proxy"
main = "src/index.js"
compatibility_date = "2024-01-01"

[vars]
SUPABASE_ORIGIN = "https://fqxiyrvhwadydqlnswzb.supabase.co/storage/v1/object/public/CatalogoJoyasValacJoyas"

# --- Opción A: usar subdominio workers.dev (gratis, para probar) ---
# workers_dev = true
# URL resultante: https://valac-image-proxy.<tu-cuenta>.workers.dev

# --- Opción B: custom domain (producción) ---
# routes = [
#   { pattern = "images.valacjoyas.com/*", zone_name = "valacjoyas.com" }
# ]
```

### 2.4 Deploy y validación

```powershell
# Deploy
wrangler deploy

# Anotar la URL resultante, ejemplo:
# https://valac-image-proxy.TUCUENTA.workers.dev
```

### 2.5 Validación del Worker (ANTES de tocar Flask)

Ejecutar estos tests desde terminal:

```powershell
# Test 1: Health check
curl -s https://valac-image-proxy.TUCUENTA.workers.dev/health
# Esperado: {"status":"ok","ts":...}

# Test 2: Imagen existente (usar un filename real de tu bucket)
curl -I https://valac-image-proxy.TUCUENTA.workers.dev/products/our-story.jpg
# Esperado: HTTP/2 200, Content-Type: image/jpeg, X-Served-By: valac-cdn-worker

# Test 3: Imagen inexistente
curl -I https://valac-image-proxy.TUCUENTA.workers.dev/products/no-existe-xyz.jpg
# Esperado: HTTP 404

# Test 4: Directory traversal (seguridad)
curl -I "https://valac-image-proxy.TUCUENTA.workers.dev/../../../etc/passwd"
# Esperado: HTTP 403

# Test 5: Verificar cache (segunda llamada)
curl -I https://valac-image-proxy.TUCUENTA.workers.dev/products/our-story.jpg
# Esperado: cf-cache-status: HIT (segunda vez)
```

**No avanzar a Fase 2 hasta que los 5 tests pasen.**

---

## 3. Fase 2 — Cambios en Flask

### 3.1 Archivo: `.env`

**Agregar** nueva variable (NO borrar `SUPABASE_STORAGE_URL` todavía):

```diff
 SUPABASE_STORAGE_URL=https://fqxiyrvhwadydqlnswzb.supabase.co/storage/v1/object/public/CatalogoJoyasValacJoyas/products/
+CDN_BASE_URL=https://valac-image-proxy.TUCUENTA.workers.dev/products/
```

> **Producción con dominio propio**: `CDN_BASE_URL=https://images.valacjoyas.com/products/`

---

### 3.2 Archivo: `valac_jewelry/config.py` (L7)

**Antes:**
```python
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
    SUPABASE_STORAGE_URL = os.environ.get('SUPABASE_STORAGE_URL')
```

**Después:**
```python
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
    SUPABASE_STORAGE_URL = os.environ.get('SUPABASE_STORAGE_URL')
    # CDN: Cloudflare Worker proxy. Fallback a SUPABASE_STORAGE_URL si no está configurada.
    CDN_BASE_URL = os.environ.get('CDN_BASE_URL') or os.environ.get('SUPABASE_STORAGE_URL')
```

**Razón**: Si `CDN_BASE_URL` no está seteada, usa automáticamente la URL de Supabase → zero downtime.

---

### 3.3 Archivo: `valac_jewelry/__init__.py` (L54-55)

**Antes:**
```python
    @app.context_processor
    def inject_supabase_storage_url():
        return dict(SUPABASE_STORAGE_URL=app.config.get("SUPABASE_STORAGE_URL"))
```

**Después:**
```python
    @app.context_processor
    def inject_supabase_storage_url():
        return dict(
            SUPABASE_STORAGE_URL=app.config.get("SUPABASE_STORAGE_URL"),
            CDN_BASE_URL=app.config.get("CDN_BASE_URL"),
        )
```

**Razón**: Inyecta `CDN_BASE_URL` a todos los templates. Los templates de marketing (`home.html`, `about.html`) usarán `CDN_BASE_URL` en lugar de `SUPABASE_STORAGE_URL`.

---

### 3.4 Archivo: `valac_jewelry/routers/product_images.py` (L53 y L73)

**L53 — Antes:**
```python
        if any(f["name"] == filename for f in files):
            public_url = f"{current_app.config.get('SUPABASE_STORAGE_URL')}{filename}"
            logging.info("Imagen %s: Duplicado detectado. Reutilizando URL.", original_filename)
```

**L53 — Después:**
```python
        if any(f["name"] == filename for f in files):
            public_url = f"{current_app.config.get('CDN_BASE_URL')}{filename}"
            logging.info("Imagen %s: Duplicado detectado. Reutilizando URL.", original_filename)
```

**L73 — Antes:**
```python
        upload_response = supabase.storage.from_(bucket).upload(filename, content)
        if upload_response:
            public_url = f"{current_app.config.get('SUPABASE_STORAGE_URL')}{filename}"
            logging.info("Imagen %s: Subida exitosa. URL: %s", original_filename, public_url)
```

**L73 — Después:**
```python
        upload_response = supabase.storage.from_(bucket).upload(filename, content)
        if upload_response:
            public_url = f"{current_app.config.get('CDN_BASE_URL')}{filename}"
            logging.info("Imagen %s: Subida exitosa. URL: %s", original_filename, public_url)
```

---

### 3.5 Archivo: `valac_jewelry/routes/admin.py` — Refactor de `get_public_url()`

Este es el cambio más quirúrgico. El SDK `get_public_url()` siempre devuelve URLs de Supabase directas. Hay que reemplazarlo con construcción manual usando `CDN_BASE_URL`.

#### 3.5.1 Agregar helper centralizado (después de los helpers existentes, ~L100)

**Insertar después de** `def _parse_json_list(raw: str) -> List[Any]:` **(que termina ~L97):**

```python
def _build_cdn_url(storage_key: str) -> str:
    """
    Construye la URL pública de una imagen usando CDN_BASE_URL.
    
    storage_key: path relativo al bucket, ej "products/1234-abc.webp"
    Retorna: "https://images.valacjoyas.com/products/1234-abc.webp"
    
    Fallback: si CDN_BASE_URL no está configurada, construye la URL de Supabase.
    """
    cdn = _get_cfg("CDN_BASE_URL")
    if cdn:
        # CDN_BASE_URL ya termina en "products/", storage_key empieza con "products/"
        # Evitar duplicación del path prefix
        if storage_key.startswith("products/") and cdn.rstrip("/").endswith("/products"):
            filename = storage_key[len("products/"):]
            return f"{cdn.rstrip('/')}/{filename}" if not cdn.endswith("/") else f"{cdn}{filename}"
        return f"{cdn.rstrip('/')}/{storage_key.lstrip('/')}"
    
    # Fallback: construcción clásica Supabase
    base = _get_cfg("SUPABASE_URL")
    bucket = "CatalogoJoyasValacJoyas"
    return f"{base}/storage/v1/object/public/{bucket}/{storage_key}"
```

#### 3.5.2 L259 — Fallback upload (raw sin WebP)

**Antes (L252-263):**
```python
                sb.storage.from_("CatalogoJoyasValacJoyas").upload(
                    key_fb, tmp_path, {"content-type": mime_fb, "x-upsert": "false"},
                )
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
                pub = sb.storage.from_("CatalogoJoyasValacJoyas").get_public_url(key_fb)
                public_url = _extract_public_url(pub)
                if not public_url:
                    return jsonify({"error": "No se pudo obtener URL pública"}), 500
                return jsonify({"url": f"{public_url}?t={int(time.time() * 1000)}"}), 200
```

**Después:**
```python
                sb.storage.from_("CatalogoJoyasValacJoyas").upload(
                    key_fb, tmp_path, {"content-type": mime_fb, "x-upsert": "false"},
                )
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
                public_url = _build_cdn_url(key_fb)
                return jsonify({"url": f"{public_url}?t={int(time.time() * 1000)}"}), 200
```

#### 3.5.3 L297 — Upload WebP normal

**Antes (L297-302):**
```python
            # Obtener URL pública (manejar distintos retornos)
            pub = sb.storage.from_("CatalogoJoyasValacJoyas").get_public_url(key)
            public_url = _extract_public_url(pub)
            if not public_url:
                return jsonify({"error": "No se pudo obtener URL pública"}), 500

            # Cache bust
            return jsonify({"url": f"{public_url}?t={int(time.time() * 1000)}"}), 200
```

**Después:**
```python
            # Construir URL pública via CDN
            public_url = _build_cdn_url(key)

            # Cache bust
            return jsonify({"url": f"{public_url}?t={int(time.time() * 1000)}"}), 200
```

#### 3.5.4 Limpieza: `_extract_public_url` puede quedarse (no rompe nada) pero ya no se usa en el flujo principal.

---

### 3.6 Templates de marketing — Cambiar a CDN_BASE_URL

#### `valac_jewelry/templates/home.html`

**L78:**
```diff
-        <img src="{{ SUPABASE_STORAGE_URL }}jasmin-chew-UBeNYvk6ED0-unsplash.jpg" alt="Colección Mujer">
+        <img src="{{ CDN_BASE_URL }}jasmin-chew-UBeNYvk6ED0-unsplash.jpg" alt="Colección Mujer">
```

**L87:**
```diff
-        <img src="{{ SUPABASE_STORAGE_URL }}mangoldchain.jpg" alt="Colección Hombre">
+        <img src="{{ CDN_BASE_URL }}mangoldchain.jpg" alt="Colección Hombre">
```

**L114:**
```diff
-        <img src="{{ SUPABASE_STORAGE_URL }}our-story.jpg" alt="Nuestra Historia" ...>
+        <img src="{{ CDN_BASE_URL }}our-story.jpg" alt="Nuestra Historia" ...>
```

**L174:**
```diff
-      const placeholder = "{{ config['SUPABASE_STORAGE_URL'] }}placeholder.jpg";
+      const placeholder = "{{ CDN_BASE_URL }}placeholder.jpg";
```

#### `valac_jewelry/templates/about.html`

**L8:**
```diff
-  <section ... style="background-image: url('{{ SUPABASE_STORAGE_URL }}about-banner.jpg'); ...">
+  <section ... style="background-image: url('{{ CDN_BASE_URL }}about-banner.jpg'); ...">
```

**L88:**
```diff
-        <img src="{{ SUPABASE_STORAGE_URL }}goldbracelet.jpg" ...>
+        <img src="{{ CDN_BASE_URL }}goldbracelet.jpg" ...>
```

---

### 3.7 Templates que usan `p.imagen` de BD — NO requieren cambio de código

Estos renderizan la URL completa que ya está guardada en la BD. Funcionarán automáticamente después de la Fase 3 (migración de datos):

- `cart.html`
- `product.html`
- `collection.html`
- `success.html`
- `email/order_success_email.html`
- `admin/supabase_products.html`
- `admin/supabase_gallery.html`
- `admin/supabase_edit_product.html`
- `admin/bulk_upload.html`

---

## 4. Fase 3 — Migración de datos en BD

### 4.1 Definiciones

```
URL_VIEJA = https://fqxiyrvhwadydqlnswzb.supabase.co/storage/v1/object/public/CatalogoJoyasValacJoyas/
URL_NUEVA = https://valac-image-proxy.TUCUENTA.workers.dev/    (o https://images.valacjoyas.com/)
```

### 4.2 SELECT de verificación ANTES del cambio

Ejecutar en Supabase SQL Editor:

```sql
-- Contar registros afectados en products
SELECT COUNT(*) AS total_products,
       COUNT(*) FILTER (
         WHERE imagen LIKE '%fqxiyrvhwadydqlnswzb.supabase.co%'
       ) AS con_url_supabase
FROM products;

-- Contar registros afectados en product_images
SELECT COUNT(*) AS total_images,
       COUNT(*) FILTER (
         WHERE imagen LIKE '%fqxiyrvhwadydqlnswzb.supabase.co%'
       ) AS con_url_supabase
FROM product_images;

-- Ver muestra de URLs actuales
SELECT id, LEFT(imagen, 120) AS imagen_preview
FROM products
WHERE imagen IS NOT NULL
LIMIT 5;

SELECT id, LEFT(imagen, 120) AS imagen_preview
FROM product_images
WHERE imagen IS NOT NULL
LIMIT 5;
```

**Anotar los conteos.** Los usarás para verificar después.

### 4.3 Backup (CRÍTICO — hacer ANTES del UPDATE)

```sql
-- Crear tablas de backup
CREATE TABLE products_backup_urls AS
SELECT id, imagen FROM products WHERE imagen IS NOT NULL;

CREATE TABLE product_images_backup_urls AS
SELECT id, imagen FROM product_images WHERE imagen IS NOT NULL;

-- Verificar backup
SELECT COUNT(*) FROM products_backup_urls;
SELECT COUNT(*) FROM product_images_backup_urls;
```

### 4.4 UPDATE masivo

```sql
-- ⚠️ REEMPLAZA 'https://images.valacjoyas.com/' con tu URL real del Worker ⚠️

-- Tabla: products
UPDATE products
SET imagen = REPLACE(
  imagen,
  'https://fqxiyrvhwadydqlnswzb.supabase.co/storage/v1/object/public/CatalogoJoyasValacJoyas/',
  'https://images.valacjoyas.com/'
)
WHERE imagen LIKE '%fqxiyrvhwadydqlnswzb.supabase.co%';

-- Tabla: product_images
UPDATE product_images
SET imagen = REPLACE(
  imagen,
  'https://fqxiyrvhwadydqlnswzb.supabase.co/storage/v1/object/public/CatalogoJoyasValacJoyas/',
  'https://images.valacjoyas.com/'
)
WHERE imagen LIKE '%fqxiyrvhwadydqlnswzb.supabase.co%';
```

### 4.5 SELECT de verificación DESPUÉS del cambio

```sql
-- Verificar que YA NO quedan URLs de Supabase
SELECT COUNT(*) FILTER (
  WHERE imagen LIKE '%fqxiyrvhwadydqlnswzb.supabase.co%'
) AS urls_viejas_restantes
FROM products;

SELECT COUNT(*) FILTER (
  WHERE imagen LIKE '%fqxiyrvhwadydqlnswzb.supabase.co%'
) AS urls_viejas_restantes
FROM product_images;
-- Ambas deben dar 0.

-- Verificar que las nuevas URLs apuntan al CDN
SELECT id, LEFT(imagen, 120) AS imagen_preview
FROM products
WHERE imagen IS NOT NULL
LIMIT 5;

SELECT id, LEFT(imagen, 120) AS imagen_preview
FROM product_images
WHERE imagen IS NOT NULL
LIMIT 5;
```

---

## 5. Fase 4 — Rollback Plan (< 5 minutos)

### Escenario A: Worker se cae / imágenes no cargan

**Tiempo estimado: 2 minutos**

#### Paso 1: Revertir BD (SQL — 30 segundos)

```sql
-- Restaurar products
UPDATE products p
SET imagen = b.imagen
FROM products_backup_urls b
WHERE p.id = b.id;

-- Restaurar product_images
UPDATE product_images pi
SET imagen = b.imagen
FROM product_images_backup_urls b
WHERE pi.id = b.id;
```

#### Paso 2: Revertir .env en producción (30 segundos)

```bash
# Borrar CDN_BASE_URL o apuntarla de vuelta a Supabase
CDN_BASE_URL=https://fqxiyrvhwadydqlnswzb.supabase.co/storage/v1/object/public/CatalogoJoyasValacJoyas/products/
```

#### Paso 3: Restart del servicio Flask (30 segundos)

```bash
# Si usas Render/Railway/Heroku:
# Push del .env revertido o cambiar variable en dashboard

# Si usas Waitress local:
# Ctrl+C y re-ejecutar
python run_waitress.py
```

### Escenario B: Solo los templates de marketing fallan

Cambiar `CDN_BASE_URL` de vuelta en los templates a `SUPABASE_STORAGE_URL`:
```
Ya lo tienes en git — un solo `git checkout main -- valac_jewelry/templates/home.html valac_jewelry/templates/about.html`
```

### Escenario C: Solo nuevas imágenes subidas fallan

Revertir `product_images.py` y `admin.py` a usar `SUPABASE_STORAGE_URL`:
```
git checkout main -- valac_jewelry/routers/product_images.py valac_jewelry/routes/admin.py
```

### Post-rollback: limpiar tablas de backup (solo cuando todo sea estable)

```sql
DROP TABLE IF EXISTS products_backup_urls;
DROP TABLE IF EXISTS product_images_backup_urls;
```

---

## 6. Checklist Final

### Pre-deploy
- [ ] Worker desplegado y los 5 tests de Fase 1 pasan
- [ ] `.env` tiene `CDN_BASE_URL` apuntando al Worker
- [ ] `config.py` tiene `CDN_BASE_URL` con fallback
- [ ] `__init__.py` inyecta `CDN_BASE_URL` al context
- [ ] `product_images.py` usa `CDN_BASE_URL` en L53 y L73
- [ ] `admin.py` usa `_build_cdn_url()` en lugar de `get_public_url()`
- [ ] `home.html` usa `CDN_BASE_URL` (4 ocurrencias)
- [ ] `about.html` usa `CDN_BASE_URL` (2 ocurrencias)
- [ ] Tablas de backup creadas en BD (`products_backup_urls`, `product_images_backup_urls`)
- [ ] UPDATE masivo ejecutado y verificado (0 URLs viejas restantes)

### Post-deploy — Validación funcional
- [ ] **Home**: Las 3 imágenes de marketing cargan (Mujer, Hombre, Nuestra Historia)
- [ ] **About**: Banner y imagen de bracelet cargan
- [ ] **Collection**: Grid de productos muestra imágenes
- [ ] **Producto individual**: Galería multi-imagen funciona
- [ ] **Carrito**: Thumbnails de productos visibles
- [ ] **Admin → Productos**: Lista muestra imágenes
- [ ] **Admin → Galería**: Imágenes de galería visibles
- [ ] **Admin → Upload**: Subir nueva imagen → la URL guardada usa CDN
- [ ] **Admin → Carga Masiva**: CSV con imágenes funciona
- [ ] **Email de confirmación**: Imágenes en email se renderizan
- [ ] **Inspeccionar Network tab**: Todas las imágenes vienen con header `X-Served-By: valac-cdn-worker`
- [ ] **Cache**: Segunda carga de una imagen muestra `cf-cache-status: HIT`

### Limpieza (1 semana después, si todo estable)
- [ ] Eliminar tablas de backup: `DROP TABLE products_backup_urls; DROP TABLE product_images_backup_urls;`
- [ ] Remover código muerto: `_extract_public_url()` en `admin.py` (opcional, no rompe nada)
- [ ] Opcional: Renombrar `SUPABASE_STORAGE_URL` a `SUPABASE_STORAGE_URL_LEGACY` en `.env`

---

## Mapa de archivos modificados (resumen)

| Archivo | Cambio | Riesgo |
|---------|--------|--------|
| `.env` | Agregar `CDN_BASE_URL` | Bajo (additive) |
| `valac_jewelry/config.py` | Agregar `CDN_BASE_URL` con fallback | Bajo |
| `valac_jewelry/__init__.py` | Inyectar `CDN_BASE_URL` al context | Bajo |
| `valac_jewelry/routers/product_images.py` | 2 líneas: L53, L73 | Medio |
| `valac_jewelry/routes/admin.py` | Agregar `_build_cdn_url()`, reemplazar 2 bloques | Medio |
| `valac_jewelry/templates/home.html` | 4 ocurrencias `SUPABASE_STORAGE_URL` → `CDN_BASE_URL` | Bajo |
| `valac_jewelry/templates/about.html` | 2 ocurrencias `SUPABASE_STORAGE_URL` → `CDN_BASE_URL` | Bajo |
| **BD: `products`** | UPDATE masivo de campo `imagen` | Alto (tiene rollback) |
| **BD: `product_images`** | UPDATE masivo de campo `imagen` | Alto (tiene rollback) |

**Total: 5 archivos Python/config + 2 templates + 2 tablas en BD.**
