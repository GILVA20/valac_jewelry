---
description: "Ejecuta un task específico del plan de migración VALAC Joyas. Use when: ejecutar task puntual, implementar un paso, build task individual."
agent: "valac-executor"
model: ["Claude Sonnet 4.6", "Claude Sonnet 4.5"]
---

## Instrucciones

1. Lee el plan desde `/memories/session/migration_plan_v1.md`
2. Busca el task indicado: {{task_id}}
3. Lee TODOS los archivos listados en ese task
4. Implementa los cambios
5. Valida que no haya errores
6. Reporta: qué se cambió, qué archivos se tocaron
