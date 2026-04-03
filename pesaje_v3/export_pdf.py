"""
export_pdf.py -Genera reporte PDF del analisis mensual.

Pagina 1: Resumen mensual (tabla de dias)
Paginas 2+: Una pagina por dia con detalle de casos no limpios
"""
from fpdf import FPDF
from typing import List, Tuple, Optional
from datetime import datetime


def _safe(text: str) -> str:
    """Sanitiza texto para Helvetica (Latin-1). Reemplaza caracteres fuera de rango."""
    if not text:
        return text
    out = []
    for ch in text:
        try:
            ch.encode('latin-1')
            out.append(ch)
        except UnicodeEncodeError:
            # Reemplazos conocidos
            _MAP = {
                '\u2248': '~',   # ≈
                '\u2264': '<=',  # ≤
                '\u2265': '>=',  # ≥
                '\u2192': '->',  # →
                '\u2190': '<-',  # ←
                '\u2194': '<->', # ↔
                '\u00b1': '+-',  # ±
                '\u2713': 'OK',  # ✓
                '\u26a0': '!',   # ⚠
                '\u26aa': '?',   # ⚪
                '\u2b1c': '-',   # ⬜
            }
            out.append(_MAP.get(ch, '?'))
    return ''.join(out)


class ReportePDF(FPDF):
    """PDF con header/footer corporativo."""

    def __init__(self, titulo_workbook: str):
        super().__init__(orientation='L', unit='mm', format='A4')
        self.titulo_workbook = titulo_workbook
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        self.set_font('Helvetica', 'B', 9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 5, f'Pesaje v3 -{self.titulo_workbook}', ln=True, align='L')
        self.set_draw_color(200, 200, 200)
        self.line(10, self.get_y(), self.w - 10, self.get_y())
        self.ln(2)

    def footer(self):
        self.set_y(-12)
        self.set_font('Helvetica', '', 7)
        self.set_text_color(150, 150, 150)
        self.cell(0, 5, f'Generado {datetime.now().strftime("%d/%m/%Y %H:%M")}', align='L')
        self.cell(0, 5, f'Pagina {self.page_no()}/{{nb}}', align='R')


# ═══════════════════════════════════════════════════════════════
# Colores
# ═══════════════════════════════════════════════════════════════

_HEADER_BG = (30, 58, 95)      # azul oscuro
_HEADER_FG = (255, 255, 255)
_ROW_EVEN = (248, 250, 252)
_ROW_ODD = (255, 255, 255)
_ALERT_BG = (255, 243, 224)    # naranja claro
_TOTAL_BG = (30, 58, 95)
_TOTAL_FG = (255, 255, 255)
_GREEN = (46, 125, 50)
_RED = (198, 40, 40)
_ORANGE = (230, 81, 0)
_BLUE = (21, 101, 192)
_GRAY = (120, 120, 120)


def _fmt(n, sep=True):
    """Formatea numero con separador de miles."""
    if n is None:
        return '-'
    if isinstance(n, float):
        return f'{n:,.0f}'.replace(',', '.')
    return f'{n:,}'.replace(',', '.')


# ═══════════════════════════════════════════════════════════════
# PAGINA 1: Resumen mensual
# ═══════════════════════════════════════════════════════════════

def _pagina_resumen(pdf: ReportePDF, dias_data: list):
    """Tabla resumen: una fila por dia."""
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_text_color(30, 58, 95)
    pdf.cell(0, 10, 'Resumen Mensual de Ventas', ln=True, align='C')
    pdf.ln(3)

    # Columnas: Dia | RAW | Confirmado | Operativo | Refinada | VDP | Latas | Corr | H0
    cols = [
        ('Dia', 18),
        ('RAW', 28),
        ('Confirmado', 28),
        ('Operativo', 28),
        ('Refinada', 28),
        ('VDP', 22),
        ('Latas', 16),
        ('Corr', 16),
        ('H0', 14),
        ('Notas', 75),
    ]
    total_w = sum(w for _, w in cols)
    x_start = (pdf.w - total_w) / 2

    # Header
    pdf.set_x(x_start)
    pdf.set_font('Helvetica', 'B', 7)
    pdf.set_fill_color(*_HEADER_BG)
    pdf.set_text_color(*_HEADER_FG)
    for name, w in cols:
        align = 'L' if name in ('Dia', 'Notas') else 'R'
        pdf.cell(w, 6, name, border=0, fill=True, align=align)
    pdf.ln()

    # Filas
    pdf.set_font('Helvetica', '', 7)
    totals = {'raw': 0, 'conf': 0, 'op': 0, 'ref': 0, 'vdp': 0, 'latas': 0, 'corr': 0, 'h0': 0}

    for i, d in enumerate(dias_data):
        bg = _ROW_EVEN if i % 2 == 0 else _ROW_ODD
        if d['h0'] > 3:
            bg = _ALERT_BG
        pdf.set_fill_color(*bg)
        pdf.set_text_color(30, 30, 30)
        pdf.set_x(x_start)

        vals = [
            ('L', f"D{d['label']}"),
            ('R', _fmt(d['raw'])),
            ('R', _fmt(d['conf'])),
            ('R', _fmt(d['op'])),
            ('R', _fmt(d['ref'])),
            ('R', _fmt(d['vdp'])),
            ('R', str(d['latas'])),
            ('R', str(d['corr'])),
            ('R', str(d['h0'])),
            ('L', _safe(d.get('notas', ''))),
        ]
        for (align, val), (_, w) in zip(vals, cols):
            pdf.cell(w, 5, val, border=0, fill=True, align=align)
        pdf.ln()

        totals['raw'] += d['raw']
        totals['conf'] += d['conf']
        totals['op'] += d['op']
        totals['ref'] += d['ref']
        totals['vdp'] += d['vdp']
        totals['latas'] += d['latas']
        totals['corr'] += d['corr']
        totals['h0'] += d['h0']

    # Fila total
    pdf.set_x(x_start)
    pdf.set_font('Helvetica', 'B', 7)
    pdf.set_fill_color(*_TOTAL_BG)
    pdf.set_text_color(*_TOTAL_FG)
    total_vals = [
        ('L', 'TOTAL'),
        ('R', _fmt(totals['raw'])),
        ('R', _fmt(totals['conf'])),
        ('R', _fmt(totals['op'])),
        ('R', _fmt(totals['ref'])),
        ('R', _fmt(totals['vdp'])),
        ('R', str(totals['latas'])),
        ('R', str(totals['corr'])),
        ('R', str(totals['h0'])),
        ('L', ''),
    ]
    for (align, val), (_, w) in zip(total_vals, cols):
        pdf.cell(w, 6, val, border=0, fill=True, align=align)
    pdf.ln()

    # Leyenda
    pdf.ln(5)
    pdf.set_text_color(*_GRAY)
    pdf.set_font('Helvetica', '', 6)
    pdf.cell(0, 4, 'RAW = formula pura sin correccion | Confirmado = RAW + correcciones tipo A (2+ planos) | '
                    'Operativo = Confirmado + tipo B (forzado) | Refinada = Operativo + tipo D (estimado)', ln=True, align='C')
    pdf.cell(0, 4, 'VDP = ventas de postres sin peso | Latas = aperturas detectadas | '
                    'Corr = correcciones aplicadas | H0 = casos sin resolver', ln=True, align='C')


# ═══════════════════════════════════════════════════════════════
# PAGINA POR DIA: Detalle de no-limpios
# ═══════════════════════════════════════════════════════════════

def _pagina_dia(pdf: ReportePDF, dia_data: dict):
    """Una pagina por dia con casos no limpios."""
    pdf.add_page()

    # Titulo
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(30, 58, 95)
    pdf.cell(0, 8, f"Dia {dia_data['label']} -Detalle de Analisis", ln=True, align='L')

    # Resumen del dia
    pdf.set_font('Helvetica', '', 8)
    pdf.set_text_color(60, 60, 60)
    r = dia_data
    pdf.cell(0, 5,
             f"RAW: {_fmt(r['raw'])}g  |  Refinada: {_fmt(r['ref'])}g  |  "
             f"VDP: {_fmt(r['vdp'])}g  |  Latas: {r['latas']}  |  "
             f"Correcciones: {r['corr']}  |  Sin resolver: {r['h0']}",
             ln=True)
    pdf.ln(3)

    casos = dia_data.get('casos_no_limpios', [])
    if not casos:
        pdf.set_font('Helvetica', 'I', 9)
        pdf.set_text_color(*_GREEN)
        pdf.cell(0, 8, 'Todos los sabores son LIMPIO -sin anomalias detectadas.', ln=True, align='C')
        return

    # Tabla de casos
    cols = [
        ('Sabor', 38),
        ('Status', 22),
        ('RAW', 22),
        ('Corregida', 22),
        ('Delta', 22),
        ('Banda', 22),
        ('Conf', 16),
        ('Nota', 110),
    ]
    total_w = sum(w for _, w in cols)
    x_start = (pdf.w - total_w) / 2

    # Header
    pdf.set_x(x_start)
    pdf.set_font('Helvetica', 'B', 6.5)
    pdf.set_fill_color(*_HEADER_BG)
    pdf.set_text_color(*_HEADER_FG)
    for name, w in cols:
        align = 'L' if name in ('Sabor', 'Nota') else 'R'
        if name == 'Status':
            align = 'C'
        pdf.cell(w, 5, name, border=0, fill=True, align=align)
    pdf.ln()

    # Filas
    pdf.set_font('Helvetica', '', 6.5)
    for i, caso in enumerate(casos):
        bg = _ROW_EVEN if i % 2 == 0 else _ROW_ODD

        # Color de status
        status = caso.get('status', '')
        if 'H0' in status:
            bg = _ALERT_BG

        pdf.set_fill_color(*bg)
        pdf.set_text_color(30, 30, 30)
        pdf.set_x(x_start)

        raw_val = caso.get('raw', 0)
        corr_val = caso.get('corregida')
        delta = caso.get('delta')
        banda = caso.get('banda', '')
        conf = caso.get('confianza')
        nota = _safe(caso.get('nota', ''))

        # Color del delta
        delta_str = f"{delta:+,}".replace(',', '.') if delta is not None and delta != 0 else '-'
        corr_str = _fmt(corr_val) if corr_val is not None else '-'
        conf_str = f"{conf:.0%}" if conf is not None else '-'

        vals = [
            ('L', _safe(caso.get('sabor', ''))),
            ('C', _safe(status)),
            ('R', _fmt(raw_val)),
            ('R', corr_str),
            ('R', delta_str),
            ('C', banda),
            ('R', conf_str),
            ('L', nota[:75]),
        ]

        for (align, val), (_, w) in zip(vals, cols):
            pdf.cell(w, 5, val, border=0, fill=True, align=align)
        pdf.ln()

        # Si la nota es larga, segunda linea
        if len(nota) > 75:
            pdf.set_x(x_start)
            pdf.set_font('Helvetica', 'I', 5.5)
            pdf.set_text_color(*_GRAY)
            pdf.cell(total_w, 4, f'  {nota[75:150]}', fill=True, align='L')
            pdf.ln()
            pdf.set_font('Helvetica', '', 6.5)

    # Pie del dia
    pdf.ln(3)
    total_delta = sum(c.get('delta', 0) or 0 for c in casos)
    n_confirmado = sum(1 for c in casos if c.get('banda') == 'CONFIRMADO')
    n_estimado = sum(1 for c in casos if c.get('banda') == 'ESTIMADO')
    n_h0 = sum(1 for c in casos if 'H0' in c.get('status', ''))

    pdf.set_font('Helvetica', '', 7)
    pdf.set_text_color(*_GRAY)
    resumen = f"Total delta: {total_delta:+,}g".replace(',', '.')
    if n_confirmado:
        resumen += f"  |  {n_confirmado} CONFIRMADO"
    if n_estimado:
        resumen += f"  |  {n_estimado} ESTIMADO"
    if n_h0:
        resumen += f"  |  {n_h0} SIN RESOLVER"
    pdf.cell(0, 4, resumen, ln=True, align='C')


# ═══════════════════════════════════════════════════════════════
# FUNCION PRINCIPAL
# ═══════════════════════════════════════════════════════════════

def generar_pdf_desde_resultados(resultados: list, titulo: str, path_salida: str):
    """
    Genera el PDF a partir de resultados ya calculados por el pipeline.
    Evita correr el pipeline dos veces (una en web.py y otra aqui).

    resultados: lista de (datos, cont, c3, c4, resultado) igual que en cli.py
    titulo: nombre del workbook para el header del PDF
    """
    from pesaje_v3.modelos import StatusC3, Banda

    dias_data = []
    for datos, cont, c3, c4, r in resultados:
        casos_no_limpios = []
        c4_map = {c.nombre_norm: c for c in c4.correcciones}

        for nombre in sorted(cont.sabores.keys()):
            s3 = c3.sabores.get(nombre)
            if not s3 or s3.status == StatusC3.LIMPIO:
                continue

            sc = cont.sabores[nombre]
            c4c = c4_map.get(nombre)
            is_h0 = nombre in c4.sin_resolver

            caso = {
                'sabor': nombre,
                'raw': sc.venta_raw,
                'status': '',
                'corregida': None,
                'delta': None,
                'banda': '',
                'confianza': None,
                'nota': '',
            }

            if s3.status == StatusC3.ENGINE:
                caso['status'] = 'ENGINE'
                caso['corregida'] = s3.venta_final_c3
                if c4c:
                    caso['delta'] = c4c.delta
                    caso['banda'] = c4c.banda.value
                    caso['confianza'] = c4c.confianza
                    caso['nota'] = c4c.motivo[:120]
                else:
                    caso['nota'] = 'Apertura detectada, venta raw valida'
            elif s3.status in (StatusC3.SOLO_DIA, StatusC3.SOLO_NOCHE):
                caso['status'] = s3.status.value
                caso['nota'] = 'Solo un turno presente, venta no calculable'
            elif s3.prototipo:
                caso['status'] = f'C3:{s3.prototipo.codigo}'
                caso['corregida'] = s3.prototipo.venta_corregida
                caso['delta'] = s3.prototipo.delta
                caso['confianza'] = s3.prototipo.confianza
                caso['banda'] = 'CONFIRMADO' if s3.prototipo.confianza >= 0.85 else 'ESTIMADO'
                caso['nota'] = s3.prototipo.descripcion[:120]
            elif c4c:
                caso['status'] = 'C4'
                caso['corregida'] = c4c.venta_corregida
                caso['delta'] = c4c.delta
                caso['banda'] = c4c.banda.value
                caso['confianza'] = c4c.confianza
                caso['nota'] = c4c.motivo[:120]
            elif is_h0:
                caso['status'] = 'H0'
                flags_str = ', '.join(f.codigo for f in s3.flags) if s3.flags else ''
                caso['nota'] = f'Sin resolver. Flags: {flags_str}'
            else:
                caso['status'] = s3.status.value
                caso['nota'] = 'Clasificacion sin resolucion'

            casos_no_limpios.append(caso)

        notas_dia = []
        if r.n_latas > 0:
            notas_dia.append(f'{r.n_latas} latas')
        if len(c4.sin_resolver) > 0:
            notas_dia.append(f'{len(c4.sin_resolver)} H0')

        dias_data.append({
            'label': datos.dia_label,
            'raw': r.venta_raw,
            'conf': r.venta_confirmado,
            'op': r.venta_operativo,
            'ref': r.venta_refinado,
            'vdp': r.vdp,
            'latas': r.n_latas,
            'corr': len(c4.correcciones),
            'h0': len(c4.sin_resolver),
            'notas': ' | '.join(notas_dia),
            'casos_no_limpios': casos_no_limpios,
        })

    pdf = ReportePDF(titulo)
    pdf.alias_nb_pages()
    _pagina_resumen(pdf, dias_data)
    for dia in dias_data:
        _pagina_dia(pdf, dia)
    pdf.output(path_salida)
    return path_salida


def generar_pdf(path_excel: str, path_salida: str):
    """Corre el pipeline completo y genera el PDF."""
    import os
    from pathlib import Path
    from pesaje_v3.capa1_parser import cargar_todos_los_dias
    from pesaje_v3.capa2_contrato import calcular_contabilidad
    from pesaje_v3.capa3_motor import clasificar, canonicalizar_nombres, aplicar_canonicalizacion
    from pesaje_v3.capa4_expediente import resolver_escalados
    from pesaje_v3.capa5_residual import segunda_pasada
    from pesaje_v3.cli import _armar_resultado
    from pesaje_v3.modelos import StatusC3, Banda

    stem = Path(path_excel).stem
    titulo = stem.replace('_', ' ')

    dias_all = cargar_todos_los_dias(path_excel)
    if not dias_all:
        raise ValueError("No se encontraron dias validos.")

    dias_data = []

    for datos in sorted(dias_all, key=lambda d: int(d.dia_label) if d.dia_label.isdigit() else 0):
        canon = canonicalizar_nombres(datos)
        aplicar_canonicalizacion(datos, canon)
        cont = calcular_contabilidad(datos)
        c3 = clasificar(datos, cont)
        c4 = resolver_escalados(datos, cont, c3)
        c5 = segunda_pasada(datos, c3, c4.correcciones, stats={})
        r = _armar_resultado(datos, cont, c3, c4)

        # Construir lista de casos no limpios
        casos_no_limpios = []
        c4_map = {c.nombre_norm: c for c in c4.correcciones}

        for nombre in sorted(cont.sabores.keys()):
            s3 = c3.sabores.get(nombre)
            if not s3:
                continue

            # Solo incluir no-limpios
            if s3.status == StatusC3.LIMPIO:
                continue

            sc = cont.sabores[nombre]
            c4c = c4_map.get(nombre)
            is_h0 = nombre in c4.sin_resolver

            caso = {
                'sabor': nombre,
                'raw': sc.venta_raw,
                'status': '',
                'corregida': None,
                'delta': None,
                'banda': '',
                'confianza': None,
                'nota': '',
            }

            if s3.status == StatusC3.ENGINE:
                caso['status'] = 'ENGINE'
                caso['corregida'] = s3.venta_final_c3
                if c4c:
                    caso['delta'] = c4c.delta
                    caso['banda'] = c4c.banda.value
                    caso['confianza'] = c4c.confianza
                    caso['nota'] = c4c.motivo[:120]
                else:
                    caso['nota'] = 'Apertura detectada, venta raw valida'

            elif s3.status in (StatusC3.SOLO_DIA, StatusC3.SOLO_NOCHE):
                caso['status'] = s3.status.value
                caso['nota'] = 'Solo un turno presente, venta no calculable'

            elif s3.prototipo:
                caso['status'] = f'C3:{s3.prototipo.codigo}'
                caso['corregida'] = s3.prototipo.venta_corregida
                caso['delta'] = s3.prototipo.delta
                caso['confianza'] = s3.prototipo.confianza
                caso['banda'] = 'CONFIRMADO' if s3.prototipo.confianza >= 0.85 else 'ESTIMADO'
                caso['nota'] = s3.prototipo.descripcion[:120]

            elif c4c:
                caso['status'] = 'C4'
                caso['corregida'] = c4c.venta_corregida
                caso['delta'] = c4c.delta
                caso['banda'] = c4c.banda.value
                caso['confianza'] = c4c.confianza
                caso['nota'] = c4c.motivo[:120]

            elif is_h0:
                caso['status'] = 'H0'
                flags_str = ', '.join(f.codigo for f in s3.flags) if s3.flags else ''
                caso['nota'] = f'Sin resolver. Flags: {flags_str}'

            else:
                caso['status'] = s3.status.value
                caso['nota'] = 'Clasificacion sin resolucion'

            casos_no_limpios.append(caso)

        # Notas del dia
        notas_dia = []
        if r.n_latas > 0:
            notas_dia.append(f'{r.n_latas} latas')
        if len(c4.sin_resolver) > 0:
            notas_dia.append(f'{len(c4.sin_resolver)} H0')

        dia_entry = {
            'label': datos.dia_label,
            'raw': r.venta_raw,
            'conf': r.venta_confirmado,
            'op': r.venta_operativo,
            'ref': r.venta_refinado,
            'vdp': r.vdp,
            'latas': r.n_latas,
            'corr': len(c4.correcciones),
            'h0': len(c4.sin_resolver),
            'notas': ' | '.join(notas_dia),
            'casos_no_limpios': casos_no_limpios,
        }
        dias_data.append(dia_entry)

    # Generar PDF
    pdf = ReportePDF(titulo)
    pdf.alias_nb_pages()

    # Pagina 1: Resumen
    _pagina_resumen(pdf, dias_data)

    # Paginas por dia
    for dia in dias_data:
        _pagina_dia(pdf, dia)

    pdf.output(path_salida)
    return path_salida


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("Uso: python -m pesaje_v3.export_pdf <input.xlsx> [output.pdf]")
        sys.exit(1)

    path_in = sys.argv[1]
    path_out = sys.argv[2] if len(sys.argv) > 2 else path_in.replace('.xlsx', '_Reporte.pdf')
    generar_pdf(path_in, path_out)
    print(f"PDF generado: {path_out}")
