"""
web.py -- App web para el sistema de pesaje v3.

Uso:
    python -m pesaje_v3.web
    Abrir http://localhost:5000

Arrastra una planilla .xlsx y descarga el reporte analizado.
"""
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, render_template_string, send_file

from datetime import timedelta

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'pesaje-dev-key-cambiar-en-prod')
app.permanent_session_lifetime = timedelta(days=30)  # sesion dura 30 dias
_outputs: dict = {}

# Version del deploy actual. Se usa para que el frontend detecte cuando hay
# una version nueva disponible y avise al operario sin imponer reload.
# Prioridad de fuente: variable de entorno (Railway) > timestamp del archivo.
def _compute_deploy_version():
    v = os.environ.get('RAILWAY_DEPLOYMENT_ID') or os.environ.get('GIT_SHA') or os.environ.get('SOURCE_VERSION')
    if v:
        return v[:12]
    try:
        return str(int(os.path.getmtime(__file__)))
    except Exception:
        return 'unknown'

DEPLOY_VERSION = _compute_deploy_version()


@app.route('/version')
def version_endpoint():
    """Devuelve la version del deploy actual. El frontend la consulta
    cada N minutos y si difiere de la que recibio al cargar la pagina,
    levanta una bandera interna para sugerir actualizar al operario
    en el proximo momento seguro (post save exitoso, no antes)."""
    from flask import jsonify
    return jsonify({'v': DEPLOY_VERSION})

# Logging de errores a stderr (visible en Railway logs)
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

def _backup_once():
    """Registra snapshot de conteo en _backups si no se hizo hoy."""
    from pesaje_v3.db import get_db, _is_postgres
    if not _is_postgres():
        return
    try:
        db = get_db()
        try:
            db.execute("""CREATE TABLE IF NOT EXISTS _backups (
                id %s, fecha TEXT NOT NULL UNIQUE, n_turnos INTEGER, n_sabores INTEGER,
                status TEXT, created_at TEXT NOT NULL DEFAULT %s
            )""" % ('SERIAL PRIMARY KEY' if db.is_pg else 'INTEGER PRIMARY KEY',
                    'CURRENT_TIMESTAMP' if db.is_pg else "(datetime('now'))"))
            db.commit()
        except Exception:
            try: db._conn.rollback()
            except: pass

        from datetime import date
        hoy = date.today().isoformat()
        row = db.execute("SELECT 1 FROM _backups WHERE fecha = ?", (hoy,)).fetchone()
        if row:
            db.close()
            return

        r1 = db.execute("SELECT COUNT(*) as n FROM turnos").fetchone()
        n_turnos = r1['n'] if isinstance(r1, dict) else r1[0]
        r2 = db.execute("SELECT COUNT(*) as n FROM sabores_turno").fetchone()
        n_sabores = r2['n'] if isinstance(r2, dict) else r2[0]

        # Health self-check
        status = 'ok'
        try:
            r3 = db.execute("SELECT COUNT(DISTINCT sucursal_id) as n FROM turnos").fetchone()
            n_sucs = r3['n'] if isinstance(r3, dict) else r3[0]
            if n_sucs == 0:
                status = 'warn:no_turnos'
        except Exception:
            status = 'error:health_check_failed'

        db.execute("INSERT INTO _backups (fecha, n_turnos, n_sabores, status) VALUES (?, ?, ?, ?)",
                   (hoy, n_turnos, n_sabores, status))
        db.commit()
        db.close()
        logging.info(f'[BACKUP] {hoy}: {n_turnos} turnos, {n_sabores} sabores, status={status}')
    except Exception as e:
        logging.error(f'[BACKUP] FAILED: {e}')


def _start_daily_tasks():
    """Inicia thread daemon que ejecuta backup + self-check cada 12 horas.
    No depende de restarts: corre mientras el proceso viva."""
    import threading

    def _loop():
        import time
        while True:
            try:
                _backup_once()
            except Exception as e:
                logging.error(f'[DAILY] Error: {e}')
            time.sleep(43200)  # 12 horas

    t = threading.Thread(target=_loop, daemon=True)
    t.start()
    logging.info('[DAILY] Background backup/health thread started (every 12h)')


# --- Blueprint de carga manual ---
from pesaje_v3.web_entrada import entrada_bp
from pesaje_v3.db import init_db
app.register_blueprint(entrada_bp)
init_db()
logging.info('Pesaje app initialized')

# Backup + self-check: una vez al arrancar + thread cada 12h
_backup_once()
_start_daily_tasks()



@app.teardown_appcontext
def _close_db(exc):
    """Cierra conexiones DB abiertas durante el request."""
    pass  # get_db() crea conexiones locales que se cierran en cada endpoint


# ─── Health check + backup endpoint ────────────────────────────────

@app.route('/health')
def health():
    """Health check para monitoreo. Verifica DB, turnos, errores."""
    from pesaje_v3.db import get_db
    import traceback
    status = {'status': 'ok', 'checks': {}}
    try:
        db = get_db()
        # DB connection
        row = db.execute("SELECT COUNT(*) as n FROM turnos").fetchone()
        n = row['n'] if isinstance(row, dict) else row[0]
        status['checks']['db'] = 'ok'
        status['checks']['turnos'] = n

        # Sucursales
        row2 = db.execute("SELECT COUNT(*) as n FROM sucursales").fetchone()
        status['checks']['sucursales'] = row2['n'] if isinstance(row2, dict) else row2[0]

        # Turnos por sucursal
        rows = db.execute(
            """SELECT s.nombre, COUNT(t.id) as n,
                      SUM(CASE WHEN t.estado='confirmado' THEN 1 ELSE 0 END) as conf
               FROM sucursales s LEFT JOIN turnos t ON s.id = t.sucursal_id
               GROUP BY s.nombre ORDER BY s.nombre"""
        ).fetchall()
        status['checks']['por_sucursal'] = {r['nombre']: {'total': r['n'], 'confirmados': r['conf']} for r in rows}

        # Ultimo turno
        ult = db.execute("SELECT fecha, tipo_turno, estado FROM turnos ORDER BY fecha DESC, id DESC LIMIT 1").fetchone()
        if ult:
            status['checks']['ultimo_turno'] = dict(ult)

        # Postgres o SQLite
        status['checks']['engine'] = 'postgres' if db.is_pg else 'sqlite'

        # Ultimo backup
        try:
            bk = db.execute("SELECT fecha, n_turnos, n_sabores, status, created_at FROM _backups ORDER BY fecha DESC LIMIT 1").fetchone()
            if bk:
                status['checks']['ultimo_backup'] = dict(bk)
                # Alertar si el backup tiene mas de 2 dias
                from datetime import date, timedelta
                bk_date = date.fromisoformat(bk['fecha'])
                if (date.today() - bk_date).days > 2:
                    status['status'] = 'warn'
                    status['checks']['backup_alerta'] = f'Ultimo backup hace {(date.today() - bk_date).days} dias'
        except Exception:
            pass  # tabla puede no existir

        db.close()
    except Exception as e:
        status['status'] = 'error'
        status['checks']['db'] = f'ERROR: {str(e)[:200]}'
        status['error'] = traceback.format_exc()[-500:]

    from flask import jsonify
    code = 200 if status['status'] == 'ok' else 500
    return jsonify(status), code


@app.route('/backup')
def backup():
    """Descarga un dump SQL de la DB (solo Postgres). Protegido por query param."""
    from flask import request, jsonify, Response
    key = request.args.get('key', '')
    if key != 'tolentinos2512':
        return jsonify({'error': 'Unauthorized'}), 403

    from pesaje_v3.db import get_db, _is_postgres
    if not _is_postgres():
        return jsonify({'error': 'Backup only available on Postgres'}), 400

    db = get_db()
    try:
        tables = ['sucursales', 'turnos', 'sabores_turno', 'vdp_turno',
                  'consumo_turno', 'notas_turno', 'postres_turno',
                  'ajustes_manuales', 'log_actividad', 'stock_insumos',
                  'catalogo_sabores']

        lines = ['-- Backup Pesaje Tolentinos']
        lines.append(f'-- Generated: {__import__("datetime").datetime.utcnow().isoformat()}')
        lines.append('')

        for table in tables:
            try:
                rows = db.execute(f"SELECT * FROM {table}").fetchall()
                if not rows:
                    continue
                cols = list(rows[0].keys())
                lines.append(f'-- {table}: {len(rows)} rows')
                for row in rows:
                    vals = []
                    for c in cols:
                        v = row[c]
                        if v is None:
                            vals.append('NULL')
                        elif isinstance(v, (int, float)):
                            vals.append(str(v))
                        else:
                            vals.append("'" + str(v).replace("'", "''") + "'")
                    lines.append(f"INSERT INTO {table} ({','.join(cols)}) VALUES ({','.join(vals)});")
                lines.append('')
            except Exception:
                lines.append(f'-- ERROR reading {table}')
                continue

        db.close()

        content = '\n'.join(lines)
        return Response(
            content,
            mimetype='text/sql',
            headers={'Content-Disposition': f'attachment; filename=backup_pesaje_{__import__("datetime").date.today().isoformat()}.sql'}
        )
    except Exception as e:
        db.close()
        return jsonify({'error': str(e)[:200]}), 500


def _procesar(path_in: str, filename: str):
    """Corre el pipeline v3 sobre el archivo y retorna stats + path de salida."""
    from pesaje_v3.capa1_parser import cargar_todos_los_dias
    from pesaje_v3.capa2_contrato import calcular_contabilidad
    from pesaje_v3.capa3_motor import clasificar, canonicalizar_nombres, aplicar_canonicalizacion
    from pesaje_v3.capa4_expediente import resolver_escalados
    from pesaje_v3.capa5_residual import segunda_pasada
    from pesaje_v3.modelos import StatusC3, Banda
    from pesaje_v3.exporter_multi import exportar_multi

    dias = cargar_todos_los_dias(path_in)
    if not dias:
        raise ValueError("No se encontraron dias validos en el workbook.")

    resultados = []
    for datos in sorted(dias, key=lambda d: int(d.dia_label) if d.dia_label.isdigit() else 0):
        canon = canonicalizar_nombres(datos)
        aplicar_canonicalizacion(datos, canon)
        cont = calcular_contabilidad(datos)
        c3 = clasificar(datos, cont)
        c4 = resolver_escalados(datos, cont, c3)
        c5 = segunda_pasada(datos, c3, c4.correcciones, stats={})

        # Armar resultado
        from pesaje_v3.cli import _armar_resultado
        resultado = _armar_resultado(datos, cont, c3, c4)
        resultados.append((datos, cont, c3, c4, resultado))

    # Exportar Excel
    stem = Path(filename).stem
    output_name = f"Reporte_{stem}.xlsx"
    tmp_out = os.path.join(tempfile.gettempdir(), output_name)
    exportar_multi(resultados, tmp_out)

    # Exportar PDF (reusar resultados ya calculados, sin volver a correr el pipeline)
    from pesaje_v3.export_pdf import generar_pdf_desde_resultados
    pdf_name = f"Reporte_{stem}.pdf"
    pdf_path = os.path.join(tempfile.gettempdir(), pdf_name)
    generar_pdf_desde_resultados(resultados, stem, pdf_path)

    # Stats
    total_dias = len(resultados)
    total_corr = sum(len(c4.correcciones) for _, _, _, c4, _ in resultados)
    total_h0 = sum(len(c4.sin_resolver) for _, _, _, c4, _ in resultados)
    total_raw = sum(r.venta_raw for _, _, _, _, r in resultados)
    total_ref = sum(r.venta_refinado for _, _, _, _, r in resultados)
    total_vdp = sum(r.vdp for _, _, _, _, r in resultados)
    total_latas = sum(r.n_latas for _, _, _, _, r in resultados)
    total_final = sum(r.total_refinado for _, _, _, _, r in resultados)

    return {
        'output_name': output_name,
        'output_path': tmp_out,
        'pdf_name': pdf_name,
        'pdf_path': pdf_path,
        'n_dias': total_dias,
        'n_correcciones': total_corr,
        'n_sin_resolver': total_h0,
        'total_raw': total_raw,
        'total_refinada': total_ref,
        'total_vdp': total_vdp,
        'total_latas': total_latas,
        'total_final': total_final,
        'dias': [{
            'label': f'D{r.dia_label}',
            'raw': r.venta_raw,
            'refinada': r.venta_refinado,
            'total': r.total_refinado,
            'vdp': r.vdp,
            'latas': r.n_latas,
            'corr': len(c4.correcciones),
            'h0': len(c4.sin_resolver),
        } for _, _, _, c4, r in resultados],
    }


_PAGE = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Pesaje v3</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #f5f7fa; color: #1a1a2e; min-height: 100vh;
      display: flex; align-items: flex-start; justify-content: center;
      padding: 32px 16px;
    }
    .card {
      background: #fff; border-radius: 12px;
      box-shadow: 0 4px 24px rgba(0,0,0,.08);
      padding: 36px; width: 100%; max-width: 720px;
    }
    h1 { font-size: 1.4rem; font-weight: 700; color: #1e3a5f; margin-bottom: 4px; }
    .sub { color: #666; font-size: .85rem; margin-bottom: 28px; }
    .drop-zone {
      border: 2px dashed #c0cfe0; border-radius: 8px;
      padding: 40px 24px; text-align: center;
      cursor: pointer; transition: all .2s;
      margin-bottom: 16px; position: relative;
    }
    .drop-zone.drag-over { border-color: #2e7dd1; background: #f0f6ff; transform: scale(1.01); }
    .drop-zone:hover { border-color: #2e7dd1; background: #f0f6ff; }
    .drop-zone input[type=file] { display: none; }
    .drop-zone .icon { font-size: 2.2rem; margin-bottom: 6px; }
    .drop-zone .label { font-size: .9rem; color: #555; }
    .drop-zone .chosen { font-size: .85rem; color: #2e7dd1; font-weight: 600;
                         margin-top: 6px; word-break: break-all; }
    .btn {
      display: block; width: 100%; padding: 12px;
      background: #2e7dd1; color: #fff; border: none;
      border-radius: 8px; font-size: .95rem; font-weight: 600;
      cursor: pointer; transition: background .2s;
    }
    .btn:hover { background: #1d5fa3; }
    .btn:disabled { background: #9ab8d9; cursor: not-allowed; }
    .result {
      margin-top: 24px; padding: 20px; border-radius: 8px;
      background: #f0f9f0; border-left: 4px solid #4caf50;
    }
    .result h2 { font-size: 1rem; color: #2e7a35; margin-bottom: 12px; }
    .stats { display: flex; gap: 12px; margin-bottom: 14px; flex-wrap: wrap; }
    .stat-box {
      flex: 1; min-width: 80px; background: #fff; border-radius: 6px;
      padding: 10px; text-align: center;
      box-shadow: 0 1px 4px rgba(0,0,0,.07);
    }
    .stat-box .num { font-size: 1.3rem; font-weight: 700; color: #1e3a5f; }
    .stat-box .lbl { font-size: .7rem; color: #888; margin-top: 2px; }
    table { width: 100%; border-collapse: collapse; font-size: .8rem; margin: 12px 0; }
    th { background: #1e3a5f; color: #fff; padding: 6px 8px; text-align: right; font-weight: 600; }
    th:first-child { text-align: left; }
    td { padding: 5px 8px; text-align: right; border-bottom: 1px solid #e8e8e8; }
    td:first-child { text-align: left; font-weight: 600; }
    tr:nth-child(even) { background: #f8fafc; }
    tr.alert td { background: #fff3e0; }
    tr.total td { background: #1e3a5f; color: #fff; font-weight: 700; border: none; font-size: .85rem; }
    tr.total td:first-child { text-align: left; }
    .dl-btn {
      display: block; width: 100%; padding: 11px;
      background: #4caf50; color: #fff; border: none;
      border-radius: 8px; font-size: .9rem; font-weight: 600;
      cursor: pointer; text-decoration: none; text-align: center;
    }
    .dl-btn:hover { background: #388e3c; }
    .error {
      margin-top: 20px; padding: 16px; border-radius: 8px;
      background: #fff0f0; border-left: 4px solid #e53935;
      font-size: .85rem; color: #b71c1c;
    }
    .spinner { display: none; width: 16px; height: 16px;
               border: 2px solid #fff; border-top-color: transparent;
               border-radius: 50%; animation: spin .7s linear infinite;
               vertical-align: middle; margin-left: 8px; }
    @keyframes spin { to { transform: rotate(360deg); } }
  </style>
</head>
<body>
<div class="card">
  <h1>Pesaje v3</h1>
  <p class="sub">Arrastra o selecciona la planilla mensual de turnos (.xlsx)</p>

  <form method="post" enctype="multipart/form-data" id="frm">
    <div class="drop-zone" id="dz">
      <div class="icon">📂</div>
      <div class="label">Soltar archivo aqui o hacer clic</div>
      <div class="chosen" id="fname"></div>
      <input type="file" id="f" name="xlsx" accept=".xlsx" required>
    </div>
    <button class="btn" type="submit" id="btn">
      Analizar planilla <span class="spinner" id="spin"></span>
    </button>
  </form>

  {% if result %}
  <div class="result">
    <h2>Analisis completado</h2>
    <div class="stats">
      <div class="stat-box"><div class="num">{{ result.n_dias }}</div><div class="lbl">Días</div></div>
      <div class="stat-box"><div class="num">{{ '{:,}'.format(result.total_final) }}g</div><div class="lbl">Total del mes</div></div>
      <div class="stat-box"><div class="num">{{ '{:,}'.format(result.total_vdp) }}g</div><div class="lbl">VDP</div></div>
      <div class="stat-box"><div class="num">{{ result.n_correcciones }}</div><div class="lbl">Correcciones</div></div>
    </div>
    <table>
      <tr><th>Día</th><th>Helados</th><th>VDP</th><th>Total</th><th>Latas</th><th>Corr</th><th>H0</th></tr>
      {% for d in result.dias %}
      <tr class="{{ 'alert' if d.h0 > 3 else '' }}">
        <td>{{ d.label }}</td>
        <td>{{ '{:,}'.format(d.refinada) }}</td>
        <td>{{ '{:,}'.format(d.vdp) }}</td>
        <td>{{ '{:,}'.format(d.total) }}</td>
        <td>{{ d.latas }}</td>
        <td>{{ d.corr }}</td>
        <td>{{ d.h0 }}{{ ' ⚠' if d.h0 > 0 else '' }}</td>
      </tr>
      {% endfor %}
      <tr class="total">
        <td>TOTAL</td>
        <td>{{ '{:,}'.format(result.total_refinada) }}</td>
        <td>{{ '{:,}'.format(result.total_vdp) }}</td>
        <td>{{ '{:,}'.format(result.total_final) }}</td>
        <td>{{ result.total_latas }}</td>
        <td>{{ result.n_correcciones }}</td>
        <td>{{ result.n_sin_resolver }}</td>
      </tr>
    </table>
    <div style="display:flex; gap:10px; margin-top:8px;">
      <a class="dl-btn" href="/download/{{ result.output_name }}" style="flex:1;">
        Descargar Excel
      </a>
      <a class="dl-btn" href="/download/{{ result.pdf_name }}" style="flex:1; background:#1e3a5f;">
        Descargar PDF
      </a>
    </div>
  </div>
  {% endif %}

  {% if error %}
  <div class="error"><strong>Error:</strong> {{ error }}</div>
  {% endif %}
</div>

<script>
const dz = document.getElementById('dz');
const fi = document.getElementById('f');
const fn = document.getElementById('fname');

dz.addEventListener('click', () => fi.click());
fi.addEventListener('change', () => { fn.textContent = fi.files[0]?.name || ''; });

['dragenter','dragover'].forEach(e => dz.addEventListener(e, ev => { ev.preventDefault(); dz.classList.add('drag-over'); }));
['dragleave','drop'].forEach(e => dz.addEventListener(e, ev => { ev.preventDefault(); dz.classList.remove('drag-over'); }));
dz.addEventListener('drop', ev => {
  const file = ev.dataTransfer.files[0];
  if (file) { fi.files = ev.dataTransfer.files; fn.textContent = file.name; }
});

document.getElementById('frm').addEventListener('submit', () => {
  document.getElementById('btn').disabled = true;
  document.getElementById('btn').innerHTML = 'Procesando... <span class="spinner" style="display:inline-block"></span>';
});
</script>
</body>
</html>"""


@app.route('/', methods=['GET', 'POST'])
def index():
    result = None
    error = None

    if request.method == 'POST':
        f = request.files.get('xlsx')
        if not f or not f.filename:
            error = "No se selecciono ningun archivo."
        else:
            tmp_in = None
            try:
                suffix = Path(f.filename).suffix or '.xlsx'
                with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                    f.save(tmp.name)
                    tmp_in = tmp.name

                t0 = time.time()
                stats = _procesar(tmp_in, f.filename)
                elapsed = time.time() - t0

                _outputs[stats['output_name']] = stats['output_path']
                _outputs[stats['pdf_name']] = stats['pdf_path']
                result = stats
                result['elapsed'] = f'{elapsed:.1f}s'
                result['input_name'] = f.filename

            except Exception as ex:
                error = str(ex)
            finally:
                if tmp_in and os.path.exists(tmp_in):
                    os.unlink(tmp_in)

    return render_template_string(_PAGE, result=result, error=error)


@app.route('/download/<path:filename>')
def download(filename):
    path = _outputs.get(filename)
    if not path or not os.path.exists(path):
        return "Archivo no encontrado o expirado.", 404
    return send_file(path, as_attachment=True, download_name=filename)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    print(f"Pesaje v3 — http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)
