import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import scipy.stats

import graficas_patas  # parte visual (opción B): mapa de calor, sectores del IC y esquema del escorpión

os.system('cls')
DEBUG = True
imagenes = pd.read_csv(r"Exploration\Geometria_estadistica\datos\imagenes.csv")
puntos = pd.read_csv(r"Exploration\Geometria_estadistica\datos\puntos.csv")

## Comprobaciones de datos
if DEBUG:
    print(imagenes.head())
    print(puntos.head())
    print(imagenes.keys())
    print(puntos.keys())

## Mapa de saturación generado por los puntos de cada pata
pares = puntos['par'].unique()
# Sin descartadas. Las en_progreso sí entran: les falta una pata oculta bajo la pinza, pero el eje y el círculo existen
nombres_imagenes = imagenes[imagenes['estado'] != 'descartada']['imagen'].unique()

# Ajustes
COLORES = {"P1": "tab:red", "P2": "tab:orange", "P3": "tab:green", "P4": "tab:blue"}
MODOS = {"Espejo": True, "Pares": False}  # True: junta izq y der en espejo (un centroide por par); False: los separa
SALIDA = os.path.join("SALIDAS", "geometria_patas_{}.png")  # una figura por modo

def orientainador(ORIGEN:np.ndarray, FRENTE:np.ndarray, ATRAS:np.ndarray, X:np.ndarray, Y:np.ndarray, ABS:bool = False, DBG:bool = False) -> np.ndarray:
    '''
    Orienta la imagen para la estadística.

    Args:
        ORIGEN (np.ndarray): Centro del círculo
        FRENTE (np.ndarray): Coordenadas del eje (frente)
        ATRAS (np.ndarray): Coordenadas del eje (atrás)
        X (np.ndarray): Puntos en X
        Y (np.ndarray): Puntos en Y

    Returns:
        rho (np.ndarray): Radio generado por los puntos en la pata del escorpión
        theta (np.ndarray): Ángulo generado por los puntos en la pata del escorpión
    '''
    # Vector unitario
    s = np.sqrt(np.pow(FRENTE[0]-ATRAS[0],2)+np.pow(FRENTE[1]-ATRAS[1],2))
    u = np.array([FRENTE[0]-ATRAS[0], FRENTE[1]-ATRAS[1]])/s
    # Perpendicular
    v = np.array([-u[1], u[0]])

    # Ajuste al centro
    XY_ajustado = np.array([X-ORIGEN[0], Y-ORIGEN[1]])

    # Rotar
    a = np.array(XY_ajustado[0]*u[0]+ XY_ajustado[1]*u[1])
    l = np.array(XY_ajustado[0]*v[0]+ XY_ajustado[1]*v[1])

    # Angulo y radio
    th = np.atan2(np.abs(l) if ABS else l, a)
    rho = np.sqrt(np.pow(l,2)+np.pow(a,2))
    rho_escalado = rho/s
    if DBG:
        print(u,v)
        print(XY_ajustado)
        print(a, l)
        print(XY_ajustado.shape)
        print(th, rho_escalado)
    return rho_escalado, th

def analizar(ESPEJO:bool):
    '''
    Centroides y estadística de cada par en un modo.

    Returns:
        estadistica (dict): por clave (P1 en espejo, o P1-izq y P1-der), centroides por foto, radios, ángulos, medias e IC
        xy_por_par (dict): por par, todos los clics en el marco del cuerpo, forma (2, n)
        pesos_por_par (dict): por par, el peso de cada clic para el mapa de calor (cada foto pesa lo mismo)
    '''
    estadistica = {}  # mismas claves que centroides: P1 en espejo, o P1-izq y P1-der separado
    xy_por_par, pesos_por_par = {}, {}
    for par in pares:
        puntos_par = puntos[(puntos['par'] == par) & (puntos['visible'] == 1)]
        if DEBUG: print(par)
        xy_completo = np.empty((2,0))  # fila 0: x, fila 1: y; una columna por punto
        pesos_completo = np.empty(0)
        # Un centroide por foto: una sola lista en espejo, o una por lado
        centroides = {f'{par}': []} if ESPEJO else {f'{par}-{nombre_lado}': [] for nombre_lado in ('izq', 'der')}
        for imagen in nombres_imagenes:
            datos_imagen = imagenes[(imagenes['imagen']==imagen)].copy().reset_index(drop = True)
            origen = np.array([datos_imagen['circulo_x'][0], datos_imagen['circulo_y'][0]])
            frente = np.array([datos_imagen['eje_frente_x'][0], datos_imagen['eje_frente_y'][0]])
            atras = np.array([datos_imagen['eje_atras_x'][0], datos_imagen['eje_atras_y'][0]])

            # PUNTOS DE LA IMAGEN
            puntos_imagen = puntos_par[puntos_par['imagen'] == imagen]
            x = np.array(puntos_imagen['x'])
            y = np.array(puntos_imagen['y'])
            lado = np.array(puntos_imagen['lado'])  # mismo tamaño y orden que x, y

            # Dirección del cuerpo
            rho, theta = orientainador(origen, frente, atras, x, y, ABS = ESPEJO, DBG = False)

            xy = np.array([rho*np.sin(theta), rho*np.cos(theta)])
            xy_completo = np.hstack((xy_completo, xy))

            # Centroides, paso 1: promedio de los clics de cada pata en ESTA foto (un voto por foto)
            centroides_foto = {}
            pesos = np.zeros(len(lado))  # peso de cada clic en el mapa de calor
            for nombre_lado in ('izq', 'der'):
                mascara = lado == nombre_lado  # columnas (puntos) de ese lado
                if mascara.any():  # la pata puede no ser visible o no estar marcada todavía
                    centroides_foto[nombre_lado] = np.mean(xy[:, mascara], axis=1)
                    pesos[mascara] = 1 / mascara.sum()  # cada pata suma 1, sin importar cuántos clics tenga
            if ESPEJO and centroides_foto:
                # En espejo las dos patas ocupan la misma posición: se promedian sus centroides (sigue siendo un voto
                # por foto, y la pata con más clics no pesa más que la otra)
                centroides[f'{par}'].append(np.mean(list(centroides_foto.values()), axis=0))
                pesos /= len(centroides_foto)  # en espejo la foto suma 1 aunque tenga dos patas visibles
            elif not ESPEJO:
                for nombre_lado, c in centroides_foto.items():
                    centroides[f'{par}-{nombre_lado}'].append(c)
            pesos_completo = np.concatenate((pesos_completo, pesos))

        # Centroides, paso 2: promedio de los centroides de cada foto; todas las fotos pesan lo mismo
        centroide = {clave: np.mean(lista, axis=0) for clave, lista in centroides.items() if lista}
        if DEBUG:
            print({clave: len(lista) for clave, lista in centroides.items()}, centroide)  # fotos por lado y promedio

        for clave, lista in centroides.items():  # todas las listas (en modo separado, las dos)
            if lista:
                estadistica[clave] = {"centroides": np.array(lista), "radios": [], "angulos": []}  # forma (n_fotos, 2)
        xy_por_par[par], pesos_por_par[par] = xy_completo, pesos_completo

    ## Estadística
    # Paso 0: radio y ángulo de cada centroide (un valor por foto), vectorizado sobre todas las fotos a la vez
    for clave in estadistica:
        e = estadistica[clave]
        C = e["centroides"]  # columna 0: lateral (x), columna 1: hacia el frente (y)
        n = len(C)
        e["radios"] = np.hypot(C[:, 0], C[:, 1])
        e["angulos"] = np.atan2(C[:, 0], C[:, 1])
        e["media_radios"] = np.mean(e["radios"])
        e["media_angulos"] = np.mean(e["angulos"])
        e["media_angulos_c"] = np.atan2(np.sum(np.sin(e["angulos"])), np.sum(np.cos(e["angulos"])))
        e["std_radios"] = np.std(e["radios"], ddof=1)
        e["std_angulos"] = np.std(e["angulos"], ddof=1)
        e["EE_radios"] = e["std_radios"]/np.sqrt(n)
        e["EE_angulos"] = e["std_angulos"]/np.sqrt(n)
        e["t"] = scipy.stats.t.ppf(0.975, n-1)  # una vez por clave: n - 1 grados de libertad
        e["t-student_radios"] = [e["media_radios"] - e["t"]*e["EE_radios"], e["media_radios"] + e["t"]*e["EE_radios"]]
        e["t-student_angulos"] = [e["media_angulos"] - e["t"]*e["EE_angulos"], e["media_angulos"] + e["t"]*e["EE_angulos"]]
    return estadistica, xy_por_par, pesos_por_par

resultados = {modo: analizar(espejo) for modo, espejo in MODOS.items()}
if DEBUG:
    for modo, (estadistica, _, _) in resultados.items():
        print(modo, estadistica)

## Gráficas
figuras = graficas_patas.figuras(resultados, graficas_patas.posicion_frente(imagenes, nombres_imagenes), COLORES)
for modo, fig in figuras.items():
    fig.savefig(SALIDA.format(modo.lower()), dpi=200)
plt.show()
