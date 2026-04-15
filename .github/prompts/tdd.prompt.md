---
description: "Workflow TDD para VALAC Joyas con pytest. Use when: escribir tests, crear test, TDD, testing, cobertura, test-driven development."
agent: "valac-tdd-guide"
model: ["Claude Sonnet 4.6", "Claude Sonnet 4.5"]
tools: [read, edit, search, execute]
---

Guía al usuario a través del ciclo TDD para el código indicado.

## Ciclo

1. **RED** — Escribe un test que falle para el comportamiento esperado
2. **RUN** — `pytest tests/ -x -v` → confirmar que falla
3. **GREEN** — Escribe el código mínimo para que pase
4. **RUN** — `pytest tests/ -x -v` → confirmar que pasa
5. **REFACTOR** — Mejorar el código sin romper tests
6. **COVERAGE** — `pytest tests/ --cov=valac_jewelry --cov-report=term-missing`

## Reglas

- Tests antes de código. Siempre.
- Mock Supabase y MercadoPago — nunca llamar servicios reales en tests
- Precios siempre `Decimal` en tests (ej: `Decimal("5000")`, no `5000.0`)
- Un assert por concepto. Múltiples asserts OK si verifican el mismo caso.
- Tests independientes — sin shared state entre tests
- Nombres descriptivos: `test_apply_coupon_percent_with_cap_limits_discount`

Si el usuario no especifica qué testear, sugerir empezar por `services/pricing.py` (lógica pura, sin mocks necesarios, alto riesgo de negocio).
