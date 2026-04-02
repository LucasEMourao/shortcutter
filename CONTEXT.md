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
│   └── 20260402_1040/               ← Ultrafast + adaptativo (vídeo 13min, 14 clips)
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
5. Status atual: Análise adaptativa + FFmpeg ultrafast implementados e testados
6. Questão em aberto: Ajustar CRF para reduzir tamanho dos arquivos? (atual: CRF 23, ultrafast, arquivos 5-24x maiores que preset fast)
7. Próximo passo: Validar cortes gerados em players de vídeo, decidir sobre CRF

## Resultados da última execução (20260402_1040 — Ultrafast + Adaptativo)

### Vídeo de 13min (data centers) — Ultrafast + Chunked Analysis

| Corte | Timestamp | Duração | Score | Hook |
|-------|-----------|---------|-------|------|
| 1 | 13.0s–35.2s | 22.2s | 8.0 | pattern_interrupt |
| 2 | 100.8s–134.6s | 33.8s | 9.4 | curiosity_gap |
| 3 | 140.6s–158.9s | 18.3s | 8.6 | controversial |
| 4 | 230.7s–253.8s | 23.1s | 8.4 | pain_point |
| 5 | 268.8s–300.3s | 31.5s | 7.7 | curiosity_gap |
| 6 | 313.8s–352.2s | 38.4s | 7.6 | result_first |
| 7 | 384.3s–423.0s | 38.7s | 8.4 | curiosity_gap |
| 8 | 438.8s–472.5s | 33.7s | 8.3 | result_first |
| 9 | 472.5s–504.1s | 31.6s | 7.6 | pain_point |
| 10 | 504.1s–555.9s | 51.8s | 8.4 | curiosity_gap |
| 11 | 581.7s–619.7s | 38.0s | 8.7 | controversial |
| 12 | 670.0s–689.4s | 19.4s | 8.4 | curiosity_gap |
| 13 | 705.7s–736.9s | 31.2s | 7.7 | controversial |
| 14 | 752.8s–781.8s | 29.0s | 8.0 | pattern_interrupt |

**FFmpeg:**
- Preset: ultrafast (vs fast anterior)
- Tempo de geração: ~3.5min (antes: timeout)
- Precisão de corte: perfeita (todos os timestamps exatos)
- Tamanho dos arquivos: 5-24x maior que preset fast

### Vídeo de 4min (curto) — Análise Direta (sem chunking)

| Corte | Timestamp | Duração | Score | Hook |
|-------|-----------|---------|-------|------|
| 1 | 11.0s–41.0s | 30.0s | 7.85 | curiosity_gap |
| 2 | 102.0s–131.0s | 29.0s | 8.85 | result_first |
| 3 | 131.0s–168.0s | 37.0s | 8.05 | pattern_interrupt |
| 4 | 180.0s–218.0s | 38.0s | 9.25 | curiosity_gap |

**Economia:** 1 chamada API vs ~2 com chunking (50% menos)

**Chunking info:**
- Chunks de 3 minutos (>10min) ou 4 minutos (5-10min)
- Overlap de 5 segmentos
- Quality floor: viral_score >= 7.5
- Merge inteligente remove duplicatas (>80% sobreposição)
- Análise direta para vídeos < 5min

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
