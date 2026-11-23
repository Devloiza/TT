"""Configura el audio de las sesiones de voz (Obj. 3) una sola vez por máquina.

Hecho por Claude con la especificación del autor (2026-11-22). Es una utilidad de adquisición, no análisis del TT.

Hace las mismas pruebas que antes pedía presentador_frases.py al inicio de cada sesión:
  1. Habla: dispositivo de entrada, prueba de nivel de 3 s por canal y canal del micrófono (AT2020).
  2. Escucha: salida de los audífonos y tono de prueba (o ninguna: las indicaciones solo se muestran).
Guarda la elección en config_audio.json, junto a este archivo. Desde entonces presentador_frases.py arranca sin
preguntar nada de audio. Busca los dispositivos por nombre y API, porque los índices cambian al conectar o
desconectar aparatos. Si alguno ya no aparece, avisa y hay que correr esto de nuevo.

Uso:  python Exploration/Prueba_BD/configurar_audio.py   (opciones: --dispositivo N y --salida N, de --listar)
Ver los dispositivos:  python Exploration/Prueba_BD/presentador_frases.py --listar
"""
import argparse
import datetime
import json

import presentador_frases as pf


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--dispositivo", type=int, default=None, help="índice de la entrada (si no, se elige aquí)")
    p.add_argument("--salida", type=int, default=None, help="índice de la salida de los audífonos")
    a = p.parse_args()
    if pf.ARCHIVO_CONFIG.exists():
        anterior = json.loads(pf.ARCHIVO_CONFIG.read_text(encoding="utf-8"))
        print(f"Configuración actual ({anterior.get('fecha', '')}): entrada «{anterior['entrada']['nombre']}», "
              f"canal {anterior['entrada']['canal']}. Se va a reemplazar.")
    print("\n=== 1. Habla: micrófono ===")
    entrada = pf.elegir_entrada(a.dispositivo)
    print("\n=== 2. Escucha: audífonos ===")
    salida = pf.elegir_salida(a.salida)
    config = {"fecha": datetime.datetime.now().isoformat(timespec="seconds"), "entrada": entrada, "salida": salida}
    pf.ARCHIVO_CONFIG.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nGuardado en {pf.ARCHIVO_CONFIG}. Ya puedes correr presentador_frases.py.")


if __name__ == "__main__":
    main()
