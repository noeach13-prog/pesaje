# Pesaje v3.0.0 — Baseline estable post-refactor

Fecha: 2026-03-26

## Arquitectura

Pipeline de 5 capas con separacion estricta observacion/hipotesis/decision:

- **Capa 1** (`capa1_parser.py`): Wrapper sobre parser v1. Detecta DIA/NOCHE o turno unico.
- **Capa 2** (`capa2_contrato.py`): Formula contable inmutable. Sin inferencia.
- **Capa 3** (`capa3_motor.py`): Screening + prototipos PF1-PF8 + arbitro.
- **Capa 4** (`capa4_expediente.py`): Expediente multi-plano para escalados.
- **Capa 5** (`capa5_residual.py`): Segunda pasada residual sobre limpios.

## Reforma constitucional (Capa 3)

- `_observar()` es el unico punto de contacto con datos crudos por sabor.
- `_screening()` lee solo ObservacionC3, no toca Excel.
- Constantes fisicas centralizadas en `constantes_c3.py`.
- Canonicalizacion segura con deteccion de colisiones (`canonicalizar_nombres`).
- PFs como generadores puros de `HipotesisCorreccion` (`generadores_c3.py`).
- Arbitro unico (`arbitro_c3.py`) con filtro de coherencia material.
- Doble eje de status: `screening_status` + `resolution_status`.
- `SOLO_DIA`/`SOLO_NOCHE` = `venta_final_c3 = None` (no 0).
- `assert_invariantes_sabor()` ejecutable en tests y shadow mode.

## Correcciones clave

- **Arbitro**: filtra hipotesis fisicamente absurdas antes de contar conflictos.
  - COOKIES D25: PF1 vs PF4, PF4 descartada por incoherencia (venta=-5570g).
- **Apertura real**: se genera por conteo de cerradas (`n_cerr_a > n_cerr_b`),
  no solo por rise de abierta. Resuelve D. GRANIZADO y PISTACHO D28.
- **PF1 offsets**: centena (100-300g) ademas de millar (1000-2000g).
- **Desempate**: coherencia > confianza > especificidad (PF1 prioriza).

## Validacion

- 27 tests, 0 failed, 0 xfailed.
- D5: operativo=33,745g
- D25: operativo=19,745g (match exacto con PDF resuelto)
- D27: operativo=32,720g
- D28: operativo=63,885g, 0 sin resolver

## Interfaces

- CLI: `python -m pesaje_v3.pipeline <xlsx> <dia>`
- Web: `python -m pesaje_v3.web` (localhost:5001)

## Pendientes declarados

- Parser Union (turno unico, sin DIA/NOCHE).
- VDP no capturado en algunos dias (D27 spec=250g, sistema=0g).
- Capa 5 residual: solo diagnostica, no reabre casos.
- Exporter multi-dia: funcional pero sin trazabilidad por sabor.
