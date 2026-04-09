---
description: "Build o fix directo en VALAC Joyas sin plan previo. Use when: bug fix, cambio pequeño, agregar ruta, editar template, query supabase, ajuste frontend."
agent: "agent"
model: ["Claude Sonnet 4.6", "Claude Sonnet 4.5"]
---

Ejecuta el cambio solicitado en VALAC Joyas.

## Stack rápido
Flask 3.1 + supabase-py v2 (`current_app.supabase`) + MercadoPago + Jinja2/Tailwind + jQuery

## Reglas
- Lee el archivo antes de editarlo
- Diff mínimo. No repitas contexto
- Precios: Decimal. Admin: @login_required. Imágenes: CDN_BASE_URL
- NO Flask-SQLAlchemy
- Si el cambio toca más de 3 archivos, lista los cambios primero y pide confirmación
