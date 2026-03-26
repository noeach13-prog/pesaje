---
name: test-first-design
description: Definir casos de validación concretos antes de modificar lógica, para saber si el cambio funciona antes de implementarlo.
---

# Test-First Design

## Cuándo usar
- Antes de modificar cualquier lógica de cálculo o inferencia.
- Cuando un cambio puede producir resultados silenciosamente incorrectos.
- Cuando no hay forma obvia de verificar si el resultado es correcto.

## Protocolo
Antes de escribir código, presentar:

1. **Caso real:** un ejemplo tomado de datos reales del proyecto, con entrada y salida esperada.
2. **Caso sintético favorable:** entrada diseñada donde el cambio debe producir mejora visible.
3. **Caso sintético adverso:** entrada diseñada donde el cambio NO debe empeorar el resultado actual.
4. **Criterio de aprobación:** condición concreta que determina si el cambio pasa o falla.

## Reglas
- No implementar sin al menos los 3 casos definidos.
- Si no se puede construir un caso real, explicar por qué y compensar con un caso sintético adicional.
- Los casos deben ser verificables por el usuario sin ejecutar código complejo.
- Presentar los casos al usuario y esperar aprobación antes de implementar.

## Salida
- Tabla de casos (entrada, salida esperada, tipo)
- Criterio de aprobación en una oración
- Método de verificación (cómo el usuario puede confirmar el resultado)
