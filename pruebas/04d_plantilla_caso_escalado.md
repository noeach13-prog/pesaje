# Plantilla caso escalado — 1 bloque por caso

## Formato obligatorio (máximo 8 líneas)

```
### [SABOR] — [prototipo o "sin prototipo"]
- Señales: [lista de señales detectadas, ej: raw=-3635, cerr 6545 NOCHE sin match DIA]
- H1: [hipótesis principal + evidencia clave]
- H2: [hipótesis alternativa, o "ninguna plausible"]
- Corrección: [acción concreta: "agregar cerr X a DIA" / "poner cerr X en 0" / H0]
- Impacto: [MASA: ±Ng en venta_stock] o [INTERP: redistribuye entre sabores, neto 0]
- Conf: [0.XX]
- Delta: [raw → corregido = ±Ng]
```

---

## Ejemplos reales (D28)

### CHOCOLATE — PF5:CERR_OMITIDA_DIA
- Señales: raw=-3635, cerr 6545 en NOCHE sin match en DIA, historial 6545 como entrante D27
- H1: cerr 6545 omitida del registro DIA (operador olvidó anotarla)
- H2: cerr 6545 es nueva (llegó durante turno noche sin documentar)
- Corrección: agregar cerr 6545 a total_DIA
- Impacto: MASA: +6545g en venta_stock
- Conf: 0.85
- Delta: -3635 → 2910 = +6545g

### CHOC DUBAI — PF6:APERTURA_CON_PHANTOM
- Señales: raw=8140, 2 cerr DIA (6400,6355), 0 cerr NOCHE, ab 1420→6035
- H1: cerr 6400 phantom (sin historial), solo 6355 fue abierta (1 lata)
- H2: ambas reales y abiertas (2 latas, pero ab sube solo 4615 vs esperado ~12000)
- Corrección: poner cerr 6400 en 0, contar 1 lata
- Impacto: MASA: -6400g en venta_stock, -1 lata
- Conf: 0.80
- Delta: 8140 → 1740 = -6400g

### SAMBAYON — PF3:PHANTOM_CERR
- Señales: raw=7105, cerr 6450 fue abierta D27 (ab 1260→6235), reaparece como cerr DIA D28
- H1: cerr 6450 phantom por RM-3 (no puede resellarse), cerr 6675 real (sin evidencia contra)
- H2: ambas phantom (6675 tampoco tiene historial) → venta=555
- Corrección: poner cerr 6450 en 0, mantener 6675
- Impacto: MASA: -6450g en venta_stock, -1 lata
- Conf: 0.80
- Delta: 7105 → 655 = -6450g

### MARACUYA — PF2:ENTRANTE_DUP
- Señales: raw=-5825, entrante 6380 en DIA y NOCHE, ab 0→5825
- H1: entrante fue abierto, persiste en NOCHE por error de registro
- H2: ninguna plausible
- Corrección: poner entrante NOCHE en 0, contar 1 lata
- Impacto: MASA: +6380g en venta_stock (remover de total_NOCHE)
- Conf: 0.90
- Delta: -5825 → 555 = +6380g

### PISTACHO — PF3:PHANTOM_CERR
- Señales: raw=7900, cerr 6350 en DIA sin historial, no está en NOCHE, ab baja 2705→1155
- H1: cerr 6350 phantom (no existe, ab confirma 0 aperturas)
- H2: cerr 6350 omitida de NOCHE (AN: mismo resultado numérico)
- Corrección: poner cerr 6350 en 0 en DIA
- Impacto: MASA: -6350g en venta_stock, -1 lata
- Conf: 0.85
- Delta: 7900 → 1550 = -6350g
