"""
exporter_multi.py -- Genera un unico Excel con todos los dias.

Hojas:
  - "Resumen": tabla mensual con una fila por dia
  - "D5", "D27", etc.: detalle de ventas por sabor por dia
  - "Trazabilidad": todas las correcciones de todos los dias
"""
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from .modelos import (
    ResultadoC3, SaborClasificado, StatusC3,
    Correccion, Banda, ResultadoDia,
)
from typing import List, Tuple


# -- Colores --
C_HEADER = "1F4E79"
C_WHITE = "FFFFFF"
C_ALT_ROW = "F2F7FC"
C_CONFIRMADO = "E2EFDA"
C_FORZADO = "FFF2CC"
C_ESTIMADO = "FCE4EC"
C_NEGATIVE = "FFE0B2"
C_ENGINE = "E8F5E9"
C_PF = "E3F2FD"
C_SOLO = "F5F5F5"

BANDA_COLORS = {
    Banda.CONFIRMADO: C_CONFIRMADO,
    Banda.FORZADO: C_FORZADO,
    Banda.ESTIMADO: C_ESTIMADO,
}


def _fill(hex_color):
    return PatternFill("solid", fgColor=hex_color)

def _font(bold=False, color="000000", size=10):
    return Font(bold=bold, color=color, size=size, name="Arial")

def _align(h="center", v="center", wrap=False):
    return Alignment(horizontal=h, vertical=v, wrap_text=wrap)

def _thin_border():
    s = Side(style='thin', color='CCCCCC')
    return Border(left=s, right=s, top=s, bottom=s)

def _set_cell(ws, row, col, value, font=None, fill=None, align=None, border=None):
    cell = ws.cell(row=row, column=col, value=value)
    if font: cell.font = font
    if fill: cell.fill = fill
    if align: cell.alignment = align
    if border: cell.border = border
    return cell


# ===================================================================
# HOJA RESUMEN MENSUAL
# ===================================================================

def _write_resumen_mensual(ws, resultados):
    """Una fila por dia con totales."""
    hdr_font = _font(bold=True, color=C_WHITE)
    hdr_fill = _fill(C_HEADER)
    hdr_align = _align(wrap=True)
    border = _thin_border()

    headers = ['Dia', 'Venta RAW', '+ CONFIRMADO', '+ FORZADO', '+ ESTIMADO',
               'Venta Refinada', 'VDP', 'Latas', 'Lid', 'Total Operativo',
               'LIMPIO', 'ENGINE', 'Escalados', 'Correcciones', 'Sin resolver']
    for col, h in enumerate(headers, 1):
        _set_cell(ws, 1, col, h, hdr_font, hdr_fill, hdr_align, border)

    widths = [8, 12, 12, 10, 10, 12, 8, 6, 8, 14, 8, 8, 10, 12, 12]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    row = 2
    for datos, cont, c3, c4, resultado in resultados:
        vals = [
            f'D{resultado.dia_label}',
            resultado.venta_raw,
            resultado.venta_confirmado - resultado.venta_raw,
            resultado.venta_operativo - resultado.venta_confirmado,
            resultado.venta_refinado - resultado.venta_operativo,
            resultado.venta_refinado,
            resultado.vdp,
            resultado.n_latas,
            resultado.lid_discount,
            resultado.total_operativo,
            resultado.n_limpio,
            resultado.n_engine,
            resultado.n_escalado,
            len(c4.correcciones),
            len(c4.sin_resolver),
        ]
        row_fill = _fill(C_ALT_ROW if row % 2 == 0 else C_WHITE)
        for col, val in enumerate(vals, 1):
            f = _font(bold=(col == 1))
            _set_cell(ws, row, col, val, f, row_fill, _align(), border)
        row += 1

    # Fila totales
    row += 1
    _set_cell(ws, row, 1, 'TOTAL', _font(bold=True, color=C_WHITE), _fill(C_HEADER), _align(), border)
    for col in range(2, 16):
        if col in (8,):  # latas: sumar
            total = sum(r.n_latas for _, _, _, _, r in resultados)
        elif col == 1:
            total = ''
        else:
            # Sumar la columna correspondiente
            vals_col = []
            for datos, cont, c3, c4, resultado in resultados:
                row_vals = [
                    resultado.venta_raw,
                    resultado.venta_confirmado - resultado.venta_raw,
                    resultado.venta_operativo - resultado.venta_confirmado,
                    resultado.venta_refinado - resultado.venta_operativo,
                    resultado.venta_refinado,
                    resultado.vdp,
                    resultado.n_latas,
                    resultado.lid_discount,
                    resultado.total_operativo,
                    resultado.n_limpio,
                    resultado.n_engine,
                    resultado.n_escalado,
                    len(c4.correcciones),
                    len(c4.sin_resolver),
                ]
                vals_col.append(row_vals[col - 2])
            total = sum(vals_col)
        _set_cell(ws, row, col, total, _font(bold=True, color=C_WHITE), _fill(C_HEADER), _align(), border)


# ===================================================================
# HOJA POR DIA
# ===================================================================

def _write_dia(ws, clasificacion, correcciones, resultado):
    """Detalle de ventas por sabor para un dia."""
    corr_map = {c.nombre_norm: c for c in correcciones}
    hdr_font = _font(bold=True, color=C_WHITE)
    hdr_fill = _fill(C_HEADER)
    border = _thin_border()

    headers = ['Sabor', 'Status', 'Raw', 'Delta', 'Final', 'Banda', 'Tipo', 'Conf']
    for col, h in enumerate(headers, 1):
        _set_cell(ws, 1, col, h, hdr_font, hdr_fill, _align(wrap=True), border)

    widths = [22, 12, 10, 10, 10, 14, 8, 8]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    order = {StatusC3.COMPUESTO: 0, StatusC3.SENAL: 1, StatusC3.ESCALAR: 2,
             StatusC3.ENGINE: 3, StatusC3.LIMPIO: 4,
             StatusC3.SOLO_DIA: 5, StatusC3.SOLO_NOCHE: 6}
    sabores_sorted = sorted(clasificacion.sabores.items(),
                            key=lambda x: (order.get(x[1].status, 99), x[0]))

    row = 2
    for nombre, sc in sabores_sorted:
        corr = corr_map.get(nombre)
        raw = sc.contable.venta_raw
        has_proto = sc.prototipo is not None

        if corr:
            vf = corr.venta_corregida
            delta = corr.delta
            banda = corr.banda.value
            tipo = corr.tipo_justificacion.value
            conf = f'{corr.confianza:.0%}'
            row_fill = _fill(BANDA_COLORS.get(corr.banda, C_WHITE))
        elif has_proto:
            vf = sc.prototipo.venta_corregida
            delta = sc.prototipo.delta
            banda = 'PF'
            tipo = sc.prototipo.codigo
            conf = f'{sc.prototipo.confianza:.0%}'
            row_fill = _fill(C_PF)
        elif sc.status in (StatusC3.SOLO_DIA, StatusC3.SOLO_NOCHE):
            vf = 0
            delta = 0
            banda = '-'
            tipo = '-'
            conf = '-'
            row_fill = _fill(C_SOLO)
        elif sc.venta_final_c3 is not None:
            vf = sc.venta_final_c3
            delta = 0
            banda = '-'
            tipo = '-'
            conf = '-'
            row_fill = _fill(C_ENGINE if sc.status == StatusC3.ENGINE else C_WHITE)
        else:
            vf = raw
            delta = 0
            banda = 'H0'
            tipo = '-'
            conf = '-'
            row_fill = _fill(C_NEGATIVE)

        vals = [nombre, sc.status.value, raw, delta, vf, banda, tipo, conf]
        for col, val in enumerate(vals, 1):
            f = _font(bold=(col == 1))
            a = _align(h='left' if col == 1 else 'center')
            _set_cell(ws, row, col, val, f, row_fill, a, border)
        row += 1


# ===================================================================
# HOJA TRAZABILIDAD
# ===================================================================

def _write_trazabilidad_multi(ws, resultados):
    """Todas las correcciones de todos los dias."""
    hdr_font = _font(bold=True, color=C_WHITE)
    hdr_fill = _fill(C_HEADER)
    border = _thin_border()

    headers = ['Dia', 'Sabor', 'Raw', 'Corregida', 'Delta', 'Origen',
               'Tipo/Codigo', 'Banda', 'Conf', 'Motivo']
    for col, h in enumerate(headers, 1):
        _set_cell(ws, 1, col, h, hdr_font, hdr_fill, _align(wrap=True), border)

    widths = [8, 22, 10, 10, 10, 10, 10, 14, 8, 60]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    row = 2
    for datos, cont, c3, c4, resultado in resultados:
        dia = f'D{resultado.dia_label}'

        # Prototipos C3
        for nombre, sc in sorted(c3.sabores.items()):
            if sc.prototipo:
                p = sc.prototipo
                row_fill = _fill(C_PF)
                vals = [dia, nombre, sc.contable.venta_raw, p.venta_corregida, p.delta,
                        'C3', p.codigo, 'PF', f'{p.confianza:.0%}', p.descripcion]
                for col, val in enumerate(vals, 1):
                    _set_cell(ws, row, col, val, _font(), row_fill,
                              _align(h='left' if col >= 10 else 'center', wrap=(col >= 10)), border)
                row += 1

        # Correcciones C4
        for corr in sorted(c4.correcciones, key=lambda c: c.nombre_norm):
            row_fill = _fill(BANDA_COLORS.get(corr.banda, C_WHITE))
            vals = [dia, corr.nombre_norm, corr.venta_raw, corr.venta_corregida, corr.delta,
                    'C4', corr.tipo_justificacion.value, corr.banda.value,
                    f'{corr.confianza:.0%}', corr.motivo]
            for col, val in enumerate(vals, 1):
                _set_cell(ws, row, col, val, _font(), row_fill,
                          _align(h='left' if col >= 10 else 'center', wrap=(col >= 10)), border)
            row += 1


# ===================================================================
# FUNCION PRINCIPAL
# ===================================================================

def exportar_multi(resultados, path_output: str):
    """
    Genera un unico Excel con todos los dias.

    Args:
        resultados: lista de (datos, contabilidad, clasificacion, c4, resultado)
        path_output: ruta del Excel de salida
    """
    wb = openpyxl.Workbook()

    # Hoja 1: Resumen mensual
    ws_resumen = wb.active
    ws_resumen.title = 'Resumen'
    _write_resumen_mensual(ws_resumen, resultados)

    # Una hoja por dia
    for datos, cont, c3, c4, resultado in resultados:
        ws = wb.create_sheet(f'D{resultado.dia_label}')
        _write_dia(ws, c3, c4.correcciones, resultado)

    # Hoja final: Trazabilidad
    ws_traza = wb.create_sheet('Trazabilidad')
    _write_trazabilidad_multi(ws_traza, resultados)

    wb.save(path_output)
    print(f'Exportado: {path_output}')
