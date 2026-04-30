#!/usr/bin/env python3
"""Benchmark CRF variants for a fixed video segment."""

import argparse
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from pipeline_common import save_json


def parse_args():
    parser = argparse.ArgumentParser(
        description="Compara variantes de CRF para um mesmo trecho de video."
    )
    parser.add_argument("video_path")
    parser.add_argument("start_sec", type=float)
    parser.add_argument("end_sec", type=float)
    parser.add_argument("output_dir")
    parser.add_argument(
        "--preset",
        default="ultrafast",
        help="Preset do ffmpeg para todas as variantes (padrao: ultrafast).",
    )
    parser.add_argument(
        "--crfs",
        default="23,28,32",
        help="Lista de CRFs separados por virgula (padrao: 23,28,32).",
    )
    parser.add_argument(
        "--label",
        default=None,
        help="Rotulo opcional para os arquivos gerados.",
    )
    return parser.parse_args()


def ensure_tool(name):
    result = subprocess.run(
        ["bash", "-lc", f"command -v {name} >/dev/null 2>&1"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Dependencia nao encontrada: {name}")


def ffprobe_duration(path):
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(result.stdout.strip())


def render_variant(video_path, start_sec, end_sec, output_path, preset, crf):
    duration = end_sec - start_sec
    command = [
        "ffmpeg",
        "-ss",
        str(start_sec),
        "-i",
        str(video_path),
        "-t",
        str(duration),
        "-c:v",
        "libx264",
        "-preset",
        preset,
        "-crf",
        str(crf),
        "-c:a",
        "aac",
        "-movflags",
        "+faststart",
        "-pix_fmt",
        "yuv420p",
        str(output_path),
        "-y",
    ]

    started = time.perf_counter()
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    elapsed = round(time.perf_counter() - started, 3)
    if result.returncode != 0:
        error_text = (result.stderr or result.stdout or "erro desconhecido").strip()
        raise RuntimeError(f"Falha ao gerar variante CRF {crf}: {error_text}")

    size_bytes = output_path.stat().st_size
    duration_real = round(ffprobe_duration(output_path), 3)
    size_mb = round(size_bytes / (1024 * 1024), 3)
    bitrate_mbps = round((size_bytes * 8) / max(duration_real, 0.001) / 1_000_000, 3)

    return {
        "crf": crf,
        "preset": preset,
        "output_file": output_path.name,
        "elapsed_sec": elapsed,
        "duration_sec": duration_real,
        "size_bytes": size_bytes,
        "size_mb": size_mb,
        "bitrate_mbps": bitrate_mbps,
    }


def render_markdown(report):
    baseline = report["variants"][0]
    lines = [
        "# Benchmark de Encoding",
        "",
        f"- Video: `{report['input_video']}`",
        f"- Segmento: `{report['segment']['start_sec']:.1f}s` ate `{report['segment']['end_sec']:.1f}s`",
        f"- Preset: `{report['preset']}`",
        f"- Gerado em: `{report['generated_at']}`",
        "",
        "| CRF | Tamanho (MB) | Tempo (s) | Bitrate (Mbps) | Delta vs baseline | Arquivo |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]

    for variant in report["variants"]:
        delta_percent = 0.0
        if baseline["size_bytes"] > 0:
            delta_percent = (
                (variant["size_bytes"] - baseline["size_bytes"])
                / baseline["size_bytes"]
            ) * 100
        lines.append(
            "| "
            f"{variant['crf']} | "
            f"{variant['size_mb']:.3f} | "
            f"{variant['elapsed_sec']:.3f} | "
            f"{variant['bitrate_mbps']:.3f} | "
            f"{delta_percent:+.1f}% | "
            f"`{variant['output_file']}` |"
        )

    lines.extend(
        [
            "",
            "## Proximo passo",
            "",
            "1. Compare visualmente os arquivos em um player.",
            "2. Procure artefatos em rosto, texto, movimento e transicoes.",
            "3. Escolha o menor CRF que ainda preserve a qualidade aceitavel para o tipo de conteudo.",
            "",
        ]
    )
    return "\n".join(lines)


def main():
    args = parse_args()
    if args.end_sec <= args.start_sec:
      print("Erro: end_sec deve ser maior que start_sec")
      sys.exit(1)

    for dependency in ("ffmpeg", "ffprobe"):
        ensure_tool(dependency)

    crfs = [int(value.strip()) for value in args.crfs.split(",") if value.strip()]
    if not crfs:
        print("Erro: informe ao menos um CRF")
        sys.exit(1)

    video_path = Path(args.video_path).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    label = args.label or f"{video_path.stem}_{int(args.start_sec)}-{int(args.end_sec)}s"

    variants = []
    for crf in crfs:
        output_file = output_dir / f"{label}_preset-{args.preset}_crf-{crf}.mp4"
        print(f"Gerando variante CRF {crf}...")
        variants.append(
            render_variant(
                video_path=video_path,
                start_sec=args.start_sec,
                end_sec=args.end_sec,
                output_path=output_file,
                preset=args.preset,
                crf=crf,
            )
        )

    report = {
        "input_video": video_path.name,
        "generated_at": datetime.now().isoformat() + "Z",
        "segment": {
            "start_sec": args.start_sec,
            "end_sec": args.end_sec,
            "duration_sec": round(args.end_sec - args.start_sec, 3),
        },
        "preset": args.preset,
        "variants": variants,
    }

    json_path = output_dir / "benchmark.json"
    markdown_path = output_dir / "benchmark.md"
    save_json(json_path, report)
    markdown_path.write_text(render_markdown(report), encoding="utf-8")

    print(f"Benchmark salvo em: {json_path}")
    print(f"Resumo salvo em: {markdown_path}")


if __name__ == "__main__":
    main()
