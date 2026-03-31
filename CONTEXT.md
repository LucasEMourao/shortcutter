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
   - Trocamos modelo de análise para gemini-2.5-flash (250 req/dia)
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
│   └── 20260331_1757/               ← Chunked analysis (vídeo 17min)
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
- ✅ scripts/validate_cuts.py com validação estrutural e de conteúdo
- ✅ references/prompts.md com prompts Gemini otimizados
- ✅ references/ffmpeg.md com comandos de referência
- ✅ examples/examples.md com referências genéricas de qualidade
- ✅ skills_index.json atualizado
- ✅ GEMINI_API_KEY configurada via `.env`
- ✅ faster-whisper instalado para transcrição local
- ✅ Modelo de análise: `gemini-2.5-flash` (250 req/dia)
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
5. Status atual: Chunked analysis implementado e testado com 2 vídeos
6. Próximo passo: testar com mais vídeos ou implementar melhorias adicionais

## Resultados da última execução (20260331_1439 — Chunked Analysis)

### Vídeo de 13min (data centers) — Chunked Analysis

| Corte | Timestamp | Duração | Score | Hook |
|-------|-----------|---------|-------|------|
| 1 | 7.5s–54.6s | 47.1s | 8.4 | curiosity_gap |
| 2 | 100.8s–132.6s | 31.8s | 9.0 | result_first |
| 3 | 132.6s–158.9s | 26.3s | 8.0 | controversial |
| 4 | 203.0s–248.6s | 45.6s | 8.7 | curiosity_gap |
| 5 | 251.8s–283.7s | 31.9s | 7.7 | pattern_interrupt |
| 6 | 301.6s–339.2s | 37.6s | 8.7 | curiosity_gap |
| 7 | 403.7s–421.0s | 17.2s | 8.0 | curiosity_gap |
| 8 | 421.0s–470.2s | 49.2s | 9.0 | curiosity_gap |
| 9 | 485.8s–511.8s | 26.0s | 8.7 | curiosity_gap |
| 10 | 511.8s–555.9s | 44.1s | 8.4 | curiosity_gap |
| 11 | 581.7s–619.7s | 38.0s | 8.4 | result_first |
| 12 | 651.2s–686.9s | 35.7s | 8.4 | controversial |
| 13 | 715.0s–731.9s | 16.9s | 7.7 | pattern_interrupt |
| 14 | 773.1s–792.8s | 19.7s | 8.0 | controversial |

**Melhoria vs sem chunking:**
- Cortes: 5 → 14 (+180%)
- Cobertura: 28.7% → 57.7% (+101%)
- Final capturado: 513.8s → 792.8s (+279s)

### Vídeo de 17min (tutorial) — Chunked Analysis

**Melhoria vs sem chunking:**
- Cortes: 7 → 16 (+129%)
- Cobertura: 21.7% → 44.2% (+104%)
- Início capturado: 171.2s → 60.0s (+111s)
- Final capturado: 845.3s → 1057.8s (+212s)

**Chunking info:**
- Chunks de 3 minutos
- Overlap de 5 segmentos
- Quality floor: viral_score >= 7.5
- Merge inteligente remove duplicatas (>80% sobreposição)

## Limitação atual

- **Transcrição:** Whisper local (sem custo, sem limite de quota)
- **Análise:** `gemini-2.5-flash` — ~6 chamadas por run (chunked), 250 req/dia
- **Impacto:** permite ~40 runs/dia (vs ~250 antes com 1 chamada/run)
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
   - Análise: `gemini-2.5-flash` (250 req/dia, estável, ~6 chamadas/run)

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
