#!/usr/bin/env python3
"""Validate analysis cuts before buffering."""

import sys

from pipeline_common import get_cut_problems, load_json, save_json
from video_cutter_config import (
    CONSERVATIVE_MIN_CUT_DURATION,
    MAX_CUT_DURATION,
    MIN_CUT_DURATION,
)


def main():
    if len(sys.argv) != 5:
        print(
            "Uso: python3 validate_analysis_cuts.py "
            "<analysis.json> <video_duration> <mode> <output.json>"
        )
        sys.exit(1)

    analysis_path = sys.argv[1]
    video_duration = float(sys.argv[2])
    mode = sys.argv[3]
    output_path = sys.argv[4]

    analysis = load_json(analysis_path)
    min_duration = (
        CONSERVATIVE_MIN_CUT_DURATION if mode == "conservative" else MIN_CUT_DURATION
    )

    valid_cuts = []
    for cut in analysis["cuts"]:
        problems = get_cut_problems(cut, video_duration, min_duration, MAX_CUT_DURATION)
        duration = cut["end_sec"] - cut["start_sec"]
        if problems:
            print(
                f"  [x] Cut {cut['id']}: INVALIDO "
                f"({', '.join(problems)})"
            )
            continue

        valid_cuts.append(cut)
        print(
            f"  [ok] Cut {cut['id']}: "
            f"{cut['start_sec']:.1f}s - {cut['end_sec']:.1f}s ({duration:.1f}s)"
        )

    save_json(output_path, valid_cuts)
    print(f"\nCortes validos: {len(valid_cuts)}")


if __name__ == "__main__":
    main()
