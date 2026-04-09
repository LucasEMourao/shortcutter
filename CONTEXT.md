# CONTEXTO PARA NOVA CONVERSA - shortcutter

## O que fizemos até agora

1. **Analisamos o projeto OpenCut** como referência conceitual (não reutilizamos código)
2. **Identificamos aprendizados** importantes:
   - Sanitização determinística de timestamps em código (não no prompt)
   - Duas passagens: transcrição primeiro, depois análise
   - FFmpeg nativo em vez de WASM
   - Validação de timestamps em 3 camadas
   - Structured output via Gemini API

3. **Instalamos skill-creator** como referência de spec oficial:
   - `npx skills add https://github.com/anthropics/skills --skill skill-creator`
   - Instalada em `.agents/skills/skill-creator/`

4. **Reestruturamos a skill video-cutter** seguindo a spec oficial:
   - YAML frontmatter no SKILL.md
   - Scripts separados em `scripts/`
   - Referências detalhadas em `references/`
   - Exemplos em `examples/`

5. **Testamos e refinamos a skill** com vídeo real:
   - GEMINI_API_KEY configurada via `.env`
   - Vídeo de teste: 535s (WhatsApp guitarra Fender Ultra)
   - 4 clips gerados com sucesso
   - Buffer inteligente implementado

6. **Automatizamos o fluxo** com `scripts/run.sh`:
   - Script que executa todos os 9 passos do SKILL.md
   - Carrega `.env` automaticamente
   - Gera clips em `./output/YYYYMMDD_HHMM/`
   - Cria `cuts.json` com metadados

7. **Validamos buffer e alinhamento** (26/03/2026):
   - Investigação: código OK (2.0s), output antigo 1.5s era de versão anterior
   - Execução 20260326_1401 confirmou buffer correto
   - 4 clips válidos: 28.4s–47.5s, scores 7.4–8.7
   - Nenhuma sobreposição, durações 15–60s ✓
   - Cobertura: 28.8% do vídeo (154s de 535s)

8. **Descobrimos e resolvemos o problema de alucinação do Gemini** (30/03/2026):
   - Gemini alucinava conteúdo da transcrição (Cut 1 com 0% de match com áudio real)
   - Testamos chunked transcription (chunks de 4min) — melhorou mas não resolveu
   - Descobrimos que Gemini não é modelo de transcrição — gera texto pelo significado, não palavra por palavra
   - Instalamos faster-whisper (modelo small, local, sem API) para transcrição
   - Resultado: Cut 1 passou de 0% para 69% de similaridade de conteúdo
   - Trocamos modelo de análise para gemini-2.5-flash (20 req/dia free tier)
   - Criamos validate_cuts.py para validação estrutural e de conteúdo
   - Instalamos skill gemini-api-dev como referência de API
   - Fix: ordenação por timestamp antes de verificação de sobreposição

9. **Resolvemos o problema de cobertura baixa com chunked analysis** (31/03/2026):
   - Identificamos que Gemini ignorava início e final de vídeos longos (cobertura 21-29%)
   - Testamos com 6 vídeos diferentes (4min, 9min, 12min, 13min, 16min, 17min)
   - Problema era attention bias — modelo foca no meio de textos longos
   - Implementamos chunked analysis (chunks de 3min com overlap de 5 segmentos)
   - Adicionamos quality floor (viral_score mínimo 7.5)
   - Resultados: cobertura dobrou (28%→58% vlog, 22%→44% tutorial)
   - Início e final do vídeo agora são capturados corretamente
   - Criação do script `analyze_chunked.py`
   - Modificação do `run.sh` para usar chunked analysis

10. **Implementamos fallback entre modelos e retry com backoff** (01/04/2026):
    - Descobrimos que quota real do gemini-2.5-flash free tier é 20 req/dia (não 250)
    - Rodamos todos os 6 vídeos com chunked analysis
    - Implementamos fallback automático: gemini-2.5-flash → gemini-3-flash-preview → gemini-3.1-flash-lite-preview
    - Implementamos retry com backoff (até 3 tentativas, 10s/20s/30s) para erros 503 (overload)
    - Todos os vídeos processados com sucesso mesmo após exceder quota do modelo primário
    - Cobertura final validada: 79-98% em todos os vídeos testados

11. **Descoberta dinâmica de modelos via API** (01/04/2026):
    - Substituímos fallback hardcoded por descoberta via endpoint /v1beta/models
    - API retorna modelos disponíveis em tempo real (9 modelos flash encontrados)
    - Ordenação: não-lite primeiro (mais capazes), depois versão descendente
    - Se Google lançar novo modelo, será usado automaticamente sem alterar código
    - Resultado: cobertura equivalente, com mais opções de fallback

12. **Análise adaptativa e FFmpeg otimizado** (02/04/2026):
    - Descoberta: chunking é overkill para vídeos curtos (<5min)
    - Implementamos `analyze_adaptive.py` com estratégia por duração:
      - < 5min → análise direta (1 chamada API, economiza 50%)
      - 5-10min → chunks de 4min (2-3 chamadas)
      - > 10min → chunks de 3min (4-6 chamadas, padrão atual)
    - Testado com sucesso: vídeo 4min (análise direta, 3 clips) e 13min (chunked, 14 clips)
    - Timeout do FFmpeg resolvido: `preset fast` → `preset ultrafast`
    - Stream copy testado mas descartado (cortes imprecisos por keyframe alignment)
    - Ultrafast: 14 clips em ~3.5min (antes: timeout), precisão de timestamps perfeita
    - Trade-off: arquivos 5-24x maiores que `preset fast` (CRF 23, ultrafast)
    - Questão em aberto: ajustar CRF para reduzir tamanho dos arquivos?

13. **Teste completo com 6 vídeos + bug fixes** (09/04/2026):
    - Rodou a skill em todos os 6 vídeos de teste (do menor para o maior)
    - Todos processados com sucesso com cuts.json gerado
    - Switchover de modelo automático funcionou (fallback gemini-3-flash → gemini-2.5-flash → gemini-3.1-flash-lite-preview)
    - Bug encontrado e corrigido: GEMINI_MODEL ficava vazio no resumo final
    - Bug encontrado e corrigido: cortes podiam ficar abaixo de 15s após correção de sobreposição
    - Resultado detalhado por vídeo:
      - 4min (curto): 4 clips, análise direta, scores 7.7-9.7
      - 9min (WhatsApp): 6 clips, chunked 4min, scores 7.7-8.7
      - 12min (standup): 13 clips, chunked 3min, scores 8.3-10.0
      - 13min (data centers): 14 clips, chunked 3min, scores 7.7-9.0
      - 15min (podcast): 13 clips, chunked 3min, scores 8.0-9.0
      - 17min (tutorial): 13 clips, chunked 3min, scores 7.7-8.7 (1 clip <15s removido pelo fix)

## Estrutura atual do projeto

```
~/projetos/shortcutter/
├── .agents/
│   └── skills/
│       ├── skill-creator/           ← Referência de spec oficial
│       │   ├── SKILL.md
│       │   ├── agents/
│       │   ├── scripts/
│       │   └── ...
│       ├── video-cutter/            ← Nossa skill
│       │   ├── SKILL.md             ← YAML frontmatter + fluxo conciso
│       │   ├── scripts/
│       │   │   ├── helper.sh        ← FFmpeg utils
│       │   │   ├── run.sh           ← Automação completa
│       │   │   ├── analyze_chunked.py ← Chunked analysis (3min chunks)
│       │   │   ├── analyze_adaptive.py ← Análise adaptativa (<5min direto, >5min chunked)
│       │   │   └── validate_cuts.py ← Validação de output
│       │   ├── references/
│       │   │   ├── prompts.md       ← Prompts Gemini detalhados
│       │   │   └── ffmpeg.md        ← Comandos FFmpeg
│       │   └── examples/
│       │       └── examples.md      ← Exemplos de uso
│       ├── gemini-api-dev/          ← Skill de referência Google
│       │   └── SKILL.md             ← Modelos, SDKs, limites API
│       └── skills_index.json
├── .env                             ← API key configurada
├── AGENTS.md                        ← Instruções para commits
├── CONTEXT.md                       ← Este arquivo
├── PLANO.md                         ← Plano de desenvolvimento
├── test/
│   ├── WhatsApp Video 2026-03-25 at 14.35.40.mp4
│   ├── videoTeste13min.mp4          ← Vídeo de teste longo
│   ├── videoTeste17min.mp4          ← Vídeo de teste tutorial
│   ├── videoTestePodcast15min.mp4   ← Vídeo de teste podcast
│   ├── videoStandup12min.mp4        ← Vídeo de teste comédia
│   └── videoCurtoParaTeste4min.mp4  ← Vídeo de teste curto
├── output/                          ← Clips gerados
│   ├── ...                          ← Runs anteriores
│   ├── 20260326_1401/               ← Buffer 2.0s validado (vídeo 9min)
│   ├── 20260331_0024/               ← Whisper validado (vídeo 13min)
│   ├── 20260331_1439/               ← Chunked analysis (vídeo 13min)
│   ├── 20260331_1757/               ← Chunked analysis (vídeo 17min)
│   ├── 20260402_0955/               ← Análise adaptativa direta (vídeo 4min)
│   ├── 20260402_1020/               ← Stream copy test (vídeo 9min, descartado)
│   ├── 20260402_1037/               ← Ultrafast test (vídeo 4min)
│   ├── 20260402_1040/               ← Ultrafast + adaptativo (vídeo 13min, 14 clips)
│   ├── 20260409_0955/               ← Vídeo 4min (4 clips, score 7.7-9.7)
│   ├── 20260409_1000/               ← Vídeo 9min (6 clips, score 7.7-8.7)
│   ├── 20260409_1020/               ← Vídeo 12min (13 clips, score 8.3-10.0)
│   ├── 20260409_1032/               ← Vídeo 13min (14 clips, score 7.7-9.0)
│   ├── 20260409_1044/               ← Vídeo 15min (13 clips, score 8.0-9.0)
│   └── 20260409_1058/               ← Vídeo 17min (13 clips, score 7.7-8.7)
└── skills-lock.json                 ← Gerado pelo npx skills
```

## O que está pronto ✅

- ✅ Skill-creator instalada como referência
- ✅ Skill gemini-api-dev instalada (referência de modelos e quotas)
- ✅ SKILL.md com YAML frontmatter (`disable-model-invocation: true`)
- ✅ Fluxo de 9 passos documentado
- ✅ scripts/helper.sh com comandos FFmpeg
- ✅ scripts/run.sh com automação completa
- ✅ scripts/analyze_chunked.py com chunked analysis (3min chunks, overlap 5 segmentos)
- ✅ scripts/analyze_adaptive.py com análise adaptativa (<5min direto, 5-10min chunks 4min, >10min chunks 3min)
- ✅ scripts/validate_cuts.py com validação estrutural e de conteúdo
- ✅ FFmpeg helper.sh com preset ultrafast (precisão de corte + velocidade, trade-off: arquivos maiores)
- ✅ references/prompts.md com prompts Gemini otimizados
- ✅ references/ffmpeg.md com comandos de referência
- ✅ examples/examples.md com referências genéricas de qualidade
- ✅ skills_index.json atualizado
- ✅ GEMINI_API_KEY configurada via `.env`
- ✅ faster-whisper instalado para transcrição local
- ✅ Modelo de análise: modelos Flash descobertos dinamicamente via API (mais recente primeiro)
- ✅ Buffer inteligente implementado (MAX_GAP=2.0s, BUFFER=2.0s)
- ✅ Quality floor implementado (viral_score mínimo 7.5)
- ✅ Chunked analysis implementado (cobertura 2x maior)
- ✅ Referências genéricas de qualidade no prompt (hook patterns, quality indicators)
- ✅ Testes realizados com sucesso (6 vídeos diferentes)

## Como usar a skill

**Via script (recomendado):**
```bash
cd ~/projetos/shortcutter
./.agents/skills/video-cutter/scripts/run.sh ./video.mp4
```

**Via agente (conversa):**
```
Analise o vídeo ./video.mp4 e gere cortes para TikTok
```

## Comandos úteis

```bash
# Executar skill com script
./.agents/skills/video-cutter/scripts/run.sh ./video.mp4

# Modo conservador
./.agents/skills/video-cutter/scripts/run.sh ./video.mp4 ./output conservative

# Verificar estrutura
find ~/projetos/shortcutter/.agents -type f | sort

# Testar script auxiliar
~/projetos/shortcutter/.agents/skills/video-cutter/scripts/helper.sh info ./video.mp4
```

## Para continuar em nova conversa

1. Abra terminal em ~/projetos/shortcutter
2. Inicie nova conversa com o agente
3. Cole este documento como contexto inicial
4. Diga: "Continuar desenvolvimento da AgentSkill video-cutter"
5. Status atual: Análise adaptativa + FFmpeg ultrafast + bug fixes aplicados
6. Todos os 6 vídeos processados com sucesso (09/04/2026)
7. Bugs corrigidos: GEMINI_MODEL vazio no resumo, cortes <15s após sobreposição
8. Questão em aberto: Ajustar CRF para reduzir tamanho dos arquivos? (atual: CRF 23, ultrafast)
9. Próximo passo: Validar cortes manualmente, decidir sobre CRF

## Resultados da última execução completa (09/04/2026 — 6 vídeos)

### Vídeo de 4min (curto) — Análise Direta

| Corte | Timestamp | Duração | Score | Hook |
|-------|-----------|---------|-------|------|
| 1 | 16s–65s | 49.0s | 8.4 | curiosity_gap |
| 2 | 113s–138s | 25.0s | 8.7 | curiosity_gap |
| 3 | 138s–168s | 30.0s | 7.7 | curiosity_gap |
| 4 | 178s–218s | 40.0s | 9.7 | pattern_interrupt |

### Vídeo de 9min (WhatsApp) — Chunked 4min

| Corte | Timestamp | Duração | Score | Hook |
|-------|-----------|---------|-------|------|
| 1 | 20s–61s | 41.0s | 8.4 | curiosity_gap |
| 2 | 61s–88s | 27.0s | 8.0 | result_first |
| 3 | 105s–126s | 21.0s | 8.0 | result_first |
| 4 | 424s–448s | 24.0s | 7.7 | result_first |
| 5 | 466s–483s | 17.0s | 8.7 | result_first |
| 6 | 511s–528s | 17.0s | 8.3 | curiosity_gap |

### Vídeo de 12min (standup) — Chunked 3min

| Corte | Timestamp | Duração | Score | Hook |
|-------|-----------|---------|-------|------|
| 1 | 47s–74s | 27.0s | 8.7 | controversial |
| 2 | 74s–96s | 22.0s | 9.0 | pattern_interrupt |
| 3 | 153s–178s | 25.0s | 10.0 | controversial |
| 4 | 193s–218s | 25.0s | 8.3 | pattern_interrupt |
| 5 | 264s–287s | 23.0s | 8.4 | curiosity_gap |
| 6 | 303s–331s | 28.0s | 9.3 | controversial |
| 7 | 342s–390s | 48.0s | 9.0 | controversial |
| 8 | 432s–452s | 20.0s | 8.8 | curiosity_gap |
| 9 | 491s–525s | 34.0s | 8.5 | controversial |
| 10 | 539s–586s | 47.0s | 9.0 | curiosity_gap |
| 11 | 616s–656s | 40.0s | 9.4 | controversial |
| 12 | 662s–682s | 20.0s | 9.0 | pattern_interrupt |
| 13 | 682s–712s | 30.0s | 8.4 | controversial |

### Vídeo de 13min (data centers) — Chunked 3min

| Corte | Timestamp | Duração | Score | Hook |
|-------|-----------|---------|-------|------|
| 1 | 13s–35s | 22.2s | 8.0 | curiosity_gap |
| 2 | 100s–134s | 33.8s | 9.0 | controversial |
| 3 | 140s–162s | 22.3s | 8.0 | fomo |
| 4 | 232s–253s | 20.8s | 8.7 | curiosity_gap |
| 5 | 268s–296s | 27.8s | 7.7 | pattern_interrupt |
| 6 | 367s–391s | 24.6s | 8.4 | curiosity_gap |
| 7 | 403s–423s | 19.3s | 9.0 | pattern_interrupt |
| 8 | 458s–479s | 21.7s | 8.0 | curiosity_gap |
| 9 | 504s–553s | 49.8s | 8.1 | curiosity_gap |
| 10 | 553s–581s | 27.8s | 8.7 | result_first |
| 11 | 581s–619s | 38.0s | 8.0 | controversial |
| 12 | 670s–689s | 19.4s | 8.7 | curiosity_gap |
| 13 | 702s–724s | 21.0s | 8.0 | curiosity_gap |
| 14 | 748s–781s | 33.6s | 7.7 | pattern_interrupt |

### Vídeo de 15min (podcast) — Chunked 3min

| Corte | Timestamp | Duração | Score | Hook |
|-------|-----------|---------|-------|------|
| 1 | 0s–38s | 38.5s | 8.4 | curiosity_gap |
| 2 | 83s–121s | 37.0s | 8.4 | controversial |
| 3 | 126s–156s | 29.0s | 8.0 | curiosity_gap |
| 4 | 253s–274s | 20.9s | 8.7 | curiosity_gap |
| 5 | 282s–316s | 34.0s | 8.4 | controversial |
| 6 | 323s–342s | 19.0s | 8.0 | pattern_interrupt |
| 7 | 361s–383s | 22.0s | 9.0 | controversial |
| 8 | 429s–466s | 37.0s | 8.0 | curiosity_gap |
| 9 | 554s–577s | 23.0s | 8.7 | curiosity_gap |
| 10 | 625s–646s | 21.0s | 8.7 | result_first |
| 11 | 737s–779s | 42.0s | 8.7 | curiosity_gap |
| 12 | 811s–854s | 43.0s | 9.0 | pattern_interrupt |
| 13 | 854s–891s | 37.0s | 8.7 | controversial |

### Vídeo de 17min (tutorial) — Chunked 3min

| Corte | Timestamp | Duração | Score | Hook |
|-------|-----------|---------|-------|------|
| 1 | 92s–124s | 32.6s | 8.55 | result_first |
| 2 | 149s–167s | 18.1s | 7.85 | fomo |
| 3 | 181s–226s | 44.2s | 8.7 | fomo |
| 4 | 279s–322s | 42.9s | 8.7 | result_first |
| 5 | 343s–378s | 35.2s | 8.7 | result_first |
| 6 | 452s–483s | 30.9s | 8.3 | pattern_interrupt |
| 7 | 515s–549s | 33.6s | 8.7 | result_first |
| 8 | 639s–671s | 31.9s | 8.0 | curiosity_gap |
| 9 | 706s–724s | 18.3s | 8.7 | result_first |
| 10 | 811s–845s | 33.7s | 8.4 | result_first |
| 11 | 875s–910s | 35.7s | 7.7 | pain_point |
| 12 | 997s–1018s | 20.2s | 8.4 | fomo |

**Nota:** 13 cortes gerados, 1 removido por sobreposição resultar em duração <15s (cut 10 original: 798-811s = 12.9s)

## Limitação atual

- **Transcrição:** Whisper local (sem custo, sem limite de quota)
- **Análise:** Modelos Flash descobertos dinamicamente via API (~6 chamadas por run), 20 req/dia por modelo no free tier
- **Fallback:** Modelos descobertos dinamicamente via API. Percorre todos os Flash disponíveis até encontrar um com quota
- **Retry:** Erros 503 (overload) têm retry automático com backoff (até 3 tentativas)
- **Impacto:** ~3 runs/dia por modelo no free tier (20 req ÷ ~6 chamadas/run), mas com fallback entre 9 modelos permite muito mais
- **Dependência:** faster-whisper precisa de `pip install --user --break-system-packages faster-whisper`

## Decisões técnicas importantes

1. **Duas passagens separadas:**
   - Passagem 1: Whisper transcreve áudio localmente (sem API)
   - Passagem 2: Gemini analisa e identifica cortes virais (~6 chamadas API com chunking)

2. **Chunked analysis:**
   - Divide transcrição em chunks de 3 minutos com overlap de 5 segmentos
   - Analisa cada chunk separadamente (1-3 cortes por chunk)
   - Merge inteligente remove duplicatas por sobreposição >80%
   - Quality floor: viral_score mínimo 7.5
   - Resultado: cobertura 2x maior, início e final capturados

2. **Análise adaptativa:**
   - < 5min: análise direta (1 chamada API, sem chunking)
   - 5-10min: chunks de 4 minutos (2-3 chamadas)
   - > 10min: chunks de 3 minutos (4-6 chamadas)
   - Script: analyze_adaptive.py (substitui analyze_chunked.py no run.sh)

2. **Anti-alucinação:**
   - Whisper é modelo dedicado para transcrição — não alucina
   - Timestamps precisos por segmento (precisão de centésimos)
   - Gemini usado apenas para análise, nunca para transcrição
   - Chunked analysis força análise de cada parte do vídeo

3. **Modos de operação:**
   - Agressivo: 3-8 cortes, foco viralidade
   - Conservador: 1-3 cortes, foco narrativa

4. **Buffer inteligente:**
   - MAX_GAP = 2.0s (estende até próximo segmento se gap ≤ 2s)
   - BUFFER = 2.0s (buffer fixo se gap > 2s)
   - Evita cortar palavras no meio

5. **Modelos de IA:**
   - Transcrição: faster-whisper small (local, CPU, int8)
   - Análise: modelos Flash descobertos dinamicamente via API (/v1beta/models)
   - Ordenação: não-lite primeiro (mais capazes), depois versão descendente
   - Fallback automático: percorre todos os modelos até encontrar um com quota
   - Retry: erros 503 têm backoff automático (10s/20s/30s)
   - Modelos atuais (exemplo): gemini-3-flash → gemini-2.5-flash → gemini-2.0-flash → ... → gemini-3.1-flash-lite → gemini-2.5-flash-lite

6. **Referências genéricas de qualidade:**
   - Padrões de hook (curiosity_gap, result_first, pattern_interrupt, pain_point, fomo)
   - Indicadores de qualidade (hook_power, retention_potential, shareability)
   - Duração ideal por tipo (15-25s, 25-40s, 40-60s)

7. **Chunked analysis:**
   - CHUNK_DURATION_SEC = 180 (3 minutos por chunk)
   - CHUNK_OVERLAP_SEGMENTS = 5 (overlap entre chunks)
   - QUALITY_FLOOR = 7.5 (score mínimo para incluir corte)
   - Merge inteligente remove duplicatas por sobreposição >80%

8. **Validação de output:**
   - validate_cuts.py: validação estrutural sem API
   - Opção --verify-content: usa Gemini para verificar se áudio real bate com JSON

9. **Bug fixes (09/04/2026):**
   - GEMINI_MODEL ficava vazio no resumo — agora extrai model_used do analysis.json
   - Cortes podiam ficar abaixo de 15s após correção de sobreposição — agora removidos e renumerados
