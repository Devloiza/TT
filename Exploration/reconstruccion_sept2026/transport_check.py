"""
transport_check.py — Etapa 1a: verificación pura de transporte USB.

El firmware esp32_stage1a_transport.txt manda un contador uint16 que sube
de 1 en 1 (con wraparound en 65536) a ~32000 bytes/s. Este script verifica
que no se pierda ni se duplique ni una muestra durante N segundos.

Uso:
    python transport_check.py COM8 [segundos]
"""

import sys
import time
import serial
import numpy as np

if len(sys.argv) < 2:
    print("Uso: python transport_check.py <PUERTO> [segundos]")
    sys.exit(1)

puerto = sys.argv[1]
dur    = float(sys.argv[2]) if len(sys.argv) > 2 else 15.0
baud   = int(sys.argv[3]) if len(sys.argv) > 3 else 3000000

ser = serial.Serial(puerto, baud, timeout=1)
print(f"(abierto a {baud} baud — para USB CDC nativo no debería importar, "
      f"pero estamos verificando si en este driver sí afecta la tasa real)")
print(f"Verificando transporte en {puerto} por {dur:.0f}s...\n")

## ── Resincronización de alineamiento de byte ──────────────────────────────────
# Si Python se conecta a mitad de un stream que ya está corriendo, puede quedar
# desfasado 1 byte respecto a los pares uint16 — y entonces CADA muestra sale
# mal, no al azar. Buscamos qué offset (0 o 1) da una rampa consistente antes
# de empezar a contar de verdad.

def encontrar_offset(datos: bytes) -> int:
    mejor_offset, mejor_ok = 0, -1
    for offset in (0, 1):
        usable = len(datos) - offset
        n = (usable // 2) * 2
        if n < 16:
            continue
        muestras = np.frombuffer(datos[offset:offset + n], dtype="<u2").astype(np.int32)
        diffs = np.diff(muestras)
        ok = int(np.sum((diffs == 1) | (diffs == 1 - 65536)))
        if ok > mejor_ok:
            mejor_ok, mejor_offset = ok, offset
    return mejor_offset

sync_buf = bytearray()
while len(sync_buf) < 512:
    sync_buf += ser.read(512 - len(sync_buf))

offset = encontrar_offset(bytes(sync_buf))
sync_buf = sync_buf[offset:]
print(f"Alineamiento encontrado: offset={offset} byte(s) descartado(s) al inicio")
print(f"Primeros 32 bytes crudos (hex): {bytes(sync_buf[:32]).hex(' ')}")
print(f"Interpretados como <u2: {list(np.frombuffer(bytes(sync_buf[:32]), dtype='<u2'))}\n")

buf           = sync_buf
total_bytes   = len(sync_buf)
total_samples = 0
gaps          = 0
max_gap       = 0
prev          = None

t_start     = time.time()
last_report = t_start

while time.time() - t_start < dur:
    dato = ser.read(4096)
    if dato:
        buf += dato
        total_bytes += len(dato)

    n_pairs = len(buf) // 2
    if n_pairs:
        muestras = np.frombuffer(bytes(buf[:n_pairs * 2]), dtype="<u2")
        buf = buf[n_pairs * 2:]

        if prev is not None:
            secuencia = np.concatenate(([prev], muestras))
        else:
            secuencia = muestras

        diffs    = np.diff(secuencia.astype(np.int32))
        esperado = (diffs == 1) | (diffs == 1 - 65536)
        malos    = np.where(~esperado)[0]

        if len(malos):
            for idx in malos:
                salto = diffs[idx] if diffs[idx] > 0 else diffs[idx] + 65536
                max_gap = max(max_gap, int(salto))
            gaps += len(malos)

        total_samples += len(muestras)
        prev = secuencia[-1]

    if time.time() - last_report > 2:
        elapsed = time.time() - t_start
        rate = total_bytes / elapsed if elapsed > 0 else 0
        print(f"  bytes={total_bytes}  muestras={total_samples}  "
              f"gaps={gaps}  tasa={rate:.0f} B/s")
        if len(muestras) >= 8:
            print(f"    muestra cruda: {list(muestras[:8])}")
        last_report = time.time()

ser.close()

rate = total_bytes / dur if dur > 0 else 0
print("\n=== RESULTADO ===")
print(f"Bytes totales    : {total_bytes}  (~{rate:.0f} B/s, esperado ~32000 B/s)")
print(f"Muestras totales : {total_samples}")
print(f"Gaps detectados  : {gaps}  (máx salto: {max_gap} muestras)")

if gaps == 0:
    print("OK  — transporte limpio, cero pérdidas de datos.")
else:
    print("FALLA — se perdieron/duplicaron muestras en el transporte USB.")
