"""
monitor_8LR.py — Sistema completo, 2x ESP32-S3 + SYNC.

Reconstruido en sept 2026: ESP_BAUD debe coincidir EXACTAMENTE con
Serial.begin()/Serial0.begin() del firmware (esp32_8micLR.txt usa
PROJECT_BAUD = 3,000,000) — ver Documentation.md sección 10 para el
detalle de la causa raíz encontrada (Serial y Serial0 comparten el mismo
periférico UART físico en este hardware).

Arquitectura:
  Hilo lector ESP1  ──┐
                       ├──► Hilo sincronizador ──► q_combinada (CHUNK, 8)
  Hilo lector ESP2  ──┘                                  │
                                                         ▼
                                                  Hilo reproductor
"""

import pyaudio
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
import serial
import serial.tools.list_ports
import json
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

# Puertos: se leen de las variables de entorno ESP1_PORT/ESP2_PORT si están
# definidas (así no hay que editar este archivo al cambiar de máquina —
# export ESP1_PORT=/dev/ttyACM1 ESP2_PORT=/dev/ttyACM3 en la Pi, por ejemplo).
# Si no están definidas, usa los defaults de Windows.
ESP1_PORT = os.environ.get("ESP1_PORT", "COM8")    # Master — Mics 1-4
ESP2_PORT = os.environ.get("ESP2_PORT", "COM6")    # Slave  — Mics 5-8

# SKIP_AUDIO=1 desactiva PyAudio/reproducción por completo — útil para
# diagnosticar si la reproducción de audio compite por CPU con los hilos
# de lectura serial (sospecha en Raspberry Pi con PipeWire inestable).
SKIP_AUDIO = os.environ.get("SKIP_AUDIO", "0") == "1"

ESP_BAUD  = 3000000   # DEBE coincidir con PROJECT_BAUD en el firmware
ESP_RATE  = 16000
CHUNK     = 512

GEOMETRIA_FILE = "geometria.json"
SALIDAS_DIR    = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "SALIDAS")

ESP1_MICS = [True, True, True, True]
ESP2_MICS = [True, True, True, True]

PAR_ACTIVO = 0

PAR_INFO = {
    0: (0, 1, "Mic1+Mic2  ESP1 Bus0  pines 4/5/6"),
    1: (2, 3, "Mic3+Mic4  ESP1 Bus1  pines 11/12/13"),
    2: (4, 5, "Mic5+Mic6  ESP2 Bus0  pines 4/5/6"),
    3: (6, 7, "Mic7+Mic8  ESP2 Bus1  pines 11/12/13"),
}

N_CANALES    = 4
N_TOTAL      = 8
CHUNK_BYTES  = CHUNK * N_CANALES * 2
LATENCY_MS   = CHUNK * 1000 // ESP_RATE
ID_ESPERADOS = [0, 1, 2, 3]
AUDIO_MASK   = np.int16(-4)

# Grupos de 4 muestras consecutivos que deben calzar con ID_ESPERADOS antes
# de aceptar un punto como alineado. Con solo 2 bits de ID, un grupo puede
# calzar por azar en audio real (~1/256) — cada grupo extra de verificación
# multiplica esa probabilidad por ~1/256 más (3 grupos => ~1/16.7M).
N_VERIF_SYNC = 3


# Patrón de N_VERIF_SYNC grupos [0,1,2,3] concatenados, en unidades de MUESTRA
# (no bytes) — ej. [0,1,2,3,0,1,2,3,0,1,2,3] para N_VERIF_SYNC=3.
_PATRON_MUESTRAS  = np.tile(np.array(ID_ESPERADOS, dtype=np.int16), N_VERIF_SYNC)
_LARGO_PATRON     = len(_PATRON_MUESTRAS)   # en muestras


def _buscar_offset_muestras(ids: np.ndarray):
    """Busca, vectorizado con numpy (sin loop de Python por candidato), el
    primer índice de MUESTRA donde N_VERIF_SYNC grupos consecutivos calzan
    con ID_ESPERADOS. Devuelve None si no hay match. `ids` ya debe traer
    aplicada la máscara (`raw & 0x03`).

    Un loop de Python probando offset por offset (con una llamada a numpy
    por candidato) resultó demasiado lento en Raspberry Pi cuando había
    muchos frames desalineados seguidos: el escaneo se comía la CPU,
    retrasaba la lectura del puerto serie, y eso causaba AÚN MÁS
    desalineamiento — un ciclo vicioso que no se veía en PC/laptop con más
    CPU disponible.
    """
    if len(ids) < _LARGO_PATRON:
        return None
    ventanas = sliding_window_view(ids, _LARGO_PATRON)
    coincide = np.all(ventanas == _PATRON_MUESTRAS, axis=1)
    if not coincide.any():
        return None
    return int(np.argmax(coincide))


def _buscar_offset_bytes(datos):
    """Busca el patrón en AMBAS paridades de byte (offset par e impar).

    BUG encontrado en producción: un solo byte perdido/agregado en el
    transporte desalinea el stream por una cantidad IMPAR de bytes.
    `np.frombuffer(datos, dtype=np.int16)` siempre reagrupa en pares fijos
    (0-1, 2-3, 4-5...) desde el byte 0 — una búsqueda que solo reordena
    DENTRO de ese array ya construido NUNCA puede recuperar un corrimiento
    impar, sin importar cuánto busque, porque el reagrupamiento en pares
    de 2 bytes queda fijo desde su creación. Confirmado con hex real: los
    bytes "tal cual" (paridad par) daban un patrón `[2,3,2,2]` sin sentido,
    pero desplazados 1 byte daban `[2,3,0,1]` — una rotación perfecta de
    `[0,1,2,3]`, es decir, alineación real de 1 byte, no corrupción.

    Devuelve el offset en BYTES desde el inicio de `datos`, o None.
    """
    b = np.frombuffer(bytes(datos), dtype=np.uint8)
    mejor = None
    for paridad in (0, 1):
        ids = (b[paridad::2] & 0x03).astype(np.int16)
        idx = _buscar_offset_muestras(ids)
        if idx is not None:
            offset = paridad + idx * 2
            if mejor is None or offset < mejor:
                mejor = offset
    return mejor

q_esp1      : queue.Queue[np.ndarray] = queue.Queue(maxsize=8)
q_esp2      : queue.Queue[np.ndarray] = queue.Queue(maxsize=8)
q_combinada : queue.Queue[np.ndarray] = queue.Queue(maxsize=8)

stop_evt = threading.Event()
par_lock = threading.Lock()

grabando_evt    = threading.Event()
frames_grabados : list[np.ndarray] = []
grab_lock       = threading.Lock()

stats_data = {
    "esp1_ok": 0, "esp1_err": 0, "esp1_realign": 0, "esp1_bytes": 0,
    "esp2_ok": 0, "esp2_err": 0, "esp2_realign": 0, "esp2_bytes": 0,
    "sync_ok": 0, "sync_drop": 0,
    "underruns": 0,
}
BYTES_ESPERADOS_POR_SEG = ESP_RATE * N_CANALES * 2   # 128,000 B/s por placa a 16kHz/4ch/16bit

## ── CARGA DE GEOMETRÍA ────────────────────────────────────────────────────────

def cargar_geometria() -> dict:
    try:
        with open(GEOMETRIA_FILE, "r", encoding="utf-8") as f:
            geo = json.load(f)
        dbg(f"Geometría cargada: {len(geo['micrófonos'])} micrófonos")
        return geo
    except FileNotFoundError:
        print(f"[WARN] {GEOMETRIA_FILE} no encontrado — DAS no disponible hasta crearlo")
        return None
    except json.JSONDecodeError as e:
        print(f"[ERROR] Error leyendo {GEOMETRIA_FILE}: {e}")
        return None

## ── CONEXIÓN ──────────────────────────────────────────────────────────────────

def conectar(port: str, label: str) -> serial.Serial:
    dbg(f"[{label}] Conectando a {port} @ {ESP_BAUD} baud...")
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
    buf = bytearray()
    deadline = time.time() + 30
    intentos = 0
    ultimo_log = time.time()

    while time.time() < deadline:
        try:
            dato = ser.read(4096)
            if dato:
                buf += dato
        except Exception as e:
            dbg(f"[{label}] Error durante sync: {e}")

        # Búsqueda vectorizada en AMBAS paridades de byte (ver
        # _buscar_offset_bytes) — un corrimiento de un número impar de
        # bytes nunca se recupera si solo se reordena dentro de un array
        # ya reagrupado en pares fijos.
        if len(buf) >= _LARGO_PATRON * 2 + 1:
            offset = _buscar_offset_bytes(buf)
            if offset is not None:
                dbg(f"[{label}] Sincronizado (offset byte={offset})")
                return bytearray(buf[offset + 8:])

            # Nada calzó en todo lo acumulado — conserva solo la cola
            # necesaria (cubriendo ambas paridades) por si un match cruza
            # el borde del próximo read.
            cola_bytes = _LARGO_PATRON * 2
            intentos += max(0, len(buf) - cola_bytes)
            if len(buf) > cola_bytes:
                buf = buf[-cola_bytes:]
            if DEBUG and time.time() - ultimo_log > 2:
                dbg(f"[{label}] Buscando... intentos={intentos}")
                ultimo_log = time.time()

    print(f"ERROR [{label}]: Sin sincronización en 30s")
    ser.close()
    return None

## ── HILO LECTOR ───────────────────────────────────────────────────────────────

def hilo_lector(ser: serial.Serial, resto: bytearray, label: str, out_q: queue.Queue,
                 mics_activos: list, k_ok: str, k_err: str, k_realign: str, k_bytes: str):

    resto = bytearray(resto)
    cnt = 0
    dbg(f"[{label}] Hilo lector iniciado")

    while not stop_evt.is_set():
        while len(resto) < CHUNK_BYTES and not stop_evt.is_set():
            try:
                dato = ser.read(min(4096, CHUNK_BYTES - len(resto)))
                if dato:
                    resto += dato
                    stats_data[k_bytes] += len(dato)
            except serial.SerialException:
                dbg(f"[{label}] SerialException — deteniendo")
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
            stats_data[k_err] += 1
            print(f"\n[WARN {label}] Desalineamiento frame {cnt} IDs={ids_inicio}")

            # Búsqueda vectorizada en ambas paridades de byte (igual que
            # sincronizar() — ver _buscar_offset_bytes para el porqué).
            offset = _buscar_offset_bytes(bloque)
            if offset is not None:
                resto = bytearray(bloque[offset + 8:]) + resto
                stats_data[k_realign] += 1
                dbg(f"[{label}] Realineado offset={offset}")
            else:
                dbg(f"[{label}] No se pudo realinear — descartando")
                dbg(f"[{label}] hex bloque (primeros 64B): {bloque[:64].hex(' ')}")
            continue

        stats_data[k_ok] += 1

        audio = (raw & AUDIO_MASK).reshape(CHUNK, N_CANALES).astype(np.float32) / 32768.0

        for i in range(N_CANALES):
            if not mics_activos[i]:
                audio[:, i] = 0.0

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
    cnt_sync = 0
    dbg("Hilo sincronizador iniciado")

    while not stop_evt.is_set():
        try:
            f1 = q_esp1.get(timeout=0.05)
        except queue.Empty:
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
            stats_data["sync_drop"] += 1
            continue

        frame_8ch = np.concatenate([f1, f2], axis=1)   # (CHUNK, 8)

        if grabando_evt.is_set():
            with grab_lock:
                frames_grabados.append(frame_8ch.copy())
        cnt_sync += 1
        stats_data["sync_ok"] += 1

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
            frame_8ch = q_combinada.get(timeout=0.1)
        except queue.Empty:
            stream.write(silencio.flatten().tobytes())
            stats_data["underruns"] += 1
            continue

        with par_lock:
            par = PAR_ACTIVO

        col_izq, col_der, _ = PAR_INFO[par]
        estereo = np.stack([frame_8ch[:, col_izq], frame_8ch[:, col_der]], axis=1)
        try:
            stream.write(estereo.flatten().tobytes())
        except OSError as e:
            dbg(f"OSError reproductor: {e}")
            break

    dbg("Hilo reproductor terminado")

## ── HILO ESTADÍSTICAS ─────────────────────────────────────────────────────────

def stats():
    prev_bytes1 = prev_bytes2 = 0
    prev_t = time.time()

    while not stop_evt.is_set():
        time.sleep(5)
        if stop_evt.is_set():
            break
        with par_lock:
            par = PAR_ACTIVO
        _, _, desc = PAR_INFO[par]

        now = time.time()
        dt = now - prev_t
        rate1 = (stats_data["esp1_bytes"] - prev_bytes1) / dt if dt > 0 else 0
        rate2 = (stats_data["esp2_bytes"] - prev_bytes2) / dt if dt > 0 else 0
        prev_bytes1, prev_bytes2, prev_t = stats_data["esp1_bytes"], stats_data["esp2_bytes"], now

        print(f"\n[STATS]"
              f"\n  Par activo   : {par} — {desc}"
              f"\n  Colas        : ESP1={q_esp1.qsize()}  ESP2={q_esp2.qsize()}  Combinada={q_combinada.qsize()}"
              f"\n  Sync OK/Drop : {stats_data['sync_ok']}  /  {stats_data['sync_drop']}"
              f"\n  Underruns    : {stats_data['underruns']}"
              f"\n  ESP1         : OK={stats_data['esp1_ok']}  ERR={stats_data['esp1_err']}  Realign={stats_data['esp1_realign']}"
              f"  tasa={rate1:.0f} B/s (esperado ~{BYTES_ESPERADOS_POR_SEG})"
              f"\n  ESP2         : OK={stats_data['esp2_ok']}  ERR={stats_data['esp2_err']}  Realign={stats_data['esp2_realign']}"
              f"  tasa={rate2:.0f} B/s (esperado ~{BYTES_ESPERADOS_POR_SEG})")

## ── HILO TECLADO ──────────────────────────────────────────────────────────────

def escuchar_teclado():
    global PAR_ACTIVO
    while not stop_evt.is_set():
        try:
            tecla = input().strip()
            if tecla in ("1", "2", "3", "4"):
                par = int(tecla) - 1
                with par_lock:
                    PAR_ACTIVO = par
                _, _, desc = PAR_INFO[par]
                print(f"\n  → Par {par}: {desc}\n")
            elif tecla.lower() == "g":
                if grabando_evt.is_set():
                    grabando_evt.clear()
                    with grab_lock:
                        if frames_grabados:
                            audio = np.concatenate(frames_grabados, axis=0)
                            os.makedirs(SALIDAS_DIR, exist_ok=True)
                            nombre = os.path.join(SALIDAS_DIR, f"grabacion_{int(time.time())}.npy")
                            np.save(nombre, audio)
                            print(f"\n  → Guardado: {nombre}  ({len(audio)/ESP_RATE:.1f}s)")
                            frames_grabados.clear()
                else:
                    with grab_lock:
                        frames_grabados.clear()
                    grabando_evt.set()
                    print("\n  → Grabando... ('g' de nuevo para guardar)\n")
            elif tecla.lower() == "q":
                stop_evt.set()
        except EOFError:
            break

## ── MAIN ──────────────────────────────────────────────────────────────────────

def monitor():
    global stream

    dbg(f"ESP1={ESP1_PORT}  ESP2={ESP2_PORT}  BAUD={ESP_BAUD}")

    geo = cargar_geometria()

    ser1 = conectar(ESP1_PORT, "ESP1")
    ser2 = conectar(ESP2_PORT, "ESP2")
    if ser1 is None or ser2 is None:
        print("ERROR: No se pudo conectar a uno o ambos ESP32.")
        sys.exit(1)

    resto1 = sincronizar(ser1, "ESP1")
    resto2 = sincronizar(ser2, "ESP2")
    if resto1 is None or resto2 is None:
        print("ERROR: Fallo de sincronización.")
        sys.exit(1)

    p = stream = None
    if not SKIP_AUDIO:
        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paFloat32, channels=2, rate=ESP_RATE,
                         output=True, frames_per_buffer=CHUNK)
    else:
        dbg("SKIP_AUDIO=1 — reproducción desactivada")

    print("\n" + "═" * 62)
    print("  Monitor Etapa 3 — 8 micrófonos, 2× ESP32-S3 + SYNC")
    print(f"  ESP1 (Master): {ESP1_PORT}   ESP2 (Slave): {ESP2_PORT}   Baud: {ESP_BAUD}")
    print(f"  Fs: {ESP_RATE} Hz  |  Latencia: ~{LATENCY_MS} ms")
    print(f"  Geometría: {'cargada ✓' if geo else 'no disponible'}")
    print("═" * 62)
    print(f"\n  Par activo: {PAR_INFO[PAR_ACTIVO][2]}")
    print("\n  Comandos: 1-4 cambiar par | g grabar/guardar | q salir\n")

    t_l1 = threading.Thread(target=hilo_lector, args=(ser1, resto1, "ESP1", q_esp1, ESP1_MICS,
                             "esp1_ok", "esp1_err", "esp1_realign", "esp1_bytes"), daemon=True)
    t_l2 = threading.Thread(target=hilo_lector, args=(ser2, resto2, "ESP2", q_esp2, ESP2_MICS,
                             "esp2_ok", "esp2_err", "esp2_realign", "esp2_bytes"), daemon=True)
    t_sync    = threading.Thread(target=hilo_sincronizador, daemon=True)
    t_audio   = threading.Thread(target=reproducir, daemon=True) if not SKIP_AUDIO else None
    t_stats   = threading.Thread(target=stats, daemon=True)
    t_teclado = threading.Thread(target=escuchar_teclado, daemon=True)

    t_l1.start(); t_l2.start(); t_sync.start()
    if t_audio:
        t_audio.start()
    t_stats.start(); t_teclado.start()

    t_teclado.join()

    print("\nDeteniendo...")
    stop_evt.set()
    for t in (t_l1, t_l2, t_sync, t_audio):
        if t:
            t.join(timeout=2)

    if stream:
        stream.stop_stream()
        stream.close()
        p.terminate()

    print("\n[RESUMEN FINAL]")
    print(f"  Frames sincronizados : {stats_data['sync_ok']}")
    print(f"  Frames descartados   : {stats_data['sync_drop']}")
    print(f"  Underruns            : {stats_data['underruns']}")
    print(f"  ESP1 — OK:{stats_data['esp1_ok']}  ERR:{stats_data['esp1_err']}  Realign:{stats_data['esp1_realign']}  bytes:{stats_data['esp1_bytes']}")
    print(f"  ESP2 — OK:{stats_data['esp2_ok']}  ERR:{stats_data['esp2_err']}  Realign:{stats_data['esp2_realign']}  bytes:{stats_data['esp2_bytes']}")


if __name__ == "__main__":
    print("=== Monitor Etapa 3 — 8 micrófonos, 2x ESP32-S3 ===\n")
    monitor()
