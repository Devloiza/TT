import serial
import wave
import numpy as np
import sounddevice as sd
import soundfile as sf
import sys
import time

PORT       = "COM3"       # Windows: "COM3", Mac/Linux: "/dev/ttyUSB0"
BAUD       = 921600
RATE       = 8000
CHANNELS   = 1
DURATION   = 5            # segundos a grabar
OUTPUT     = "audio.wav"

SAMPLES    = RATE * DURATION
DTYPE      = np.int16
BYTES_EACH = 2            # int16 = 2 bytes por muestra

print(f"Conectando a {PORT}...")
ser = serial.Serial(PORT, BAUD, timeout=5)

# Esperar la señal START del ESP32
print("Esperando señal del ESP32...")
buf = b""
deadline = time.time() + 10
while b"START" not in buf:
    buf += ser.read(64)
    if time.time() > deadline:
        print("ERROR: No se recibió señal START. Verifica el puerto y el baudrate.")
        sys.exit(1)

# Descartar cualquier byte extra antes del START
buf = buf[buf.index(b"START") + 5:]

print(f"Grabando {DURATION} segundos... habla al micrófono!")

needed   = SAMPLES * BYTES_EACH
raw_data = buf  # puede traer algunos bytes ya leídos

while len(raw_data) < needed:
    chunk = ser.read(min(1024, needed - len(raw_data)))
    raw_data += chunk
    elapsed = len(raw_data) / (BYTES_EACH * RATE)
    print(f"  {elapsed:.1f} / {DURATION} seg", end="\r")

ser.close()
print("\nRecepción completa.")

# Convertir a numpy
samples = np.frombuffer(raw_data[:needed], dtype=DTYPE)

# ── Guardar WAV ────────────────────────────────────────────
sf.write(OUTPUT, samples, RATE, subtype="PCM_16")
print(f"Archivo guardado: {OUTPUT}")

# ── Reproducir en la PC ────────────────────────────────────
print("Reproduciendo...")
sd.play(samples.astype(np.float32) / 32768.0, samplerate=RATE)
sd.wait()
print("Listo.")