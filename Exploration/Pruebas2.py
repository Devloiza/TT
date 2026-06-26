"""
explorador_2mic.py
══════════════════════════════════════════════════════════════════════════════
Exploración de 2 micrófonos ICS-43434 / INMP441 conectados a un ESP32.

Funciones:
  - Recibe stream estéreo intercalado [Mic1, Mic2] por Serial
  - Compara lo que capta cada micrófono (forma de onda + FFT)
  - Beamforming delay-and-sum básico
  - Gráfica en tiempo real del ángulo estimado de la fuente sonora
  - Guarda grabación de los 2 canales + señal beamformed en WAV

Uso:
  python explorador_2mic.py

Dependencias:
  pip install pyserial pyaudio numpy matplotlib scipy soundfile
══════════════════════════════════════════════════════════════════════════════
"""

import serial
import pyaudio
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.animation as animation
import soundfile as sf
import threading
import queue
import time
import sys
import os

os.system('cls' if os.name == 'nt' else 'clear')

## ── CONFIG ────────────────────────────────────────────────────────────────────

ESP32_PORT    = "COM9"      # cambia al puerto real
ESP32_BAUD    = 921600
ESP32_RATE    = 16000       # debe coincidir con SAMPLE_RATE del .ino
CHUNK         = 512         # debe coincidir con CHUNK_SAMPLES del .ino
RECORD_SECS   = 10          # segundos a grabar (0 = solo monitorear)
OUTPUT_BASE   = "grabacion" # nombre base — se crean _mic1.wav, _mic2.wav, _beam.wav

# Geometría del arreglo
MIC_DIST_M    = 0.07        # distancia entre micrófonos en metros (10 cm)
SPEED_SOUND   = 343.0       # m/s a ~20°C

# Visualización
ANGLE_HISTORY = 100         # puntos de historial en la gráfica de ángulo
FFT_SIZE      = 1024        # puntos para la FFT en tiempo reall
PLOT_INTERVAL = 50          # ms entre actualizaciones de la gráfica

## ── CONSTANTES DERIVADAS ──────────────────────────────────────────────────────

CHUNK_BYTES   = CHUNK * 2 * 2          # 2 canales × 2 bytes (int16)
LATENCY_MS    = CHUNK * 1000 // ESP32_RATE
MAX_DELAY_S   = MIC_DIST_M / SPEED_SOUND          # retardo máximo posible
MAX_DELAY_SMP = MAX_DELAY_S * ESP32_RATE           # en muestras

## ── ESTADO COMPARTIDO ─────────────────────────────────────────────────────────

audio_q   : queue.Queue[np.ndarray] = queue.Queue(maxsize=30)
stop_evt  = threading.Event()

# Buffers para la visualización (actualizados por el hilo de procesamiento)
vis_lock  = threading.Lock()
vis_data  = {
    "mic1"     : np.zeros(CHUNK),
    "mic2"     : np.zeros(CHUNK),
    "beam"     : np.zeros(CHUNK),
    "fft_mic1" : np.zeros(FFT_SIZE // 2 + 1),
    "fft_mic2" : np.zeros(FFT_SIZE // 2 + 1),
    "fft_beam" : np.zeros(FFT_SIZE // 2 + 1),
    "angulo"   : 0.0,
    "angulos"  : np.zeros(ANGLE_HISTORY),
    "energia"  : 0.0,
}

# Acumuladores para guardar el WAV completo
rec_mic1  : list[np.ndarray] = []
rec_mic2  : list[np.ndarray] = []
rec_beam  : list[np.ndarray] = []

## ── BEAMFORMING DELAY-AND-SUM ─────────────────────────────────────────────────

def delay_and_sum(mic1: np.ndarray, mic2: np.ndarray,
                  delay_samples: float) -> np.ndarray:
    """
    Suma los dos micrófonos con un retardo fraccional aplicado al mic2.
    delay_samples > 0  →  la fuente está del lado del Mic1
    delay_samples < 0  →  la fuente está del lado del Mic2
    Usa interpolación lineal para retardos fraccionarios.
    """
    n = len(mic1)
    d = delay_samples

    if abs(d) < 1e-6:
        return (mic1 + mic2) * 0.5

    # Retardo entero + fracción
    d_int  = int(np.floor(abs(d)))
    d_frac = abs(d) - d_int

    # Índices con retardo
    idx       = np.arange(n)
    idx_delay = np.clip(idx - d_int,     0, n - 1)
    idx_next  = np.clip(idx - d_int - 1, 0, n - 1)

    if d >= 0:
        mic2_delayed = (1 - d_frac) * mic2[idx_delay] + d_frac * mic2[idx_next]
        return (mic1 + mic2_delayed) * 0.5
    else:
        mic1_delayed = (1 - d_frac) * mic1[idx_delay] + d_frac * mic1[idx_next]
        return (mic1_delayed + mic2) * 0.5


def estimar_tdoa(mic1: np.ndarray, mic2: np.ndarray) -> float:
    """
    Estima el TDOA (Time Difference Of Arrival) entre los dos micrófonos
    usando GCC (Generalized Cross-Correlation).
    Devuelve el retardo en muestras (positivo = fuente más cerca de Mic1).
    """
    n     = len(mic1) + len(mic2) - 1
    n_fft = int(2 ** np.ceil(np.log2(n)))   # potencia de 2 para la FFT

    M1 = np.fft.rfft(mic1, n=n_fft)
    M2 = np.fft.rfft(mic2, n=n_fft)

    # GCC-PHAT: normaliza por la magnitud para dar más peso a la fase
    denom = np.abs(M1 * np.conj(M2))
    denom = np.where(denom < 1e-10, 1e-10, denom)
    gcc   = np.fft.irfft(M1 * np.conj(M2) / denom)

    # Buscar el máximo dentro del rango de retardo físicamente posible
    max_lag = int(np.ceil(MAX_DELAY_SMP)) + 1
    gcc_sym = np.concatenate([gcc[-max_lag:], gcc[:max_lag + 1]])
    lags    = np.arange(-max_lag, max_lag + 1)

    mejor   = np.argmax(gcc_sym)
    tdoa    = float(lags[mejor])
    return tdoa


def tdoa_a_angulo(tdoa_samples: float) -> float:
    """
    Convierte TDOA en muestras a ángulo de llegada en grados.
    0°   = frente al arreglo (fuente equidistante)
    +90° = lado Mic1
    -90° = lado Mic2
    """
    tdoa_s  = tdoa_samples / ESP32_RATE
    # Clamp para evitar acos fuera de [-1, 1]
    arg     = np.clip(tdoa_s * SPEED_SOUND / MIC_DIST_M, -1.0, 1.0)
    angulo  = np.degrees(np.arcsin(arg))
    return angulo


def fft_magnitud(signal: np.ndarray) -> np.ndarray:
    """FFT con ventana Hanning, devuelve magnitud normalizada."""
    n   = min(len(signal), FFT_SIZE)
    win = np.hanning(n)
    sig = signal[:n] * win
    mag = np.abs(np.fft.rfft(sig, n=FFT_SIZE)) / FFT_SIZE
    return mag

## ── HILO DE RECEPCIÓN SERIAL ──────────────────────────────────────────────────

def hilo_serial():
    print(f"Conectando a {ESP32_PORT} @ {ESP32_BAUD} baud...")
    try:
        ser = serial.Serial(ESP32_PORT, ESP32_BAUD, timeout=5)
    except serial.SerialException as e:
        print(f"ERROR abriendo {ESP32_PORT}: {e}")
        stop_evt.set()
        return

    # Esperar START
    print("Esperando START del ESP32...")
    buf      = b""
    deadline = time.time() + 10
    while b"START" not in buf:
        buf += ser.read(64)
        if time.time() > deadline:
            print("ERROR: No llegó START.")
            stop_evt.set()
            ser.close()
            return

    resto = bytearray(buf[buf.index(b"START") + 5:])
    print("START recibido. Capturando audio...\n")

    while not stop_evt.is_set():
        while len(resto) < CHUNK_BYTES and not stop_evt.is_set():
            try:
                resto += ser.read(min(2048, CHUNK_BYTES - len(resto)))
            except serial.SerialException:
                stop_evt.set()
                return

        if stop_evt.is_set():
            break

        bloque = bytes(resto[:CHUNK_BYTES])
        resto  = resto[CHUNK_BYTES:]

        # Parsear: (CHUNK, 2) → col 0 = Mic1, col 1 = Mic2
        frame = np.frombuffer(bloque, dtype=np.int16) \
                  .reshape(CHUNK, 2) \
                  .astype(np.float32) / 32768.0

        try:
            audio_q.put_nowait(frame)
        except queue.Full:
            pass

    ser.close()

## ── HILO DE PROCESAMIENTO ─────────────────────────────────────────────────────

def hilo_procesamiento():
    """
    Consume frames de audio_q, calcula TDOA, beamforming y actualiza vis_data.
    También acumula los canales para guardar el WAV al final.
    """
    p      = pyaudio.PyAudio()
    stream = p.open(
        format            = pyaudio.paFloat32,
        channels          = 1,               # reproducimos la señal beamformed (mono)
        rate              = ESP32_RATE,
        output            = True,
        frames_per_buffer = CHUNK,
    )

    t_inicio   = time.time()
    grabando   = RECORD_SECS > 0
    underruns  = 0
    silencio   = np.zeros(CHUNK, dtype=np.float32)

    while not stop_evt.is_set():
        try:
            frame = audio_q.get(timeout=0.1)   # shape (CHUNK, 2)
        except queue.Empty:
            stream.write(silencio.tobytes())
            underruns += 1
            continue

        mic1 = frame[:, 0]
        mic2 = frame[:, 1]

        # ── TDOA y ángulo ────────────────────────────────────────────────────
        tdoa   = estimar_tdoa(mic1, mic2)
        angulo = tdoa_a_angulo(tdoa)

        # ── Beamforming ──────────────────────────────────────────────────────
        beam   = delay_and_sum(mic1, mic2, tdoa)

        # ── Reproducir señal beamformed ──────────────────────────────────────
        try:
            stream.write(beam.astype(np.float32).tobytes())
        except OSError:
            pass

        # ── Acumular para WAV ────────────────────────────────────────────────
        if grabando:
            rec_mic1.append(mic1.copy())
            rec_mic2.append(mic2.copy())
            rec_beam.append(beam.copy())
            if time.time() - t_inicio >= RECORD_SECS:
                grabando = False
                print(f"\n[grabación completada: {RECORD_SECS}s]")

        # ── Actualizar visualización ─────────────────────────────────────────
        with vis_lock:
            vis_data["mic1"]      = mic1.copy()
            vis_data["mic2"]      = mic2.copy()
            vis_data["beam"]      = beam.copy()
            vis_data["fft_mic1"]  = fft_magnitud(mic1)
            vis_data["fft_mic2"]  = fft_magnitud(mic2)
            vis_data["fft_beam"]  = fft_magnitud(beam)
            vis_data["angulo"]    = angulo
            vis_data["angulos"]   = np.roll(vis_data["angulos"], -1)
            vis_data["angulos"][-1] = angulo
            vis_data["energia"]   = float(np.sqrt(np.mean(beam**2)))

    stream.stop_stream()
    stream.close()
    p.terminate()
    if underruns:
        print(f"Underruns de audio: {underruns}")

## ── GUARDAR WAV ───────────────────────────────────────────────────────────────

def guardar_wavs():
    if not rec_mic1:
        return

    datos_mic1 = np.concatenate(rec_mic1)
    datos_mic2 = np.concatenate(rec_mic2)
    datos_beam = np.concatenate(rec_beam)

    sf.write(f"{OUTPUT_BASE}_mic1.wav", datos_mic1, ESP32_RATE, subtype="PCM_16")
    sf.write(f"{OUTPUT_BASE}_mic2.wav", datos_mic2, ESP32_RATE, subtype="PCM_16")
    sf.write(f"{OUTPUT_BASE}_beam.wav", datos_beam, ESP32_RATE, subtype="PCM_16")

    dur = len(datos_mic1) / ESP32_RATE
    print(f"WAVs guardados ({dur:.1f}s):")
    print(f"  {OUTPUT_BASE}_mic1.wav  — Micrófono 1 (L/R=GND)")
    print(f"  {OUTPUT_BASE}_mic2.wav  — Micrófono 2 (L/R=VCC)")
    print(f"  {OUTPUT_BASE}_beam.wav  — Señal beamformed")

## ── VISUALIZACIÓN EN TIEMPO REAL ──────────────────────────────────────────────

def iniciar_visualizacion():
    freqs = np.fft.rfftfreq(FFT_SIZE, d=1.0 / ESP32_RATE)
    t_eje = np.linspace(0, CHUNK / ESP32_RATE * 1000, CHUNK)   # en ms
    hist_x = np.arange(ANGLE_HISTORY)

    # ── Layout ───────────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(15, 9), facecolor="#0d0d0d")
    fig.suptitle("Explorador 2 micrófonos — Beamforming en tiempo real",
                 color="white", fontsize=13, fontweight="bold")

    gs = gridspec.GridSpec(3, 3, figure=fig,
                           hspace=0.45, wspace=0.35,
                           left=0.07, right=0.97,
                           top=0.92, bottom=0.07)

    COLOR_MIC1  = "#00e5ff"
    COLOR_MIC2  = "#ff4081"
    COLOR_BEAM  = "#69f0ae"
    COLOR_ANGLE = "#ffeb3b"
    BG          = "#0d0d0d"
    GRID_C      = "#222222"

    def ax_style(ax, title):
        ax.set_facecolor(BG)
        ax.set_title(title, color="white", fontsize=9, pad=4)
        ax.tick_params(colors="#888888", labelsize=7)
        for sp in ax.spines.values():
            sp.set_edgecolor("#333333")
        ax.grid(True, color=GRID_C, linewidth=0.5)

    # Fila 0 — formas de onda
    ax_w1 = fig.add_subplot(gs[0, 0])
    ax_w2 = fig.add_subplot(gs[0, 1])
    ax_wb = fig.add_subplot(gs[0, 2])
    ax_style(ax_w1, "Forma de onda — Mic 1 (L/R=GND)")
    ax_style(ax_w2, "Forma de onda — Mic 2 (L/R=VCC)")
    ax_style(ax_wb, "Forma de onda — Beamformed")
    for ax in (ax_w1, ax_w2, ax_wb):
        ax.set_xlim(0, CHUNK / ESP32_RATE * 1000)
        ax.set_ylim(-1, 1)
        ax.set_xlabel("Tiempo (ms)", color="#888888", fontsize=7)
        ax.set_ylabel("Amplitud", color="#888888", fontsize=7)

    ln_w1, = ax_w1.plot(t_eje, np.zeros(CHUNK), color=COLOR_MIC1, lw=0.8)
    ln_w2, = ax_w2.plot(t_eje, np.zeros(CHUNK), color=COLOR_MIC2, lw=0.8)
    ln_wb, = ax_wb.plot(t_eje, np.zeros(CHUNK), color=COLOR_BEAM, lw=0.8)

    # Fila 1 — FFTs
    ax_f1 = fig.add_subplot(gs[1, 0])
    ax_f2 = fig.add_subplot(gs[1, 1])
    ax_fb = fig.add_subplot(gs[1, 2])
    ax_style(ax_f1, "Espectro — Mic 1")
    ax_style(ax_f2, "Espectro — Mic 2")
    ax_style(ax_fb, "Espectro — Beamformed")
    for ax in (ax_f1, ax_f2, ax_fb):
        ax.set_xlim(0, ESP32_RATE // 2)
        ax.set_ylim(0, 0.05)
        ax.set_xlabel("Frecuencia (Hz)", color="#888888", fontsize=7)
        ax.set_ylabel("Magnitud", color="#888888", fontsize=7)

    ln_f1, = ax_f1.plot(freqs, np.zeros(len(freqs)), color=COLOR_MIC1, lw=0.8)
    ln_f2, = ax_f2.plot(freqs, np.zeros(len(freqs)), color=COLOR_MIC2, lw=0.8)
    ln_fb, = ax_fb.plot(freqs, np.zeros(len(freqs)), color=COLOR_BEAM, lw=0.8)

    # Fila 2 izquierda — historial de ángulos
    ax_ha = fig.add_subplot(gs[2, :2])
    ax_style(ax_ha, "Ángulo estimado de la fuente sonora (historial)")
    ax_ha.set_xlim(0, ANGLE_HISTORY)
    ax_ha.set_ylim(-95, 95)
    ax_ha.set_xlabel("Frames recientes →", color="#888888", fontsize=7)
    ax_ha.set_ylabel("Ángulo (°)", color="#888888", fontsize=7)
    ax_ha.axhline(y=0,   color="#444444", lw=0.8, linestyle="--")
    ax_ha.axhline(y=90,  color="#555555", lw=0.5, linestyle=":")
    ax_ha.axhline(y=-90, color="#555555", lw=0.5, linestyle=":")
    ax_ha.text(2,  92, "Mic 1 →",  color="#888888", fontsize=7)
    ax_ha.text(2, -94, "← Mic 2",  color="#888888", fontsize=7)
    ln_ang, = ax_ha.plot(hist_x, np.zeros(ANGLE_HISTORY),
                         color=COLOR_ANGLE, lw=1.2)

    # Fila 2 derecha — indicador polar del ángulo actual
    ax_pol = fig.add_subplot(gs[2, 2], projection="polar")
    ax_pol.set_facecolor(BG)
    ax_pol.set_title("Dirección actual", color="white", fontsize=9, pad=10)
    ax_pol.tick_params(colors="#888888", labelsize=7)
    ax_pol.set_theta_zero_location("N")   # 0° arriba (frente)
    ax_pol.set_theta_direction(-1)         # sentido horario
    ax_pol.set_ylim(0, 1)
    ax_pol.set_yticks([])
    ax_pol.set_xticks(np.radians([0, 45, 90, 135, 180, 225, 270, 315]))
    ax_pol.set_xticklabels(
        ["0°\n(frente)", "45°", "90°\n(Mic1)", "135°",
         "180°", "225°", "270°\n(Mic2)", "315°"],
        color="#888888", fontsize=6
    )
    # Dibujar los dos micrófonos como puntos de referencia
    ax_pol.plot([np.radians(90)],  [0.85], "o",
                color=COLOR_MIC1, markersize=6, label="Mic1")
    ax_pol.plot([np.radians(270)], [0.85], "o",
                color=COLOR_MIC2, markersize=6, label="Mic2")
    ax_pol.legend(loc="lower right", fontsize=6,
                  labelcolor="white", facecolor="#1a1a1a", edgecolor="#333")

    # Flecha de dirección (se actualiza en cada frame)
    arrow_pol = ax_pol.annotate(
        "", xy=(0, 0.75), xytext=(0, 0),
        arrowprops=dict(arrowstyle="->", color=COLOR_ANGLE, lw=2)
    )

    # Texto del ángulo actual
    txt_angulo = ax_ha.text(
        ANGLE_HISTORY * 0.75, 78, "0.0°",
        color=COLOR_ANGLE, fontsize=11, fontweight="bold"
    )

    # Texto de energía
    txt_energia = fig.text(
        0.5, 0.01,
        "RMS: 0.000",
        color="#888888", fontsize=8, ha="center"
    )

    # ── Función de actualización de la animación ──────────────────────────────
    def update(_frame):
        with vis_lock:
            m1   = vis_data["mic1"].copy()
            m2   = vis_data["mic2"].copy()
            bm   = vis_data["beam"].copy()
            f1   = vis_data["fft_mic1"].copy()
            f2   = vis_data["fft_mic2"].copy()
            fb   = vis_data["fft_beam"].copy()
            ang  = vis_data["angulo"]
            angs = vis_data["angulos"].copy()
            rms  = vis_data["energia"]

        # Formas de onda
        ln_w1.set_ydata(m1)
        ln_w2.set_ydata(m2)
        ln_wb.set_ydata(bm)

        # Auto-escala suave de los ejes Y de onda
        for ax, sig in ((ax_w1, m1), (ax_w2, m2), (ax_wb, bm)):
            pico = max(np.max(np.abs(sig)) * 1.2, 0.01)
            ax.set_ylim(-pico, pico)

        # FFTs
        ln_f1.set_ydata(f1)
        ln_f2.set_ydata(f2)
        ln_fb.set_ydata(fb)

        # Auto-escala suave de los ejes Y de FFT
        for ax, ff in ((ax_f1, f1), (ax_f2, f2), (ax_fb, fb)):
            tope = max(np.max(ff) * 1.3, 0.001)
            ax.set_ylim(0, tope)

        # Historial de ángulos
        ln_ang.set_ydata(angs)

        # Texto del ángulo
        txt_angulo.set_text(f"{ang:+.1f}°")

        # Flecha polar
        ang_rad = np.radians(ang)
        arrow_pol.xy       = (ang_rad, 0.75)
        arrow_pol.xytext   = (ang_rad, 0.0)
        arrow_pol.arrowprops["color"] = COLOR_ANGLE

        # Energía
        txt_energia.set_text(f"RMS señal beamformed: {rms:.4f}")

        return (ln_w1, ln_w2, ln_wb,
                ln_f1, ln_f2, ln_fb,
                ln_ang, txt_angulo, txt_energia)

    ani = animation.FuncAnimation(
        fig, update,
        interval=PLOT_INTERVAL,
        blit=False,
        cache_frame_data=False,
    )

    plt.show()
    return ani   # mantener referencia para evitar que el GC lo elimine

## ── MAIN ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("═" * 58)
    print("  Explorador 2 micrófonos — Beamforming + Ángulo")
    print(f"  Puerto  : {ESP32_PORT}  @  {ESP32_BAUD} baud")
    print(f"  Fs      : {ESP32_RATE} Hz  |  Chunk: {CHUNK} muestras")
    print(f"  Dist.   : {MIC_DIST_M*100:.0f} cm  |  Max delay: "
          f"{MAX_DELAY_SMP:.1f} muestras")
    if RECORD_SECS > 0:
        print(f"  Grabará : {RECORD_SECS}s → {OUTPUT_BASE}_mic1/mic2/beam.wav")
    print("═" * 58)

    # Arrancar hilos de fondo
    t_serial = threading.Thread(target=hilo_serial,        daemon=True)
    t_proc   = threading.Thread(target=hilo_procesamiento, daemon=True)

    t_serial.start()
    t_proc.start()

    # Pequeña espera para que el serial arranque antes de abrir la gráfica
    time.sleep(2)

    if stop_evt.is_set():
        print("No se pudo conectar al ESP32. Verifica el puerto.")
        sys.exit(1)

    print("Abre la ventana de gráficas. Ciérrala para terminar.\n")

    try:
        ani = iniciar_visualizacion()   # bloquea hasta cerrar la ventana
    except KeyboardInterrupt:
        pass
    finally:
        stop_evt.set()
        t_serial.join(timeout=2)
        t_proc.join(timeout=2)
        guardar_wavs()
        print("\nListo.")