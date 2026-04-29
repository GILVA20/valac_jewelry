-- 007: Configuración de banners y secciones promocionales (admin-controlled)
-- Usa la tabla existente site_settings (key-value)

-- === BANNER SUPERIOR (marquee) ===
INSERT INTO site_settings (key, value) VALUES
  ('promo_banner_active',     'true'),
  ('promo_banner_messages',   '["Hasta 6 MSI con Mercado Pago","🔥 Oro 10k y 14k","🚚 Envíos a todo México"]'),
  ('promo_banner_bg_color',   '#000000'),
  ('promo_banner_text_color', '#F59E0B')
ON CONFLICT (key) DO NOTHING;

-- === SECCIÓN PROMO HERO (home page, arriba de Compromiso) ===
INSERT INTO site_settings (key, value) VALUES
  ('promo_section_active',   'false'),
  ('promo_section_title',    ''),
  ('promo_section_subtitle', ''),
  ('promo_section_media_url',''),
  ('promo_section_link',     ''),
  ('promo_section_link_text','Ver más'),
  ('promo_section_bg_color', '#000000')
ON CONFLICT (key) DO NOTHING;
