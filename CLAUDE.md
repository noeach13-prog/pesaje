# Proyecto Pesaje - Reglas del sistema

## Qué es este proyecto
Este proyecto NO es una web app, NO es un servidor y NO necesita preview, puertos ni launch.json.
Es un motor Python CLI para analizar planillas Excel de stock de helado por turno/día.

## Problema real
Las planillas NO representan verdad absoluta.
Los empleados a veces:      
- olvidan registrar latas cerradas
- olvidan registrar entrantes
- cargan pesos con errores
- registran turnos fuera de orden o con ruido

El objetivo NO es comparar A->B de forma literal.
El objetivo es reconstruir el stock más probable a través de múltiples turnos y luego calcular ventas en gramos con nivel de confianza.

## Invariantes
- Nunca asumir que una aparición de stock implica automáticamente "venta negativa".
- Nunca asumir identidad física perfecta de una lata solo por peso.
- Tratar cada hoja como observación ruidosa.
- Mantener siempre separación entre:
  - stock observado (raw)
  - stock reconciliado (inferred)
- Toda corrección reconciliada debe dejar trazabilidad.
- Si la confianza no es suficiente, marcar como unresolved en lugar de inventar una explicación fuerte.

## Arquitectura esperada
- parser.py: lectura de workbook y hojas válidas
- reconciler.py: reconciliación multi-turno
- calculator.py: cálculo de ventas usando stock reconciliado
- exporter.py: exportación Excel con colores por confianza

## Reglas de trabajo para Claude
- No trabajar en preview, puertos o launch.json.
- No reescribir parser.py salvo pedido explícito.
- Antes de cambiar lógica central, explicar:
  1. qué archivo tocarás
  2. por qué
  3. qué hipótesis usarás
- Preferir cambios pequeños, auditables y testeables.
- Mantener modo auditor cuando una nueva lógica aún no está validada.