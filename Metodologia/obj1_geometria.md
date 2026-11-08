# Obj. 1 — Geometría de las patas a partir de fotos dorsales

> **Objetivo específico 1** ([`CONTEXTO.md` §2.3](../CONTEXTO.md#23-objetivos-específicos-textual-del-protocolo)): adaptar la distribución geométrica y el esquema de muestreo espacial inspirados en las *slit sensilla* del escorpión a un arreglo multimicrófono no uniforme.

**Estado:** en curso. Este registro cubre la **estadística sobre imágenes**: dónde quedan, en promedio, las patas caminadoras respecto al cuerpo. Las medidas físicas del arreglo ($d_1$–$d_4$ en `Avances/geometria.json`) y la forma final (collar) siguen pendientes ([`CONTEXTO.md` §3.4](../CONTEXTO.md#34-dónde-estamos-actualizar-conforme-avance)).

**Autoría** (detalle en [`REGISTRO_IA.md`](../REGISTRO_IA.md)):

| Parte | Quién |
|:--|:--|
| Diseño del estudio, selección de fotos y anotación | El autor |
| Transformación al marco del cuerpo y estadística (`estadistica_imagenes.py`) | El autor, con revisión y correcciones de Claude a petición |
| Herramienta de anotación (`patainador.py`) | Claude, con la especificación del autor |
| Gráficas (`graficas_patas.py`) | Claude, con la especificación del autor |

---

## 1. Propósito

Obtener, para cada par de patas caminadoras (P1 a P4), una **posición típica** respecto al cuerpo: un ángulo y una distancia radial con su incertidumbre. Es un insumo para decidir la distribución del arreglo:

- la no linealidad ([D1](../CONTEXTO.md#25-compromisos-de-diseño-fáciles-de-perder-de-vista));
- las separaciones diferenciadas.

La adaptación es funcional, no una réplica ([D5](../CONTEXTO.md#25-compromisos-de-diseño-fáciles-de-perder-de-vista)). El autor decidió usar los ángulos medios y escalar el radio según la longitud de los cables (§8.1). Los detalles de esa escala siguen abiertos (§8.2).

## 2. Material

**Fotos:**
- Vista dorsal (desde arriba) de escorpiones, recopiladas de las fuentes de [`Fuentes.md`](../Exploration/Geometria_estadistica/Fuentes.md).
- Se guardan solo en local, en `Exploration/Geometria_estadistica/fotos/<orientación>/`; no se versionan.

**Datos versionados:**
- [`datos/imagenes.csv`](../Exploration/Geometria_estadistica/datos/imagenes.csv): una fila por foto, con el eje, el círculo, el estado, el motivo de descarte y la fecha.
- [`datos/puntos.csv`](../Exploration/Geometria_estadistica/datos/puntos.csv): una fila por clic, con par, lado, coordenadas, centroide de la pata y visibilidad.

Las coordenadas están en píxeles de la imagen original:
- la rotación EXIF está corregida;
- el origen está arriba a la izquierda;
- $y$ crece hacia abajo.

**Estado de los datos al 2026-11-07:**

13 fotos anotadas, todas en `Escorpiones_V_Superior/`:

| Especie (según el nombre del archivo) | Completas | Descartadas |
|:--|:--:|:--:|
| *Smeringurus mesaensis* | 5 | 0 |
| *Heterometrus spinifer* | 4 | 0 |
| *Heterometrus longimanus* | 1 | 0 |
| *Diplocentrus* sp. | 1 | 1 |
| *Heterometrus indus* | 0 | 1 |
| **Total** | **11** | **2** |

**Clics:**
- 2169 clics en total: 2160 sobre patas visibles y 9 marcas de patas no visibles.
- Una pata visible tiene en promedio 25 clics y como mínimo 9. Todas superan el mínimo de 5 que exige la herramienta.

**Descartes:**

| Motivo | Fotos |
|:--|:--:|
| Patas sobrepuestas | 1 |
| Doble imagen | 1 |

## 3. Anotación (`patainador.py`)

Uso y teclas: encabezado de [`patainador.py`](../Exploration/Geometria_estadistica/patainador.py). Por cada foto se marca:

1. **Eje del cuerpo.**
   - Un punto al **frente**.
   - Un punto **atrás**: justo donde termina el cuerpo y empieza la cola, es decir, el final del mesosoma (definición del autor, 2026-11-07).
   - Por lo tanto, el eje mide el largo **prosoma + mesosoma**, sin la cola.
2. **Patas caminadoras por pares.**
   - Numeración: P1 es el par más cercano a la cabeza y P4 el más cercano a la cola.
   - Sobre la **zona del basitarso** de cada pata se hacen varios clics (mínimo `MIN_PUNTOS_PATA = 5`). El **centroide** de esos clics es la posición de la pata.
   - El **lado** (izquierda o derecha del animal) no se marca a mano. Se deduce del eje, con el producto cruz respecto a la dirección atrás → frente.
   - Si una pata no se ve (por ejemplo, oculta bajo la pinza), se marca como no visible con la tecla `n`. Así la foto puede quedar `completa` aunque le falte una pata.
3. **Círculo.**
   - Se calcula sobre los centroides de las patas.
   - Por defecto es un ajuste por mínimos cuadrados (`METODO_CIRCULO = "ajuste"`); la alternativa es el círculo mínimo que los encierra.
   - El centro y el radio se pueden corregir a mano; queda registrado en `circulo_manual`.
   - Las 11 fotos actuales usan el **ajuste**.

**Supuesto de vista dorsal:** con la cabeza hacia arriba en la foto, la izquierda del animal queda a la izquierda de la imagen.

**Fecha:** la `fecha` de cada foto solo cambia cuando su anotación cambia de verdad (desde 2026-11-05). Abrir una foto sin modificarla no altera el CSV.

## 4. Marco del cuerpo

Para comparar fotos de distinto tamaño, orientación y encuadre, cada clic se lleva a un marco común. La transformación es de **semejanza**: traslación, rotación y escala uniforme.

Datos de cada foto (en píxeles):

| Símbolo | Significado |
|:--|:--|
| $\mathbf{o}$ | Centro del círculo |
| $\mathbf{f}$ | Punto del frente |
| $\mathbf{t}$ | Punto de atrás |
| $\mathbf{p}$ | Un clic |

$$
s = \lVert \mathbf{f}-\mathbf{t} \rVert, \qquad
\mathbf{u} = \frac{\mathbf{f}-\mathbf{t}}{s}, \qquad
\mathbf{v} = (-u_y,\; u_x)
$$

$$
a = (\mathbf{p}-\mathbf{o})\cdot\mathbf{u}, \qquad
\ell = (\mathbf{p}-\mathbf{o})\cdot\mathbf{v}
$$

$$
\theta = \operatorname{atan2}(\ell,\, a), \qquad
\rho = \frac{\sqrt{a^2+\ell^2}}{s}
$$

**Qué significa cada cantidad:**

- **Origen:** el centro del círculo de las patas.
- **$a$:** componente hacia el frente del animal.
- **$\ell$:** componente lateral; es positiva hacia la **derecha del animal**. Se validó contra la columna `lado` de la herramienta: coinciden los 1906 clics visibles de las 11 fotos completas (2026-11-07).
- **$\theta$:** ángulo respecto al frente, en $(-180°, 180°]$. Vale 0° al frente, ±90° a los lados y 180° atrás. Es negativo del lado izquierdo.
- **$\rho$:** distancia radial en **largos de cuerpo** (prosoma + mesosoma). $\rho = 1$ equivale a la distancia entre el frente y el atrás marcados.

En las gráficas se usan $x = \rho\sin\theta$ (lateral) e $y = \rho\cos\theta$ (hacia el frente).

Implementación: función `orientainador` de [`estadistica_imagenes.py`](../Exploration/Geometria_estadistica/estadistica_imagenes.py).

## 5. Estadística

### 5.1 Unidad de análisis: la foto

Los clics de una misma pata en una misma foto **no son observaciones independientes**: son mediciones repetidas del mismo punto. Tratarlos como independientes es **pseudorreplicación** (Hurlbert, 1984). Daría un intervalo de confianza artificialmente estrecho y favorecería a las fotos con más clics.

Por eso el centroide se calcula en dos niveles:

1. **Por pata y por foto:** $\mathbf{c}_k$ es la media de los clics de esa pata en la foto $k$.
2. **Entre fotos:** media de los $\mathbf{c}_k$. Cada foto pesa lo mismo, sin importar cuántos clics tenga; equivale a dar a cada clic el peso $1/(K\,n_k)$.

La varianza del centroide medio,

$$
\operatorname{Var}(\bar{\mathbf{c}}) = \frac{\sigma_b^2 + \sigma_w^2/n_k}{K},
$$

está dominada por la variación **entre fotos** ($\sigma_b^2$). Con 5 o 30 clics por pata, el término dentro de la foto ($\sigma_w^2/n_k$) se vuelve pequeño. Agregar fotos reduce la incertidumbre más que agregar clics.

### 5.2 Dos modos

| Modo | Qué agrupa | Uso |
|:--|:--|:--|
| **Pares** | Izquierda y derecha por separado (`P1-izq`, `P1-der`, …). Un centroide por foto y por lado | **El que se usa para el TT** (decisión del autor, 2026-11-07): la diferencia de ángulos se analiza por pares |
| **Espejo** | Se toma $\lvert\ell\rvert$ y las dos patas de un par se tratan como la misma. Si las dos son visibles, se promedian sus centroides, así que cada foto sigue siendo un voto | Solo de ejemplo, para mostrar la forma simétrica idealizada |

### 5.3 Ángulo, radio e intervalo de confianza

Para cada clave (par y lado), con los $n$ centroides por foto:

1. **Valores por foto:** $r_k = \lVert\mathbf{c}_k\rVert$ y $\theta_k = \operatorname{atan2}(c_{k,x},\, c_{k,y})$.
2. **Media y dispersión:** $\bar r$ y $\bar\theta$. La desviación estándar muestral usa $n-1$ grados de libertad (`ddof=1`). El error estándar es $EE = s/\sqrt{n}$.
3. **Intervalo de confianza del 95 %** con la distribución *t* de Student, porque $n$ es pequeño y $\sigma$ desconocida:

$$
\bar x \pm t_{0.975,\,n-1}\,\frac{s}{\sqrt{n}}
$$

`scipy.stats.t.ppf(0.975, n-1)`. El intervalo es simétrico, así que se reporta como media ± mitad del IC.

**Media circular.** Los ángulos son una variable circular. Como control se calculó la media circular, $\operatorname{atan2}(\sum\sin\theta_k,\, \sum\cos\theta_k)$. Difiere de la media lineal en menos de 0.1° en todas las claves, porque ningún par cruza el corte de ±180°. Por eso el IC lineal es válido con estos datos. Si en algún momento P4 se acercara a 180°, habría que pasar a estadística circular (Mardia y Jupp, 2000).

**El IC no describe a un individuo.** El IC es para la **posición media**, no para dónde cae la pata de un escorpión en particular. Para eso se usaría el intervalo de predicción, $\bar x \pm t\,s\sqrt{1+1/n}$, que no se ha calculado.

## 6. Visualización (`graficas_patas.py`)

Se genera **una figura por modo**, con una fila y dos columnas. Se guardan en `SALIDAS/geometria_patas_pares.png` y `SALIDAS/geometria_patas_espejo.png`, y no se versionan. Las dos figuras comparten escala.

**Columna izquierda: mapa de calor y sectores del IC**

- El mapa de calor es una **estimación de densidad por núcleos** (KDE gaussiana), ponderada con los mismos pesos de §5.1.
  - Ancho de banda: regla de Scott (Scott, 1992).
  - Se normaliza al máximo de cada par, así que la opacidad indica concentración relativa dentro de ese par, no una comparación entre pares.
  - Por debajo del 8 % del máximo el mapa es transparente.
  - En espejo se refleja una copia de los datos en $x<0$ para que la estimación no se corte en el borde.
- **Sector de anillo:** ángulo dentro de su IC y radio dentro de su IC. El rombo marca la media.

**Columna derecha: esquema del escorpión**

- Es **ilustrativo**. Solo la punta de cada pata es dato (posición media).
- El cuerpo, la cola, los pedipalpos, el punto donde nace cada pata y la "rodilla" son supuestos de dibujo.
- La cola se dibuja detrás del punto "atrás", coherente con su definición (§3).
- Junto a cada punta aparecen $\theta$ y $\rho$ ± mitad del IC. Se activa con `MOSTRAR_VALORES`.

## 7. Resultados preliminares

**Corrida del 2026-11-07:** 11 fotos completas, con los datos de §2.

Son **preliminares**: la muestra es pequeña y mezcla géneros a propósito (§8.1). Se regeneran corriendo el script; si los datos cambian, esta tabla queda desactualizada.

**Modo pares:** media ± mitad del IC 95 %.

| Clave | $n$ (fotos) | $\theta$ (°) | $\rho$ (largos de cuerpo) | $s_\theta$ (°) | $s_\rho$ |
|:--|:--:|:--:|:--:|:--:|:--:|
| P1-izq | 7 | −17.8 ± 4.4 | 0.718 ± 0.108 | 4.7 | 0.117 |
| P1-der | 10 | 25.8 ± 7.3 | 0.660 ± 0.066 | 10.2 | 0.093 |
| P2-izq | 10 | −57.1 ± 9.3 | 0.631 ± 0.124 | 13.0 | 0.174 |
| P2-der | 9 | 59.6 ± 9.7 | 0.629 ± 0.151 | 12.7 | 0.196 |
| P3-izq | 11 | −96.6 ± 11.2 | 0.543 ± 0.112 | 16.7 | 0.166 |
| P3-der | 11 | 99.3 ± 10.2 | 0.579 ± 0.095 | 15.2 | 0.142 |
| P4-izq | 11 | −143.2 ± 6.8 | 0.711 ± 0.080 | 10.2 | 0.118 |
| P4-der | 10 | 138.7 ± 7.1 | 0.693 ± 0.103 | 9.9 | 0.144 |

**Modo espejo:** solo de referencia.

| Par | $n$ | $\theta$ (°) | $\rho$ |
|:--|:--:|:--:|:--:|
| P1 | 11 | 22.5 ± 5.4 | 0.689 ± 0.061 |
| P2 | 11 | 58.9 ± 5.9 | 0.615 ± 0.115 |
| P3 | 11 | 97.7 ± 9.7 | 0.557 ± 0.098 |
| P4 | 11 | 141.7 ± 5.3 | 0.693 ± 0.074 |

**Observaciones para revisar.** No son conclusiones:

- **P1 tiene $n$ distinto por lado:** 7 fotos a la izquierda y 10 a la derecha. Su ángulo medio difiere unos 8° entre lados, aunque los IC de $\lvert\theta\rvert$ se traslapan.
- **Mapas bimodales en P2 y P3:** el mapa de calor muestra dos zonas de concentración por lado. La media cae entre ellas, así que puede no representar a ningún grupo real. Una explicación posible es la mezcla de especies.
- **Radios sin un patrón claro:** todos los $\rho$ caen entre 0.54 y 0.72. P3 es el par más cercano al centro.

## 8. Decisiones, pendientes y limitaciones

### 8.1 Decisiones del autor (2026-11-07)

**Especies de varios géneros.**

- Se incluyen especies fuera de *Heterometrus*: *Smeringurus* y *Diplocentrus*, que son 6 de las 11 fotos completas.
- **Motivo:** una fuente reporta *slit sensilla* en más especies. Como es el órgano de interés, se busca saber si la geometría de las patas es propia de los escorpiones en general o de cada especie.
- **Contraste preliminar:** las 11 fotos válidas convergen a valores muy similares a los de una de las fuentes del proyecto.
- La recopilación de más fotos sigue en curso.

**De la estadística al arreglo.**

- **Ángulos:** se usan los ángulos medios que da la estadística, en modo pares (§7).
- **Radio:** se lleva a escala según la longitud que permitan los cables del arreglo.
- Como $\rho$ ya es una proporción (largos de cuerpo), basta un factor de escala. La radial de la pata $i$ en el arreglo sería

$$
r_i = R\,\frac{\rho_i}{\rho_{\text{ref}}}
$$

- $R$ es el radio máximo que permiten los cables.
- $\rho_{\text{ref}}$ es la referencia que cae justo en $R$. Si $\rho_{\text{ref}} = \max_i \rho_i$, cada par queda en el porcentaje $\rho_i/\rho_{\max}$ de $R$ y el más lejano usa todo el cable.
- Escalar así conserva las proporciones entre pares, es decir, la forma.

### 8.2 Pendientes de esa decisión

- **Citar las fuentes del criterio de especies** en `Fuentes.md`: la que reporta *slit sensilla* en otras especies y la del contraste. Ese archivo todavía dice que se usarán especies de *Heterometrus*.
- **Elegir $R$ y $\rho_{\text{ref}}$**, y decidir si se conservan las diferencias de radio entre pares o se usa un radio común.
  - Hoy los $\rho$ van de 0.54 a 0.72 y varios IC se traslapan. Con 11 fotos no está claro que los pares difieran en radio; en ángulo sí.
- **Considerar el aliasing espacial al fijar $R$.** Con $f_s = 16$ kHz, la frecuencia más alta es 8 kHz. La media longitud de onda es $\lambda/2 = c/(2f) \approx 2.1$ cm con $c = 343$ m/s.
  - Separaciones entre micrófonos vecinos mayores que eso producen lóbulos fantasma a esas frecuencias.
  - Una apertura mayor mejora la resolución angular a frecuencias bajas.
  - Por eso $R$ no solo depende del cable.
- **D2 (pesos diferenciados):** no sale de esta estadística y queda por definir.
- **Tamaño de muestra:** el IC se estrecha como $1/\sqrt{n}$. Si se analiza por especie, cada especie necesita sus propias fotos.

### 8.3 Limitaciones del método

- **Proyección 2D.** La foto es una proyección; una inclinación de la cámara respecto al dorso deforma ángulos y radios. No se corrige.
- **Postura.** Las fotos son de animales en posturas distintas (caminando, en reposo). La media mezcla posturas.
- **Marcado.** El "frente" y el "atrás" se marcan a ojo. Su error se propaga a la escala $s$ y a la orientación $\mathbf{u}$ de toda la foto.

### 8.4 Pendientes técnicos

- La portabilidad de `estadistica_imagenes.py` (rutas de Windows y `cls`) queda como trabajo a futuro: [`Documentation.md` §14.2](../Avances/Documentation.md#142-portabilidad-de-estadistica_imagenespy-nov-2026).

## 9. Reproducir

Desde la raíz del repositorio:

```bash
python Exploration/Geometria_estadistica/patainador.py              # anotar o corregir fotos
python Exploration/Geometria_estadistica/estadistica_imagenes.py    # estadística y figuras → SALIDAS/
```

**Ajustes:**

- En `estadistica_imagenes.py`:
  - `DEBUG`: imprime los datos y los diccionarios de estadística;
  - `MODOS`: qué modos se calculan.
- En `graficas_patas.py`, al inicio del archivo:
  - tamaños de texto y línea;
  - resolución y umbral del mapa;
  - `MOSTRAR_VALORES`;
  - `COLA_DETRAS_DEL_EJE`.

**Dependencias:** `numpy`, `pandas`, `scipy` y `matplotlib` (`requirements.txt`).

## 10. Referencias

- Hurlbert, S. H. (1984). Pseudoreplication and the design of ecological field experiments. *Ecological Monographs*, 54(2), 187–211.
- Mardia, K. V. y Jupp, P. E. (2000). *Directional Statistics*. Wiley.
- Scott, D. W. (1992). *Multivariate Density Estimation: Theory, Practice, and Visualization*. Wiley.

## Bitácora

| Fecha | Cambio |
|:--|:--|
| 2026-11-03 | Herramienta de anotación y primeras anotaciones (`f4aca2d`) |
| 2026-11-05 | `patainador.py`: tamaños configurables y fecha solo con cambios reales (`a5381f1`) |
| 2026-11-07 | Criterio de especies (varios géneros con *slit sensilla*) y paso al arreglo (ángulos medios, radio a escala del cableado) |
| 2026-11-07 | Transformación al marco del cuerpo, centroides en dos niveles, IC con *t* de Student, modos pares y espejo, figuras por modo. "Atrás" definido como el final del mesosoma. Fotos en progreso completadas marcando las patas ocultas con `n` |
