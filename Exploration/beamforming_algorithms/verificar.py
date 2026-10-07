"""
verificar.py — Batería de verificación del DAS contra la simulación ideal.

Cada prueba tiene un resultado esperado conocido de antemano; si el código
del DAS/SRP/GCC está bien, todas pasan para todas las geometrías:

  1. Retardos: GCC-PHAT sobre señal de banda ancha recupera los tau
     teóricos (error < 0.1 muestra).
  2. Reconstrucción campo lejano: onda plana + DAS apuntado a la fuente
     reproduce la señal original (error < -40 dB), seno y banda ancha.
  3. Reconstrucción campo cercano: onda esférica con atenuación 1/r + DAS
     apuntado al punto exacto reproduce la señal (error < -40 dB).
  4. DOA por SRP: el máximo cae en el azimut real (±1°) en 24 azimuts. En
     un arreglo colineal se acepta también el espejo (ambigüedad
     frente/espalda inevitable), y se reporta.
  5. Ganancia en SNR con ruido de sensor blanco independiente:
     10*log10(8) = 9.03 dB (±0.3 dB).

Uso:  python verificar.py            (todas las geometrías)
      python verificar.py ula_2cm    (solo una)
"""

import sys

import numpy as np

import campo
import das
import geometrias

FS = campo.FS
C = campo.C_SONIDO
RECORTE = int(0.010 * FS)       # muestras descartadas en cada borde (transitorio del retardo por FFT)


def error_db(y, ref):
    """Error residual (dB) de y contra ref tras ajustar una ganancia por mínimos cuadrados."""
    y, ref = y[RECORTE:-RECORTE], ref[RECORTE:-RECORTE]
    g = np.dot(y, ref) / np.dot(ref, ref)
    return 10 * np.log10(np.sum((y - g * ref) ** 2) / np.sum((g * ref) ** 2))


def referencia(senal, info, tau_apunte):
    """Lo que el DAS debería entregar: la señal original retrasada al instante de alineación."""
    t_alineado = np.mean(info["tau"] + (tau_apunte.max() - tau_apunte))
    return senal(info["t"] - t_alineado)


def diferencia_angular(a, b):
    return np.abs((a - b + 180) % 360 - 180)


def verificar_geometria(nombre):
    pos = geometrias.obtener(nombre)
    centro = geometrias.centroide(pos)
    eje = geometrias.eje_si_colineal(pos)
    res = []

    def check(desc, ok, detalle):
        res.append(ok)
        print(f"  [{'PASA' if ok else 'FALLA'}] {desc:<46} {detalle}")

    print(f"\n── {nombre}  (apertura {geometrias.apertura(pos)*100:.1f} cm, "
          f"sep. mín {geometrias.separacion_minima(pos)*100:.1f} cm"
          f"{', COLINEAL' if eje is not None else ''})")

    bb = campo.multitono()
    sen = campo.seno(1000)

    # 1. Retardos por GCC-PHAT. Se usa un pulso completo dentro de la ventana:
    # con una señal estacionaria (multitono, chirp) cada canal ve un tramo
    # distinto en los bordes y eso sesga GCC ~0.1 muestra — error del
    # estimador sobre una ventana finita, no del modelo de retardos.
    fuente = campo.fuente_polar(centro, 1.0, 30.0)
    x, info = campo.simular(pos, fuente, campo.pulso(), FS, 0.2, C, modelo="esferico")
    max_tau = geometrias.apertura(pos) / C
    medidos = np.array([das.gcc_phat(x[:, m], x[:, 0], FS, max_tau, interp=64)
                        for m in range(pos.shape[0])])
    teoricos = info["tau"] - info["tau"][0]
    err = np.abs(medidos - teoricos).max() * FS
    check("Retardos GCC-PHAT vs teóricos (pulso)", err < 0.05, f"err máx = {err:.3f} muestras")

    # 2. Reconstrucción campo lejano (onda plana)
    for s in (sen, bb):
        fuente = campo.fuente_polar(centro, 3.0, 70.0)
        x, info = campo.simular(pos, fuente, s, FS, 0.5, C, modelo="plano")
        tau = das.retardos_campo_lejano(pos, 70.0, c=C)
        e = error_db(das.das(x, tau, FS), referencia(s, info, tau))
        check(f"Reconstrucción campo lejano ({s.nombre})", e < -40, f"error = {e:.1f} dB")

    # 3. Reconstrucción campo cercano (onda esférica, 1/r)
    fuente = campo.fuente_polar(centro, 0.30, 200.0)
    x, info = campo.simular(pos, fuente, bb, FS, 0.5, C, modelo="esferico")
    tau = das.retardos_campo_cercano(pos, fuente, c=C)
    e = error_db(das.das(x, tau, FS), referencia(bb, info, tau))
    check("Reconstrucción campo cercano a 30 cm", e < -40, f"error = {e:.1f} dB")

    # 4. DOA por SRP
    rejilla = np.arange(0, 360, 0.5)
    errores, espejos = [], 0
    for az in np.arange(0, 360, 15.0):
        x, _ = campo.simular(pos, campo.fuente_polar(centro, 2.0, az), bb, FS, 0.25, C)
        est = rejilla[np.argmax(das.srp(x, pos, rejilla, FS, C))]
        e = diferencia_angular(est, az)
        if eje is not None:
            e_espejo = diferencia_angular(est, 2 * eje - az)
            if e_espejo < e:
                e, espejos = e_espejo, espejos + 1
        errores.append(e)
    nota = f" ({espejos} resueltos solo como espejo)" if espejos else ""
    check("DOA por SRP en 24 azimuts (fuente a 2 m)", max(errores) <= 1.0,
          f"err máx = {max(errores):.1f}°{nota}")

    # 5. Ganancia de SNR con ruido de sensor
    fuente = campo.fuente_polar(centro, 3.0, 120.0)
    x, info = campo.simular(pos, fuente, bb, FS, 2.0, C, modelo="plano")
    ruido = campo.ruido_sensor(*x.shape, snr_db=0.0, potencia_senal=np.mean(x ** 2))
    tau = das.retardos_campo_lejano(pos, 120.0, c=C)
    ys, yr = das.das(x, tau, FS), das.das(ruido, tau, FS)
    snr_in = 10 * np.log10(np.mean(x ** 2) / np.mean(ruido ** 2))
    snr_out = 10 * np.log10(np.mean(ys[RECORTE:-RECORTE] ** 2) / np.mean(yr[RECORTE:-RECORTE] ** 2))
    esperada = 10 * np.log10(pos.shape[0])
    g = snr_out - snr_in
    check("Ganancia SNR con ruido de sensor", abs(g - esperada) < 0.3,
          f"{g:.2f} dB (teórica {esperada:.2f} dB)")

    return all(res)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")   # consola de Windows (cp1252) no imprime ─, °, µ
    nombres = sys.argv[1:] or list(geometrias.GEOMETRIAS)
    resultados = {n: verificar_geometria(n) for n in nombres}
    print("\n" + "=" * 70)
    for n, ok in resultados.items():
        print(f"  {n:<20} {'TODO PASA' if ok else 'HAY FALLAS'}")
    sys.exit(0 if all(resultados.values()) else 1)
