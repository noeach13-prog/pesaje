---
name: inventory-reconciliation
description: Usa esta skill cuando el problema involucre reconstrucción de stock real entre turnos, omisiones de latas, entrantes no documentados y cálculo de venta reconciliada.
---

# Inventory Reconciliation

## Cuándo usar esta skill
Usar cuando haya que:
- comparar stock entre turnos
- explicar ventas negativas
- rastrear latas omitidas o reaparecidas
- reconstruir stock verdadero bajo error humano
- revisar reconciler.py, calculator.py o models.py

## Principios
- Cada hoja es una observación imperfecta, no verdad absoluta.
- Una lata faltante en un turno puede ser omisión, no venta.
- Una lata nueva sin entrante puede ser:
  1. lata omitida antes
  2. entrante no documentado
  3. stock genuinamente nuevo
- No asumir identidad física perfecta por peso; tratar matches como probabilísticos.
- Antes de corregir stock en dos períodos, exigir confianza suficiente.

## Reglas de decisión
- Comparar ventanas de múltiples turnos, no solo A->B.
- Mantener raw y reconciled en paralelo.
- Toda inferencia debe dejar evento explicativo.
- Si no hay evidencia suficiente, usar unresolved.

## Salida esperada
Cuando uses esta skill:
1. explicar hipótesis
2. proponer cambios por archivo
3. implementar de forma incremental
4. dejar trazabilidad y validación