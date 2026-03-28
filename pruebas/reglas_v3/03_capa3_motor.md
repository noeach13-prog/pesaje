# Capa 3 — Motor local (screening + senales + prototipos)

## Responsabilidad

Clasificar cada sabor, detectar senales, aplicar prototipos fuertes,
y marcar calidad del dato. Resuelve ~95% de los casos.

---

## Input

- Datos crudos de Capa 1 (DIA y NOCHE del periodo)
- Venta raw de Capa 2
- Contexto temporal: turnos adyacentes (T-1, T+1 minimo)

## Output

Cada sabor sale con exactamente UNO de:
- **LIMPIO** → pasa a Capa 5 para revision
- **ENGINE_CONFIRMADO** → valor corregido aceptado
- **RESUELTO_PROTOTIPO** → 1 prototipo fuerte aplicado
- **OBSERVACION** → 1 senal aislada, baja magnitud, sin corregir
- **ESCALAR_A_CAPA_4** → requiere expediente ampliado

---

## S3.1 — Screening (5 condiciones)

Evaluar en orden. Primera falla → SOSPECHOSO.

| # | Condicion | Variable | Falla → |
|---|-----------|----------|---------|
| C1 | `raw >= -50g` | Venta no imposiblemente negativa | SOSPECHOSO |
| C2 | `raw < 5000g` O hay apertura | Venta no absurdamente alta | SOSPECHOSO |
| C3 | `ab_N <= ab_D + 20g` O hay apertura | Abierta no sube sin explicacion | SOSPECHOSO |
| C4 | Toda cerrada tiene match ±30g | No hay cerrada huerfana | SOSPECHOSO |
| C5 | `engine == raw` | Engine no intervino | Si engine != raw → ENGINE |

Si pasa TODAS → **LIMPIO**.

### Definicion de apertura para screening (proxy rapido)
```
apertura = (ab_N - ab_D > 3000) AND (n_cerr_A > n_cerr_B)
```
Este es un proxy. La definicion completa de apertura (3 patas) se usa solo en Capa 4.

---

## S3.2 — Clasificacion de senales

Para cada sabor SOSPECHOSO, registrar que condiciones fallaron:

| Flag | Significado |
|------|------------|
| NEG | C1 fallo: raw < -50g |
| HIGH | C2 fallo: raw >= 5000g sin apertura |
| AB_UP | C3 fallo: ab sube sin apertura |
| C4d:PESO | C4 fallo: cerrada de DIA sin match en NOCHE |
| C4n:PESO | C4 fallo: cerrada de NOCHE sin match en DIA |
| CERR+N | Mas cerradas en NOCHE que en DIA |

Clasificacion secundaria:
- 1 flag → **SENAL** (simple)
- >=2 flags de distinto tipo → **COMPUESTO**

---

## S3.3 — Prototipos fuertes PF1-PF8

Se aplican SOLO si:
1. El caso matchea exactamente 1 prototipo
2. La evidencia es univoca (no hay hipotesis alternativa plausible)
3. La confianza del prototipo es >= 0.85

### PF1 — Error de digito en cerrada
**Firma**: cerrada con peso que difiere ±1000 o ±2000g del historial estable (>=5 sightings, varianza <=30g).
**Correccion**: reemplazar peso erroneo por peso historico del can.
**Conf**: 0.92 si >=5 sightings; 0.85 si 3-4 sightings.
**Ejemplo**: COOKIES D25 (5705→6705), KITKAT D26 (4385→6385).

### PF2 — Entrante duplicado
**Firma**: entrante de DIA persiste en NOCHE despues de que su cerrada fue abierta. El entrante ya se convirtio en cerrada pero no fue borrado.
**Correccion**: entrante NOCHE = 0 (remover del calculo).
**Conf**: 0.90 si la cerrada nueva en NOCHE matchea ±50g del entrante DIA.
**Ejemplo**: MARACUYA D28 (entrante 5825 persiste).

### PF3 — Phantom por RM-3
**Firma**: cerrada que fue abierta en turno anterior (RM-3: can abierto no puede reaparecer como cerrado). Ab no sube correspondiente a esa cerrada.
**Correccion**: cerrada = 0 (phantom).
**Conf**: 0.88 si ab confirma no-apertura.
**Ejemplo**: SAMBAYON D28 (cerr 6450 phantom).

### PF4 — Cerrada omitida en NOCHE
**Firma**: cerrada con historial (>=3 sightings) presente en DIA, ausente en NOCHE, ab no sube (no hubo apertura).
**Correccion**: agregar cerrada a NOCHE con peso historico.
**Conf**: 0.85 si >=3 sightings; 0.80 si 2 sightings.
**Ejemplo**: CHOCOLATE D28 (cerr 6545 omitida en DIA).

### PF5 — Cerrada omitida en DIA
**Firma**: cerrada con historial presente en NOCHE y turnos adyacentes, ausente en DIA, raw muy negativo.
**Correccion**: agregar cerrada a DIA con peso historico.
**Conf**: 0.85 si >=3 sightings.
**Ejemplo**: DDL D5 (cerr 6555 omitida en DIA, via CONJUNTO).

### PF6 — Apertura + phantom combinado
**Firma**: ab sube + desaparecen M cerradas + pero rise solo es coherente con N<M cerradas. Las M-N restantes son phantoms.
**Correccion**: eliminar M-N phantoms, contar N latas.
**Conf**: 0.80 (multiple correccion).
**Ejemplo**: CHOC DUBAI D28 (2 cerr desaparecen, rise coherente con 1).

### PF7 — Abierta imposible (AB_IMP)
**Firma**: ab sube entre turnos SIN apertura de cerrada, cerradas intactas, sin entrante que explique.
**Correccion**: reemplazar valor erroneo por referencia forward/backward.
**Conf**: 0.88 si forward confirma; 0.75 si solo backward.
**Ejemplo**: AMERICANA D25 (ab 1650→4365 backward).

### PF8 — Nombre inconsistente
**Firma**: dos sabores que nunca coexisten en el mismo turno, pesos coherentes entre ambos.
**Correccion**: combinar como un solo sabor.
**Conf**: 0.95 si pesos son continuacion obvia.
**Ejemplo**: TIRAMISU/TIRAMIZU D25, KITKAT/KIYKAT D5.

---

## S3.4 — Precedencias P1-P5

Cuando hay conflicto entre correcciones:

```
P1 PRESERVAR: cerrada real no se elimina salvo evidencia directa
   (RM-3, nota explicita, P1.c completo)
P2 ELIMINAR: solo phantoms con P1.a (RM-3), P1.b (0 sightings + ab no sube),
   o P1.c (P1+P2+P3 convergen)
P3 COMPLETAR: cerrada con >=2 sightings va al turno faltante
P4 RECONTAR: latas solo despues de P1-P3. Ab coherente con aperturas.
P5 NO ELIMINAR extra sin evidencia directa
```

---

## S3.5 — Marcas de calidad del dato

| Marca | Condicion | Efecto |
|-------|-----------|--------|
| DATO_NORMAL | Variacion normal entre turnos | Ninguno |
| COPIA_POSIBLE_LEVE | 2 turnos ab identica exacta (±0g), venta esperada >200g | Nota informativa |
| COPIA_POSIBLE_FUERTE | >=3 turnos ab identica exacta (±0g) | Conf -0.15 en resoluciones dependientes |

Estas marcas NO corrigen. Solo degradan confianza.

---

## S3.6 — Criterios de escalado a Capa 4

Escalar SOLO si:
- SOSPECHA COMPUESTA (>=2 flags simultaneos)
- VIOLACION ESTRUCTURAL que no cierra con 1 prototipo
- Conflicto entre >=2 prototipos con resultados distintos
- Correccion potencial >2000g sin evidencia univoca

NO escalar:
- LIMPIO (va a Capa 5)
- ENGINE simple confirmado
- Prototipo fuerte con evidencia univoca

---

## Test de validacion

Para D5:
- 41 sabores LIMPIO
- 4 sabores ENGINE (AMERICANA, COOKIES, MENTA, SAMBAYON AMORES)
- 7 sabores con senales que requieren analisis (DDL, DA, VAINILLA, KITKAT, PISTACHO, CHOCOLATE, CH C/ALM)
- PF8 aplicado: KIYKAT→KITKAT (nombre corregido antes de calculo)
