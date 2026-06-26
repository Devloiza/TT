import pyaudio
import numpy as np
import serial
import sys
import time
import threading
import queue
import os

os.system('cls' if os.name == 'nt' else 'clear')

## ── CONFIG ────────────────────────────────────────────────────────────────────

ESP32_PORT  = "COM9"    # cambia al puerto de tu ESP32
ESP32_BAUD  = 921600
ESP32_RATE  = 16000     # debe coincidir con SAMPLE_RATE del .ino
CHUNK       = 512       # muestras por canal — debe coincidir con CHUNK_SAMPLES

## ── CONSTANTES DERIVADAS ──────────────────────────────────────────────────────

# El ESP32 manda CHUNK muestras Mic1 + CHUNK muestras Mic2 intercaladas
# → CHUNK*2 valores int16 → CHUNK*2*2 bytes por iteración
CHUNK_BYTES = CHUNK * 2 * 2
LATENCY_MS  = CHUNK * 1000 // ESP32_RATE

## ── RECEPCIÓN ─────────────────────────────────────────────────────────────────

def esperar_start(ser) -> bytearray:
    print("Esperando START del ESP32...")
    buf = b""
    deadline = time.time() + 10
    while b"START" not in buf:
        buf += ser.read(64)
        if time.time() > deadline:
            print("ERROR: No llegó START. Verifica puerto y baudrate.")
            ser.close()
            sys.exit(1)
    print("START recibido.\n")
    return bytearray(buf[buf.index(b"START") + 5:])


def monitor():
    print(f"Conectando a {ESP32_PORT} @ {ESP32_BAUD} baud...")
    try:
        ser = serial.Serial(ESP32_PORT, ESP32_BAUD, timeout=5)
    except serial.SerialException as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    resto      = esperar_start(ser)
    audio_q    : queue.Queue[np.ndarray] = queue.Queue(maxsize=20)
    stop_evt   = threading.Event()
    underruns  = 0

    # ── Hilo lector: serial → queue de arrays numpy ───────────────────────────
    def leer_serial():
        nonlocal resto
        while not stop_evt.is_set():
            while len(resto) < CHUNK_BYTES and not stop_evt.is_set():
                try:
                    resto += ser.read(min(2048, CHUNK_BYTES - len(resto)))
                except serial.SerialException:
                    stop_evt.set()
                    return

            if stop_evt.is_set():
                break

            bloque  = bytes(resto[:CHUNK_BYTES])
            resto   = resto[CHUNK_BYTES:]

            # Parsear stream intercalado → shape (CHUNK, 2): col0=Mic1, col1=Mic2
            muestras = np.frombuffer(bloque, dtype=np.int16) \
                         .reshape(CHUNK, 2) \
                         .astype(np.float32) / 32768.0

            try:
                audio_q.put_nowait(muestras)
            except queue.Full:
                pass

        ser.close()
        print("Puerto cerrado.")

    # ── Hilo reproductor: queue → PyAudio estéreo ─────────────────────────────
    def reproducir():
        nonlocal underruns
        silencio = np.zeros((CHUNK, 2), dtype=np.float32)

        while not stop_evt.is_set():
            try:
                frame = audio_q.get(timeout=0.08)   # shape (CHUNK, 2)
            except queue.Empty:
                frame = silencio
                underruns += 1

            # PyAudio espera el array aplanado: [M1_0, M2_0, M1_1, M2_1, ...]
            try:
                stream.write(frame.flatten().tobytes())
            except OSError:
                break

    # ── Hilo de estadísticas ──────────────────────────────────────────────────
    def stats():
        while not stop_evt.is_set():
            time.sleep(5)
            if stop_evt.is_set():
                break
            print(f"  [stats]  Cola: {audio_q.qsize():>2}  "
                  f"Underruns: {underruns}")

    # ── Abrir stream PyAudio estéreo ──────────────────────────────────────────
    p      = pyaudio.PyAudio()
    stream = p.open(
        format            = pyaudio.paFloat32,
        channels          = 2,
        rate              = ESP32_RATE,
        output            = True,
        frames_per_buffer = CHUNK,
    )

    print(f"Escuchando  {ESP32_PORT}  —  2 mics estéreo @ {ESP32_RATE} Hz")
    print(f"  Mic 1 (L/R=GND)  →  oído izquierdo")
    print(f"  Mic 2 (L/R=VCC)  →  oído derecho")
    print(f"  Latencia estimada: ~{LATENCY_MS} ms\n")
    print("Presiona ENTER para detener.\n")

    t_leer  = threading.Thread(target=leer_serial, daemon=True)
    t_audio = threading.Thread(target=reproducir,  daemon=True)
    # t_stats = threading.Thread(target=stats,        daemon=True)

    t_leer.start()
    t_audio.start()
    # t_stats.start()

    input()

    print("\nDeteniendo...")
    stop_evt.set()
    t_leer.join(timeout=2)
    t_audio.join(timeout=2)

    stream.stop_stream()
    stream.close()
    p.terminate()
    print(f"Monitor detenido. Underruns totales: {underruns}")


## ── MAIN ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== Monitor estéreo — 2 mics en 1 ESP32 ===\n")
    monitor()