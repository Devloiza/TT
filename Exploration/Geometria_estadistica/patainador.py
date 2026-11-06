"""Herramienta para anotar la geometría de las patas de escorpiones en fotos de vista superior.

Apoyo al Obj. 1 (geometría del arreglo inspirada en las slit sensilla). Por cada foto se marca:
  1. El eje del cuerpo: un clic al frente y uno atrás.
  2. Las 8 patas caminadoras por pares (P1 = más cercano a la cabeza ... P4 = más cercano a la cola):
     varios clics sobre la zona del basitarso; su centroide es el punto de la pata. El lado
     (izquierda/derecha del animal) se deduce del eje del cuerpo.
  3. Un círculo que se ajusta a los centroides (por mínimos cuadrados o el mínimo que los encierra).

Los datos van a dos CSV versionados en datos/: imagenes.csv (una fila por foto) y puntos.csv (una fila
por clic). Las coordenadas están en píxeles de la imagen original (rotación EXIF corregida), con origen
arriba a la izquierda y el eje y hacia abajo. Las fotos se quedan locales en fotos/<orientación>/.

Se supone vista dorsal (desde arriba): con la cabeza hacia arriba en la foto, la izquierda del animal
queda a la izquierda de la imagen.

Referencia de ángulos: con el eje marcado se dibuja una cruz en el centro del círculo (origen de la
estadística), paralela al eje (0° al frente, 180° atrás) y perpendicular (90°). Con MOSTRAR_ANGULOS cada
pata muestra su ángulo respecto al frente (0 a 180°, igual para las dos patas en espejo); es solo una
guía visual y no se guarda: la perpendicular y los ángulos se deducen del eje en el análisis.

Uso:  python Exploration/Geometria_estadistica/patainador.py

Teclas:
  1-4      elegir el par de la pata que se va a marcar
  Enter    cerrar la pata (mínimo MIN_PUNTOS_PATA puntos)
  n        la pata que falta del par no es visible
  z        deshacer el último punto
  r        regresar el círculo al calculado
  d        descartar la foto (pide un motivo); otra vez para recuperarla
  →  ←     guardar y pasar a la siguiente / anterior
  q        guardar y salir
Mouse:
  clic izquierdo     mientras marcas el eje o una pata: agrega un punto (aunque esté junto a otro).
                     Sin nada en curso: arrastra un punto existente o el centro del círculo.
  clic derecho       borrar el punto más cercano
  rueda              cambiar el radio del círculo
"""
import csv
import datetime
import itertools
import math
from pathlib import Path

import matplotlib

matplotlib.use("TkAgg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image, ImageOps  # noqa: E402

# ----------------------------------------------------------------- configuración
CARPETA_BASE = Path(__file__).resolve().parent
CARPETA_FOTOS = CARPETA_BASE / "fotos"
CARPETA_DATOS = CARPETA_BASE / "datos"
METODO_CIRCULO = "ajuste"  # "ajuste" (mínimos cuadrados) o "minimo" (el menor que encierra los centroides)
MIN_PUNTOS_PATA = 5
MOSTRAR_ANGULOS = True  # ángulo de cada pata respecto al frente, solo en pantalla (no se guarda)

# Tamaños del dibujo (solo en pantalla; útiles para capturas en presentaciones)
TEXT_SIZE = 15  # todos los textos: encabezado, etiquetas de patas y de la cruz de referencia
LINE_SIZE = 3  # grosor de todas las líneas: eje, cruz de referencia y círculo
CENTROID_SIZE = 20  # tamaño del marcador del centroide de cada pata

EXTENSIONES = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"}
PARES = ("P1", "P2", "P3", "P4")
LADOS = ("izq", "der")
COLORES = {"P1": "tab:red", "P2": "tab:orange", "P3": "tab:green", "P4": "tab:blue"}
TOLERANCIA_PX = 10  # distancia en pantalla para tomar un punto existente

COLUMNAS_IMAGENES = ["imagen", "ancho_px", "alto_px", "eje_frente_x", "eje_frente_y", "eje_atras_x",
                     "eje_atras_y", "circulo_metodo", "circulo_x", "circulo_y", "circulo_r",
                     "circulo_manual", "estado", "motivo_descarte", "fecha"]
COLUMNAS_PUNTOS = ["imagen", "par", "lado", "punto", "x", "y", "centroide_x", "centroide_y", "visible"]


# ----------------------------------------------------------------- geometría
def lado_respecto_al_eje(frente, atras, p):
    """'izq' o 'der' del animal para el punto p, con el eje atrás→frente (coordenadas de imagen, y hacia abajo)."""
    ax, ay = frente[0] - atras[0], frente[1] - atras[1]
    cruz = ax * (p[1] - atras[1]) - ay * (p[0] - atras[0])
    return "izq" if cruz < 0 else "der"


def direccion_del_eje(frente, atras):
    """Vector unitario atrás→frente (dirección de 0°) y su perpendicular (dirección de 90°)."""
    ux, uy = frente[0] - atras[0], frente[1] - atras[1]
    norma = math.hypot(ux, uy) or 1.0
    ux, uy = ux / norma, uy / norma
    return (ux, uy), (-uy, ux)


def angulo_respecto_al_frente(origen, frente, atras, p):
    """Ángulo en grados (0 a 180) entre la dirección del frente y el punto p, visto desde el origen."""
    (ux, uy), _ = direccion_del_eje(frente, atras)
    vx, vy = p[0] - origen[0], p[1] - origen[1]
    norma = math.hypot(vx, vy)
    if norma == 0:
        return None
    coseno = max(-1.0, min(1.0, (ux * vx + uy * vy) / norma))
    return math.degrees(math.acos(coseno))


def circulo_ajuste(puntos):
    """Círculo de mínimos cuadrados (ajuste algebraico de Kåsa). None si hay menos de 3 puntos o son colineales."""
    p = np.asarray(puntos, dtype=float)
    if len(p) < 3:
        return None
    a = np.column_stack([2 * p[:, 0], 2 * p[:, 1], np.ones(len(p))])
    b = (p ** 2).sum(axis=1)
    sol, _, rango, _ = np.linalg.lstsq(a, b, rcond=None)
    if rango < 3:
        return None
    cx, cy, c = sol
    return float(cx), float(cy), float(math.sqrt(c + cx ** 2 + cy ** 2))


def _circuncirculo(a, b, c):
    d = 2 * (a[0] * (b[1] - c[1]) + b[0] * (c[1] - a[1]) + c[0] * (a[1] - b[1]))
    if abs(d) < 1e-12:
        return None
    ux = ((a[0] ** 2 + a[1] ** 2) * (b[1] - c[1]) + (b[0] ** 2 + b[1] ** 2) * (c[1] - a[1])
          + (c[0] ** 2 + c[1] ** 2) * (a[1] - b[1])) / d
    uy = ((a[0] ** 2 + a[1] ** 2) * (c[0] - b[0]) + (b[0] ** 2 + b[1] ** 2) * (a[0] - c[0])
          + (c[0] ** 2 + c[1] ** 2) * (b[0] - a[0])) / d
    return ux, uy, math.hypot(a[0] - ux, a[1] - uy)


def circulo_minimo(puntos):
    """El menor círculo que encierra los puntos (búsqueda exhaustiva; bastan pares y tercias para <= 8 puntos)."""
    p = [tuple(map(float, q)) for q in puntos]
    if len(p) < 2:
        return None
    candidatos = []
    for a, b in itertools.combinations(p, 2):
        candidatos.append(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, math.dist(a, b) / 2))
    for a, b, c in itertools.combinations(p, 3):
        cc = _circuncirculo(a, b, c)
        if cc:
            candidatos.append(cc)
    validos = [c for c in candidatos if all(math.dist((c[0], c[1]), q) <= c[2] * (1 + 1e-9) + 1e-9 for q in p)]
    return min(validos, key=lambda c: c[2]) if validos else None


def calcular_circulo(centroides):
    if len(centroides) < 3:
        return None
    return circulo_ajuste(centroides) if METODO_CIRCULO == "ajuste" else circulo_minimo(centroides)


# ----------------------------------------------------------------- datos de una foto
class Anotacion:
    def __init__(self, imagen, ancho, alto):
        self.imagen, self.ancho, self.alto = imagen, ancho, alto
        self.eje_frente = self.eje_atras = None
        self.patas = {}  # (par, lado) -> {"puntos": [[x, y], ...], "visible": bool}
        self.circulo = None  # (cx, cy, r)
        self.circulo_manual = False
        self.circulo_metodo = METODO_CIRCULO
        self.estado = "en_progreso"
        self.motivo = ""
        self.fecha = ""

    def centroide(self, clave):
        pts = self.patas[clave]["puntos"]
        return tuple(np.mean(pts, axis=0)) if pts else None

    def centroides(self):
        return [self.centroide(k) for k, v in self.patas.items() if v["visible"] and v["puntos"]]

    def recalcular_circulo(self):
        if not self.circulo_manual:
            self.circulo = calcular_circulo(self.centroides())
            self.circulo_metodo = METODO_CIRCULO

    def faltantes(self):
        """Lista de lo que falta para que la foto quede completa (vacía si está completa)."""
        faltan = []
        if self.eje_frente is None or self.eje_atras is None:
            faltan.append("eje")
        for par, lado in itertools.product(PARES, LADOS):
            pata = self.patas.get((par, lado))
            if pata is None:
                faltan.append(f"{par}-{lado}")
            elif pata["visible"] and len(pata["puntos"]) < MIN_PUNTOS_PATA:
                faltan.append(f"{par}-{lado} (<{MIN_PUNTOS_PATA} puntos)")
        if self.circulo is None:
            faltan.append("círculo")
        return faltan

    def actualizar_estado(self):
        if self.estado != "descartada":
            self.estado = "completa" if not self.faltantes() else "en_progreso"

    def firma(self):
        """Todo lo que se guarda en los CSV salvo la fecha, redondeado como en el CSV (para detectar cambios reales)."""
        redondear = lambda p: None if p is None else tuple(_num(v) for v in p)
        patas = tuple(sorted((k, v["visible"], tuple(redondear(p) for p in v["puntos"])) for k, v in self.patas.items()))
        return (redondear(self.eje_frente), redondear(self.eje_atras), redondear(self.circulo),
                self.circulo_metodo if self.circulo else "", self.circulo_manual, self.estado, self.motivo, patas)


# ----------------------------------------------------------------- CSV
def _num(v):
    return "" if v is None else round(float(v), 2)


def guardar_csv(anotaciones, carpeta_datos):
    carpeta_datos.mkdir(parents=True, exist_ok=True)
    with open(carpeta_datos / "imagenes.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, COLUMNAS_IMAGENES)
        w.writeheader()
        for a in sorted(anotaciones.values(), key=lambda a: a.imagen):
            c = a.circulo or (None, None, None)
            w.writerow({"imagen": a.imagen, "ancho_px": a.ancho, "alto_px": a.alto,
                        "eje_frente_x": _num(a.eje_frente and a.eje_frente[0]),
                        "eje_frente_y": _num(a.eje_frente and a.eje_frente[1]),
                        "eje_atras_x": _num(a.eje_atras and a.eje_atras[0]),
                        "eje_atras_y": _num(a.eje_atras and a.eje_atras[1]),
                        "circulo_metodo": a.circulo_metodo if a.circulo else "",
                        "circulo_x": _num(c[0]), "circulo_y": _num(c[1]), "circulo_r": _num(c[2]),
                        "circulo_manual": int(a.circulo_manual), "estado": a.estado,
                        "motivo_descarte": a.motivo, "fecha": a.fecha})
    with open(carpeta_datos / "puntos.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, COLUMNAS_PUNTOS)
        w.writeheader()
        for a in sorted(anotaciones.values(), key=lambda a: a.imagen):
            for (par, lado) in sorted(a.patas):
                pata = a.patas[(par, lado)]
                if not pata["visible"]:
                    w.writerow({"imagen": a.imagen, "par": par, "lado": lado, "punto": "", "x": "", "y": "",
                                "centroide_x": "", "centroide_y": "", "visible": 0})
                    continue
                cx, cy = a.centroide((par, lado))
                for i, (x, y) in enumerate(pata["puntos"], start=1):
                    w.writerow({"imagen": a.imagen, "par": par, "lado": lado, "punto": i, "x": _num(x),
                                "y": _num(y), "centroide_x": _num(cx), "centroide_y": _num(cy), "visible": 1})


def cargar_csv(carpeta_datos):
    anotaciones = {}
    ruta_img, ruta_pts = carpeta_datos / "imagenes.csv", carpeta_datos / "puntos.csv"
    if not ruta_img.exists():
        return anotaciones
    flotante = lambda v: float(v) if v not in ("", None) else None
    with open(ruta_img, newline="", encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            a = Anotacion(fila["imagen"], int(fila["ancho_px"]), int(fila["alto_px"]))
            if fila["eje_frente_x"]:
                a.eje_frente = (flotante(fila["eje_frente_x"]), flotante(fila["eje_frente_y"]))
            if fila["eje_atras_x"]:
                a.eje_atras = (flotante(fila["eje_atras_x"]), flotante(fila["eje_atras_y"]))
            if fila["circulo_x"]:
                a.circulo = tuple(flotante(fila[k]) for k in ("circulo_x", "circulo_y", "circulo_r"))
                a.circulo_metodo = fila["circulo_metodo"]
            a.circulo_manual = fila["circulo_manual"] == "1"
            a.estado, a.motivo, a.fecha = fila["estado"], fila["motivo_descarte"], fila["fecha"]
            anotaciones[a.imagen] = a
    if ruta_pts.exists():
        with open(ruta_pts, newline="", encoding="utf-8") as f:
            for fila in csv.DictReader(f):
                a = anotaciones.get(fila["imagen"])
                if a is None:
                    continue
                pata = a.patas.setdefault((fila["par"], fila["lado"]), {"puntos": [], "visible": True})
                if fila["visible"] == "0":
                    pata["visible"] = False
                else:
                    pata["puntos"].append([float(fila["x"]), float(fila["y"])])
    return anotaciones


# ----------------------------------------------------------------- interfaz
class Anotador:
    def __init__(self, carpeta, carpeta_fotos=CARPETA_FOTOS, carpeta_datos=CARPETA_DATOS):
        self.carpeta_fotos, self.carpeta_datos = Path(carpeta_fotos), Path(carpeta_datos)
        self.fotos = sorted(p for p in Path(carpeta).iterdir() if p.suffix.lower() in EXTENSIONES)
        if not self.fotos:
            raise SystemExit(f"No hay fotos en {carpeta}")
        self.anotaciones = cargar_csv(self.carpeta_datos)
        self.indice = next((i for i, p in enumerate(self.fotos)
                            if self._anotacion_de(p, crear=False) is None
                            or self._anotacion_de(p, crear=False).estado == "en_progreso"), 0)
        for clave in ("keymap.back", "keymap.forward", "keymap.home", "keymap.quit", "keymap.save"):
            plt.rcParams[clave] = [k for k in plt.rcParams[clave] if k not in ("left", "right", "r", "q", "s")]
        self.fig, self.ax = plt.subplots(figsize=(11, 8))
        self.fig.subplots_adjust(left=0.02, right=0.98, top=0.9, bottom=0.03)
        self.artistas = []
        self.arrastre = None  # ("eje", "frente"|"atras") | ("pata", clave, i) | ("actual", i) | ("circulo",)
        self.mensaje = ""
        for evento, funcion in (("button_press_event", self.al_presionar), ("button_release_event", self.al_soltar),
                                ("motion_notify_event", self.al_mover), ("key_press_event", self.al_teclear),
                                ("scroll_event", self.al_girar), ("close_event", self.al_cerrar)):
            self.fig.canvas.mpl_connect(evento, funcion)
        self.cargar_foto()

    # ---- foto actual
    def _clave(self, ruta):
        try:
            return ruta.resolve().relative_to(self.carpeta_fotos.resolve()).as_posix()
        except ValueError:
            return ruta.name

    def _anotacion_de(self, ruta, crear=True, tamano=None):
        clave = self._clave(ruta)
        if clave not in self.anotaciones and crear:
            self.anotaciones[clave] = Anotacion(clave, *tamano)
        return self.anotaciones.get(clave)

    def cargar_foto(self):
        ruta = self.fotos[self.indice]
        with Image.open(ruta) as im:
            imagen = np.asarray(ImageOps.exif_transpose(im).convert("RGB"))
        self.a = self._anotacion_de(ruta, tamano=(imagen.shape[1], imagen.shape[0]))
        self.firma_guardada = self.a.firma()  # antes de recalcular: un cambio de METODO_CIRCULO sí cuenta como cambio
        self.a.recalcular_circulo()  # con el METODO_CIRCULO vigente, salvo que se haya ajustado a mano
        self.par_actual, self.puntos_actuales, self.esperando_lado_oculto = None, [], False
        self.ax.clear()
        self.ax.imshow(imagen)
        self.ax.set_axis_off()
        self.artistas = []
        self.mensaje = "" if self.a.eje_atras else "Marca el eje: clic al FRENTE del cuerpo."
        self.redibujar()

    def guardar(self):
        self.a.actualizar_estado()
        if self.a.firma() != self.firma_guardada:  # la fecha es la de la última modificación, no la de la última vista
            self.a.fecha = datetime.date.today().isoformat()
            self.firma_guardada = self.a.firma()
        guardar_csv(self.anotaciones, self.carpeta_datos)

    # ---- dibujo
    def redibujar(self):
        for art in self.artistas:
            art.remove()
        self.artistas = []
        dib = self.artistas.append
        a = self.a
        for nombre, p in (("frente", a.eje_frente), ("atrás", a.eje_atras)):
            if p:
                dib(self.ax.plot(*p, "w^" if nombre == "frente" else "wv", ms=10, mec="k")[0])
        eje_listo = a.eje_frente is not None and a.eje_atras is not None
        origen = None
        if eje_listo:
            xs, ys = zip(a.eje_atras, a.eje_frente)
            dib(self.ax.plot(xs, ys, "w--", lw=LINE_SIZE)[0])
            # Cruz de referencia: paralela al eje (0° al frente, 180° atrás) y perpendicular (90°), en el centro
            # del círculo (origen de la estadística) o, sin círculo, en el punto medio del eje.
            if a.circulo:
                origen, largo = a.circulo[:2], a.circulo[2] * 1.15
            else:
                origen = ((a.eje_frente[0] + a.eje_atras[0]) / 2, (a.eje_frente[1] + a.eje_atras[1]) / 2)
                largo = math.dist(a.eje_frente, a.eje_atras) / 2
            (ux, uy), (vx, vy) = direccion_del_eje(a.eje_frente, a.eje_atras)
            ox, oy = origen
            for (dx, dy), etiquetas in (((ux, uy), ("0°", "180°")), ((vx, vy), ("90°", "90°"))):
                dib(self.ax.plot([ox - dx * largo, ox + dx * largo], [oy - dy * largo, oy + dy * largo],
                                 color="yellow", lw=LINE_SIZE, ls=":")[0])
                for signo, texto in ((1, etiquetas[0]), (-1, etiquetas[1])):
                    dib(self.ax.annotate(texto, (ox + signo * dx * largo, oy + signo * dy * largo), color="yellow",
                                         fontsize=TEXT_SIZE, ha="center", va="center",
                                         bbox={"fc": "black", "alpha": 0.5, "pad": 1, "lw": 0}))
        for (par, lado), pata in a.patas.items():
            if not pata["visible"] or not pata["puntos"]:
                continue
            pts = np.array(pata["puntos"])
            dib(self.ax.plot(pts[:, 0], pts[:, 1], "o", color=COLORES[par], ms=4, mec="k", mew=0.5)[0])
            cx, cy = a.centroide((par, lado))
            dib(self.ax.plot(cx, cy, "P", color=COLORES[par], ms=CENTROID_SIZE, mec="w")[0])
            aviso = "!" if len(pts) < MIN_PUNTOS_PATA else ""
            angulo = ""
            if MOSTRAR_ANGULOS and origen is not None:
                theta = angulo_respecto_al_frente(origen, a.eje_frente, a.eje_atras, (cx, cy))
                angulo = f" {theta:.0f}°" if theta is not None else ""
            dib(self.ax.annotate(f"{par}-{lado}{aviso}{angulo}", (cx, cy), xytext=(6, 6), textcoords="offset points",
                                 color="w", fontsize=TEXT_SIZE, bbox={"fc": COLORES[par], "alpha": 0.7, "pad": 1}))
        if self.puntos_actuales:
            pts = np.array(self.puntos_actuales)
            dib(self.ax.plot(pts[:, 0], pts[:, 1], "x", color=COLORES[self.par_actual], ms=8, mew=2)[0])
        if a.circulo:
            cx, cy, r = a.circulo
            estilo = "-" if a.circulo_manual else "--"
            dib(self.ax.add_patch(plt.Circle((cx, cy), r, fill=False, color="cyan", lw=LINE_SIZE, ls=estilo)))
            dib(self.ax.plot(cx, cy, "c+", ms=14, mew=2)[0])
        ocultas = [f"{p}-{l}" for (p, l), v in a.patas.items() if not v["visible"]]
        estado = "DESCARTADA: " + a.motivo if a.estado == "descartada" else ", ".join(a.faltantes()[:6]) or "completa"
        linea1 = (f"[{self.indice + 1}/{len(self.fotos)}] {a.imagen}   |   par: {self.par_actual or '-'}"
                  f" ({len(self.puntos_actuales)} pts)   |   círculo: {METODO_CIRCULO}"
                  f"{' (manual)' if a.circulo_manual else ''}")
        linea2 = f"Falta: {estado}" + (f"   |   no visibles: {', '.join(ocultas)}" if ocultas else "")
        self.ax.set_title(f"{linea1}\n{linea2}\n{self.mensaje}", fontsize=TEXT_SIZE, loc="left")
        self.fig.canvas.draw_idle()

    # ---- utilidades
    def _en_pantalla(self, x, y):
        return self.ax.transData.transform((x, y))

    def _punto_cercano(self, evento):
        """El elemento más cercano al cursor dentro de la tolerancia, o None."""
        candidatos = []
        a = self.a
        if a.eje_frente:
            candidatos.append((("eje", "frente"), a.eje_frente))
        if a.eje_atras:
            candidatos.append((("eje", "atras"), a.eje_atras))
        for clave, pata in a.patas.items():
            for i, p in enumerate(pata["puntos"]):
                candidatos.append((("pata", clave, i), p))
        for i, p in enumerate(self.puntos_actuales):
            candidatos.append((("actual", i), p))
        if a.circulo:
            candidatos.append((("circulo",), a.circulo[:2]))
        mejor, dist = None, TOLERANCIA_PX
        for ref, p in candidatos:
            sx, sy = self._en_pantalla(*p)
            d = math.hypot(sx - evento.x, sy - evento.y)
            if d <= dist:
                mejor, dist = ref, d
        return mejor

    def _barra_activa(self):
        barra = self.fig.canvas.toolbar
        return barra is not None and bool(barra.mode)

    def _tras_editar(self):
        self.a.recalcular_circulo()
        self.a.actualizar_estado()

    # ---- mouse
    def al_presionar(self, ev):
        if ev.inaxes != self.ax or self._barra_activa() or ev.xdata is None:
            return
        if self.a.estado == "descartada":
            self.mensaje = "Foto descartada: presiona d para recuperarla."
            return self.redibujar()
        cercano = self._punto_cercano(ev)
        if ev.button == 3:
            return self._borrar(cercano)
        if ev.button != 1:
            return
        a = self.a
        # Mientras se marca algo (eje, pata, lado oculto) el clic siempre agrega: los puntos del basitarso
        # quedan muy juntos y un clic cercano no debe confundirse con arrastrar. Se arrastra fuera de ese modo.
        marcando = a.eje_frente is None or a.eje_atras is None or self.par_actual or self.esperando_lado_oculto
        if cercano and not marcando:
            self.arrastre = cercano
            return
        p = (ev.xdata, ev.ydata)
        if a.eje_frente is None:
            a.eje_frente, self.mensaje = p, "Ahora clic ATRÁS del cuerpo (base de la cola)."
        elif a.eje_atras is None:
            a.eje_atras, self.mensaje = p, "Eje listo. Elige un par con 1-4 y marca el basitarso."
        elif self.esperando_lado_oculto:
            lado = lado_respecto_al_eje(a.eje_frente, a.eje_atras, p)
            a.patas[(self.par_actual, lado)] = {"puntos": [], "visible": False}
            self.esperando_lado_oculto, self.mensaje = False, f"{self.par_actual}-{lado} marcada como no visible."
            self._tras_editar()
        elif self.par_actual:
            self.puntos_actuales.append(list(p))
            n = len(self.puntos_actuales)
            self.mensaje = (f"{self.par_actual}: {n} puntos" +
                            (". Enter para cerrar la pata." if n >= MIN_PUNTOS_PATA else f" (mínimo {MIN_PUNTOS_PATA})."))
        else:
            self.mensaje = "Elige primero un par con las teclas 1-4."
        self.redibujar()

    def al_mover(self, ev):
        if not self.arrastre or ev.inaxes != self.ax or ev.xdata is None:
            return
        p, a, ref = [ev.xdata, ev.ydata], self.a, self.arrastre
        if ref[0] == "eje":
            setattr(a, "eje_frente" if ref[1] == "frente" else "eje_atras", tuple(p))
        elif ref[0] == "pata":
            a.patas[ref[1]]["puntos"][ref[2]] = p
        elif ref[0] == "actual":
            self.puntos_actuales[ref[1]] = p
        elif ref[0] == "circulo":
            a.circulo, a.circulo_manual = (p[0], p[1], a.circulo[2]), True
        if ref[0] == "pata":
            a.recalcular_circulo()
        self.redibujar()

    def al_soltar(self, ev):
        if self.arrastre:
            self.arrastre = None
            self._tras_editar()
            self.redibujar()

    def al_girar(self, ev):
        if self.a.circulo and ev.inaxes == self.ax:
            cx, cy, r = self.a.circulo
            self.a.circulo = (cx, cy, r * (1.03 if ev.button == "up" else 1 / 1.03))
            self.a.circulo_manual = True
            self.redibujar()

    def _borrar(self, ref):
        a = self.a
        if ref is None:
            return
        if ref[0] == "eje":
            setattr(a, "eje_frente" if ref[1] == "frente" else "eje_atras", None)
            self.mensaje = "Punto del eje borrado: vuelve a marcarlo."
        elif ref[0] == "pata":
            pts = a.patas[ref[1]]["puntos"]
            pts.pop(ref[2])
            if not pts:
                del a.patas[ref[1]]
            self.mensaje = f"Punto borrado de {ref[1][0]}-{ref[1][1]}."
        elif ref[0] == "actual":
            self.puntos_actuales.pop(ref[1])
        self._tras_editar()
        self.redibujar()

    # ---- teclado
    def al_teclear(self, ev):
        a, k = self.a, ev.key
        if k in ("right", "left"):
            self._navegar(1 if k == "right" else -1)
            return
        if k == "q":
            self.guardar()
            plt.close(self.fig)
            return
        if k == "d":
            return self._descartar()
        if a.estado == "descartada":
            return
        if k in ("1", "2", "3", "4"):
            par = f"P{k}"
            if self.puntos_actuales:
                self.mensaje = f"Primero cierra {self.par_actual} con Enter o borra sus puntos con z."
            elif a.eje_atras is None:
                self.mensaje = "Primero marca el eje del cuerpo (frente y atrás)."
            elif all((par, l) in a.patas for l in LADOS):
                self.mensaje = f"{par} ya tiene sus dos patas. Para corregir, arrastra o borra puntos."
            else:
                self.par_actual, self.esperando_lado_oculto = par, False
                self.mensaje = f"{par}: haz clic sobre el basitarso (mínimo {MIN_PUNTOS_PATA} puntos) y Enter."
        elif k == "enter":
            self._cerrar_pata()
        elif k == "n":
            self._pata_no_visible()
        elif k == "z":
            if self.puntos_actuales:
                self.puntos_actuales.pop()
            elif a.eje_atras is not None and not a.patas:
                a.eje_atras = None
            elif a.eje_frente is not None and not a.patas:
                a.eje_frente = None
        elif k == "r":
            a.circulo_manual = False
            a.recalcular_circulo()
            self.mensaje = "Círculo recalculado."
        else:
            return
        self.redibujar()

    def _cerrar_pata(self):
        a, pts = self.a, self.puntos_actuales
        if not self.par_actual or not pts:
            self.mensaje = "No hay pata en curso."
            return
        if len(pts) < MIN_PUNTOS_PATA:
            self.mensaje = f"Faltan puntos: {len(pts)} de {MIN_PUNTOS_PATA}."
            return
        lado = lado_respecto_al_eje(a.eje_frente, a.eje_atras, tuple(np.mean(pts, axis=0)))
        if (self.par_actual, lado) in a.patas:
            self.mensaje = (f"¡Ya existe {self.par_actual}-{lado}! Las dos patas del par quedaron del mismo lado "
                            f"del eje. Revisa el eje o los puntos (z deshace).")
            return
        a.patas[(self.par_actual, lado)] = {"puntos": [list(p) for p in pts], "visible": True}
        self.mensaje = f"{self.par_actual}-{lado} cerrada."
        self.par_actual, self.puntos_actuales = None, []
        self._tras_editar()

    def _pata_no_visible(self):
        a, par = self.a, self.par_actual
        if not par or self.puntos_actuales:
            self.mensaje = "Elige el par con 1-4 (sin puntos en curso) y luego n."
            return
        existentes = [l for l in LADOS if (par, l) in a.patas]
        if len(existentes) == 1:
            lado = "der" if existentes[0] == "izq" else "izq"
            a.patas[(par, lado)] = {"puntos": [], "visible": False}
            self.par_actual, self.mensaje = None, f"{par}-{lado} marcada como no visible."
            self._tras_editar()
        else:
            self.esperando_lado_oculto = True
            self.mensaje = f"Haz clic donde estaría la pata oculta de {par} (solo para saber de qué lado es)."

    def _descartar(self):
        a = self.a
        if a.estado == "descartada":
            a.estado, a.motivo = "en_progreso", ""
            self._tras_editar()
            self.mensaje = "Foto recuperada."
        else:
            from tkinter import simpledialog
            motivo = simpledialog.askstring("Descartar foto", "Motivo:", parent=self.fig.canvas.get_tk_widget())
            if motivo is None:
                return
            a.estado, a.motivo = "descartada", motivo.strip() or "sin motivo"
            self.mensaje = "Foto descartada."
        self.guardar()
        self.redibujar()

    def _navegar(self, paso):
        if self.puntos_actuales:
            self.mensaje = f"Cierra {self.par_actual} con Enter o borra sus puntos con z antes de cambiar de foto."
            return self.redibujar()
        self.guardar()
        nuevo = self.indice + paso
        if not 0 <= nuevo < len(self.fotos):
            self.mensaje = "Es la última foto." if paso > 0 else "Es la primera foto."
            return self.redibujar()
        self.indice = nuevo
        self.cargar_foto()

    def al_cerrar(self, ev):
        self.guardar()


def main():
    import tkinter as tk
    from tkinter import filedialog
    CARPETA_FOTOS.mkdir(parents=True, exist_ok=True)
    raiz = tk.Tk()
    raiz.withdraw()
    carpeta = filedialog.askdirectory(title="Elige la carpeta de fotos (orientación)", initialdir=CARPETA_FOTOS)
    raiz.destroy()
    if not carpeta:
        return
    # Hay que conservar la referencia: matplotlib guarda los callbacks de mouse y teclado como referencias
    # débiles, y si el objeto se libera los clics dejan de hacer algo.
    anotador = Anotador(carpeta)
    plt.show()
    return anotador


if __name__ == "__main__":
    main()
