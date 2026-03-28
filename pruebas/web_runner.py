"""
web_runner.py — Interfaz web para el sistema de pesaje de Heladería San Martín.

Uso:
    python web_runner.py
    Luego abrir http://localhost:5000
"""
import os
import tempfile
from pathlib import Path
from flask import Flask, request, render_template_string, send_file

import sys
sys.path.insert(0, os.path.dirname(__file__))
from parser import load_shifts
from calculator import calculate_periods
from exporter import export

app = Flask(__name__)
_outputs: dict = {}   # output_name -> temp_path

# ── HTML ──────────────────────────────────────────────────────────────────────

_PAGE = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Pesaje — Heladería San Martín</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #f5f7fa; color: #1a1a2e; min-height: 100vh;
      display: flex; align-items: flex-start; justify-content: center;
      padding: 48px 16px;
    }
    .card {
      background: #fff; border-radius: 12px;
      box-shadow: 0 4px 24px rgba(0,0,0,.08);
      padding: 40px; width: 100%; max-width: 560px;
    }
    h1 { font-size: 1.5rem; font-weight: 700; color: #1e3a5f; margin-bottom: 6px; }
    .sub { color: #666; font-size: .9rem; margin-bottom: 32px; }
    .drop-zone {
      border: 2px dashed #c0cfe0; border-radius: 8px;
      padding: 36px 24px; text-align: center;
      cursor: pointer; transition: border-color .2s, background .2s;
      margin-bottom: 20px;
    }
    .drop-zone:hover { border-color: #2e7dd1; background: #f0f6ff; }
    .drop-zone input[type=file] { display: none; }
    .drop-zone .icon { font-size: 2.4rem; margin-bottom: 8px; }
    .drop-zone .label { font-size: .95rem; color: #555; }
    .drop-zone .chosen { font-size: .9rem; color: #2e7dd1; font-weight: 600;
                         margin-top: 6px; word-break: break-all; }
    .btn {
      display: block; width: 100%; padding: 13px;
      background: #2e7dd1; color: #fff; border: none;
      border-radius: 8px; font-size: 1rem; font-weight: 600;
      cursor: pointer; transition: background .2s;
    }
    .btn:hover { background: #1d5fa3; }
    .btn:disabled { background: #9ab8d9; cursor: not-allowed; }
    .result {
      margin-top: 28px; padding: 20px; border-radius: 8px;
      background: #f0f9f0; border-left: 4px solid #4caf50;
    }
    .result h2 { font-size: 1rem; color: #2e7a35; margin-bottom: 14px; }
    .stats { display: flex; gap: 16px; margin-bottom: 16px; flex-wrap: wrap; }
    .stat-box {
      flex: 1; min-width: 100px; background: #fff; border-radius: 6px;
      padding: 12px; text-align: center;
      box-shadow: 0 1px 4px rgba(0,0,0,.07);
    }
    .stat-box .num { font-size: 1.6rem; font-weight: 700; color: #1e3a5f; }
    .stat-box .lbl { font-size: .75rem; color: #888; margin-top: 2px; }
    .anom-box { background: #fff8e1; border-radius: 6px; padding: 12px; text-align: center;
                box-shadow: 0 1px 4px rgba(0,0,0,.07); }
    .anom-box .num { font-size: 1.6rem; font-weight: 700;
                     color: {{ '#c62828' if result and result.n_errors > 0 else '#e65100' }}; }
    .anom-box .lbl { font-size: .75rem; color: #888; margin-top: 2px; }
    .anom-detail { font-size: .82rem; color: #555; margin-bottom: 14px; }
    .dl-btn {
      display: block; width: 100%; padding: 11px;
      background: #4caf50; color: #fff; border: none;
      border-radius: 8px; font-size: .95rem; font-weight: 600;
      cursor: pointer; text-decoration: none; text-align: center;
      transition: background .2s;
    }
    .dl-btn:hover { background: #388e3c; }
    .error {
      margin-top: 24px; padding: 18px; border-radius: 8px;
      background: #fff0f0; border-left: 4px solid #e53935; font-size: .9rem;
      color: #b71c1c;
    }
    .spinner { display: none; margin: 0 auto 0 8px; width: 18px; height: 18px;
               border: 2px solid #fff; border-top-color: transparent;
               border-radius: 50%; animation: spin .7s linear infinite; vertical-align: middle; }
    @keyframes spin { to { transform: rotate(360deg); } }
  </style>
</head>
<body>
<div class="card">
  <h1>🍦 Pesaje — San Martín</h1>
  <p class="sub">Subí la planilla mensual de turnos para generar el análisis comparativo.</p>

  <form method="post" enctype="multipart/form-data" id="frm">
    <div class="drop-zone" onclick="document.getElementById('f').click()">
      <div class="icon">📂</div>
      <div class="label">Hacer clic para seleccionar el archivo <strong>.xlsx</strong></div>
      <div class="chosen" id="fname">Ningún archivo seleccionado</div>
      <input type="file" id="f" name="xlsx" accept=".xlsx" required
             onchange="document.getElementById('fname').textContent = this.files[0]?.name || 'Ningún archivo'">
    </div>
    <button class="btn" type="submit" id="btn">
      Analizar planilla
      <span class="spinner" id="spin"></span>
    </button>
  </form>

  {% if result %}
  <div class="result">
    <h2>✓ Análisis completado — {{ result.input_name }}</h2>
    <div class="stats">
      <div class="stat-box">
        <div class="num">{{ result.n_shifts }}</div>
        <div class="lbl">Turnos</div>
      </div>
      <div class="stat-box">
        <div class="num">{{ result.n_periods }}</div>
        <div class="lbl">Períodos</div>
      </div>
      <div class="anom-box">
        <div class="num">{{ result.n_anomalies }}</div>
        <div class="lbl">Anomalías</div>
      </div>
    </div>
    {% if result.n_errors > 0 %}
    <p class="anom-detail">
      ⚠ <strong>{{ result.n_errors }}</strong> errores críticos  ·
      {{ result.n_warnings }} advertencias
    </p>
    {% else %}
    <p class="anom-detail">{{ result.n_warnings }} advertencias</p>
    {% endif %}
    <a class="dl-btn" href="/download/{{ result.output_name }}">
      ⬇ Descargar {{ result.output_name }}
    </a>
  </div>
  {% endif %}

  {% if error %}
  <div class="error"><strong>Error:</strong> {{ error }}</div>
  {% endif %}
</div>

<script>
document.getElementById('frm').addEventListener('submit', function() {
  document.getElementById('btn').disabled = true;
  document.getElementById('btn').textContent = 'Procesando...';
  document.getElementById('spin').style.display = 'inline-block';
});
</script>
</body>
</html>"""

# ── Routes ────────────────────────────────────────────────────────────────────

@app.route('/', methods=['GET', 'POST'])
def index():
    result = None
    error  = None

    if request.method == 'POST':
        f = request.files.get('xlsx')
        if not f or not f.filename:
            error = "No se seleccionó ningún archivo."
        else:
            tmp_in = None
            try:
                suffix = Path(f.filename).suffix or '.xlsx'
                with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                    f.save(tmp.name)
                    tmp_in = tmp.name

                shifts = load_shifts(tmp_in)
                shifts = [s for s in shifts if s.is_valid]
                if not shifts:
                    error = "No se encontraron hojas válidas (A1='SABORES')."
                else:
                    periods = calculate_periods(shifts)

                    stem        = Path(f.filename).stem
                    output_name = f"Comparativa_Ventas_{stem}.xlsx"
                    tmp_out     = os.path.join(tempfile.gettempdir(), output_name)
                    export(periods, tmp_out)
                    _outputs[output_name] = tmp_out

                    n_errors   = sum(1 for p in periods for r in p.flavors.values()
                                     for a in r.anomalies if a.severity == 'error')
                    n_warnings = sum(1 for p in periods for r in p.flavors.values()
                                     for a in r.anomalies if a.severity == 'warning')

                    result = dict(
                        input_name  = f.filename,
                        output_name = output_name,
                        n_shifts    = len(shifts),
                        n_periods   = len(periods),
                        n_anomalies = n_errors + n_warnings,
                        n_errors    = n_errors,
                        n_warnings  = n_warnings,
                    )
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


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("Pesaje Web Runner — http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)
