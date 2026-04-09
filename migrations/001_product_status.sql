-- ============================================================
-- Migración 001: Campo estado + imagen nullable + external_id
-- Tabla: products
-- Ejecutar en: Supabase Dashboard → SQL Editor
-- ============================================================

-- 1. Campo estado (activo | borrador | archivado)
ALTER TABLE products
  ADD COLUMN IF NOT EXISTS estado TEXT NOT NULL DEFAULT 'activo'
  CONSTRAINT products_estado_check CHECK (estado IN ('activo', 'borrador', 'archivado'));

-- 2. Hacer imagen nullable (para productos sin imagen aún)
ALTER TABLE products
  ALTER COLUMN imagen DROP NOT NULL;

-- 3. Campo external_id para referencias externas (importaciones CSV, ERPs, etc.)
ALTER TABLE products
  ADD COLUMN IF NOT EXISTS external_id TEXT;

-- Índices de soporte
CREATE INDEX IF NOT EXISTS idx_products_estado       ON products (estado);
CREATE INDEX IF NOT EXISTS idx_products_external_id  ON products (external_id);

-- Backfill: todos los existentes quedan activos (ya tiene default, pero por seguridad)
UPDATE products SET estado = 'activo' WHERE estado IS NULL;
