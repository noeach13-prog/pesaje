---
name: problem-framing
description: Usa esta skill para definir con claridad el problema real antes de proponer arquitectura, lógica o cambios de código.
---

# Problem Framing

## Cuándo usar esta skill
Usar cuando haya que:
- entender qué problema se está resolviendo realmente
- separar síntoma de causa
- distinguir entre dato observado y conclusión inferida
- redefinir el objetivo antes de programar
- revisar si una solución está atacando el problema correcto

## Qué debe hacer Claude
Antes de proponer cambios, Claude debe responder:
1. cuál es el problema real
2. qué supuestos está usando
3. qué parte es observación y qué parte es inferencia
4. qué soluciones ingenuas parecerían correctas pero no lo son
5. qué criterio define éxito en este proyecto

## Principios
- No asumir que la formulación inicial del problema es correcta.
- No empezar a programar antes de redefinir el problema.
- Separar claramente:
  - hechos observados
  - hipótesis
  - riesgos de interpretación

## Salida esperada
Claude debe devolver:
- una reformulación del problema
- una lista de supuestos explícitos
- un criterio de éxito
- una advertencia sobre el principal riesgo conceptual