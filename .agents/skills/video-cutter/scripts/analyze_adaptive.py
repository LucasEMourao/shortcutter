#!/usr/bin/env python3
"""
analyze_adaptive.py - Analise adaptativa de cortes virais

Decide automaticamente entre analise direta (sem chunking) ou chunked analysis
baseado na duracao do video.

Threshold:
- < 5min: analise direta (1 chamada API)
- 5-10min: chunking com chunks de 4min
- > 10min: chunking com chunks de 3min

Uso: python3 analyze_adaptive.py <transcription.json> <video_duration> <mode> <output.json> <api_key> [model]
"""

import json
import sys

from analysis_common import call_gemini, create_chunks, merge_cuts, prepare_models
from analysis_prompts import build_chunk_prompt, build_direct_prompt
from video_cutter_config import (
    CHUNK_DURATION_LONG,
    CHUNK_DURATION_SHORT,
    CHUNK_OVERLAP_SEGMENTS,
    CONSERVATIVE_MAX_TOTAL_CUTS,
    CONSERVATIVE_MIN_CUT_DURATION,
    DIRECT_ANALYSIS_THRESHOLD,
    MAX_CUT_DURATION,
    MEDIUM_VIDEO_THRESHOLD,
    MIN_CUT_DURATION,
    QUALITY_FLOOR,
)


def default_analysis():
    return {
        "content_type": "other",
        "main_topics": [],
        "overall_viral_potential": 0,
    }


def enforce_mode_limit(cuts, mode):
    """Apply final cut limits for conservative mode after merge."""
    if mode != "conservative" or len(cuts) <= CONSERVATIVE_MAX_TOTAL_CUTS:
        return cuts, 0

    limited = sorted(
        cuts,
        key=lambda cut: (-cut.get("viral_score", 0), cut["start_sec"], cut["end_sec"]),
    )[:CONSERVATIVE_MAX_TOTAL_CUTS]
    limited.sort(key=lambda cut: cut["start_sec"])

    for idx, cut in enumerate(limited, start=1):
        cut["id"] = idx

    return limited, len(cuts) - len(limited)


def apply_filters(cuts, mode):
    mode_min_duration = (
        CONSERVATIVE_MIN_CUT_DURATION if mode == "conservative" else MIN_CUT_DURATION
    )

    before_floor = len(cuts)
    filtered_by_score = [
        cut for cut in cuts if cut.get("viral_score", 0) >= QUALITY_FLOOR
    ]
    removed_by_score = before_floor - len(filtered_by_score)
    if removed_by_score > 0:
        print(f"  Quality floor: {removed_by_score} cortes removidos (score < {QUALITY_FLOOR})")

    before_duration = len(filtered_by_score)
    filtered_by_duration = [
        cut
        for cut in filtered_by_score
        if mode_min_duration <= (cut["end_sec"] - cut["start_sec"]) <= MAX_CUT_DURATION
    ]
    removed_by_duration = before_duration - len(filtered_by_duration)
    if removed_by_duration > 0:
        print(
            "  Duracao: "
            f"{removed_by_duration} cortes removidos "
            f"(fora de {mode_min_duration}-{MAX_CUT_DURATION}s)"
        )

    return filtered_by_duration, {
        "raw_cuts": before_floor,
        "after_quality_floor": before_duration,
        "after_duration_filter": len(filtered_by_duration),
    }


def collect_result(result, cuts, analysis, warnings, chunk_id=None):
    if "cuts" in result:
        if chunk_id is not None:
            for cut in result["cuts"]:
                cut["chunk_id"] = chunk_id
        cuts.extend(result["cuts"])
        print(f"    -> {len(result['cuts'])} cortes encontrados")

    if "analysis" in result and result["analysis"].get("content_type") != "other":
        if analysis["content_type"] == "other":
            analysis.update(result["analysis"])

    if "quality_warnings" in result:
        warnings.extend(result["quality_warnings"])


def run_direct_analysis(transcription, video_duration, mode, api_key, models, current_model_idx):
    cuts = []
    analysis = default_analysis()
    warnings = []

    prompt = build_direct_prompt(transcription, video_duration, mode)
    try:
        result, current_model_idx = call_gemini(prompt, api_key, models, current_model_idx)
        collect_result(result, cuts, analysis, warnings)
    except Exception as exc:
        print(f"    [warn] Erro na analise direta: {exc}")
        warnings.append(f"Erro na analise direta: {exc}")

    return {
        "cuts": cuts,
        "analysis": analysis,
        "warnings": warnings,
        "current_model_idx": current_model_idx,
        "chunking_info": {
            "total_chunks": 1,
            "chunk_duration_sec": int(video_duration),
            "overlap_segments": 0,
            "strategy": "direct",
        },
    }


def run_chunked_analysis(transcription, video_duration, mode, api_key, models, current_model_idx, chunk_duration, strategy):
    cuts = []
    analysis = default_analysis()
    warnings = []

    chunks = create_chunks(transcription, chunk_duration)
    print(f"  Chunks criados: {len(chunks)}")
    for chunk in chunks:
        print(
            "    Chunk "
            f"{chunk['chunk_id']}: {chunk['start_time']:.1f}s - {chunk['end_time']:.1f}s "
            f"({len(chunk['transcription']['transcription'])} segmentos)"
        )

    for chunk in chunks:
        print(f"  Analisando chunk {chunk['chunk_id']}...")
        prompt = build_chunk_prompt(chunk, video_duration, mode)
        try:
            result, current_model_idx = call_gemini(prompt, api_key, models, current_model_idx)
            collect_result(result, cuts, analysis, warnings, chunk_id=chunk["chunk_id"])
        except Exception as exc:
            print(f"    [warn] Erro no chunk {chunk['chunk_id']}: {exc}")
            warnings.append(f"Erro no chunk {chunk['chunk_id']}: {exc}")

    return {
        "cuts": cuts,
        "analysis": analysis,
        "warnings": warnings,
        "current_model_idx": current_model_idx,
        "chunking_info": {
            "total_chunks": len(chunks),
            "chunk_duration_sec": chunk_duration,
            "overlap_segments": CHUNK_OVERLAP_SEGMENTS,
            "strategy": strategy,
        },
    }


def main():
    if len(sys.argv) < 6:
        print("Uso: python3 analyze_adaptive.py <transcription.json> <video_duration> <mode> <output.json> <api_key> [model]")
        sys.exit(1)

    transcription_path = sys.argv[1]
    video_duration = float(sys.argv[2])
    mode = sys.argv[3]
    output_path = sys.argv[4]
    api_key = sys.argv[5]
    user_model = sys.argv[6] if len(sys.argv) > 6 else None

    models = prepare_models(api_key, user_model)
    current_model_idx = 0

    with open(transcription_path, encoding="utf-8") as handle:
        transcription = json.load(handle)

    total_segments = len(transcription["transcription"])
    print(f"  Transcricao: {total_segments} segmentos, {video_duration:.1f}s")

    if video_duration < DIRECT_ANALYSIS_THRESHOLD:
        print("  Estrategia: ANALISE DIRETA (video < 5min)")
        run_result = run_direct_analysis(
            transcription,
            video_duration,
            mode,
            api_key,
            models,
            current_model_idx,
        )
    else:
        if video_duration < MEDIUM_VIDEO_THRESHOLD:
            chunk_duration = CHUNK_DURATION_SHORT
            strategy = "chunked_medium"
            print(
                f"  Estrategia: CHUNKED (chunks de {chunk_duration / 60:.0f}min, video 5-10min)"
            )
        else:
            chunk_duration = CHUNK_DURATION_LONG
            strategy = "chunked_long"
            print(
                f"  Estrategia: CHUNKED (chunks de {chunk_duration / 60:.0f}min, video > 10min)"
            )

        run_result = run_chunked_analysis(
            transcription,
            video_duration,
            mode,
            api_key,
            models,
            current_model_idx,
            chunk_duration,
            strategy,
        )

    all_cuts = run_result["cuts"]
    all_analysis = run_result["analysis"]
    all_warnings = run_result["warnings"]
    current_model_idx = run_result["current_model_idx"]
    chunking_info = run_result["chunking_info"]

    print(f"  Total de cortes brutos: {len(all_cuts)}")

    filtered_cuts, filter_stats = apply_filters(all_cuts, mode)
    merged_cuts = merge_cuts(filtered_cuts)
    cuts_after_merge = len(merged_cuts)
    print(f"  Apos merge: {cuts_after_merge} cortes unicos")

    mode_trimmed = 0
    if mode == "conservative":
        merged_cuts, mode_trimmed = enforce_mode_limit(merged_cuts, mode)
        if mode_trimmed > 0:
            warning = (
                f"Modo conservative limitado a {CONSERVATIVE_MAX_TOTAL_CUTS} cortes finais; "
                f"{mode_trimmed} corte(s) adicional(is) foram removido(s)."
            )
            all_warnings.append(warning)
            print(
                "  Conservative mode: "
                f"{mode_trimmed} cortes removidos para respeitar o limite final"
            )

    final_result = {
        "analysis": all_analysis,
        "cuts": merged_cuts,
        "quality_warnings": all_warnings,
        "model_used": models[min(current_model_idx, len(models) - 1)] if models else "unknown",
        "chunking_info": {
            **chunking_info,
            "quality_floor": QUALITY_FLOOR,
            "raw_cuts": filter_stats["raw_cuts"],
            "after_quality_floor": filter_stats["after_quality_floor"],
            "after_duration_filter": filter_stats["after_duration_filter"],
            "after_merge": cuts_after_merge,
            "after_mode_limit": len(merged_cuts),
        },
    }

    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(final_result, handle, indent=2, ensure_ascii=False)

    print(f"  Analise salva: {output_path}")
    print(f"  Cortes finais: {len(merged_cuts)}")


if __name__ == "__main__":
    main()
