import pyaudio
import numpy as np
import matplotlib.pyplot as plt
import wave
import time
import sys
import os
from filtros_fourier import pasa_bajos, pasa_altos, pasa_banda, notch
from filtros_fourier import aplicar_filtro, graficar_filtros, guardar_filtros

try:
    import serial
    _ESP32_DISPONIBLE = True
except ImportError:
    _ESP32_DISPONIBLE = False

os.system('cls')

## ── CONFIGURACIÓN PC ──────────────────────────────────────────────────────────

SAMPLE_RATE   = 44100
CHANNELS      = 1
FORMAT        = pyaudio.paInt16
CHUNK         = int(2**8)
RECORD_SECS   = 10
OUTPUT_FILE   = r"audio.wav"

## ── CONFIGURACIÓN ESP32 ───────────────────────────────────────────────────────

ESP32_PORT    = "COM5"
ESP32_BAUD    = 921600
ESP32_RATE    = 30000    # Hz que configura el ADC del ESP32
ESP32_DTYPE   = np.int16
ESP32_BYTES   = 2        # bytes por muestra (int16)

## ── DISPOSITIVOS DE AUDIO ─────────────────────────────────────────────────────

def listar_dispositivos():
    p = pyaudio.PyAudio()
    print("\n=== Dispositivos de audio disponibles ===")
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        tipo = []
        if info["maxInputChannels"] > 0:
            tipo.append("ENTRADA")
        if info["maxOutputChannels"] > 0:
            tipo.append("SALIDA")
        print(f"  [{i}] {info['name']}  |  {' / '.join(tipo)}"
              f"  |  {int(info['defaultSampleRate'])} Hz")
    p.terminate()

## ── GRABAR DESDE MICRÓFONO PC ─────────────────────────────────────────────────

def grabar_audio(duracion=RECORD_SECS) -> tuple[np.ndarray, int]:
    """Graba audio del micrófono del PC. Devuelve (array int16, sample_rate)."""
    p = pyaudio.PyAudio()
    stream = p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=SAMPLE_RATE,
        input=True,
        frames_per_buffer=CHUNK
    )

    print(f"\nGrabando {duracion} segundos... habla ahora!")
    frames = []
    total_chunks = int(SAMPLE_RATE / CHUNK * duracion)

    for i in range(total_chunks):
        data = stream.read(CHUNK)
        frames.append(data)
        progreso = int((i + 1) / total_chunks * 20)
        print(f"\r  [{'█' * progreso}{'░' * (20 - progreso)}]", end="", flush=True)

    print("\nGrabación terminada.")
    stream.stop_stream()
    stream.close()
    p.terminate()

    audio_np = np.frombuffer(b"".join(frames), dtype=np.int16)
    return audio_np, SAMPLE_RATE

## ── GRABAR DESDE ESP32 ────────────────────────────────────────────────────────

def grabar_audio_esp32(duracion=RECORD_SECS) -> tuple[np.ndarray, int]:
    """
    Recibe audio del ESP32 vía serial.
    El ESP32 debe enviar 'START' y luego muestras int16 little-endian en bruto.
    Devuelve (array int16, sample_rate).
    """
    if not _ESP32_DISPONIBLE:
        print("ERROR: Instala 'pyserial', 'sounddevice' y 'soundfile' para usar el ESP32.")
        sys.exit(1)

    needed = duracion * ESP32_RATE * ESP32_BYTES

    print(f"\nConectando a {ESP32_PORT} @ {ESP32_BAUD} baud...")
    ser = serial.Serial(ESP32_PORT, ESP32_BAUD, timeout=5)

    print("Esperando señal START del ESP32...")
    buf = b""
    deadline = time.time() + 10
    while b"START" not in buf:
        buf += ser.read(64)
        if time.time() > deadline:
            ser.close()
            print("ERROR: No se recibió señal START. Verifica el puerto y el baudrate.")
            sys.exit(1)

    # Descartar bytes anteriores al marcador
    buf = buf[buf.index(b"START") + 5:]

    print(f"Grabando {duracion} segundos desde ESP32... habla al micrófono!")
    raw_data = buf

    while len(raw_data) < needed:
        chunk = ser.read(min(1024, needed - len(raw_data)))
        raw_data += chunk
        elapsed = len(raw_data) / (ESP32_BYTES * ESP32_RATE)
        print(f"  {elapsed:.1f} / {duracion} seg", end="\r")

    ser.close()
    print("\nRecepción completa.")

    samples = np.frombuffer(raw_data[:needed], dtype=ESP32_DTYPE)
    return samples, ESP32_RATE

## ── GUARDAR WAV ───────────────────────────────────────────────────────────────

def guardar_wav(audio_np: np.ndarray, nombre_archivo=OUTPUT_FILE, sample_rate=SAMPLE_RATE):
    """Guarda un array NumPy int16 como archivo WAV."""
    p = pyaudio.PyAudio()
    with wave.open(nombre_archivo, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(sample_rate)
        wf.writeframes(audio_np.tobytes())
    p.terminate()
    print(f"Audio guardado en: {nombre_archivo}")

## ── LEER WAV ──────────────────────────────────────────────────────────────────

def leer_wav(nombre_archivo=OUTPUT_FILE) -> tuple[np.ndarray, int]:
    """Lee un archivo WAV. Devuelve (array int16, sample_rate)."""
    with wave.open(nombre_archivo, "rb") as wf:
        canales  = wf.getnchannels()
        ancho    = wf.getsampwidth()
        tasa     = wf.getframerate()
        raw_data = wf.readframes(wf.getnframes())

    audio_np = np.frombuffer(raw_data, dtype=np.int16)
    print(f"\nArchivo leído: {nombre_archivo}")
    print(f"   Canales: {canales} | Bits: {ancho*8} | Tasa: {tasa} Hz | Muestras: {len(audio_np)}")
    return audio_np, tasa

## ── MANIPULACIÓN DE SEÑAL ─────────────────────────────────────────────────────

def manipular_audio(audio_np: np.ndarray, Only_OG:bool = False) -> dict:
    audio_f = audio_np.copy()
    if Only_OG:
        return { "original": audio_f}

    amplificado = (audio_f * 5.0).astype(np.int16)
    invertido   = -audio_f
    cortado     = audio_f.copy()
    cortado[: len(cortado) // 2] = 0
    rapido      = audio_f[::2]

    print("\nManipulaciones aplicadas:")
    print(f"   Original    — {len(audio_f)} muestras")
    print(f"   Amplificado — x5")
    print(f"   Invertido   — fase invertida")
    print(f"   Cortado     — primera mitad en silencio")
    print(f"   Rápido      — {len(rapido)} muestras (velocidad x2)")

    return {
        "original":    audio_f,
        "amplificado": amplificado,
        "invertido":   invertido,
        "cortado":     cortado,
        "rapido":      rapido,
    }

## ── GRAFICAR ──────────────────────────────────────────────────────────────────

def graficar_audio(audio_np: np.ndarray, variantes: dict, sample_rate=SAMPLE_RATE):
    audio_f = audio_np.astype(np.float32) / 32768.0
    tiempo  = np.linspace(0, len(audio_f) / sample_rate, num=len(audio_f))

    fig, axes = plt.subplots(2, 2, figsize=(14, 8))
    fig.suptitle("PyAudio + NumPy — Análisis de audio", fontsize=14, fontweight="bold")

    ax = axes[0, 0]
    ax.plot(tiempo, audio_f, color="#2196F3", linewidth=0.5)
    ax.set_title("Forma de onda original")
    ax.set_xlabel("Tiempo (s)")
    ax.set_ylabel("Amplitud")
    ax.grid(True, alpha=0.3)

    ax = axes[0, 1]
    for nombre, variante in variantes.items():
        t_var = np.linspace(0, len(variante) / sample_rate, num=len(variante))
        ax.plot(t_var, variante, label=nombre, linewidth=0.5, alpha=0.8)
    ax.set_title("Comparación de variantes")
    ax.set_xlabel("Tiempo (s)")
    ax.set_ylabel("Amplitud")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    ax = axes[1, 0]
    N     = len(audio_f)
    fft_v = np.fft.rfft(audio_f)
    freqs = np.fft.rfftfreq(N, d=1.0 / sample_rate)
    ax.plot(freqs, np.abs(fft_v), color="#E91E63", linewidth=0.5)
    ax.set_title("Espectro de frecuencias (FFT)")
    ax.set_xlabel("Frecuencia (Hz)")
    ax.set_ylabel("Magnitud")
    ax.set_xlim(0, sample_rate // 2)
    ax.grid(True, alpha=0.3)

    ax = axes[1, 1]
    ax.specgram(audio_f, NFFT=1024, Fs=sample_rate, noverlap=512, cmap="inferno")
    ax.set_title("Espectrograma")
    ax.set_xlabel("Tiempo (s)")
    ax.set_ylabel("Frecuencia (Hz)")

    plt.tight_layout()
    plt.savefig("analisis_audio.png", dpi=150, bbox_inches="tight")
    print("\nGráficas guardadas en: analisis_audio.png")
    plt.show()

## ── REPRODUCIR ────────────────────────────────────────────────────────────────

def reproducir_audio(audio_np: np.ndarray, sample_rate=SAMPLE_RATE):
    """Reproduce un array NumPy int16 por los altavoces."""
    p = pyaudio.PyAudio()
    stream = p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=sample_rate,
        output=True
    )
    for i in range(0, len(audio_np), CHUNK):
        stream.write(audio_np[i: i + CHUNK].tobytes())
    stream.stop_stream()
    stream.close()
    p.terminate()

## ── MAIN ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":

    print("=== Fuente de audio ===")
    print("  1. Micrófono del PC")
    print("  2. Micrófono del ESP32 (serial)")
    print("  3. Cargar archivo WAV existente")
    opcion = input("Elige una opción [1/2/3]: ").strip()

    if opcion == "1":
        audio, rate = grabar_audio(duracion=RECORD_SECS)
        guardar_wav(audio, OUTPUT_FILE, sample_rate=rate)

    elif opcion == "2":
        audio, rate = grabar_audio_esp32(duracion=RECORD_SECS)
        guardar_wav(audio, OUTPUT_FILE, sample_rate=rate)

    elif opcion == "3":
        audio, rate = leer_wav(OUTPUT_FILE)

    else:
        print("Opción no válida.")
        sys.exit(1)

    # Pipeline de análisis (igual para cualquier fuente)
    variantes = manipular_audio(audio, Only_OG=True)
    graficar_audio(audio, variantes, sample_rate=rate)

    for nombre, variante in variantes.items():
        print(f'----- {nombre} -----')
        reproducir_audio(variante, sample_rate=rate)

    freqs = np.fft.rfftfreq(len(audio), d=1.0 / rate)

    resultados = {
        "pasa_bajos": aplicar_filtro(audio, pasa_bajos(freqs, 1000)),
        "pasa_altos": aplicar_filtro(audio, pasa_altos(freqs, 500)),
        "pasa_banda": aplicar_filtro(audio, pasa_banda(freqs, 20, 2000)),
        "notch 60Hz": aplicar_filtro(audio, notch(freqs, 60)),
    }

    for nombre, resultado in resultados.items():
        print(f'----- {nombre} -----')
        reproducir_audio(resultado, sample_rate=rate)

    graficar_filtros(audio, resultados, rate)
    guardar_filtros(variantes, rate)
    guardar_filtros(resultados, rate)
