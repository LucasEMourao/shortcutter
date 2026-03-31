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
│   └── videoTeste13min.mp4          ← Vídeo de teste longo
├── output/                          ← Clips gerados
│   ├── ...                          ← Runs anteriores
│   ├── 20260326_1401/               ← Buffer 2.0s validado (vídeo 9min)
│   └── 20260331_0024/               ← Whisper validado (vídeo 13min)
└── skills-lock.json                 ← Gerado pelo npx skills
```

## O que está pronto ✅

- ✅ Skill-creator instalada como referência
- ✅ Skill gemini-api-dev instalada (referência de modelos e quotas)
- ✅ SKILL.md com YAML frontmatter (`disable-model-invocation: true`)
- ✅ Fluxo de 9 passos documentado
- ✅ scripts/helper.sh com comandos FFmpeg
- ✅ scripts/run.sh com automação completa
- ✅ scripts/validate_cuts.py com validação estrutural e de conteúdo
- ✅ references/prompts.md com prompts Gemini otimizados
- ✅ references/ffmpeg.md com comandos de referência
- ✅ examples/examples.md com referências genéricas de qualidade
- ✅ skills_index.json atualizado
- ✅ GEMINI_API_KEY configurada via `.env`
- ✅ faster-whisper instalado para transcrição local
- ✅ Modelo de análise: `gemini-2.5-flash` (250 req/dia)
- ✅ Buffer inteligente implementado (MAX_GAP=2.0s, BUFFER=2.0s)
- ✅ Referências genéricas de qualidade no prompt (hook patterns, quality indicators)
- ✅ Testes realizados com sucesso (vídeo 9min e 13min)

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

## Resultados da última execução (20260331_0024 — Whisper)

| Corte | Timestamp | Duração | Score | Hook |
|-------|-----------|---------|-------|------|
| 1 | 9.1s–54.6s | 45.5s | 8.7 | curiosity_gap |
| 2 | 100.8s–134.6s | 33.8s | 9.7 | result_first |
| 3 | 294.6s–355.6s | 61.0s | 8.3 | curiosity_gap |
| 4 | 367.2s–423.0s | 55.8s | 9.0 | pattern_interrupt |
| 5 | 485.8s–513.8s | 28.0s | 8.7 | curiosity_gap |

**Validação:**
- ✅ Transcrição: 319 segmentos via Whisper (sem alucinação)
- ✅ Cut 1: 69% de similaridade de conteúdo (era 0% com Gemini)
- ✅ Todos os clips válidos (tamanhos 1.9M–5.0M)
- ✅ Nenhuma sobreposição entre cortes
- ⚠️ Cut 3: 61.0s (1s acima do limite de 60s)

## Limitação atual

- **Transcrição:** Whisper local (sem custo, sem limite de quota)
- **Análise:** `gemini-2.5-flash` — 1 chamada por run, 250 req/dia
- **Impacto:** permite ~250 runs/dia (vs ~10 antes com gemini-3-flash-preview)
- **Dependência:** faster-whisper precisa de `pip install --user --break-system-packages faster-whisper`

## Decisões técnicas importantes

1. **Duas passagens separadas:**
   - Passagem 1: Whisper transcreve áudio localmente (sem API)
   - Passagem 2: Gemini analisa e identifica cortes virais (1 chamada API)

2. **Anti-alucinação:**
   - Whisper é modelo dedicado para transcrição — não alucina
   - Timestamps precisos por segmento (precisão de centésimos)
   - Gemini usado apenas para análise, nunca para transcrição

3. **Modos de operação:**
   - Agressivo: 3-8 cortes, foco viralidade
   - Conservador: 1-3 cortes, foco narrativa

4. **Buffer inteligente:**
   - MAX_GAP = 2.0s (estende até próximo segmento se gap ≤ 2s)
   - BUFFER = 2.0s (buffer fixo se gap > 2s)
   - Evita cortar palavras no meio

5. **Modelos de IA:**
   - Transcrição: faster-whisper small (local, CPU, int8)
   - Análise: `gemini-2.5-flash` (250 req/dia, estável)

6. **Referências genéricas de qualidade:**
   - Padrões de hook (curiosity_gap, result_first, pattern_interrupt, pain_point, fomo)
   - Indicadores de qualidade (hook_power, retention_potential, shareability)
   - Duração ideal por tipo (15-25s, 25-40s, 40-60s)

7. **Validação de output:**
   - validate_cuts.py: validação estrutural sem API
   - Opção --verify-content: usa Gemini para verificar se áudio real bate com JSON
