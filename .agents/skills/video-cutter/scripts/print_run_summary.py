#!/usr/bin/env python3
"""Pretty-print the final pipeline summary from cuts.json."""

import sys

from pipeline_common import load_json


def main():
    if len(sys.argv) != 2:
        print("Uso: python3 print_run_summary.py <cuts.json>")
        sys.exit(1)

    cuts_path = sys.argv[1]
    data = load_json(cuts_path)

    print("")
    print("===============================================")
    print("  [ok] CORTES GERADOS COM SUCESSO")
    print("===============================================")
    print("")
    print(f"Output: {data['output_dir']}")
    print(f"Clips: {data['total_cuts']}")
    print(f"Modelo: {data.get('model', 'unknown')}")
    print(f"Modo: {data.get('mode', 'unknown')}")
    encoding = data.get("encoding", {})
    if encoding:
        print(
            "Encoding: "
            f"{encoding.get('video_codec', 'unknown')} "
            f"preset={encoding.get('preset', 'unknown')} "
            f"crf={encoding.get('crf', 'unknown')}"
        )
    print("")
    print("Resumo:")
    for cut in data["cuts"]:
        print(
            "  - "
            f"{cut['filename']} ({cut['duration']:.1f}s) - "
            f"Score: {cut['viral_score']} - {cut['hook_type']}"
        )
    print("")
    print(f"Metadados: {data['output_dir']}/cuts.json")
    print("")
    print("Para visualizar:")
    print(f"  explorer.exe {data['output_dir']}")
    print("")


if __name__ == "__main__":
    main()
