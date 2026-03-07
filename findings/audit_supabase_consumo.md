# Auditoría de Consumo Supabase — VALAC Joyas

> **Fecha**: 6 de marzo de 2026  
> **Objetivo**: Reducir Cached Egress y Storage al mínimo sin costo adicional  
> **Estado actual del ciclo Mar–Abr 2026**:

| Recurso | Uso | Límite | % |
|---------|----:|------:|--:|
| **Cached Egress** | 2.379 GB | 5 GB | **48%** ← objetivo principal |
| **Storage Size** | 0.463 GB | 1 GB | **46%** ← segundo objetivo |
| Egress directo | 0.139 GB | 5 GB | 3% |
| Database | 0.079 GB | 0.5 GB | 16% |

---

## FASE 1 — Inventario de Imágenes en Storage

### Puntos de Upload Encontrados

Se identificaron **4 mecanismos independientes** de upload de imágenes:

#### A. Admin Principal (new/edit product) — `admin.py` L162–L257

| Aspecto | Valor |
|---------|-------|
| Endpoint | `POST /admin/supabase_products/storage/upload` |
| Auth | Supabase **SERVICE KEY** (backend) |
| Formatos | `.jpg`, `.jpeg`, `.png`, `.webp` |
| Bucket | `CatalogoJoyasValacJoyas` → path `products/` |
| Key naming | `products/{timestamp_ms}-{uuid_hex}{ext}` |
| **Compresión** | ❌ **NINGUNA** — archivo raw subido tal cual |
| **Redimensionamiento** | ❌ **NINGUNO** |
| **Conversión WebP** | ❌ **NO** |
| **Límite servidor** | ❌ `MAX_CONTENT_LENGTH` **no está definido** |
| Límite cliente | 5 MB (validación JS) |
| **Thumbnails** | ❌ Solo se genera 1 versión |

> **Este es el path principal de upload** — usado por los templates de crear/editar producto.

#### B. Bulk Upload Router — `routers/product_images.py`

| Aspecto | Valor |
|---------|-------|
| Formatos | Solo `.jpg`, `.jpeg` (rechaza png/webp) |
| **Compresión** | ✅ **SÍ** — si archivo > 2 MB, Pillow recomprime a JPEG q70 |
| Auth | Anon key (⚠️ sin SERVICE KEY) |
| Deduplicación | Lista archivos del bucket, evita duplicados |

#### C. Bulk Upload Admin View — `admin_bulk_upload.py`

- Solo valida CSV. **No hace insert** — el código Supabase está comentado.
- Lee columna `imagen` del CSV como URL. No sube archivos.

#### D. Bulk Upload Template JS — `bulk_upload.html` L148–L162

- Upload directo desde browser con **anon key expuesta**.
- **Sin compresión** ni validación de tamaño.

### Resumen de Procesamiento de Imágenes

| Path de upload | Compresión | Resize | WebP | Thumbnails |
|---------------|:-:|:-:|:-:|:-:|
| Admin new/edit | ❌ | ❌ | ❌ | ❌ |
| Bulk router | ✅ JPEG q70 si >2MB | ❌ | ❌ | ❌ |
| Bulk template JS | ❌ | ❌ | ❌ | ❌ |

### Librerías Disponibles

- `Pillow==11.2.1` — **instalada** pero solo usada en bulk router
- `pillow_heif==0.22.0` — **instalada pero nunca importada** (dependencia muerta)

### Schema de Imágenes

```
products.imagen     → URL string (imagen principal/portada)
product_images      → tabla separada con FK (galería multi-imagen)
  ├── product_id    → FK a products.id
  ├── imagen        → URL string  
  └── orden         → int (orden de display)
```

---

## FASE 2 — Cómo Se Sirven las Imágenes

### Inventario de `<img>` tags

| # | Archivo | `loading="lazy"` | `width/height` | `srcset` | Tipo |
|---|---------|:-:|:-:|:-:|---|
| 1 | `collection.html` (product cards JS) | ❌ | ❌ | ❌ | Producto — grid principal |
| 2 | `collection.html` (hover images JS) | ❌ | ❌ | ❌ | Producto — hover |
| 3 | `home.html` (hero Mujer) | ❌ | ❌ | ❌ | Marketing — above fold |
| 4 | `home.html` (hero Hombre) | ❌ | ❌ | ❌ | Marketing — above fold |
| 5 | `home.html` (Our Story) | ❌ | ❌ | ❌ | Marketing — below fold |
| 6 | `home.html` (product cards JS) | ✅ | ❌ | ❌ | Producto — grid |
| 7 | `product.html` (main gallery) | ✅ | ❌ | ⚠️ Fake* | Detalle |
| 8 | `product.html` (thumbnails) | ✅ | ❌ | ❌ | Detalle |
| 9 | `product.html` (related) | ✅ | ❌ | ❌ | Relacionados |
| 10 | `cart.html` | ❌ | ❌ | ❌ | Carrito |
| 11 | `about.html` | ❌ | ❌ | ❌ | Marketing |

> *\* `product.html` tiene `srcset="url 400w, url 800w"` pero usa la **misma URL** para ambos breakpoints — no genera versiones reales.*

### Hallazgos Críticos de Serving

1. **`collection.html` — la página más visitada — NO tiene `loading="lazy"`** en las imágenes de productos. Todas las imágenes del grid cargan eagerly, incluyendo las que están debajo del fold.

2. **Cada imagen se sirve a resolución original** sin importar el contexto:
   - En el grid de colección (muestra a ~256px de alto) se descarga la imagen full-size (puede ser 2000x3000px).
   - No hay thumbnails ni versiones redimensionadas.

3. **Hover images**: Cada producto en el grid carga **2 imágenes** (main + hover). La hover image se descarga aún si el usuario nunca pasa el mouse por encima.

4. **No hay CDN ni cache headers**: Cero configuración de `Cache-Control`, `max-age`, o CDN. Las imágenes dependen enteramente de los headers default de Supabase Storage.

5. **Marketing images hardcodeadas** en Storage: `home.html` y `about.html` referencian imágenes estáticas (hero, our-story, backgrounds) directamente desde Supabase Storage con `{{ SUPABASE_STORAGE_URL }}filename.jpg`. Cada visita al home descarga estas imágenes.

### URLs de Imágenes

- **Productos**: URL completa almacenada en DB (`products.imagen` y `product_images.imagen`).
- **Marketing**: Concatenación manual: `{{ SUPABASE_STORAGE_URL }}nombre-archivo.jpg`.
- **`get_public_url()`**: Solo se llama 1 vez — al momento del upload en `admin.py` L247. No se regenera en cada request (bien).
- **Cache-bust**: Se agrega `?t={timestamp}` a la URL al momento del upload para evitar caché del admin.

---

## FASE 3 — Auditoría de Queries a la Base de Datos

### Queries que Usan `SELECT *`

| # | Archivo | Línea | Tabla | Contexto | Impacto |
|---|---------|-------|-------|----------|---------|
| 1 | `main.py` | L11 | `products` | Home page — 3 productos | Bajo (solo 3 rows) |
| 2 | `products.py` | L11 | `products` | Detalle de producto | Bajo (1 row) |
| 3 | `products.py` | L20 | `product_images` | Galería de producto | Bajo |
| 4 | `products.py` | L27 | `products` + nested | Relacionados | Medio — trae `descripcion` innecesariamente |
| 5 | `checkout.py` | L35 | `products` | **Dentro de loop** | **Alto** — N+1 |
| 6 | `cart.py` | L382 | `products` | **Wishlist loop** | **Alto** — N+1 |
| 7 | `admin.py` | L265 | `products` | Admin index — TODOS los productos | Medio (admin) |

### Queries con Columnas Específicas (bien)

| Archivo | Tabla | Columnas |
|---------|-------|----------|
| `collection.py` L70 | `products` | `id, nombre, descripcion, precio, descuento_pct, precio_descuento, tipo_producto, genero, tipo_oro, imagen, created_at` |
| `cart.py` L174 | `products` | `id, nombre, precio, descuento_pct, precio_descuento, stock_total, imagen` |
| `admin.py` L401 | `products` | `id, precio, stock_total` |
| `admin.py` L877 | `products` | `id, nombre, imagen` |

### Queries Sin LIMIT (traen toda la tabla)

| Archivo | Línea | Tabla | Problema |
|---------|-------|-------|----------|
| `analytics.py` | L107 | `product_views` | **Trae TODOS los registros de vistas** — crece infinitamente |
| `analytics.py` | L158 | `user_navigation` | **Trae TODOS los eventos de navegación** — crece infinitamente |
| `admin.py` | L265 | `products` | Todos los productos con `SELECT *` (admin) |

### Patrones N+1 (CRÍTICOS)

#### 1. Cart — `cart.py` L170–L195
```python
for product_key, quantity in cart_data.items():
    resp = sb.table('products').select('id,nombre,precio,...').eq('id', pid).single().execute()
```
**5 items en carrito = 5 queries HTTP separadas a Supabase.**

#### 2. Checkout — `checkout.py` L30–L50
```python
for product_id_str, quantity in cart_data.items():
    resp = supabase.table('products').select('*').eq('id', product_id).single().execute()
```
**Mismo patrón N+1 durante checkout** — la ruta más sensible a latencia.

#### 3. Wishlist — `cart.py` L380–L390
```python
for product_id in wishlist_items:
    resp = sb.table('products').select('*').eq('id', product_id).single().execute()
```

**Solución para los 3**: Reemplazar el loop por una sola query con `.in_()`:
```python
product_ids = list(cart_data.keys())
resp = sb.table('products').select('id,nombre,precio,...').in_('id', product_ids).execute()
```

### Tracking Duplicado — **El hallazgo más impactante en egress**

**En `product.html`**, cada visita a un producto dispara:

| Fuente | Calls HTTP | Inserts DB |
|--------|:-:|:-:|
| Script inline (L292–L300) | `track_navigation` + `track_view` = 2 | 2 |
| `{% include 'partials/tracking.html' %}` (L348) | `track_navigation` + `track_view` = 2 | 2 |
| **Total por page view** | **4 requests** | **4 inserts** |

Cada tracking call además ejecuta `requests.get("https://ipapi.co/{ip}/json/")` — una llamada HTTP síncrona externa que:
- **Bloquea la respuesta de Flask** hasta 2.5s
- Usa la API gratuita de ipapi.co (límite de 1000/día)
- Duplica el trabajo porque se llama 4 veces con el mismo IP

**Impacto estimado**: Si la página de producto recibe 100 visitas/día:
- 400 inserts/día en Supabase (200 innecesarios)
- 400 llamadas a ipapi.co (200 innecesarias)
- Las tablas `product_views` y `user_navigation` crecen al doble de velocidad

### Tracking en Otras Páginas

| Página | Tracking calls |
|--------|:-:|
| `home.html` | 1 (`/api/track-route`) + 1 tracking partial = **2** (uno duplicado) |
| `collection.html` | 1 por click en producto (OK — no duplicado) |
| `product.html` | **4** (2 duplicados) |

### Query Client-Side Sin Limit

**`collection.html` L351–L390** — La query JS al catálogo:
```js
let query = supabaseClient
  .from('products')
  .select(`id, nombre, descripcion, precio, ... product_images(imagen, orden)`)
  .gte('precio', parseInt(price_min))
  .lte('precio', parseInt(price_max));

const { data: products, error } = await query;
```

**No tiene `.limit()` ni `.range()`** — trae TODOS los productos que cumplan el filtro de precio. Con nested `product_images`, si hay 200 productos con 5 imágenes cada uno = 200 + 1000 rows en una sola respuesta.

---

## FASE 4 — Quick Wins de Optimización

### P0 — Impacto Alto, Esfuerzo Bajo

#### P0-1. Eliminar tracking duplicado en `product.html`

**Problema**: Cada vista de producto genera 4 requests HTTP y 4 inserts en DB (el doble de lo necesario).  
**Reducción estimada**: ~50% del crecimiento de tablas de analytics + ~50% de las geolocation API calls.

**Solución**: Eliminar los scripts inline de tracking en `product.html` (L288–L306) y dejar solo el `{% include 'partials/tracking.html' %}`.

```html
<!-- ELIMINAR este bloque completo de product.html (L288-L306): -->
<script>
  const sessionId = localStorage.getItem("valac_session_id") || crypto.randomUUID();
  localStorage.setItem("valac_session_id", sessionId);
  fetch("/admin/analytics/track_navigation", { ... });
  fetch("/admin/analytics/track_view/{{ product.id }}", { ... });
</script>
```

**Complejidad**: 🟢 5 minutos

---

#### P0-2. Agregar `loading="lazy"` a imágenes del grid en `collection.html`

**Problema**: Todas las imágenes del catálogo (la página más visitada) cargan eagerly — incluyendo las ~20+ que están debajo del fold.  
**Reducción estimada**: ~30-40% del cached egress de imágenes en la página de colección.

**Solución**: En `collection.html` ~L473, agregar `loading="lazy"` a los `<img>`:

```js
// Antes:
<img src="${mainImage}" alt="${product.nombre}"
     class="w-full h-full object-cover ...">

// Después:
<img src="${mainImage}" alt="${product.nombre}"
     loading="lazy"
     class="w-full h-full object-cover ...">
```

Lo mismo para la hover image (~L476).

**Complejidad**: 🟢 5 minutos

---

#### P0-3. Agregar compresión WebP + resize en el upload principal

**Problema**: Las imágenes se suben raw. Una foto de 4000×3000px en JPEG de 4MB se almacena y sirve tal cual, cuando solo se necesitan ~800px de ancho máximo para el sitio.  
**Reducción estimada**: ~50-70% de Storage + ~50-70% de Cached Egress por imágenes.

**Solución**: En `admin.py` `storage_upload()`, antes de escribir al temp file, procesar con Pillow:

```python
from PIL import Image
import io

# Después de recibir el archivo, antes de subir:
f.stream.seek(0)
img = Image.open(f.stream)

# Limitar dimensiones máximas (1200px lado mayor)
max_dim = 1200
if max(img.size) > max_dim:
    img.thumbnail((max_dim, max_dim), Image.LANCZOS)

# Convertir a WebP con calidad 80
buffer = io.BytesIO()
img.save(buffer, format="WEBP", quality=80, optimize=True)
buffer.seek(0)

# Cambiar la extensión y mime
ext = ".webp"
mime = "image/webp"
key = f"products/{int(time.time() * 1000)}-{uuid.uuid4().hex}{ext}"

# Escribir buffer al tmp file (en lugar del raw)
tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".webp")
tmp.write(buffer.read())
tmp_path = tmp.name
tmp.close()
```

**Impacto numérico**:
- Imagen típica JPEG 4MB → WebP 1200px ~150-300KB = **reducción ~90%**
- Si hay 200 imágenes a 2MB promedio = 400MB storage → ~60MB = **ahorro ~340MB de storage**
- Cada vez que se sirve, el egress se reduce proporcionalmente

**Complejidad**: 🟡 30 minutos

---

#### P0-4. Limitar la query del catálogo con `.limit()`

**Problema**: `collection.html` JS trae TODOS los productos sin paginación, incluyendo nested `product_images`.  
**Reducción estimada**: ~20-30% de database egress si hay >50 productos.

**Solución**: Agregar `.limit(100)` a la query JS (o implementar paginación real):

```js
const { data: products, error } = await query.limit(100);
```

**Complejidad**: 🟢 5 minutos

---

### P1 — Impacto Medio, Esfuerzo Medio

#### P1-1. Eliminar el query dual (server + client)

**Problema**: `collection.py` construye una query server-side que **nunca se usa**. El template hace su propia query JS.  
**Solución**: Elegir uno:
- **Opción A** (rápida): Eliminar la query server-side de `collection.py` — reducir a solo pasar parámetros al template.
- **Opción B** (mejor): Mover toda la lógica a server-side, pasar `products|tojson` al template, eliminar query JS.

**Complejidad**: 🟡 Opción A: 30 min / 🔴 Opción B: 4-6 horas

---

#### P1-2. Resolver N+1 en cart y checkout

**Problema**: Cart con 5 items = 5 queries. Checkout = 5 queries más.  
**Solución**: Batch query con `.in_()`:

```python
# cart.py — view_cart()
product_ids = [str(k) for k in cart_data.keys()]
resp = sb.table('products') \
    .select('id,nombre,precio,descuento_pct,precio_descuento,stock_total,imagen') \
    .in_('id', product_ids) \
    .execute()
products_by_id = {str(p['id']): p for p in (resp.data or [])}

# Luego armar cart_items iterando cart_data usando products_by_id[pid]
```

**Reducción**: 5 queries → 1 query por vista de carrito/checkout.

**Complejidad**: 🟡 1 hora

---

#### P1-3. Generar thumbnails al momento del upload

**Problema**: En el grid se muestra la imagen a 256px de alto pero se descarga la versión completa.  
**Solución**: Al subir, generar 2 versiones:
1. `products/{id}_full.webp` — max 1200px (para detalle)
2. `products/{id}_thumb.webp` — max 400px (para grid/carrito)

Guardar ambas URLs en `product_images`:

```python
# Generar thumbnail
thumb = img.copy()
thumb.thumbnail((400, 400), Image.LANCZOS)
thumb_buffer = io.BytesIO()
thumb.save(thumb_buffer, format="WEBP", quality=75)
# Upload thumb_buffer con key diferente
```

**Reducción**: Las imágenes en grid pasan de ~500KB a ~30-50KB.

**Complejidad**: 🟡 2 horas (incluye migración de URLs existentes)

---

#### P1-4. Mover imágenes estáticas de marketing fuera de Supabase Storage

**Problema**: `home.html` y `about.html` referencian imágenes de marketing (hero, backgrounds, our-story) desde Supabase Storage. Cada visita al home las descarga.  
**Solución**: Mover a `/static/images/` y servir desde Flask (o CDN gratuito como Cloudflare Pages).

Archivos afectados:
- `jasmin-chew-UBeNYvk6ED0-unsplash.jpg` (hero Mujer)
- `mangoldchain.jpg` (hero Hombre)
- `our-story.jpg`
- `gold-earring.jpg` (background categorías)
- `cadenasjorge.jpg` (background categorías)
- `goldbracelet.jpg` (about)
- `placeholder.jpg`

**Reducción estimada**: Si estas 7 imágenes pesan ~5MB total y el home recibe 50 visitas/día:
- 5MB × 50 × 30 = ~7.5GB/mes de egress → se elimina de Supabase

**Complejidad**: 🟡 1 hora

---

### P2 — Mejoras Estructurales

#### P2-1. Agregar paginación real al catálogo

Implementar cursor-based o offset pagination en server-side con 36 productos/página.

#### P2-2. Implementar CDN con cache headers

- Agregar `Cache-Control: public, max-age=31536000, immutable` a las respuestas de imágenes estáticas.
- Considerar Cloudflare (free tier) como CDN frontal.

#### P2-3. Implementar `srcset` real

Generar versiones de 400w, 800w, 1200w al momento del upload. Usar `srcset` real en los templates.

#### P2-4. Cachear geolocalización de IP

Implementar cache en memoria (dict simple o `functools.lru_cache`) para evitar llamar ipapi.co con el mismo IP múltiples veces.

```python
from functools import lru_cache

@lru_cache(maxsize=256)
def get_location_from_ip_cached(ip_address):
    return self.get_location_from_ip(ip_address)
```

#### P2-5. Eliminar `pillow_heif` de requirements

Dependencia muerta — nunca se importa. Ahorrar build time.

---

## FASE 5 — Verificación de Optimizaciones de Alto Impacto

### A. WebP Conversion

| Estado | Detalle |
|--------|--------|
| **¿Se suben como PNG/JPG?** | ✅ Sí — se aceptan jpg/jpeg/png/webp pero no se convierten |
| **¿Pillow disponible?** | ✅ Sí — `pillow==11.2.1` en requirements |
| **¿Se usa para conversión?** | ❌ No — solo se usa en bulk router para compresión JPEG |
| **Reducción estimada** | JPEG→WebP: **30-50%** del tamaño / PNG→WebP: **60-80%** |
| **Recomendación** | Convertir a WebP q80 en `admin.py storage_upload()` — Pillow ya está instalada |

### B. Lazy Loading

| Estado | Detalle |
|--------|--------|
| **¿El catálogo carga todo eagerly?** | ✅ `collection.html` — **SÍ**, sin `loading="lazy"` |
| **¿Home?** | ⚠️ Hero eagerly (correcto) pero producto cards tienen lazy (OK) |
| **¿Product detail?** | ✅ Ya tiene `loading="lazy"` |
| **Reducción estimada** | ~30-40% menos de imagen egress por visita a colección |
| **Recomendación** | Agregar `loading="lazy"` a TODOS los img del grid en collection.html |

### C. Thumbnail System

| Estado | Detalle |
|--------|--------|
| **¿Solo existe 1 versión?** | ✅ Sí — la imagen original se usa en todos los contextos |
| **Grid muestra a** | ~256px de alto (h-64) |
| **Imagen original puede ser** | 2000-4000px |
| **Ratio desperdicio** | Se descarga ~10-20x más píxeles de los necesarios |
| **Reducción estimada** | Thumbnail 400px WebP: ~30-50KB vs original ~500KB-2MB = **90%+** |
| **Recomendación** | Generar `_thumb.webp` (400px) + `_full.webp` (1200px) al upload |

### D. Query Optimization

| Estado | Detalle |
|--------|--------|
| **¿Traen campos innecesarios?** | ✅ Sí — 7 queries usan `SELECT *` |
| **¿Hay N+1?** | ✅ Sí — 3 patrones en cart/checkout/wishlist |
| **¿Hay queries sin limit?** | ✅ Sí — analytics, admin, catálogo JS |
| **Reducción estimada** | N+1 fix: 5 queries → 1 / SELECT específico: ~30% menos bytes/query |

### E. URL Caching

| Estado | Detalle |
|--------|--------|
| **¿Se regeneran URLs cada request?** | ❌ No — las URLs están almacenadas en DB como strings completos |
| **`get_public_url()` se llama** | Solo 1 vez al upload (correcto) |
| **Problema** | No es URL regeneration — el problema es que NO hay cache headers en las respuestas HTTP |

---

## Resumen Ejecutivo — Potencial de Reducción

### Cached Egress (actual: 2.379 GB / 5 GB)

| Optimización | Reducción estimada | Esfuerzo |
|-------------|------------------:|----------|
| **P0-2** Lazy loading en collection | ~15-20% del total | 🟢 5 min |
| **P0-3** WebP + resize en upload | ~25-35% del total* | 🟡 30 min |
| **P0-1** Eliminar tracking duplicado | ~5-10% del total | 🟢 5 min |
| **P1-4** Mover marketing images a static | ~10-15% del total | 🟡 1 hora |
| **P1-3** Sistema de thumbnails | ~15-20% del total* | 🟡 2 horas |

> *\* Aplica a imágenes nuevas. Para reducir el egress de imágenes existentes se necesitaría un script de migración que descargue, convierta y re-suba.*

**Reducción total estimada (solo quick wins P0)**: **45-65%** del Cached Egress  
**Con P0 + P1**: **70-85%** de reducción  
**Egress proyectado post-optimización**: ~0.5-1.2 GB (vs 2.379 actual)

### Storage Size (actual: 0.463 GB / 1 GB)

| Optimización | Reducción estimada |
|-------------|------------------:|
| **P0-3** WebP + resize (nuevas imágenes) | ~50-70% de imágenes futuras |
| **Migración** de imágenes existentes | ~50-70% del storage actual (~0.23-0.32 GB recuperados) |
| **P1-4** Mover marketing images | ~20-50 MB recuperados |

**Storage proyectado post-optimización**: ~0.15-0.20 GB (vs 0.463 actual)

### Acción Inmediata Recomendada (Top 3 por ROI)

| Prioridad | Acción | Tiempo | Impacto |
|:-:|--------|-------:|---------|
| 🥇 | Eliminar tracking duplicado en product.html | 5 min | Reduce DB writes 50%, elimina API calls duplicadas |
| 🥈 | Agregar `loading="lazy"` en collection.html | 5 min | Reduce egress ~15-20% inmediatamente |
| 🥉 | WebP + resize en upload (admin.py) | 30 min | Reduce storage y egress ~50-70% para imágenes nuevas |

**¿Implemento estos 3 cambios?**
