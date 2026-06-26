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

## ── DEBUG ─────────────────────────────────────────────────────────────────────
DEBUG = True    # True = imprime todos los puntos de control
                # False = producción, solo errores críticos

def dbg(msg):
    if DEBUG:
        print(f"[DBG] {msg}")

## ── CONFIG ────────────────────────────────────────────────────────────────────

ESP32_PORT  = "COM8"
ESP32_BAUD  = 115200
ESP32_RATE  = 16000
CHUNK       = 512

## ── PROTOCOLO DE CANAL ────────────────────────────────────────────────────────
#
#   Bits [1:0] de cada muestra int16 identifican el canal:
#   00 → Mic 1 (Bus0-L)
#   01 → Mic 2 (Bus0-R)
#   10 → Mic 3 (Bus1-L)
#   11 → Mic 4 (Bus1-R)
#
#   Orden esperado dentro de cada grupo de 4: [0, 1, 2, 3]

ID_ESPERADOS  = [0, 1, 2, 3]
ID_MASK       = np.int16(0x03)    # máscara para extraer los 2 bits bajos
AUDIO_MASK    = np.int16(-4)      # 0xFFFC — limpia los 2 bits bajos para audio

## ── CONSTANTES ────────────────────────────────────────────────────────────────

N_CANALES   = 4
CHUNK_BYTES = CHUNK * N_CANALES * 2
LATENCY_MS  = CHUNK * 1000 // ESP32_RATE

PAR_ACTIVO = 0

PAR_NOMBRES = {
    0: "Bus I2S 0  →  Mic1 (izq, L/R=GND) + Mic2 (der, L/R=VCC)  [pines 4/5/6]",
    1: "Bus I2S 1  →  Mic3 (izq, L/R=GND) + Mic4 (der, L/R=VCC)  [pines 11/12/13]",
}

PAR_COLS = {0: (0, 1), 1: (2, 3)}

audio_q   : queue.Queue[np.ndarray] = queue.Queue(maxsize=40)
stop_evt  = threading.Event()
par_lock  = threading.Lock()

# Contadores globales de debug
stats_data = {
    "underruns"     : 0,
    "realineamientos": 0,
    "frames_ok"     : 0,
    "frames_err"    : 0,
}

## ── CONEXIÓN ──────────────────────────────────────────────────────────────────

def conectar() -> serial.Serial:
    dbg(f"Intentando conectar a {ESP32_PORT}...")
    ser = None
    for intento in range(10):
        try:
            ser = serial.Serial(ESP32_PORT, ESP32_BAUD, timeout=2)
            ser.reset_input_buffer()
            time.sleep(0.5)
            dbg(f"Conectado en intento {intento + 1}")
            break
        except serial.SerialException as e:
            dbg(f"Intento {intento + 1}/10 fallido: {e}")
            time.sleep(1)

    if ser is None:
        print("ERROR: No se pudo conectar. Puertos disponibles:")
        for p in serial.tools.list_ports.comports():
            print(f"  {p.device}  —  {p.description}")
        sys.exit(1)

    return ser

## ── SINCRONIZACIÓN ────────────────────────────────────────────────────────────

def sincronizar(ser) -> bytearray:
    """
    Lee bytes hasta encontrar un grupo de 4 muestras con IDs [0,1,2,3]
    en orden correcto. No necesita marcador especial — usa los bits de canal.
    """
    dbg("Buscando sincronización por bits de canal...")
    buf      = bytearray()
    deadline = time.time() + 30
    intentos = 0

    while time.time() < deadline:
        try:
            dato = ser.read(256)
            if dato:
                buf += dato
        except Exception as e:
            dbg(f"Error leyendo durante sync: {e}")

        # Necesitamos al menos 8 bytes (4 muestras int16) para verificar
        while len(buf) >= 8:
            # Leer 4 muestras int16 desde el inicio del buffer
            muestras = np.frombuffer(bytes(buf[:8]), dtype=np.int16)
            ids      = [int(m & 0x03) for m in muestras]

            if ids == ID_ESPERADOS:
                dbg(f"Sincronización encontrada tras {intentos} intentos")
                dbg(f"IDs verificados: {ids}")
                return bytearray(buf[8:])   # descartar las 4 muestras de sync
            else:
                # Desalineado — avanzar 2 bytes y reintentar
                buf    = buf[2:]
                intentos += 1
                if DEBUG and intentos % 100 == 0:
                    dbg(f"Buscando alineamiento... intento {intentos} IDs={ids}")

    print("ERROR: No se encontró sincronización en 30 segundos.")
    ser.close()
    sys.exit(1)

## ── HILO LECTOR ───────────────────────────────────────────────────────────────

def leer_serial(ser, resto):
    resto    = bytearray(resto)
    cnt      = 0
    err_cons = 0   # errores consecutivos de alineamiento

    dbg("Hilo lector iniciado")

    while not stop_evt.is_set():
        # Acumular bytes hasta tener un chunk completo
        while len(resto) < CHUNK_BYTES and not stop_evt.is_set():
            try:
                dato = ser.read(min(4096, CHUNK_BYTES - len(resto)))
                if dato:
                    resto += dato
            except serial.SerialException:
                dbg("SerialException en hilo lector — deteniendo")
                stop_evt.set()
                return

        if stop_evt.is_set():
            break

        bloque = bytes(resto[:CHUNK_BYTES])
        resto  = resto[CHUNK_BYTES:]
        cnt   += 1

        # Parsear a int16 sin convertir todavía — necesitamos los bits de canal
        raw = np.frombuffer(bloque, dtype=np.int16)   # shape: (CHUNK*4,)

        # ── Verificar alineamiento de canal ───────────────────────────────────
        # Los IDs en las 4 primeras muestras deben ser [0, 1, 2, 3]
        ids_inicio = [int(raw[j] & 0x03) for j in range(4)]

        if ids_inicio != ID_ESPERADOS:
            stats_data["frames_err"] += 1
            err_cons += 1

            print(f"\n[WARN] Desalineamiento detectado en frame {cnt} "
                  f"— IDs={ids_inicio} esperados={ID_ESPERADOS} "
                  f"(errores consecutivos: {err_cons})")

            # Resincronizar: buscar en el bloque el primer grupo [0,1,2,3]
            realineado = False
            for offset in range(0, len(bloque) - 8, 2):
                sub = np.frombuffer(bloque[offset:offset+8], dtype=np.int16)
                if list(sub & 0x03) == ID_ESPERADOS:
                    resto      = bytearray(bloque[offset+8:]) + resto
                    realineado = True
                    stats_data["realineamientos"] += 1
                    err_cons   = 0
                    dbg(f"Realineamiento exitoso en offset={offset}")
                    break

            if not realineado:
                dbg("No se pudo realinear en este bloque — descartando")
            continue

        # Alineamiento correcto
        err_cons = 0
        stats_data["frames_ok"] += 1

        # Limpiar bits de canal y convertir a float32
        audio = (raw & AUDIO_MASK).reshape(CHUNK, N_CANALES).astype(np.float32) / 32768.0

        # Debug periódico de RMS
        if DEBUG and cnt % 200 == 0:
            rms  = [float(np.sqrt(np.mean(audio[:, i]**2))) for i in range(4)]
            pico = [float(np.max(np.abs(audio[:, i]))) for i in range(4)]
            print(f"\n[DBG frame={cnt}]"
                  f"  RMS  M1={rms[0]:.4f} M2={rms[1]:.4f}"
                  f" M3={rms[2]:.4f} M4={rms[3]:.4f}"
                  f"  PICO M1={pico[0]:.4f} M2={pico[1]:.4f}"
                  f" M3={pico[2]:.4f} M4={pico[3]:.4f}")

        try:
            audio_q.put_nowait(audio)
        except queue.Full:
            dbg(f"Cola llena en frame {cnt} — descartando frame")

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
            if DEBUG and stats_data["underruns"] % 10 == 0:
                dbg(f"Underrun #{stats_data['underruns']}")
            continue

        with par_lock:
            col_izq, col_der = PAR_COLS[PAR_ACTIVO]

        estereo = np.stack([frame[:, col_izq],
                            frame[:, col_der]], axis=1)
        try:
            stream.write(estereo.flatten().tobytes())
        except OSError as e:
            dbg(f"OSError en reproductor: {e}")
            break

    dbg("Hilo reproductor terminado")

## ── HILO ESTADÍSTICAS ─────────────────────────────────────────────────────────

def stats():
    dbg("Hilo estadísticas iniciado")
    while not stop_evt.is_set():
        time.sleep(5)
        if stop_evt.is_set():
            break
        with par_lock:
            par = PAR_ACTIVO
        print(f"\n[STATS]"
              f"  Cola: {audio_q.qsize():>2}"
              f"  Underruns: {stats_data['underruns']}"
              f"  Frames OK: {stats_data['frames_ok']}"
              f"  Frames ERR: {stats_data['frames_err']}"
              f"  Realineamientos: {stats_data['realineamientos']}"
              f"  Par activo: {par}")

## ── HILO TECLADO ──────────────────────────────────────────────────────────────

def escuchar_teclado():
    global PAR_ACTIVO
    dbg("Hilo teclado iniciado")
    while not stop_evt.is_set():
        try:
            tecla = input()
            if tecla.strip() == "1":
                with par_lock:
                    PAR_ACTIVO = 0
                print(f"\n  → Par 0: {PAR_NOMBRES[0]}\n")
            elif tecla.strip() == "2":
                with par_lock:
                    PAR_ACTIVO = 1
                print(f"\n  → Par 1: {PAR_NOMBRES[1]}\n")
            elif tecla.strip().lower() == "q":
                dbg("Usuario solicitó salir")
                stop_evt.set()
        except EOFError:
            break

## ── MAIN ──────────────────────────────────────────────────────────────────────

def monitor():
    global stream

    dbg(f"Iniciando monitor — DEBUG={DEBUG}")
    dbg(f"Puerto={ESP32_PORT} Rate={ESP32_RATE} Chunk={CHUNK}")
    dbg(f"CHUNK_BYTES={CHUNK_BYTES} N_CANALES={N_CANALES}")

    ser   = conectar()
    resto = sincronizar(ser)

    dbg("Abriendo stream PyAudio...")
    p      = pyaudio.PyAudio()
    stream = p.open(
        format            = pyaudio.paFloat32,
        channels          = 2,
        rate              = ESP32_RATE,
        output            = True,
        frames_per_buffer = CHUNK,
    )
    dbg("Stream PyAudio listo")

    print("\n" + "═" * 60)
    print("  Monitor 4 micrófonos — USB CDC  16000 Hz")
    print(f"  Puerto : {ESP32_PORT}")
    print(f"  Fs     : {ESP32_RATE} Hz  |  Latencia: ~{LATENCY_MS} ms")
    print(f"  DEBUG  : {DEBUG}")
    print("═" * 60)
    print(f"\n  Par activo: {PAR_NOMBRES[PAR_ACTIVO]}\n")
    print("  Comandos:")
    print("    1 + ENTER  →  Bus 0 (Mic1 + Mic2)")
    print("    2 + ENTER  →  Bus 1 (Mic3 + Mic4)")
    print("    q + ENTER  →  salir\n")

    t_leer   = threading.Thread(target=leer_serial,
                                args=(ser, resto), daemon=True)
    t_audio  = threading.Thread(target=reproducir,       daemon=True)
    t_stats  = threading.Thread(target=stats,             daemon=True)
    t_teclas = threading.Thread(target=escuchar_teclado,  daemon=True)

    t_leer.start()
    t_audio.start()
    t_stats.start()
    t_teclas.start()

    dbg("Todos los hilos iniciados")

    t_teclas.join()

    print("\nDeteniendo...")
    stop_evt.set()
    t_leer.join(timeout=2)
    t_audio.join(timeout=2)

    stream.stop_stream()
    stream.close()
    p.terminate()

    print(f"\n[RESUMEN FINAL]")
    print(f"  Frames OK          : {stats_data['frames_ok']}")
    print(f"  Frames con error   : {stats_data['frames_err']}")
    print(f"  Realineamientos    : {stats_data['realineamientos']}")
    print(f"  Underruns de audio : {stats_data['underruns']}")
    dbg("Monitor terminado")


if __name__ == "__main__":
    print("=== Monitor 4 micrófonos — Bits de canal ===\n")
    monitor()