"""Proceso aparte que carga el modelo de Piper UNA sola vez y sintetiza muchas
frases sin pagar otra vez el costo de arrancar el interprete + cargar el modelo
en cada una. Medido real en este entorno: un `python -m piper` por frase tardaba
~3 s por frase (sobre todo cargar el modelo de 63 MB) -- muy por encima del
presupuesto de latencia de Dentia (docs/05_ASISTENTE_DENTIA_VOZ_CONVERSACIONAL.md
sec. 5.1: < 1.5 s en la ruta rapida). Este script se queda vivo y resuelve cada
frase nueva en el orden de decimas de segundo.

Es el UNICO archivo de este proyecto que hace `import piper` -- y aun asi sigue
siendo un PROCESO APARTE del backend (ver tts.py, que lo arranca con
`subprocess_exec`, nunca con un `import`): el motor Piper activo es GPL-3.0
desde oct. 2025 (ver comentario en tts.py y requirements.txt), y este sistema se
distribuye instalado en cada clinica, asi que importar `piper` dentro del mismo
proceso del backend si seria incorporar esa licencia al programa que lo llama.

Protocolo:
  arranque: escribe b"READY\n" en stdout en cuanto el modelo esta cargado.
  entrada:  una linea de texto UTF-8 (sin salto de linea) por stdin, por frase
            a sintetizar.
  salida:   un frame binario por respuesta: 4 bytes big-endian con la longitud,
            seguidos de exactamente esa cantidad de bytes de PCM16 mono crudo
            (longitud 0 si la sintesis de esa frase fallo). No se usa texto ni
            base64 aqui -- un audio de varios segundos en base64 supera el
            limite de linea por defecto de asyncio.StreamReader.readline().
"""

import struct
import sys


def main() -> None:
    if len(sys.argv) != 3:
        print("Uso: piper_worker.py <model.onnx> <config.json>", file=sys.stderr)
        sys.exit(1)

    from piper import PiperVoice

    model_path, config_path = sys.argv[1], sys.argv[2]
    voice = PiperVoice.load(model_path, config_path=config_path)
    sys.stdout.buffer.write(b"READY\n")
    sys.stdout.buffer.flush()

    for raw_line in sys.stdin:
        text = raw_line.rstrip("\n")
        if text:
            try:
                pcm = b"".join(chunk.audio_int16_bytes for chunk in voice.synthesize(text))
            except Exception:
                pcm = b""
        else:
            pcm = b""
        sys.stdout.buffer.write(struct.pack(">I", len(pcm)) + pcm)
        sys.stdout.buffer.flush()


if __name__ == "__main__":
    main()
