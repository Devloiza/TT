# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Trabajo Terminal (TT) de Ingeniería Biónica — UPIITA-IPN, proyecto `DTA.MI.2026-2.5BM1.LMP.01`: sistema de localización acústica multimicrófono inspirado en el sensado vibracional de escorpiones, para mejorar la inteligibilidad del habla en entornos ruidosos (hipótesis: ≥10% de mejora en STOI/PESQ y ≥3 dB de SNR frente a un arreglo lineal uniforme con DAS convencional, para SNR de entrada entre −5 y 10 dB).

**Fuente de verdad de alcance:** `CONTEXTO.md` (raíz del repo) es el documento base — destila `PROTOCOLO_TT.pdf` en compromisos verificables, el orden de construcción y sus extensiones. **Leerlo antes de cualquier decisión de alcance.** Jerarquía: `PROTOCOLO_TT.pdf` (institucional, no versionado en git) > `CONTEXTO.md` > `Avances/Documentation.md` (bitácora técnica, describe la implementación, no define alcance) > el código.

Distinción que gobierna las prioridades: lo que está en el protocolo es **compromiso** (no negociable); lo demás es **extensión** y no se trabaja antes de cerrar el compromiso que la contiene. `CONTEXTO.md` §0 y §4.

## Setup y comandos

No hay build system, linter ni suite de tests — es un proyecto de investigación con scripts Python ejecutados directamente.

```bash
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

Ejecutar el sistema completo de adquisición (requiere ambos ESP32-S3 conectados por USB *antes* de arrancar el script):

```bash
python Avances/monitor_8LR.py
```

Puertos serie por variable de entorno (evita hardcodear por máquina; default Windows `COM8`/`COM6`):

```bash
export ESP1_PORT=/dev/ttyACM1   # Linux/Raspberry Pi
export ESP2_PORT=/dev/ttyACM3
```

Otras variables de entorno relevantes de `monitor_8LR.py`: `SKIP_AUDIO=1` (desactiva PyAudio para diagnosticar contención de CPU), `AUDIO_DEVICE_INDEX` (fuerza dispositivo de salida — usar `python Avances/listar_audio.py` para listarlos), `AUTO_CYCLE_SECONDS` (recorre los 4 pares de mics sin teclado, para demos), `debug=true` como argumento (DEBUG está apagado por defecto).

Comandos en tiempo real del monitor: teclas `1`-`4` cambian el par de mics en escucha, `g` graba a `SALIDAS/`, `q` sale.

Análisis offline de una grabación (`SALIDAS/*.npy`): `python Avances/analisis.py` (ajustar `ARCHIVO`/`MIC_ACTIVO` en el propio script).

Resultados generados (grabaciones `.npy`, gráficas) van siempre a `SALIDAS/` — no se versionan (ver `.gitignore`), solo `SALIDAS/README.md` como marcador.

## Arquitectura

### Hardware → firmware → Python

Dos ESP32-S3 (Arduino, `Avances/esp32_8micLR.txt`), Master y Slave, cada uno lee 4 micrófonos I2S ICS-43434 (2 buses × modo estéreo L/R) y transmite por USB CDC (`Serial`) a 3,000,000 baud — valor crítico, debe coincidir *exactamente* entre firmware y Python o hay corrupción de bits. `Serial0` (debug) comparte el mismo periférico UART físico que `Serial` (audio) en este hardware, así que ambos deben abrirse al mismo baud.

Formato del frame por placa: 512 muestras interleaved `[Mic1_s0, Mic2_s0, Mic3_s0, Mic4_s0, Mic1_s1, ...]`, int16, con el **ID de canal codificado en los bits [1:0]** de cada muestra (`0xFFFC` para extraer el audio puro). Esta codificación es lo que permite a Python detectar y corregir desalineamiento del stream.

Al arranque, el Master envía un pulso SYNC (GPIO10, 10 µs) tras 500 ms de espera; el Slave lo espera (timeout 15 s) antes de iniciar I2S, para alinear el muestreo entre ambas placas en hardware.

### Pipeline Python (`Avances/monitor_8LR.py`)

Arquitectura de hilos productor/consumidor con colas `Queue` de tamaño fijo (política drop-oldest si se llenan):

```
hilo_lector ESP1 ─┐
                   ├─► hilo_sincronizador ─► q_combinada (CHUNK, 8) ─► hilo reproductor (PyAudio)
hilo_lector ESP2 ─┘
```

- `hilo_lector` (uno por placa): lee bytes serie, valida el patrón de canal `[0,1,2,3]` en `N_VERIF_SYNC` grupos consecutivos antes de aceptar sincronización/realineamiento (evita falsos positivos — el ID de canal son solo 2 bits), prueba ambas paridades de byte al buscar offset (un desplazamiento de un número impar de bytes es irrecuperable si solo se prueba una paridad), produce frames `(CHUNK, 4)`.
- `hilo_sincronizador`: empareja frames de ambas placas (descarta ambos si uno no llega en 50 ms) y produce el frame combinado `(CHUNK, 8)` — **este es el único punto de extensión para el DAS** (delay-and-sum beamforming), aún no implementado.
- `reproducir`: extrae el par activo del frame de 8 canales y lo manda a PyAudio.
- Normalización: int16 → float32 `[-1.0, 1.0]` (÷32768); canales deshabilitados se fuerzan a `0.0`.

La búsqueda de offset de realineamiento está vectorizada con `numpy.lib.stride_tricks.sliding_window_view` — un loop de Python por offset candidato fue, en el pasado, lo bastante lento en Raspberry Pi como para retrasar la lectura serial y causar más desalineamiento. Cualquier código nuevo en el pipeline en tiempo real debe mantener ese mismo cuidado de vectorización (ver decisión de arquitectura abajo).

### `geometria.json`

Posiciones físicas (x, y, z en metros) de los 8 micrófonos, necesarias para calcular retardos del DAS. Actualmente son placeholders — las mediciones reales del arreglo (separaciones $d_1$-$d_4$ entre pares LR1-LR4) siguen pendientes (ver `Avances/Documentation.md` sección Pendientes).

### Decisión de arquitectura: Python, no Rust

Se evaluó y descartó (por ahora) reescribir partes en Rust. Decisión: quedarse en Python + NumPy/SciPy vectorizado; no optimizar anticipadamente. Razonamiento completo en `Avances/Documentation.md` sección 14.1 — en resumen: los problemas de rendimiento encontrados hasta ahora fueron bugs de loops no vectorizados (no un límite del lenguaje), el DAS y GCC-PHAT/TDOA son computacionalmente triviales para NumPy, hay ~32 ms de presupuesto por frame a `CHUNK=512`/16 kHz, y la evaluación de métricas (PESQ/STOI/SNR) es offline sin presión de tiempo real. No reabrir esta decisión sin evidencia de un cuello de botella medido.

### `Exploration/`

Prototipos y herramientas de diagnóstico, incluyendo `reconstruccion_sept2026/` (reconstrucción incremental por etapas del sistema completo — transporte puro → 1 mic → 4 mics — usada como referencia histórica y para depurar problemas de transporte futuros). No es código de producción del TT.

## Notas operativas importantes

- Conectar siempre ambos ESP32 por USB *antes* de correr `monitor_8LR.py`.
- Un desalineamiento ocasional autocorregido (~0.2% de frames, log `Realineado offset=...`) es esperado y no indica un bug — coincide con los prints periódicos de debug del firmware compartiendo el mismo UART que el audio.
- Si aparecen muchos `WARN Desalineamiento`, sospechar primero de un baud desalineado entre firmware y Python antes que de pérdida de bytes por USB.
- En Raspberry Pi: el usuario necesita los grupos `dialout` (puertos serie) y `audio`; cada ESP32-S3 en modo Hardware CDC and JTAG expone dos `/dev/ttyACM*` (usar el de grupo `dialout`, no `plugdev`).
