# Reglas madre del sistema

## Reglas metodologicas RM-1 a RM-10

### RM-1: La planilla es observacion ruidosa, no verdad
Cada celda del Excel es lo que un empleado anoto.
No es lo que realmente pesa la lata.
Tratar todo dato como observacion con ruido.

### RM-2: La fisica no se negocia
Si un valor viola conservacion de masa (abierta sube sin fuente,
cerrada desaparece sin apertura), el valor es un error.
No importa que el threshold del engine no lo detecte.
No importa la magnitud.

### RM-3: Cerrada abierta no puede reaparecer como cerrada
Una lata que fue abierta (ab subio, cerr desaparecio) no puede
volver a aparecer como cerrada en turnos posteriores.
Si aparece → es phantom o error de registro.
Es imposibilidad fisica, no heuristica.

### RM-4: Separar stock observado de stock reconciliado
- **Observado (raw)**: lo que dice la planilla, sin modificar
- **Reconciliado (engine)**: correcciones automaticas del tracker
- **Corregido (multi-turno)**: correcciones del analisis humano/LLM
Cada nivel deja trazabilidad de que cambio y por que.

### RM-5: Si no sabes, deci que no sabes
Si la evidencia es insuficiente para corregir, clasificar como
H0/UNRESOLVED con el valor raw/engine.
Nunca inventar una explicacion para cerrar el caso.

### RM-6: La confianza es continua, no binaria
No existe "correcto" o "incorrecto" absoluto. La confianza
va de 0.50 (minimo para intervenir) a 0.95+ (prototipo validado).

### RM-7: Forward gana sobre backward
Cuando DIA y NOCHE tienen valores contradictorios:
- Si NOCHE es coherente con turnos POSTERIORES → NOCHE es correcto
- Si DIA es coherente con turnos ANTERIORES y NOCHE no → DIA es correcto
La secuencia forward tiene mas peso (menos propagacion de error).

### RM-8: Prototipos se validan con PDF, luego se generalizan
Un patron de error se convierte en prototipo solo despues de validacion
contra un dia con PDF resuelto. Prototipos validados:
- PF1 digito cerrada: COOKIES D25, KITKAT D26
- PF2 entrante dup: MARACUYA D28
- PF3 phantom RM-3: SAMBAYON D28
- PF7 AB_IMP: AMERICANA D25
- PF8 nombre: TIRAMISU/TIRAMIZU D25

### RM-9: El total operativo = CONFIRMADO + FORZADO
El numero operativo no puede contener valores demostrativamente imposibles.
FORZADO entra al operativo porque la alternativa (mantener raw imposible)
ya fue refutada. La distincion CONFIRMADO/FORZADO se preserva en trazabilidad.

### RM-10: Cada dia se resuelve completo antes de avanzar
Los 50+ sabores se clasifican, los corregidos se verifican,
los sospechosos se analizan. El total se cierra.
Recien entonces se pasa al dia siguiente.

---

## Principios fisicos P1-P6

### P1: Conservacion de masa del helado
La masa en un balde solo puede:
- **Bajar**: consumo (venta, degustacion, derretimiento)
- **Subir**: apertura de cerrada, agregado de entrante, o error
- **Mantenerse**: entre cierre y apertura (varianza ±15-20g)

### P2: Integridad de lata cerrada
Peso entre 6000-7900g. Solo cambia por:
- Varianza de pesaje: ±15-30g entre mediciones
- Error de registro: ±1000-2000g (digito equivocado)
- Si no se abre, debe aparecer en turno siguiente con peso similar

### P3: Apertura de cerrada
Cuando se abre una cerrada:
- Abierta salta significativamente (+4000-6500g tipico)
- Cerrada desaparece del listado
- Tracker marca can como "opened"

### P4: Cierre→Apertura entre turnos
Entre cierre NOCHE y apertura DIA siguiente:
- Diferencia en abierta ~0g (±0-150g por condensacion)
- Diferencia >300g sugiere error o evento no registrado

### P5: Imposibilidad de subida sin fuente
Si abierta SUBE entre DIA→NOCHE sin apertura, sin entrante,
sin otra fuente → **el valor es error de registro**.
No importa la magnitud.

### P6: Existencia fisica de lata no abierta
Si cerrada aparece en DIA pero no en NOCHE,
y abierta no muestra salto de apertura
→ **la lata sigue existiendo**. Fue omitida del registro.

---

## Thresholds instrumentales vs razonamiento fisico

### Thresholds rigidos (herramientas del tracker)
| Threshold | Valor | Uso |
|-----------|-------|-----|
| Tolerancia tracker | 30g default, 45-105g adaptativo | Matching de cans |
| Peso maximo lata | 7900g | Deteccion T11 |
| Lid discount | 280g/lata | Calculo de total |
| Varianza pesaje | ±15-30g | Distinguir misma lata vs diferente |
| Digit offset | ±1000/±2000 | Deteccion automatica typo |

### Razonamiento fisico (sin threshold)
| Decision | Razonamiento |
|----------|-------------|
| Se abrio la cerrada? | Mirar si ab salta. No hay threshold. |
| Es error de registro? | Viola conservacion de masa → error. Magnitud irrelevante. |
| Cual valor es correcto? | Forward/backward. Coherente con secuencia = correcto. |
| Cerrada omitida o trasladada? | Forward: reaparece? Hay entrante similar? Sin forward → incertidumbre. |

**Principio clave: los thresholds son herramientas. El razonamiento final es SIEMPRE fisico.**
Si threshold dice "no hay anomalia" pero la secuencia muestra imposibilidad → secuencia gana.
Si threshold dice "anomalia" pero secuencia es coherente → secuencia gana.
