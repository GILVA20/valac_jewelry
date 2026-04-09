-- ============================================================
-- Migración 001: imagen nullable + external_id + índice activo
-- Tabla: products
-- Ejecutar en: Supabase Dashboard → SQL Editor
-- 
-- NOTA: El campo 'activo' (boolean) YA EXISTE en la tabla.
--       Todos los 63 productos actuales tienen activo=True.
--       Esta migración solo agrega lo que falta.
-- ============================================================

-- 1. Hacer imagen nullable (para productos en borrador sin foto aún)
ALTER TABLE products
  ALTER COLUMN imagen DROP NOT NULL;

-- 2. Campo external_id para sync con Google Sheets / CSV
ALTER TABLE products
  ADD COLUMN IF NOT EXISTS external_id TEXT;

-- 3. Índices de soporte
CREATE INDEX IF NOT EXISTS idx_products_activo      ON products (activo);
CREATE INDEX IF NOT EXISTS idx_products_external_id ON products (external_id)
  WHERE external_id IS NOT NULL;
