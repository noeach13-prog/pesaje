"""Debug: comparar raw del pipeline v3 vs calculo manual d5_desglose.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pesaje_v3.capa1_parser import cargar_dia
from pesaje_v3.capa2_contrato import calcular_contabilidad

EXCEL = r"C:\Users\EliteBook\Downloads\Febrero San Martin 2026 (1).xlsx"

datos = cargar_dia(EXCEL, 5)

# Antes de PF8
print("=== CAPA 1: Sabores en DIA ===")
for n in sorted(datos.turno_dia.sabores.keys()):
    s = datos.turno_dia.sabores[n]
    print(f"  {n:<22} ab={s.abierta}  cerr={s.cerradas}  ent={s.entrantes}")

print(f"\nTotal sabores DIA: {len(datos.turno_dia.sabores)}")

print("\n=== CAPA 1: Sabores en NOCHE ===")
for n in sorted(datos.turno_noche.sabores.keys()):
    s = datos.turno_noche.sabores[n]
    print(f"  {n:<22} ab={s.abierta}  cerr={s.cerradas}  ent={s.entrantes}")

print(f"\nTotal sabores NOCHE: {len(datos.turno_noche.sabores)}")

# Check missing from manual
manual_dia = {
    'CADBURY', 'AMERICANA', 'ANANA', 'B, SPLIT', 'CHOCOLATE', 'AMARGO',
    'BLANCO', 'CH C/ALM', 'CH AMORES', 'DOS CORAZONES', 'CABSHA',
    'COOKIES', 'DULCE C/NUEZ', 'DULCE D LECHE', 'D. GRANIZADO',
    'DULCE AMORES', 'SUPER', 'DURAZNO', 'FERRERO', 'FLAN', 'CEREZA',
    'FRAMBUEZA', 'FRUTILLA CREMA', 'FRUTILLA REINA', 'FRUTILLA AGUA',
    'BOSQUE', 'GRANIZADO', 'LIMON', 'MANTECOL', 'MANZANA', 'MARROC',
    'MASCARPONE', 'MENTA', 'MIX DE FRUTA', 'MOUSSE LIMON', 'SAMBAYON',
    'SAMBAYON AMORES', 'TRAMONTANA', 'TIRAMIZU', 'VAINILLA', 'LEMON PIE',
    'IRLANDESA', 'NUTE', 'RUSA', 'FRANUI', 'CIELO', 'KINDER',
    'MARACUYA', 'PISTACHO', 'CHOCOLATE DUBAI', 'KITKAT', 'COCO'
}

parsed_dia = set(datos.turno_dia.sabores.keys())
print(f"\n=== Diferencias ===")
print(f"En manual pero NO en parser DIA: {manual_dia - parsed_dia}")
print(f"En parser DIA pero NO en manual: {parsed_dia - manual_dia}")

# Aplicar PF8 y recalcular
from pesaje_v3.capa3_motor import _aplicar_pf8
_aplicar_pf8(datos)

contabilidad = calcular_contabilidad(datos)

print(f"\n=== CAPA 2: Ventas raw por sabor ===")
total = 0
for n in sorted(contabilidad.sabores.keys()):
    sc = contabilidad.sabores[n]
    tag = ''
    if sc.solo_dia: tag = ' [SOLO_DIA]'
    elif sc.solo_noche: tag = ' [SOLO_NOCHE]'
    if not sc.solo_dia and not sc.solo_noche:
        total += sc.venta_raw
    print(f"  {n:<22} raw={sc.venta_raw:>8}g  totA={sc.total_a:>6} totB={sc.total_b:>6} newE={sc.new_ent_b:>5} L={sc.n_latas}{tag}")

print(f"\n  TOTAL RAW: {total}g")
print(f"  Esperado:  40095g")
print(f"  Diferencia: {total - 40095}g")
