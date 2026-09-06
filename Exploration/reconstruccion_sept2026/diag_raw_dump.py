"""
diag_raw_dump.py
Volcado crudo de un puerto serie — sin parseo, sin sincronización.
Úsalo con DIAG_MODE 1 en el firmware para ver exactamente qué canal
(Serial USB nativo vs Serial0 UART) le está llegando a este puerto.

Uso:
    python diag_raw_dump.py COM8
"""

import sys
import serial

if len(sys.argv) < 2:
    print("Uso: python diag_raw_dump.py <PUERTO>   (ej. COM8)")
    sys.exit(1)

puerto = sys.argv[1]
ser = serial.Serial(puerto, 115200, timeout=1)
print(f"Leyendo crudo de {puerto}... (Ctrl+C para salir)\n")

try:
    while True:
        dato = ser.read(256)
        if dato:
            # Muestra texto imprimible tal cual, bytes no imprimibles como .
            texto = "".join(chr(b) if 32 <= b < 127 or b in (9, 10, 13) else "." for b in dato)
            print(texto, end="", flush=True)
except KeyboardInterrupt:
    pass
finally:
    ser.close()
