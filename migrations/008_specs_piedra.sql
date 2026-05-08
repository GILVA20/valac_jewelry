-- 008: Add JSONB column for engagement ring stone specifications
-- Used when tipo_producto = 'Anillos de Compromiso'
-- Example: {"tipo_piedra":"Diamante","forma":"Redondo","quilates":0.5,"color":"G","claridad":"VS1","corte":"Excellent","certificado":"GIA","tipo_engaste":"Solitario"}

ALTER TABLE products
  ADD COLUMN IF NOT EXISTS specs_piedra JSONB DEFAULT NULL;

COMMENT ON COLUMN products.specs_piedra IS 'Stone/setting specs for engagement rings (JSONB). NULL for other product types.';
