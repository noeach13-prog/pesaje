"""
cli.py -- Entry point principal del sistema v3.

Uso:
    python -m pesaje_v3.cli archivo.xlsx [output.xlsx]

Procesa todos los dias del workbook. Genera un unico Excel con:
  - Una hoja por dia (ventas por sabor)
  - Hoja resumen mensual
  - Hoja trazabilidad (todas las correcciones)

Imprime en consola una sintesis seca de cada dia.
"""
import sys
import os
import time

from .capa1_parser import cargar_todos_los_dias, _detectar_modo_workbook
from .capa2_contrato import calcular_contabilidad
from .capa3_motor import clasificar, canonicalizar_nombres, aplicar_canonicalizacion
from .capa4_expediente import resolver_escalados
from .capa5_residual import segunda_pasada
from .modelos import StatusC3, Banda, ResultadoDia, ContabilidadDia, ResultadoC3
from .exporter_multi import exportar_multi


def _armar_resultado(datos, contabilidad, clasificacion, c4):
    """Arma ResultadoDia combinando Capas 2-4."""
    corr_map = {c.nombre_norm: c for c in c4.correcciones}
    venta_raw = contabilidad.venta_raw_total

    delta_confirmado = sum(c.delta for c in c4.correcciones if c.banda == Banda.CONFIRMADO)
    delta_forzado = sum(c.delta for c in c4.correcciones if c.banda == Banda.FORZADO)
    delta_estimado = sum(c.delta for c in c4.correcciones if c.banda == Banda.ESTIMADO)

    for sc in clasificacion.sabores.values():
        if sc.prototipo:
            delta_confirmado += sc.prototipo.delta

    venta_confirmado = venta_raw + delta_confirmado
    venta_operativo = venta_confirmado + delta_forzado
    venta_refinado = venta_operativo + delta_estimado

    n_latas = sum(s.n_latas for s in contabilidad.sabores.values())
    lid_discount = n_latas * 280

    n_limpio = sum(1 for s in clasificacion.sabores.values() if s.status == StatusC3.LIMPIO)
    n_engine = sum(1 for s in clasificacion.sabores.values() if s.status == StatusC3.ENGINE)
    n_escalado = len(clasificacion.escalados)
    n_solo = sum(1 for s in clasificacion.sabores.values()
                 if s.status in (StatusC3.SOLO_DIA, StatusC3.SOLO_NOCHE))

    return ResultadoDia(
        dia_label=datos.dia_label,
        venta_raw=venta_raw,
        venta_confirmado=venta_confirmado,
        venta_operativo=venta_operativo,
        venta_refinado=venta_refinado,
        n_latas=n_latas,
        vdp=contabilidad.vdp_total,
        lid_discount=lid_discount,
        correcciones=c4.correcciones,
        n_limpio=n_limpio,
        n_engine=n_engine,
        n_escalado=n_escalado,
        n_solo_dia=n_solo,
    )


def procesar_workbook(path_excel: str, path_output: str = None):
    """Procesa todos los dias del workbook."""
    if path_output is None:
        stem = os.path.splitext(os.path.basename(path_excel))[0]
        path_output = os.path.join(os.path.dirname(path_excel), f'Reporte_{stem}.xlsx')

    t0 = time.time()
    print(f'Cargando {os.path.basename(path_excel)}...')

    # Cargar todos los dias
    todos_los_dias = cargar_todos_los_dias(path_excel)
    print(f'  {len(todos_los_dias)} dias encontrados')
    print()

    # Procesar dia por dia
    resultados = []  # (datos, contabilidad, clasificacion, c4, resultado)

    # Header consola
    print(f'{"DIA":<8} {"RAW":>8} {"REFIN":>8} {"VDP":>6} {"LATAS":>6} {"ESC":>4} {"CORR":>4} {"H0":>4}')
    print('-' * 60)

    for datos in sorted(todos_los_dias, key=lambda d: int(d.dia_label) if d.dia_label.isdigit() else 0):
        # PF8
        canon = canonicalizar_nombres(datos)
        aplicar_canonicalizacion(datos, canon)

        # Capa 2
        contabilidad = calcular_contabilidad(datos)

        # Capa 3
        clasificacion = clasificar(datos, contabilidad)

        # Capa 4
        c4 = resolver_escalados(datos, contabilidad, clasificacion)

        # Capa 5
        c5 = segunda_pasada(datos, clasificacion, c4.correcciones, stats={})

        # Resultado
        resultado = _armar_resultado(datos, contabilidad, clasificacion, c4)

        resultados.append((datos, contabilidad, clasificacion, c4, resultado))

        # Sintesis consola
        n_h0 = len(c4.sin_resolver)
        n_corr = len(c4.correcciones)
        n_esc = resultado.n_escalado
        alertas = []
        if n_h0 > 0:
            alertas.append(f'{n_h0} sin resolver')
        if canon.tiene_colisiones:
            alertas.append('COLISION')
        alerta_str = f'  [{", ".join(alertas)}]' if alertas else ''

        print(f'D{resultado.dia_label:<6} {resultado.venta_raw:>8,} {resultado.venta_refinado:>8,} '
              f'{resultado.vdp:>6,} {resultado.n_latas:>4}({resultado.lid_discount:>4}) '
              f'{n_esc:>4} {n_corr:>4} {n_h0:>4}{alerta_str}')

    # Totales
    print('-' * 60)
    total_raw = sum(r.venta_raw for _, _, _, _, r in resultados)
    total_ref = sum(r.venta_refinado for _, _, _, _, r in resultados)
    total_vdp = sum(r.vdp for _, _, _, _, r in resultados)
    total_latas = sum(r.n_latas for _, _, _, _, r in resultados)
    total_lid = sum(r.lid_discount for _, _, _, _, r in resultados)
    total_corr = sum(len(c4.correcciones) for _, _, _, c4, _ in resultados)
    total_h0 = sum(len(c4.sin_resolver) for _, _, _, c4, _ in resultados)
    print(f'{"TOTAL":<8} {total_raw:>8,} {total_ref:>8,} '
          f'{total_vdp:>6,} {total_latas:>4}({total_lid:>4}) '
          f'{"":>4} {total_corr:>4} {total_h0:>4}')

    # Exportar
    print()
    exportar_multi(resultados, path_output)

    elapsed = time.time() - t0
    print(f'Listo en {elapsed:.1f}s')

    return resultados


def main():
    if len(sys.argv) < 2:
        print('Uso: python -m pesaje_v3.cli <archivo.xlsx> [output.xlsx]')
        print()
        print('Procesa todos los dias del workbook y genera un reporte.')
        sys.exit(1)

    path = sys.argv[1]
    output = sys.argv[2] if len(sys.argv) > 2 else None
    procesar_workbook(path, output)


if __name__ == '__main__':
    main()
