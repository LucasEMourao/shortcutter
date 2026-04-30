#!/usr/bin/env python3
"""Normalize and sanitize transcription timestamps."""

import sys

from pipeline_common import load_json, save_json


def main():
    if len(sys.argv) != 4:
        print("Uso: python3 sanitize_transcription.py <transcription.json> <video_duration> <output.json>")
        sys.exit(1)

    input_path = sys.argv[1]
    video_duration = float(sys.argv[2])
    output_path = sys.argv[3]

    transcription = load_json(input_path)
    max_timestamp = max(segment["end_sec"] for segment in transcription["transcription"])
    warnings = []

    if max_timestamp > video_duration:
        scale = video_duration / max_timestamp
        for segment in transcription["transcription"]:
            segment["start_sec"] = round(segment["start_sec"] * scale, 3)
            segment["end_sec"] = round(segment["end_sec"] * scale, 3)
        warnings.append(f"Normalizacao aplicada: escala {scale:.4f}")
        print(f"  Normalizacao aplicada (escala: {scale:.4f})")

    original_count = len(transcription["transcription"])
    transcription["transcription"] = [
        segment
        for segment in transcription["transcription"]
        if segment["start_sec"] >= 0
        and segment["end_sec"] <= video_duration
        and segment["end_sec"] > segment["start_sec"]
    ]
    removed = original_count - len(transcription["transcription"])
    if removed > 0:
        warnings.append(f"{removed} segmentos removidos por timestamps invalidos")

    transcription["sanitization"] = {
        "applied": max_timestamp > video_duration,
        "original_max_ts": max_timestamp,
        "warnings": warnings,
    }
    save_json(output_path, transcription)

    print(f"  Segmentos validos: {len(transcription['transcription'])}")


if __name__ == "__main__":
    main()
