"""
pipeline.py — Orquestador del análisis v3.
Corre capa por capa y muestra resultados parciales.
"""
import sys
import os

from .modelos import (
    StatusC3, ResultadoC3, ContabilidadDia, DatosDia, Banda,
    ResultadoDia, Correccion,
)
from .capa1_parser import cargar_dia
from .capa2_contrato import calcular_contabilidad
from .capa3_motor import clasificar
from .capa4_expediente import resolver_escalados, ResultadoC4
from .capa5_residual import segunda_pasada, ResultadoC5, StatusC5
from .exporter import exportar


def analizar_dia(path_excel: str, dia_num: int, verbose: bool = True):
    """
    Pipeline completo: Capa 1 -> 2 -> 3.
    Capas 4 y 5 son manuales por ahora.
    Retorna (datos, contabilidad, clasificacion).
    """

    # ── CAPA 1 ─────────────────────────────────────────────
    if verbose:
        print(f"=== CAPA 1: Parser -- Dia {dia_num} ===")

    datos = cargar_dia(path_excel, dia_num)

    if verbose:
        n_dia = len(datos.turno_dia.sabores)
        n_noche = len(datos.turno_noche.sabores)
        n_ctx = len(datos.contexto)
        print(f"  DIA:     {datos.turno_dia.nombre_hoja} ({n_dia} sabores)")
        print(f"  NOCHE:   {datos.turno_noche.nombre_hoja} ({n_noche} sabores)")
        print(f"  Contexto: {n_ctx} turnos adyacentes")
        print()

    # PF8 pre-proceso: canonicalizacion segura (una sola vez, antes de Capa 2)
    from .capa3_motor import canonicalizar_nombres, aplicar_canonicalizacion
    canon = canonicalizar_nombres(datos)
    collision_warnings = aplicar_canonicalizacion(datos, canon)
    if verbose and canon.aliases_aplicados:
        print(f"  PF8: {len(canon.aliases_aplicados)} alias(es) aplicados")
    if collision_warnings:
        for w in collision_warnings:
            print(f"  WARNING: {w}")

    # ── CAPA 2 ─────────────────────────────────────────────
    if verbose:
        print(f"=== CAPA 2: Contrato contable ===")

    contabilidad = calcular_contabilidad(datos)

    if verbose:
        n_sabores = len(contabilidad.sabores)
        solo_dia = sum(1 for s in contabilidad.sabores.values() if s.solo_dia)
        solo_noche = sum(1 for s in contabilidad.sabores.values() if s.solo_noche)
        activos = n_sabores - solo_dia - solo_noche
        n_latas = sum(s.n_latas for s in contabilidad.sabores.values())
        print(f"  Sabores: {n_sabores} total ({activos} activos, {solo_dia} SOLO_DIA, {solo_noche} SOLO_NOCHE)")
        print(f"  Venta RAW: {contabilidad.venta_raw_total:,}g")
        print(f"  VDP: {contabilidad.vdp_total:,}g")
        print(f"  Latas abiertas: {n_latas} ({n_latas * 280}g)")
        print()

    # ── CAPA 3 ─────────────────────────────────────────────
    if verbose:
        print(f"=== CAPA 3: Motor local ===")

    clasificacion = clasificar(datos, contabilidad)

    if verbose:
        _imprimir_clasificacion(clasificacion, contabilidad)

    # ── CAPA 4 ─────────────────────────────────────────────
    if verbose:
        print()
        print(f"=== CAPA 4: Expediente ampliado ===")

    resultado_c4 = resolver_escalados(datos, contabilidad, clasificacion)

    if verbose:
        _imprimir_capa4(resultado_c4)

    # ── CAPA 5 ─────────────────────────────────────────────
    # Por ahora sin estadisticas historicas (requiere correr todos los dias)
    resultado_c5 = segunda_pasada(
        datos, clasificacion, resultado_c4.correcciones,
        stats={}, media_dia=0, std_dia=0,
    )

    if verbose:
        _imprimir_capa5(resultado_c5)

    # ── RESULTADO FINAL ───────────────────────────────────
    resultado = _armar_resultado(datos, contabilidad, clasificacion, resultado_c4)

    if verbose:
        print()
        print(f"=== RESULTADO FINAL: Dia {dia_num} ===")
        print(f"  Venta RAW:        {resultado.venta_raw:>8,}g")
        print(f"  + CONFIRMADO:     {resultado.venta_confirmado - resultado.venta_raw:>+8,}g")
        print(f"  + FORZADO:        {resultado.venta_operativo - resultado.venta_confirmado:>+8,}g")
        print(f"  + ESTIMADO:       {resultado.venta_refinado - resultado.venta_operativo:>+8,}g")
        print(f"  = Venta Refinada: {resultado.venta_refinado:>8,}g")
        print(f"  VDP:              {resultado.vdp:>8,}g")
        print(f"  Latas:            {resultado.n_latas} ({resultado.lid_discount}g)")
        print(f"  TOTAL OPERATIVO:  {resultado.total_operativo:>8,}g")

    return datos, contabilidad, clasificacion, resultado_c4, resultado_c5, resultado


def _imprimir_clasificacion(c3: ResultadoC3, c2: ContabilidadDia):
    """Imprime el resultado de Capa 3 en formato tabla."""

    # Contar por status
    conteo = {}
    for s in c3.sabores.values():
        st = s.status.value
        conteo[st] = conteo.get(st, 0) + 1

    for st in ['LIMPIO', 'ENGINE', 'SENAL', 'COMPUESTO', 'SOLO_DIA', 'SOLO_NOCHE']:
        if st in conteo:
            print(f"  {st}: {conteo[st]}")

    # Tabla de escalados
    escalados = c3.escalados
    if escalados:
        print(f"\n  -- Sabores que requieren Capa 4 ({len(escalados)}) --")
        print(f"  {'SABOR':<20} {'STATUS':<12} {'RAW':>8} {'FLAGS'}")
        print(f"  {'-'*70}")
        for nombre, sc in sorted(escalados.items()):
            flags_str = ', '.join(f.codigo for f in sc.flags)
            print(f"  {nombre:<20} {sc.status.value:<12} {sc.contable.venta_raw:>8}g  {flags_str}")
        print()

    # Resumen ENGINE
    engines = {k: v for k, v in c3.sabores.items() if v.status == StatusC3.ENGINE}
    if engines:
        print(f"  -- ENGINE ({len(engines)}) --")
        for nombre, sc in sorted(engines.items()):
            flags_str = ', '.join(f.codigo for f in sc.flags) if sc.flags else 'apertura limpia'
            print(f"  {nombre:<20} raw={sc.contable.venta_raw:>8}g  {flags_str}")
        print()

    # Total
    total_resuelto = sum(
        sc.contable.venta_raw for sc in c3.sabores.values()
        if sc.status in (StatusC3.LIMPIO, StatusC3.ENGINE)
    )
    total_escalado = sum(
        sc.contable.venta_raw for sc in escalados.values()
    )
    print(f"  Venta resuelta en C3: {total_resuelto:,}g")
    print(f"  Venta pendiente (escalados): {total_escalado:,}g")
    print(f"  {'-'*40}")
    print(f"  TOTAL RAW: {c2.venta_raw_total:,}g")
    print()
    print(f"  -> Capa 4 necesaria para {len(escalados)} sabores")
    print(f"  -> Capa 5 revisara {conteo.get('LIMPIO', 0)} sabores LIMPIO")


def _imprimir_capa4(c4: ResultadoC4):
    """Imprime resultado de Capa 4."""
    if c4.correcciones:
        print(f"  Correcciones: {len(c4.correcciones)}")
        print()
        print(f"  {'SABOR':<22} {'RAW':>8} {'CORR':>8} {'DELTA':>8} {'TIPO':>5} {'BANDA':<12} {'CONF':>5}")
        print(f"  {'-'*80}")
        total_delta = 0
        for corr in sorted(c4.correcciones, key=lambda c: c.nombre_norm):
            print(f"  {corr.nombre_norm:<22} {corr.venta_raw:>8}g {corr.venta_corregida:>8}g "
                  f"{corr.delta:>+8}g {corr.tipo_justificacion.value:>5} {corr.banda.value:<12} {corr.confianza:>5.2f}")
            print(f"    {corr.motivo}")
            total_delta += corr.delta
        print(f"  {'-'*80}")
        print(f"  {'TOTAL DELTA':<22} {'':>8} {'':>8} {total_delta:>+8}g")
    else:
        print(f"  Sin correcciones.")

    if c4.sin_resolver:
        print(f"\n  Sin resolver (H0): {', '.join(sorted(c4.sin_resolver))}")

    # Bandas summary
    by_banda = {}
    for c in c4.correcciones:
        banda = c.banda.value
        by_banda.setdefault(banda, []).append(c)

    if by_banda:
        print(f"\n  -- Resumen por banda --")
        for banda in ['CONFIRMADO', 'FORZADO', 'ESTIMADO']:
            corrs = by_banda.get(banda, [])
            if corrs:
                delta = sum(c.delta for c in corrs)
                nombres = ', '.join(c.nombre_norm for c in corrs)
                print(f"  {banda:<12}: {delta:>+8}g  ({nombres})")


def _imprimir_capa5(c5: ResultadoC5):
    """Imprime resultado de Capa 5."""
    print()
    print(f"=== CAPA 5: Segunda pasada residual ===")
    n_confirmado = sum(1 for v in c5.sabores.values() if v.status == StatusC5.LIMPIO_CONFIRMADO)
    n_nota = sum(1 for v in c5.sabores.values() if v.status == StatusC5.LIMPIO_CON_NOTA)
    n_reabrir = sum(1 for v in c5.sabores.values() if v.status == StatusC5.REABRIR)
    print(f"  LIMPIO_CONFIRMADO: {n_confirmado}")
    print(f"  LIMPIO_CON_NOTA:   {n_nota}")
    print(f"  REABRIR:           {n_reabrir}")

    if c5.senales_dia:
        print(f"  Senales dia: {', '.join(s.subtipo for s in c5.senales_dia)}")

    if n_reabrir > 0:
        print(f"  Sabores a reabrir: {', '.join(c5.reaperturas)}")


def _armar_resultado(datos: DatosDia, contabilidad: ContabilidadDia,
                     clasificacion: ResultadoC3, c4: ResultadoC4) -> ResultadoDia:
    """Arma el ResultadoDia final combinando Capas 2-4."""
    corr_map = {c.nombre_norm: c for c in c4.correcciones}

    # Venta raw total
    venta_raw = contabilidad.venta_raw_total

    # Deltas por banda
    delta_confirmado = sum(c.delta for c in c4.correcciones if c.banda == Banda.CONFIRMADO)
    delta_forzado = sum(c.delta for c in c4.correcciones if c.banda == Banda.FORZADO)
    delta_estimado = sum(c.delta for c in c4.correcciones if c.banda == Banda.ESTIMADO)

    # Prototipos de Capa 3 se consideran CONFIRMADO
    for sc in clasificacion.sabores.values():
        if sc.prototipo:
            delta_confirmado += sc.prototipo.delta

    venta_confirmado = venta_raw + delta_confirmado
    venta_operativo = venta_confirmado + delta_forzado
    venta_refinado = venta_operativo + delta_estimado

    n_latas = sum(s.n_latas for s in contabilidad.sabores.values())
    lid_discount = n_latas * 280

    # Conteos
    n_limpio = sum(1 for s in clasificacion.sabores.values() if s.status == StatusC3.LIMPIO)
    n_engine = sum(1 for s in clasificacion.sabores.values() if s.status == StatusC3.ENGINE)
    n_escalado = len(clasificacion.escalados)
    n_solo_dia = sum(1 for s in clasificacion.sabores.values()
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
        n_solo_dia=n_solo_dia,
    )


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

def main():
    if len(sys.argv) < 3:
        print("Uso: python -m pesaje_v3.pipeline <archivo.xlsx> <dia> [output.xlsx]")
        print("  Ejemplo: python -m pesaje_v3.pipeline 'Febrero San Martin 2026.xlsx' 5")
        sys.exit(1)

    path = sys.argv[1]
    dia = int(sys.argv[2])
    output = sys.argv[3] if len(sys.argv) > 3 else None

    datos, contabilidad, clasificacion, resultado_c4, resultado_c5, resultado = analizar_dia(path, dia)

    # Exportar si se pide
    if output:
        out_path = exportar(resultado, clasificacion, resultado_c4.correcciones, output)
        print(f"\n  Exportado: {out_path}")


if __name__ == '__main__':
    main()
