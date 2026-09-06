"""
monitor_stage2_4mic.py — Etapa 2: 4 micrófonos, 1 placa, sin SYNC.

Basado en Exploration/monitor_4LR.py, con el baud corregido a 3,000,000
(la causa raíz encontrada en la Etapa 1a: Serial y Serial0 comparten el
mismo periférico UART físico en esta placa, así que firmware y Python
deben coincidir exactamente en el baud).
"""

import pyaudio
import numpy as np
import serial
import serial.tools.list_ports
import sys
import time
import threading
import queue
import os

os.system('cls' if os.name == 'nt' else 'clear')

DEBUG = True

def dbg(msg):
    if DEBUG:
        print(f"[DBG] {msg}")

## ── CONFIG ────────────────────────────────────────────────────────────────────

ESP32_PORT  = "COM8"
ESP32_BAUD  = 3000000
ESP32_RATE  = 16000
CHUNK       = 512

ID_ESPERADOS = [0, 1, 2, 3]
AUDIO_MASK   = np.int16(-4)   # 0xFFFC

N_CANALES   = 4
CHUNK_BYTES = CHUNK * N_CANALES * 2
LATENCY_MS  = CHUNK * 1000 // ESP32_RATE

PAR_ACTIVO = 0
PAR_NOMBRES = {
    0: "Bus I2S 0  →  Mic1 (izq) + Mic2 (der)  [pines 4/5/6]",
    1: "Bus I2S 1  →  Mic3 (izq) + Mic4 (der)  [pines 11/12/13]",
}
PAR_COLS = {0: (0, 1), 1: (2, 3)}

audio_q  : queue.Queue[np.ndarray] = queue.Queue(maxsize=40)
stop_evt = threading.Event()
par_lock = threading.Lock()

stats_data = {
    "underruns": 0, "realineamientos": 0, "frames_ok": 0, "frames_err": 0,
}

## ── CONEXIÓN ──────────────────────────────────────────────────────────────────

def conectar() -> serial.Serial:
    dbg(f"Conectando a {ESP32_PORT} @ {ESP32_BAUD} baud...")
    for intento in range(10):
        try:
            ser = serial.Serial(ESP32_PORT, ESP32_BAUD, timeout=2)
            ser.reset_input_buffer()
            time.sleep(0.5)
            dbg(f"Conectado en intento {intento + 1}")
            return ser
        except serial.SerialException as e:
            dbg(f"Intento {intento + 1}/10 fallido: {e}")
            time.sleep(1)

    print("ERROR: No se pudo conectar. Puertos disponibles:")
    for p in serial.tools.list_ports.comports():
        print(f"  {p.device}  —  {p.description}")
    sys.exit(1)

## ── SINCRONIZACIÓN POR BITS DE CANAL ─────────────────────────────────────────

def sincronizar(ser) -> bytearray:
    dbg("Buscando sincronización por bits de canal...")
    buf = bytearray()
    deadline = time.time() + 30
    intentos = 0

    while time.time() < deadline:
        dato = ser.read(256)
        if dato:
            buf += dato

        while len(buf) >= 8:
            muestras = np.frombuffer(bytes(buf[:8]), dtype=np.int16)
            ids = [int(m & 0x03) for m in muestras]
            if ids == ID_ESPERADOS:
                dbg(f"Sincronizado tras {intentos} intentos")
                return bytearray(buf[8:])
            buf = buf[2:]
            intentos += 1
            if DEBUG and intentos % 200 == 0:
                dbg(f"Buscando... intento {intentos} IDs={ids}")

    print("ERROR: No se encontró sincronización en 30s.")
    ser.close()
    sys.exit(1)

## ── HILO LECTOR ───────────────────────────────────────────────────────────────

def leer_serial(ser, resto):
    resto = bytearray(resto)
    cnt = 0

    dbg("Hilo lector iniciado")

    while not stop_evt.is_set():
        while len(resto) < CHUNK_BYTES and not stop_evt.is_set():
            try:
                dato = ser.read(min(4096, CHUNK_BYTES - len(resto)))
                if dato:
                    resto += dato
            except serial.SerialException:
                dbg("SerialException — deteniendo")
                stop_evt.set()
                return

        if stop_evt.is_set():
            break

        bloque = bytes(resto[:CHUNK_BYTES])
        resto = resto[CHUNK_BYTES:]
        cnt += 1

        raw = np.frombuffer(bloque, dtype=np.int16)
        ids_inicio = [int(raw[j] & 0x03) for j in range(4)]

        if ids_inicio != ID_ESPERADOS:
            stats_data["frames_err"] += 1
            print(f"\n[WARN] Desalineamiento frame {cnt} IDs={ids_inicio}")

            realineado = False
            for offset in range(0, len(bloque) - 8, 2):
                sub = np.frombuffer(bloque[offset:offset+8], dtype=np.int16)
                if list(sub & 0x03) == ID_ESPERADOS:
                    resto = bytearray(bloque[offset+8:]) + resto
                    realineado = True
                    stats_data["realineamientos"] += 1
                    dbg(f"Realineado offset={offset}")
                    break
            if not realineado:
                dbg("No se pudo realinear — descartando")
            continue

        stats_data["frames_ok"] += 1
        audio = (raw & AUDIO_MASK).reshape(CHUNK, N_CANALES).astype(np.float32) / 32768.0

        if DEBUG and cnt % 200 == 0:
            rms = [float(np.sqrt(np.mean(audio[:, i]**2))) for i in range(4)]
            print(f"\n[DBG frame={cnt}]  RMS M1={rms[0]:.4f} M2={rms[1]:.4f} "
                  f"M3={rms[2]:.4f} M4={rms[3]:.4f}")

        try:
            audio_q.put_nowait(audio)
        except queue.Full:
            dbg(f"Cola llena en frame {cnt} — descartando")

    ser.close()
    dbg("Hilo lector terminado")

## ── HILO REPRODUCTOR ──────────────────────────────────────────────────────────

def reproducir():
    silencio = np.zeros((CHUNK, 2), dtype=np.float32)
    dbg("Hilo reproductor iniciado")

    while not stop_evt.is_set():
        try:
            frame = audio_q.get(timeout=0.1)
        except queue.Empty:
            stream.write(silencio.flatten().tobytes())
            stats_data["underruns"] += 1
            continue

        with par_lock:
            col_izq, col_der = PAR_COLS[PAR_ACTIVO]

        estereo = np.stack([frame[:, col_izq], frame[:, col_der]], axis=1)
        try:
            stream.write(estereo.flatten().tobytes())
        except OSError as e:
            dbg(f"OSError reproductor: {e}")
            break

    dbg("Hilo reproductor terminado")

## ── HILO ESTADÍSTICAS ─────────────────────────────────────────────────────────

def stats():
    while not stop_evt.is_set():
        time.sleep(5)
        if stop_evt.is_set():
            break
        with par_lock:
            par = PAR_ACTIVO
        print(f"\n[STATS]  Cola: {audio_q.qsize():>2}  "
              f"Underruns: {stats_data['underruns']}  "
              f"Frames OK: {stats_data['frames_ok']}  "
              f"Frames ERR: {stats_data['frames_err']}  "
              f"Realineamientos: {stats_data['realineamientos']}  "
              f"Par activo: {par}")

## ── HILO TECLADO ──────────────────────────────────────────────────────────────

def escuchar_teclado():
    global PAR_ACTIVO
    while not stop_evt.is_set():
        try:
            tecla = input().strip()
            if tecla == "1":
                with par_lock:
                    PAR_ACTIVO = 0
                print(f"\n  → Par 0: {PAR_NOMBRES[0]}\n")
            elif tecla == "2":
                with par_lock:
                    PAR_ACTIVO = 1
                print(f"\n  → Par 1: {PAR_NOMBRES[1]}\n")
            elif tecla.lower() == "q":
                stop_evt.set()
        except EOFError:
            break

## ── MAIN ──────────────────────────────────────────────────────────────────────

def monitor():
    global stream

    dbg(f"Puerto={ESP32_PORT} Baud={ESP32_BAUD} Rate={ESP32_RATE} Chunk={CHUNK}")

    ser = conectar()
    resto = sincronizar(ser)

    p = pyaudio.PyAudio()
    stream = p.open(
        format=pyaudio.paFloat32, channels=2, rate=ESP32_RATE,
        output=True, frames_per_buffer=CHUNK,
    )

    print("\n" + "═" * 60)
    print("  Monitor Etapa 2 — 4 micrófonos, 1 placa (sin SYNC)")
    print(f"  Puerto: {ESP32_PORT} @ {ESP32_BAUD} baud  |  Fs: {ESP32_RATE} Hz")
    print(f"  Latencia: ~{LATENCY_MS} ms")
    print("═" * 60)
    print(f"\n  Par activo: {PAR_NOMBRES[PAR_ACTIVO]}\n")
    print("  Comandos:  1/2 cambiar par  |  q salir\n")

    t_leer   = threading.Thread(target=leer_serial, args=(ser, resto), daemon=True)
    t_audio  = threading.Thread(target=reproducir, daemon=True)
    t_stats  = threading.Thread(target=stats, daemon=True)
    t_teclas = threading.Thread(target=escuchar_teclado, daemon=True)

    t_leer.start()
    t_audio.start()
    t_stats.start()
    t_teclas.start()

    t_teclas.join()

    print("\nDeteniendo...")
    stop_evt.set()
    t_leer.join(timeout=2)
    t_audio.join(timeout=2)

    stream.stop_stream()
    stream.close()
    p.terminate()

    print(f"\n[RESUMEN] Frames OK: {stats_data['frames_ok']}  "
          f"ERR: {stats_data['frames_err']}  "
          f"Realineamientos: {stats_data['realineamientos']}  "
          f"Underruns: {stats_data['underruns']}")


if __name__ == "__main__":
    print("=== Monitor Etapa 2 — 4 micrófonos ===\n")
    monitor()
