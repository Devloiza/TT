"""Gráficas de la geometría de las patas: apoyo visual de estadistica_imagenes.py.

Hecho por Claude con la especificación del autor (opción B: la transformación al marco del cuerpo y la estadística
son del autor y están en estadistica_imagenes.py; este módulo solo dibuja lo que ese script calcula).

Marco del cuerpo: x lateral (positivo hacia la derecha del animal), y hacia el frente, origen en el centro del
círculo y unidades en largos del eje del cuerpo (|frente - atrás| = 1). Ángulos en radianes, 0 al frente.

Una figura por modo (espejo y pares), en una fila de dos columnas:
  izquierda  mapa de calor de los clics (cada foto pesa lo mismo) + sector del IC 95 % de ángulo y radio por par
  derecha    escorpión esquemático con las patas en la posición media de cada par y los valores con su IC
"""
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import scipy.stats
from matplotlib.lines import Line2D
from matplotlib.patches import Ellipse, Patch, Polygon

# ----------------------------------------------------------------- configuración
TEXT_SIZE = 12  # todos los textos de la figura
LINE_SIZE = 2  # grosor de los contornos de los sectores y de las patas del esquema
TAMANO_FIGURA = (16, 8)  # pulgadas, por figura (una por modo)
TAMANO_VALORES = 14  # texto de los valores (ángulo y radio con su IC) en el esquema
RESOLUCION_MAPA = 250  # puntos por lado de la malla del mapa de calor
NIVELES_MAPA = 8  # escalones de opacidad del mapa de calor
UMBRAL_MAPA = 0.08  # densidad relativa por debajo de la cual el mapa es transparente
ALFA_MAXIMO = 0.75  # opacidad de la zona de mayor concentración de cada par
ANCHO_KDE = None  # bw_method de scipy.stats.gaussian_kde (None = regla de Scott)
COLA_DETRAS_DEL_EJE = True  # "atrás" se marca donde termina el cuerpo e inicia la cola (autor, 2026-11-07)
MOSTRAR_VALORES = True  # ángulo y radio medios ± la mitad del IC 95 % junto a cada pata del esquema


def _a_xy(radio, angulo):
    """Polar del marco del cuerpo -> cartesianas (x lateral, y al frente)."""
    return radio * np.sin(angulo), radio * np.cos(angulo)


def _par(clave):
    return clave.split("-")[0]


def _etiqueta(d, espejo_izq=False):
    """Ángulo medio (grados, 0° al frente) y radio medio (largos de cuerpo), cada uno ± la mitad de su IC 95 %."""
    angulo = -np.degrees(d["media_angulos"]) if espejo_izq else np.degrees(d["media_angulos"])
    m_ang = np.degrees(d["t-student_angulos"][1] - d["media_angulos"])  # mitad del IC (es simétrico)
    m_rad = d["t-student_radios"][1] - d["media_radios"]
    return f"θ = {angulo:.0f}° ± {m_ang:.0f}°\nρ = {d['media_radios']:.2f} ± {m_rad:.2f}"


# ----------------------------------------------------------------- piezas
def mapa_calor(ax, xy, pesos, color, limites, espejo=False):
    """Densidad de los clics ponderada (KDE), normalizada a su máximo: la opacidad es concentración relativa.

    En espejo los datos tienen x >= 0; se refleja una copia en x < 0 para que la estimación no se "escape" del borde
    y solo se dibuja la mitad derecha.
    """
    datos, w = xy, pesos
    if espejo:
        datos = np.hstack((xy, xy * np.array([[-1], [1]])))
        w = np.concatenate((pesos, pesos))
    kde = scipy.stats.gaussian_kde(datos, weights=w, bw_method=ANCHO_KDE)
    gx, gy = np.meshgrid(np.linspace(*limites[0], RESOLUCION_MAPA), np.linspace(*limites[1], RESOLUCION_MAPA))
    z = kde(np.vstack((gx.ravel(), gy.ravel()))).reshape(gx.shape)
    if espejo:
        z[gx < 0] = 0
    z /= z.max()
    mapa = mcolors.LinearSegmentedColormap.from_list(
        "", [mcolors.to_rgba(color, 0.05), mcolors.to_rgba(color, ALFA_MAXIMO)])
    ax.contourf(gx, gy, z, levels=np.linspace(UMBRAL_MAPA, 1, NIVELES_MAPA + 1), cmap=mapa, antialiased=True)


def sector_ic(ax, ic_radio, ic_angulo, color):
    """Sector de anillo: ángulo dentro de su IC y radio dentro de su IC."""
    angulos = np.linspace(ic_angulo[0], ic_angulo[1], 60)
    xe, ye = _a_xy(ic_radio[1], angulos)
    xi, yi = _a_xy(ic_radio[0], angulos[::-1])
    vertices = np.column_stack((np.concatenate((xe, xi)), np.concatenate((ye, yi))))
    ax.add_patch(Polygon(vertices, closed=True, fc=mcolors.to_rgba(color, 0.15), ec=color, lw=LINE_SIZE))


def guia_polar(ax, radio, espejo):
    """Rayos de referencia cada 45° (0° al frente) y círculo de radio dado, para leer los ángulos."""
    grados = np.arange(0, 181, 45) if espejo else np.arange(-135, 181, 45)  # -180° y 180° son el mismo rayo
    for g in grados:
        x, y = _a_xy(radio, np.radians(g))
        ax.plot([0, x], [0, y], color="0.6", lw=0.8, ls=":", zorder=0)
        ax.annotate(f"{g}°", (x * 1.07, y * 1.07), ha="center", va="center", color="0.4", fontsize=TEXT_SIZE * 0.8)
    t = np.linspace(0 if espejo else -np.pi, np.pi, 200)
    ax.plot(*_a_xy(radio, t), color="0.6", lw=0.8, ls=":", zorder=0)
    ax.plot(0, 0, "k+", ms=10)


def posicion_frente(imagenes, nombres_imagenes):
    """Posición media del punto "frente" en el marco del cuerpo (y, en largos de cuerpo), para ubicar el esquema.

    Es la misma proyección del análisis, aplicada solo al punto del frente; no entra en la estadística.
    """
    fotos = imagenes[imagenes["imagen"].isin(nombres_imagenes)]
    f = fotos[["eje_frente_x", "eje_frente_y"]].to_numpy()
    t = fotos[["eje_atras_x", "eje_atras_y"]].to_numpy()
    o = fotos[["circulo_x", "circulo_y"]].to_numpy()
    largo = np.linalg.norm(f - t, axis=1)
    u = (f - t) / largo[:, None]
    return float(np.mean(np.sum((f - o) * u, axis=1) / largo))


def escorpion(ax, estadistica, frente_y, colores, espejo):
    """Escorpión esquemático (vista dorsal) con cada pata terminando en la posición media de su par.

    Solo las puntas de las patas son datos (radio y ángulo medios). El cuerpo, la cola, los pedipalpos, el punto
    donde nace cada pata y la "rodilla" son supuestos de dibujo.
    """
    atras_y = frente_y - 1
    gris, borde = "0.75", "0.35"
    # Cuerpo: prosoma y mesosoma entre el frente y el atrás marcados
    ax.add_patch(Ellipse((0, frente_y - 0.19), 0.30, 0.38, fc=gris, ec=borde, lw=1.2, zorder=3))
    ax.add_patch(Ellipse((0, frente_y - 0.66), 0.36, 0.68, fc=gris, ec=borde, lw=1.2, zorder=3))
    for k in range(1, 7):  # segmentos del mesosoma
        y = frente_y - 0.36 - k * 0.088
        semi = 0.18 * np.sqrt(max(0.0, 1 - ((y - (frente_y - 0.66)) / 0.34) ** 2))
        ax.plot([-semi, semi], [y, y], color=borde, lw=0.7, zorder=4)
    # Cola (metasoma) y telson, curvada hacia un lado
    if COLA_DETRAS_DEL_EJE:
        s = np.linspace(0, 1, 6)
        cola = np.column_stack((0.12 * np.sin(np.pi * s * 0.9), atras_y - 0.75 * s))
        for (x0, y0), (x1, y1), ancho in zip(cola[:-1], cola[1:], np.linspace(0.11, 0.08, 5)):
            ax.add_patch(Ellipse(((x0 + x1) / 2, (y0 + y1) / 2), ancho, 0.17, angle=np.degrees(np.arctan2(x1 - x0, y0 - y1)),
                                 fc=gris, ec=borde, lw=1, zorder=3))
        ax.add_patch(Ellipse((cola[-1, 0] - 0.02, cola[-1, 1] - 0.08), 0.08, 0.13, fc="0.55", ec=borde, lw=1, zorder=3))
    # Pedipalpos con pinzas
    for signo in (-1, 1):
        base, codo, pinza = (signo * 0.10, frente_y - 0.06), (signo * 0.30, frente_y + 0.12), (signo * 0.30, frente_y + 0.36)
        # debajo de las patas (zorder bajo) y más claros, para que no tapen las puntas de P1
        ax.plot(*zip(base, codo, pinza), color="0.8", lw=LINE_SIZE * 2.2, solid_capstyle="round", zorder=0)
        ax.add_patch(Ellipse(pinza, 0.15, 0.24, fc="0.88", ec="0.6", lw=1, zorder=0))
    # Patas: nacen a lo largo del prosoma (supuesto) y terminan en la posición media de su par (dato)
    patas = []
    for clave, d in estadistica.items():
        x, y = _a_xy(d["media_radios"], d["media_angulos"])
        if espejo:
            patas += [(_par(clave), x, y, _etiqueta(d)), (_par(clave), -x, y, _etiqueta(d, espejo_izq=True))]
        else:
            patas.append((_par(clave), x, y, _etiqueta(d)))
    orden = sorted({p for p, _, _, _ in patas})
    for par, x, y, texto in patas:
        k = orden.index(par)
        signo = 1 if x >= 0 else -1
        base = np.array([signo * 0.09, frente_y - 0.12 - 0.075 * k])
        punta = np.array([x, y])
        tramo = punta - base
        normal = np.array([-tramo[1], tramo[0]]) / np.linalg.norm(tramo)
        if normal[0] * signo < 0:  # la rodilla se dobla hacia afuera del cuerpo
            normal = -normal
        rodilla = base + 0.5 * tramo + 0.18 * np.linalg.norm(tramo) * normal
        tarso = punta + 0.10 * (punta - rodilla) / np.linalg.norm(punta - rodilla)
        ax.plot(*zip(base, rodilla, punta, tarso), color=colores[par], lw=LINE_SIZE * 1.6,
                solid_capstyle="round", solid_joinstyle="round", zorder=2)
        ax.plot(*punta, "o", color=colores[par], mec="k", ms=7, zorder=5)
        if MOSTRAR_VALORES:
            ax.annotate(texto, tarso, xytext=(signo * 10, 0), textcoords="offset points", fontsize=TAMANO_VALORES,
                        ha="left" if signo > 0 else "right", va="center", color=colores[par], fontweight="bold",
                        zorder=6, bbox={"fc": "white", "ec": "none", "alpha": 0.8, "pad": 1})


# ----------------------------------------------------------------- figuras
def figuras(resultados, frente_y, colores):
    """resultados: {"Espejo": (estadistica, xy_por_par, pesos_por_par), "Pares": (...)} -> {modo: figura de 1 x 2}.

    Las escalas (alcance del mapa y radio de la guía) son comunes a todos los modos, para poder comparar las figuras.
    """
    plt.rcParams.update({"font.size": TEXT_SIZE})
    todos = np.hstack([xy for _, xy_por_par, _ in resultados.values() for xy in xy_por_par.values()])
    alcance = 1.25 * np.max(np.abs(todos))  # margen para la cola del mapa de calor
    radio_guia = np.mean([d["media_radios"] for est, _, _ in resultados.values() for d in est.values()])
    leyenda = [Patch(fc=mcolors.to_rgba(c, 0.5), ec=c, label=p) for p, c in colores.items()]
    leyenda += [Line2D([], [], marker="D", ls="", color="0.4", mec="k", label="media"),
                Patch(fc="none", ec="0.3", lw=LINE_SIZE, label="IC 95 % (ángulo y radio)")]
    salida = {}
    for modo, (estadistica, xy_por_par, pesos_por_par) in resultados.items():
        espejo = modo.lower().startswith("espejo")
        ancho = TAMANO_FIGURA[0] * (0.8 if espejo else 1)  # en espejo el mapa ocupa media anchura
        fig, (ax_mapa, ax_esquema) = plt.subplots(1, 2, figsize=(ancho, TAMANO_FIGURA[1]), layout="constrained",
                                                  gridspec_kw={"width_ratios": (1, 1.6) if espejo else (1, 1.2)})
        # Izquierda: mapa de calor + IC
        limites = ((0 if espejo else -alcance, alcance), (-alcance, alcance))
        guia_polar(ax_mapa, radio_guia * 1.25, espejo)
        for par, xy in xy_por_par.items():
            mapa_calor(ax_mapa, xy, pesos_por_par[par], colores[par], limites, espejo)
        for clave, d in estadistica.items():
            sector_ic(ax_mapa, d["t-student_radios"], d["t-student_angulos"], colores[_par(clave)])
            ax_mapa.plot(*_a_xy(d["media_radios"], d["media_angulos"]), "D", color=colores[_par(clave)], mec="k", ms=7)
        ax_mapa.set_xlim(*limites[0])
        ax_mapa.set_ylim(*limites[1])
        ax_mapa.set_aspect("equal")
        ax_mapa.set_title("Mapa de calor e IC 95 %")
        ax_mapa.set_xlabel("lateral (largos de cuerpo)  →  derecha")
        ax_mapa.set_ylabel("hacia el frente (largos de cuerpo)")
        # Derecha: esquema con los valores
        escorpion(ax_esquema, estadistica, frente_y, colores, espejo)
        ax_esquema.set_aspect("equal")
        ax_esquema.margins(x=0.45 if MOSTRAR_VALORES else 0.05)  # espacio para las etiquetas a los lados
        ax_esquema.autoscale_view()
        ax_esquema.set_axis_off()
        ax_esquema.set_title("Posiciones medias" + (" (θ y ρ ± mitad del IC 95 %)" if MOSTRAR_VALORES else ""))
        fig.suptitle(modo, fontsize=TEXT_SIZE * 1.3, fontweight="bold")
        fig.legend(handles=leyenda, loc="outside lower center", ncol=len(leyenda), frameon=False)  # sin encimarse
        fig.draw_without_rendering()  # una pasada previa: sin ella el primer guardado encima la leyenda en el eje x
        salida[modo] = fig
    return salida
