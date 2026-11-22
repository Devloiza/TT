# Exploration — prototipos y herramientas

Nada en esta carpeta es código de producción. Aquí se prototipa, se diagnostica y se conserva la historia del desarrollo. Lo que funciona y pasa sus verificaciones se **promueve** a [`../Avances/`](../Avances/README.md).

| Carpeta | Estado | Para qué sirve | Documentación |
|:--|:--|:--|:--|
| [`reconstruccion_sept2026/`](reconstruccion_sept2026/) | 📦 Histórico, con herramientas vigentes | Reconstrucción por etapas del sistema de adquisición (transporte puro → 1 mic → 4 mics) que llevó a `v0.1.0`. `transport_check.py` y `diag_raw_dump.py` siguen siendo útiles para depurar problemas de transporte serie. | [`Documentation.md` §10](../Avances/Documentation.md#10-reconstrucción-por-etapas-sept-2026) |
| [`Geometria_estadistica/`](Geometria_estadistica/) | 🟡 En curso (autor) | Recopilación de fuentes e imágenes de especies de escorpiones con *slit sensilla*, de varios géneros y centradas en *Heterometrus*, para hacer estadística sobre las imágenes, como apoyo al Obj. 1 (geometría del arreglo inspirada en las *slit sensilla*). El índice de especies de `Fuentes.md` se completa conforme avanza la recopilación. `patainador.py` es la herramienta para marcar en cada foto el eje del cuerpo, las patas por pares (P1–P4, zona del basitarso) y el círculo; guarda `datos/imagenes.csv` y `datos/puntos.csv` (versionados). Las fotos van en `fotos/<orientación>/`, solo en local. La estadística es del autor (`estadistica_imagenes.py`). `estadistica_error.py` (del autor) dibuja histogramas de D, l/D, (D−l)/D, r/D y la resolución a partir de ese CSV, así que hay que correr antes el exportador. `exportar_error_proyeccion.py` exporta a `SALIDAS/Escorpiones_estadistica/` el CSV del error de proyección del centro sobre el eje, con una figura por foto procesable (foto sola y foto anotada, lado a lado). `graficas_patas.py` dibuja una figura por modo (pares y espejo) en `SALIDAS/`: mapa de calor con el IC 95 % y esquema del escorpión con los valores medios. | [`Metodologia/obj1_geometria.md`](../Metodologia/obj1_geometria.md); [`Fuentes.md`](Geometria_estadistica/Fuentes.md); uso y teclas en el encabezado de [`patainador.py`](Geometria_estadistica/patainador.py) |
| [`Prueba_BD/`](Prueba_BD/) | 🟡 En curso | Preparación de la adquisición de voz del Obj. 3. Contiene las listas *Sharvard* (`Lists_SHARVARD.txt`, con las propuestas del autor), su adaptación a México (`Lists_SHARVARD_MX.txt` y `adaptaciones_SHARVARD_MX.csv`), la lista de calibración (`calibracion.txt`) y `presentador_frases.py`, el programa de sesión hecho por Claude con la especificación del autor. Las grabaciones van a `SALIDAS/BD_voz/`, que no se versiona. | [`Metodologia/obj3_base_de_datos.md`](../Metodologia/obj3_base_de_datos.md) §4 (programa: §4.5) |
| [`Primeros_intentos/`](Primeros_intentos/) | 📦 Histórico | Primeros prototipos de 1, 2 y 4 micrófonos, previos a la reconstrucción. Superados por `Avances/`. | Esta página |

## `Primeros_intentos/`

Se conservan como referencia. **Pueden no funcionar tal cual con el hardware actual**: usan baudios distintos (460 800 o 921 600, contra 3 000 000 del firmware oficial), pines del ESP32-WROOM y versiones previas del protocolo de canal.

| Archivo | Qué era |
|:--|:--|
| `esp32_mic.txt` | Firmware de 1 micrófono (ESP32-WROOM, 921 600 baud). |
| `esp32_micLR.txt` | Firmware de 2 micrófonos en el bus I2S 0 del ESP32-S3 (L/R). |
| `esp32_4micLR.txt` | Firmware de 4 micrófonos con ID de canal en los bits [1:0]; antecesor de `esp32_8micLR.txt`. |
| `monitor.py`, `monitor_LR.py`, `monitor_4LR.py` | Monitores de 1, 2 y 4 micrófonos; antecesores de `monitor_8LR.py`. |
| `inmp441_audio.py`, `inmp144.py` | Captura de 1 micrófono INMP441 a WAV (16 kHz y 8 kHz). |
| `Pruebas.py` | Captura con filtrado en frecuencia (usa `filtros_fourier.py`; importa como paquete, correr desde la raíz del repo). |
| `filtros_fourier.py` | Máscaras de filtros pasa-bajos, pasa-altos, pasa-banda y notch en el dominio de Fourier. |
| `Pruebas2.py` | Explorador de 2 micrófonos: forma de onda, FFT, DAS básico y ángulo estimado en tiempo real. Es el primer intento de beamforming. |
