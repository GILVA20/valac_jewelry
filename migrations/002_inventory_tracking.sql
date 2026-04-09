-- Migración 002: Tracking de inventario (costos, pesos, estado físico)
-- Ejecutar en Supabase Dashboard → SQL Editor

ALTER TABLE products
  ADD COLUMN IF NOT EXISTS peso_gramos      NUMERIC,
  ADD COLUMN IF NOT EXISTS precio_por_gramo NUMERIC,
  ADD COLUMN IF NOT EXISTS precio_costo     NUMERIC,
  ADD COLUMN IF NOT EXISTS estado_inventario TEXT NOT NULL DEFAULT 'disponible',
  ADD COLUMN IF NOT EXISTS devolucion_a     TEXT;

-- Índice para filtrar por estado en admin
CREATE INDEX IF NOT EXISTS idx_products_estado_inventario
  ON products(estado_inventario);

-- Verificar:
-- SELECT id, nombre, peso_gramos, precio_costo, estado_inventario FROM products LIMIT 5;
