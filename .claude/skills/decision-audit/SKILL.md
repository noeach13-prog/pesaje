---
name: decision-audit
description: Justificar explícitamente cada recomendación importante con observación, evidencia, alternativas y confianza.
---

# Decision Audit

## Cuándo usar
- Cuando se recomienda una arquitectura, algoritmo o cambio de diseño.
- Cuando se elige una interpretación sobre otra.
- Cuando una decisión será difícil de revertir.

## Protocolo
Para cada decisión o recomendación importante, documentar:

1. **Observación:** qué dato o situación dispara la decisión.
2. **Conclusión:** qué se recomienda hacer.
3. **Evidencia:** qué datos soportan la conclusión (con nivel: fuerte/media/débil).
4. **Alternativas descartadas:** al menos una opción considerada y por qué se rechazó.
5. **Confianza:** alta / media / baja — y qué la bajaría o subiría.

## Reglas
- No hacer recomendaciones sin al menos una alternativa descartada.
- Si la confianza es baja, presentar como opción, no como recomendación.
- Si hay dos alternativas con confianza similar, presentar ambas y pedir decisión al usuario.
- Nunca ocultar incertidumbre detrás de lenguaje afirmativo.

## Salida
- Tabla de decisión (observación, conclusión, evidencia, alternativas, confianza)
- Si confianza < alta: pregunta explícita al usuario
