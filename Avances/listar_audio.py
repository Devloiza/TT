"""
listar_audio.py — Lista los dispositivos de salida de audio que ve PyAudio,
con su índice. Úsalo para encontrar el índice del dispositivo USB y pasarlo
a monitor_8LR.py vía la variable de entorno AUDIO_DEVICE_INDEX.

Uso:
    python listar_audio.py
"""

import pyaudio

p = pyaudio.PyAudio()
print(f"\n{'Índice':<8}{'Canales salida':<16}Nombre")
print("-" * 60)
for i in range(p.get_device_count()):
    info = p.get_device_info_by_index(i)
    if info["maxOutputChannels"] > 0:
        print(f"{i:<8}{info['maxOutputChannels']:<16}{info['name']}")

print(f"\nDefault de PyAudio: índice {p.get_default_output_device_info()['index']} "
      f"— {p.get_default_output_device_info()['name']}")
p.terminate()
