---
name: minimal-change-implementation
description: Forzar el set de cambios más pequeño y seguro posible antes de implementar.
---

# Minimal Change Implementation

## Cuándo usar
- Antes de implementar cualquier cambio que toque más de un archivo.
- Cuando un cambio puede tener efectos cascada sobre otros módulos.
- Cuando se quiere agregar funcionalidad sin romper lo existente.

## Protocolo
Antes de editar código, declarar:

1. **Archivos a tocar:** lista exacta, con razón por archivo.
2. **Archivos que NO se tocan:** lista explícita de lo que queda intacto y por qué.
3. **Justificación de mínimo viable:** por qué este es el set más chico que resuelve el problema.
4. **Interfaces preservadas:** qué firmas, tipos de retorno o contratos públicos no cambian.
5. **Riesgos:** qué podría salir mal y cómo se detectaría.

## Reglas
- Si se puede resolver tocando 1 archivo, no tocar 2.
- Preferir extender sobre reescribir.
- No cambiar interfaces públicas salvo que sea el objetivo explícito.
- No agregar dependencias nuevas salvo necesidad demostrada.
- Cada cambio debe ser reversible sin afectar otros módulos.

## Salida
- Tabla de cambios (archivo, tipo de cambio, razón)
- Declaración de interfaces preservadas
- Principal riesgo y su mitigación
