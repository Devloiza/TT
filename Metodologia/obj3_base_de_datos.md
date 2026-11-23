# Obj. 3: Diseño de la adquisición de la base de datos

> **Objetivo específico 3** ([`CONTEXTO.md` §2.3](../CONTEXTO.md#23-objetivos-específicos-textual-del-protocolo)): recopilar una base de datos de señales de habla, ruido y habla combinada con ruido.

**Estado:** diseño de la adquisición, todavía sin grabaciones. Este documento registra **cómo** se va a adquirir la base y las decisiones del autor, con su fecha. El guion de sesión y el formato de metadatos se derivan de aquí.

**Autoría:** el diseño y todas las decisiones son de los autores. Claude propuso opciones y criterios (detalle en [`REGISTRO_IA.md`](../REGISTRO_IA.md)).

---

## 1. Compromisos del protocolo que este diseño atiende

| Compromiso | Qué pide | Cómo se atiende |
|:--|:--|:--|
| Obj. 3 | Habla, ruido y habla con ruido | Las tres secciones de este documento (§4, §5 y §6) |
| D7 (p. 7) | Dos estrategias complementarias: mezclas sintéticas de **bases públicas** y grabaciones propias **con el dispositivo** | Grabaciones propias (fuente con micrófono profesional, re-grabación con el arreglo) más bases públicas para completar categorías de ruido |
| D6 (pp. 7–8) | SNR con sonómetro, por dos mediciones consecutivas (ruido solo y con habla); es una estimación aproximada | §6, subconjunto simultáneo |
| D8 (p. 8) | Al menos una fuente de ruido activa simultánea a la de habla | §6, dos monitores sonando a la vez |
| D10 (p. 11) | STOI y PESQ requieren referencia limpia | La voz se graba limpia y por separado del ruido; se mezcla después |
| C4 | SNR de entrada de −5 a 10 dB | Rejilla de evaluación: −5, 0, 5 y 10 dB |
| C5, C6 y Obj. 7 | Mismo número de micrófonos e idénticas condiciones de entrada | El arreglo lineal se graba solo en la evaluación, en la misma sesión y sala (§6) |
| p. 8 | La base se usa para entrenar el clasificador habla/ruido y para la localización | Partición en §3.3 y etiquetas en §4.4 |

## 2. Equipo y lugares

| Elemento | Elección (2026-11-21) | Ajustes |
|:--|:--|:--|
| Micrófono para la voz y los ruidos fuente | Audio-Technica AT2020 (condensador, cardioide, 20 Hz–20 kHz) | Alimentación fantasma de +48 V desde la interfaz, filtro antipop, de 15 a 20 cm de la boca |
| Interfaz | Behringer UMC202HD (hasta 192 kHz y 24 bits) | Se graba a **48 kHz y 24 bits**. Se baja a **16 kHz** al procesar y se conserva el original. Ganancia fija por sesión, con picos cerca de −12 dBFS |
| Sonómetro | TS-501B, ponderaciones A y C | Siempre en **dB(A)**. Las lecturas son estimaciones aproximadas: no es un instrumento de clase 1 (D6) |
| Reproducción | Dos monitores Edifier MR5 (izquierdo y derecho) | **Siempre por cable** (XLR, TRS o RCA), nunca por Bluetooth, y con la ecualización de la app desactivada |
| Adquisición con el dispositivo | El arreglo de 8 micrófonos a 16 kHz (`Avances/monitor_8LR.py`) | Puertos nativos y `USB CDC On Boot = Enabled` (`Avances/Documentation.md` §2.1) |
| Lugar principal | Cubículo de la escuela acondicionado | Medir largo, ancho y alto. Estimar la reverberación con un aplauso grabado |
| Lugar alterno para la voz | Interior de un auto **estacionado en un lugar tranquilo y con el motor apagado**, para quien no pueda ir a la escuela | **Sin limpiador de ruido comercial**, porque deja artefactos en la referencia. Se anota el lugar en los metadatos |
| Re-grabaciones con monitores | Siempre en el cubículo | El arreglo va sobre una **base giratoria** con marcas cada 22.5° |

## 3. Participantes, ética y partición

### 3.1 Participantes

- **Total:** 50 personas, mitad hombres y mitad mujeres.
- **Grupos de edad:** niños (5–12), adolescentes (13–17), adultos jóvenes (18–30), adultos (31–59) y adultos mayores (60+). No es obligatorio que tengan el mismo tamaño, porque niños y adultos mayores son los más difíciles de conseguir. La edad mínima está por definir.
- **Variante del idioma:** solo español de México. Extenderlo a otros acentos e idiomas queda como trabajo a futuro.
- **Niños:** hacen la sesión corta (§4.2). Si no se consiguen suficientes, quedan como trabajo a futuro; el protocolo no exige grupos de edad.

### 3.2 Consentimiento y datos personales

- **Consentimiento firmado:**
  - autorización para uso interno;
  - una **casilla aparte** para autorizar la publicación en un artículo.
- **Menores:** firma del padre, madre o tutor, más el asentimiento del menor.
- **Identificación:** cada persona tiene un código (P01, P02…). Su nombre no aparece en los archivos.
- **Almacenamiento:** las grabaciones se quedan fuera de git, como las fotos de escorpiones.

### 3.3 Partición (híbrida)

- **10 personas de prueba**, balanceadas por sexo y edad. El modelo no las ve hasta la evaluación final.
- **Validación cruzada de 5 grupos** con las otras 40, para ajustar el modelo.
- **Los ruidos** se separan igual, dentro de cada categoría (§5).
- **Las mezclas de prueba** solo usan voces y ruidos de prueba.

## 4. Voz

### 4.1 Sesión de adolescentes y adultos (20–25 min)

| Bloque | Duración | Contenido |
|:--|:--|:--|
| a. Bienvenida y prueba de nivel | 1–2 min | Consentimiento firmado. Decir el código y una frase para ajustar la ganancia (no se usa) |
| b. Silencio de referencia | 30 s | Ruido de fondo de la sesión. También se anota la lectura del sonómetro |
| c. Frases *Sharvard* adaptadas a México | 6–8 min | **6 listas de 10 frases** (decisión del 2026-11-22). **3 fijas para todos**: las de mayor densidad de sonidos que se confunden con ruido (/s/, /f/, /x/ y /tʃ/). **3 al azar**, asignadas de forma balanceada entre participantes. Antes va **1 lista de calibración** que mide el ritmo de lectura de la persona. Después, un programa en Python avanza solo las frases con ese ritmo más un margen, y estandariza los silencios entre frases y entre listas. Texto adaptado: `Exploration/Prueba_BD/Lists_SHARVARD_MX.txt`. Cambios documentados en `adaptaciones_SHARVARD_MX.csv` |
| d. Lectura continua | 1 min | "El viento norte y el sol" |
| e. Secuencias | 1 min | Contar del 1 al 20 y decir los días de la semana |
| f. Habla libre guiada | 12–13 min | §4.3: imágenes (3 min), estilos guiados (unos 4 min) y plática (5 min), con cada estilo indicado explícitamente |

### 4.2 Sesión corta: niños y no lectores (unos 10 min)

- **Inicio:** bloques a y b de §4.1.
- **Repetición:** 15–20 frases cortas que el conductor dice en voz alta.
- **Secuencias:** contar del 1 al 10.
- **Habla libre:** describir una imagen del mismo conjunto que los adultos y una pregunta sencilla ("¿Qué te gusta jugar?").
- **Criterio:** si la repetición sale mal, se descarta y se conserva la descripción de la imagen.

### 4.3 Habla libre guiada

Las preguntas son accesibles para todos los grupos y no piden datos personales sensibles.

Decisión del 2026-11-22: el bloque tiene tres partes, cada una con tiempo fijo y una barra que lo muestra. El conductor decide cuándo pasar a la siguiente imagen o pregunta.

| Parte | Estilo | Contenido | Duración |
|:--|:--|:--|:--|
| Imágenes | Normal | "Describe esta imagen". Escenas con varias personas y objetos, de un conjunto de Pexels (`Exploration/Prueba_BD/image/`, no versionado; fuentes en `fuentes_imagenes.csv`). Salen en **orden balanceado** entre participantes: primero las menos mostradas. Si la persona termina rápido, el conductor pasa a otra; si describe despacio, se queda en una | 3 min |
| Estilos guiados | Fuerte ("como si hablaras con alguien al otro lado del salón"), baja ("como en una biblioteca") y susurro | Las 3 primeras preguntas de `preguntas.txt`, **fijas** (una por estilo), para que todos hagan lo mismo. Si el conductor pasa a otra pregunta, la nueva sale del banco balanceado | 1 min 15 s cada uno |
| Plática | Normal, y el conductor pide otros estilos en medio | Banco de **30 preguntas** de `preguntas.txt` (2026-11-22), de temas variados para que cada persona encuentre alguna que le guste: vida diaria, entretenimiento, viajes y cultura, naturaleza y ciencia, ingeniería y tecnología, y gustos. Salen en **orden balanceado** entre participantes, igual que las imágenes (decisión del 2026-11-22), para que se use todo el banco. El conductor se salta con Espacio la que no funcione. Por ejemplo "Cuéntame qué hiciste el fin de semana", "¿Cuál es tu comida favorita y cómo se prepara?", "Explícame cómo llegar de aquí a la entrada de la escuela" o "¿Cómo se juega tu juego favorito?" | 5 min |

**Sin la voz del conductor en la grabación:** las indicaciones y las preguntas se muestran en pantalla y además suenan **pregrabadas por audífonos cerrados** (decisión del 2026-11-22). El programa anota cuándo suena cada audio, para excluir lo que se filtre al micrófono.

### 4.4 Procesamiento y etiquetas

- **Procesamiento mínimo:** filtro pasa-altas suave (alrededor de 70–80 Hz), recorte de los extremos y normalización.
  - Sin reducción de ruido.
  - Si una grabación queda con ruido de fondo por encima del umbral, se repite.
  - La misma cadena se aplica a todas las grabaciones.
- **Las pausas se conservan** porque son parte del patrón del habla. Se etiquetan en tres clases:
  - **habla activa**;
  - **pausa dentro del habla**;
  - **silencio largo**.

  Así, después se puede decidir si el clasificador trabaja por ventanas cortas o por segmentos de 1–2 s sin volver a etiquetar.
- **Etiquetas adicionales por segmento:** tarea (frases, lectura continua, secuencias, imagen, estilos guiados o plática) y estilo (normal, fuerte, baja o susurro). El programa ya las escribe en `frases.csv` para la parte que presenta.
- **Volumen esperado:** 50 personas × unos 15 min útiles ≈ 12 h de voz limpia.

### 4.5 Programa de presentación (`Exploration/Prueba_BD/presentador_frases.py`)

Hecho por Claude con la especificación del autor (2026-11-22).

- **Flujo:**
  1. **Audio:** se configura una vez por máquina con `configurar_audio.py` (prueba de habla y de escucha) y queda en `config_audio.json`, que no se versiona. El presentador lo lee y no pregunta nada; busca cada dispositivo por nombre y API porque los índices cambian al conectar aparatos, y si alguno no aparece avisa. Sin configuración, la elección se hace en la consola como sigue. **Entrada:** Se elige el dispositivo (solo aparecen los que aceptan 48 kHz y 24 bits) y se hace una prueba de nivel de 3 s por canal. Luego se elige el canal: la UMC202HD es un par estéreo (IN 1-2) y hay que usar la entrada donde está el AT2020. Dispositivo, canal y niveles quedan en `sesion.json`.
  2. Datos de la sesión en la consola.
  3. 30 s de silencio de referencia, con una barra «Silencio» que muestra cuánto falta.
  4. **Calibración** con `calibracion.txt`: 10 frases cotidianas propias, que no son de *Sharvard* y no requieren balance. El conductor presiona Espacio al terminar cada frase y se mide el ritmo en segundos por sílaba.
  5. **6 listas** en orden mezclado por persona: las fijas **15, 33 y 3** más 3 aleatorias balanceadas, elegidas entre las menos usadas en `asignaciones.csv`, con semilla según el código.
  6. **Habla libre guiada** (§4.3): imágenes, estilos guiados y plática, cada parte con su barra de «Tiempo». La consigna va arriba en azul y la imagen o la pregunta abajo. Con Espacio el conductor pasa a la siguiente imagen o pregunta, y en la plática pide otro estilo con **F** (fuerte), **B** (baja), **S** (susurro) o **N** (normal). Una pausa a mitad de una parte la retoma con el tiempo que le quedaba.
- **Audífonos:** en la misma configuración se elige la salida (solo aparecen las que aceptan 48 kHz en estéreo) y se oye un tono de prueba. Con Enter se sigue sin audio y las indicaciones solo se muestran. Cada indicación o pregunta suena si existe `audios_preguntas/<id>.wav` (los ids están en `preguntas.txt`; el audio se remuestrea a 48 kHz si hace falta). Al iniciar, el programa avisa qué audios faltan.
- **Imágenes y preguntas balanceadas:** las mostradas se suman en las columnas `imagenes` y `preguntas` de `asignaciones.csv`, salvo en P00. El orden de cada participante pone primero las menos usadas, con desempate al azar según el código.
- **Avance automático:** cada frase dura sílabas × ritmo × **1.25**, seguida de **2 s** en blanco. Entre listas hay **5 s** de descanso, con una **barra arriba** que dice «Descanso» y se vacía con el tiempo. Su funcionamiento se muestra antes de la calibración, después del silencio y con la misma duración que un descanso real (5 s), para que no se confunda con algo que hay que leer.
- **Datos de la sesión:**
  - **El código se asigna solo** (P01, P02…), para evitar errores.
  - **P00 es el código de prueba:** se guarda igual que las demás sesiones, no se sobrescribe (cada sesión va en su carpeta con fecha y hora) y no cuenta para el balance de listas.
  - Se pide la **edad exacta** y el grupo de edad se deduce de ella.
- **Mientras se lee,** una barra delgada y discreta arriba indica cuántas frases faltan para el siguiente descanso. Es distinta de la barra grande de descanso.
- **Los errores de lectura se conservan,** porque también ocurren en la realidad. Solo se repite una frase en casos extremos, como un ruido externo fuerte e inesperado.
- **Teclas, solo para el conductor:**
  - **P:** pausa de emergencia. La frase interrumpida se repite completa y el evento queda registrado.
  - **R:** repite la frase actual o la que acaba de terminar. La toma anterior queda en `frases.csv` con `repetida = 1`, para descartarla al etiquetar.
  - **M:** marca una frase dudosa.
  - **Esc:** termina la sesión antes.
- **Salida** en `SALIDAS/BD_voz/<código>_<fecha>/` (no se versiona):
  - `audio.wav` a 48 kHz y 24 bits, en una sola toma;
  - `frases.csv` con el inicio y el fin de cada frase, imagen o pregunta en el reloj del audio, con su tarea (`tipo`) y su `estilo`. Las filas `indicacion` son los audios que sonaron por los audífonos. Es la segmentación automática para el etiquetado;
  - `sesion.json` con datos, ritmo, listas, imágenes y preguntas mostradas, entrada y salida de audio (`entrada`, `salida_audifonos`, `audios_faltantes`) y eventos (pausas y cambios de estilo).
- **Uso:** `python Exploration/Prueba_BD/presentador_frases.py`. Opciones: `--listar` (entradas y salidas), `--dispositivo N`, `--salida N`, `--prueba` (recorrido corto automático) y `--sin-audio` (no graba ni reproduce; para probar la pantalla). La UMC202HD aparece varias veces. La que reporta 48 kHz (WASAPI) funcionó en la prueba del 2026-11-22.

## 5. Ruido

- **Dos versiones de cada ruido,** grabadas en el lugar:
  - **fuente**, con el AT2020, para reproducirla después por el monitor;
  - **de dominio**, con el arreglo, para el clasificador.
- **Por cada muestra se mide y se documenta:**
  - el nivel en dB(A) en el lugar;
  - la distancia aproximada a la fuente;
  - el lugar, la hora y la categoría.

  Así queda registrado el sonido original. Para las pruebas, el nivel se ajusta.
- **Duración:** de 2 a 3 min por muestra, para poder sacar tramos distintos al mezclar.
- **Bases públicas** (MUSAN, DEMAND, ESC-50 o WHAM!; licencias por verificar): solo para completar las categorías que no se consigan grabar.
- **Separación:** entrenamiento y prueba dentro de cada categoría (por ejemplo, 80/20).

Se muestrean todas las categorías:

| Categoría | Ejemplos | Meta |
|:--|:--|:--|
| Estacionario | Ventilador, aire acondicionado, refrigerador, motor en marcha | 8–10 |
| Fluctuante | Calle, tráfico, metro, pasillo de la escuela | 8–10 |
| Impulsivo | Puertas, platos, teclado, pasos, objetos que caen | 8–10 |
| Babble y hablante competidor | Cafetería, salón lleno, una persona hablando desde otra dirección | 10–12 (el caso más difícil) |
| Tonal y música | Alarmas, timbres, música con y sin voz | 6–8 |

## 6. Habla con ruido (re-grabación en el cubículo)

**Montaje:**
- El arreglo va sobre la base giratoria, a la altura del tweeter.
- Un monitor reproduce la voz y el otro el ruido.

**Calibración de cada sesión:**
- **Voz:** el monitor se ajusta para que llegue a unos 60–65 dB(A) a 1 m, el nivel de una conversación normal.
- **Ruido:** cada uno a su nivel documentado.

| Elemento | Diseño |
|:--|:--|
| Ángulos | 16, cada 22.5°, **girando el arreglo**. El monitor solo se mueve para cambiar de distancia. La sala no es perfectamente simétrica: se anota como limitación |
| Distancias | 1, 1.5, 2, 2.5 y 3 m |
| Repeticiones | **5 frases distintas por posición**, sin mover nada (repetición de medición). La **repetición de colocación** (5 veces) se hace solo en una muestra de posiciones, por ejemplo 4 ángulos × 2 distancias, para estimar el error de colocar |
| Voz por posición | Un subconjunto fijo de frases comunes, con las de personas de prueba y las de entrenamiento por separado |
| Ruido por posición | En **posiciones fijas** (0°, 90°, 180° y 270°) y **relativas a la voz** (separadas 45°, 90° y 180°). Cada posición se graba una vez por tipo de ruido y se combina al mezclar |
| Mezcla digital | Voz y ruido grabados **por separado**. El SNR se define con las señales grabadas **en el arreglo**. Para entrenar: valores intermedios aleatorios entre −5 y 15 dB. Para evaluar: −5, 0, 5 y 10 dB |
| Simultáneo (D6, D8) | Los dos monitores a la vez en unas 10–20 combinaciones. El SNR se estima con el sonómetro: primero ruido solo y luego ruido con voz |
| Arreglo lineal (Obj. 7) | Solo el subconjunto de evaluación, en la **misma sesión y sala** que el bioinspirado |

**Tiempo estimado:** unas 4 h por geometría para la voz (2–3 min por ángulo), más el ruido y la muestra de repetición de colocación.

## 7. Decisiones del autor

| Fecha | Decisión |
|:--|:--|
| 2026-11-08 | Grabar la fuente con un micrófono de mejor calidad y re-grabar con monitores para controlar distancias y señal. El arreglo lineal se graba solo para la evaluación |
| 2026-11-15 | Partición híbrida. Procesamiento mínimo de la voz. Trabajo a 16 kHz |
| 2026-11-21 | Solo español de México. Cubículo como lugar principal y auto con motor apagado como alterno, sin limpiador de ruido. Equipo de §2. Sesión de 15–30 min con lectura y habla libre en estilos indicados explícitamente. Niños con sesión corta (trabajo a futuro si no se consiguen). Mismas frases para todos (publicadas y propias). Pausas etiquetadas en tres clases. Todas las categorías de ruido, grabadas en el lugar con el AT2020 y con el arreglo, y complementadas con bases públicas. Niveles medidos y documentados. Rejilla cada 22.5° con base giratoria y 5 distancias. Ruido en posiciones fijas y relativas. SNR intermedios para entrenar. Mezcla digital más un subconjunto simultáneo |
| 2026-11-22 | 6 listas *Sharvard* adaptadas por sesión: 15, 33 y 3 fijas, más 3 aleatorias balanceadas, en orden mezclado. Adaptaciones mínimas con sonidos parecidos. Calibración con una lista propia y avance automático a ritmo × 1.25, con 2 s entre frases y 5 s entre listas. Sin repetir frases (los errores se conservan). Pausa y marca controladas solo por el conductor. Habla libre: imágenes de Pexels al azar balanceado durante 3 min (el conductor pasa a la siguiente), estilos guiados y dentro de la plática, plática de 5 min al final, e indicaciones en pantalla y pregrabadas por audífonos para no grabar la voz del conductor |

## 8. Pendientes antes de grabar

- [ ] **Frases comunes:**
  - ~~conseguir el corpus *Sharvard* y su licencia~~: el autor encontró el PDF con las frases (2026-11-21). El dataset está en Edinburgh DataShare con licencia **Creative Commons Attribution 4.0 International**: se puede usar y adaptar citando el artículo y el dataset;
  - elegir listas completas (no frases sueltas, para conservar el balance de cada lista) y anotar cada cambio de vocabulario (original → adaptada);
  - ~~adaptar el vocabulario~~: hecho el 2026-11-22. Son 51 frases en 37 listas, con cambios mínimos y sonidos parecidos (por ejemplo coger → tomar, euro → peso, jersey → suéter, cubo → cubeta). `Lists_SHARVARD.txt` (con las propuestas del autor) se conserva sin cambios;
  - ~~elegir las 3 listas fijas~~: 15, 33 y 3, las de mayor densidad de /s/, /f/, /x/ y /tʃ/, con al menos 3 de cada uno de los últimos tres;
  - ~~especificar el programa de presentación~~: hecho (§4.5);
  - redactar las frases propias y comprobar el balance contando fonemas.
- [ ] **Imágenes para describir:** ~~elegirlas~~: conjunto de Pexels en `Exploration/Prueba_BD/image/` (2026-11-22). ~~Llenar la URL y el fotógrafo en `fuentes_imagenes.csv`~~ (hecho por el autor, 2026-11-22). Falta quedarse con escenas parejas (con personas y objetos).
- [ ] **Preguntas:** ~~completar el banco~~: 30 en `preguntas.txt` (2026-11-22), por revisar por el autor. Falta grabar sus audios y los de las indicaciones en `audios_preguntas/`.
- [ ] **Audífonos cerrados** para el participante, y comprobar que no se filtren al AT2020 al volumen de la sesión.
- [ ] **Lectura continua y secuencias** (bloques d y e de §4.1): todavía no están en el programa.
- [ ] **Consentimiento:** redactar el formato (adultos y menores).
- [ ] **Guion de sesión** escrito, idéntico para los dos conductores.
- [ ] **Metadatos:** definir el formato y la convención de nombres de archivo.
- [ ] **Etiquetado:** elegir la herramienta (habla activa, pausa y silencio largo).
- [ ] **Cubículo:** medirlo y estimar su reverberación. Fijar el umbral de ruido de fondo para aceptar una grabación.
- [ ] **Base giratoria:** construirla con marcas cada 22.5°.
- [ ] **Reproducción en el cubículo:** fijar los niveles de calibración (voz a 1 m y ruidos).
- [ ] **Evaluación:** definir el subconjunto de frases y de ruidos.
- [ ] **Edad mínima** de los niños.

## 9. Referencias por verificar

- V. Aubanel, M. L. García Lecumberri y M. Cooke, "The Sharvard Corpus: A phonemically-balanced Spanish sentence resource for audiology", *International Journal of Audiology*, vol. 53, núm. 9, pp. 633–638, 2014. Licencia del dataset: CC BY 4.0 (verificada por el autor). **Falta verificar la cita contra el artículo y agregar la cita del dataset (Edinburgh DataShare).** Las grabaciones también pueden entrar al bloque de bases públicas (D7)
- "El viento norte y el sol": texto de ejemplo de la Asociación Fonética Internacional para el español. **Ubicar la fuente exacta.**
- Bases de ruido: MUSAN, DEMAND, ESC-50, WHAM! **Verificar las licencias.**
