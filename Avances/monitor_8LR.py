"""
monitor_das_8mic.py
══════════════════════════════════════════════════════════════════════════════
Monitor 8 micrófonos — 2× ESP32-S3 con arquitectura preparada para DAS.

Arquitectura:
  Hilo lector ESP1  ──┐
                       ├──► Hilo sincronizador ──► q_combinada (CHUNK, 8)
  Hilo lector ESP2  ──┘                                  │
                                                         ▼
                                                  Hilo reproductor
                                                  (escucha par activo)

La cola combinada garantiza que ambos ESP32 estén sincronizados en tiempo
antes de procesar — requisito fundamental para DAS.

Geometría del arreglo: geometria.json (editar con mediciones reales del collar)

Dependencias:
    pip install pyserial pyaudio numpy

Uso:
    python monitor_das_8mic.py
══════════════════════════════════════════════════════════════════════════════
"""

import pyaudio
import numpy as np
import serial
import serial.tools.list_ports
import json
import sys
import time
import threading
import queue
import os

os.system('cls' if os.name == 'nt' else 'clear')

## ── DEBUG ─────────────────────────────────────────────────────────────────────
DEBUG = True

def dbg(msg):
    if DEBUG:
        print(f"[DBG] {msg}")

## ── CONFIG ────────────────────────────────────────────────────────────────────

ESP1_PORT = "COM8"    # Master — Mics 1-4
ESP2_PORT = "COM6"    # Slave  — Mics 5-8
ESP_BAUD  = 115200
ESP_RATE  = 16000
CHUNK     = 512

GEOMETRIA_FILE = "geometria.json"

## ── HABILITACIÓN DE MICRÓFONOS ────────────────────────────────────────────────
#
#   Índice: [Bus0-L, Bus0-R, Bus1-L, Bus1-R]

ESP1_MICS = [True,  True,  True, True]
ESP2_MICS = [True,  True,  True, True]

## ── SELECCIÓN DE PAR A ESCUCHAR ───────────────────────────────────────────────
#
#   0 → ESP1 Bus0 (Mic1+Mic2)   1 → ESP1 Bus1 (Mic3+Mic4)
#   2 → ESP2 Bus0 (Mic5+Mic6)   3 → ESP2 Bus1 (Mic7+Mic8)

PAR_ACTIVO = 0

PAR_INFO = {
    0: (0, 1, "Mic1+Mic2  ESP1 Bus0  pines 4/5/6"),
    1: (2, 3, "Mic3+Mic4  ESP1 Bus1  pines 11/12/13"),
    2: (4, 5, "Mic5+Mic6  ESP2 Bus0  pines 4/5/6"),
    3: (6, 7, "Mic7+Mic8  ESP2 Bus1  pines 11/12/13"),
}

## ── CONSTANTES ────────────────────────────────────────────────────────────────

N_CANALES    = 4
N_TOTAL      = 8
CHUNK_BYTES  = CHUNK * N_CANALES * 2
LATENCY_MS   = CHUNK * 1000 // ESP_RATE
ID_ESPERADOS = [0, 1, 2, 3]
AUDIO_MASK   = np.int16(-4)   # 0xFFFC — limpia bits de canal

## ── COLAS ─────────────────────────────────────────────────────────────────────

# Colas individuales por ESP (frames de 4 canales)
q_esp1 : queue.Queue[np.ndarray] = queue.Queue(maxsize=8)
q_esp2 : queue.Queue[np.ndarray] = queue.Queue(maxsize=8)

# Cola combinada para el reproductor/DAS (frames de 8 canales)
q_combinada : queue.Queue[np.ndarray] = queue.Queue(maxsize=8)

stop_evt = threading.Event()
par_lock = threading.Lock()

stats_data = {
    "esp1_ok"      : 0, "esp1_err"    : 0, "esp1_realign": 0,
    "esp2_ok"      : 0, "esp2_err"    : 0, "esp2_realign": 0,
    "sync_ok"      : 0, "sync_drop"   : 0,
    "underruns"    : 0,
}

## ── CARGA DE GEOMETRÍA ────────────────────────────────────────────────────────

def cargar_geometria() -> dict:
    try:
        with open(GEOMETRIA_FILE, "r", encoding="utf-8") as f:
            geo = json.load(f)
        dbg(f"Geometría cargada: {len(geo['micrófonos'])} micrófonos")
        for mic in geo["micrófonos"]:
            dbg(f"  Mic{mic['id']}: x={mic['x']} y={mic['y']} z={mic['z']}")
        return geo
    except FileNotFoundError:
        print(f"[WARN] {GEOMETRIA_FILE} no encontrado — "
              f"DAS no disponible hasta crearlo")
        return None
    except json.JSONDecodeError as e:
        print(f"[ERROR] Error leyendo {GEOMETRIA_FILE}: {e}")
        return None

## ── CONEXIÓN ──────────────────────────────────────────────────────────────────

def conectar(port: str, label: str) -> serial.Serial:
    dbg(f"[{label}] Conectando a {port}...")
    for intento in range(10):
        try:
            ser = serial.Serial(port, ESP_BAUD, timeout=2)
            ser.reset_input_buffer()
            time.sleep(0.5)
            dbg(f"[{label}] Conectado en intento {intento + 1}")
            return ser
        except serial.SerialException as e:
            dbg(f"[{label}] Intento {intento + 1}/10: {e}")
            time.sleep(1)

    print(f"ERROR [{label}]: No se pudo conectar a {port}")
    print("Puertos disponibles:")
    for p in serial.tools.list_ports.comports():
        print(f"  {p.device}  —  {p.description}")
    return None

## ── SINCRONIZACIÓN POR BITS DE CANAL ─────────────────────────────────────────

def sincronizar(ser: serial.Serial, label: str) -> bytearray:
    dbg(f"[{label}] Buscando sincronización...")
    buf      = bytearray()
    deadline = time.time() + 30
    intentos = 0

    while time.time() < deadline:
        try:
            dato = ser.read(256)
            if dato:
                buf += dato
        except Exception as e:
            dbg(f"[{label}] Error durante sync: {e}")

        while len(buf) >= 8:
            muestras = np.frombuffer(bytes(buf[:8]), dtype=np.int16)
            ids      = [int(m & 0x03) for m in muestras]
            if ids == ID_ESPERADOS:
                dbg(f"[{label}] Sincronizado tras {intentos} intentos")
                return bytearray(buf[8:])
            else:
                buf      = buf[2:]
                intentos += 1
                if DEBUG and intentos % 200 == 0:
                    dbg(f"[{label}] Buscando... intento {intentos} IDs={ids}")

    print(f"ERROR [{label}]: Sin sincronización en 30s")
    ser.close()
    return None

## ── HILO LECTOR ───────────────────────────────────────────────────────────────

def hilo_lector(ser: serial.Serial, resto: bytearray,
                label: str, out_q: queue.Queue,
                mics_activos: list,
                k_ok: str, k_err: str, k_realign: str):

    resto = bytearray(resto)
    cnt   = 0
    dbg(f"[{label}] Hilo lector iniciado")

    while not stop_evt.is_set():
        while len(resto) < CHUNK_BYTES and not stop_evt.is_set():
            try:
                dato = ser.read(min(4096, CHUNK_BYTES - len(resto)))
                if dato:
                    resto += dato
            except serial.SerialException:
                dbg(f"[{label}] SerialException — deteniendo")
                stop_evt.set()
                return

        if stop_evt.is_set():
            break

        bloque = bytes(resto[:CHUNK_BYTES])
        resto  = resto[CHUNK_BYTES:]
        cnt   += 1

        raw        = np.frombuffer(bloque, dtype=np.int16)
        ids_inicio = [int(raw[j] & 0x03) for j in range(4)]

        if ids_inicio != ID_ESPERADOS:
            stats_data[k_err] += 1
            print(f"\n[WARN {label}] Desalineamiento frame {cnt} "
                  f"IDs={ids_inicio}")

            realineado = False
            for offset in range(0, len(bloque) - 8, 2):
                sub = np.frombuffer(bloque[offset:offset+8], dtype=np.int16)
                if list(sub & 0x03) == ID_ESPERADOS:
                    resto      = bytearray(bloque[offset+8:]) + resto
                    realineado = True
                    stats_data[k_realign] += 1
                    dbg(f"[{label}] Realineado offset={offset}")
                    break

            if not realineado:
                dbg(f"[{label}] No se pudo realinear — descartando")
            continue

        stats_data[k_ok] += 1

        audio = (raw & AUDIO_MASK).reshape(CHUNK, N_CANALES) \
                                  .astype(np.float32) / 32768.0

        for i in range(N_CANALES):
            if not mics_activos[i]:
                audio[:, i] = 0.0

        if DEBUG and cnt % 200 == 0:
            rms  = [float(np.sqrt(np.mean(audio[:, i]**2))) for i in range(4)]
            pico = [float(np.max(np.abs(audio[:, i]))) for i in range(4)]
            print(f"\n[DBG {label} frame={cnt}]"
                  f"  RMS  M1={rms[0]:.4f} M2={rms[1]:.4f}"
                  f" M3={rms[2]:.4f} M4={rms[3]:.4f}"
                  f"  PICO M1={pico[0]:.4f} M2={pico[1]:.4f}"
                  f" M3={pico[2]:.4f} M4={pico[3]:.4f}")

        # Meter en cola — si llena, descartar el más viejo
        try:
            out_q.put_nowait(audio)
        except queue.Full:
            try:
                out_q.get_nowait()
                out_q.put_nowait(audio)
            except queue.Empty:
                pass

    ser.close()
    dbg(f"[{label}] Hilo lector terminado")

## ── HILO SINCRONIZADOR ────────────────────────────────────────────────────────

def hilo_sincronizador():
    """
    Empareja frames de ambos ESP32 y produce frames combinados de 8 canales.
    Si uno de los dos no llega en 50ms, descarta ambos para evitar desfase.
    Este hilo es el punto de extensión para el DAS — aquí se aplicará
    el beamforming cuando esté listo.
    """
    cnt_sync = 0
    dbg("Hilo sincronizador iniciado")

    while not stop_evt.is_set():
        try:
            f1 = q_esp1.get(timeout=0.05)
        except queue.Empty:
            # ESP1 no llegó — drenar ESP2 para no acumular desfase
            while not q_esp2.empty():
                try:
                    q_esp2.get_nowait()
                    stats_data["sync_drop"] += 1
                except queue.Empty:
                    break
            continue

        try:
            f2 = q_esp2.get(timeout=0.05)
        except queue.Empty:
            # ESP2 no llegó — descartar el frame de ESP1 ya obtenido
            stats_data["sync_drop"] += 1
            if DEBUG and stats_data["sync_drop"] % 20 == 0:
                dbg(f"Sync drop #{stats_data['sync_drop']} "
                    f"(colas ESP1={q_esp1.qsize()} ESP2={q_esp2.qsize()})")
            continue

        # ── Aquí se aplicará DAS cuando esté implementado ─────────────────
        #
        # frame_8ch shape: (CHUNK, 8)
        # Canales 0-3: ESP1 (Mics 1-4)
        # Canales 4-7: ESP2 (Mics 5-8)
        #
        # Ejemplo futuro:
        #   retardos = calcular_retardos(geometria, angulo_doa)
        #   salida   = delay_and_sum(frame_8ch, retardos)
        # ──────────────────────────────────────────────────────────────────

        frame_8ch = np.concatenate([f1, f2], axis=1)   # (CHUNK, 8)
        cnt_sync += 1
        stats_data["sync_ok"] += 1

        if DEBUG and cnt_sync % 200 == 0:
            dbg(f"Sincronizador frame={cnt_sync} "
                f"colas ESP1={q_esp1.qsize()} ESP2={q_esp2.qsize()}")

        # Meter en cola combinada — si llena, descartar el más viejo
        try:
            q_combinada.put_nowait(frame_8ch)
        except queue.Full:
            try:
                q_combinada.get_nowait()
                q_combinada.put_nowait(frame_8ch)
            except queue.Empty:
                pass

    dbg("Hilo sincronizador terminado")

## ── HILO REPRODUCTOR ──────────────────────────────────────────────────────────

def reproducir():
    silencio = np.zeros((CHUNK, 2), dtype=np.float32)
    dbg("Hilo reproductor iniciado")

    while not stop_evt.is_set():
        try:
            frame_8ch = q_combinada.get(timeout=0.1)   # (CHUNK, 8)
        except queue.Empty:
            stream.write(silencio.flatten().tobytes())
            stats_data["underruns"] += 1
            if DEBUG and stats_data["underruns"] % 20 == 0:
                dbg(f"Underrun #{stats_data['underruns']}")
            continue

        with par_lock:
            par = PAR_ACTIVO

        col_izq, col_der, _ = PAR_INFO[par]
        estereo = np.stack([frame_8ch[:, col_izq],
                            frame_8ch[:, col_der]], axis=1)
        try:
            stream.write(estereo.flatten().tobytes())
        except OSError as e:
            dbg(f"OSError reproductor: {e}")
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
        _, _, desc = PAR_INFO[par]
        print(f"\n[STATS]"
              f"\n  Par activo   : {par} — {desc}"
              f"\n  Colas        : ESP1={q_esp1.qsize()}"
              f"  ESP2={q_esp2.qsize()}"
              f"  Combinada={q_combinada.qsize()}"
              f"\n  Sync OK/Drop : {stats_data['sync_ok']}"
              f"  /  {stats_data['sync_drop']}"
              f"\n  Underruns    : {stats_data['underruns']}"
              f"\n  ESP1         : OK={stats_data['esp1_ok']}"
              f"  ERR={stats_data['esp1_err']}"
              f"  Realign={stats_data['esp1_realign']}"
              f"\n  ESP2         : OK={stats_data['esp2_ok']}"
              f"  ERR={stats_data['esp2_err']}"
              f"  Realign={stats_data['esp2_realign']}")

## ── HILO TECLADO ──────────────────────────────────────────────────────────────

def escuchar_teclado():
    global PAR_ACTIVO
    dbg("Hilo teclado iniciado")
    while not stop_evt.is_set():
        try:
            tecla = input()
            t = tecla.strip()
            if t in ("1", "2", "3", "4"):
                par = int(t) - 1
                with par_lock:
                    PAR_ACTIVO = par
                _, _, desc = PAR_INFO[par]
                print(f"\n  → Par {par}: {desc}\n")
            elif t.lower() == "q":
                dbg("Usuario solicitó salir")
                stop_evt.set()
            else:
                print("  Comandos: 1-4 cambiar par | q salir")
        except EOFError:
            break

## ── MAIN ──────────────────────────────────────────────────────────────────────

def monitor():
    global stream

    dbg(f"DEBUG={DEBUG}")
    dbg(f"ESP1={ESP1_PORT}  ESP2={ESP2_PORT}")
    dbg(f"Rate={ESP_RATE}  Chunk={CHUNK}  CHUNK_BYTES={CHUNK_BYTES}")
    dbg(f"ESP1_MICS={ESP1_MICS}  ESP2_MICS={ESP2_MICS}")

    # Cargar geometría
    geo = cargar_geometria()
    if geo:
        dbg(f"Velocidad sonido: {geo['velocidad_sonido']} m/s")
    else:
        dbg("Geometría no cargada — DAS no disponible")

    # Conectar
    ser1 = conectar(ESP1_PORT, "ESP1")
    ser2 = conectar(ESP2_PORT, "ESP2")
    if ser1 is None or ser2 is None:
        print("ERROR: No se pudo conectar a uno o ambos ESP32.")
        sys.exit(1)

    # Sincronizar
    dbg("Sincronizando ESP1...")
    resto1 = sincronizar(ser1, "ESP1")
    dbg("Sincronizando ESP2...")
    resto2 = sincronizar(ser2, "ESP2")
    if resto1 is None or resto2 is None:
        print("ERROR: Fallo de sincronización.")
        sys.exit(1)

    # Stream de audio
    dbg("Abriendo stream PyAudio...")
    p      = pyaudio.PyAudio()
    stream = p.open(
        format            = pyaudio.paFloat32,
        channels          = 2,
        rate              = ESP_RATE,
        output            = True,
        frames_per_buffer = CHUNK,
    )
    dbg("Stream PyAudio listo")

    mics_habilitados = ESP1_MICS + ESP2_MICS
    n_activos        = sum(mics_habilitados)

    print("\n" + "═" * 62)
    print("  Monitor 8 micrófonos — 2× ESP32-S3  USB CDC  16000 Hz")
    print(f"  ESP1 (Master): {ESP1_PORT}   ESP2 (Slave): {ESP2_PORT}")
    print(f"  Fs: {ESP_RATE} Hz  |  Latencia: ~{LATENCY_MS} ms  |  DEBUG: {DEBUG}")
    print(f"  Geometría: {'cargada ✓' if geo else 'no disponible'}")
    print("═" * 62)
    print(f"\n  Micrófonos activos ({n_activos}/8):")
    nombres = ["Mic1","Mic2","Mic3","Mic4","Mic5","Mic6","Mic7","Mic8"]
    for nombre, activo in zip(nombres, mics_habilitados):
        print(f"    [{'✓' if activo else '✗'}] {nombre}")
    print(f"\n  Par activo: {PAR_ACTIVO} — {PAR_INFO[PAR_ACTIVO][2]}")
    print("\n  Comandos:")
    print("    1 → ESP1 Bus0 (Mic1+Mic2)   2 → ESP1 Bus1 (Mic3+Mic4)")
    print("    3 → ESP2 Bus0 (Mic5+Mic6)   4 → ESP2 Bus1 (Mic7+Mic8)")
    print("    q → salir\n")

    # Arrancar hilos
    t_l1 = threading.Thread(
        target=hilo_lector,
        args=(ser1, resto1, "ESP1", q_esp1, ESP1_MICS,
              "esp1_ok", "esp1_err", "esp1_realign"),
        daemon=True
    )
    t_l2 = threading.Thread(
        target=hilo_lector,
        args=(ser2, resto2, "ESP2", q_esp2, ESP2_MICS,
              "esp2_ok", "esp2_err", "esp2_realign"),
        daemon=True
    )
    t_sync  = threading.Thread(target=hilo_sincronizador, daemon=True)
    t_audio = threading.Thread(target=reproducir,         daemon=True)
    t_stats = threading.Thread(target=stats,              daemon=True)
    t_teclado = threading.Thread(target=escuchar_teclado, daemon=True)

    t_l1.start()
    t_l2.start()
    t_sync.start()
    t_audio.start()
    t_stats.start()
    t_teclado.start()

    dbg("Todos los hilos iniciados")
    t_teclado.join()

    print("\nDeteniendo...")
    stop_evt.set()
    for t in (t_l1, t_l2, t_sync, t_audio):
        t.join(timeout=2)

    stream.stop_stream()
    stream.close()
    p.terminate()

    print("\n[RESUMEN FINAL]")
    print(f"  Frames sincronizados : {stats_data['sync_ok']}")
    print(f"  Frames descartados   : {stats_data['sync_drop']}")
    print(f"  Underruns            : {stats_data['underruns']}")
    print(f"  ESP1 — OK:{stats_data['esp1_ok']}"
          f"  ERR:{stats_data['esp1_err']}"
          f"  Realign:{stats_data['esp1_realign']}")
    print(f"  ESP2 — OK:{stats_data['esp2_ok']}"
          f"  ERR:{stats_data['esp2_err']}"
          f"  Realign:{stats_data['esp2_realign']}")
    dbg("Monitor terminado")


if __name__ == "__main__":
    print("=== Monitor DAS 8 micrófonos — 2× ESP32-S3 ===\n")
    monitor()