# `beamforming_algorithms` — Documentación técnica del playground de beamforming

> Banco de pruebas en simulación para el **delay-and-sum (DAS)** y la **estimación de la dirección de llegada (DOA)** del TT `DTA.MI.2026-2.5BM1.LMP.01`.
> Ubicación: `Exploration/` — es **exploración**, no código de producción. Los algoritmos que pasen los criterios de la [§11](#11-criterios-para-promover-un-algoritmo-a-avances) se promueven a `Avances/`.
> Fuente de alcance: `CONTEXTO.md`. Este documento describe *cómo* funciona el playground y *por qué* está hecho así; no define alcance.

---

## Índice

0. [Resumen rápido](#0-resumen-rápido)
1. [Propósito y lugar en el TT](#1-propósito-y-lugar-en-el-tt)
2. [Convenciones](#2-convenciones)
3. [Fundamentos teóricos](#3-fundamentos-teóricos)
   - 3.1 [Propagación: onda esférica](#31-propagación-onda-esférica)
   - 3.2 [Aproximación de campo lejano](#32-aproximación-de-campo-lejano-onda-plana)
   - 3.3 [Modelo de señal en el arreglo](#33-modelo-de-señal-en-el-arreglo)
   - 3.4 [Delay-and-sum](#34-delay-and-sum-das)
   - 3.5 [Retardos fraccionarios](#35-retardos-fraccionarios)
   - 3.6 [Patrón de haz, resolución y aliasing espacial](#36-patrón-de-haz-resolución-y-aliasing-espacial)
   - 3.7 [Ambigüedades geométricas](#37-ambigüedades-geométricas)
   - 3.8 [Ganancia frente a ruido blanco y pesos](#38-ganancia-frente-a-ruido-blanco-y-el-papel-de-los-pesos)
   - 3.9 [SRP y SRP-PHAT](#39-srp-y-srp-phat-estimación-de-doa)
   - 3.10 [GCC-PHAT](#310-gcc-phat-medición-de-retardos-entre-pares)
   - 3.11 [Señales de prueba](#311-señales-de-prueba)
   - 3.12 [Ruido de sensor](#312-ruido-de-sensor)
4. [Criterios de diseño del código](#4-criterios-de-diseño-del-código)
5. [Referencia de la API](#5-referencia-de-la-api)
   - 5.1 [`geometrias.py`](#51-geometriaspy)
   - 5.2 [`campo.py`](#52-campopy)
   - 5.3 [`das.py`](#53-daspy)
6. [`prueba_das.py` — escenario visual](#6-prueba_daspy--escenario-visual)
7. [`verificar.py` — batería de verificación](#7-verificarpy--batería-de-verificación)
8. [Recetas de uso](#8-recetas-de-uso)
9. [Rendimiento](#9-rendimiento)
10. [Supuestos y limitaciones](#10-supuestos-y-limitaciones)
11. [Criterios para promover un algoritmo a `Avances/`](#11-criterios-para-promover-un-algoritmo-a-avances)
12. [Hoja de ruta](#12-hoja-de-ruta)
13. [Glosario](#13-glosario)
14. [Referencias](#14-referencias)

---

## 0. Resumen rápido

```bash
# desde la raíz del repo (o desde esta carpeta, da igual)
python Exploration/beamforming_algorithms/verificar.py      # ¿el DAS está bien? (≈30 s)
python Exploration/beamforming_algorithms/prueba_das.py     # figura del escenario por defecto
python Exploration/beamforming_algorithms/prueba_das.py GEOMETRIA=ula_2cm SENAL=multitono AZIMUT=60
```

Requisitos: `numpy`, `scipy`, `matplotlib` (ya están en `requirements.txt`). No usa PyAudio ni pyserial: no requiere hardware.

| Archivo | Rol |
|:--|:--|
| `geometrias.py` | Define dónde están los 8 micrófonos (geometrías candidatas, carga de `.json`). |
| `campo.py` | Genera lo que "escucharían" los micrófonos: fuente puntual, propagación ideal, señales de prueba analíticas. |
| `das.py` | Los algoritmos: retardos de apuntamiento, DAS, SRP (DOA), GCC-PHAT (retardos). |
| `verificar.py` | Pruebas con resultado conocido de antemano. Es el "test suite" del DAS. |
| `prueba_das.py` | Escenario configurable con figura de 6 paneles → `SALIDAS/`. |

**Estado (2026-10-07):** las 4 geometrías definidas pasan las 6 verificaciones (tabla en la [§7.4](#74-resultados-actuales)).

---

## 1. Propósito y lugar en el TT

### 1.1 Por qué simular antes de tocar el hardware

Con hardware real, una salida mala del DAS puede deberse a un bug en el algoritmo, a una geometría mal medida, a la desincronización entre placas, a mics con distinta sensibilidad, a la reverberación o al ruido. Son demasiadas causas posibles y no hay forma de separarlas. En simulación todas esas variables están **bajo control** y la respuesta correcta se **conoce de antemano**. Si el algoritmo no reproduce la respuesta conocida en el caso ideal, está mal programado. Si sí la reproduce, cualquier degradación posterior con hardware real se le puede atribuir al mundo físico, no al código.

### 1.2 Relación con los compromisos del protocolo

| Elemento de `CONTEXTO.md` | Cómo lo atiende este playground |
|:--|:--|
| **Obj. 1** — geometría no uniforme | La geometría es un **parámetro**: se pueden comparar candidatas *antes* de fijarlas físicamente. Desacopla el desarrollo del DAS de la medición real de $d_1$–$d_4$ (§3.2 de `CONTEXTO.md`): cuando exista la geometría medida, solo se cambia el `.json`. |
| **Obj. 5** — DOA + beamforming | `das.py` implementa DAS, DOA por SRP y medición de TDOA por GCC-PHAT. |
| **Obj. 7 / C5 / D3** — baseline lineal uniforme, mismo número de mics | `ula_2cm` es el baseline; el **mismo** código procesa todas las geometrías (paridad de procesamiento). |
| **D1** — geometría **no lineal** | La simulación muestra la ambigüedad frente/espalda de un arreglo colineal (§3.7). Es un argumento cuantitativo a favor de D1. |
| **D2** — pesos diferenciados | `das()` y `srp()` aceptan `pesos`. La §3.8 explica qué pueden y qué **no** pueden hacer los pesos. |
| **C3** — +3 dB de SNR vs. ULA | La métrica de ganancia de SNR ya está implementada para ruido de sensor (§3.8). El ruido direccional está en la hoja de ruta. |
| **P1 / P2** (extensiones, §4.1) | P1 = localización en régimen limpio con tono de 1 kHz → `SENAL=seno`. P2 = mismas condiciones y mismo procesamiento en dos geometrías → este playground. |

### 1.3 Qué NO es

- No es una simulación de sala: no hay reverberación ni reflexiones (ver [§10](#10-supuestos-y-limitaciones)).
- No es el pipeline en tiempo real: procesa señales completas, no frames de 512 muestras con continuidad entre frames.
- No sustituye la evaluación con PESQ/STOI (Obj. 8), que requerirá habla real y ruido.

---

## 2. Convenciones

| Concepto | Convención |
|:--|:--|
| Unidades | SI: metros, segundos, hertz. Los retardos internos están en **segundos** (no en muestras). |
| Sistema de coordenadas | Cartesiano derecho $(x, y, z)$. El arreglo está en el plano $z = 0$. |
| Origen angular | Centroide del arreglo $\bar{\mathbf p} = \frac{1}{M}\sum_m \mathbf p_m$. |
| Azimut $\theta$ | Medido desde $+x$, **antihorario**, en grados, $[0°, 360°)$. $90°$ apunta a $+y$. |
| Elevación $\varphi$ | Medida desde el plano $XY$ hacia $+z$, en grados. Por ahora siempre $0°$. |
| Índices de micrófono | En código `m = 0..7`; en texto y figuras `M1..M8` (= `id` 1..8 de `geometria.json`). |
| Frecuencia de muestreo | $f_s = 16\,000$ Hz (`campo.FS`), igual que `ESP_RATE` del firmware. |
| Velocidad del sonido | $c = 343$ m/s (`campo.C_SONIDO`), igual que `velocidad_sonido` de `geometria.json`. |
| Formato de señales | Arreglo `(N, M)` `float32` en $[-1, 1]$: filas = muestras, columnas = micrófonos. Es **idéntico** al frame `(CHUNK, 8)` que produce `hilo_sincronizador` en `monitor_8LR.py`. |
| Tiempo de llegada $\tau_m$ | Instante en que el frente de onda llega al mic $m$. Un $\tau$ mayor significa que la señal llega **después**. |

---

## 3. Fundamentos teóricos

### 3.1 Propagación: onda esférica

Una fuente puntual en $\mathbf s$ que emite $s(t)$ en un medio homogéneo, sin pérdidas y sin fronteras, produce en el punto $\mathbf p$ la presión acústica

$$
p(\mathbf p, t) = \frac{1}{4\pi r}\, s\!\left(t - \frac{r}{c}\right), \qquad r = \lVert \mathbf s - \mathbf p \rVert ,
$$

que es la solución de onda saliente de la ecuación de onda $\nabla^2 p - \frac{1}{c^2}\frac{\partial^2 p}{\partial t^2} = 0$. Tiene dos efectos:

1. **Retardo de propagación** $\tau = r/c$. Es la base de todo beamforming temporal.
2. **Atenuación esférica** $\propto 1/r$. Los mics más cercanos a la fuente reciben más amplitud.

En `campo.simular(..., modelo="esferico")` cada micrófono $m$ recibe

$$
x_m(t) = a_m\, s(t - \tau_m), \qquad \tau_m = \frac{\lVert \mathbf s - \mathbf p_m \rVert}{c}, \qquad a_m = \frac{R}{\lVert \mathbf s - \mathbf p_m\rVert},
$$

con $R = \lVert \mathbf s - \bar{\mathbf p}\rVert$ la distancia de la fuente al centroide. La normalización $a_m = R / r_m$ (en lugar de $1/(4\pi r_m)$) hace que $s(t)$ sea directamente "la señal que se mediría en el centroide del arreglo". El factor $4\pi$ y la escala absoluta no importan para el DAS. Con `atenuacion=False`, $a_m = 1$.

### 3.2 Aproximación de campo lejano (onda plana)

Sea $\mathbf u$ el vector unitario del centroide hacia la fuente, $\mathbf s = \bar{\mathbf p} + R\,\mathbf u$, y $\mathbf q_m = \mathbf p_m - \bar{\mathbf p}$ la posición del mic relativa al centroide. Al expandir la distancia:

$$
\lVert \mathbf s - \mathbf p_m \rVert = \sqrt{R^2 - 2R\,\mathbf u\cdot\mathbf q_m + \lVert\mathbf q_m\rVert^2}
\;\approx\; R \;-\; \mathbf u\cdot\mathbf q_m \;+\; \underbrace{\frac{\lVert\mathbf q_m\rVert^2 - (\mathbf u\cdot\mathbf q_m)^2}{2R}}_{\text{término de curvatura}} .
$$

Si $R \gg \lVert\mathbf q_m\rVert$, el término de curvatura se desprecia y el frente de onda es **plano**:

$$
\tau_m^{\text{plano}} = \frac{R - \mathbf u\cdot\mathbf q_m}{c}.
$$

En `modelo="plano"` también $a_m = 1$, porque se desprecia la diferencia de amplitudes. El vector de dirección en función de azimut y elevación es

$$
\mathbf u(\theta,\varphi) = \big(\cos\theta\cos\varphi,\; \sin\theta\cos\varphi,\; \sin\varphi\big).
$$

**¿Cuándo vale la aproximación?** El criterio clásico de Fraunhofer exige que el error de fase por curvatura en los extremos del arreglo sea menor que $\pi/8$:

$$
R \;>\; R_F = \frac{2D^2}{\lambda}, \qquad \lambda = \frac{c}{f},
$$

donde $D$ es la **apertura** (distancia máxima entre dos micrófonos). Como $R_F$ crece con la frecuencia, una fuente puede estar en campo lejano para los graves y en campo cercano para los agudos:

| Geometría | $D$ | $R_F$ a 1 kHz | $R_F$ a 4 kHz | $R_F$ a 7 kHz |
|:--|:--:|:--:|:--:|:--:|
| `placeholder_json` | 13.5 cm | 0.11 m | 0.42 m | 0.74 m |
| `ula_2cm` | 14.0 cm | 0.11 m | 0.46 m | 0.80 m |
| `circular_beck` | 9.0 cm | 0.05 m | 0.19 m | 0.33 m |
| `pares_radiales` | 8.8 cm | 0.05 m | 0.18 m | 0.31 m |

**Orden de magnitud del error de modelo.** Para $\lVert\mathbf q_m\rVert = 5$ cm y $R = 1$ m, el término de curvatura vale como máximo $0.0025/(2\cdot 343) \approx 3.6\ \mu$s ≈ 0.06 muestras. Parece poco, pero si el arreglo es asimétrico respecto a su centroide, ese error no se cancela y el modelo plano lo interpreta como un pequeño giro del ángulo. Eso explica el sesgo de ~1° que se observó en `pares_radiales` con la fuente a 1 m (y de ~0.5° a 2 m: escala como $1/R$).

### 3.3 Modelo de señal en el arreglo

Con ruido aditivo $n_m(t)$ en cada sensor:

$$
x_m(t) = a_m\, s(t - \tau_m) + n_m(t), \qquad m = 1,\dots,M .
$$

Por el **teorema de desplazamiento** de Fourier, $\mathcal F\{s(t-\tau)\} = S(f)\,e^{-j2\pi f\tau}$, así que en frecuencia queda

$$
X_m(f) = a_m\, S(f)\, e^{-j2\pi f \tau_m} + N_m(f).
$$

En forma vectorial, $\mathbf x(f) = S(f)\,\mathbf d(f) + \mathbf n(f)$, con el **vector de apuntamiento** (*steering vector*)

$$
\mathbf d(f) = \big[a_1 e^{-j2\pi f\tau_1},\; \dots,\; a_M e^{-j2\pi f\tau_M}\big]^T .
$$

Toda la información espacial está en las **fases** $2\pi f\tau_m$ y, en campo cercano, también en las amplitudes $a_m$. Esto conecta con el Obj. 1 del protocolo: "diferencias de amplitud y tiempo de llegada".

Los **retardos de apuntamiento** $\hat\tau_m$ son los que *supone* el algoritmo para una dirección o punto candidato. En `das.py`:

$$
\hat\tau_m^{\text{lejano}}(\theta,\varphi) = -\frac{\mathbf u(\theta,\varphi)\cdot\mathbf q_m}{c}
\qquad\qquad
\hat\tau_m^{\text{cercano}}(\mathbf s) = \frac{\lVert \mathbf s - \mathbf p_m\rVert}{c}.
$$

El de campo lejano omite el término común $R/c$ porque no se conoce la distancia y una constante común no afecta al DAS. El signo menos indica que un mic desplazado *hacia* la fuente ($\mathbf u\cdot\mathbf q_m > 0$) recibe la señal **antes**.

### 3.4 Delay-and-sum (DAS)

**Idea.** Retrasar cada canal lo justo para que la señal de la dirección de interés quede alineada en todos, y luego promediar. Lo que viene de esa dirección se suma **en fase** (coherentemente). El ruido independiente y lo que viene de otras direcciones se suma con fases desalineadas y se atenúa.

**Definición (versión causal, la implementada).** Dados los retardos de apuntamiento $\hat\tau_m$:

$$
\Delta_m = \max_k \hat\tau_k \;-\; \hat\tau_m \;\;\ge 0,
\qquad
y(t) = \sum_{m=1}^{M} w_m\, x_m(t - \Delta_m), \qquad \sum_m w_m = 1 .
$$

Cada canal se **retrasa** $\Delta_m \ge 0$ para alcanzar al último micrófono en recibir la señal. Nunca se adelanta un canal, porque en tiempo real no se dispone de muestras futuras.

**Por qué funciona (sin distorsión).** Si el apuntamiento es correcto, $\hat\tau_m = \tau_m - \tau_0$ para una constante $\tau_0$ común. Entonces $\tau_m + \Delta_m = \tau_0 + \max_k\hat\tau_k \equiv T$ es igual para todos los $m$ y

$$
y(t) = \sum_m w_m\, a_m\, s(t - \tau_m - \Delta_m) = \Big(\sum_m w_m a_m\Big)\, s(t - T).
$$

En onda plana ($a_m = 1$) y con $\sum w_m = 1$, la salida es **exactamente** la señal original retrasada: $y(t) = s(t-T)$. Esta es la propiedad *distortionless* (ganancia unitaria en la dirección de mirada), y es lo que comprueban las pruebas 2 y 3 de `verificar.py`.

**En frecuencia (como está implementado).**

$$
Y(f) = \sum_m w_m\, X_m(f)\, e^{-j2\pi f \Delta_m} .
$$

### 3.5 Retardos fraccionarios

**El problema.** El periodo de muestreo es $T_s = 1/f_s = 62.5\ \mu$s, en el que el sonido recorre $c\,T_s \approx 2.14$ cm. En un arreglo de ~14 cm de apertura, el retardo máximo entre mics es $D/c \approx 392\ \mu$s ≈ **6.3 muestras**, y para casi cualquier dirección los $\Delta_m$ **no son enteros**.

**Por qué no redondear.** Si $\Delta_m$ se redondea a la muestra más cercana, el error $\varepsilon_m$ queda en $[-T_s/2, T_s/2]$. Si se modela como uniforme e independiente por canal, la ganancia coherente esperada a la frecuencia $f$ es

$$
\big|\mathbb E\big[e^{-j2\pi f\varepsilon}\big]\big| = \operatorname{sinc}\!\left(\frac{f}{f_s}\right) = \frac{\sin(\pi f/f_s)}{\pi f/f_s} .
$$

| $f$ | Pérdida de ganancia coherente por redondeo |
|:--:|:--:|
| 1 kHz | −0.06 dB |
| 2 kHz | −0.22 dB |
| 4 kHz | −0.91 dB |
| 7 kHz | −2.93 dB |

Además de la pérdida, el error residual se convierte en distorsión. En la parte alta del espectro de voz (consonantes, clave para la inteligibilidad), redondear cuesta decibeles comparables a los 3 dB que exige C3. Por eso **no se redondea**.

**Implementación (`das.alinear`).** Se aplica el teorema de desplazamiento con la DFT:

$$
x_m[n - \Delta_m f_s] \;\;\longleftrightarrow\;\; X_m[k]\, e^{-j2\pi f_k \Delta_m}, \qquad f_k = \frac{k f_s}{N_{\text{FFT}}} .
$$

1. `rfft` de cada canal con $N_{\text{FFT}} = 2^{\lceil \log_2(N + \lceil \max_m\Delta_m f_s\rceil + 1)\rceil}$. El *zero-padding* deja espacio para que lo que se retrasa no "dé la vuelta" al inicio del buffer.
2. Multiplicación por la fase $e^{-j2\pi f_k\Delta_m}$, vectorizada para todos los canales a la vez.
3. `irfft` y recorte a las primeras $N$ muestras.

Para señales de banda limitada, esto equivale a interpolar con una sinc ideal, el retardo fraccionario exacto.

**Precios a pagar:**

- **La DFT es circular.** La interpolación sinc ideal es infinita y no causal: requiere muestras pasadas y futuras que no existen en una señal recortada. Los bordes del bloque quedan con **transitorios** (efecto tipo Gibbs). Por eso las métricas descartan 10 ms (160 muestras) en cada extremo (`RECORTE`).
- **El bin de Nyquist** ($f_s/2$) de una señal real debe ser real. Al multiplicarlo por una fase compleja, `irfft` descarta la parte imaginaria. El error es despreciable porque las señales de prueba no tienen energía en 8 kHz.
- **En tiempo real** (frames de 512 muestras) este esquema por bloque no sirve tal cual. Ver la [§12](#12-hoja-de-ruta): FIR de retardo fraccionario (sinc enventanada, Lagrange o Farrow; Laakso et al., 1996) con overlap-save y una latencia de media longitud del filtro.

### 3.6 Patrón de haz, resolución y aliasing espacial

**Patrón de haz.** Si el DAS se apunta a $\theta_0$ y llega una onda plana desde $\theta$, la respuesta a la frecuencia $f$ es

$$
B(f;\theta,\theta_0) = \sum_m w_m\, e^{\,j2\pi f\,[\hat\tau_m(\theta_0) - \hat\tau_m(\theta)]} ,
$$

con $B = 1$ en $\theta = \theta_0$ (pesos normalizados). $\lvert B\rvert^2$ en dB es el patrón de directividad.

**Resolución.** El ancho del lóbulo principal escala como $\lambda/D$ radianes. Es una aproximación de orden de magnitud: exacta para un ULA mirando de frente y útil como guía para cualquier geometría.

| $f$ | $\lambda$ | $\lambda/D$ con $D=13.5$ cm (`placeholder_json`) | $\lambda/D$ con $D=9$ cm (`circular_beck`) |
|:--:|:--:|:--:|:--:|
| 1 kHz | 34.3 cm | ≈146° | ≈218° (sin directividad útil) |
| 2 kHz | 17.2 cm | ≈73° | ≈109° |
| 4 kHz | 8.6 cm | ≈37° | ≈55° |
| 7 kHz | 4.9 cm | ≈21° | ≈31° |

Hay dos consecuencias importantes:

1. **Un tono de 1 kHz con un arreglo de ~14 cm casi no tiene directividad.** El patrón SRP de la figura por defecto ocupa media circunferencia. Aun así el **pico** cae en el ángulo correcto, porque sin ruido la *exactitud* del máximo puede ser mucho mejor que la *resolución* del lóbulo. Pero en cuanto haya ruido o una segunda fuente, el lóbulo ancho dominará.
2. **Implicación para C3.** La energía de la voz se concentra aproximadamente entre 300 Hz y 3.4 kHz. Con aperturas de ~10–15 cm, el DAS tendrá poca selectividad espacial justo ahí. Es un criterio de diseño para la geometría: a mayor apertura, más resolución en graves, pero más riesgo de aliasing en agudos.

**Aliasing espacial.** Para un ULA con separación $d$, aparecen **lóbulos de rejilla** (réplicas del lóbulo principal) si $d > \lambda/2$, es decir, por encima de

$$
f_{\text{alias}} = \frac{c}{2d}.
$$

- `ula_2cm`: $f_{\text{alias}} = 8.6$ kHz > $f_s/2 = 8$ kHz → **libre de aliasing** en toda la banda.
- `placeholder_json`: separación de 10 cm en $x$ → 1.7 kHz; de 3 cm en $y$ → 5.7 kHz.
- En geometrías **2D no uniformes** el aliasing no produce réplicas exactas, sino lóbulos laterales altos y dispersos. Es una de las ventajas teóricas de la no uniformidad: las distintas separaciones no "aliasan" en las mismas direcciones. Conviene verificarlo con el patrón SRP para cada geometría candidata.

### 3.7 Ambigüedades geométricas

**Arreglo colineal → ambigüedad frente/espalda.** Si todos los mics están sobre un eje con dirección $\mathbf e = (\cos\alpha, \sin\alpha, 0)$, entonces $\mathbf q_m = \ell_m\mathbf e$ y

$$
\hat\tau_m(\theta) = -\frac{\ell_m \cos(\theta - \alpha)}{c}.
$$

Como $\cos(\theta-\alpha) = \cos\big((2\alpha - \theta) - \alpha\big)$, las direcciones $\theta$ y su **espejo** $2\alpha - \theta$ producen **exactamente los mismos retardos**. Ningún algoritmo puede distinguirlas con esos datos. Para `ula_2cm` ($\alpha = 0°$), 60° y 300° son indistinguibles, y así se ve en el patrón polar. `geometrias.eje_si_colineal()` detecta este caso y `verificar.py` lo reporta en lugar de contarlo como falla.

> **Relevancia para D1:** una geometría no lineal no tiene esta ambigüedad. Es un argumento cuantitativo (no solo biomimético) para la exigencia "no lineal" del protocolo, y una desventaja estructural del baseline del Obj. 7.

**Arreglo plano → ambigüedad arriba/abajo.** Con todos los mics en $z=0$, $\mathbf u(\theta,\varphi)\cdot\mathbf q_m = \cos\varphi\,(q_{m,x}\cos\theta + q_{m,y}\sin\theta)$, que es par en $\varphi$. Una fuente a $+\varphi$ y otra a $-\varphi$ son indistinguibles. Además, la elevación **comprime** todos los retardos por $\cos\varphi$. Si la fuente no está en el plano del arreglo (`ALTURA ≠ 0`), el SRP en azimut sigue apuntando al azimut correcto, pero con un lóbulo más ancho.

### 3.8 Ganancia frente a ruido blanco y el papel de los pesos

Supóngase onda plana ($a_m = 1$), apuntamiento correcto y ruido $n_m$ blanco, de varianza $\sigma_n^2$ e **independiente** entre micrófonos. Tras alinear, la señal útil suma $\big(\sum_m w_m\big)s$ y el ruido tiene varianza $\sigma_n^2\sum_m w_m^2$. Un retardo es un filtro pasa-todo: no cambia la varianza ni la independencia. La **ganancia de SNR** (*white noise gain*, WNG) es

$$
G = \frac{\mathrm{SNR}_{\text{out}}}{\mathrm{SNR}_{\text{in}}} = \frac{\left(\sum_m w_m\right)^2}{\sum_m w_m^2}.
$$

Por la desigualdad de Cauchy–Schwarz, $\left(\sum_m w_m\right)^2 \le M\sum_m w_m^2$, con igualdad **si y solo si los pesos son uniformes**:

$$
G_{\max} = M \;\Rightarrow\; 10\log_{10} 8 = 9.03 \text{ dB}.
$$

Ejemplo: con `PESOS=[1,1,1,1,2,2,2,2]`, $G = 12^2/20 = 7.2$ → **8.57 dB**, medio decibel menos que el DAS uniforme. Coincide con lo que se midió en simulación: error de salida de −8.5 dB con `SNR_SENSOR=0`.

**Si las amplitudes difieren** ($a_m$ distintos: campo cercano, sombra acústica, mics de distinta sensibilidad), la SNR de salida es

$$
\mathrm{SNR}_{\text{out}} = \frac{\sigma_s^2}{\sigma_n^2}\,\frac{\left(\sum_m w_m a_m\right)^2}{\sum_m w_m^2},
$$

que se maximiza con $w_m \propto a_m$ (*maximal ratio combining*), dando $\frac{\sigma_s^2}{\sigma_n^2}\sum_m a_m^2$.

> **Criterio de diseño para D2 (pesos diferenciados).** Contra ruido blanco independiente y amplitudes iguales, **ningún** esquema de pesos supera al DAS uniforme: la ganancia de los pesos diferenciados tiene que venir de otro lado. Hay tres mecanismos legítimos:
> 1. **Diferencias de amplitud** entre mics → pesos $\propto a_m$ (MRC).
> 2. **Ruido direccional** (una fuente interferente en otra dirección) → los pesos moldean el patrón para bajar los lóbulos laterales o poner un nulo hacia el interferente, a costa de algo de WNG.
> 3. **Pesos dependientes de la frecuencia** → mantener el ancho de haz constante en banda.
>
> La justificación de D2 en la tesina debe apoyarse en alguno de estos mecanismos, y la mejora debe medirse **con ruido direccional** (todavía no simulado; ver la [§12](#12-hoja-de-ruta)). Con ruido blanco, los pesos diferenciados siempre pierden un poco.

### 3.9 SRP y SRP-PHAT (estimación de DOA)

La **potencia de respuesta apuntada** (*steered response power*) es la energía de la salida del DAS apuntado a cada dirección candidata:

$$
P(\theta) = \sum_{k \in \mathcal K} \Big|\, \sum_{m} w_m\, X_m[k]\; e^{+j2\pi f_k \hat\tau_m(\theta)} \Big|^2,
\qquad
\hat\theta_{\text{DOA}} = \arg\max_\theta P(\theta),
$$

donde $\mathcal K$ son los bins dentro de $[f_{\min}, f_{\max}]$. Por el teorema de Parseval, $P(\theta)$ es (salvo efectos de borde) la energía de $y_\theta(t)$. Cuando $\theta$ coincide con la dirección real, las fases $e^{-j2\pi f\tau_m}$ de la señal se cancelan con las de apuntamiento y los términos se suman en fase, lo que da el máximo.

Notas de implementación (`das.srp`):

- Se usa $e^{+j2\pi f\hat\tau_m}$ en lugar del retardo causal $e^{-j2\pi f\Delta_m}$. Difieren en el factor común $e^{-j2\pi f \max\hat\tau}$, que no cambia el módulo.
- Se evalúa una **rejilla** de azimuts (por defecto 0.5° en los scripts). La exactitud máxima está limitada por el paso de la rejilla.
- La operación es un tensor `(A, F, M)` (ángulos × bins × mics), que se procesa en bloques de 32 ángulos para acotar la memoria (~16 MB por bloque con 0.5 s de señal).
- **PHAT** (*phase transform*, `phat=True`): reemplaza $X_m[k] \to X_m[k]/\lvert X_m[k]\rvert$, de modo que todos los bins pesan igual y solo cuenta la fase. Es la variante más usada en ambientes reverberantes (DiBiase, 2000), porque evita que unas pocas frecuencias con mucha energía dominen. **No debe usarse con un tono puro**: los bins sin señal (solo fuga espectral o ruido numérico) recibirían el mismo peso que el bin del tono.

### 3.10 GCC-PHAT (medición de retardos entre pares)

Para estimar la diferencia de tiempos de llegada (TDOA) entre una señal $x$ y una referencia $r$:

$$
G[k] = X[k]\,R^*[k], \qquad
\Psi[k] = \frac{G[k]}{\lvert G[k]\rvert + \epsilon}, \qquad
\rho[n] = \mathrm{IDFT}\{\Psi[k]\}, \qquad
\hat\tau = \frac{\arg\max_n \lvert\rho[n]\rvert}{f_s} .
$$

En el caso ideal $X = R\,e^{-j2\pi f\tau}$, se tiene $\Psi = e^{-j2\pi f\tau}$ y $\rho$ es un **impulso** en $\tau$. PHAT convierte el pico ancho de la correlación cruzada clásica en uno muy agudo (Knapp & Carter, 1976).

Detalles de `das.gcc_phat`:

- **Correlación lineal, no circular:** las FFT se calculan con longitud $n = \text{len}(x) + \text{len}(r)$.
- **Resolución sub-muestra:** la IDFT se calcula con longitud $n \cdot \texttt{interp}$, lo que equivale a interpolar $\rho$ con sinc. La resolución es $1/(\texttt{interp}\cdot f_s)$: 3.9 µs con `interp=16` y 0.98 µs con `interp=64`.
- **Ventana de búsqueda física:** para cualquier posición de la fuente, por la desigualdad del triángulo, $\lvert\tau_i - \tau_j\rvert \le \lVert\mathbf p_i - \mathbf p_j\rVert/c \le D/c$. Con `max_tau = D/c` se descartan picos imposibles.
- **Signo:** $\hat\tau > 0$ significa que $x$ llega **después** que $r$.

**Hallazgo al verificar.** Con señales estacionarias (multitono, chirp), GCC-PHAT sobre una ventana finita mostró un sesgo de ~0.1 muestras. Cada canal ve un tramo ligeramente distinto de la señal en los bordes de la ventana, y PHAT amplifica esa diferencia. Con un **pulso** contenido por completo en la ventana, el error baja a <0.01 muestras. Por eso la prueba 1 usa un pulso. Es una limitación del estimador sobre ventanas finitas, no del modelo de retardos, y habrá que tenerla presente al estimar TDOA con habla real (que sí es "estacionaria por tramos").

### 3.11 Señales de prueba

Todas son **funciones continuas de $t$** (callables de Python). La simulación evalúa $s(t - \tau_m)$ exactamente para cada mic, sin interpolar, de modo que la verdad de referencia **no se genera con el mismo método que se está probando** (ver el criterio 1 de la [§4](#4-criterios-de-diseño-del-código)).

| Nombre | Expresión | Parámetros por defecto | Para qué sirve |
|:--|:--|:--|:--|
| `seno` | $A\sin(2\pi f t)$ | $f = 1$ kHz, $A = 0.5$ | Caso más simple; coincide con P1 y con Beck et al. Débil para localizar (§3.6) y ambiguo para GCC (periódico). |
| `chirp` | $A\cos\!\big(2\pi(f_0\tau + \tfrac{f_1-f_0}{2T}\tau^2)\big)$, $\tau = t \bmod T$ | 200→7000 Hz, $T = 0.5$ s, $A=0.5$ | Banda ancha con frecuencia instantánea $f_0 + (f_1-f_0)\tau/T$; útil para ver comportamiento por frecuencia. |
| `multitono` | $a\sum_{k=1}^{K}\sin(2\pi f_k t + \phi_k)$, $a = \mathrm{rms}\sqrt{2/K}$ | $K=40$, $f_k \sim \mathcal U(200, 7000)$, $\phi_k\sim\mathcal U(0,2\pi)$, rms $=0.15$, semilla 0 | Banda ancha, estacionaria y analítica. Es la señal "de trabajo" para DOA y reconstrucción. |
| `pulso` | $A\,e^{-\alpha(t-t_0)^2}\cos\big(2\pi f_c (t-t_0)\big)$ | $f_c = 2$ kHz, ancho de banda fraccional 0.8 a −6 dB (≈1.2–2.8 kHz), $t_0 = 50$ ms, $A=0.8$ | Transitorio contenido en la ventana; ideal para medir retardos con GCC (§3.10). |

Para `pulso`, $\alpha = -\dfrac{(\pi f_c\, b)^2}{4\ln\!\big(10^{b_r/20}\big)}$ con $b = 0.8$ y $b_r = -6$ dB (`scipy.signal.gausspulse`). El `chirp` es **periódico** (por el `mod T`): para $t - \tau_m < 0$ toma el final del barrido anterior, y esa discontinuidad cae dentro de la zona descartada por `RECORTE`.

Cada señal lleva dos atributos: `.nombre` (texto para figuras) y `.banda_ancha` (bool). `prueba_das.py` usa el segundo para ajustar la ventana de visualización y advertir cuando se usa un tono puro.

### 3.12 Ruido de sensor

`campo.ruido_sensor` genera ruido gaussiano blanco i.i.d. por canal con

$$
\sigma = \sqrt{\frac{P_s}{10^{\,\mathrm{SNR}/10}}},
$$

donde $P_s$ es la potencia media de la señal (sobre todos los canales). Representa ruido **propio de cada micrófono** (eléctrico, de cuantización), no ruido ambiental. El ruido ambiental de una fuente real es **direccional y correlacionado** entre mics, y se comporta de forma muy distinta frente al DAS. Semilla fija (1) para reproducibilidad.

---

## 4. Criterios de diseño del código

| # | Criterio | Justificación |
|:--:|:--|:--|
| 1 | **La verdad de referencia es independiente del método bajo prueba.** Las señales se generan analíticamente en $s(t-\tau_m)$; el DAS retrasa por FFT. | Si la simulación usara el mismo retardo por FFT que el DAS, un error en esa función se cancelaría consigo mismo y las pruebas pasarían con el código mal. |
| 2 | **La geometría es un parámetro, nunca está hardcodeada.** | Permite comparar candidatas (Obj. 1) y garantiza la paridad de procesamiento entre arreglo propuesto y baseline (Obj. 7, P2). La geometría medida entra después cambiando solo el `.json`. |
| 3 | **Mismo formato que el pipeline real:** `(N, 8)` float32 en $[-1,1]$, $f_s = 16$ kHz. | `das()` se podrá llamar sobre el frame de `hilo_sincronizador` sin adaptadores. |
| 4 | **Cálculo de retardos separado del filtrado.** `das()` recibe `tau`, no una dirección. | En tiempo real, los retardos de una dirección se calculan **una vez** y por frame solo queda FFT + multiplicación + suma. Además, se cambia de modelo (lejano/cercano) sin tocar `das()`. |
| 5 | **Causalidad:** solo retrasos ($\Delta_m \ge 0$). | En tiempo real no existen muestras futuras; el playground se comporta como se comportará el sistema. |
| 6 | **Pesos normalizados** a $\sum w_m = 1$. | Ganancia unitaria en la dirección de mirada (sin distorsión) para cualquier esquema de pesos; así distintos pesos se comparan en igualdad de condiciones. |
| 7 | **Retardos fraccionarios exactos** (en frecuencia). | Redondear cuesta hasta ~3 dB de ganancia coherente en agudos (§3.5). |
| 8 | **Vectorización NumPy**, sin loops de Python por muestra ni por canal. | Regla del proyecto (`CLAUDE.md`, decisión Python vs. Rust). El único loop es por **bloques de ángulos** en `srp()`, y existe para acotar memoria, no por comodidad. |
| 9 | **Pruebas con valor esperado analítico** y umbrales holgados frente al error numérico pero estrictos frente a bugs plausibles. | Ver la [§7.2](#72-por-qué-esos-umbrales). |
| 10 | **Reproducibilidad:** semillas fijas en `multitono` (0) y `ruido_sensor` (1). | Dos corridas con la misma configuración dan exactamente el mismo resultado; cualquier cambio en los números se debe al código. |
| 11 | **Configuración arriba del script + `CLAVE=valor` en la línea de comandos**, sin `argparse`. | Mismo estilo que `analisis.py` (variables arriba) y `monitor_8LR.py` (`debug=true`). |
| 12 | **Resultados a `SALIDAS/`** (no versionado). | Convención del repo. |
| 13 | **Separación playground / producción.** | `Exploration/` permite iterar libremente; solo lo verificado pasa a `Avances/` (§11). |

---

## 5. Referencia de la API

> Los módulos se importan como hermanos (`import campo, das, geometrias`). Al ejecutar un script de esta carpeta, Python agrega su directorio a `sys.path`, así que funciona desde cualquier directorio de trabajo.

### 5.1 `geometrias.py`

Todas las funciones de geometría devuelven `np.ndarray` de forma **`(M, 3)`** con $(x, y, z)$ en metros, una fila por micrófono, en el orden M1..M8.

#### `desde_json(ruta=RUTA_JSON_AVANCES) -> (M, 3)`
Lee posiciones desde un `.json` con el formato de `Avances/geometria.json` (lista `"micrófonos"` con `id`, `x`, `y`, `z`), ordenadas por `id`. Por defecto lee `Avances/geometria.json` (ruta absoluta calculada desde el propio módulo).

#### `ula(n=8, d=0.02) -> (n, 3)`
Arreglo lineal uniforme sobre el eje $x$, centrado en el origen: $x_m = (m - \frac{n-1}{2})\,d$. Es el **baseline** del Obj. 7. Con `d=0.02`, la apertura es de 14 cm (comparable con `placeholder_json`, 13.5 cm) y $f_{\text{alias}} = 8.6$ kHz.

#### `circular(n=8, radio=0.045) -> (n, 3)`
Arreglo circular uniforme: $\mathbf p_m = r(\cos\frac{2\pi m}{n}, \sin\frac{2\pi m}{n}, 0)$. Con los valores por defecto replica la geometría de Beck et al. (2016): 8 MEMS en una PCB de 90 mm.

#### `pares_radiales(separaciones=(0.02,0.04,0.06,0.08), orientaciones_deg=(0,45,90,135), radio_centro=0.03) -> (8, 3)`
Cuatro pares LR. El par $i$ tiene separación $d_i$, su centro está a `radio_centro` del origen en la dirección $\beta_i$ y el par se orienta **perpendicular** a ese radio. **Es solo un ejemplo** de geometría no lineal y no uniforme para ejercitar el código; **no es el diseño biomimético del TT**.

#### `GEOMETRIAS` (dict)
Registro `nombre → función sin argumentos`. Nombres actuales: `placeholder_json`, `ula_2cm`, `circular_beck`, `pares_radiales`. `verificar.py` sin argumentos recorre todas.

#### `obtener(nombre) -> (M, 3)`
Resuelve un nombre del registro **o** la ruta a un `.json`. Lanza `ValueError` con la lista de opciones si no encuentra ninguno.

#### `centroide(pos) -> (3,)`
$\bar{\mathbf p} = \frac1M\sum_m\mathbf p_m$. Es el origen de los ángulos y de la distancia a la fuente.

#### `apertura(pos) -> float`
$D = \max_{i,j}\lVert\mathbf p_i - \mathbf p_j\rVert$. Determina la resolución angular (§3.6), el criterio de campo lejano (§3.2) y el máximo TDOA físico ($D/c$).

#### `separacion_minima(pos) -> float`
Mínima distancia entre dos micrófonos distintos. Sirve para verificar que la geometría sea construible físicamente (cada ICS-43434 ocupa espacio en la PCB) y como referencia para el aliasing.

#### `eje_si_colineal(pos, tol=1e-6) -> float | None`
Hace una SVD de las posiciones centradas. Si el segundo valor singular es despreciable frente al primero ($s_1 \le \text{tol}\cdot s_0$), los mics son colineales y devuelve el ángulo $\alpha$ (grados) del eje en el plano $XY$. Si no, devuelve `None`. Con $\alpha$, el espejo de un azimut $\theta$ es $2\alpha - \theta$ (§3.7). La dirección del eje es ambigua en ±180°, pero eso no afecta la fórmula del espejo módulo 360°.

```python
import geometrias
pos = geometrias.obtener("ula_2cm")
geometrias.apertura(pos)         # 0.14
geometrias.eje_si_colineal(pos)  # 0.0  -> colineal sobre x
geometrias.eje_si_colineal(geometrias.obtener("circular_beck"))  # None
```

### 5.2 `campo.py`

Constantes: `FS = 16000`, `C_SONIDO = 343.0`.

#### Señales: `seno(f=1000, amplitud=0.5)`, `chirp(f0=200, f1=7000, duracion=0.5, amplitud=0.5)`, `multitono(fmin=200, fmax=7000, n_tonos=40, rms=0.15, semilla=0)`, `pulso(fc=2000, bw=0.8, t0=0.05, amplitud=0.8)`
Cada una devuelve un **callable** `s(t)` que acepta escalares o arreglos de cualquier forma (difunde con broadcasting) y tiene los atributos `.nombre` y `.banda_ancha`. Las fórmulas están en la §3.11. `SENALES` es el registro `nombre → fábrica` que usa `prueba_das.py`.

```python
s = campo.multitono(n_tonos=80, semilla=3)
s(np.array([0.0, 1e-3]))   # evaluar en t = 0 y 1 ms
s.nombre, s.banda_ancha    # ('multitono 80x 200-7000 Hz', True)
```

#### `vector_direccion(azimut_deg, elevacion_deg=0.0) -> (..., 3)`
$\mathbf u(\theta,\varphi)$ de la §3.2. Acepta un azimut escalar (devuelve `(3,)`) o un arreglo `(A,)` (devuelve `(A, 3)`).

#### `fuente_polar(centro, distancia, azimut_deg, altura=0.0) -> (3,)`
Posición 3D de una fuente a `distancia` (medida **en el plano XY**) y `azimut_deg` del `centro`, a la altura `altura` (desplazamiento en $z$). Con `altura ≠ 0` la distancia 3D real es $\sqrt{\text{distancia}^2 + \text{altura}^2}$.

#### `simular(posiciones, fuente, senal, fs=FS, duracion=0.5, c=C_SONIDO, modelo="esferico", atenuacion=True) -> (x, info)`

| Parámetro | Significado |
|:--|:--|
| `posiciones` | `(M, 3)` de `geometrias`. |
| `fuente` | `(3,)` posición de la fuente (con `modelo="plano"` solo importa su **dirección** desde el centroide). |
| `senal` | Callable de la §3.11. |
| `modelo` | `"esferico"`: propagación exacta desde el punto, con atenuación $R/r_m$ si `atenuacion=True` (§3.1). `"plano"`: onda plana desde la dirección de la fuente, $a_m = 1$ (§3.2). |
| `duracion` | Segundos; $N = \mathrm{round}(\text{duracion}\cdot f_s)$ muestras. |

Devuelve:
- `x`: `(N, M)` float32, la "grabación" ideal.
- `info["t"]`: `(N,)` instantes de muestreo (s).
- `info["tau"]`: `(M,)` tiempos de llegada **verdaderos** (s), absolutos (incluyen $R/c$).
- `info["ganancias"]`: `(M,)` los $a_m$.

Uso típico de `info`: construir la señal de referencia que el DAS debería entregar (§7.1), o comparar retardos medidos contra teóricos.

#### `ruido_sensor(n, m, snr_db, potencia_senal, semilla=1) -> (n, m)`
Ruido blanco gaussiano i.i.d. (§3.12), float32. `potencia_senal` suele ser `np.mean(x**2)`.

### 5.3 `das.py`

#### `retardos_campo_lejano(posiciones, azimut_deg, elevacion_deg=0.0, c=C_SONIDO) -> (M,) | (A, M)`
$\hat\tau_m = -\mathbf u(\theta,\varphi)\cdot\mathbf q_m / c$, referidos al centroide (§3.3). Con un azimut escalar devuelve `(M,)`; con un arreglo `(A,)` devuelve `(A, M)` (lo usa `srp`).

#### `retardos_campo_cercano(posiciones, punto, c=C_SONIDO) -> (M,) | (A, M)`
$\hat\tau_m = \lVert\mathbf s - \mathbf p_m\rVert/c$ hacia un punto `(3,)` o varios `(A, 3)`. Hace falta cuando la fuente está más cerca que $R_F$ (§3.2), y es la base de una futura localización 2D (ángulo y distancia).

#### `alinear(frame, tau, fs) -> (N, M)`
Retrasa cada canal $\Delta_m = \max\tau - \tau_m$ con retardo fraccionario exacto por FFT (§3.5). Devuelve los canales **alineados** sin sumar; sirve para inspeccionar la alineación o para construir otros beamformers sobre ella.

#### `das(frame, tau, fs, pesos=None) -> (N,)`
Delay-and-sum (§3.4): `alinear(...) @ w`. Con `pesos=None` usa $w_m = 1/M$ (DAS convencional); si no, normaliza `pesos / sum(pesos)`.
- `frame`: `(N, M)`.
- `tau`: `(M,)` retardos de apuntamiento de `retardos_campo_*`, o los que se quieran probar.
- **Precaución:** pesos que sumen 0 (p. ej. diferenciales $+1, -1$) dividen entre cero. Ese caso (beamformers diferenciales) requeriría otra normalización.

#### `srp(frame, posiciones, azimuts_deg, fs, c=C_SONIDO, pesos=None, phat=False, fmin=100.0, fmax=None, bloque=32) -> (A,)`
Mapa de potencia $P(\theta)$ sobre la rejilla `azimuts_deg` (§3.9), en campo lejano y con elevación 0. La DOA es `azimuts_deg[np.argmax(P)]`.
- `fmin`, `fmax`: banda usada (por defecto 100 Hz – $f_s/2$). Restringirla a la banda de voz reduce el costo y el efecto de ruido fuera de banda.
- `phat`: SRP-PHAT; **no** usar con tonos puros.
- `bloque`: ángulos por bloque (compromiso entre memoria y velocidad).

#### `gcc_phat(x, ref, fs, max_tau=None, interp=16) -> float`
TDOA de `x` respecto a `ref` en segundos (§3.10). Positivo si `x` llega después. Pasar `max_tau = apertura/c` para limitar la búsqueda a retardos físicos. **Ambiguo para tonos puros** (la correlación de una senoidal es periódica).

```python
import numpy as np, campo, das, geometrias

pos    = geometrias.obtener("circular_beck")
centro = geometrias.centroide(pos)
fuente = campo.fuente_polar(centro, distancia=1.0, azimut_deg=45)
x, info = campo.simular(pos, fuente, campo.multitono(), duracion=0.5)

tau = das.retardos_campo_lejano(pos, 45)        # apuntar a 45°
y   = das.das(x, tau, campo.FS)                 # (8000,) señal mejorada

rejilla = np.arange(0, 360, 1.0)
P = das.srp(x, pos, rejilla, campo.FS)
print("DOA:", rejilla[P.argmax()])               # 45.0

dt = das.gcc_phat(x[:, 3], x[:, 0], campo.FS, geometrias.apertura(pos) / campo.C_SONIDO)
print("TDOA M4-M1 (µs):", dt * 1e6, "teórico:", (info["tau"][3] - info["tau"][0]) * 1e6)
```

---

## 6. `prueba_das.py` — escenario visual

### 6.1 Configuración

Variables al inicio del script. Cualquiera se puede sobreescribir con `CLAVE=valor`:

| Variable | Default | Valores | Efecto |
|:--|:--|:--|:--|
| `GEOMETRIA` | `"placeholder_json"` | nombre de `GEOMETRIAS` o ruta `.json` | Posiciones de los mics. |
| `DISTANCIA` | `1.0` | m | Distancia de la fuente al centroide, en el plano XY. |
| `AZIMUT` | `60.0` | grados | Dirección real de la fuente. |
| `ALTURA` | `0.0` | m | $z$ de la fuente (≠ 0 → fuera del plano, §3.7). |
| `SENAL` | `"seno"` | `seno`, `chirp`, `multitono`, `pulso` | Señal de la fuente (§3.11). |
| `FRECUENCIA` | `1000.0` | Hz | Solo aplica a `seno`; las demás usan sus parámetros por defecto. |
| `DURACION` | `0.5` | s | Longitud de la simulación. |
| `MODELO` | `"esferico"` | `esferico`, `plano` | Física de la simulación (§3.1–3.2). |
| `APUNTE` | `"lejano"` | `lejano`, `cercano` | Modelo de retardos del DAS. `cercano` apunta al punto exacto de la fuente. |
| `SNR_SENSOR` | `None` | dB o `None` | Ruido blanco por mic (§3.12). |
| `PESOS` | `None` | `None` o lista de 8 números | Pesos del DAS y del SRP (§3.8). |

Los valores se interpretan como JSON (números, `null`, listas). Si no son JSON válido, quedan como texto. Un nombre de variable desconocido termina el programa con un mensaje de error.

```bash
python prueba_das.py GEOMETRIA=circular_beck SENAL=multitono AZIMUT=200 DISTANCIA=0.5
python prueba_das.py MODELO=esferico APUNTE=cercano DISTANCIA=0.3 SENAL=pulso
python prueba_das.py SNR_SENSOR=0 --no-show
```

> **PowerShell:** las comas sin comillas se interpretan como arreglos de PowerShell. Las listas van entre comillas: `python prueba_das.py "PESOS=[1,1,1,1,2,2,2,2]"`.

`--no-show` no abre ventana (backend `Agg`) y solo guarda el PNG.

### 6.2 Salidas

- Consola: el resumen numérico (el mismo del panel f).
- Archivo: `SALIDAS/sim_das_{GEOMETRIA}_{SENAL}_az{AZIMUT}.png` (se sobreescribe si se repiten esos tres parámetros).

### 6.3 Cómo leer los seis paneles

| Panel | Qué muestra | Qué buscar |
|:--|:--|:--|
| **(a) Escena** | Plano XY a escala real: mics (puntos de color), fuente (estrella roja), círculo de radio `DISTANCIA`, línea roja punteada centroide→fuente y línea verde centroide→DOA estimada. | Que la línea verde se superponga con la roja. Da una idea de cuán "lejos" está la fuente comparada con el tamaño del arreglo. |
| **(b) Arreglo** | Zoom en cm. Cada mic se etiqueta con su **retardo de llegada relativo** (µs, el primero en recibir = 0). La flecha indica la dirección hacia la fuente. | Los mics más cercanos a la flecha deben tener los retardos más pequeños. Es una comprobación intuitiva de la física. |
| **(c) Señales** | Los 8 canales apilados en una ventana corta (4 ms para tonos, 1.5 ms para banda ancha), con puntos en cada muestra. | Los desfases entre canales. Que los retardos sean de fracciones de muestra se nota en que la "forma" se desplaza sin coincidir con la rejilla de muestras. |
| **(d) SRP polar** | $10\log_{10}(P/P_{\max})$, recortado a −30 dB; línea roja punteada = azimut real, línea verde = estimado. | El ancho del lóbulo (resolución, §3.6), los lóbulos secundarios (aliasing) y la simetría espejo en arreglos colineales (§3.7). |
| **(e) Salida vs. original** | 5 ms a mitad de la señal: la referencia alineada y escalada (gris grueso), la salida del DAS (azul) y M1 crudo (punteado). | Que la azul quede encima de la gris. M1 crudo muestra cuánto desfase corrigió el DAS (si M1 es el último en recibir, coincide con la salida). |
| **(f) Resumen** | Configuración y métricas: DOA estimada y su error, error de reconstrucción en dB, ganancia ajustada $g$, retardo máximo entre mics, avisos (colineal, tono puro). | Error de DOA ≈ 0° y error de salida ≪ −40 dB en condiciones ideales. Con `SNR_SENSOR`, el error de salida ≈ −(SNR + WNG) dB. |

### 6.4 Escenarios recomendados

| Para ver… | Comando |
|:--|:--|
| Falta de directividad de un tono de 1 kHz | `SENAL=seno` (default) |
| Cómo se cierra el lóbulo en banda ancha | `SENAL=multitono` |
| Ambigüedad frente/espalda | `GEOMETRIA=ula_2cm SENAL=multitono AZIMUT=60` → lóbulo espejo en 300° |
| Error de modelo de campo cercano | `GEOMETRIA=pares_radiales SENAL=multitono DISTANCIA=0.3` (comparar con `APUNTE=cercano`) |
| WNG de 9 dB | `MODELO=plano SENAL=multitono SNR_SENSOR=0` → error de salida ≈ −9 dB |
| Costo de los pesos no uniformes | lo anterior + `"PESOS=[1,1,1,1,2,2,2,2]"` → ≈ −8.6 dB |
| Fuente fuera del plano | `ALTURA=0.5 SENAL=multitono` |

---

## 7. `verificar.py` — batería de verificación

```bash
python verificar.py                    # las 4 geometrías del registro
python verificar.py ula_2cm            # solo una
python verificar.py ruta/a/mi.json     # una geometría desde archivo
```

Imprime `[PASA]`/`[FALLA]` por prueba y un resumen. El **código de salida** es 0 si todo pasa y 1 si hay alguna falla, así que sirve en scripts o hooks.

### 7.1 Metodología: métrica de error y referencia

**Referencia.** Lo que el DAS *debería* entregar es la señal original retrasada al instante de alineación:

$$
r(t) = s(t - T), \qquad T = \frac1M\sum_m \big(\tau_m + \Delta_m\big),
$$

con los $\tau_m$ **verdaderos** de la simulación. Si el apuntamiento es exacto, todos los $\tau_m + \Delta_m$ son iguales (§3.4) y el promedio es solo una forma robusta de calcular $T$.

**Error de reconstrucción.** Sobre el interior $\mathcal I$ (se descartan 160 muestras = 10 ms en cada borde, §3.5):

$$
g = \frac{\langle y, r\rangle_{\mathcal I}}{\langle r, r\rangle_{\mathcal I}}, \qquad
E = 10\log_{10}\frac{\sum_{\mathcal I}\big(y - g\,r\big)^2}{\sum_{\mathcal I}\big(g\,r\big)^2}\ \text{[dB]} .
$$

La ganancia $g$ se ajusta por mínimos cuadrados porque en campo esférico la amplitud de salida es $\sum_m w_m a_m \ne 1$ (§3.4). La prueba evalúa **forma y temporización**; la ganancia se reporta aparte.

**Ganancia de SNR.** Por linealidad, $\mathrm{DAS}(x + n) = \mathrm{DAS}(x) + \mathrm{DAS}(n)$. Se procesan por separado la señal limpia y el ruido, y

$$
\Delta\mathrm{SNR} = 10\log_{10}\frac{P\{\mathrm{DAS}(x)\}}{P\{\mathrm{DAS}(n)\}} - 10\log_{10}\frac{P\{x\}}{P\{n\}} .
$$

### 7.2 Las pruebas y por qué esos umbrales

| # | Prueba | Escenario | Criterio | Por qué ese umbral |
|:--:|:--|:--|:--|:--|
| 1 | **Retardos** GCC-PHAT vs. teóricos | Pulso, fuente esférica a 1 m, 30°; `interp=64`; todos los mics contra M1 | error máx < **0.05 muestras** (3.1 µs) | La resolución de la interpolación es 1/64 de muestra. Con un pulso el error observado es <0.01 (§3.10). Un error de signo, de geometría o de $c$ da errores de muestras completas. |
| 2a | **Reconstrucción campo lejano**, tono | Onda plana, 1 kHz, 70°, 3 m | $E <$ **−40 dB** | Un error de **media muestra en un solo canal** a 1 kHz ya produce ≈$20\log_{10}(2\pi\cdot 1000\cdot 31.25\,\mu\text{s}/8) \approx$ **−32 dB**. −40 dB detecta cualquier bug realista y está muy por encima del ruido numérico (se observan −104 a −126 dB). |
| 2b | **Reconstrucción campo lejano**, banda ancha | Onda plana, multitono, 70°, 3 m | $E <$ −40 dB | Igual. En banda ancha los errores de retardo pesan más (crecen con $f$). |
| 3 | **Reconstrucción campo cercano** | Fuente esférica a **30 cm**, 200°, con $1/r$; DAS de campo cercano al punto exacto | $E <$ −40 dB | A 30 cm la curvatura es grande (§3.2). Si el modelo cercano estuviera mal, el error sería mucho mayor. |
| 4 | **DOA por SRP** | Multitono, fuente esférica a 2 m, 24 azimuts (0°–345° cada 15°), rejilla 0.5° | error máx ≤ **1°** | Rejilla de 0.5° + sesgo de campo cercano a 2 m (~0.5° en la geometría más asimétrica). En arreglos **colineales** se acepta el espejo y se reporta cuántas veces ocurrió. |
| 5 | **Ganancia de SNR** | Onda plana, multitono, 120°, **2 s**, SNR de entrada 0 dB, pesos uniformes | $\lvert\Delta\mathrm{SNR} - 9.03\rvert <$ **0.3 dB** | Valor teórico exacto $10\log_{10}M$ (§3.8). Con 32 000 muestras, la incertidumbre estadística de cada potencia es ≈0.03 dB; 0.3 dB deja margen y aun así detecta, por ejemplo, pesos mal normalizados o canales perdidos (1 canal menos → 8.45 dB). |

### 7.3 Cómo leer la salida

```
── ula_2cm  (apertura 14.0 cm, sep. mín 2.0 cm, COLINEAL)
  [PASA] Retardos GCC-PHAT vs teóricos (pulso)          err máx = 0.007 muestras
  [PASA] Reconstrucción campo lejano (seno 1000 Hz)     error = -105.3 dB
  ...
  [PASA] DOA por SRP en 24 azimuts (fuente a 2 m)       err máx = 0.0° (11 resueltos solo como espejo)
```

"11 resueltos solo como espejo" significa que en 11 de los 24 azimuts el SRP eligió el ángulo espejo. Es el comportamiento esperado de un ULA (§3.7), **no un bug**. En una geometría no colineal, ese número no debe aparecer.

### 7.4 Resultados actuales

Corrida del 2026-10-07:

| Geometría | Apertura | Retardos (muestras) | Rec. lejano tono | Rec. lejano BA | Rec. cercano | DOA | ΔSNR |
|:--|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| `placeholder_json` | 13.5 cm | 0.008 | −105.5 dB | −81.1 dB | −74.1 dB | 0.0° | 8.99 dB |
| `ula_2cm` | 14.0 cm | 0.007 | −105.3 dB | −78.5 dB | −82.6 dB | 0.0° (11 espejo) | 9.00 dB |
| `circular_beck` | 9.0 cm | 0.008 | −125.8 dB | −74.7 dB | −68.2 dB | 0.0° | 8.98 dB |
| `pares_radiales` | 8.8 cm | 0.007 | −103.8 dB | −83.2 dB | −73.8 dB | 0.5° | 9.08 dB |

---

## 8. Recetas de uso

### 8.1 Probar una geometría nueva

**Opción A — `.json`** (recomendada para geometrías "de verdad", porque es el mismo formato que usará el sistema). Copiar `Avances/geometria.json`, editar `x, y, z` y correr:

```bash
python verificar.py mis_geometrias/candidata_A.json
python prueba_das.py GEOMETRIA=mis_geometrias/candidata_A.json SENAL=multitono
```

**Opción B — función paramétrica** (para barrer parámetros). En `geometrias.py`:

```python
def mi_geometria(d1=0.02, d2=0.035):
    ...
    return np.array(pos)            # (8, 3)

GEOMETRIAS["mi_geometria"] = mi_geometria
```

Antes de dar por buena una geometría, comprobar: (1) que `verificar.py` pase completo, (2) que `eje_si_colineal` sea `None` (D1), (3) que `separacion_minima` sea físicamente construible y (4) que el patrón SRP con `multitono` no tenga lóbulos secundarios comparables al principal.

### 8.2 Comparar geometrías (base de P2)

Mismo escenario y mismo procesamiento; solo cambia `GEOMETRIA`:

```bash
for g in placeholder_json ula_2cm circular_beck pares_radiales; do
  python prueba_das.py GEOMETRIA=$g SENAL=multitono AZIMUT=60 --no-show
done
```

Para una comparación cuantitativa (p. ej. error de DOA medio en 360° con ruido), conviene escribir un script de barrido sobre la API (§5) en lugar de mirar figuras.

### 8.3 Probar un esquema de pesos (D2)

```bash
python prueba_das.py MODELO=plano SENAL=multitono SNR_SENSOR=0 "PESOS=[1,1,1,1,2,2,2,2]"
```

Recordar la §3.8: contra ruido blanco el DAS uniforme es óptimo. Un esquema de pesos debe evaluarse contra el mecanismo que pretende explotar (amplitudes distintas, interferente direccional).

### 8.4 Agregar un algoritmo nuevo (p. ej. MVDR, DAS ponderado en frecuencia)

1. Implementarlo en `das.py` (o en un módulo nuevo) respetando los criterios de la §4: entrada `(N, M)`, vectorizado, causal y con ganancia unitaria en la dirección de mirada.
2. Agregar a `verificar.py` al menos una prueba con **resultado analítico conocido** (p. ej. MVDR debe reducirse a DAS con ruido blanco; con un interferente debe poner un nulo en su dirección).
3. Exponerlo en `prueba_das.py` como opción de CONFIG.

### 8.5 Uso programático

Ver el ejemplo al final de la §5.3. Todo lo que hacen los scripts está disponible como funciones.

---

## 9. Rendimiento

Medido en la PC de desarrollo (Windows, Python 3.11, NumPy 2.3). La Raspberry Pi será más lenta: **hay que medir allá** antes de decidir.

| Operación | Tamaño | Tiempo | Fracción del presupuesto por frame (32 ms) |
|:--|:--|:--:|:--:|
| `das()` | frame `(512, 8)` | **≈135 µs** | ≈0.4% |
| `srp()`, rejilla 1° (360 ángulos) | `(512, 8)`, banda completa | ≈16 ms | ≈50% |
| `srp()`, rejilla 0.5° (720 ángulos) | `(512, 8)`, banda completa | ≈31 ms | ≈96% |

Conclusiones:
- **El DAS es trivial** en costo. Confirma la decisión de quedarse en Python + NumPy (`CLAUDE.md`).
- **El SRP con rejilla fina no cabe en cada frame.** En tiempo real hay varias opciones: rejilla de 2–5° con refinamiento local alrededor del máximo (*coarse-to-fine*), restringir la banda (p. ej. 300–4000 Hz), y/o actualizar la DOA cada N frames (Beck et al. la estiman cada 500 ms ≈ 16 frames). La dirección de una persona hablando no cambia en 32 ms.

---

## 10. Supuestos y limitaciones

| Supuesto o limitación | Consecuencia | Cuándo atenderlo |
|:--|:--|:--|
| **Sin reverberación** (campo libre) | En una sala, las reflexiones son fuentes virtuales coherentes: el SRP mostrará picos falsos y el DAS dejará pasar parte del eco. PHAT ayuda. | Antes de la evaluación en entornos reales; simulable con el método de imágenes (p. ej. `pyroomacoustics`) si se decide. |
| **Sin ruido ambiental direccional** | Hoy solo hay ruido de sensor (blanco, independiente). C3 y D8 hablan de ruido de una **fuente** simultánea. | **Siguiente paso** (§12). |
| **Micrófonos ideales** (misma sensibilidad y fase, omnidireccionales) | Diferencias reales de sensibilidad entre ICS-43434 equivalen a $a_m$ distintos no modelados; los errores de fase, a errores de retardo. | Al pasar al hardware: calibrar ganancias por canal. |
| **Geometría exacta** | Un error de posición $\delta$ equivale a un error de retardo $\delta/c$; con 2 mm, ≈5.8 µs ≈ 0.09 muestras. | Simular perturbaciones aleatorias de posición para conocer la tolerancia de medición requerida para `geometria.json`. |
| **$c$ fija en 343 m/s** | $c \approx 331.3 + 0.606\,T_{°C}$ m/s: a 30 °C es ≈349.5 m/s (+1.9%), lo que escala todos los retardos. Sobre ~390 µs de apertura, ≈7 µs ≈ 0.12 muestras. | Medir la temperatura en las pruebas reales o estimar $c$. |
| **Sin deriva de reloj entre placas** | Las dos ESP32-S3 arrancan alineadas por el pulso SYNC, pero cada una muestrea con su propio cristal. Una diferencia de reloj de, por ejemplo, 20 ppm (**valor ilustrativo, no medido**) acumularía 20 µs por segundo (≈0.3 muestras/s) entre M1–M4 y M5–M8, y el DAS se desalinearía en segundos. | **Medir pronto** con hardware: grabar un pulso o chirp largo y seguir con GCC-PHAT el TDOA entre un mic de cada placa a lo largo del tiempo. Una pendiente distinta de cero es deriva. Simulable aquí agregando un retardo creciente a los canales 5–8. |
| **Sin cuantización int16 ni máscara de 2 bits de ID** | El pipeline real descarta los 2 LSB (`& 0xFFFC`) → piso de cuantización de 14 bits efectivos. | Se puede agregar a `simular()` para ver el piso de ruido real. |
| **Procesamiento por bloque completo** | Los bordes de la FFT circular no importan aquí (se recortan), pero en frames de 512 muestras sí. | Antes de integrar al pipeline (§12). |
| **SRP solo en azimut y campo lejano** | No estima distancia ni elevación. | Si la aplicación lo requiere: SRP sobre una rejilla de puntos con `retardos_campo_cercano`. |
| **Una sola fuente** | No se prueba la resolución entre dos fuentes cercanas. | Junto con el ruido direccional. |

---

## 11. Criterios para promover un algoritmo a `Avances/`

Un algoritmo pasa de este playground a `Avances/` (y eventualmente a `hilo_sincronizador` en `monitor_8LR.py`) cuando:

1. **Pasa `verificar.py`** completo en todas las geometrías candidatas y en la geometría medida.
2. **Funciona frame a frame** con `CHUNK = 512`, con continuidad entre frames (sin clics ni transitorios en las fronteras) y su latencia agregada está documentada.
3. **Su costo está medido en la Raspberry Pi** y deja margen holgado dentro de los 32 ms por frame, junto con el resto del pipeline (lectura serial y audio).
4. **Respeta la vectorización** (`CLAUDE.md`).
5. **Queda documentado** en `Avances/Documentation.md` (cómo y por qué) y en `CHANGELOG.md`.
6. **Usa la geometría real** de `Avances/geometria.json` con medidas físicas, no placeholders (R1 de `CONTEXTO.md`).

---

## 12. Hoja de ruta

En orden sugerido. Lo marcado como compromiso viene de `CONTEXTO.md`.

1. **Ruido direccional** — segunda fuente puntual (ruido blanco o habla) en otra dirección, con SNR de entrada controlada de −5 a 10 dB. Métrica: mejora de SNR. Es la base de C3 y D8 (**compromiso**).
2. **Comparación P2** — script de barrido: misma escena y mismo procesamiento en el ULA y en las geometrías candidatas, con error de DOA y mejora de SNR en 360°.
3. **Deriva de reloj e imperfecciones** — retardo creciente entre placas, error de posición y ganancias desiguales, para conocer las tolerancias que debe cumplir el hardware.
4. **DAS en tiempo real** — FIR de retardo fraccionario (sinc enventanada, Lagrange o Farrow; Laakso et al., 1996) aplicado con overlap-save sobre frames de 512 muestras; documentar la latencia agregada (≈ media longitud del filtro).
5. **Pesos diferenciados (D2)** — evaluarlos contra ruido direccional y con amplitudes de campo cercano (§3.8).
6. **DOA en tiempo real** — SRP-PHAT coarse-to-fine, actualizado cada N frames.
7. **Habla real** — reemplazar las señales sintéticas por grabaciones limpias (con referencia disponible, D10) para preparar PESQ/STOI.

---

## 13. Glosario

| Término | Significado |
|:--|:--|
| **Apertura ($D$)** | Distancia máxima entre dos micrófonos del arreglo. |
| **Beamforming** | Combinar las señales de varios sensores para favorecer una dirección espacial. |
| **Campo cercano / lejano** | Régimen en el que la curvatura del frente de onda es / no es apreciable sobre el arreglo (§3.2). |
| **Coherente (suma)** | Suma de señales en fase: las amplitudes se suman. En una suma incoherente se suman potencias. |
| **DAS** | *Delay-and-sum*: retrasar y sumar (§3.4). |
| **DOA** | *Direction of arrival*: dirección de llegada de la fuente. |
| **Distortionless** | Ganancia unitaria y sin distorsión para la señal de la dirección de mirada. |
| **GCC-PHAT** | Correlación cruzada generalizada con transformada de fase (§3.10). |
| **Lóbulo principal / secundario / de rejilla** | Máximo del patrón en la dirección de mirada / máximos menores / réplicas por aliasing espacial. |
| **MRC** | *Maximal ratio combining*: pesos proporcionales a la amplitud de la señal en cada canal. |
| **Overlap-save** | Técnica para filtrar una señal continua por bloques con FFT sin artefactos en las fronteras. |
| **PHAT** | Normalizar el espectro por su magnitud, de modo que solo cuenta la fase. |
| **Retardo fraccionario** | Retardo que no es múltiplo entero del periodo de muestreo. |
| **SRP** | *Steered response power*: potencia de salida del beamformer en función de la dirección (§3.9). |
| **Steering (apuntamiento)** | Elegir los retardos o fases que hacen que el beamformer "mire" a una dirección. |
| **TDOA** | *Time difference of arrival*: diferencia de tiempos de llegada entre dos mics. |
| **ULA** | *Uniform linear array*: arreglo lineal uniforme. |
| **WNG** | *White noise gain*: ganancia de SNR frente a ruido blanco independiente (§3.8). |

---

## 14. Referencias

1. H. L. Van Trees, *Optimum Array Processing (Part IV of Detection, Estimation, and Modulation Theory)*. Wiley, 2002. — Teoría general de arreglos, patrón de haz, WNG.
2. J. Benesty, J. Chen, Y. Huang, *Microphone Array Signal Processing*. Springer, 2008. — Beamforming y localización aplicados a micrófonos y voz.
3. C. H. Knapp, G. C. Carter, "The generalized correlation method for estimation of time delay," *IEEE Trans. Acoustics, Speech, and Signal Processing*, vol. 24, no. 4, pp. 320–327, 1976. — GCC y la ponderación PHAT.
4. J. H. DiBiase, *A High-Accuracy, Low-Latency Technique for Talker Localization in Reverberant Environments Using Microphone Arrays*, tesis doctoral, Brown University, 2000. — SRP-PHAT.
5. T. I. Laakso, V. Välimäki, M. Karjalainen, U. K. Laine, "Splitting the unit delay: Tools for fractional delay filter design," *IEEE Signal Processing Magazine*, vol. 13, no. 1, pp. 30–60, 1996. — Retardos fraccionarios (sinc enventanada, Lagrange, Farrow).
6. C. Beck, G. Garreau, J. Georgiou, "Sound Source Localization through 8 MEMS Microphones Array Using a Sand-Scorpion-Inspired Spiking Neural Network," *Frontiers in Neuroscience*, vol. 10, p. 479, 2016. — Referencia [34] de `CONTEXTO.md`; geometría `circular_beck`.
