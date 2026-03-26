# Bandas y tipos de justificacion

## Responsabilidad

Clasificar epistemologicamente cada correccion y asignarla a una banda
que determine su inclusion en el numero operativo.

---

## B6.1 — Taxonomia de justificaciones (4 tipos)

El tipo de justificacion manda sobre el conteo bruto de planos.
El criterio ">=2 planos" es un proxy util para tipo A, no requisito universal.

### Tipo A — Convergencia independiente
- **Definicion**: >=2 planos apuntan al mismo hecho. La correccion tiene identidad causal clara.
- **Criterio**: sabemos QUE paso y POR QUE.
- **Ejemplo**: DDL+DA D5 — P1 (ab normales) + P2 (sightings 4v1) explican exactamente que cerrada fue mal asignada.

### Tipo B — Reductio / exclusion fisica
- **Definicion**: el raw es demostrativamente imposible. La correccion es el mecanismo mas viable pero no el unico concebible.
- **Criterio**: sabemos que el raw esta MAL, pero la correccion exacta tiene incertidumbre residual.
- **Ejemplo**: CHOCOLATE D5 — sin apertura, raw=7485g es imposible. Fix (ent 6530~6630=mismo can) es unico viable pero matching de 100g.

### Tipo C — Prototipo historico fuerte
- **Definicion**: un solo plano pero con patron de error bien establecido y ratio de sightings alto (>=3:1).
- **Criterio**: convergencia temporal interna equivale a convergencia multi-plano. Negar la correccion requiere asumir que N pesajes se equivocaron y 1 acerto.
- **Ejemplo**: PISTACHO D5 — PF1 digit 6630→6330, ratio 3:1, patron clasico de centena.
- **Condicion de guardia**: ratio >=3:1 Y patron PF conocido. Si ratio <3:1 → baja a ESTIMADO.

### Tipo D — Ajuste plausible menor
- **Definicion**: correccion de baja magnitud con evidencia parcial. Ni imposible ni confirmada.
- **Criterio**: si se omitiera, el resultado no se vuelve absurdo.
- **Ejemplo**: CH C/ALM D5 — pesaje variance 60g, solo P2, ambos valores razonables.

---

## B6.2 — Las 3 bandas

| Banda | Tipos que entran | Semantica | Intervalo de confianza |
|-------|-----------------|-----------|----------------------|
| **CONFIRMADO** | A, C | Sabemos que paso. Valor corregido preciso. | Estrecho |
| **FORZADO** | B | Raw imposible. Fix es el mejor disponible. | Mas ancho |
| **ESTIMADO** | D, y B/C sin evidencia suficiente | Ajuste plausible, prescindible. | Amplio |

### Excepciones al mapeo
- Tipo C con ratio <3:1 → baja a ESTIMADO
- Tipo B con mecanismo correctivo univoco Y preciso → puede subir a CONFIRMADO (raro)
- Tipo D con delta <100g → queda en ESTIMADO sin penalizacion (insignificante)

---

## B6.3 — Regla de routing A- → CONJUNTO

Cuando un sabor tiene:
- Convergencia numerica univoca (solo 1 valor posible)
- Pero mecanismo causal ambiguo en analisis individual

NO crear subcategoria A-. En cambio:
1. Escalar a analisis multifactor conjunto (E4.8)
2. Buscar patron cruzado con otros sabores del turno
3. Si patron existe → CONFIRMADO_CONJUNTO (tipo A)
4. Si patron no existe → FORZADO (tipo B)

Esto mantiene la taxonomia limpia (A/B/C/D sin variantes).

---

## B6.4 — Interaccion con confianza

La confianza numerica (0.XX) es interna al expediente.
La banda es la clasificacion operativa que sale al reporte.

| Conf | Efecto |
|------|--------|
| >= 0.85 | Banda segun tipo normalmente |
| 0.70 - 0.84 | Banda segun tipo pero con nota |
| 0.50 - 0.69 | Revisar si debe bajar una banda |
| < 0.50 | H0 / UNRESOLVED automatico |

### Ajustes de confianza
- COPIA_POSIBLE_FUERTE: -0.15
- Conflicto entre hipotesis sin resolucion clara: -0.15
- Matching en limite de tolerancia: -0.10

---

## B6.5 — Aplicacion por dia

Al cerrar un dia, cada correccion queda clasificada:

```
sabor | raw | corregido | delta | tipo | banda | motivo_breve
```

Y las bandas se acumulan:
```
CONFIRMADO = sum(deltas tipo A + tipo C)
FORZADO = sum(deltas tipo B)
ESTIMADO = sum(deltas tipo D)
```

---

## Ejemplo aplicado: D5

| Sabor | Delta | Tipo | Banda |
|-------|-------|------|-------|
| DULCE D LECHE | +6555 | A | CONFIRMADO |
| DULCE AMORES | -6275 | A | CONFIRMADO |
| VAINILLA | +6445 | A | CONFIRMADO |
| KITKAT | -6120 | A | CONFIRMADO |
| PISTACHO | -300 | C | CONFIRMADO |
| CHOCOLATE | -6630 | B | FORZADO |
| CH C/ALM | -60 | D | ESTIMADO |

Totales: CONFIRMADO = +305g, FORZADO = -6630g, ESTIMADO = -60g.
