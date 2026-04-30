#!/usr/bin/env python3
"""Shared analysis helpers for Gemini-based cut selection."""

import json
import time
import urllib.error
import urllib.request

from video_cutter_config import CHUNK_OVERLAP_SEGMENTS, DEFAULT_FALLBACK_MODELS


def create_chunks(transcription, chunk_duration, overlap_segments=CHUNK_OVERLAP_SEGMENTS):
    """Split transcription into time-based chunks with segment overlap."""
    segments = transcription["transcription"]
    chunks = []

    chunk_start_idx = 0
    chunk_num = 0

    while chunk_start_idx < len(segments):
        chunk_num += 1
        chunk_start_time = segments[chunk_start_idx]["start_sec"]
        chunk_end_time = chunk_start_time + chunk_duration

        chunk_end_idx = chunk_start_idx
        for idx in range(chunk_start_idx, len(segments)):
            if segments[idx]["start_sec"] < chunk_end_time:
                chunk_end_idx = idx + 1
            else:
                break

        if chunk_end_idx <= chunk_start_idx:
            chunk_end_idx = chunk_start_idx + 1

        chunk_segments = segments[chunk_start_idx:chunk_end_idx]
        chunks.append(
            {
                "chunk_id": chunk_num,
                "start_time": chunk_segments[0]["start_sec"],
                "end_time": chunk_segments[-1]["end_sec"],
                "segment_start_idx": chunk_start_idx,
                "segment_end_idx": chunk_end_idx - 1,
                "transcription": {
                    "transcription": chunk_segments,
                    "total_duration_sec": round(chunk_segments[-1]["end_sec"], 2),
                    "language": transcription.get("language", "pt"),
                },
            }
        )

        next_start_idx = chunk_end_idx - overlap_segments
        if next_start_idx <= chunk_start_idx:
            next_start_idx = chunk_end_idx
        chunk_start_idx = next_start_idx

    return chunks


def call_gemini(prompt, api_key, models, current_model_idx=0):
    """Call Gemini with model fallback and 503 retries."""
    if isinstance(models, str):
        models = [models]

    last_error = None
    max_retries_503 = 3

    for idx in range(current_model_idx, len(models)):
        model = models[idx]
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={api_key}"
        )

        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"response_mime_type": "application/json"},
        }
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")

        for attempt in range(max_retries_503):
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            try:
                with urllib.request.urlopen(req, timeout=120) as response:
                    result = json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                error_body = exc.read().decode("utf-8") if exc.fp else "Unknown"
                if exc.code == 429:
                    print(f"    [warn] 429 em {model}, tentando proximo modelo...")
                    last_error = f"429 em {model}: quota esgotada"
                    break
                if exc.code == 503:
                    wait_seconds = 10 * (attempt + 1)
                    print(
                        "    [warn] 503 em "
                        f"{model}, retry em {wait_seconds}s "
                        f"(tentativa {attempt + 1}/{max_retries_503})..."
                    )
                    time.sleep(wait_seconds)
                    continue
                raise Exception(f"Erro na API Gemini ({exc.code}) com {model}: {error_body}") from exc
            except Exception as exc:
                raise Exception(f"Erro ao chamar API Gemini com {model}: {exc}") from exc

            if "error" in result:
                err_msg = result["error"].get("message", "Unknown")
                err_code = result["error"].get("code", 0)
                if err_code == 429 or "quota" in err_msg.lower() or "RESOURCE_EXHAUSTED" in str(result["error"]):
                    print(f"    [warn] 429 em {model}, tentando proximo modelo...")
                    last_error = f"429 em {model}: {err_msg}"
                    break
                if err_code == 503 or "UNAVAILABLE" in str(result["error"]):
                    wait_seconds = 10 * (attempt + 1)
                    print(
                        "    [warn] 503 em "
                        f"{model}, retry em {wait_seconds}s "
                        f"(tentativa {attempt + 1}/{max_retries_503})..."
                    )
                    time.sleep(wait_seconds)
                    continue
                raise Exception(f"Erro na API Gemini com {model}: {err_msg}")

            if "candidates" not in result:
                preview = json.dumps(result, ensure_ascii=False)[:200]
                raise Exception(f"Resposta inesperada da API com {model}: {preview}")

            text = result["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(text)

            if idx > current_model_idx:
                print(f"    [ok] Fallback para {model} funcionou")

            return parsed, idx

    raise Exception(f"Todos os modelos esgotaram. Ultimo erro: {last_error}")


def merge_cuts(all_cuts):
    """Deduplicate overlapping cuts and keep the highest scoring version."""
    if not all_cuts:
        return []

    all_cuts.sort(key=lambda cut: (cut["start_sec"], cut["end_sec"]))

    merged = []
    for cut in all_cuts:
        is_duplicate = False
        for existing in list(merged):
            overlap_start = max(cut["start_sec"], existing["start_sec"])
            overlap_end = min(cut["end_sec"], existing["end_sec"])
            overlap = max(0, overlap_end - overlap_start)

            cut_duration = cut["end_sec"] - cut["start_sec"]
            existing_duration = existing["end_sec"] - existing["start_sec"]

            if cut_duration <= 0 or existing_duration <= 0:
                continue

            overlap_ratio = overlap / min(cut_duration, existing_duration)
            if overlap_ratio > 0.8:
                is_duplicate = True
                if cut["viral_score"] > existing["viral_score"]:
                    merged.remove(existing)
                    merged.append(cut)
                break

        if not is_duplicate:
            merged.append(cut)

    merged.sort(key=lambda cut: cut["start_sec"])
    for idx, cut in enumerate(merged, start=1):
        cut["id"] = idx

    return merged


def discover_models(api_key):
    """Discover available text Flash models ordered from strongest to weakest."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    req = urllib.request.Request(url, method="GET")

    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        print(f"  [warn] Nao foi possivel listar modelos: {exc}")
        return []

    if "models" not in data:
        return []

    skip_keywords = ["image", "tts", "latest"]
    flash_models = []
    for model in data["models"]:
        name = model.get("name", "").replace("models/", "")
        supported = model.get("supportedGenerationMethods", [])

        if "generateContent" not in supported or "flash" not in name.lower():
            continue
        if any(keyword in name for keyword in skip_keywords):
            continue
        flash_models.append(name)

    def sort_key(model_name):
        parts = model_name.replace("gemini-", "").split("-")
        version_str = parts[0] if parts else "0"
        try:
            version = tuple(int(part) for part in version_str.split("."))
        except ValueError:
            version = (0, 0)
        is_preview = 1 if "preview" in model_name else 0
        is_lite = 1 if "lite" in model_name else 0
        return (is_lite, -version[0], -version[1] if len(version) > 1 else 0, is_preview)

    flash_models.sort(key=sort_key)

    if flash_models:
        print(f"  Modelos Flash disponiveis: {' -> '.join(flash_models)}")

    return flash_models


def prepare_models(api_key, user_model=None):
    """Build the ordered list of models to try."""
    models = discover_models(api_key) or list(DEFAULT_FALLBACK_MODELS)

    if user_model:
        if user_model in models:
            models.remove(user_model)
        models.insert(0, user_model)

    return models
