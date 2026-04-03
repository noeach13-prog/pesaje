"""
constantes_c3.py -- Nombres para todos los umbrales de Capa 3.

Cada numero que antes vivia desnudo en capa3_motor.py tiene un nombre aqui.
Los nombres distinguen entre ley fisica, proxy operativo y heuristica local.
"""

# === Proxies operativos (NO leyes fisicas) ===
APERTURA_PROXY_MIN_RISE = 3000    # proxy: ab sube mas que esto -> probable apertura
TOL_SUBA_AB_LEVE = 20             # proxy: ab sube menos que esto -> sin cambio real

# === Tolerancias de matching ===
TOL_MATCH_CERRADA = 30            # +-30g: misma lata cerrada DIA/NOCHE
TOL_MATCH_ENTRANTE = 50           # +-50g: mismo entrante DIA/NOCHE
TOL_PROMO_ENTRANTE = 100          # +-100g: entrante DIA -> cerrada NOCHE (promocion)
TOL_MISMATCH_LEVE = 200           # +-200g: varianza de pesaje, no desaparicion real

# === Umbrales de venta (screening) ===
# Principio: el threshold HIGH debe respetar la unidad temporal real del período.
# DIA_NOCHE  (medio día):  5000g en un turno es anormal → flag.
# TURNO_UNICO (día completo): una lata entera (~6700g) entre días es normal.
# Usar 5000g universal en TURNO_UNICO es una acusación sistemática, no prudencia.
VENTA_NEG_THRESHOLD = -50                    # C1: raw por debajo -> flag NEG
VENTA_HIGH_THRESHOLD_DUAL_SHIFT   = 5000    # C2 DIA_NOCHE:   medio día, 5000g sospechoso
VENTA_HIGH_THRESHOLD_SINGLE_SHIFT = 8000    # C2 TURNO_UNICO: día completo, umbral coherente
VENTA_HIGH_THRESHOLD = VENTA_HIGH_THRESHOLD_DUAL_SHIFT  # alias legacy (no usar en código nuevo)

# === Constantes fisicas ===
TARA_LATA = 280                   # peso de la tapa, se descuenta al abrir

# === PF1: Error de digito ===
# Offsets de error de digito.
# Centenas bajas (100-300): ya incluidas, requieren >=3 sightings
# Centenas altas (400-900): solo con >=5 sightings (mas riesgo de falso positivo)
# Millares (1000-2000): siempre incluidas
PF1_OFFSETS = [300, -300, 1000, -1000, 2000, -2000]
PF1_OFFSETS_CENTENA_ALTA = [400, -400, 500, -500, 600, -600, 700, -700, 800, -800, 900, -900]
PF1_MIN_SIGHTINGS_CENTENA_ALTA = 5
PF1_MIN_SIGHTINGS_STRONG = 5
PF1_MIN_SIGHTINGS_WEAK = 3
PF1_MAX_VAR_WEAK = 30             # varianza maxima para sightings < 5
PF1_CONF_STRONG = 0.92
PF1_CONF_WEAK = 0.85

# === PF2: Entrante duplicado ===
PF2_CONF = 0.90

# === PF3: Phantom RM-3 ===
PF3_CONF = 0.88
PF3_MAX_SIGHTINGS_PHANTOM = 2

# === PF4: Cerrada omitida en NOCHE ===
PF4_MIN_SIGHTINGS = 3
PF4_MIN_SIGHTINGS_NO_FORWARD = 5
PF4_CONF = 0.85
PF4_CONF_WEAK = 0.80

# === PF5: Cerrada omitida en DIA ===
PF5_MIN_SIGHTINGS = 3
PF5_MIN_SIGHTINGS_NO_BACKWARD = 5
PF5_CONF = 0.85
PF5_CONF_WEAK = 0.80

# === PF6: Apertura + phantom ===
PF6_CONF = 0.80
PF6_RISE_COHERENCE_RATIO = 0.60   # rise >= este ratio de total -> no hay phantom
PF6_RISE_MAX_DIFF_RATIO = 0.25    # diff maxima como ratio del rise

# === PF7: Abierta imposible ===
PF7_CONF_FORWARD = 0.88
PF7_CONF_BACKWARD_ONLY = 0.75
PF7_BACKWARD_TOLERANCE = 300      # abs(ab_d - ab_backward) <= esto -> DIA coherente

# === INTRADUP_MASIVO_TURNO: vicio de carga sistematico a nivel planilla ===
# Condicion compuesta: N sabores + Y% del total + peso minimo
# El hallazgo NO absuelve en masa; cambia el estatuto de evidencia de cada PFIT individual.
# "una doctrina buena no absuelve en masa; vuelve mas visible lo que ya era sospechoso."
INTRADUP_MASIVO_MIN_SABORES = 8       # N minimo de sabores con patron intra-turno
INTRADUP_MASIVO_MIN_PCT     = 0.15    # % minimo del total de sabores del turno
INTRADUP_MASIVO_MIN_PESO    = 50_000  # peso total duplicado minimo (g)

# === PFIT: Entrante duplicado intra-turno ===
# Distinto de PF2 (genealogía entrante→cerrada cross-turno).
# PFIT detecta doble registro: mismo can registrado como cerrada Y entrante
# en la MISMA planilla (mismo turno).
PFIT_TOL_INTRA    = 100   # +-100g: match entrante vs cerrada del mismo turno
PFIT_TOL_CONTEXTO = 200   # +-200g: buscar cerrada en turnos adyacentes
PFIT_CONF_FUERTE  = 0.88  # cerrada existía en turno previo (backward confirma)
PFIT_CONF_MEDIA   = 0.72  # cerrada persiste en turno siguiente, previo ambiguo

# === Arbitraje ===
# Definido antes de PFIT_CONF_AMBIGU porque AMBIGU deriva de CONFIANZA_MINIMA_VIABLE.
# Si se sube CONFIANZA_MINIMA_VIABLE, AMBIGU sube con ella — es la intención.
CONFIANZA_MINIMA_FUERTE = 0.85
CONFIANZA_MINIMA_VIABLE = 0.70

# PFIT_CONF_AMBIGU debe derivar de CONFIANZA_MINIMA_VIABLE, no coincidir por casualidad.
# Doctrina: AMBIGU nace exactamente en el piso viable.
# - Por debajo: el árbitro la descartaría silenciosamente (falla invisible).
# - Por encima del piso pero por debajo de FUERTE: garantiza CORREGIDO_C3_BAJA_CONFIANZA.
# Si CONFIANZA_MINIMA_VIABLE cambia, AMBIGU cambia con ella conscientemente.
PFIT_CONF_AMBIGU = CONFIANZA_MINIMA_VIABLE

# === Calidad ===
CALIDAD_PENALIZACION_COPIA_FUERTE = 0.15
