import pandas as pd
import numpy as np
import os

os.system('cls')

imagenes = pd.read_csv(r"Exploration\Geometria_estadistica\datos\imagenes.csv")
puntos = pd.read_csv(r"Exploration\Geometria_estadistica\datos\puntos.csv")

print(imagenes.head())
print(puntos.head())

print(imagenes.keys())
print(puntos.keys())
