# Auditoría Completa — Display de Productos VALAC Joyas

> **Fecha**: 6 de marzo de 2026  
> **Scope**: Lógica de sorting, filtering, grid layout, colecciones, stock handling, UX mobile  
> **Stack**: Flask (blueprints), Supabase (PostgreSQL + Storage), TailwindCSS, JS client-side

---

## A. Estado Actual

### Arquitectura de Datos

- **No existe tabla `collections`** — las "colecciones" se arman dinámicamente combinando `genero` + `tipo_producto` como query params en la URL (`/collection?genero=Mujer&category=anillos`).
- La tabla `products` usa `tipo_producto` (Anillos, Aretes, Cadenas, Pulsos, Dijes) como categoría.
- El campo `stock_total` es un entero que controla disponibilidad.
- **No existen los campos**: `sort_order`, `display_order`, `is_featured`, `is_active`.
- Los campos `ventas`, `destacado` y `valoracion` están referenciados en `collection.py` (L149–L155) para sorting, pero **probablemente no existen en la BD o son siempre null**, haciendo esas opciones de ordenamiento inoperantes.

### Schema Inferido de la Tabla `products`

| Columna | Tipo | Notas |
|---------|------|-------|
| `id` | UUID (string) | PK |
| `nombre` | text | Nombre del producto |
| `descripcion` | text | Descripción |
| `precio` | float | Precio original |
| `descuento_pct` | int | Porcentaje de descuento (0–100) |
| `precio_descuento` | float | Calculado: `precio * (1 - descuento_pct/100)` |
| `tipo_producto` | text | Categoría: Anillos, Aretes, Cadenas, Pulsos, Dijes, Collares |
| `genero` | text | Hombre, Mujer, Unisex |
| `tipo_oro` | text | 10k, 14k |
| `imagen` | text (URL) | Imagen principal |
| `stock_total` | int | Inventario |
| `created_at` | timestamp | Auto-generado |
| `peso` | float? | Se muestra en `product.html` si existe |
| `ventas` | int? | Referenciado en sort pero nunca poblado |
| `destacado` | bool? | Referenciado en sort pero nunca poblado |
| `valoracion` | float? | Referenciado en sort pero nunca poblado |

### Schema de `product_images`

| Columna | Tipo | Notas |
|---------|------|-------|
| `id` | UUID | PK |
| `product_id` | UUID (FK) | Relación a `products` |
| `imagen` | text (URL) | URL de imagen |
| `orden` | int | Orden de display |

### Patrón de Queries Dual (Redundante)

| Componente | Query Server-side | Query Client-side (JS) | ¿Cuál renderiza? |
|---|---|---|---|
| **Home** | `main.py` L11: `.select("*").gt("stock_total",0).limit(3)` | `home.html` L248: JS `supabaseClient.from('products').select(...)` con 12+ columnas | **JS client-side** |
| **Collection** | `collection.py` L76–L113: query con filtros + paginación (36/page) | `collection.html` L351–L390: JS replica la query completa | **JS client-side** |
| **Product detail** | `products.py` L11–L34: `.single()` + images + related | Jinja server-rendered | **Server-side** |

> **Hallazgo crítico**: En `home.html` y `collection.html`, el servidor construye una query Python que **NO se usa para renderizar**. El JS del template vuelve a consultar Supabase directamente. Esto duplica las llamadas a la BD y expone la API key de Supabase en el frontend.

---

### Sorting Actual — `collection.html` L408–L432

```js
// Separar en stock vs agotados
const inStock    = filteredProducts.filter(p => Number(p.stock_total) > 0);
const outOfStock = filteredProducts.filter(p => Number(p.stock_total) <= 0);

const sortFn = (arr) => {
  switch (sort) {
    case 'precio_asc':  return arr.sort((a, b) => effectivePrice(a) - effectivePrice(b));
    case 'precio_desc': return arr.sort((a, b) => effectivePrice(b) - effectivePrice(a));
    case 'novedades':   return arr.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    default: { /* ofertas primero, luego normales por precio asc */ }
  }
};
const ordered = [...sortFn(inStock), ...sortFn(outOfStock)];
```

- ✅ Productos en stock primero, agotados al final.
- ✅ Agotados con opacidad 55% + escala de grises + CTA deshabilitado.
- ❌ Opciones `nombre_asc` y `nombre_desc` del dropdown **no están implementadas** en el switch.

---

### Grid Layout — `collection.html` L35–L53

| Breakpoint | Columnas |
|---|---|
| `< 640px` (mobile) | 2 columnas |
| `640px+` (sm) | 2 columnas |
| `768px+` (md) | 3 columnas |
| `1024px+` (lg) | 4 columnas |

- Las imágenes usan `h-64` fijo (256px) — **sin `aspect-ratio` definido**, lo que puede causar distorsión y CLS.
- El precio **sí es visible** sin interacción en mobile.

---

### Home Products — `home.html` L258–L259

```js
const ofertas   = products.filter(p => hasOffer(p) && Number(p.stock_total) > 0).sort(...)
const novedades = products.filter(p => !hasOffer(p) && Number(p.stock_total) > 0).sort(...)
```

- ✅ Filtra `stock > 0`.
- Si hay ofertas activas muestra "Ofertas"; si no, "Novedades". Máximo 6 productos.

---

### Productos Relacionados — `products.py` L27–L33

```python
related_resp = supabase.table('products')
    .select('*, product_images(imagen,orden)')
    .eq('tipo_producto', product['tipo_producto'])
    .neq('id', product_id)
    .limit(4)
    .execute()
```

- ❌ **No filtra por stock** — puede mostrar productos agotados como recomendaciones.
- ❌ **No tiene orden** — devuelve los primeros 4 de la BD (orden indefinido).

---

### Navegación y "Colecciones"

La navegación del header (`partials/header.html`) ofrece un mega-menú con estructura:

```
Colección
├── Hombre
│   ├── Aretes → /collection?genero=Hombre&category=aretes&mix_unisex=1
│   ├── Cadenas
│   ├── Anillos
│   ├── Dijes
│   └── Pulsos
├── Mujer
│   ├── Aretes → /collection?genero=Mujer&category=aretes&mix_unisex=1
│   └── ...
├── Ofertas activas → /collection?category=ofertas
└── Explorar toda la colección → /collection
```

- Todo basado en query params — no hay entidades de colección persistentes.
- El link "Ofertas activas" usa `category=ofertas` pero no existe esa categoría en `tipo_producto`, así que probablemente no filtra nada o filtra vacío.

---

## B. Gaps Críticos (P0)

### 1. Opciones de sort del dropdown no implementadas en JS

- **Impacto**: Alto — El dropdown ofrece `nombre_asc` y `nombre_desc` pero el JS `sortFn` no tiene esos cases. Caen al `default` que ordena ofertas→normales. El usuario selecciona "Nombre: A-Z" y **ve otra cosa**.
- **Archivos**: `collection.html` L279–L280 (dropdown) vs L413–L428 (sortFn)
- **Riesgo**: Percepción de producto roto, pérdida de confianza.

### 2. Productos relacionados sin filtro de stock

- **Impacto**: Alto — Un usuario en el detalle de un producto disponible puede ver 4 recomendaciones agotadas, con botón activo. Clic → producto agotado → decepción → abandono.
- **Archivo**: `products.py` L27–L33
- **Riesgo**: Frustración directa en el funnel de conversión.

### 3. Query dual: Server + Client-side Supabase

- **Impacto**: Alto — 
  - Doble latencia (server query + client query).
  - La API key de Supabase **se expone en el JS del frontend** vía `supabase-client.js`.
  - La lógica server-side de `collection.py` (filtros, paginación de 36 items) se ignora completamente — el JS trae **TODOS los productos** sin `.limit()`.
- **Archivos**: `collection.py` vs `collection.html` L351–L390
- **Riesgo**: Seguridad + performance degradado con catálogo creciente.

### 4. Sin paginación real en el frontend

- **Impacto**: Medio-Alto — El JS trae todos los productos matching de la BD de golpe. Con 500+ productos será lento, pesado en memoria y costará RPCs de Supabase.
- **Archivo**: `collection.html` L351–L390 — no hay `.range()` ni `.limit()` en la query JS.
- **Riesgo**: Degradación progresiva conforme crece el catálogo.

### 5. Imágenes del grid sin `aspect-ratio` — CLS en mobile

- **Impacto**: Medio — En mobile, las imágenes con `h-64` fijo sin `aspect-ratio` causan Cumulative Layout Shift (CLS) alto. Afecta Core Web Vitals y UX percibido.
- **Archivo**: `collection.html` L445 — `<div class="relative w-full h-64 overflow-hidden">`
- **Riesgo**: SEO penalizado + mala experiencia visual en scroll.

---

## C. Recomendaciones de Implementación

### C1. Completar los cases de sorting en JS

**Complejidad**: 🟢 Bajo (10 min)

Agregar `nombre_asc` y `nombre_desc` al `sortFn` en `collection.html` L413–L428:

```js
case 'nombre_asc':
  return arr.sort((a, b) => (a.nombre || '').localeCompare(b.nombre || '', 'es'));
case 'nombre_desc':
  return arr.sort((a, b) => (b.nombre || '').localeCompare(a.nombre || '', 'es'));
```

---

### C2. Filtrar stock en productos relacionados

**Complejidad**: 🟢 Bajo (10 min)

En `products.py` L27–L33:

```python
related_resp = supabase.table('products')\
    .select('*, product_images(imagen,orden)')\
    .eq('tipo_producto', product['tipo_producto'])\
    .neq('id', product_id)\
    .gt('stock_total', 0)\           # ← NUEVO: solo productos con stock
    .order('created_at', desc=True)\  # ← NUEVO: novedades primero
    .limit(4)\
    .execute()
```

---

### C3. Agregar `aspect-ratio` al contenedor de imágenes del grid

**Complejidad**: 🟢 Bajo (15 min)

En `collection.html` render JS, cambiar:

```html
<!-- Antes -->
<div class="relative w-full h-64 overflow-hidden">

<!-- Después -->
<div class="relative w-full overflow-hidden" style="aspect-ratio:4/5;">
```

Mismo cambio en `home.html` L281.

---

### C4. Eliminar query dual — consolidar en server-side

**Complejidad**: 🔴 Alto (4–6 horas)

1. Mover TODA la lógica de filtrado y sorting a `collection.py`
2. Incluir `stock_total` en el `select` server-side
3. Aplicar la estrategia in-stock-first en Python
4. Pasar productos como JSON en el template context: `{{ products|tojson }}`
5. Eliminar la query JS a Supabase
6. Implementar paginación real con offset/limit
7. Eliminar la exposición de la API key en el frontend (o usar Row Level Security)

---

### C5. Agregar campos de catálogo a la tabla `products`

**Complejidad**: 🟡 Medio (1–2 horas)

```sql
ALTER TABLE products
  ADD COLUMN IF NOT EXISTS sort_order    INTEGER DEFAULT 0,
  ADD COLUMN IF NOT EXISTS is_featured   BOOLEAN DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS is_active     BOOLEAN DEFAULT TRUE;

CREATE INDEX IF NOT EXISTS idx_products_catalog
  ON products (is_active, stock_total DESC, sort_order, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_products_category
  ON products (tipo_producto, genero, is_active);
```

Luego actualizar:
- `collection.py` para filtrar `is_active = TRUE`
- Admin para poder marcar `is_featured` e `is_active`
- Sorting para usar `sort_order` como prioridad manual

---

### C6. Corregir link "Ofertas activas" en navegación

**Complejidad**: 🟢 Bajo (10 min)

El link `href="/collection?category=ofertas"` en `partials/header.html` usa `category=ofertas` que no existe como `tipo_producto`. Cambiar la lógica para que filtre por `descuento_pct > 0` o crear un parámetro especial `offers_only=1`.

---

## D. Quick Wins (< 2 horas, mayor ROI)

| # | Cambio | Impacto | Tiempo Est. |
|---|---|---|---|
| **1** | Completar cases `nombre_asc` / `nombre_desc` en `sortFn` del JS | Sorting roto → funcional | 10 min |
| **2** | Agregar `.gt('stock_total', 0).order('created_at', desc=True)` a productos relacionados | Evitar recomendar agotados | 10 min |
| **3** | Agregar `aspect-ratio:4/5` a contenedores de imagen del grid (collection + home) | Eliminar CLS en mobile | 15 min |

**ROI combinado**: Corrigen las 3 fricciones más visibles para el usuario con ~35 minutos de trabajo.

---

## E. Propuesta de Schema Optimizado

### Tabla: `collections` (nueva)

```sql
-- ============================================================
-- Permite agrupar productos en colecciones curateadas
-- con soporte para lanzamientos programados y banners
-- ============================================================
CREATE TABLE IF NOT EXISTS collections (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  nombre        TEXT NOT NULL,
  slug          TEXT UNIQUE NOT NULL,           -- URL-friendly: "anillos-mujer-14k"
  descripcion   TEXT,
  imagen_banner TEXT,                           -- URL de imagen hero
  is_active     BOOLEAN DEFAULT TRUE,
  sort_order    INTEGER DEFAULT 0,              -- Orden manual en nav
  publish_at    TIMESTAMPTZ,                    -- Lanzamiento programado
  created_at    TIMESTAMPTZ DEFAULT NOW(),
  updated_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_collections_active
  ON collections (is_active, sort_order);
```

### Tabla: `products` (campos nuevos)

```sql
ALTER TABLE products
  ADD COLUMN IF NOT EXISTS sort_order     INTEGER DEFAULT 0,
  ADD COLUMN IF NOT EXISTS is_featured    BOOLEAN DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS is_active      BOOLEAN DEFAULT TRUE,
  ADD COLUMN IF NOT EXISTS collection_id  UUID REFERENCES collections(id) ON DELETE SET NULL;
```

### Índices optimizados

```sql
-- Catálogo general (query principal)
CREATE INDEX IF NOT EXISTS idx_products_catalog
  ON products (is_active, is_featured DESC, sort_order, created_at DESC)
  WHERE is_active = TRUE;

-- Productos con stock (filtro más común)
CREATE INDEX IF NOT EXISTS idx_products_stock
  ON products (stock_total DESC)
  WHERE is_active = TRUE AND stock_total > 0;

-- Filtros por categoría y género
CREATE INDEX IF NOT EXISTS idx_products_category_gender
  ON products (tipo_producto, genero)
  WHERE is_active = TRUE;

-- Productos por colección
CREATE INDEX IF NOT EXISTS idx_products_collection
  ON products (collection_id)
  WHERE collection_id IS NOT NULL;

-- Precio efectivo para sorting
CREATE INDEX IF NOT EXISTS idx_products_price_effective
  ON products (
    COALESCE(precio_descuento, precio)
  ) WHERE is_active = TRUE AND stock_total > 0;
```

### Vista de catálogo (opcional pero recomendada)

```sql
CREATE OR REPLACE VIEW v_catalog AS
SELECT
  p.id,
  p.nombre,
  p.descripcion,
  p.precio,
  p.descuento_pct,
  p.precio_descuento,
  COALESCE(p.precio_descuento, p.precio) AS precio_efectivo,
  p.tipo_producto,
  p.genero,
  p.tipo_oro,
  p.imagen,
  p.stock_total,
  p.is_featured,
  p.sort_order,
  p.created_at,
  p.collection_id,
  c.nombre   AS collection_nombre,
  c.slug     AS collection_slug,
  CASE
    WHEN p.stock_total <= 0 THEN 'agotado'
    WHEN p.stock_total <= 3 THEN 'bajo_stock'
    ELSE 'disponible'
  END AS stock_status
FROM products p
LEFT JOIN collections c ON p.collection_id = c.id
WHERE p.is_active = TRUE
ORDER BY
  (p.stock_total > 0) DESC,   -- En stock primero
  p.is_featured DESC,          -- Destacados después
  p.sort_order ASC,            -- Orden manual
  p.created_at DESC;           -- Más nuevos al final
```

---

## Resumen Ejecutivo

La tienda funciona pero tiene **deuda técnica significativa** en la capa de display:

| Área | Estado | Prioridad |
|------|--------|-----------|
| Sort por nombre (A-Z / Z-A) | ❌ Roto — no implementado en JS | P0 |
| Productos relacionados con stock | ❌ Puede recomendar agotados | P0 |
| Query dual (server + client) | ⚠️ Redundante + API key expuesta | P1 |
| Paginación real | ❌ No existe — trae todo de golpe | P1 |
| Aspect-ratio en grid images | ❌ CLS alto en mobile | P1 |
| Tabla de colecciones | ❌ No existe | P2 |
| Campos `is_active`, `is_featured`, `sort_order` | ❌ No existen | P2 |
| Link "Ofertas activas" en nav | ⚠️ Apunta a categoría inexistente | P2 |

**Acciones inmediatas** (3 quick wins, ~35 min): Corregirían las fricciones más visibles para el usuario final.
