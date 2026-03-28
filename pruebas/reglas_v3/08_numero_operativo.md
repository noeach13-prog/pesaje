# Numero operativo — Definicion y reporte

## Responsabilidad

Definir que subtotal se usa operativamente como numero del dia
y como se reporta hacia el consumidor del dato.

---

## N8.1 — Definicion

### Numero operativo = CONFIRMADO + FORZADO

```
NUMERO_OPERATIVO = sum(raw_limpio) + sum(raw_engine) + sum(corr_confirmado) + sum(corr_forzado)
```

Incluye:
- Todas las correcciones con evidencia positiva convergente (Tipo A, C)
- Todas las correcciones forzadas por exclusion del raw (Tipo B)

### Numero refinado = OPERATIVO + ESTIMADO

```
NUMERO_REFINADO = NUMERO_OPERATIVO + sum(corr_estimado)
```

Incluye adicionalmente los ajustes finos plausibles (Tipo D).

---

## N8.2 — Justificacion

El numero operativo no puede contener valores demostrativamente imposibles.

Si una correccion existe porque el raw fue excluido por imposibilidad fisica,
el raw ya no es un valor admisible. Dejarlo vivo en el numero operativo
no es "conservador" — es incorrecto.

FORZADO no es "confirmado" epistemologicamente.
Pero si entra al numero operativo porque el raw rival ya fue excluido.
La diferencia se preserva en la trazabilidad.

---

## N8.3 — Solo para trazabilidad

- **RAW**: documentado pero nunca usado como numero operativo
- **CONFIRMADO solo**: en la auditoria como piso epistemologico, no publicado
  (porque contiene imposibles sin corregir)
- **Detalle por banda**: en el expediente para auditoria futura

---

## N8.4 — Umbral de calidad

```
diferencia = abs(OPERATIVO - REFINADO) / OPERATIVO * 100
```

| Diferencia | Interpretacion |
|------------|---------------|
| < 2% | Normal. ESTIMADO es marginal. |
| 2% - 5% | Atencion. Mucho peso en ESTIMADO. |
| > 5% | Problema. Reclasificar o buscar mas evidencia. |

Si FORZADO > 30% del delta total de correcciones → senal de calidad
de datos degradada que debe documentarse.

---

## N8.5 — Formato de reporte estandar

```
DIA X — RESULTADO
  Operativo:  XXXXXg  (CONF+FORZ, N correcciones)
  Refinado:   XXXXXg  (+ ESTIMADO, M ajustes finos)
  Delta:      XXXg (X.X%)
  Latas:      N
  VDP:        XXXXg
```

### Ecuacion por bandas (trazabilidad interna)

```
  [RAW]g       RAW
  +[X]g        CONFIRMADO  (lista de deltas)
  -[Y]g        FORZADO     (lista de deltas)
  -[Z]g        ESTIMADO    (lista de deltas)
  -------
  [TOTAL]g     TOTAL CORREGIDO
```

---

## N8.6 — Componentes del total del dia

```
TOTAL_DIA = venta_stock_operativo + VDP
```

Donde:
- venta_stock_operativo = NUMERO_OPERATIVO (ya incluye lid_discount via ajuste_latas)
- VDP = ventas de postres parseadas de seccion POSTRES

El lid_discount se reporta por separado para trazabilidad:
- lid_discount = N_latas_totales * 280g

---

## Ejemplo aplicado: D5

```
DIA 5 — RESULTADO
  Operativo:  35,265g  (CONF+FORZ, 6 correcciones)
  Refinado:   35,205g  (+ ESTIMADO, 1 ajuste fino)
  Delta:      60g (0.17%)
  Latas:      4
  VDP:        1,495g
```

Ecuacion:
```
  40,095g   RAW
    +305g   CONFIRMADO  (DDL +6555, DA -6275, VAN +6445, KIT -6120, PIS -300)
  -6,630g   FORZADO     (CHOCOLATE -6630)
    -60g    ESTIMADO    (CH C/ALM -60)
  -------
  33,710g   VENTA STOCK CORREGIDA

  + 1,495g  VDP
  -------
  35,205g   TOTAL DIA (REFINADO)
```
