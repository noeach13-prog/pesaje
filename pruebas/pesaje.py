"""
pesaje.py — Entry point for the Heladería San Martín sales analysis system.

Usage:
    python pesaje.py <input.xlsx> [output.xlsx]

If output path is omitted, it is derived from the input filename:
    Marzo_SanMartin_2026.xlsx → Comparativa_Ventas_Marzo_SanMartin_2026.xlsx
"""
import sys
import os
from pathlib import Path

from parser import load_shifts
from reconciler import reconcile_shifts
from calculator import calculate_periods
from exporter import export


def main():
    if len(sys.argv) < 2:
        print("Uso: python pesaje.py <archivo_entrada.xlsx> [archivo_salida.xlsx]")
        sys.exit(1)

    input_path = sys.argv[1]
    if not os.path.exists(input_path):
        print(f"Error: no se encontró el archivo '{input_path}'")
        sys.exit(1)

    if len(sys.argv) >= 3:
        output_path = sys.argv[2]
    else:
        stem = Path(input_path).stem
        parent = Path(input_path).parent
        output_path = str(parent / f"Comparativa_Ventas_{stem}.xlsx")

    print(f"Leyendo: {input_path}")
    shifts = load_shifts(input_path)

    if not shifts:
        print("Error: no se encontraron hojas válidas (A1='SABORES') en el archivo.")
        sys.exit(1)

    print(f"  {len(shifts)} turnos válidos encontrados:")
    for s in shifts:
        n_flavors = len(s.flavors)
        n_ventas  = len(s.ventas_sin_peso)
        n_consumos = len(s.consumos)
        print(f"    [{s.index:02d}] {s.name:<35} {n_flavors:2d} sabores  "
              f"{n_ventas:2d} ventas  {n_consumos:2d} consumos")

    # Filter out empty shifts (template sheets with no data)
    empty = [s.name for s in shifts if not s.is_valid]
    if empty:
        print(f"  Hojas vacias ignoradas: {', '.join(empty)}")
    shifts = [s for s in shifts if s.is_valid]

    print(f"\nReconciliando stock a través de turnos...")
    reconciled_shifts = reconcile_shifts(shifts)
    shifts = [rs.to_shift_data() for rs in reconciled_shifts]

    print(f"\nCalculando {len(shifts)-1} periodos con datos reconciliados...")
    periods = calculate_periods(shifts)

    total_anomalies = sum(
        len(res.anomalies)
        for p in periods
        for res in p.flavors.values()
    )
    print(f"  {total_anomalies} anomalías detectadas.")

    print(f"\nGenerando: {output_path}")
    export(periods, output_path)

    print("\nResumen de anomalias por periodo:")
    for p in periods:
        anom_in_period = [
            (fname, a)
            for fname, res in p.flavors.items()
            for a in res.anomalies
        ]
        if anom_in_period:
            print(f"\n  {p.turno_a_name} -> {p.turno_b_name}:")
            for fname, a in anom_in_period:
                sev = "[!]" if a.severity == 'error' else "[ ]"
                msg = a.message.encode('ascii', errors='replace').decode('ascii')
                print(f"    {sev} T{a.tipo} {fname}: {msg[:80]}")


if __name__ == "__main__":
    main()
