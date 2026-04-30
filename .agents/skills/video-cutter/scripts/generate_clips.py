#!/usr/bin/env python3
"""Render clip files from the final cut list."""

import os
import subprocess
import sys

from pipeline_common import load_json, save_json, to_display_path


def main():
    if len(sys.argv) != 7:
        print(
            "Uso: python3 generate_clips.py "
            "<final_cuts.json> <video> <run_dir> <helper.sh> <project_dir> <output.json>"
        )
        sys.exit(1)

    final_cuts_path = sys.argv[1]
    video_path = sys.argv[2]
    run_dir = sys.argv[3]
    helper_path = sys.argv[4]
    project_dir = sys.argv[5]
    output_path = sys.argv[6]

    data = load_json(final_cuts_path)
    cuts = data["cuts"]
    buffer_details_by_id = {detail["id"]: detail for detail in data.get("buffer_details", [])}

    run_dir_display = to_display_path(run_dir, project_dir)
    successful_cuts = []
    successful_buffer_details = []
    clip_failures = []

    for cut in cuts:
        source_id = cut["id"]
        next_id = len(successful_cuts) + 1
        filename = (
            f"cut_{next_id:02d}_{int(cut['start_sec'])}-{int(cut['end_sec'])}s.mp4"
        )
        output_file = os.path.join(run_dir, filename)
        command = [
            helper_path,
            "cut",
            video_path,
            str(cut["start_sec"]),
            str(cut["end_sec"]),
            output_file,
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=False)

        if result.returncode == 0:
            rendered_cut = dict(cut)
            rendered_cut["id"] = next_id
            rendered_cut["filename"] = filename
            rendered_cut["path"] = f"{run_dir_display}/{filename}"
            successful_cuts.append(rendered_cut)

            if source_id in buffer_details_by_id:
                detail = dict(buffer_details_by_id[source_id])
                detail["id"] = next_id
                successful_buffer_details.append(detail)

            print(f"  [ok] {filename} ({rendered_cut['duration']:.1f}s)")
            continue

        error_text = (result.stderr or result.stdout or "erro desconhecido").strip()
        clip_failures.append(
            {
                "source_id": source_id,
                "filename": filename,
                "error": error_text,
            }
        )
        print(f"  [x] {filename}: {error_text}")

    if not successful_cuts:
        print("Nenhum clip pode ser gerado.")
        sys.exit(1)

    data["cuts"] = successful_cuts
    data["buffer_details"] = successful_buffer_details
    data["clip_failures"] = clip_failures
    save_json(output_path, data)


if __name__ == "__main__":
    main()
