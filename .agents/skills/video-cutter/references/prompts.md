# Prompts para Gemini

## Índice

- [Transcrição](#transcrição) — Passagem 1: áudio → texto com timestamps
- [Análise de Cortes](#análise-de-cortes) — Passagem 2: texto → segmentos virais
- [Output JSON](#output-json) — Estrutura do cuts.json

---

## Transcrição

Enviar o arquivo de áudio extraído para Gemini com este prompt:

```
Você é um transcritor profissional. Transcreva o áudio com timestamps precisos.

DURAÇÃO TOTAL DO ÁUDIO: <DURAÇÃO> segundos

FORMATO DE SAÍDA (JSON obrigatório):
{
  "transcription": [
    {"id": 1, "start_sec": 0.0, "end_sec": 5.2, "text": "..."}
  ],
  "total_duration_sec": <DURAÇÃO>,
  "language": "pt-BR",
  "audio_quality": "high"
}

REGRAS OBRIGATÓRIAS:
1. OBRIGATÓRIO: todos os timestamps (start_sec e end_sec) devem ser MENORES que total_duration_sec (<DURAÇÃO>)
2. NÃO crie entradas para pausas. Apenas transcreva o que é dito.
3. Se houver silêncio/pausa longa no áudio, simplesmente PULE e continue com o próximo segmento de fala.
4. NÃO invente timestamps. Use apenas o que você ouve no áudio.
5. Cada segmento = uma frase/unidade de fala completa.
6. Se não entender algo: "[UNCLEAR]"
7. NUNCA ultrapasse o limite de <DURAÇÃO> segundos. O último segmento DEVE terminar antes ou em <DURAÇÃO>.

VALIDAÇÃO ANTES DE RESPONDER:
- Verifique que TODOS os end_sec são <= <DURAÇÃO>
- Verifique que TODOS os start_sec são >= 0
- Verifique que end_sec > start_sec para cada segmento
```

### Dicas de transcrição

- Enviar como arquivo WAV (16kHz mono) para melhor compatibilidade
- Se o áudio for muito longo (>25min), considerar dividir em partes
- `audio_quality` deve ser: `high`, `medium` ou `low`

---

## Análise de Cortes

Após receber a transcrição, enviar este prompt com o texto transcrito:

```
Analise a transcrição e identifique os melhores momentos para cortes virais.

TRANSCRIÇÃO:
<COLE A TRANSCRIÇÃO AQUI>

DURAÇÃO TOTAL: <DURAÇÃO> segundos

FORMATO DE SAÍDA (JSON obrigatório):
{
  "analysis": {
    "content_type": "tutorial|vlog|interview|review|story|other",
    "main_topics": ["topic1", "topic2"],
    "overall_viral_potential": 8.5
  },
  "cuts": [
    {
      "id": 1,
      "start_sec": 12.5,
      "end_sec": 38.2,
      "content": "Transcrição do segmento...",
      "hook_type": "pattern_interrupt|curiosity_gap|result_first|controversial|fomo",
      "hook_power": 9,
      "retention_potential": 8,
      "shareability": 7,
      "viral_score": 8.1,
      "reason": "Por que este corte funciona..."
    }
  ],
  "quality_warnings": ["Aviso 1"]
}

CRITÉRIOS:
- HOOK (0-3s): pattern_interrupt, curiosity_gap, result_first, controversial, fomo
- SCORE: viral_score = (hook × 0.4) + (retention × 0.3) + (shareability × 0.3)
- DURAÇÃO: 15-60 segundos por corte
- MÍNIMO: 3 cortes, MÁXIMO: 8 cortes

REGRAS DE CORTE:
- O corte DEVE começar no INÍCIO de uma frase ou segmento de fala
- O corte DEVE terminar no FIM de uma frase completa ou pensamento completo
- NUNCA corte no meio de uma frase. O último segmento do corte deve terminar com pontuação natural (ponto, exclamação, interrogação) ou pausa clara
- Se o melhor momento termina no meio de uma frase, ESTENDA o corte até o final da frase

REGRAS CRÍTICAS:
1. Timestamps DEVEM existir na transcrição
2. NÃO invente timestamps
3. OBRIGATÓRIO: end_sec DEVE ser <= DURAÇÃO TOTAL (<DURAÇÃO>)
4. OBRIGATÓRIO: start_sec DEVE ser < end_sec
5. Se não houver bons cortes: array vazio com explicação

PADRÕES DE HOOK (adapte ao conteúdo do vídeo):
- curiosity_gap: Pergunta que cria lacuna mental → "O que acontece quando...", "Você sabia que..."
- result_first: Mostra resultado primeiro → "Olha o resultado...", "Veja o que acontece quando..."
- pattern_interrupt: Começa no meio da ação, sem introdução → [execução direta, sem "olá pessoal"]
- pain_point: Identifica problema comum → "Se você tem esse problema...", "Se isso acontece com você..."
- fomo: Cria urgência → "Você precisa saber isso antes de...", "Não faça isso sem saber..."

INDICADORES DE QUALIDADE (independente de conteúdo):
- hook_power 8+: Para de scrollar nos primeiros 3s
- retention_potential 8+: Mantém atenção do início ao fim
- shareability 7+: Vale enviar pra um amigo
- viral_score 7.5+: Combinado dos três acima

DURAÇÃO IDEAL POR TIPO:
- 15-25s: Dica rápida, conceito único
- 25-40s: Tutorial, explicação
- 40-60s: História, review detalhado

O QUE NÃO FAZER:
- Cortar no meio de uma frase
- Silêncio > 1.5s dentro do corte
- Hook fraco nos primeiros 3s
- Duração > 60s (perde atenção)
- Sem CTA ou frase de efeito
```

### Modo conservador

Adicionar ao final do prompt:

```
MODO CONSERVADOR: 1-3 cortes com narrativa COMPLETA.
Priorize COERÊNCIA e VALOR sobre viralidade.
Duração mínima: 20s.
```

### Tipos de hook

| Tipo | Descrição | Exemplo |
|------|-----------|---------|
| pattern_interrupt | Quebra expectativa imediata | "Você está fazendo tudo errado" |
| curiosity_gap | Cria lacuna mental | "O que ninguém te conta sobre..." |
| result_first | Mostra resultado antes | "Olha o resultado final..." |
| controversial | Posição polêmica | "Hot take: isso é inútil" |
| fomo | Medo de perder | "Você precisa saber isso antes de..." |

---

## Output JSON

Estrutura final do `./output/cuts.json`:

```json
{
  "input_video": "video.mp4",
  "output_dir": "./output",
  "generated_at": "2024-01-01T12:00:00Z",
  "mode": "aggressive",
  "cuts": [
    {
      "filename": "cut_01_12-38s.mp4",
      "path": "./output/cut_01_12-38s.mp4",
      "start_sec": 12.5,
      "end_sec": 38.2,
      "duration": 25.7,
      "hook_score": 9,
      "retention_score": 8,
      "viral_score": 8.1,
      "hook_type": "pattern_interrupt",
      "content": "Transcrição do segmento...",
      "reason": "Por que este corte funciona..."
    }
  ],
  "total_cuts": 3,
  "quality_warnings": []
}
```
