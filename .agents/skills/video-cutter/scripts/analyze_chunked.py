#!/usr/bin/env python3
"""
analyze_chunked.py - Análise de cortes virais com chunking

Divide a transcrição em chunks de ~3-4 minutos, analisa cada chunk
separadamente com Gemini, e faz merge dos resultados.

Uso: python3 analyze_chunked.py <transcription.json> <video_duration> <mode> <output.json> <api_key> [model]
"""

import json
import sys
import os
import urllib.request
import urllib.error

# Configurações
CHUNK_DURATION_SEC = 180  # 3 minutos por chunk
CHUNK_OVERLAP_SEGMENTS = 5  # Overlap de 5 segmentos entre chunks
QUALITY_FLOOR = 7.5  # Score mínimo para incluir corte
MIN_CUT_DURATION = 15
MAX_CUT_DURATION = 60


def create_chunks(transcription, video_duration):
    """Divide a transcrição em chunks de ~3 minutos com overlap."""
    segments = transcription["transcription"]
    chunks = []
    
    chunk_start_idx = 0
    chunk_num = 0
    
    while chunk_start_idx < len(segments):
        chunk_num += 1
        chunk_start_time = segments[chunk_start_idx]["start_sec"]
        chunk_end_time = chunk_start_time + CHUNK_DURATION_SEC
        
        # Encontrar o último segmento que cabe neste chunk
        chunk_end_idx = chunk_start_idx
        for i in range(chunk_start_idx, len(segments)):
            if segments[i]["start_sec"] < chunk_end_time:
                chunk_end_idx = i + 1
            else:
                break
        
        # Se não avançou, forçar pelo menos 1 segmento
        if chunk_end_idx <= chunk_start_idx:
            chunk_end_idx = chunk_start_idx + 1
        
        # Criar chunk
        chunk_segments = segments[chunk_start_idx:chunk_end_idx]
        chunk = {
            "chunk_id": chunk_num,
            "start_time": chunk_segments[0]["start_sec"],
            "end_time": chunk_segments[-1]["end_sec"],
            "segment_start_idx": chunk_start_idx,
            "segment_end_idx": chunk_end_idx - 1,
            "transcription": {
                "transcription": chunk_segments,
                "total_duration_sec": round(chunk_segments[-1]["end_sec"], 2),
                "language": transcription.get("language", "pt")
            }
        }
        chunks.append(chunk)
        
        # Próximo chunk com overlap
        next_start_idx = chunk_end_idx - CHUNK_OVERLAP_SEGMENTS
        if next_start_idx <= chunk_start_idx:
            next_start_idx = chunk_end_idx
        
        chunk_start_idx = next_start_idx
    
    return chunks


def build_prompt(chunk, video_duration, mode):
    """Constrói o prompt de análise para um chunk."""
    transcription_json = json.dumps(chunk["transcription"], ensure_ascii=False)
    
    extra_rules = ""
    if mode == "conservative":
        extra_rules = """
MODO CONSERVADOR: 1-3 cortes com narrativa COMPLETA.
Priorize COERÊNCIA e VALOR sobre viralidade.
Duração mínima: 20s."""

    prompt = f"""Analise a transcrição e identifique os melhores momentos para cortes virais.

TRANSCRIÇÃO (chunk {chunk["chunk_id"]}, {chunk["start_time"]:.1f}s - {chunk["end_time"]:.1f}s):
{transcription_json}

DURAÇÃO TOTAL DO VÍDEO COMPLETO: {video_duration} segundos

IMPORTANTE: Esta é apenas uma PARTE do vídeo completo ({chunk["start_time"]:.1f}s - {chunk["end_time"]:.1f}s).
Os timestamps na transcrição são absolutos (referentes ao vídeo completo).

FORMATO DE SAÍDA (JSON obrigatório):
{{"analysis": {{"content_type": "tutorial|vlog|interview|review|story|other", "main_topics": ["topic1", "topic2"], "overall_viral_potential": 8.5}}, "cuts": [{{"id": 1, "start_sec": 12.5, "end_sec": 38.2, "content": "Transcrição do segmento...", "hook_type": "pattern_interrupt|curiosity_gap|result_first|controversial|fomo", "hook_power": 9, "retention_potential": 8, "shareability": 7, "viral_score": 8.1, "reason": "Por que este corte funciona..."}}], "quality_warnings": ["Aviso 1"]}}

CRITÉRIOS:
- HOOK (0-3s): pattern_interrupt, curiosity_gap, result_first, controversial, fomo
- SCORE: viral_score = (hook × 0.4) + (retention × 0.3) + (shareability × 0.3)
- DURAÇÃO: {MIN_CUT_DURATION}-{MAX_CUT_DURATION} segundos por corte
- MÍNIMO: 1 corte, MÁXIMO: 3 cortes por chunk
- QUALITY FLOOR: viral_score >= {QUALITY_FLOOR}. NÃO inclua cortes com score abaixo de {QUALITY_FLOOR}.

REGRAS DE CORTE:
- O corte DEVE começar no INÍCIO de uma frase ou segmento de fala
- O corte DEVE terminar no FIM de uma frase completa ou pensamento completo
- NUNCA corte no meio de uma frase

REGRAS CRÍTICAS:
1. Timestamps DEVEM existir na transcrição
2. NÃO invente timestamps
3. end_sec DEVE ser <= {video_duration}
4. start_sec DEVE ser < end_sec
5. start_sec DEVE ser >= {chunk["start_time"]}
6. end_sec DEVE ser <= {chunk["end_time"]}
7. Se não houver bons cortes: array vazio com explicação

PADRÕES DE HOOK:
- curiosity_gap: Pergunta que cria lacuna mental
- result_first: Mostra resultado primeiro
- pattern_interrupt: Começa no meio da ação
- pain_point: Identifica problema comum
- fomo: Cria urgência

O QUE NÃO FAZER:
- Cortar no meio de uma frase
- Silêncio > 1.5s dentro do corte
- Hook fraco nos primeiros 3s
- Duração > {MAX_CUT_DURATION}s
- Incluir cortes com viral_score < {QUALITY_FLOOR}{extra_rules}"""
    
    return prompt


def call_gemini(prompt, api_key, model="gemini-2.5-flash"):
    """Chama a API Gemini e retorna a resposta parseada."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"response_mime_type": "application/json"}
    }
    
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else "Unknown"
        raise Exception(f"Erro na API Gemini ({e.code}): {error_body}")
    except Exception as e:
        raise Exception(f"Erro ao chamar API Gemini: {e}")
    
    if "error" in result:
        raise Exception(f"Erro na API Gemini: {result['error'].get('message', 'Unknown')}")
    
    if "candidates" not in result:
        raise Exception(f"Resposta inesperada da API: {json.dumps(result)[:200]}")
    
    text = result["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(text)


def merge_cuts(all_cuts, video_duration):
    """Merge cortes de todos os chunks, deduplica e ordena."""
    if not all_cuts:
        return []
    
    # Ordenar por timestamp
    all_cuts.sort(key=lambda c: (c["start_sec"], c["end_sec"]))
    
    # Deduplicar por sobreposição significativa (>80%)
    merged = []
    for cut in all_cuts:
        is_duplicate = False
        for existing in merged:
            # Calcular sobreposição
            overlap_start = max(cut["start_sec"], existing["start_sec"])
            overlap_end = min(cut["end_sec"], existing["end_sec"])
            overlap = max(0, overlap_end - overlap_start)
            
            cut_duration = cut["end_sec"] - cut["start_sec"]
            existing_duration = existing["end_sec"] - existing["start_sec"]
            
            if cut_duration > 0 and existing_duration > 0:
                overlap_ratio = overlap / min(cut_duration, existing_duration)
                if overlap_ratio > 0.8:
                    is_duplicate = True
                    # Manter o de maior score
                    if cut["viral_score"] > existing["viral_score"]:
                        merged.remove(existing)
                        merged.append(cut)
                    break
        
        if not is_duplicate:
            merged.append(cut)
    
    # Reordenar e re-ids
    merged.sort(key=lambda c: c["start_sec"])
    for i, cut in enumerate(merged):
        cut["id"] = i + 1
    
    return merged


def main():
    if len(sys.argv) < 6:
        print("Uso: python3 analyze_chunked.py <transcription.json> <video_duration> <mode> <output.json> <api_key> [model]")
        sys.exit(1)
    
    transcription_path = sys.argv[1]
    video_duration = float(sys.argv[2])
    mode = sys.argv[3]
    output_path = sys.argv[4]
    api_key = sys.argv[5]
    model = sys.argv[6] if len(sys.argv) > 6 else "gemini-2.5-flash"
    
    # Carregar transcrição
    with open(transcription_path) as f:
        transcription = json.load(f)
    
    total_segments = len(transcription["transcription"])
    print(f"  Transcrição: {total_segments} segmentos, {video_duration:.1f}s")
    
    # Criar chunks
    chunks = create_chunks(transcription, video_duration)
    print(f"  Chunks criados: {len(chunks)}")
    for chunk in chunks:
        print(f"    Chunk {chunk['chunk_id']}: {chunk['start_time']:.1f}s - {chunk['end_time']:.1f}s ({len(chunk['transcription']['transcription'])} segmentos)")
    
    # Analisar cada chunk
    all_cuts = []
    all_analysis = {
        "content_type": "other",
        "main_topics": [],
        "overall_viral_potential": 0
    }
    all_warnings = []
    
    for chunk in chunks:
        print(f"  Analisando chunk {chunk['chunk_id']}...")
        
        prompt = build_prompt(chunk, video_duration, mode)
        
        try:
            result = call_gemini(prompt, api_key, model)
            
            # Coletar cortes
            if "cuts" in result:
                for cut in result["cuts"]:
                    cut["chunk_id"] = chunk["chunk_id"]
                all_cuts.extend(result["cuts"])
                print(f"    → {len(result['cuts'])} cortes encontrados")
            
            # Coletar analysis (do primeiro chunk com dados)
            if "analysis" in result and result["analysis"].get("content_type") != "other":
                if all_analysis["content_type"] == "other":
                    all_analysis = result["analysis"]
            
            # Coletar warnings
            if "quality_warnings" in result:
                all_warnings.extend(result["quality_warnings"])
                
        except Exception as e:
            print(f"    ⚠️ Erro no chunk {chunk['chunk_id']}: {e}")
            all_warnings.append(f"Erro no chunk {chunk['chunk_id']}: {str(e)}")
    
    print(f"  Total de cortes brutos: {len(all_cuts)}")
    
    # Aplicar quality floor
    before_floor = len(all_cuts)
    all_cuts = [c for c in all_cuts if c.get("viral_score", 0) >= QUALITY_FLOOR]
    filtered = before_floor - len(all_cuts)
    if filtered > 0:
        print(f"  Quality floor: {filtered} cortes removidos (score < {QUALITY_FLOOR})")
    
    # Validar duração
    before_dur = len(all_cuts)
    all_cuts = [c for c in all_cuts if MIN_CUT_DURATION <= (c["end_sec"] - c["start_sec"]) <= MAX_CUT_DURATION]
    filtered_dur = before_dur - len(all_cuts)
    if filtered_dur > 0:
        print(f"  Duração: {filtered_dur} cortes removidos (fora de {MIN_CUT_DURATION}-{MAX_CUT_DURATION}s)")
    
    # Merge e deduplicação
    merged_cuts = merge_cuts(all_cuts, video_duration)
    print(f"  Após merge: {len(merged_cuts)} cortes únicos")
    
    # Montar resultado final
    final_result = {
        "analysis": all_analysis,
        "cuts": merged_cuts,
        "quality_warnings": all_warnings,
        "chunking_info": {
            "total_chunks": len(chunks),
            "chunk_duration_sec": CHUNK_DURATION_SEC,
            "overlap_segments": CHUNK_OVERLAP_SEGMENTS,
            "quality_floor": QUALITY_FLOOR,
            "raw_cuts": len(all_cuts) + filtered,
            "after_quality_floor": len(all_cuts),
            "after_merge": len(merged_cuts)
        }
    }
    
    # Salvar
    with open(output_path, "w") as f:
        json.dump(final_result, f, indent=2, ensure_ascii=False)
    
    print(f"  Análise salva: {output_path}")
    print(f"  Cortes finais: {len(merged_cuts)}")


if __name__ == "__main__":
    main()
