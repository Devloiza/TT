# Changelog

Todos los cambios notables de este proyecto se documentan en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/),
y este proyecto sigue [Versionamiento Semántico](https://semver.org/lang/es/).

## [Unreleased]

### Fixed
- **Desalineamiento periódico (~0.2 % de frames, cada ~16 s).** No era "esperado".
  - Una placa estaba flasheada con `USB CDC On Boot = Disabled`, así que `Serial` (audio) salía por la UART (CH343) junto con la línea de depuración que el firmware imprime cada 500 frames.
  - Ahora el audio se lee por el **USB nativo** (VID `303A`). Los puertos por defecto de `monitor_8LR.py` pasan a `COM7`/`COM5`.
  - Cero realineamientos aun con `DEBUG true`.
  - La conclusión de 0.1.0 de que "`Serial` y `Serial0` comparten la UART" queda corregida (`Documentation.md` §2.1).

### Added
- Protección contra la configuración incorrecta:
  - `esp32_8micLR.txt` no compila si `USB CDC On Boot`, `USB Mode` o la versión del core no son las correctas.
  - `monitor_8LR.py` rechaza puertos cuyo VID no sea el USB nativo (`303A`).
- Capacidad del transporte por USB nativo medida con `transport_check.py`: hasta 512 kB/s en una placa y 256 kB/s por placa con las dos en paralelo, sin pérdidas durante el stream.

## [0.2.0] - 2026-09-07

Sistema base validado también en **Raspberry Pi 4/5**, no solo en PC/Windows — corriendo los 8 micrófonos + SYNC + audio en vivo de forma estable. En el camino se encontró y corrigió un bug de fondo en la sincronización que también podía afectar a Windows, solo que se manifestaba con más frecuencia en la Pi.

### Added
- Soporte para correr `monitor_8LR.py` en Raspberry Pi: puertos configurables vía variables de entorno `ESP1_PORT`/`ESP2_PORT` (antes hardcodeados a valores de Windows). Documentado el proceso completo de despliegue (SSH, grupos `dialout`/`audio`, venv, audio) en `Avances/Documentation.md` sección 12.
- `SKIP_AUDIO=1` para desactivar PyAudio/reproducción por completo (diagnóstico de contención de CPU).
- `AUDIO_DEVICE_INDEX` + `listar_audio.py` para forzar el dispositivo de salida de audio por índice, en vez de depender de un "default" de ALSA/PipeWire que puede no estar bien enrutado.
- Contador de bytes recibidos por placa y tasa real (B/s) en las estadísticas periódicas, para diagnosticar pérdida de datos vs. corrupción.

### Fixed
- Corregido un LED con orden de color real RGB (no GRB) en una de las placas — el firmware ahora declara `NEO_RGB` en el constructor de `Adafruit_NeoPixel`.
- Corregido bug de falsos positivos en la sincronización por bits de canal: al ser solo 2 bits (4 valores), 4 muestras de audio real podían calzar por azar con el patrón esperado y producir una "sincronización"/realineamiento incorrectos, desatando cascadas de desalineamiento que solo se resolvían reiniciando el script. Ahora se exige que el patrón se cumpla en 3 grupos consecutivos (`N_VERIF_SYNC`) antes de aceptarlo.
- **Bug de raíz más grave**: la búsqueda de realineamiento solo reagrupaba bytes en pares fijos (0-1, 2-3...), por lo que nunca podía recuperar un desalineamiento de un número **impar** de bytes (posible con la pérdida/inserción de un solo byte en el transporte) — causaba que "No se pudo realinear" se repitiera frame tras frame de forma persistente. Confirmado con datos reales de una corrida en Raspberry Pi. Ahora la búsqueda prueba ambas paridades de byte.
- Optimizada la búsqueda de alineamiento: vectorizada con numpy (`sliding_window_view`) en vez de un loop de Python por offset candidato — en Raspberry Pi ese loop era lo bastante lento como para retrasar la lectura serial y causar aún más desalineamiento.
- Salida de audio en Raspberry Pi: el jack 3.5mm integrado tiene un control de mezcla específico (`PCM`/`Headphone`) que puede quedar muteado aunque el volumen "general" esté alto; documentado el fix. Para mejor calidad se usa un adaptador USB-C de audio en vez del códec integrado (más ruidoso por ser PWM, no un DAC real).

### Changed
- `.gitignore` generalizado a `venv-*/` (antes `venv-laptop/` específico) para cubrir cualquier entorno virtual por máquina.

## [0.1.0] - 2026-09-06

Primer hito estable: el sistema **base** de adquisición (8 micrófonos, 2×
ESP32-S3 sincronizados) funciona de extremo a extremo. Aún no es el sistema
completo del TT — falta DAS, estimación de DOA, clasificación habla/ruido,
etc. (ver `Avances/Documentation.md`, sección Pendientes).

### Added
- Sistema base de adquisición de audio con 8 micrófonos (2× ESP32-S3
  sincronizados) funcionando de forma estable end-to-end.
- Reconstrucción del firmware y del monitor de Python por etapas
  incrementales (transporte puro → 1 mic real → 4 mics → sistema completo
  con SYNC), cada una con su propia prueba de verificación. Archivos de las
  etapas 1a/1b/2 en `Exploration/reconstruccion_sept2026/`.
- Herramientas de diagnóstico de transporte serie: `diag_raw_dump.py`,
  `transport_check.py`.
- Indicador visual distinto en el LED del Slave para diferenciar SYNC
  recibido vs timeout (antes ambos casos se veían iguales).
- Carpeta `SALIDAS/` como destino único de todos los resultados generados
  (grabaciones `.npy`, gráficas, etc.), no versionada — `monitor_8LR.py` y
  `analisis.py` actualizados para usarla.

### Fixed
- Causa raíz de ~1 mes de fallas de sincronización: `Serial` y `Serial0`
  comparten el mismo periférico UART físico en el ESP32-S3 usado — el baud
  debe coincidir exactamente entre firmware y Python (antes se asumía,
  incorrectamente, que el baud no importaba para USB CDC nativo). Corregido
  a 3,000,000 baud en ambos lados.
- Colores de LED intercambiados (Slave mostraba verde en vez de rojo;
  confirmación de SYNC del Master mostraba rojo en vez de verde) por mal
  entendimiento del orden de parámetros de `Adafruit_NeoPixel::Color()`.
- Bug del paquete de placas `esp32` (Espressif) v3.3.10 que rompía el canal
  USB nativo en modo "Hardware CDC and JTAG" para ESP32-S3 — corregido
  actualizando a 3.3.11+.
- Error de subida por selección incorrecta de Board en Arduino IDE (esptool
  detectaba ESP32-S3 pero se pedía flashear como ESP32 genérico).

### Changed
- `Avances/esp32_8micLR.txt` y `Avances/monitor_8LR.py` reemplazados por las
  versiones reconstruidas y validadas (antes nunca lograban sincronizar de
  forma estable).
- `Avances/Documentation.md` corregido y ampliado: se retiró el supuesto
  erróneo sobre el baud de USB CDC, se documentó el patrón de
  desalineamiento conocido (~0.2%, autocorregido), y se agregó el registro
  completo de la reconstrucción por etapas.

### Removed
- Versiones previas de `esp32_8micLR.txt` y `monitor_8LR.py` que nunca
  lograban sincronización estable (recuperables desde el historial de git).
