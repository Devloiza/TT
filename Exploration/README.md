# Exploration — prototipos y herramientas

Nada en esta carpeta es código de producción. Aquí se prototipa, se diagnostica y se conserva la historia del desarrollo. Lo que funciona y pasa sus verificaciones se **promueve** a [`../Avances/`](../Avances/README.md).

| Carpeta | Estado | Para qué sirve | Documentación |
|:--|:--|:--|:--|
| [`beamforming_algorithms/`](beamforming_algorithms/) | 🟢 **Activo** | DAS y DOA en simulación: geometrías candidatas, retardos fraccionarios, SRP, GCC-PHAT y una batería de verificación. Atiende los Obj. 1, 5 y 7. | [`README.md`](beamforming_algorithms/README.md) (teoría, diseño y API) |
| [`reconstruccion_sept2026/`](reconstruccion_sept2026/) | 📦 Histórico, con herramientas vigentes | Reconstrucción por etapas del sistema de adquisición (transporte puro → 1 mic → 4 mics) que llevó a `v0.1.0`. `transport_check.py` y `diag_raw_dump.py` siguen siendo útiles para depurar problemas de transporte serie. | [`Documentation.md` §10](../Avances/Documentation.md#10-reconstrucción-por-etapas-sept-2026) |
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
| `Pruebas2.py` | Explorador de 2 micrófonos: forma de onda, FFT, DAS básico y ángulo estimado en tiempo real. Es el primer intento de beamforming, antes del playground. |
