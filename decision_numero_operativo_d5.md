# Decisión: número operativo del Día 5

---

## A. Planteo del problema

Las 3 bandas (CONFIRMADO / FORZADO / ESTIMADO) clasifican la calidad epistemológica de cada corrección. Pero no responden la pregunta operativa: **¿qué número uso?**

Si reporto el día con 3 subtotales (40,400 / 33,770 / 33,710), el consumidor del dato tiene que elegir cuál creer. Eso es trasladar la decisión metodológica al usuario en lugar de tomarla yo. Las bandas son herramientas internas del auditor; el número operativo es lo que sale del sistema.

El problema concreto es CHOCOLATE (-6,630g). Si uso solo CONFIRMADO (40,400g), el total incluye un raw de 7,485g para CHOCOLATE que es físicamente imposible. Estaría publicando un número que contiene un valor que yo mismo demostré que no puede existir.

---

## B. Decisión

**Opción B: CONFIRMADO + FORZADO es el número operativo base.**

### Justificación

El número operativo no puede contener valores demostrativamente imposibles. Si una corrección existe porque el raw fue excluido por imposibilidad física, el raw ya no es un valor admisible. Dejarlo vivo en el número operativo no es "conservador" — es incorrecto.

La distinción entre CONFIRMADO y FORZADO es epistemológica, no operativa:

- **CONFIRMADO** dice: "sabemos qué pasó y el valor corregido es preciso."
- **FORZADO** dice: "sabemos que el raw es imposible y el valor corregido es la mejor estimación disponible."

Ambos son operativamente necesarios. La diferencia es que CONFIRMADO tiene intervalo de confianza más estrecho que FORZADO. Pero FORZADO sigue siendo mejor que el raw (que tiene confianza cero, porque es imposible).

Usar solo CONFIRMADO como número operativo equivale a decir: "prefiero publicar un número que contiene un imposible antes que aceptar una corrección forzada." Eso no es conservadurismo metodológico. Es error por omisión.

### Qué NO es la Opción B

La Opción B no dice que FORZADO tenga la misma calidad que CONFIRMADO. Dice que FORZADO es operativamente obligatorio porque la alternativa (mantener el raw) ya fue refutada. La distinción se preserva en la trazabilidad.

---

## C. Regla operativa final

### Número operativo base = CONFIRMADO + FORZADO

Este es el número que se reporta como venta del día. Incluye:
- Todas las correcciones con evidencia positiva convergente (Tipo A, C)
- Todas las correcciones forzadas por exclusión del raw (Tipo B)

### Número refinado = CONFIRMADO + FORZADO + ESTIMADO

Este es el número que incluye adicionalmente los ajustes finos plausibles (Tipo D). Se informa como dato complementario. La diferencia con el operativo es siempre pequeña (en el Día 5: 60g, 0.2%).

### Solo para trazabilidad

- El RAW (40,095g) queda documentado pero nunca se usa como número operativo.
- El subtotal CONFIRMADO solo (40,400g) queda en la auditoría como piso epistemológico pero no se publica como número operativo, porque contiene imposibles sin corregir.
- El detalle por banda de cada corrección queda en el expediente para auditoría futura.

### Formalización

```
NÚMERO OPERATIVO = sum(raw_limpio) + sum(raw_engine) + sum(corr_confirmado) + sum(corr_forzado)
NÚMERO REFINADO  = NÚMERO OPERATIVO + sum(corr_estimado)
```

La diferencia OPERATIVO - REFINADO siempre debe ser < 2% del total. Si supera el 2%, hay demasiada corrección en ESTIMADO y el sistema necesita más evidencia o reclasificación.

---

## D. Aplicación al Día 5

### Ecuación por bandas (verificada)

```
  40,095g   RAW
    +305g   CONFIRMADO  (DDL +6555, DA -6275, VAN +6445, KIT -6120, PIS -300)
  -6,630g   FORZADO     (CHOCOLATE -6630)
    -60g    ESTIMADO    (CH C/ALM -60)
```

### Números del Día 5

| Concepto | Venta stock | VDP | Total |
|----------|-------------|-----|-------|
| RAW (solo trazabilidad) | 40,095g | 1,495g | 41,590g |
| **OPERATIVO (CONF+FORZ)** | **33,770g** | **1,495g** | **35,265g** |
| REFINADO (CONF+FORZ+EST) | 33,710g | 1,495g | 35,205g |

### Número operativo del Día 5: **35,265g**
### Número refinado del Día 5: **35,205g**
### Diferencia: 60g (0.17%) — dentro del umbral de 2%

### Cómo reportar hacia adelante

Formato estándar por día:

```
DÍA X — RESULTADO
  Operativo:  XXXXXg  (CONF+FORZ, N correcciones)
  Refinado:   XXXXXg  (+ ESTIMADO, M ajustes finos)
  Delta:      XXXg (X.X%)
  Latas:      N
  VDP:        XXXXg
```

Para el Día 5:

```
DÍA 5 — RESULTADO
  Operativo:  35,265g  (CONF+FORZ, 6 correcciones)
  Refinado:   35,205g  (+ ESTIMADO, 1 ajuste fino)
  Delta:      60g (0.17%)
  Latas:      4
  VDP:        1,495g
```

---

## Nota sobre la distinción CONFIRMADO vs FORZADO dentro del operativo

Que ambos entren al número operativo NO borra su diferencia. En la auditoría de cada día, cada corrección sigue marcada con su tipo (A/B/C/D) y su banda (CONFIRMADO/FORZADO/ESTIMADO). Si un día tiene mucho peso en FORZADO (ej: >30% del delta total es Tipo B), eso es una señal de calidad de datos degradada que debe documentarse. Pero el número operativo sigue siendo CONF+FORZ, porque la alternativa es publicar imposibles.
