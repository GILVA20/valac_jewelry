-- =============================================================
-- 005_reviews_table.sql
-- Sistema de reseñas con media (fotos/videos de clientes)
-- Ejecutar en Supabase SQL Editor
-- Seguro para producción: renombra tabla vieja, no borra datos
-- =============================================================

-- Renombrar tabla vieja (schema diferente) para no perder datos
ALTER TABLE IF EXISTS reviews RENAME TO reviews_legacy;

-- Tabla principal de reseñas (schema nuevo)
CREATE TABLE reviews (
  id            BIGSERIAL PRIMARY KEY,
  created_at    TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  nombre        VARCHAR(100)  NOT NULL,
  email         VARCHAR(255)  NOT NULL,
  numero_pedido VARCHAR(50)   NOT NULL,
  producto      VARCHAR(200)  NOT NULL,
  product_id    INTEGER       REFERENCES products(id) ON DELETE SET NULL,
  estrellas     INTEGER       NOT NULL CHECK (estrellas BETWEEN 1 AND 5),
  texto         TEXT          NOT NULL CHECK (char_length(texto) >= 50),
  media_urls    TEXT[]        DEFAULT '{}',
  verificado    BOOLEAN       DEFAULT FALSE,
  util_count    INTEGER       DEFAULT 0,
  ip_address    INET,
  admin_notes   TEXT
);

-- Índices para performance
CREATE INDEX idx_reviews_verificado
  ON reviews(verificado);
CREATE INDEX idx_reviews_product_id
  ON reviews(product_id);
CREATE INDEX idx_reviews_estrellas
  ON reviews(estrellas);
CREATE INDEX idx_reviews_created_at
  ON reviews(created_at DESC);

-- RLS deshabilitado — el backend Flask controla acceso vía rutas protegidas
-- (consistente con products, orders, coupons que tampoco usan RLS)

-- Verificación:
-- SELECT * FROM reviews LIMIT 1;
-- SELECT indexname FROM pg_indexes WHERE tablename = 'reviews';
