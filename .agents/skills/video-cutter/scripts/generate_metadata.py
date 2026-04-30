#!/usr/bin/env python3
"""Generate the final cuts.json metadata file."""

import sys
from datetime import datetime

from pipeline_common import load_json, save_json, to_display_path


def main():
    if len(sys.argv) != 8:
        print(
            "Uso: python3 generate_metadata.py "
            "<final_cuts_with_files.json> <analysis.json> <mode> "
            "<run_dir> <project_dir> <video_name> <output.json>"
        )
        sys.exit(1)

    final_cuts_path = sys.argv[1]
    analysis_path = sys.argv[2]
    mode = sys.argv[3]
    run_dir = sys.argv[4]
    project_dir = sys.argv[5]
    video_name = sys.argv[6]
    output_path = sys.argv[7]

    data = load_json(final_cuts_path)
    analysis = load_json(analysis_path)

    quality_warnings = list(analysis.get("quality_warnings", []))
    for failure in data.get("clip_failures", []):
        quality_warnings.append(
            f"Falha ao gerar {failure['filename']}: {failure['error']}"
        )

    payload = {
        "input_video": video_name,
        "output_dir": to_display_path(run_dir, project_dir),
        "generated_at": datetime.now().isoformat() + "Z",
        "model": analysis.get("model_used", "unknown"),
        "mode": mode,
        "buffer_strategy": "intelligent_gap_2s",
        "analysis": {
            "content_type": analysis["analysis"]["content_type"],
            "main_topics": analysis["analysis"]["main_topics"],
            "overall_viral_potential": analysis["analysis"]["overall_viral_potential"],
        },
        "chunking_info": analysis.get("chunking_info", {}),
        "buffer_details": data["buffer_details"],
        "cuts": data["cuts"],
        "total_cuts": len(data["cuts"]),
        "quality_warnings": quality_warnings,
    }
    save_json(output_path, payload)
    print(f"Metadados salvos: {output_path}")


if __name__ == "__main__":
    main()
