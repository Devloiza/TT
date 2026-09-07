# Documentación del Sistema de Adquisición — TT

## Contexto general

Este documento sirve como referencia técnica y bitácora de progreso para el Trabajo Terminal:

> **"Sistema de localización acústica multimicrófono basado en mecanismos de detección vibracional de escorpiones para la mejora de la inteligibilidad del habla en entornos acústicamente adversos"**
> UPIITA-IPN — Ingeniería Biónica — Semestre 2026/2
> Proyecto: `DTA.MI.2026-2.5BM1.LMP.01`

El sistema de adquisición está compuesto por **dos ESP32-S3** conectados vía USB a una PC con Python. Cada ESP captura 4 micrófonos ICS-43434 mediante dos buses I2S y transmite los datos en un formato interleaved por USB CDC. Python recibe ambos flujos, los sincroniza y los combina en frames de 8 canales listos para DAS (Delay-and-Sum beamforming).

---

## 1. Hardware

### 1.1 Asignación de pines ESP32-S3

Los **dos ESP32-S3 comparten el mismo esquema de pines** (el firmware diferencia Master/Slave solo por la constante `IS_MASTER`).

| GPIO | Bus I2S | Función    | Micrófono(s)       |
|:----:|:-------:|:----------:|:------------------:|
| 4    | Bus 0   | WS (LRCLK) | Mic 1 + Mic 2      |
| 5    | Bus 0   | SCK (BCLK) | Mic 1 + Mic 2      |
| 6    | Bus 0   | SD (DATA)  | Mic 1 + Mic 2      |
| 11   | Bus 1   | WS (LRCLK) | Mic 3 + Mic 4      |
| 12   | Bus 1   | SCK (BCLK) | Mic 3 + Mic 4      |
| 13   | Bus 1   | SD (DATA)  | Mic 3 + Mic 4      |
| 10   | —       | SYNC       | Master→Slave       |
| 38   | —       | NeoPixel   | LED RGB (WS2812)   |

> **Nota:** El pin SYNC (GPIO10) es **salida en el Master** y **entrada en el Slave**. Solo se usa durante el arranque para alinear el inicio de los dos flujos I2S.

### 1.2 Conexión de micrófonos ICS-43434 (I2S)

Cada bus I2S soporta dos micrófonos en modo estéreo usando el pin L/R:

| Micrófono | Bus | L/R pin | Canal I2S |
|:---------:|:---:|:-------:|:---------:|
| Mic 1     | 0   | GND     | Left      |
| Mic 2     | 0   | VCC     | Right     |
| Mic 3     | 1   | GND     | Left      |
| Mic 4     | 1   | VCC     | Right     |

> **Nota:** El mismo esquema aplica en ambas placas. En ESP1 los micrófonos son Mic1–Mic4; en ESP2 son Mic5–Mic8 (Python los distingue por puerto COM, no por el firmware).

### 1.3 Identificación visual de placas (LED RGB)

Durante los primeros 5 segundos del arranque el LED indica el rol:

| Color  | Rol    | Puerto COM (ejemplo) |
|:------:|:------:|:--------------------:|
| Azul   | Master | COM8                 |
| Rojo   | Slave  | COM6                 |
| Verde  | —      | Parpadeo al recibir/enviar pulso SYNC |

> **Nota sobre el orden de color:** el LED de esta placa física está cableado en orden **RGB real, no GRB** (a pesar de ser un WS2812/NeoPixel "genérico") — se confirmó porque con `NEO_GRB` declarado en el firmware, rojo y verde salían intercambiados. El firmware ya declara `NEO_RGB` en el constructor de `Adafruit_NeoPixel`, así que los colores de esta tabla son los que deberías ver en la placa. Si vuelves a ver rojo/verde invertidos tras algún cambio, revisa que esa declaración siga en `NEO_RGB`.

> Los puertos COM se deben ajustar en `monitor_8LR.py` según el equipo de desarrollo. Ver sección 4.

### 1.4 Configuración Arduino IDE

| Parámetro       | Valor                         |
|:---------------:|:-----------------------------:|
| Board           | ESP32S3 Dev Module            |
| USB CDC On Boot | Enabled                       |
| USB Mode        | Hardware CDC and JTAG         |
| Flash Size      | 16MB (128Mb)                  |
| PSRAM           | OPI PSRAM                     |

> **Importante:** `USB CDC On Boot: Enabled` es obligatorio. Sin esto el ESP no aparece como puerto COM al conectarse.

---

## 2. Protocolo de comunicación ESP32 a Python

### 2.1 Transporte

> **CORRECCIÓN (sept 2026):** Este documento asumía que la transmisión iba por **USB CDC nativo** y que el baud era ignorado por el driver USB. Se comprobó experimentalmente (Etapa 1a de reconstrucción, ver sección 10) que **eso es falso en este hardware**: `Serial` y `Serial0` terminan compartiendo el mismo periférico UART físico, con un reloj real. Si el baud pedido por Python no coincide EXACTAMENTE con el baud de `Serial.begin()`/`Serial0.begin()` en el firmware, se produce corrupción de bits (patrón característico: solo aparecen valores como `0x00`/`0x80`, nunca basura aleatoria completa) o, si el baud es demasiado bajo, un cuello de botella real en la tasa de datos.
>
> **Valor validado y usado en todo el proyecto desde sept 2026: `3,000,000` baud**, en firmware (`Serial.begin(3000000)` y `Serial0.begin(3000000)`) y en Python (`serial.Serial(puerto, 3000000, ...)`) a la vez. Ver `Avances/transport_check.py` para la prueba de integridad que lo comprobó.

La transmisión de audio se realiza por `Serial` en el firmware de Arduino. El debug del firmware (mensajes de texto) sale por `Serial0`. **Ambos deben abrirse al mismo baud** (3,000,000) tanto en el firmware como del lado de Python — no asumir que el baud "no importa".

### 2.2 Formato del frame de audio

Cada iteración del `loop()` del firmware genera un **frame** de 512 muestras por canal. La estructura del buffer que se envía por USB es:

```
Frame = CHUNK_SAMPLES × 4 canales × 2 bytes = 512 × 4 × 2 = 4096 bytes
```

El buffer está organizado como muestras **int16 interleaved** en el orden:

```
[Mic1_s0, Mic2_s0, Mic3_s0, Mic4_s0,  Mic1_s1, Mic2_s1, Mic3_s1, Mic4_s1, ...]
```

donde `s0`, `s1`... son las muestras consecutivas en el tiempo.

### 2.3 Codificación de canal en los bits bajos

Cada muestra int16 lleva el **ID de canal codificado en los bits [1:0]**:

| Bits [1:0] | Canal | Posición en frame |
|:----------:|:-----:|:-----------------:|
| `00` (0)   | Mic 1 | Bus0-Left         |
| `01` (1)   | Mic 2 | Bus0-Right        |
| `10` (2)   | Mic 3 | Bus1-Left         |
| `11` (3)   | Mic 4 | Bus1-Right        |

La máscara `0xFFFC` limpia los dos bits bajos para recuperar el audio puro. Python aplica esta máscara con `np.int16(-4)`.

**¿Por qué esta codificación?**
Permite detectar desalineamiento del stream: si los primeros 4 valores del frame no tienen IDs `[0, 1, 2, 3]` en ese orden, el frame está corrido y Python lo realinea buscando el patrón correcto.

### 2.4 Proceso de obtención del dato de audio en el firmware

```
I2S RX (32 bits) → shift right 16 bits → int16 → AND 0xFFFC → OR ID_MIC
```

Los micrófonos ICS-43434 entregan datos justificados a la izquierda en 32 bits. Al hacer `>> 16` se obtienen los 16 bits más significativos como un int16. Los 2 bits menos significativos del resultado se usan para inyectar el ID de canal.

---

## 3. Sincronización hardware entre ESP32s

### 3.1 Pulso SYNC al arranque

Al iniciar, el Master espera 500 ms para que el Slave esté listo y luego envía un pulso de 10 µs en GPIO10. El Slave espera ese pulso (timeout 15 s) antes de comenzar a leer el I2S. Esto alinea el inicio del muestreo en ambas placas.

```
Master:                   Slave:
  delay(500ms)              wait for SYNC pulse
  SYNC_PIN → HIGH           (timeout 15s)
  delay(10µs)
  SYNC_PIN → LOW
  → inicia I2S              → inicia I2S
```

### 3.2 Sincronización de frames en Python (software)

Python alinea los frames de los dos ESP en el **hilo sincronizador** (`hilo_sincronizador`). Si uno de los dos ESP no entrega un frame en 50 ms, ambos se descartan para evitar desfase acumulativo. Este es el punto de extensión donde se implementará el DAS.

---

## 4. Arquitectura Python (`monitor_8LR.py`)

### 4.1 Parámetros configurables

| Constante       | Valor por defecto | Descripción                          |
|:---------------:|:-----------------:|:------------------------------------:|
| `ESP1_PORT`     | `"COM8"`          | Puerto del Master (Mics 1-4). Se puede sobreescribir con la variable de entorno `ESP1_PORT` (ej. `/dev/ttyACM1` en Linux/Raspberry Pi) sin tocar el código — ver sección 12. |
| `ESP2_PORT`     | `"COM6"`          | Puerto del Slave (Mics 5-8). Igual, sobreescribible con `ESP2_PORT`. |
| `ESP_BAUD`      | `3000000`         | Baud del puerto serial — **debe coincidir exactamente** con `Serial.begin()`/`Serial0.begin()` del firmware (ver sección 2.1) |
| `ESP_RATE`      | `16000`           | Frecuencia de muestreo en Hz         |
| `CHUNK`         | `512`             | Muestras por frame por canal         |
| `ESP1_MICS`     | `[True]*4`        | Habilitar/deshabilitar Mics 1-4      |
| `ESP2_MICS`     | `[True]*4`        | Habilitar/deshabilitar Mics 5-8      |
| `PAR_ACTIVO`    | `0`               | Par estéreo a reproducir (0–3)       |
| `GEOMETRIA_FILE`| `"geometria.json"`| Archivo de posiciones de micrófonos  |
| `DEBUG`         | `True`            | Imprime mensajes de diagnóstico      |

### 4.2 Pares de micrófonos disponibles para escuchar

| Índice | Descripción               | Columnas en frame 8ch |
|:------:|:-------------------------:|:---------------------:|
| 0      | Mic1+Mic2  ESP1 Bus0      | cols 0, 1             |
| 1      | Mic3+Mic4  ESP1 Bus1      | cols 2, 3             |
| 2      | Mic5+Mic6  ESP2 Bus0      | cols 4, 5             |
| 3      | Mic7+Mic8  ESP2 Bus1      | cols 6, 7             |

### 4.3 Arquitectura de hilos (PRUEBAS)

```
Hilo lector ESP1 ➡️
                    ➡️ Hilo sincronizador ➡️ q_combinada (CHUNK, 8)
Hilo lector ESP2 ➡️                                     ⬇️
                                                  Hilo reproductor
                                                (escucha par activo)
                                                         ⬇️        
                                             Hilo estadísticas (cada 5 s)
                                            Hilo teclado (comandos 1–4, q)
```

| Hilo               | Función                                                    |
|:------------------:|:----------------------------------------------------------:|
| `hilo_lector`      | Lee bytes del puerto serial, valida alineamiento, produce frames (CHUNK, 4) |
| `hilo_sincronizador` | Empareja frames ESP1+ESP2, produce frames (CHUNK, 8) para DAS |
| `reproducir`       | Toma frames 8ch, extrae par activo, escribe a PyAudio      |
| `stats`            | Imprime contadores de OK/ERR/drops/underruns cada 5 s      |
| `escuchar_teclado` | Cambia `PAR_ACTIVO` con teclas 1–4, cierra con q           |

### 4.4 Colas y flujo de datos

| Cola          | Tipo                       | Tamaño máx | Productor          | Consumidor           |
|:-------------:|:--------------------------:|:----------:|:------------------:|:--------------------:|
| `q_esp1`      | `np.ndarray` (CHUNK, 4)    | 8 frames   | hilo_lector ESP1   | hilo_sincronizador   |
| `q_esp2`      | `np.ndarray` (CHUNK, 4)    | 8 frames   | hilo_lector ESP2   | hilo_sincronizador   |
| `q_combinada` | `np.ndarray` (CHUNK, 8)    | 8 frames   | hilo_sincronizador | hilo reproductor     |

> Si una cola está llena, se descarta el frame más antiguo (política drop-oldest) para mantener latencia baja.

### 4.5 Proceso de sincronización inicial del stream

Al arrancar, Python busca en el stream el **patrón de sincronización** `[0, 1, 2, 3]` en los bits [1:0] de 4 muestras consecutivas. Esto garantiza que los frames de audio empiecen en el offset correcto antes de entrar al bucle de lectura. Timeout: 30 s.

> **Robustez del patrón (sept 2026):** el ID de canal son solo 2 bits (4 valores posibles), así que 4 muestras de audio real pueden calzar con `[0,1,2,3]` **por pura casualidad** (~1/256 por intento) y producir un falso positivo de sincronización — el código quedaba "sincronizado" en un punto que en realidad no era el inicio real de un grupo de canales, y como el error no se detecta hasta el siguiente grupo, esto podía desatar una cascada de desalineamientos consecutivos con offsets erráticos (visto tanto en Windows como, más raramente, en Raspberry Pi — y confirmado porque simplemente reiniciar el script de Python, sin tocar las placas, lo resolvía). **Fix:** tanto `sincronizar()` como el realineamiento en `hilo_lector()` ahora exigen que el patrón se cumpla en **`N_VERIF_SYNC` (3) grupos de 4 muestras consecutivos** antes de aceptarlo (constante ajustable), bajando la probabilidad de falso positivo a ~1/16.7 millones.

### 4.6 Normalización de audio

Las muestras int16 se convierten a float32 normalizado `[-1.0, 1.0]` dividiendo entre 32768. Los canales deshabilitados en `ESP1_MICS`/`ESP2_MICS` se fuerzan a `0.0`.

### 4.7 Dependencias Python

```
pip install pyserial pyaudio numpy
```

### 4.8 Comandos en tiempo de ejecución

| Tecla | Acción                         |
|:-----:|:------------------------------:|
| `1`   | Escuchar Mic1+Mic2 (ESP1 Bus0) |
| `2`   | Escuchar Mic3+Mic4 (ESP1 Bus1) |
| `3`   | Escuchar Mic5+Mic6 (ESP2 Bus0) |
| `4`   | Escuchar Mic7+Mic8 (ESP2 Bus1) |
| `q`   | Salir                          |

---

## 5. Archivo `geometria.json`

Este archivo define las posiciones físicas de los 8 micrófonos en el espacio (collar/arreglo). Es necesario para implementar el **DAS (Delay-and-Sum beamforming)** ya que los retardos de compensación dependen de las distancias reales entre micrófonos.

### 5.1 Estructura esperada

```json
{
  "velocidad_sonido": 343,
  "micrófonos": [
    { "id": 1, "x": 0.0, "y": 0.0, "z": 0.0 },
    { "id": 2, "x": 0.0, "y": 0.0, "z": 0.0 },
    ...
    { "id": 8, "x": 0.0, "y": 0.0, "z": 0.0 }
  ]
}
```

> **TODO:** Completar con las mediciones físicas reales del arreglo (separaciones d1–d4 entre pares LR1–LR4 según la geometría inspirada en el escorpión).

### 5.2 Correspondencia micrófonos–pares del arreglo

| ID Mic | Par LR | ESP   | Bus I2S | Canal I2S | Nomenclatura en PCB |
|:------:|:------:|:-----:|:-------:|:---------:| :-: |
| 1      | LR1-L  | ESP1  | Bus 0   | Left      | L2 |
| 2      | LR1-R  | ESP1  | Bus 0   | Right     | L1 |
| 3      | LR2-L  | ESP1  | Bus 1   | Left      | L4 |
| 4      | LR2-R  | ESP1  | Bus 1   | Right     | L3 |
| 5      | LR3-L  | ESP2  | Bus 0   | Left      | R2 |
| 6      | LR3-R  | ESP2  | Bus 0   | Right     | R1 |
| 7      | LR4-L  | ESP2  | Bus 1   | Left      | R4 |
| 8      | LR4-R  | ESP2  | Bus 1   | Right     | R3 |

---

## 6. Punto de extensión: DAS Beamforming

El `hilo_sincronizador` en `monitor_8LR.py` es el **único punto donde se insertará el DAS**. El frame combinado `frame_8ch` de shape `(512, 8)` ya contiene las 8 señales sincronizadas y normalizadas.

```python
# Esquema futuro dentro de hilo_sincronizador:
frame_8ch = np.concatenate([f1, f2], axis=1)   # (512, 8) — ya disponible

# TODO: Implementar aquí
retardos = calcular_retardos(geometria, angulo_doa)   # retardos en muestras
salida   = delay_and_sum(frame_8ch, retardos)          # (512,) señal enfocada
```

Los retardos en muestras para cada micrófono `n` hacia una DOA se calculan como:

```
τ_n = round( (d_n · cos(θ)) / (v_sonido / Fs) )
```

donde `d_n` es la distancia del micrófono al origen del arreglo proyectada en la dirección θ, `v_sonido = 343 m/s` y `Fs = 16000 Hz`.

---

## 7. Notas importantes

- **Orden de arranque:** Primero conectar ambos ESP32 a USB, luego ejecutar el script Python. Si se conectan después de iniciar Python, los puertos COM pueden no estar disponibles o los buffers estarán llenos.
- **Puertos COM:** Los valores `COM8` (ESP1/Master) y `COM6` (ESP2/Slave) son específicos del equipo de desarrollo. Verificar con el Administrador de dispositivos de Windows cada vez que se conecten las placas.
- **LED:** Si el LED no enciende en los primeros segundos, verificar que la librería `Adafruit_NeoPixel` esté instalada en el Arduino IDE y que GPIO38 sea el correcto para la placa usada.
- **Timeout SYNC:** El Slave tiene un timeout de 15 s esperando el pulso SYNC del Master. Si se supera, arranca sin sincronización (los flujos de ambos ESP pueden estar desfasados hasta ~500 ms).
- **USB CDC On Boot:** Si `USB CDC On Boot` está deshabilitado, el ESP no aparecerá como puerto COM al conectarse vía USB. Solo será visible si se conecta mientras se mantiene presionado el botón de Boot.
- **UART0 vs USB:** `Serial0` es para debug del firmware, `Serial` para audio — pero en este hardware **ambos comparten el mismo periférico físico**, así que deben abrirse al mismo baud (ver sección 2.1). No asumir que son transportes independientes.
- **Baud rate — causa raíz histórica:** durante ~1 mes el sistema no lograba sincronizar por tener `ESP_BAUD=115200` (techo real ~11,520 B/s) cuando el sistema necesita ~128,000 B/s por placa (4 mics) — insuficiente por un factor de >10x. Subir el baud en Python sin subirlo también en el firmware empeoraba las cosas (corrupción de bits, no solo lentitud). Ambos lados deben coincidir exactamente. Ver sección 10.
- **Patrón de desalineamiento conocido y aceptado:** con el baud corregido (3,000,000) puede aparecer un desalineamiento ocasional (~1 cada 400-500 frames) que se autocorrige (`Realineado offset=...`) sin underruns. Coincide en tiempo con los prints periódicos de debug (`DBG_FMT` cada 500 frames) que comparten el mismo UART que el audio — sospecha: el print introduce un pequeño estanco que desfasa una muestra. No se ha considerado necesario eliminarlo (tasa de error ~0.2%, sin pérdida de audio real), pero si se busca cero errores, bajar la frecuencia del debug o quitarlo en producción.
- **Latencia:** Con `CHUNK=512` y `Fs=16000`, la latencia teórica por frame es `512/16000 ≈ 32 ms`. Con 8 frames en cola el buffer máximo es `~256 ms`.
- **Descarte de frames:** Cuando las colas se llenan se descarta el frame más antiguo. Underruns frecuentes (`stats_data["underruns"]`) indican que el procesamiento no lleva el ritmo del audio. Bajar `CHUNK` puede ayudar a latencia a costa de más overhead.
- **Alineamiento de frames:** Si se ven muchos `WARN Desalineamiento` en consola, primero verificar que el baud coincida entre firmware y Python (causa más común, ver arriba) antes de sospechar de pérdida de bytes por USB.
- **Carpeta `SALIDAS/`:** todo resultado generado (grabaciones `.npy`, gráficas, etc.) debe guardarse en `SALIDAS/` (raíz del repo), no en `Avances/` ni en la raíz del proyecto. No se versiona su contenido (ver `.gitignore`) — solo `SALIDAS/README.md` como marcador. `monitor_8LR.py` (comando `g`) y `analisis.py` ya apuntan ahí.

---

## 8. Estadísticas en tiempo de ejecución

El hilo de estadísticas imprime cada 5 segundos:

```
[STATS]
  Par activo   : 0 — Mic1+Mic2  ESP1 Bus0  pines 4/5/6
  Colas        : ESP1=N  ESP2=N  Combinada=N
  Sync OK/Drop : X  /  Y
  Underruns    : Z
  ESP1         : OK=A  ERR=B  Realign=C
  ESP2         : OK=A  ERR=B  Realign=C
```

| Contador      | Descripción                                              |
|:-------------:|:--------------------------------------------------------:|
| `sync_ok`     | Frames combinados correctamente de ambos ESP             |
| `sync_drop`   | Frames descartados por timeout de sincronización (>50 ms)|
| `underruns`   | Veces que el reproductor no encontró datos en 100 ms     |
| `espX_ok`     | Frames válidos recibidos del ESPX                        |
| `espX_err`    | Frames con desalineamiento detectado                     |
| `espX_realign`| Frames donde se encontró y corrigió el desalineamiento   |

---

## 9. Diagrama de flujo de datos (resumen)

```
[ICS-43434 x4]──I2S──[ESP32-S3 Master]──USB CDC➡️
                                                 ➡️[Python: hilo_sincronizador]──► frame(512,8)
[ICS-43434 x4]──I2S──[ESP32-S3 Slave ]──USB CDC➡️                   
                                                                    ⬇️
                                                        [TODO: DAS Beamforming]
                                                                    ⬇️
                                                        [PyAudio → salida estéreo]
```

---

## 10. Reconstrucción por etapas (sept 2026)

Tras ~1 mes sin lograr sincronización estable, se decidió abandonar el debugging directo sobre el sistema completo y reconstruir subiendo la complejidad en etapas controladas, cada una con su propia prueba de verificación. Las Etapas 1a, 1b y 2 fueron construcción incremental y ya cumplieron su propósito; sus archivos se movieron a `Exploration/reconstruccion_sept2026/` como referencia histórica. La Etapa 3 (el sistema completo) quedó **promovida a los nombres oficiales del proyecto**: `esp32_8micLR.txt` y `monitor_8LR.py`. Las versiones previas de esos dos archivos (que nunca lograron sincronizar de forma estable) se eliminaron — recuperables desde el historial de git si hiciera falta revisar el intento anterior.

| Etapa | Objetivo | Archivos (ahora en `Exploration/reconstruccion_sept2026/`, salvo Etapa 3) | Resultado |
|:-----:|:---------|:---------|:----------|
| 1a | Transporte USB puro (sin I2S) a la tasa real objetivo (~32,000 B/s) | `esp32_stage1a_transport.txt`, `transport_check.py` | **OK** a 921,600 / 2,000,000 / 3,000,000 baud (coincidiendo firmware↔Python). Reveló la causa raíz del baud (sección 2.1). |
| 1b | I2S real, 1 micrófono, 1 bus | `esp32_stage1b_1mic.txt`, `stage1b_record_plot.py` | **OK** — tasa correcta, señal real (aplausos visibles en la gráfica) |
| 2 | 4 micrófonos, ambos buses I2S, 1 sola placa (sin SYNC) | `esp32_stage2_4mic.txt`, `monitor_stage2_4mic.py` | **OK** — 0 underruns, ~0.2% de frames con desalineamiento autocorregido (ver nota en sección 7) |
| 3 | Dos placas + SYNC (el sistema completo) | **`Avances/esp32_8micLR.txt`, `Avances/monitor_8LR.py`** (nombres oficiales) | **OK** — SYNC inmediato (0 intentos) en ambas placas, 0 underruns, ~0.2% de frames con desalineamiento autocorregido, correlacionado en ambas placas a la vez (mismo patrón de la sección 7) |

Herramientas de diagnóstico creadas en el camino, en `Exploration/reconstruccion_sept2026/` (quedan disponibles para depurar problemas futuros de transporte):

- **`diag_raw_dump.py`**: vuelca bytes crudos de un puerto sin ningún parseo — útil para confirmar a simple vista qué canal (`Serial` vs `Serial0`) le está llegando realmente a un COM dado. El firmware `esp32_stage1a_transport.txt` tiene un bloque `#define DIAG_MODE` que manda un ping distinguible por cada canal (portar ese bloque si se necesita repetir el diagnóstico sobre `esp32_8micLR.txt`).
- **`transport_check.py`**: verifica integridad de transporte con un contador incremental uint16 (detecta pérdidas/duplicados/corrupción de forma más rigurosa que enviar audio real, porque el contenido esperado es exacto).

### Otros bugs encontrados y corregidos durante la reconstrucción (no relacionados al baud)

1. **Colores de LED intercambiados** en la versión anterior de `esp32_8micLR.txt`: el Slave se identificaba con verde en vez de rojo, y el parpadeo de "SYNC enviado" del Master salía rojo en vez de verde. `Adafruit_NeoPixel::Color(r,g,b)` siempre recibe los parámetros en orden RGB — la librería reordena internamente según `NEO_GRB`, no hay que invertir los argumentos a mano. Ya corregido en la versión actual.
2. **Bug de observabilidad en el Slave**: el LED de confirmación de SYNC parpadeaba igual (verde) tanto si el pulso llegaba como si había timeout tras 15s — imposible distinguir a simple vista. Se agregó una señal distinta (3 parpadeos rojos) para el caso de timeout (ya en la versión actual).
3. **Bug del core `esp32` v3.3.10**: esa versión del paquete de Espressif rompía el canal USB nativo en modo `Hardware CDC and JTAG` para S3 (aunque `USB CDC On Boot` estuviera Enabled). Corregido actualizando a 3.3.11+.
4. **Selección de Board incorrecta en Arduino IDE**: causaba error de esptool (`This chip is ESP32-S3, not ESP32`). Cambiar Tools → Board a "ESP32S3 Dev Module" resetea TODOS los submenús (USB CDC On Boot, Flash Size, PSRAM, etc.) a sus valores por defecto — hay que re-verificarlos después de cada cambio de Board.

---

## 11. Avances

<!-- Registrar aquí los avances, cambios y observaciones del desarrollo -->

| Fecha      | Descripción del avance | Archivos involucrados |
|:----------:|:----------------------:|:---------------------:|
| _25/06/2026_ | _Creación y definición de los protocolos de comunicación y pruebas con los micrófonos._         | _monitor_8LR.py, esp32_8micLR.txt y Documentation.md_             |
| _06/09/2026_ | _Tras 1 mes sin lograr SYNC, se depuró el error de esptool (Board mal seleccionado), 2 bugs de color de LED, y un bug del core esp32 v3.3.10 que rompía USB nativo en S3. Se decidió reconstruir el sistema por etapas en vez de seguir depurando el sistema completo._ | _esp32_8micLR.txt (ahora esp32_8micLR_OLD.txt), diag_raw_dump.py_ |
| _06/09/2026_ | _Encontrada la causa raíz real: `Serial`/`Serial0` comparten el mismo periférico UART físico en este hardware — el baud debe coincidir exactamente entre firmware y Python. Validado a 3,000,000 baud con Etapas 1a (transporte puro), 1b (1 mic real), 2 (4 mics, 1 placa) y 3 (sistema completo, 2 placas + SYNC) — todas OK. Ver sección 10._ | _esp32_stage1a/1b/2/3, transport_check.py, stage1b_record_plot.py, monitor_stage2/3.py_ |
| _06/09/2026_ | _Cerrado el ciclo de reconstrucción: Etapa 3 promovida a los nombres oficiales `esp32_8micLR.txt`/`monitor_8LR.py`; archivos de las Etapas 1a/1b/2 movidos a `Exploration/reconstruccion_sept2026/`; versiones previas (nunca sincronizaban de forma estable) eliminadas del árbol de trabajo._ | _esp32_8micLR.txt, monitor_8LR.py, Exploration/reconstruccion_sept2026/*_ |
| _06/09/2026_ | _Primer despliegue funcional en Raspberry Pi 4/5: acceso SSH, grupos `dialout`/`audio`, transporte validado a 3,000,000 baud en ambas placas simultáneamente, sistema completo (8 mics + SYNC) corriendo y con audio de salida funcionando. Se corrigió además un bug real de falsos positivos de sincronización (patrón de 2 bits calzando por azar), exigiendo 3 grupos consecutivos (`N_VERIF_SYNC`) para aceptar sync/realineamiento._ | _monitor_8LR.py, Documentation.md_ |
<!-- | _dd/mm/aa_ | _descripción_         | _archivo_             | # FORMATO -->

---

## 12. Despliegue en Raspberry Pi (sept 2026)

El objetivo a mediano plazo es correr el sistema en una Raspberry Pi (4/5) en vez de una PC/laptop, para tener un equipo dedicado y portátil. Validado: **transporte limpio a 3,000,000 baud en ambas placas, simultáneamente**, usando `transport_check.py` desde `Exploration/reconstruccion_sept2026/` — de hecho el driver `cdc_acm` de Linux resultó más confiable a esa tasa que el de una laptop con Windows (ver nota de la sección 7 sobre robustez de baud por host).

### 12.1 Acceso remoto (SSH)

1. En la Pi: `sudo raspi-config` → *Interface Options* → *SSH* → Enable (o `sudo systemctl enable ssh --now`).
2. Conectar la Pi a la misma red (WiFi vía `raspi-config` → *System Options* → *Wireless LAN*, o Ethernet).
3. Encontrar su IP: `hostname -I` en la propia Pi, o `ping raspberrypi.local` desde la PC.
4. Desde Windows (PowerShell trae cliente SSH integrado): `ssh <usuario>@<ip>`.
5. Los nombres de usuario en Linux deben ir en **minúsculas** (`adduser` rechaza mayúsculas por el `NAME_REGEX` por defecto).
6. Recomendado: extensión **Remote-SSH** de VS Code para navegar archivos/editar/terminal integrados.

### 12.2 Permisos de grupo (causa más común de "Permission denied")

Linux restringe el acceso a hardware por grupo — un usuario nuevo (creado con `sudo adduser`) no trae estos grupos por defecto, a diferencia del usuario que se configura durante el flasheo inicial con Raspberry Pi Imager:

| Grupo | Para qué | Comando |
|:-----:|:---------|:--------|
| `dialout` | Acceso a puertos serie (`/dev/ttyACM*`, `/dev/ttyUSB*`) | `sudo usermod -aG dialout <usuario>` |
| `audio`   | Acceso a dispositivos de audio (`/dev/snd/*`)            | `sudo usermod -aG audio <usuario>`   |
| `sudo`    | Ejecutar comandos administrativos                        | `sudo usermod -aG sudo <usuario>`    |

**Importante:** los cambios de grupo no aplican a una sesión ya abierta — hay que cerrar sesión (`exit`) y volver a conectar por SSH para que tomen efecto. Verificar con `groups` o `id`.

### 12.3 Cada ESP32-S3 expone DOS puertos `/dev/ttyACM*`

En modo `Hardware CDC and JTAG`, el mismo USB expone dos interfaces: una para JTAG/depuración (grupo `plugdev`) y otra para datos (grupo `dialout`, la que usa `Serial` en el firmware). Con dos placas conectadas pueden aparecer como `ttyACM0`–`ttyACM3`. Identificar la correcta con:
```
ls -l /dev/ttyACM*
```
La de grupo `dialout` es la de datos — la de `plugdev` no sirve para este proyecto.

### 12.4 Entorno Python

Raspberry Pi OS (Bookworm+) bloquea `pip install` fuera de un venv (PEP 668, error *externally-managed-environment*):
```
python3 -m venv venv
source venv/bin/activate      # repetir en cada sesión/pestaña nueva de tmux
pip install pyserial numpy pyaudio
```
`pyaudio` necesita la librería de sistema `portaudio19-dev` antes de instalarse: `sudo apt install -y portaudio19-dev`.

### 12.5 Puertos por variable de entorno (evita editar el código por máquina)

`monitor_8LR.py` lee `ESP1_PORT`/`ESP2_PORT` de variables de entorno si existen (default: `COM8`/`COM6` para Windows). En la Pi:
```
export ESP1_PORT=/dev/ttyACM1
export ESP2_PORT=/dev/ttyACM3
```
(Agregar a `~/.bashrc` para no repetirlo cada sesión.) Antes de este cambio, el archivo tenía los puertos de Windows y Raspberry hardcodeados en el mismo bloque — la segunda asignación siempre pisaba a la primera, causando errores de conexión confusos.

### 12.6 Codificación de terminal (UnicodeEncodeError)

Los scripts usan caracteres como `—`, y algunas sesiones SSH usan `latin-1` en vez de `UTF-8`, causando `UnicodeEncodeError` al imprimir. Fix rápido por sesión:
```
export PYTHONIOENCODING=utf-8
```

### 12.7 Audio de salida (jack 3.5mm)

`aplay -l` puede detectar la tarjeta (`bcm2835 Headphones`) sin que realmente suene nada, incluso con el volumen "general" subido en `alsamixer`. La causa fue un **control de mezcla específico** (`PCM` y/o `Headphone`) muteado o en 0, distinto del control "Master":
```
amixer -c 0 scontrols                    # lista los controles reales de la tarjeta 0
amixer -c 0 sset 'PCM' 100% unmute
amixer -c 0 sset 'Headphone' 100% unmute
speaker-test -D hw:0,0 -c2 -t wav        # probar
```
Se intentó también Bluetooth como alternativa; se encontró un conflicto real entre PipeWire y PulseAudio clásico peleando por el mismo adaptador (`RegisterProfile() failed: org.bluez.Error.NotPermitted` — no instalar `pulseaudio`/`pulseaudio-module-bluetooth` si el sistema ya usa PipeWire/WirePlumber nativo), pero no fue necesario resolverlo una vez arreglado el jack analógico.

### 12.8 tmux — sesiones persistentes y en paralelo

Para correr procesos que sobrevivan a una desconexión de SSH (el monitor completo, pruebas de las dos placas a la vez):
```
sudo apt install -y tmux
tmux new -s prueba
# Ctrl+B luego %  → divide en paneles verticales
# Ctrl+B luego flechas → cambia de panel
# Ctrl+B luego D  → se desconecta, deja todo corriendo
tmux attach -t prueba   # para volver a entrar
```

---

## 13. Pendientes

- [x] ~~Decidir si se reemplazan los archivos oficiales~~ — hecho: `esp32_8micLR.txt`/`monitor_8LR.py` ya son la versión reconstruida y validada (Etapa 3). Los archivos de las Etapas 1a/1b/2 se movieron a `Exploration/reconstruccion_sept2026/` y las versiones previas de los archivos oficiales se eliminaron (recuperables vía `git log` si hiciera falta).
- [ ] Probar la función de grabación (`g`) del monitor con los 8 mics conectados y verificar el .npy resultante antes de retomar el trabajo de DAS.
- [ ] Dejar corriendo el sistema completo en la Raspberry Pi por un periodo largo (varios minutos) para confirmar que el fix de falsos positivos de sincronización (sección 4.5/12) realmente elimina las cascadas de desalineamiento intermitentes.
- [ ] Medir y registrar las distancias físicas reales entre micrófonos en el arreglo (d1–d4).
- [ ] Editar `geometria.json` con las coordenadas reales del collar/arreglo.
- [ ] Implementar `calcular_retardos()` y `delay_and_sum()` en `hilo_sincronizador`.
- [ ] Implementar estimación de DOA (TDOA/GCC-PHAT) sobre `q_combinada`.
- [ ] Implementar algoritmo de clasificación habla/ruido.
- [ ] Evaluar con métricas PESQ, STOI y mejora de SNR.
- [ ] ¿Diseñar e implementar PCB definitiva?.
