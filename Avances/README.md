# Avances — sistema oficial

Código **validado** del sistema de adquisición. Lo que está aquí es lo que corre en la PC y en la Raspberry Pi; los prototipos viven en [`../Exploration/`](../Exploration/README.md) hasta que se promueven.

La documentación técnica completa (hardware, pines, protocolo serie, hilos, despliegue y bitácora) está en **[`Documentation.md`](Documentation.md)**. Este archivo solo es el índice de la carpeta.

| Archivo | Qué es | Detalle |
|:--|:--|:--|
| [`monitor_8LR.py`](monitor_8LR.py) | Programa principal: lee ambas ESP32-S3, sincroniza y produce frames `(512, 8)` a 16 kHz; reproduce un par de mics y graba a `SALIDAS/`. | [`Documentation.md` §4](Documentation.md#4-arquitectura-python-monitor_8lrpy) |
| [`esp32_8micLR.txt`](esp32_8micLR.txt) | Firmware Arduino Master/Slave (renombrar a `.ino`): 4 mics I2S por placa, ID de canal en los bits [1:0], pulso SYNC, 3 000 000 baud. | [`Documentation.md` §1–3](Documentation.md#1-hardware) |
| [`geometria.json`](geometria.json) | Posiciones $(x, y, z)$ de los 8 mics. **Contiene placeholders**: faltan las medidas reales $d_1$–$d_4$ (Obj. 1). | [`Documentation.md` §5](Documentation.md#5-archivo-geometriajson) |
| [`analisis.py`](analisis.py) | Análisis offline de una grabación `.npy` de `SALIDAS/` (ajustar `ARCHIVO` y `MIC_ACTIVO` en el script). | — |
| [`listar_audio.py`](listar_audio.py) | Lista los dispositivos de salida de PyAudio con su índice, para `AUDIO_DEVICE_INDEX`. | [`Documentation.md` §12.7](Documentation.md#127-audio-de-salida-jack-35mm) |
| [`visualizar.py`](visualizar.py) | Boceto que grafica posiciones de micrófonos con coordenadas de prueba. Para geometrías reales, usar el playground de beamforming. | [`beamforming_algorithms`](../Exploration/beamforming_algorithms/README.md) |

**Punto de extensión pendiente:** el DAS se insertará en `hilo_sincronizador` de `monitor_8LR.py` ([`Documentation.md` §6](Documentation.md#6-punto-de-extensión-das-beamforming)). Antes de eso tiene que cumplir los criterios de promoción del [playground §11](../Exploration/beamforming_algorithms/README.md#11-criterios-para-promover-un-algoritmo-a-avances).
