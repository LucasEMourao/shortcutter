#!/usr/bin/env python3
"""Transcribe extracted audio with faster-whisper."""

import sys

from video_cutter_config import WHISPER_LANGUAGE, WHISPER_MODEL_SIZE
from pipeline_common import save_json


def main():
    if len(sys.argv) != 3:
        print("Uso: python3 transcribe_audio.py <audio.wav> <output.json>")
        sys.exit(1)

    audio_path = sys.argv[1]
    output_path = sys.argv[2]

    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise SystemExit(
            "faster-whisper nao instalado. Instale com: "
            "pip3 install --user --break-system-packages faster-whisper"
        ) from exc

    print(f"  Carregando modelo Whisper ({WHISPER_MODEL_SIZE})...")
    model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")

    print(f"  Transcrevendo audio extraido: {audio_path}")
    segments, info = model.transcribe(audio_path, language=WHISPER_LANGUAGE, beam_size=5)

    transcription = []
    for idx, segment in enumerate(segments, start=1):
        transcription.append(
            {
                "id": idx,
                "start_sec": round(segment.start, 2),
                "end_sec": round(segment.end, 2),
                "text": segment.text.strip(),
            }
        )

    payload = {
        "transcription": transcription,
        "total_duration_sec": round(info.duration, 2),
        "language": info.language,
        "language_probability": round(info.language_probability, 4),
        "method": "whisper",
        "model_size": WHISPER_MODEL_SIZE,
    }
    save_json(output_path, payload)

    print(f"  Transcricao: {len(transcription)} segmentos")
    print(f"  Idioma: {info.language} ({info.language_probability:.2%})")


if __name__ == "__main__":
    main()
