-- 006: Tabla de configuración del sitio (key-value)
-- Usada para toggles de admin como auto-aprobación de reseñas.

CREATE TABLE IF NOT EXISTS site_settings (
  key   VARCHAR(100) PRIMARY KEY,
  value TEXT NOT NULL DEFAULT ''
);

-- Valor default: reseñas requieren aprobación manual
INSERT INTO site_settings (key, value)
VALUES ('reviews_auto_approve', 'false')
ON CONFLICT (key) DO NOTHING;
