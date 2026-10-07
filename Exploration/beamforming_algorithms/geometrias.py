"""
geometrias.py — Geometrías candidatas del arreglo de 8 micrófonos.

Todas las funciones devuelven un arreglo (M, 3) con posiciones x, y, z en
metros. Por ahora todo vive en el plano z = 0; la columna z existe para
que el resto del código ya sea 3D cuando la necesitemos.

Para probar una geometría nueva basta con agregarla a GEOMETRIAS (o pasar
la ruta a un .json con el mismo formato que Avances/geometria.json).
"""

import json
import os

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
RUTA_JSON_AVANCES = os.path.normpath(os.path.join(AQUI, "..", "..", "Avances", "geometria.json"))


def desde_json(ruta=RUTA_JSON_AVANCES):
    """Lee posiciones (M, 3) desde un .json con el formato de Avances/geometria.json."""
    with open(ruta, encoding="utf-8") as f:
        datos = json.load(f)
    mics = sorted(datos["micrófonos"], key=lambda m: m["id"])
    return np.array([[m["x"], m["y"], m["z"]] for m in mics], dtype=float)


def ula(n=8, d=0.02):
    """Arreglo lineal uniforme sobre el eje x, centrado en el origen (baseline del Obj. 7)."""
    x = (np.arange(n) - (n - 1) / 2) * d
    return np.column_stack([x, np.zeros(n), np.zeros(n)])


def circular(n=8, radio=0.045):
    """Arreglo circular uniforme (Beck et al. 2016: 8 MEMS en PCB de 90 mm de diámetro)."""
    ang = 2 * np.pi * np.arange(n) / n
    return np.column_stack([radio * np.cos(ang), radio * np.sin(ang), np.zeros(n)])


def pares_radiales(separaciones=(0.02, 0.04, 0.06, 0.08),
                   orientaciones_deg=(0, 45, 90, 135),
                   radio_centro=0.03):
    """
    4 pares LR con separaciones diferenciadas d1-d4, cada par orientado en
    una dirección distinta y desplazado del centro. Es solo un EJEMPLO de
    geometría no lineal y no uniforme para ejercitar el código — NO es el
    diseño biomimético del TT.
    """
    pos = []
    for d, ang_deg in zip(separaciones, orientaciones_deg):
        ang = np.deg2rad(ang_deg)
        centro = radio_centro * np.array([np.cos(ang), np.sin(ang), 0.0])
        eje = np.array([-np.sin(ang), np.cos(ang), 0.0])   # par perpendicular al radio
        pos.append(centro + eje * d / 2)   # L
        pos.append(centro - eje * d / 2)   # R
    return np.array(pos)


GEOMETRIAS = {
    "placeholder_json": desde_json,          # Avances/geometria.json actual (rejilla 2x4)
    "ula_2cm":          lambda: ula(8, 0.02),
    "circular_beck":    lambda: circular(8, 0.045),
    "pares_radiales":   pares_radiales,
}


def obtener(nombre):
    """Devuelve posiciones (M, 3) por nombre de GEOMETRIAS o por ruta a un .json."""
    if nombre in GEOMETRIAS:
        return GEOMETRIAS[nombre]()
    if os.path.isfile(nombre):
        return desde_json(nombre)
    raise ValueError(f"Geometría desconocida: {nombre!r}. Opciones: {list(GEOMETRIAS)}")


def centroide(pos):
    return pos.mean(axis=0)


def apertura(pos):
    """Distancia máxima entre dos micrófonos (m) — determina la resolución angular alcanzable."""
    dif = pos[:, None, :] - pos[None, :, :]
    return np.linalg.norm(dif, axis=-1).max()


def separacion_minima(pos):
    dif = np.linalg.norm(pos[:, None, :] - pos[None, :, :], axis=-1)
    return dif[np.triu_indices(len(pos), k=1)].min()


def eje_si_colineal(pos, tol=1e-6):
    """
    Si los micrófonos son colineales devuelve el ángulo (deg) de su eje en el
    plano XY; si no, None. Un arreglo colineal no distingue una fuente de su
    espejo respecto al eje (ambigüedad frente/espalda) — relevante para D1.
    """
    centrada = pos - pos.mean(axis=0)
    _, s, vt = np.linalg.svd(centrada)
    if s[1] > tol * max(s[0], 1e-12):
        return None
    return np.rad2deg(np.arctan2(vt[0, 1], vt[0, 0]))
