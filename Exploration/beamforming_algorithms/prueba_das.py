"""
prueba_das.py — Escenario visual: 8 micrófonos + fuente sintética + DAS.

Ajustar la sección CONFIG y correr:
    python prueba_das.py              (abre la figura)
    python prueba_das.py --no-show    (solo guarda el PNG en SALIDAS/)

Cualquier variable de CONFIG se puede sobreescribir como CLAVE=valor:
    python prueba_das.py GEOMETRIA=ula_2cm SENAL=multitono AZIMUT=120

Paneles:
  (a) escena completa en XY: arreglo, fuente y dirección de llegada
  (b) zoom al arreglo: retardo teórico de llegada a cada micrófono
  (c) señales de los 8 micrófonos (ventana corta) — se ven los desfases
  (d) patrón polar SRP: dónde "cree" el DAS que está la fuente
  (e) salida DAS apuntada vs. señal original y vs. un micrófono crudo
  (f) resumen numérico de la verificación
"""

import json
import os
import sys

import matplotlib
if "--no-show" in sys.argv:
    matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import campo
import das
import geometrias

# ── CONFIG ────────────────────────────────────────────────────────────────────
GEOMETRIA   = "placeholder_json"   # ver geometrias.GEOMETRIAS, o ruta a un .json
DISTANCIA   = 1.0                  # m, desde el centroide del arreglo (plano XY)
AZIMUT      = 60.0                 # grados, desde +x, antihorario
ALTURA      = 0.0                  # m, z de la fuente (por ahora mismo plano)
SENAL       = "seno"               # seno | chirp | multitono | pulso
FRECUENCIA  = 1000.0               # Hz, solo para "seno"
DURACION    = 0.5                  # s
MODELO      = "esferico"           # esferico (real) | plano (campo lejano ideal)
APUNTE      = "lejano"             # lejano (por ángulo) | cercano (al punto exacto)
SNR_SENSOR  = None                 # dB de ruido blanco por micrófono; None = sin ruido
PESOS       = None                 # None = DAS convencional (1/M); o lista de 8 pesos
# ──────────────────────────────────────────────────────────────────────────────

for _arg in sys.argv[1:]:
    if "=" in _arg:
        _clave, _valor = _arg.split("=", 1)
        if _clave not in globals():
            sys.exit(f"Variable de CONFIG desconocida: {_clave}")
        try:
            globals()[_clave] = json.loads(_valor)    # números, null, listas [1,2,...]
        except json.JSONDecodeError:
            globals()[_clave] = _valor                # texto: GEOMETRIA=ula_2cm

FS, C = campo.FS, campo.C_SONIDO
SALIDAS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "SALIDAS"))
RECORTE = int(0.010 * FS)


def main():
    pos = geometrias.obtener(GEOMETRIA)
    m = pos.shape[0]
    centro = geometrias.centroide(pos)
    fuente = campo.fuente_polar(centro, DISTANCIA, AZIMUT, ALTURA)
    senal = campo.seno(FRECUENCIA) if SENAL == "seno" else campo.SENALES[SENAL]()

    limpio, info = campo.simular(pos, fuente, senal, FS, DURACION, C, modelo=MODELO)
    x = limpio
    if SNR_SENSOR is not None:
        x = limpio + campo.ruido_sensor(*limpio.shape, SNR_SENSOR, np.mean(limpio ** 2))

    tau_apunte = (das.retardos_campo_lejano(pos, AZIMUT, c=C) if APUNTE == "lejano"
                  else das.retardos_campo_cercano(pos, fuente, c=C))
    y = das.das(x, tau_apunte, FS, PESOS)
    ref = senal(info["t"] - np.mean(info["tau"] + tau_apunte.max() - tau_apunte))

    rejilla = np.arange(0, 360, 0.5)
    P = das.srp(x, pos, rejilla, FS, C, PESOS)
    az_est = rejilla[np.argmax(P)]

    # Métricas
    yi, ri = y[RECORTE:-RECORTE], ref[RECORTE:-RECORTE]
    g = np.dot(yi, ri) / np.dot(ri, ri)
    err_db = 10 * np.log10(np.sum((yi - g * ri) ** 2) / np.sum((g * ri) ** 2))
    err_doa = abs((az_est - AZIMUT + 180) % 360 - 180)
    eje = geometrias.eje_si_colineal(pos)

    resumen = [
        f"Geometría: {GEOMETRIA}" + ("  (COLINEAL)" if eje is not None else ""),
        f"  apertura {geometrias.apertura(pos)*100:.1f} cm · sep. mín {geometrias.separacion_minima(pos)*100:.1f} cm",
        f"Fuente: {senal.nombre}",
        f"  r = {DISTANCIA:g} m · az = {AZIMUT:g}° · z = {ALTURA:g} m",
        f"Simulación: {MODELO} · apunte: {APUNTE}",
        f"Ruido de sensor: {'ninguno' if SNR_SENSOR is None else f'{SNR_SENSOR:g} dB SNR'}",
        "",
        f"DOA estimada (SRP): {az_est:.1f}°  (error {err_doa:.1f}°)",
        f"Error salida vs original: {err_db:.1f} dB",
        f"Ganancia ajustada: {g:.3f}",
        f"Retardo máx entre mics: {np.ptp(info['tau'])*1e6:.0f} µs = {np.ptp(info['tau'])*FS:.2f} muestras",
    ]
    if eje is not None:
        resumen.append(f"Arreglo colineal: el espejo {(2*eje - AZIMUT) % 360:.0f}° es indistinguible")
    if not senal.banda_ancha:
        resumen.append("Tono puro: verificar también con banda ancha")
    print("\n".join(resumen))

    graficar(pos, centro, fuente, info, x, y, ref, g, rejilla, P, az_est, senal, resumen)


def graficar(pos, centro, fuente, info, x, y, ref, g, rejilla, P, az_est, senal, resumen):
    m = pos.shape[0]
    colores = plt.cm.tab10(np.arange(m))
    fig = plt.figure(figsize=(16, 9.5))
    fig.suptitle(f"Simulación DAS — {GEOMETRIA} · {senal.nombre} · fuente a {DISTANCIA:g} m, {AZIMUT:g}°")

    # (a) escena completa
    ax = fig.add_subplot(2, 3, 1)
    ax.scatter(pos[:, 0], pos[:, 1], c=colores, s=25, zorder=3, label="micrófonos")
    ax.scatter(*fuente[:2], marker="*", s=300, c="crimson", zorder=4, label="fuente")
    ax.plot([centro[0], fuente[0]], [centro[1], fuente[1]], "--", c="crimson", lw=1)
    ax.add_patch(plt.Circle(centro[:2], DISTANCIA, fill=False, ls=":", color="gray"))
    est = centro[:2] + DISTANCIA * np.array([np.cos(np.deg2rad(az_est)), np.sin(np.deg2rad(az_est))])
    ax.plot([centro[0], est[0]], [centro[1], est[1]], c="tab:green", lw=1.5, label=f"DOA estimada {az_est:.1f}°")
    lim = DISTANCIA * 1.2
    ax.set_xlim(centro[0] - lim, centro[0] + lim)
    ax.set_ylim(centro[1] - lim, centro[1] + lim)
    ax.set_aspect("equal")
    ax.set_xlabel("x (m)"); ax.set_ylabel("y (m)")
    ax.set_title("(a) Escena (plano XY)")
    ax.legend(loc="lower left", fontsize=8)
    ax.grid(alpha=0.3)

    # (b) zoom al arreglo con retardos
    ax = fig.add_subplot(2, 3, 2)
    tau_rel = (info["tau"] - info["tau"].min()) * 1e6
    ax.scatter(pos[:, 0] * 100, pos[:, 1] * 100, c=colores, s=80, zorder=3)
    for i in range(m):
        ax.annotate(f"M{i+1}\n{tau_rel[i]:.0f} µs", pos[i, :2] * 100, textcoords="offset points",
                    xytext=(6, 4) if i % 2 == 0 else (6, -24), fontsize=8)   # alternar: no encimar en un ULA
    u = (fuente - centro)[:2]
    u = u / np.linalg.norm(u)
    span = geometrias.apertura(pos) * 100 / 2
    ax.annotate("", xy=centro[:2] * 100 + u * span * 0.6, xytext=centro[:2] * 100 + u * span * 1.3,
                arrowprops=dict(arrowstyle="<-", color="crimson", lw=2))
    ax.text(*(centro[:2] * 100 + u * span * 1.4), "hacia la fuente", color="crimson",
            fontsize=8, ha="center")
    medio = (pos[:, :2].max(axis=0) + pos[:, :2].min(axis=0)) / 2 * 100
    lado = np.ptp(pos[:, :2], axis=0).max() * 100 / 2 * 1.5 + 1.5   # cuadrado (no colapsa si es colineal)
    ax.set_xlim(medio[0] - lado, medio[0] + lado)
    ax.set_ylim(medio[1] - lado, medio[1] + lado)
    ax.set_aspect("equal")
    ax.set_xlabel("x (cm)"); ax.set_ylabel("y (cm)")
    ax.set_title("(b) Arreglo — retardo de llegada relativo")
    ax.grid(alpha=0.3)

    # (c) señales por micrófono
    ax = fig.add_subplot(2, 3, 3)
    dur_ms = 4.0 if not senal.banda_ancha else 1.5            # banda ancha: ventana corta para ver desfases
    ventana = slice(RECORTE, RECORTE + int(dur_ms * 1e-3 * FS))
    t_ms = info["t"][ventana] * 1e3
    sep = 2.2 * np.abs(x[ventana]).max()
    for i in range(m):
        ax.plot(t_ms, x[ventana, i] - i * sep, c=colores[i], lw=1, marker=".", ms=3)
        ax.text(t_ms[0], -i * sep, f"M{i+1} ", ha="right", va="center", fontsize=8)
    ax.set_yticks([])
    ax.set_xlabel("t (ms)")
    ax.set_title(f"(c) Señal en cada micrófono ({dur_ms:g} ms)")
    ax.grid(alpha=0.3, axis="x")

    # (d) SRP polar
    ax = fig.add_subplot(2, 3, 4, projection="polar")
    p_db = 10 * np.log10(P / P.max() + 1e-12)
    ax.plot(np.deg2rad(rejilla), np.maximum(p_db, -30), c="tab:green")
    ax.axvline(np.deg2rad(az_est), c="tab:green", lw=2.5, alpha=0.6, label="estimada")
    ax.axvline(np.deg2rad(AZIMUT), c="crimson", ls="--", lw=1.2, label="real")
    ax.set_ylim(-30, 1)
    ax.set_title("(d) SRP (dB, normalizado)", pad=15)
    ax.legend(loc="lower left", fontsize=8, bbox_to_anchor=(-0.15, -0.1))

    # (e) salida vs referencia
    ax = fig.add_subplot(2, 3, 5)
    ventana = slice(len(y) // 2, len(y) // 2 + int(0.005 * FS))
    t_ms = info["t"][ventana] * 1e3
    ax.plot(t_ms, g * ref[ventana], c="k", lw=3, alpha=0.35, label="original (alineada)")
    ax.plot(t_ms, y[ventana], c="tab:blue", lw=1.2, label="salida DAS")
    ax.plot(t_ms, x[ventana, 0], c=colores[0], lw=0.8, ls=":", label="M1 crudo")
    ax.set_xlabel("t (ms)")
    ax.set_title("(e) Salida DAS vs. señal original")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)

    # (f) resumen
    ax = fig.add_subplot(2, 3, 6)
    ax.axis("off")
    ax.text(0, 1, "\n".join(resumen), va="top", family="monospace", fontsize=9)
    ax.set_title("(f) Resumen")

    fig.tight_layout()
    os.makedirs(SALIDAS, exist_ok=True)
    ruta = os.path.join(SALIDAS, f"sim_das_{GEOMETRIA}_{SENAL}_az{AZIMUT:g}.png")
    fig.savefig(ruta, dpi=120)
    print(f"\nGuardado: {ruta}")
    if "--no-show" not in sys.argv:
        plt.show()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
