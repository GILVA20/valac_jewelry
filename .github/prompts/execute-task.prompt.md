---
description: "Ejecutar un task específico de un plan de feature. Use when: implementar task, ejecutar paso del plan, build task."
agent: "agent"
model: ["Claude Sonnet 4.6", "Claude Sonnet 4.5"]
---

Ejecuta SOLO el task indicado por el usuario. Nada más.

## Reglas críticas
1. Lee los archivos antes de modificarlos
2. Diff mínimo — no repitas código sin cambios
3. Precios: `Decimal`, nunca `float`
4. DB: `current_app.supabase` — no instanciar nuevo
5. Imágenes: `CDN_BASE_URL + filename`
6. Admin: `@login_required` + `current_user.is_admin`
7. No Flask-SQLAlchemy. Solo supabase-py
8. Sin comentarios obvios, sin docstrings extra
9. Si algo no está claro en el task, pregunta ANTES de implementar
