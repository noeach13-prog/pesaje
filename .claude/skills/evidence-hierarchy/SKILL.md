---
name: evidence-hierarchy
description: Clasificar evidencia en fuerte, media o débil antes de sacar conclusiones o tomar decisiones.
---

# Evidence Hierarchy

## Cuándo usar
- Antes de afirmar una conclusión basada en datos.
- Cuando hay señales contradictorias o ambiguas.
- Cuando una decisión depende de inferencias encadenadas.

## Protocolo
Para cada conclusión o recomendación, clasificar la evidencia que la soporta:

| Nivel | Criterio | Ejemplo genérico |
|-------|----------|-----------------|
| **Fuerte** | Dato directo, repetible, sin ambigüedad | Valor leído de celda, test que pasa/falla |
| **Media** | Dato indirecto o con una capa de inferencia | Correlación entre dos valores, patrón en 3+ observaciones |
| **Débil** | Suposición razonable sin dato que la confirme | "Probablemente el operador olvidó registrar" |

## Reglas
- No tratar evidencia débil como si fuera fuerte.
- Si la conclusión depende solo de evidencia débil, marcarla como hipótesis, no como hecho.
- Preferir múltiples señales medias convergentes sobre una sola señal fuerte aislada.
- Cuando dos señales se contradicen, declarar el conflicto en vez de elegir una silenciosamente.

## Salida
- Tabla de evidencia usada (nivel + dato + fuente)
- Conclusión con nivel de confianza explícito (alto/medio/bajo)
- Si confianza < media: declarar qué dato adicional resolvería la ambigüedad
