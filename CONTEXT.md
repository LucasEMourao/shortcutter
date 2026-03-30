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
│       │   │   └── run.sh           ← Automação completa
│       │   ├── references/
│       │   │   ├── prompts.md       ← Prompts Gemini detalhados
│       │   │   └── ffmpeg.md        ← Comandos FFmpeg
│       │   └── examples/
│       │       └── examples.md      ← Exemplos de uso
│       └── skills_index.json
├── .env                             ← API key configurada
├── CONTEXT.md                       ← Este arquivo
├── PLANO.md                         ← Plano de desenvolvimento
├── test/
│   └── WhatsApp Video 2026-03-25 at 14.35.40.mp4  ← Vídeo de teste
├── output/                          ← Clips gerados
│   ├── ...                          ← 14 runs anteriores
│   ├── 20260326_1344/               ← Último run com buffer antigo (1.5s)
│   └── 20260326_1401/               ← Último run validado (buffer 2.0s correto)
└── skills-lock.json                 ← Gerado pelo npx skills
```

## O que está pronto ✅

- ✅ Skill-creator instalada como referência
- ✅ SKILL.md com YAML frontmatter (`disable-model-invocation: true`)
- ✅ Fluxo de 9 passos documentado
- ✅ scripts/helper.sh com comandos FFmpeg
- ✅ scripts/run.sh com automação completa
- ✅ references/prompts.md com prompts Gemini otimizados
- ✅ references/ffmpeg.md com comandos de referência
- ✅ examples/examples.md com referências genéricas de qualidade
- ✅ skills_index.json atualizado
- ✅ GEMINI_API_KEY configurada via `.env`
- ✅ Modelo definido: `gemini-3-flash-preview`
- ✅ Buffer inteligente implementado (MAX_GAP=2.0s, BUFFER=2.0s)
- ✅ Sanitização de timestamps (Passo 4)
- ✅ Referências genéricas de qualidade no prompt (hook patterns, quality indicators)
- ✅ Testes realizados com sucesso

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

## Resultados da última execução (20260326_1401)

| Corte | Timestamp | Duração | Score | Hook | Buffer |
|-------|-----------|---------|-------|------|--------|
| 1 | 19.3s–62.0s | 42.7s | 8.4 | curiosity_gap | 2.0s fixo (gap 2.1s) |
| 2 | 62.1s–90.5s | 28.4s | 8.3 | pain_point | 2.0s fixo (gap 58.1s) |
| 3 | 448.3s–484.2s | 35.9s | 8.7 | result_first | 1.7s estendido (gap 1.7s) |
| 4 | 487.7s–535.1s | 47.5s | 7.4 | pattern_interrupt | 2.3s até fim do vídeo |

**Validação:**
- ✅ Buffer 2.0s funcionando corretamente
- ✅ Nenhuma sobreposição entre cortes
- ✅ Todas durações entre 15–60s
- ✅ Clips MP4 válidos (tamanhos 3.4M–7.7M)
- ⚠️ Gap de 358s não coberto (90s→448s) — conteúdo do vídeo, não é bug
- ⚠️ Cobertura 28.8% — pode aumentar com mais segmentos na transcrição

## Limitação atual

- **Gemini API free tier:** 20 requisições/dia por modelo
- **Modelo usado:** gemini-3-flash-preview
- **Impacto:** ~2 chamadas por run (transcrição + análise), permite ~10 runs/dia
- **Alternativa:** upgrade de plano ou usar modelo com quota maior

## Decisões técnicas importantes

1. **Duas passagens separadas:**
   - Passagem 1: Transcrição áudio → timestamps precisos
   - Passagem 2: Análise cortes → segmentos virais

2. **Anti-alucinação:**
   - Timestamps baseados apenas na transcrição
   - Validação determinística em código
   - Não estimar ou inventar timestamps

3. **Modos de operação:**
   - Agressivo: 3-8 cortes, foco viralidade
   - Conservador: 1-3 cortes, foco narrativa

4. **Buffer inteligente:**
   - MAX_GAP = 2.0s (estende até próximo segmento se gap ≤ 2s)
   - BUFFER = 2.0s (buffer fixo se gap > 2s)
   - Evita cortar palavras no meio
   - Princípio: melhor ter um pouco mais do que cortar demais

5. **Modelo de IA:**
   - Modelo principal: `gemini-3-flash-preview`
   - Respeita duração do vídeo
   - Não necessita normalização de timestamps

6. **Referências genéricas de qualidade:**
   - Padrões de hook (curiosity_gap, result_first, pattern_interrupt, pain_point, fomo)
   - Indicadores de qualidade (hook_power, retention_potential, shareability)
   - Duração ideal por tipo (15-25s, 25-40s, 40-60s)
   - Funciona para qualquer tipo de vídeo (não específico para guitarra)
