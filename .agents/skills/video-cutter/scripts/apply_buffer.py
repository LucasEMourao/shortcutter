#!/usr/bin/env python3
"""Apply the final padding/buffer rules to validated cuts."""

import sys

from pipeline_common import get_cut_problems, load_json, save_json
from video_cutter_config import (
    CONSERVATIVE_MIN_CUT_DURATION,
    FIXED_BUFFER_SEC,
    MAX_CUT_DURATION,
    MIN_CUT_DURATION,
    PADDING_MAX_SEC,
)


def clamp_end(start_sec, desired_end_sec, video_duration):
    max_end_sec = min(video_duration, start_sec + MAX_CUT_DURATION)
    return round(min(desired_end_sec, max_end_sec), 1)


def main():
    if len(sys.argv) != 6:
        print(
            "Uso: python3 apply_buffer.py "
            "<transcription.json> <valid_cuts.json> <video_duration> <mode> <output.json>"
        )
        sys.exit(1)

    transcription_path = sys.argv[1]
    cuts_path = sys.argv[2]
    video_duration = float(sys.argv[3])
    mode = sys.argv[4]
    output_path = sys.argv[5]

    transcription = load_json(transcription_path)["transcription"]
    cuts = load_json(cuts_path)
    min_duration = (
        CONSERVATIVE_MIN_CUT_DURATION if mode == "conservative" else MIN_CUT_DURATION
    )

    for cut in cuts:
        next_segment = None
        for segment in transcription:
            if segment["start_sec"] > cut["end_sec"] + 0.5:
                next_segment = segment
                break

        original_end = cut["end_sec"]
        if next_segment:
            gap = next_segment["start_sec"] - cut["end_sec"]
            if gap <= PADDING_MAX_SEC:
                desired_end = next_segment["start_sec"]
                detail = {
                    "id": cut["id"],
                    "original_end": original_end,
                    "next_segment_start": next_segment["start_sec"],
                    "gap": gap,
                    "buffer_applied": gap,
                    "reason": "Estendido ate o proximo segmento (gap <= 2s)",
                }
            else:
                desired_end = min(video_duration, cut["end_sec"] + FIXED_BUFFER_SEC)
                detail = {
                    "id": cut["id"],
                    "original_end": original_end,
                    "next_segment_start": next_segment["start_sec"],
                    "gap": gap,
                    "buffer_applied": FIXED_BUFFER_SEC,
                    "reason": (
                        f"Buffer fixo {FIXED_BUFFER_SEC}s "
                        f"(gap {gap:.1f}s > {PADDING_MAX_SEC}s)"
                    ),
                }
        else:
            desired_end = video_duration
            detail = {
                "id": cut["id"],
                "original_end": original_end,
                "next_segment_start": None,
                "gap": None,
                "buffer_applied": video_duration - original_end,
                "reason": "Ultimo corte - estendido ate o fim do video",
            }

        cut["end_sec"] = clamp_end(cut["start_sec"], desired_end, video_duration)
        cut["duration"] = round(cut["end_sec"] - cut["start_sec"], 1)
        if cut["end_sec"] < round(desired_end, 1):
            detail["clamped_to_max_duration"] = True
            detail["clamped_end_sec"] = cut["end_sec"]
        cut["_buffer_detail"] = detail
        print(
            f"  Cut {cut['id']}: {original_end:.1f}s -> {cut['end_sec']:.1f}s "
            f"({detail['reason']})"
        )

    cuts.sort(key=lambda cut: cut["start_sec"])

    for idx in range(len(cuts) - 1):
        current = cuts[idx]
        following = cuts[idx + 1]
        if current["end_sec"] > following["start_sec"]:
            current["end_sec"] = following["start_sec"]
            current["duration"] = round(current["end_sec"] - current["start_sec"], 1)
            current["_buffer_detail"]["overlap_adjusted"] = True
            current["_buffer_detail"]["overlap_adjusted_end_sec"] = current["end_sec"]
            print(
                f"  [warn] Cut {current['id']}: sobreposicao corrigida -> "
                f"{current['end_sec']:.1f}s"
            )

    validated_cuts = []
    buffer_details = []
    for next_id, cut in enumerate(cuts, start=1):
        cut["duration"] = round(cut["end_sec"] - cut["start_sec"], 1)
        problems = get_cut_problems(cut, video_duration, min_duration, MAX_CUT_DURATION)
        if problems:
            print(
                f"  [drop] Cut {cut['id']}: removido apos revalidacao final "
                f"({', '.join(problems)})"
            )
            continue

        detail = cut.pop("_buffer_detail")
        detail["id"] = next_id
        detail["final_duration"] = cut["duration"]
        buffer_details.append(detail)
        cut["id"] = next_id
        validated_cuts.append(cut)

    save_json(
        output_path,
        {
            "cuts": validated_cuts,
            "buffer_details": buffer_details,
        },
    )
    print(f"\nBuffer aplicado: {len(validated_cuts)} cortes finais")


if __name__ == "__main__":
    main()
