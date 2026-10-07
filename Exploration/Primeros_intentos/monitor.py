import pyaudio
import numpy as np
import sys
import time
import threading
import queue
import os

try:
    import serial
    _SERIAL_OK = True
except ImportError:
    _SERIAL_OK = False

os.system('cls')

## ── CONFIG ────────────────────────────────────────────────────────────────────

PC_RATE      = 44100
ESP32_PORT   = "COM7"
ESP32_BAUD   = 921600
ESP32_RATE   = 25000
CHANNELS     = 1
FORMAT       = pyaudio.paInt16
# Chunk pequeño = menos latencia. 256 → ~6 ms a 44100 Hz
CHUNK        = 256

## ── MODO 1: Micrófono PC (callback, mínima latencia) ─────────────────────────

def monitor_pc():
    p = pyaudio.PyAudio()

    def callback(in_data, frame_count, time_info, status):
        return (in_data, pyaudio.paContinue)

    stream = p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=PC_RATE,
        input=True,
        output=True,
        frames_per_buffer=CHUNK,
        stream_callback=callback
    )

    stream.start_stream()
    print(f"Escuchando micrófono PC ({PC_RATE} Hz, latencia ~{CHUNK*1000//PC_RATE} ms).")
    print("Presiona ENTER para detener.\n")
    input()

    stream.stop_stream()
    stream.close()
    p.terminate()

## ── MODO 2: Micrófono ESP32 vía serial ───────────────────────────────────────

def monitor_esp32():
    if not _SERIAL_OK:
        print("ERROR: Instala pyserial  →  pip install pyserial")
        sys.exit(1)

    print(f"\nConectando a {ESP32_PORT} @ {ESP32_BAUD} baud...")
    ser = serial.Serial(ESP32_PORT, ESP32_BAUD, timeout=5)

    print("Esperando señal START del ESP32...")
    buf = b""
    deadline = time.time() + 10
    while b"START" not in buf:
        buf += ser.read(64)
        if time.time() > deadline:
            ser.close()
            print("ERROR: No llegó START. Verifica puerto y baudrate.")
            sys.exit(1)

    # Descartar bytes anteriores al marcador
    buf = buf[buf.index(b"START") + 5:]

    audio_q: queue.Queue[bytes] = queue.Queue(maxsize=16)
    stop_evt = threading.Event()

    # Hilo lector: serial → queue
    def leer_serial():
        chunk_bytes = CHUNK * 2  # int16 = 2 bytes
        resto = buf
        while not stop_evt.is_set():
            while len(resto) < chunk_bytes and not stop_evt.is_set():
                resto += ser.read(min(1024, chunk_bytes - len(resto)))
            if stop_evt.is_set():
                break
            try:
                audio_q.put_nowait(resto[:chunk_bytes])
            except queue.Full:
                pass  # descarta si la cola está llena (evita acumulación)
            resto = resto[chunk_bytes:]
        ser.close()

    hilo = threading.Thread(target=leer_serial, daemon=True)
    hilo.start()

    p = pyaudio.PyAudio()
    stream = p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=ESP32_RATE,
        output=True,
        frames_per_buffer=CHUNK
    )

    print(f"Escuchando ESP32 ({ESP32_RATE} Hz). Presiona ENTER para detener.\n")

    def reproducir():
        while not stop_evt.is_set():
            try:
                datos = audio_q.get(timeout=0.1)
                stream.write(datos)
            except queue.Empty:
                pass

    hilo_audio = threading.Thread(target=reproducir, daemon=True)
    hilo_audio.start()

    input()
    stop_evt.set()
    hilo.join(timeout=2)
    hilo_audio.join(timeout=2)

    stream.stop_stream()
    stream.close()
    p.terminate()

## ── MAIN ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== Monitor de audio en tiempo real ===")

    monitor_esp32()
    print("Monitor detenido.")
