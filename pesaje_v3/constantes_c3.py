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
VENTA_NEG_THRESHOLD = -50         # C1: raw por debajo -> flag NEG
VENTA_HIGH_THRESHOLD = 5000       # C2: raw por encima sin apertura -> flag HIGH

# === Constantes fisicas ===
TARA_LATA = 280                   # peso de la tapa, se descuenta al abrir

# === PF1: Error de digito ===
PF1_OFFSETS = [300, -300, 1000, -1000, 2000, -2000]
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

# === Arbitraje ===
CONFIANZA_MINIMA_FUERTE = 0.85
CONFIANZA_MINIMA_VIABLE = 0.70

# === Calidad ===
CALIDAD_PENALIZACION_COPIA_FUERTE = 0.15
