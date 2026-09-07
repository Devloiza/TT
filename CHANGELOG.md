# Changelog

Todos los cambios notables de este proyecto se documentan en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/),
y este proyecto sigue [Versionamiento Semántico](https://semver.org/lang/es/).

## [Unreleased]

### Added
- Soporte para correr `monitor_8LR.py` en Raspberry Pi: puertos configurables vía variables de entorno `ESP1_PORT`/`ESP2_PORT` (antes hardcodeados a valores de Windows). Documentado el proceso completo de despliegue (SSH, grupos `dialout`/`audio`, venv, audio) en `Avances/Documentation.md` sección 12.

### Fixed
- Corregido un LED con orden de color real RGB (no GRB) en una de las placas — el firmware ahora declara `NEO_RGB` en el constructor de `Adafruit_NeoPixel`.
- Corregido bug de falsos positivos en la sincronización por bits de canal: al ser solo 2 bits (4 valores), 4 muestras de audio real podían calzar por azar con el patrón esperado y producir una "sincronización"/realineamiento incorrectos, desatando cascadas de desalineamiento que solo se resolvían reiniciando el script. Ahora se exige que el patrón se cumpla en 3 grupos consecutivos (`N_VERIF_SYNC`) antes de aceptarlo.

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
