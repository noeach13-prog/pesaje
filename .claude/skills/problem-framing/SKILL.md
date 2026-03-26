---
name: problem-framing
description: Definir con claridad el problema real antes de proponer arquitectura, lógica o cambios de código.
---

# Problem Framing

## Cuándo usar
- Antes de diseñar o modificar lógica.
- Cuando el problema parece obvio pero la solución directa podría ser incorrecta.
- Cuando hay múltiples interpretaciones posibles de los datos o del pedido.

## Protocolo
Antes de proponer cualquier cambio, responder:

1. **Problema real:** reformular en una oración qué se está resolviendo.
2. **Supuestos:** listar cada supuesto que se está usando, marcando cuáles son verificables y cuáles no.
3. **Observación vs inferencia:** separar explícitamente qué es dato crudo y qué es conclusión derivada.
4. **Trampas ingenuas:** al menos una solución que parece correcta pero no lo es, y por qué falla.
5. **Criterio de éxito:** qué condición concreta indica que el problema está resuelto.

## Principios
- La formulación inicial del problema puede estar equivocada.
- No programar antes de redefinir.
- Si no se puede articular el criterio de éxito, el problema no está entendido.

## Salida
- Reformulación del problema (1-2 oraciones)
- Lista de supuestos explícitos
- Criterio de éxito medible
- Principal riesgo conceptual
