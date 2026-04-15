-- Migration 003: Add UNIQUE constraint on products.nombre
-- PREREQUISITE: Run scripts/deduplicate_products.py FIRST to clean existing duplicates
-- Then execute this in Supabase SQL Editor

ALTER TABLE products
  ADD CONSTRAINT products_nombre_unique UNIQUE (nombre);
