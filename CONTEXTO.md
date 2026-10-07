# CONTEXTO — Fuente de verdad del Trabajo Terminal

> **Qué es este documento.** La referencia autoritativa de **a qué nos comprometimos** y **en qué orden hay que construirlo**. Todo lo que se haga en este repositorio se subordina a lo aquí registrado.
>
> **Jerarquía de fuentes** (si dos se contradicen, gana la de arriba):
>
> 1. **`PROTOCOLO_TT.pdf`** — documento institucional entregado y firmado (18 hojas, 26/06/2026). Fuente última. Si algo de este archivo lo contradice, se corrige *este* archivo.
> 2. **`CONTEXTO.md`** (este documento) — el protocolo destilado a compromisos verificables, el orden de construcción, y lo que se añade por encima.
> 3. **`Avances/Documentation.md`** — bitácora técnica de *cómo* está implementado (pines, hilos, protocolo serie, despliegue) — y los **README de cada carpeta** (p. ej. `Exploration/beamforming_algorithms/README.md`). Describen la implementación; **no definen alcance**.
> 4. **El código.**

---

## 0. Regla de oro

Todo lo que aparece en este repositorio cae en una de dos categorías, y **nunca se mezclan**:

| | **COMPROMISO** | **EXTENSIÓN** |
|:--|:--|:--|
| Origen | Está en `PROTOCOLO_TT.pdf` | No está en el protocolo |
| Negociable | No | Sí |
| Si falta | El TT **no cumple** | El TT cumple igual |
| Prioridad | Siempre primero | Solo sobre compromiso ya cerrado |

**Ninguna extensión se trabaja antes de que el compromiso que la contiene esté cerrado.** Cuando haya que decidir en qué gastar tiempo, gana lo que cierra un objetivo del protocolo. Las extensiones existen para *reforzar* los compromisos (darles validación externa y robustez), no para competir con ellos.

---

## 1. Identidad del proyecto

| Campo | Valor |
|:--|:--|
| **Título** | Sistema de localización acústica multimicrófono basado en mecanismos de detección vibracional de escorpiones para la mejora de la inteligibilidad del habla en entornos acústicamente adversos |
| Número de proyecto | `DTA.MI.2026-2.5BM1.LMP.01` |
| Programa | Ingeniería Biónica — UPIITA-IPN |
| Semestre | 2026/2 |
| Alumno 1 | Deloiza Rodríguez Arturo |
| Alumno 2 | Jiménez Jiménez Atenea |
| Asesor 1 | Ing. Carlos Ríos Ramírez (Biónica, interno) |
| Asesor 2 | Dr. Álvaro Anzueto Ríos (Biónica, interno) |
| Asesor 3 | Dr. Carlos Carrizales Velázquez (externo) |
| Profesora titular | Dra. Lilia Martínez Pérez |
| Fecha de propuesta | 18/05/2026 · Protocolo fechado 26/06/2026 |
| Confidencialidad | PÚBLICO |

---

## 2. EL COMPROMISO

### 2.1 Hipótesis (textual del protocolo)

> Un sistema de localización acústica y mejora del habla basado en un arreglo de micrófonos inspirado en las *slit sensilla* de los escorpiones permite **incrementar en al menos 10%** las métricas de Inteligibilidad Objetiva a Corto Plazo y Evaluación Perceptual de la Calidad del Habla frente a señales degradadas con ruido, así como **mejorar en al menos 3 decibeles** la relación señal-ruido respecto a un **arreglo lineal uniforme con beamforming delay-and-sum convencional**, bajo condiciones de relación señal-ruido entre **−5 dB a 10 dB**.

### 2.2 Objetivo general (textual del protocolo)

> Desarrollar un sistema de adquisición y procesamiento de señales de audio, enfocado en la localización de la fuente del habla y la mejora de su inteligibilidad en entornos con condiciones acústicas adversas, basado en el mecanismo de sensado vibracional durante la fase de depredación de los escorpiones.

### 2.3 Objetivos específicos (textual del protocolo)

1. **Adaptar** la distribución geométrica y el esquema de muestreo espacial inspirados en las *slit sensilla* del escorpión a un arreglo multimicrófono **no uniforme** basado en diferencias de amplitud y tiempo de llegada.
2. **Diseñar** un dispositivo de adquisición multimicrófono basado en los mecanismos de detección vibracional propuestos.
3. **Recopilar** una base de datos de señales de habla, ruido y habla combinada con ruido.
4. **Elaborar** un modelo de clasificación entre señales de habla y ruido a partir de la base de datos propuesta.
5. **Implementar** un método de estimación de la dirección de la fuente sonora y de *beamforming* basado en el mecanismo de detección vibracional.
6. **Integrar** los módulos de adquisición, clasificación, localización y procesamiento para la mejora de la inteligibilidad del habla.
7. **Comparar** el desempeño del sistema contra un arreglo lineal uniforme **del mismo número de micrófonos** procesado con *beamforming* delay-and-sum convencional, bajo **idénticas condiciones de entrada** y en el rango de SNR de −5 dB a 10 dB.
8. **Evaluar** el desempeño en términos de mejora de SNR, PESQ y STOI, en ambientes acústicamente adversos con SNR de entrada en el rango de −5 dB a 10 dB.

### 2.4 Los números que nos obligan

Estos son los criterios contra los que se juzgará si el TT cumplió. No son aspiracionales.

| # | Criterio | Umbral comprometido | Se mide contra | Obj. |
|:--|:--|:--|:--|:--:|
| C1 | Mejora de **STOI** | **≥ 10%** | Señal degradada con ruido | 8 |
| C2 | Mejora de **PESQ** | **≥ 10%** | Señal degradada con ruido | 8 |
| C3 | Mejora de **SNR** | **≥ 3 dB** | Arreglo lineal uniforme + DAS convencional | 7, 8 |
| C4 | Rango de operación | SNR de entrada **−5 dB a 10 dB** | — | 7, 8 |
| C5 | Paridad del baseline | **Mismo número de micrófonos (8)** | — | 7 |
| C6 | Paridad de condiciones | **Idénticas condiciones de entrada** | — | 7 |

> **Ojo con C1/C2:** el protocolo compromete mejora **relativa** (≥10%) sobre la señal degradada, no un valor absoluto de STOI/PESQ. Al reportar hay que dar ambos (valor base y valor procesado) para que el porcentaje sea auditable.
>
> **Ojo con C3:** la mejora de 3 dB es **contra el arreglo lineal uniforme**, no contra la señal cruda. Es una comparación entre dos sistemas, no entre entrada y salida.

### 2.5 Compromisos de diseño fáciles de perder de vista

Están en la prosa del protocolo (Solución Propuesta, pp. 6-8) y obligan igual que los objetivos numerados. Se listan aquí porque son los que más fácil se olvidan:

| # | Compromiso | Cita/fuente | Riesgo si se olvida |
|:--|:--|:--|:--|
| D1 | La geometría es **no lineal**, no solo no uniforme: *"cuatro pares de micrófonos en una configuración **no lineal** con separaciones y pesos diferenciados"* | p. 7 | Si los 8 mics quedan colineales, el arreglo *es* un arreglo lineal y la comparación del Obj. 7 pierde sentido |
| D2 | **Pesos diferenciados** por micrófono, no solo separaciones diferenciadas | p. 7 | Si nuestro procesamiento es DAS uniforme puro, la única diferencia con el baseline sería la geometría — se pierde la mitad de la propuesta biomimética |
| D3 | El baseline usa **el mismo sistema físico** reconfigurado (mismas 2 placas, mismos 8 mics), solo cambia la disposición y su `geometria.json` | Obj. 7 + decisión de proyecto | Si el baseline usa otro hardware, las diferencias podrían venir del hardware y no de la geometría |
| D4 | La referencia biológica son las **slit sensilla**, explícitamente **no** las *trichobothria* | pp. 13-14 | Las trichobothria son lo "obvio" para audio (detectan flujo de aire, como un micrófono). El protocolo las descarta a propósito: el principio de modulación del campo de tensiones se validó sobre las slit sensilla. Confundirlas rompe el fundamento |
| D5 | La adaptación es **funcional, no una réplica**: el puente entre dominios es el *muestreo espacial diferencial* | p. 7 | Justificar el diseño como "copia del escorpión" es atacable; el argumento válido es la lógica funcional |
| D6 | Caracterización de SNR con **sonómetro**, por **dos mediciones consecutivas** (ruido de fondo sin habla, luego con habla activa); el resultado es una **estimación aproximada** | pp. 7-8 | El sonómetro no mide SNR directamente. Reportarlo como medición exacta es incorrecto y el protocolo ya lo advierte |
| D7 | La base de datos usa **dos estrategias complementarias**: mezclas sintéticas de bases públicas + grabaciones propias con el dispositivo en entornos controlados | pp. 7-8 | Solo sintético o solo propio incumple el Obj. 3 tal como está redactado |
| D8 | **Entorno acústicamente adverso** := SNR entre −5 y 10 dB **con al menos una fuente de ruido activa simultánea** a la fuente de habla | p. 8 | La simultaneidad es parte de la definición, no un detalle |
| D9 | **Implementación del sistema de adquisición a PCB** es una meta del Gantt (meta 5, $1,000, 3 semanas) | Tabla 2, p. 16 | **No es opcional: está calendarizada y presupuestada.** ✅ **Cumplida:** el prototipo de adquisición ya está en PCB definitiva, sin cambios planeados por ahora (registrado 2026-10-07) |
| D10 | STOI y PESQ **requieren señal de referencia limpia**; SNR puede estimarse sin ella | p. 11 | Condiciona el diseño experimental: para C1/C2 hace falta grabar/sintetizar con referencia limpia disponible |

### 2.6 Presupuesto comprometido

$6,500 MXN: hardware ($2,000), ajustes ($500), PCB ($1,000), base de datos ($2,000), evaluación en entornos reales ($1,000).

---

## 3. FLUJO ESPERADO — el orden de construcción

### 3.1 Cadena de bloques del protocolo (Fig. 2)

```
Adaptación del modelo (detección vibracional del escorpión)
        ↓
Diseño del arreglo multimicrófono
        ↓
Adquisición y acondicionamiento de señales de audio
        ↓
Recopilación de la base de datos (habla, ruido, habla+ruido)
        ↓
        ├──► Clasificación de señales (habla vs ruido)
        └──► Estimación de la dirección de la fuente sonora (DOA)
                        ↓
              Aplicación de técnicas de beamforming
                        ↓
              Integración del sistema de procesamiento
                        ↓
              Generación de señal de salida mejorada
                        ↓
      Evaluación del sistema (PESQ, STOI, mejora de SNR)
```

### 3.2 Dependencias duras

Lo que **bloquea** a qué. Violar este orden produce trabajo que hay que rehacer:

```
Obj 1 (geometría real medida) ──┐
                                 ├──► Obj 5 (DOA + beamforming) ──┐
Obj 2 (dispositivo) [CERRADO] ───┘                                 │
                                                                   ├──► Obj 6 ──► Obj 7 ──► Obj 8
Obj 3 (base de datos) ──► Obj 4 (clasificador habla/ruido) ────────┘
```

> **Cuello de botella actual: `geometria.json` con medidas reales (Obj. 1).**
> Sin coordenadas físicas verdaderas, los retardos del DAS son ficticios y **nada aguas abajo es confiable**: ni la estimación de DOA, ni el beamforming, ni las métricas del Obj. 8. Es una tarea barata (medir con calibrador y registrar $d_1$–$d_4$) que desbloquea la parte más cara del proyecto. **Debe hacerse antes de integrar el DAS al pipeline o de reportar cualquier resultado con hardware.**
>
> *Aclaración (2026-10-07):* el desarrollo del DAS **en simulación** (`Exploration/beamforming_algorithms/`) no viola esta regla. Ahí la geometría es un parámetro, así que el algoritmo se verifica contra resultados analíticos con cualquier geometría y la medida real entra después cambiando solo el `.json`. Además sirve para elegir la geometría (Obj. 1) antes de fijarla físicamente. Lo que **sigue bloqueado** por el Obj. 1 es llevar el DAS a `monitor_8LR.py` y medir con hardware.

### 3.3 Correspondencia con el Gantt (Tabla 2 del protocolo)

| Fase | # | Meta | Semanas | Objetivo |
|:--|:--:|:--|:--:|:--:|
| **TT1** | 1 | Diseño del dispositivo de adquisición | 3 | 2 |
| | 2 | Selección e integración de hardware | 1 | 2 |
| | 3 | Prototipado del dispositivo | 3 | 2 |
| | 4 | Ajustes al dispositivo | 1 | 2 |
| | 5 | **Implementación del sistema de adquisición a PCB** | 3 | 2 |
| | 6 | **Recopilación de la base de datos** | **10** | 3 |
| | 7 | Preprocesamiento de señales de audio | 2 | 3 |
| | 8 | **Implementación del módulo de localización acústica** | **15** | 5 |
| | 9 | Redacción TT1 | 15 | — |
| **TT2** | 10 | Clasificación de voz y ruido | 3 | 4 |
| | 11 | Refinamiento de localización acústica | 1 | 5 |
| | 12 | Integración del sistema completo | 3 | 6 |
| | 13 | Generación de señal de salida mejorada | 2 | 6 |
| | 14 | Evaluación en entornos controlados | 1 | 8 |
| | 15 | Ajuste en entornos controlados | 1 | — |
| | 16 | Evaluación en entornos reales | 1 | 8 |
| | 17 | Ajuste en entornos reales | 1 | — |
| | 18 | Redacción TT2 | 15 | — |

**Observaciones sobre el calendario:**

- Las dos metas largas de TT1 son **base de datos (10 sem)** y **módulo de localización (15 sem)**, y corren en paralelo con la redacción. Son el verdadero contenido de TT1.
- **El Obj. 7 (comparación contra arreglo lineal uniforme) no tiene fila propia en el Gantt.** Presumiblemente vive dentro de las metas 14–17, pero conviene decidirlo explícitamente para que no se quede sin tiempo asignado — es un objetivo comprometido y es la mitad de la hipótesis (C3).
- La meta 5 (PCB) ya está cumplida — ver D9.

### 3.4 Dónde estamos (actualizar conforme avance)

| Obj. | Estado | Detalle |
|:--:|:--|:--|
| 1 | 🟡 **Parcial** | Estructura de 4 pares LR definida (pines, buses, nomenclatura PCB). `geometria.json` con **placeholders**; faltan las mediciones físicas reales $d_1$–$d_4$. **Verificar además que la geometría real sea no lineal (D1)**. Los mics están montados en **bases movibles**, así que la geometría se puede reconfigurar para cada prueba sin reimprimir nada. La **forma final (collar) sigue pendiente**. Las geometrías candidatas ya se pueden comparar en simulación (`Exploration/beamforming_algorithms/`) antes de fijarla |
| 2 | 🟢 **Cerrado** | Electrónica en **PCB definitiva** (meta 5 / D9 cumplida; sin cambios planeados por ahora): una PCB para los dos ESP32-S3 y una PCB acondicionada por micrófono, unidas por cables. La forma final del arreglo (collar) es parte del Obj. 1. Adquisición de 8 mics validada end-to-end en PC y Raspberry Pi 4/5, SYNC estable, 0 underruns |
| 3 | 🔴 **No iniciado** | Meta más larga de TT1 (10 sem) + $2,000. Requiere sonómetro (D6) y las dos estrategias (D7) |
| 4 | 🔴 **No iniciado** | Bloqueado por Obj. 3 |
| 5 | 🟡 **En simulación** (desde 2026-10-07) | DAS con retardos fraccionarios, DOA por SRP y TDOA por GCC-PHAT implementados y verificados contra resultados analíticos en 4 geometrías (`Exploration/beamforming_algorithms/`). Falta: ruido direccional, pesos diferenciados (D2), versión en tiempo real por frames. Integración en `hilo_sincronizador` (`Avances/monitor_8LR.py`, frame `(512, 8)`) **bloqueada por Obj. 1** |
| 6 | 🔴 **No iniciado** | Bloqueado por 4 y 5 |
| 7 | 🔴 **No iniciado** | Requiere una segunda variante de `geometria.json` (lineal uniforme) y reconfiguración física del arreglo (D3), que las bases movibles de los mics facilitan. El baseline ya existe en simulación (`ula_2cm`), donde se ve su ambigüedad frente/espalda |
| 8 | 🔴 **No iniciado** | Bloqueado por 7 |

---

## 4. EXTENSIONES — más allá del compromiso

> Todo en esta sección es **opcional**. Se trabaja solo sobre compromiso ya cerrado (§0). Su valor es reforzar la defensa del TT, no ampliarlo.

### 4.1 Beck et al. (2016) como referencia externa

**Cita** (siguiente número disponible tras [33] del protocolo):

> [34] C. Beck, G. Garreau, y J. Georgiou, "Sound Source Localization through 8 MEMS Microphones Array Using a Sand-Scorpion-Inspired Spiking Neural Network", *Frontiers in Neuroscience*, vol. 10, p. 479, 2016, doi: 10.3389/fnins.2016.00479.

**Estado de verificación:** ✅ Cita y cifras verificadas contra el artículo original (open access, PMC5081358) el **2026-09-14**. Todos los valores de la tabla siguiente son textuales del artículo.

**Por qué importa.** Es el trabajo biomimético de escorpión **más cercano al nuestro en la parte de localización**: también 8 micrófonos, también inspirado en el escorpión, también localización acústica. Pero difiere en tres ejes que preservan nuestra originalidad:

| Eje | Beck et al. (2016) | Nuestro TT |
|:--|:--|:--|
| Geometría | Circular **simétrica**, 8 MEMS **equiespaciados**, PCB de **90 mm** de diámetro | **No uniforme y no lineal**, 4 pares LR con $d_1$–$d_4$ diferenciadas y pesos diferenciados |
| Procesamiento | Red neuronal pulsante (SNN) derivada de la anatomía neuronal del escorpión de arena | *Beamforming* (DAS ponderado) sobre geometría no uniforme + estimación de DOA |
| Alcance | **Solo localiza.** No hace mejora del habla ni reporta PESQ/STOI | Localización **y** mejora de inteligibilidad del habla (PESQ, STOI, SNR) |
| Régimen de ruido | Ruido ambiental incidental, **sin caracterizar** | SNR de entrada **caracterizada**, −5 a 10 dB |

> ⚠️ **Implicación para la redacción (importante).** El protocolo afirma en el Estado del Arte que los desarrollos biomiméticos de escorpión *"se limitan al análisis de vibraciones de medios sólidos, dejando poco explorada la aplicación en el campo acústico"*. Beck et al. es un **contraejemplo directo** a esa frase: es escorpión **y** acústico. Al incorporarlo hay que **reformular esa afirmación con más precisión** (p. ej.: la aplicación acústica existe pero se ha abordado con modelos neuronales sobre geometrías simétricas, sin integrar mejora de inteligibilidad del habla ni evaluación en SNR adversa caracterizada). **Nuestra novedad sobrevive intacta** — pero solo si la frase se ajusta. Dejarla como está la vuelve atacable en la defensa.

#### Cifras de referencia (todas: fuente única, tono senoidal continuo 1 kHz, a 1 m, fuente rotando 0°–360° en 20 s, estimación cada 500 ms)

| Referencia | Error angular | Nota |
|:--|:--|:--|
| Escorpión en la naturaleza (Brownell & Farley, 1979) | **13°** | "Piso" biológico compartido con nuestro trabajo |
| Beck, promedio de 15 grabaciones | **9.6° ± 7.6°** | Cifra agregada honesta — la que hay que citar como su desempeño típico |
| Beck, ejemplo sin optimizar (Fig. 9) | **6.34° ± 4.36°** | Caso individual |
| Beck, mejor caso (periodo refractario 15%, Fig. 10) | **4.05° ± 3.01°** | Su mejor resultado |
| van Schaik & Shamma (cóclea neuromórfica, 2 mics) | **~4.5°** | Benchmark externo que Beck cita |
| Unidades ASU (CMOS VLSI dedicado) | **~1°** | Techo de desempeño que Beck cita |

> **Pendiente de paridad:** documentar **nuestra apertura** (diámetro efectivo del arreglo y separaciones $d_1$–$d_4$) para poder comparar *a igualdad de apertura* y no solo a igualdad de número de micrófonos. Beck: 90 mm. La apertura determina la resolución angular alcanzable — comparar sin ella sería engañoso en cualquier dirección.

#### Matriz de pruebas

> **Corrección importante respecto al borrador original de esta matriz:** el barrido de SNR adverso **no es una extensión** — es el núcleo comprometido del TT (Objetivos 7 y 8, criterios C1–C4). Aquí figura como **P0** y encabeza la lista. Clasificarlo como "extensión propia" invertiría las prioridades del proyecto.

| # | Tipo | Prueba | Condiciones | Métrica | Comparación | Qué demuestra |
|:--:|:--:|:--|:--|:--|:--|:--|
| **P0** | 🔴 **COMPROMISO** (Obj. 7, 8) | **Barrido de SNR adverso** | Habla real, ≥1 fuente de ruido simultánea, SNR de entrada −5 a 10 dB | **PESQ, STOI, mejora de SNR** | Nuestro arreglo lineal uniforme + DAS convencional, mismo hardware, idénticas condiciones | **La hipótesis completa** (C1, C2, C3). Sin esto el TT no cumple. Beck **no** probó SNR adversa: comparar contra él aquí sería injusto e inválido |
| P1 | 🟢 Extensión | **Localización en régimen limpio** | Fuente única, tono continuo 1 kHz, ~1 m, plano horizontal, fuente móvil 0°–360°, estimación cada ~500 ms | Error angular medio ± desv. est. | Beck: 4°–10° esperado. Escala: ~1° (VLSI) → 4.5° (neuromórfico) → 13° (naturaleza) | Que nuestra geometría no uniforme localiza tan bien o mejor que un arreglo circular simétrico **en el caso trivial, antes de meter ruido**. Valida el Obj. 5 de forma desacoplada del pipeline de habla |
| P2 | 🟢 Extensión | **Comparación limpia de geometría** (control interno) | Idénticas a P1, **mismo procesamiento en ambas geometrías** | Error angular medio ± desv. est. | Nuestro arreglo lineal uniforme + DAS | Aísla el efecto de **la geometría** sin confundirlo con el método. Es el control más limpio que existe para atribuir mérito a la no uniformidad — más limpio que comparar contra Beck |
| P3 | 🟢 Extensión | **Robustez ante fuente discontinua** | Fuente con pausas (conteo/habla con silencios ~1 s), replicando su escenario de Fig. 11 | Estabilidad de la estimación durante y después de la pausa; error angular si es calculable | Beck **no pudo** estimar de forma fiable aquí — es su modo de fallo documentado y declarado por los autores | Resultado de robustez fuerte: ¿aguantamos donde su SNN se rompe? Especialmente relevante porque **el habla real es intrínsecamente discontinua**, así que esto no es un caso exótico sino nuestro caso de uso |

> **P3 es la prueba estrella.** Beck declara explícitamente que su sistema *"funciona mejor con estímulos continuos"* y que con una persona hablando *"no fue posible calcular de forma fiable la posición"*. Nuestro objeto de estudio **es** habla, que tiene pausas por construcción. Si nuestro sistema sostiene la estimación donde el suyo falla, es un argumento de robustez directamente alineado con el propósito del TT — y sale casi gratis una vez que P1 esté montada.

#### Confusores a controlar (para no engañarnos)

- **Geometría** (circular simétrica de Beck vs. nuestra no uniforme): es *la variable que queremos probar*. Está bien que difiera — pero todo lo demás debe mantenerse igual para poder atribuirle la diferencia.
- **Procesamiento** (SNN de Beck vs. nuestro beamforming): **confusor incómodo**. Si comparamos nuestra-geometría + beamforming contra su-geometría + SNN, no sabremos si la diferencia vino de la geometría o del método. Por eso **P2 es el control correcto** para acreditar el mérito de la geometría: mismo procesamiento, dos geometrías.
- **Régimen de SNR**: Beck tuvo ruido ambiental incidental pero **sin caracterizar**. La única comparación válida con Beck es en **régimen limpio** (P1, P3). El barrido de SNR (P0) es territorio propio, no un empate con Beck.
- **Apertura del arreglo**: 90 mm en Beck. Si nuestra apertura es muy distinta, parte de cualquier diferencia de error angular es geometría de apertura, no bioinspiración.

#### Pendientes accionables de esta extensión

- [ ] Añadir Beck et al. (2016) a la bibliografía como [34].
- [ ] Añadir Beck et al. a la **Tabla 1** comparativa del protocolo, con sus columnas: mejora SNR = **no**; mejora de inteligibilidad del habla = **no**; localiza la fuente = **sí** (error 9.6° ± 7.6°); solución biomimética = **sí** (SNN, escorpión de arena).
- [ ] **Reformular la afirmación del Estado del Arte** sobre la escasa exploración acústica de lo biomimético-escorpión (ver advertencia arriba) — es el cambio de redacción de mayor impacto de esta sección.
- [ ] Documentar apertura de nuestro arreglo (diámetro efectivo y $d_1$–$d_4$) para comparación a igualdad de apertura.
- [ ] Definir el protocolo experimental de P1 (tono 1 kHz, fuente móvil) como prueba de localización desacoplada del pipeline de habla.
- [ ] Diseñar P3 replicando el escenario de pausas de Beck (Fig. 11).
- [ ] Asegurar que P2 use el **mismo** procesamiento en ambas geometrías.

---

## 5. Riesgos conocidos

| # | Riesgo | Mitigación |
|:--:|:--|:--|
| R1 | `geometria.json` sigue con placeholders y todo el DAS depende de él | Medir y registrar $d_1$–$d_4$ **antes** de integrar el beamforming al pipeline o reportar resultados con hardware (§3.2) |
| R2 | La geometría real podría quedar colineal, contradiciendo D1 | Verificar explícitamente que el arreglo sea 2D no lineal al medirlo |
| R3 | Obj. 7 sin tiempo asignado en el Gantt | Decidir en qué meta vive (§3.3) |
| R4 | Base de datos (10 sem, $2,000) es la meta larga de TT1 y no ha iniciado | Es la ruta crítica de TT1 junto con el módulo de localización |
| R5 | PCB tratada como opcional en `Documentation.md` cuando está comprometida | ✅ Cerrado: la PCB ya está implementada (D9) y `Documentation.md` §13 lo refleja (2026-10-07) |
| R6 | Beck et al. contradice una frase del Estado del Arte | Reformular antes de entregar (§4.1) |
| R7 | Reportar mejora de PESQ/STOI sin la señal de referencia limpia | Diseñar el experimento con referencia disponible desde el inicio (D10) |
| R8 | **Deriva de reloj entre las dos ESP32-S3**: el SYNC alinea solo el arranque y cada placa muestrea con su propio cristal, así que el desfase entre M1–M4 y M5–M8 puede crecer con el tiempo y desalinear el DAS (sin medir aún) | Medirla **antes de integrar el DAS**: grabar un pulso o chirp largo y seguir con GCC-PHAT el TDOA entre un mic de cada placa. Si la pendiente no es despreciable, se necesita resincronización periódica o compensación en software (ver `Exploration/beamforming_algorithms/README.md` §10) |

---

## 6. Mantenimiento de este documento

- Se actualiza cuando **cambia el estado de un objetivo** (§3.4) o cuando se descubre un compromiso implícito del protocolo que no estaba registrado (§2.5).
- Al cambiar §3.4, actualizar también la tabla resumen de `README.md` §3 (la tabla de aquí es la autoritativa).
- **No** se usa como bitácora técnica: eso va en `Avances/Documentation.md`, y los cambios de código en `CHANGELOG.md`.
- Si el protocolo se modifica ante la academia, este archivo se reconcilia contra la nueva versión del PDF y se anota el cambio aquí.
