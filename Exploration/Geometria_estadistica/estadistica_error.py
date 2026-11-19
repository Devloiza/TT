from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

## Ajustes
DEBUG = False
BINES = 'auto'
ARCHIVO = Path(__file__).resolve().parents[2] / 'SALIDAS' / 'Escorpiones_estadistica' / 'error_proyeccion.csv'
COLOR_LINEAS = 'red'

## Datos
db = pd.read_csv(ARCHIVO)
if DEBUG: print(list(db.keys()))

D = db['D_px'].to_numpy()      # largo del eje frente-atrás
Lf = db['l_px'].to_numpy()     # de la proyección del centro al frente
La = D - Lf                    # de atrás a la proyección del centro
R = db['r_px'].to_numpy()      # radio del círculo
AN = db['ancho_px'].to_numpy()
AL = db['alto_px'].to_numpy()

def normalizadorinador(arreglo, d_0):
    '''Divide cada valor entre el largo del eje de su foto, para comparar fotos de distinta escala.'''
    return np.asarray(arreglo) / np.asarray(d_0)

def histograminador(Arr:np.ndarray, n_subplot:int = 111, TITLE:str = '',
                    XLABEL:str = '', COLOR:str = 'k', normalizado:bool = False):
    '''Histograma con la media y ± una desviación estándar marcadas y explicadas en la leyenda.'''
    plt.subplot(n_subplot)
    plt.grid(linestyle = '--', alpha = 0.3)
    h, b, _ = plt.hist(Arr, bins = BINES, edgecolor = 'k', color = COLOR)

    mean = np.mean(Arr)
    std = np.std(Arr, ddof=1)
    plt.vlines([mean], 0, np.max(h), colors = COLOR_LINEAS, linestyles = 'dashed', linewidth = 1.5,
               label = f'Media = {mean:.2f}')
    plt.vlines([mean-std, mean+std], 0, np.max(h), colors = COLOR_LINEAS, linestyles = 'dashdot', linewidth = 1.5,
               label = f'Desviación estándar = {std:.2f}')

    if normalizado:
        plt.xlim((np.min([mean-std, 0]), np.max([mean+std, 1])))
        TITLE = TITLE + "\n(normalizado por D)"
        XLABEL = XLABEL or 'Fracción del largo del cuerpo'
    else:
        izq, der = np.min([mean-std, np.min(b)]), np.max([mean+std, np.max(b)])
        margen = 0.05*(der - izq)  # margen proporcional al rango, para que ninguna línea quede pegada al borde
        plt.xlim((izq - margen, der + margen))
    plt.ylim((0, np.max(h)*1.35))  # espacio arriba para la leyenda
    plt.title(TITLE)
    plt.xlabel(XLABEL)
    plt.ylabel('Fotos')
    plt.legend(fontsize = 9, loc = 'upper center', framealpha = 0.9)

## Gráficas
plt.figure(figsize = (15, 8))
plt.suptitle(f"{len(D)} muestras", fontsize = 16)

histograminador(Arr=D, n_subplot=231, COLOR='royalblue', TITLE='Longitud del cuerpo (D)', XLABEL='Pixeles')
histograminador(Arr=normalizadorinador(Lf, D), normalizado=True, n_subplot=232, COLOR='forestgreen',
                TITLE='Del centro proyectado al frente')
histograminador(Arr=normalizadorinador(La, D), normalizado=True, n_subplot=233, COLOR='lightsteelblue',
                TITLE='De atrás al centro proyectado')
histograminador(Arr=normalizadorinador(R, D), normalizado=True, n_subplot=234, COLOR='rosybrown',
                TITLE='Radio del círculo')
histograminador(Arr=AN, n_subplot=235, COLOR='mediumslateblue', TITLE="Ancho de las imágenes", XLABEL='Pixeles')
histograminador(Arr=AL, n_subplot=236, COLOR='cadetblue', TITLE="Alto de las imágenes", XLABEL='Pixeles')

plt.tight_layout()
plt.show()