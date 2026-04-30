#!/usr/bin/env python3
"""Prompt builders shared by the analysis scripts."""

import json

from video_cutter_config import (
    CONSERVATIVE_MAX_TOTAL_CUTS,
    CONSERVATIVE_MIN_CUT_DURATION,
    MAX_CUT_DURATION,
    MIN_CUT_DURATION,
    QUALITY_FLOOR,
)


def build_direct_prompt(transcription, video_duration, mode):
    transcription_json = json.dumps(transcription, ensure_ascii=False)

    min_duration = MIN_CUT_DURATION
    min_cuts = 3
    max_cuts = 8
    extra_rules = ""
    if mode == "conservative":
        min_duration = CONSERVATIVE_MIN_CUT_DURATION
        min_cuts = 1
        max_cuts = CONSERVATIVE_MAX_TOTAL_CUTS
        extra_rules = """
MODO CONSERVADOR: 1-3 cortes com narrativa COMPLETA.
Priorize COERENCIA e VALOR sobre viralidade.
Duracao minima: 20s."""

    return f"""Analise a transcricao e identifique os melhores momentos para cortes virais.

TRANSCRICAO COMPLETA:
{transcription_json}

DURACAO TOTAL DO VIDEO: {video_duration} segundos

FORMATO DE SAIDA (JSON obrigatorio):
{{"analysis": {{"content_type": "tutorial|vlog|interview|review|story|other", "main_topics": ["topic1", "topic2"], "overall_viral_potential": 8.5}}, "cuts": [{{"id": 1, "start_sec": 12.5, "end_sec": 38.2, "content": "Transcricao do segmento...", "hook_type": "pattern_interrupt|curiosity_gap|result_first|controversial|fomo", "hook_power": 9, "retention_potential": 8, "shareability": 7, "viral_score": 8.1, "reason": "Por que este corte funciona..."}}], "quality_warnings": ["Aviso 1"]}}

CRITERIOS:
- HOOK (0-3s): pattern_interrupt, curiosity_gap, result_first, controversial, fomo
- SCORE: viral_score = (hook x 0.4) + (retention x 0.3) + (shareability x 0.3)
- DURACAO: {min_duration}-{MAX_CUT_DURATION} segundos por corte
- MINIMO: {min_cuts} cortes, MAXIMO: {max_cuts} cortes
- QUALITY FLOOR: viral_score >= {QUALITY_FLOOR}. NAO inclua cortes com score abaixo de {QUALITY_FLOOR}.

REGRAS DE CORTE:
- O corte DEVE comecar no INICIO de uma frase ou segmento de fala
- O corte DEVE terminar no FIM de uma frase completa ou pensamento completo
- NUNCA corte no meio de uma frase

REGRAS CRITICAS:
1. Timestamps DEVEM existir na transcricao
2. NAO invente timestamps
3. end_sec DEVE ser <= {video_duration}
4. start_sec DEVE ser < end_sec
5. Se nao houver bons cortes: array vazio com explicacao

PADROES DE HOOK:
- curiosity_gap: Pergunta que cria lacuna mental
- result_first: Mostra resultado primeiro
- pattern_interrupt: Comeca no meio da acao
- pain_point: Identifica problema comum
- fomo: Cria urgencia

O QUE NAO FAZER:
- Cortar no meio de uma frase
- Silencio > 1.5s dentro do corte
- Hook fraco nos primeiros 3s
- Duracao > {MAX_CUT_DURATION}s
- Incluir cortes com viral_score < {QUALITY_FLOOR}{extra_rules}"""


def build_chunk_prompt(chunk, video_duration, mode):
    transcription_json = json.dumps(chunk["transcription"], ensure_ascii=False)

    min_duration = MIN_CUT_DURATION
    max_cuts = 3
    extra_rules = ""
    if mode == "conservative":
        min_duration = CONSERVATIVE_MIN_CUT_DURATION
        max_cuts = 1
        extra_rules = """
MODO CONSERVADOR: 1-3 cortes com narrativa COMPLETA.
Priorize COERENCIA e VALOR sobre viralidade.
Duracao minima: 20s."""

    return f"""Analise a transcricao e identifique os melhores momentos para cortes virais.

TRANSCRICAO (chunk {chunk["chunk_id"]}, {chunk["start_time"]:.1f}s - {chunk["end_time"]:.1f}s):
{transcription_json}

DURACAO TOTAL DO VIDEO COMPLETO: {video_duration} segundos

IMPORTANTE: Esta e apenas uma PARTE do video completo ({chunk["start_time"]:.1f}s - {chunk["end_time"]:.1f}s).
Os timestamps na transcricao sao absolutos (referentes ao video completo).

FORMATO DE SAIDA (JSON obrigatorio):
{{"analysis": {{"content_type": "tutorial|vlog|interview|review|story|other", "main_topics": ["topic1", "topic2"], "overall_viral_potential": 8.5}}, "cuts": [{{"id": 1, "start_sec": 12.5, "end_sec": 38.2, "content": "Transcricao do segmento...", "hook_type": "pattern_interrupt|curiosity_gap|result_first|controversial|fomo", "hook_power": 9, "retention_potential": 8, "shareability": 7, "viral_score": 8.1, "reason": "Por que este corte funciona..."}}], "quality_warnings": ["Aviso 1"]}}

CRITERIOS:
- HOOK (0-3s): pattern_interrupt, curiosity_gap, result_first, controversial, fomo
- SCORE: viral_score = (hook x 0.4) + (retention x 0.3) + (shareability x 0.3)
- DURACAO: {min_duration}-{MAX_CUT_DURATION} segundos por corte
- MINIMO: 1 corte, MAXIMO: {max_cuts} corte(s) por chunk
- QUALITY FLOOR: viral_score >= {QUALITY_FLOOR}. NAO inclua cortes com score abaixo de {QUALITY_FLOOR}.

REGRAS DE CORTE:
- O corte DEVE comecar no INICIO de uma frase ou segmento de fala
- O corte DEVE terminar no FIM de uma frase completa ou pensamento completo
- NUNCA corte no meio de uma frase

REGRAS CRITICAS:
1. Timestamps DEVEM existir na transcricao
2. NAO invente timestamps
3. end_sec DEVE ser <= {video_duration}
4. start_sec DEVE ser < end_sec
5. start_sec DEVE ser >= {chunk["start_time"]}
6. end_sec DEVE ser <= {chunk["end_time"]}
7. Se nao houver bons cortes: array vazio com explicacao

PADROES DE HOOK:
- curiosity_gap: Pergunta que cria lacuna mental
- result_first: Mostra resultado primeiro
- pattern_interrupt: Comeca no meio da acao
- pain_point: Identifica problema comum
- fomo: Cria urgencia

O QUE NAO FAZER:
- Cortar no meio de uma frase
- Silencio > 1.5s dentro do corte
- Hook fraco nos primeiros 3s
- Duracao > {MAX_CUT_DURATION}s
- Incluir cortes com viral_score < {QUALITY_FLOOR}{extra_rules}"""
