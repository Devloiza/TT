"""Exporta los datos para estimar el error de la proyección del centro del círculo sobre el eje del cuerpo.

Hecho por Claude con la especificación del autor (petición de un asesor, 2026-11-15). Es una utilidad de
exportación: no hace estadística. Lee las anotaciones de datos/ (las mismas que usa patainador.py) y escribe en
SALIDAS/Escorpiones_estadistica/:

  error_proyeccion.csv   una fila por foto procesable, todo en píxeles de la imagen original:
      imagen             nombre del archivo (coincide con la foto copiada en la misma carpeta)
      D_px               largo del eje frente-atrás, |f - t|
      l_px               de la proyección del centro al frente, medido a lo largo del eje:
                         l = D - (o - t)·u. Positivo si la proyección queda detrás del frente
      r_px               radio del círculo
      frente_x/_y, atras_x/_y, centro_x/_y   puntos marcados y centro del círculo
  <foto>.png             una figura por foto procesable, con el mismo nombre que la columna "imagen" pero
                         en .png. A la izquierda la foto sola y a la derecha con lo que dibuja el
                         patainador (eje, clics, centroides, círculo, centro y proyección). Título con la
                         especie y leyenda con cada elemento

"Procesable" = no descartada y con eje y círculo (el mismo criterio que estadistica_imagenes.py).

Uso:  python Exploration/Geometria_estadistica/exportar_error_proyeccion.py
"""
import csv
import math
from pathlib import Path

import numpy as np
from matplotlib.lines import Line2D
from PIL import Image, ImageOps

import patainador

plt = patainador.plt
plt.switch_backend("Agg")  # patainador usa TkAgg para su ventana; aquí solo se guardan archivos

TAMANO_TEXTO = 12
GROSOR_LINEA = 2
TAMANO_CENTROIDE = 14
CARPETA_SALIDA = Path(__file__).resolve().parents[2] / "SALIDAS" / "Escorpiones_estadistica"
COLUMNAS = ["imagen", "D_px", "l_px", "r_px", "frente_x", "frente_y", "atras_x", "atras_y", "centro_x", "centro_y"]


def fila_de(a):
    """Valores de una foto. Usa la misma dirección del eje y el mismo redondeo que el patainador."""
    f, t, (cx, cy, r) = a.eje_frente, a.eje_atras, a.circulo
    (ux, uy), _ = patainador.direccion_del_eje(f, t)
    largo = math.dist(f, t)
    a_lo_largo = (cx - t[0]) * ux + (cy - t[1]) * uy  # de "atrás" a la proyección del centro
    n = patainador._num
    return {"imagen": Path(a.imagen).name, "D_px": n(largo), "l_px": n(largo - a_lo_largo), "r_px": n(r),
            "frente_x": n(f[0]), "frente_y": n(f[1]), "atras_x": n(t[0]), "atras_y": n(t[1]),
            "centro_x": n(cx), "centro_y": n(cy)}


def especie(nombre_archivo):
    """'heterometrus_spinifer_3.jpg' -> 'Heterometrus spinifer' (quita el número final de la foto)."""
    partes = Path(nombre_archivo).stem.split("_")
    if partes[-1].isdigit():
        partes = partes[:-1]
    texto = " ".join(partes)
    return texto[:1].upper() + texto[1:]


def figura(a, ruta_foto):
    """Foto sola (izquierda) y foto con la anotación como la dibuja el patainador (derecha)."""
    with Image.open(ruta_foto) as im:
        imagen = np.asarray(ImageOps.exif_transpose(im).convert("RGB"))  # mismas coordenadas que el patainador
    alto, ancho = imagen.shape[:2]
    fig, (ax_foto, ax_anot) = plt.subplots(1, 2, figsize=(14, max(4.0, 7 * alto / ancho) + 1.2))
    for ax in (ax_foto, ax_anot):
        ax.imshow(imagen)
        ax.set_axis_off()
    f, t, (cx, cy, r) = a.eje_frente, a.eje_atras, a.circulo
    # Eje con frente y atrás
    ax_anot.plot(*zip(t, f), "w--", lw=GROSOR_LINEA)
    ax_anot.plot(*f, "w^", ms=10, mec="k")
    ax_anot.plot(*t, "wv", ms=10, mec="k")
    # Clics y centroide de cada pata visible
    for (par, lado), pata in a.patas.items():
        if not pata["visible"] or not pata["puntos"]:
            continue
        pts = np.array(pata["puntos"])
        color = patainador.COLORES[par]
        ax_anot.plot(pts[:, 0], pts[:, 1], "o", color=color, ms=3, mec="k", mew=0.4)
        ax_anot.plot(*a.centroide((par, lado)), "P", color=color, ms=TAMANO_CENTROIDE, mec="w")
    # Círculo, centro y proyección del centro sobre el eje
    estilo = "-" if a.circulo_manual else "--"
    ax_anot.add_patch(plt.Circle((cx, cy), r, fill=False, color="cyan", lw=GROSOR_LINEA, ls=estilo))
    ax_anot.plot(cx, cy, "c+", ms=14, mew=2)
    px, py = a.proyeccion_centro()
    ax_anot.plot([cx, px], [cy, py], color="cyan", lw=GROSOR_LINEA / 2, ls=":")
    ax_anot.plot(px, py, "D", color="cyan", ms=TAMANO_CENTROIDE / 2, mec="k")
    ax_anot.set_xlim(0, ancho)
    ax_anot.set_ylim(alto, 0)
    fig.suptitle(especie(a.imagen), fontsize=TAMANO_TEXTO + 4, fontstyle="italic")
    gris = "0.5"
    leyenda = [Line2D([], [], color=gris, ls="--", lw=GROSOR_LINEA, label="Eje del cuerpo"),
               Line2D([], [], marker="^", ls="", color="w", mec="k", ms=10, label="Frente"),
               Line2D([], [], marker="v", ls="", color="w", mec="k", ms=10, label="Atrás (inicio de la cola)")]
    leyenda += [Line2D([], [], marker="P", ls="", color=c, mec="w", ms=TAMANO_CENTROIDE * 0.8,
                       label=f"{p}: clics y centroide") for p, c in patainador.COLORES.items()]
    leyenda += [Line2D([], [], color="cyan", ls=estilo, lw=GROSOR_LINEA,
                       label="Círculo" + (" (manual)" if a.circulo_manual else " (ajuste)")),
                Line2D([], [], marker="+", ls="", color="cyan", mew=2, ms=12, label="Centro del círculo"),
                Line2D([], [], marker="D", ls=":", color="cyan", mec="k", ms=7,
                       label="Proyección del centro sobre el eje")]
    fig.legend(handles=leyenda, loc="lower center", ncol=5, fontsize=TAMANO_TEXTO, frameon=False)
    fig.tight_layout(rect=(0, 0.12, 1, 0.95))
    return fig


def main():
    anotaciones = patainador.cargar_csv(patainador.CARPETA_DATOS)
    procesables = sorted((a for a in anotaciones.values()
                          if a.estado != "descartada" and a.eje_frente and a.eje_atras and a.circulo),
                         key=lambda a: a.imagen)
    CARPETA_SALIDA.mkdir(parents=True, exist_ok=True)
    with open(CARPETA_SALIDA / "error_proyeccion.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, COLUMNAS)
        w.writeheader()
        for a in procesables:
            w.writerow(fila_de(a))
    faltantes = []
    for a in procesables:
        origen = patainador.CARPETA_FOTOS / a.imagen
        if not origen.exists():
            faltantes.append(a.imagen)
            continue
        fig = figura(a, origen)
        fig.savefig(CARPETA_SALIDA / (Path(a.imagen).stem + ".png"), dpi=150)
        plt.close(fig)
    print(f"{len(procesables)} fotos procesables de {len(anotaciones)} -> {CARPETA_SALIDA}")
    if faltantes:
        print("No se encontraron estas fotos (la fila sí está en el CSV):", *faltantes, sep="\n  ")


if __name__ == "__main__":
    main()
