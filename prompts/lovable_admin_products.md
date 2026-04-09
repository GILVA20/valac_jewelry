# Super Prompt — Lovable: Admin de Inventario VALAC Joyas

> **Contexto**: Este prompt genera una app React STANDALONE de administración
> de inventario para un ecommerce de joyería. Se conecta directo a Supabase.
> Diseñada para ser portátil — hoy administra productos de joyería, mañana
> puede administrar cualquier inventario.

---

## Arquitectura

```
                    ┌─────────────────────────┐
                    │   Supabase (PostgreSQL)  │
                    │   + Storage (imágenes)   │
                    └────────┬────────────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
     ┌────────┴───┐  ┌──────┴─────┐  ┌─────┴──────┐
     │ Flask Admin │  │  Lovable   │  │   Futuro   │
     │ (Jinja2)   │  │  React App │  │  (mobile?) │
     │ FALLBACK   │  │  PRINCIPAL │  │            │
     └────────────┘  └────────────┘  └────────────┘
```

- **Flask Admin** (templates Jinja2) = fallback que ya funciona en producción
- **Lovable React App** = nueva interfaz principal, standalone, abstracta
- Ambas apuntan a la misma BD Supabase, coexisten sin conflicto

---

## Prompt para Lovable (copiar completo)

```
Construye una aplicación STANDALONE de administración de inventario
para "VALAC Joyas", un ecommerce de joyería de lujo mexicana.

Esta app es 100% independiente — NO depende de ningún backend custom.
Se conecta directamente a Supabase (PostgreSQL + Storage).
Debe ser abstracta y portable: hoy administra joyería, pero la
arquitectura debe permitir adaptarla a cualquier inventario.

## ARQUITECTURA Y PRINCIPIOS

1. **Standalone**: app React+Vite completa con su propio index.html, router, y config
2. **Supabase-only**: todo el CRUD va directo a Supabase vía @supabase/supabase-js
3. **Sin backend propio**: no hay API server, no hay Express, no hay Next.js
4. **Abstracta**: los tipos, hooks y servicios están separados de los componentes UI
5. **Portable**: puede desplegarse en Vercel, Netlify, o como static files en cualquier servidor

## ESTRUCTURA DE CARPETAS (obligatoria)

```
src/
  types/
    product.ts           ← Tipos TypeScript del dominio (Product, ProductImage, etc.)
    filters.ts           ← Tipos para filtros y paginación
  services/
    supabase.ts          ← Cliente Supabase (singleton)
    products.ts          ← CRUD: list, get, create, update, delete, toggleActive
    product-images.ts    ← Galería: upload, reorder, delete, setPrimary
    csv-import.ts        ← Parseo + validación + batch insert
  hooks/
    useProducts.ts       ← React Query hook para listar con filtros/paginación
    useProduct.ts        ← Hook para un producto individual
    useProductMutations.ts ← Mutations: create, update, delete, toggle
    useImageUpload.ts    ← Hook para upload a Supabase Storage
    useCsvImport.ts      ← Hook para el flujo de importación
  components/
    layout/
      AppLayout.tsx      ← Sidebar + Header + Content area
      Sidebar.tsx        ← Navegación colapsable
    products/
      ProductsTable.tsx  ← DataTable con sorting, selección, paginación
      ProductRow.tsx     ← Fila individual con inline actions
      ProductFilters.tsx ← Barra de filtros (estado, tipo, material, género, precio, stock)
      BulkActions.tsx    ← Barra de acciones masivas (activar, desactivar, descuento, eliminar)
      StatusBadge.tsx    ← Badge activo/borrador clickeable
      StockBadge.tsx     ← Badge de stock con colores
      PricingDisplay.tsx ← Precio original + descuento + precio final
    product-form/
      ProductForm.tsx    ← Formulario completo (crear/editar)
      BasicInfo.tsx      ← Nombre + descripción
      PricingSection.tsx ← Precio + descuento + precio calculado
      CategorySection.tsx← Tipo, género, material
      InventorySection.tsx ← Stock
      StatusToggle.tsx   ← Switch activo/borrador
      ImageUploader.tsx  ← Drag & drop para imagen principal
      GalleryManager.tsx ← Grid de galería con DnD reorder
    csv-import/
      CsvImportDialog.tsx ← Modal/dialog completo del flujo
      CsvDropzone.tsx    ← Zona de drag & drop para archivo
      CsvPreview.tsx     ← Preview de filas con validación visual
      CsvColumnMapper.tsx← Mapeo de columnas
      CsvSummary.tsx     ← Resumen pre-import
      CsvProgress.tsx    ← Barra de progreso de inserción
    shared/
      EmptyState.tsx     ← Estado vacío reutilizable
      ConfirmDialog.tsx  ← Confirm de eliminación
      SearchInput.tsx    ← Búsqueda con debounce
  pages/
    ProductsPage.tsx     ← Lista de productos (ruta principal)
    ProductFormPage.tsx  ← Crear/Editar producto
  lib/
    utils.ts             ← cn() y helpers
    constants.ts         ← Enums: PRODUCT_TYPES, GENDERS, MATERIALS, etc.
    validators.ts        ← Reglas de validación compartidas (CSV + form)
```

## CREDENCIALES SUPABASE

Usa variables de entorno:
  VITE_SUPABASE_URL = (se configurará después)
  VITE_SUPABASE_ANON_KEY = (se configurará después)

## SCHEMA DE LA TABLA `products`

```sql
CREATE TABLE products (
  id            SERIAL PRIMARY KEY,
  nombre        TEXT NOT NULL,
  descripcion   TEXT DEFAULT 'Sin descripción',
  precio        NUMERIC NOT NULL,
  descuento_pct INTEGER DEFAULT 0,
  precio_descuento NUMERIC DEFAULT 0,
  tipo_producto TEXT NOT NULL,   -- Anillos, Cadenas, Aretes, Pulseras, Dijes, Collares
  genero        TEXT NOT NULL,   -- Mujer, Hombre, Unisex
  tipo_oro      TEXT NOT NULL,   -- 10k, 14k, Plata .925
  imagen        TEXT,            -- URL de imagen principal (puede ser NULL para borradores)
  stock_total   INTEGER DEFAULT 0,
  activo        BOOLEAN DEFAULT true,  -- true=visible en tienda, false=borrador
  destacado     BOOLEAN DEFAULT false, -- productos featured en homepage
  external_id   TEXT,            -- ID externo para sync con Google Sheets
  created_at    TIMESTAMPTZ DEFAULT now(),
  updated_at    TIMESTAMPTZ DEFAULT now(),
  created_by    TEXT,
  updated_by    TEXT
);
```

## TABLA `product_images` (galería)

```sql
CREATE TABLE product_images (
  id          SERIAL PRIMARY KEY,
  product_id  INTEGER REFERENCES products(id) ON DELETE CASCADE,
  imagen      TEXT NOT NULL,  -- URL
  orden       INTEGER DEFAULT 0
);
```

## LO QUE NECESITO — DASHBOARD DE PRODUCTOS

### Vista principal: Lista de productos (ruta `/`)

Diseño tipo Shopify/modern admin con sidebar izquierda y contenido principal.

**Sidebar** (colapsable en móvil):
- Logo "VALAC Joyas" arriba
- Navegación con iconos:
  - 📦 Productos (activa) → `/`
  - 📋 Pedidos → placeholder (link muerto con tooltip "Próximamente")
  - 🏷️ Cupones → placeholder
  - 📊 Analytics → placeholder
  - 📁 Colecciones → placeholder
  - 📸 Studio → link externo placeholder (para conectar después)
- Footer del sidebar: "v1.0 · VALAC Inventory"

**Header del contenido**:
- Título: "Productos" con counter "(63 productos)"
- Botón primario: "+ Agregar producto"
- Botón secundario: "Importar CSV"
- Search bar con lupa, filtros desplegables inline

**Barra de filtros** (horizontal, chips/pills estilo):
- Estado: "Todos", "Activos", "Borradores" (basado en campo `activo`)
- Tipo: dropdown con Anillos, Cadenas, Aretes, Pulseras, Dijes, Collares
- Material: dropdown con 10k, 14k, Plata .925
- Género: pills Mujer | Hombre | Unisex
- Precio: rango slider min/max
- Stock: "Sin stock", "Stock bajo (<5)", "Con stock"
- Botón "Limpiar filtros"

**Tabla** de productos (DataTable-style):
- Columnas: Checkbox | Imagen | Nombre + Descripción | Estado | Precio | Stock | Tipo | Material | Acciones
- La columna IMAGEN muestra thumbnail 48x48 redondeado con hover para preview grande
- La columna NOMBRE muestra nombre en bold + primera línea de descripción en gris debajo
- La columna ESTADO muestra badge: verde "Activo" / amarillo "Borrador" — clickeable para toggle
- La columna PRECIO muestra precio original, y si hay descuento, muestra el % tachado y precio final
- La columna STOCK muestra número con color: rojo si 0, naranja si <5, verde si ≥5
- ACCIONES: iconos de Editar (lápiz), Duplicar, Eliminar (trash con confirm)
- Rows seleccionables con checkbox para acciones masivas
- Sorting por click en header (nombre, precio, stock, fecha)
- Paginación real: 25 productos por página con "Anterior | 1 2 3 ... | Siguiente"

**Barra de acciones masivas** (aparece si hay selección):
- "X productos seleccionados"
- Botones: "Activar", "Desactivar", "Aplicar descuento %", "Eliminar"
- El botón "Aplicar descuento" abre un mini-modal con input numérico (0-100%)

**Empty states**:
- Si no hay productos: ilustración + "No hay productos todavía" + botón CTA
- Si los filtros no tienen resultados: "No se encontraron productos con estos filtros" + link "Limpiar"

### Vista: Crear/Editar producto (ruta `/products/new` y `/products/:id`)

**Layout dos columnas** (70/30):

**Columna izquierda (70%)**:
- **Información básica**: nombre (input text, obligatorio), descripción (textarea con counter de caracteres)
- **Precio y descuento**: precio (input numeric, formato MXN con $), descuento % (slider 0-100), precio final calculado automáticamente y mostrado en tiempo real
- **Organización**: tipo_producto (select), género (radio pills), tipo_oro/material (select)
- **Inventario**: stock_total (input numeric, con badge de estado visual)

**Columna derecha (30%)**:
- **Estado**: Toggle switch grande "Activo" / "Borrador" con texto descriptivo debajo ("Los productos activos son visibles en la tienda")
- **Imagen principal**: Zona de drag & drop para subir imagen. Preview grande. Si ya tiene imagen, muestra la actual con botón "Cambiar". Aceptar JPG/PNG/WEBP
- **Galería**: Grid de thumbnails arrastrables (drag to reorder). Botón "+ Agregar imagen". Cada imagen tiene botón X para eliminar y botón ★ para marcar como principal
- **Destacado**: Checkbox "Mostrar en homepage"
- **Info**: Fecha de creación, última actualización (solo lectura)

**Footer sticky**: Botón "Guardar" (primario) y "Cancelar" (secundario). Si hay cambios sin guardar, mostrar dot indicator en el botón

### Vista: Importar CSV (modal o ruta `/products/import`)

- Zona de drag & drop para CSV
- Preview de las primeras 5 filas en tabla
- Mapeo de columnas: mostrar columnas del CSV → columnas de la tabla. Auto-detectar si coinciden nombres
- Columnas esperadas: nombre, descripcion, precio, tipo_producto, genero, tipo_oro, imagen, stock_inicial
- Validación en tiempo real: resaltar filas con errores en rojo, warnings en amarillo
- Reglas de validación visibles:
  - tipo_oro solo acepta: 10k, 14k, Plata .925 (sin esto → ❌ skip)
  - genero: Mujer, Hombre, Unisex (auto-capitalize)
  - precio mínimo: $100 MXN
  - stock negativo → ajustar a 0
- Resumen antes de confirmar: "X productos válidos, Y con errores, Z con advertencias"
- Botón "Importar X productos como borradores"
- Barra de progreso durante la inserción
- Al finalizar: resumen con links a los productos creados

## DISEÑO Y ESTILIZACIÓN

### Paleta de colores (marca VALAC Joyas):
- Primary: `#A67C00` (dorado joyería / Cartier gold)
- Primary hover: `#8B6800`
- Background: `#FAFAFA`
- Surface: `#FFFFFF`
- Text primary: `#1A1A1A`
- Text secondary: `#6B7280`
- Success: `#10B981`
- Warning: `#F59E0B`
- Error: `#EF4444`
- Border: `#E5E7EB`

### Tipografía:
- Headings: Inter o system font, semibold
- Body: Inter, regular
- Monospace para precios: tabular-nums

### Componentes UI:
- Usa shadcn/ui para todos los componentes (Button, Input, Select, Dialog, etc.)
- Toasts para feedback (success/error) con sonner
- Skeletons para loading states
- Diseño responsive: sidebar colapsable en móvil, tabla → cards en pantallas chicas

### Interacciones:
- Botones con hover states y transiciones suaves (150ms)
- Modales con backdrop blur
- Dropdowns con animación de scale
- Drag & drop para galería con visual feedback
- Inline editing: doble-click en celda de nombre/precio/stock para editar directo en la tabla

## STACK TÉCNICO

- React 18+ con TypeScript estricto
- Vite como bundler
- Tailwind CSS + shadcn/ui (instalar fresh, no importar de otro proyecto)
- @supabase/supabase-js para todo el backend
- @tanstack/react-query para server state (cache, invalidation, optimistic updates)
- React Router v6 con BrowserRouter (standalone, no hash)
- React Hook Form + Zod para validación de formularios
- @dnd-kit/core + @dnd-kit/sortable para drag & drop de galería
- Sonner para toasts
- Lucide React para iconos
- date-fns para formateo de fechas
- papaparse para parseo de CSV

## RUTAS

```
/                    → ProductsPage (lista principal)
/products/new        → ProductFormPage (crear)
/products/:id        → ProductFormPage (editar)
/products/import     → CsvImportDialog (puede ser modal desde /)
```

## FUNCIONALIDAD SUPABASE

Todas las operaciones CRUD van directo a Supabase:

```typescript
// Listar productos con filtros y paginación
const { data, count } = await supabase
  .from('products')
  .select('*, product_images(id, imagen, orden)', { count: 'exact' })
  .eq('activo', filterActivo)  // si hay filtro
  .ilike('nombre', `%${search}%`)
  .order(sortColumn, { ascending: sortAsc })
  .range(offset, offset + limit - 1)

// Toggle activo
await supabase.from('products').update({ activo: !current }).eq('id', id)

// Crear producto
await supabase.from('products').insert({ ...formData, activo: false })

// Actualizar producto
await supabase.from('products').update(formData).eq('id', id)

// Eliminar producto (cascade borra product_images automáticamente)
await supabase.from('products').delete().eq('id', id)

// Galería: reordenar
for (const img of newOrder) {
  await supabase.from('product_images').update({ orden: img.orden }).eq('id', img.id)
}

// Upload imagen a Storage
const { data } = await supabase.storage
  .from('CatalogoJoyasValacJoyas')
  .upload(`products/${timestamp}-${uuid}.webp`, file)
```

## DESCUENTO: lógica de precio

Cuando se cambia `descuento_pct`, calcular y guardar `precio_descuento`:
```
precio_descuento = precio * (1 - descuento_pct / 100)
```
Mostrar ambos precios en la tabla: original tachado + final en bold

## NO INCLUIR

- Autenticación / login (se añadirá después; por ahora acceso directo)
- Páginas de tienda pública (solo el admin de inventario)
- Funcionalidad real de pedidos/cupones/analytics (solo placeholders en sidebar)
- Backend/API propio — todo va directo a Supabase
- Integración con frameworks server-side (no Next.js, no Remix, no Flask)

## PREPARADA PARA ESCALAR

La app debe estar estructurada para que en el futuro se pueda:
- Agregar módulo de Pedidos (nueva carpeta `components/orders/`, nuevo service, nueva page)
- Agregar módulo de Colecciones (agrupar productos)
- Agregar módulo de Variantes (tallas de anillos)
- Agregar autenticación con Supabase Auth
- Desplegar como app independiente en Vercel/Netlify
- O embeber como iframe/static en otro sistema

## ENTREGABLE

Una app React STANDALONE completa y funcional que:
1. **Arranca sola** con `npm run dev` — no depende de nada externo excepto Supabase
2. Se conecta a Supabase con env vars configurables
3. CRUD completo de productos con filtros, búsqueda, paginación, sorting
4. Galería de imágenes con drag & drop reorder y upload a Supabase Storage
5. Importación CSV con validación visual y batch insert como borradores
6. Acciones masivas: activar, desactivar, aplicar descuento, eliminar
7. Inline editing en la tabla (doble-click para editar nombre/precio/stock)
8. Responsive: sidebar colapsable, tabla → cards en móvil
9. Loading states (skeletons), empty states, toasts de feedback
10. Paleta dorada consistente de VALAC Joyas
11. **Cero acoplamiento** con Flask, Express, o cualquier backend — solo Supabase
```

---

## Instrucciones post-descarga

### Opción A: Desarrollo local standalone (recomendada para iterar)

```bash
# 1. Extraer el tar.gz de Lovable
tar xzf lovable-output.tar.gz -C valac-inventory/

# 2. Entrar y configurar env vars
cd valac-inventory
cp .env.example .env
# Editar .env con tus credenciales de Supabase:
#   VITE_SUPABASE_URL=https://xxx.supabase.co
#   VITE_SUPABASE_ANON_KEY=eyJ...

# 3. Instalar y correr
npm install
npm run dev
# → http://localhost:5173 — app standalone completa
```

### Opción B: Servir como static files desde Flask (producción)

```bash
# 1. Build de producción
cd valac-inventory
npm run build  # genera dist/

# 2. Copiar a static de Flask
cp -r dist/* ../static/inventory/

# 3. Crear blueprint en Flask (o reusar patrón existente)
# Acceso: https://www.valacjoyas.com/admin/inventory/
```

### Coexistencia con el admin actual (fallback)

```
Flask Admin (Jinja2)          Lovable React App
─────────────────             ────────────────
/admin/supabase_products/  ←  /admin/inventory/  (o standalone :5173)
/admin/supabase_products/new  /products/new
/admin/supabase_products/edit /products/:id

Ambos apuntan a las MISMAS tablas de Supabase.
El admin Flask sigue funcionando sin cambios.
Se puede migrar gradualmente: cuando el React esté estable,
el Flask admin se vuelve solo respaldo de emergencia.
```

### VALAC Studio (valacstudio/) — proyecto SEPARADO

`valacstudio/` es el pipeline de fotografía AI (VALAC Studio).
Es un proyecto React completamente independiente del admin de inventario.
NO mezclar, NO mergear. Son dos apps distintas:

| Proyecto | Ubicación | Puerto | Propósito |
|----------|-----------|--------|-----------|
| VALAC Studio | `valacstudio/` | :5173 | Fotografía AI de productos |
| VALAC Inventory | `valac-inventory/` | :5174 | Administración de inventario |
| Flask Admin | `valac_jewelry/` | :5000 | Fallback admin (Jinja2) |

### Verificación

1. `npm run dev` en `valac-inventory/` → app completa de inventario
2. Los mismos 63 productos que ves en Flask Admin aparecen aquí
3. Crear/editar/eliminar producto → se refleja en ambas interfaces
4. Importar CSV → productos creados como borradores (activo=false)
5. Toggle activo → producto aparece/desaparece de la tienda pública
