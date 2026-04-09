---
description: "Ejecuta una fase completa del plan de migración VALAC Joyas de forma autónoma. Use when: ejecutar fase, run phase, implementar fase completa, build autónomo."
agent: "valac-executor"
model: ["Claude Sonnet 4.6", "Claude Sonnet 4.5"]
---

## Instrucciones

1. Lee el plan completo desde `/memories/session/migration_plan_v1.md`
2. Identifica la fase indicada por el usuario: {{phase}}
3. Ejecuta TODOS los tasks de esa fase en orden de dependencia
4. Usa todo list para trackear progreso
5. Para Tasks de SQL (migrations/), crea el archivo .sql pero NO lo ejecutes — el usuario lo ejecuta manualmente en Supabase Dashboard
6. Para Tasks de Python, implementa los cambios directamente en los archivos
7. Al terminar, reporta: tasks completados, archivos creados/modificados, y qué debe hacer el usuario manualmente (SQL migrations)
