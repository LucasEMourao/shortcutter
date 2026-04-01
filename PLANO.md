# PLANO - Fazer a Skill Funcionar (MVP)

## Objetivo
Fazer a skill video-cutter funcionar com o mínimo de complexidade possível. Sem overengineering, sem frontend, sem banco de dados. Apenas: vídeo in → clips out.

## Status atual
**MVP completo, validado e robusto.** Whisper transcreve localmente (sem API). Gemini analisa com chunked analysis (~6 chamadas/run). Fallback automático entre modelos quando quota esgota. Retry com backoff para erros 503. Todos os 6 vídeos de teste processados com sucesso (cobertura 79-98%). Próximo passo: melhorias ou produção.

---

## Fase 1: Criar skill seguindo spec oficial ✅ CONCLUÍDA

### 1.1 Instalar skill-creator de referência
```bash
npx skills add https://github.com/anthropics/skills --skill skill-creator -y
```
Resultado: instalada em `.agents/skills/skill-creator/`

### 1.2 Reestruturar video-cutter seguindo spec
Estrutura final:
```
.agents/skills/video-cutter/
├── SKILL.md              # YAML frontmatter + fluxo conciso (~100 linhas)
├── scripts/
│   ├── helper.sh         # FFmpeg utils (info, extract-audio, cut, validate)
│   └── run.sh            # Automação completa
├── references/
│   ├── prompts.md        # Prompts Gemini detalhados (transcrição + análise)
│   └── ffmpeg.md         # Comandos FFmpeg de referência
└── examples/
    └── examples.md       # Referências genéricas de qualidade
```

### 1.3 Aplicar princípios da spec
- YAML frontmatter: `name`, `description`, `disable-model-invocation: true`
- SKILL.md conciso com links para references/
- Scripts separados em `scripts/`
- Prompts detalhados em `references/prompts.md`

---

## Fase 2: Testar a skill básica ✅ CONCLUÍDA

### 2.1 Verificar pré-requisitos ✅
- FFmpeg: instalado
- GEMINI_API_KEY: configurada via `.env`

### 2.2 Testar com vídeo de exemplo ✅
- Vídeo de teste: `./test/WhatsApp Video 2026-03-25 at 14.35.40.mp4` (535s)
- Fluxo completo executado com sucesso
- 4-5 clips gerados por execução

### 2.3 Executar fluxo manualmente ✅
Passos validados:
1. Extrair áudio ✅
2. Transcrever com Whisper (local, sem API) ✅
3. Analisar com Gemini (gemini-2.5-flash) ✅
4. Sanitizar timestamps ✅
5. Validar timestamps ✅
6. Aplicar buffer inteligente ✅
7. Gerar clips ✅
8. Criar cuts.json ✅
9. Apresentar resultados ✅

---

## Fase 3: Ajustar prompts ✅ CONCLUÍDA (durante testes)

### 3.1 Problemas encontrados e soluções

| Problema | Solução |
|----------|---------|
| `gemini-2.5-flash` inflava timestamps | Mudou para `gemini-3-flash-preview` |
| Prompt de transcrição não respeitava duração | Adicionado `DURAÇÃO TOTAL DO ÁUDIO: <DURAÇÃO>` |
| Regra de `[PAUSE Xs]` causava inflação | Removida. Pula silêncios em vez de criar entradas |
| Cortes terminavam no meio de frases | Buffer inteligente (MAX_GAP=2.0s, BUFFER=2.0s) |
| Exemplos específicos demais (guitarra) | Referências genéricas de qualidade (hook patterns) |
| Gemini alucinava conteúdo da transcrição | Substituído por faster-whisper (transcrição local) |
| gemini-3-flash-preview tinha quota limitada | Descoberta dinâmica de modelos via API (9 modelos, fallback automático) |
| Cortes fora de ordem causavam sobreposição | Sort por timestamp antes de verificação |

### 3.2 Referências genéricas adicionadas
- Padrões de hook: curiosity_gap, result_first, pattern_interrupt, pain_point, fomo
- Indicadores de qualidade: hook_power, retention_potential, shareability
- Duração ideal por tipo: 15-25s, 25-40s, 40-60s
- O que não fazer: cortar no meio de frase, silêncio > 1.5s, hook fraco

---

## Fase 4: Automatizar fluxo ✅ CONCLUÍDA

### 4.1 Script run.sh criado ✅
```bash
./.agents/skills/video-cutter/scripts/run.sh ./video.mp4
```
O script:
1. Carrega `.env` automaticamente ✅
2. Executa os 9 passos do SKILL.md ✅
3. Gera clips em `./output/YYYYMMDD_HHMM/` ✅
4. Cria `cuts.json` com metadados ✅
5. Mostra resumo ao usuário ✅

### 4.2 Validação automática ✅
- Verifica timestamps antes de cortar ✅
- Aplica sanitização (Passo 4) ✅
- Aplica buffer inteligente (Passo 7) ✅
- Trata erros da API Gemini ✅

### 4.3 Output padronizado ✅
- Sempre gera cuts.json com buffer_details ✅
- Sempre cria subdiretório por run ✅
- Sempre mostra resumo com viral scores ✅

---

## Fase 5: Validação com múltiplos vídeos ✅ CONCLUÍDA

### 5.1 Objetivo
Confirmar que a skill funciona para diferentes tipos de vídeo com o fluxo completo (Whisper + descoberta dinâmica de modelos Flash via API).

### 5.2 Vídeos testados (chunked analysis, 01/04/2026)
| Vídeo | Duração | Clips | Cobertura | Fallback usado? |
|-------|---------|-------|-----------|-----------------|
| Podcast | 15min | 17 | 0s-940s (98%) | Não |
| Standup | 12min | 13 | 13s-716s (97%) | Não (chunk 6: 429 mas completou) |
| Curto | 4min | 5 | 11s-218s (83%) | Sim (chunk 1: fallback para flash-preview) |
| WhatsApp | 9min | 5 | 105s-528s (79%) | Sim (chunks 1-2: fallback) |
| Data centers | 13min | 14 | 0s-793s (100%) | Não |
| Tutorial | 17min | 16 | 0s-1058s (100%) | Não |

### 5.2 Vídeos para testar
- Vlog / conversa direta com câmera
- Entrevista / podcast
- Review de produto
- Tutorial passo a passo
- Conteúdo em inglês (teste de idioma)

### 5.3 O que validar por vídeo
- Transcrição Whisper sem alucinação
- Cortes alinham com o conteúdo (usar validate_cuts.py --verify-content)
- Buffer não corta palavras
- Durações entre 15-60s
- Clips MP4 válidos e reproduzíveis

---

## Fase 6: Melhorias (FUTURO)

### 6.1 Batch processing
- Processar múltiplos vídeos
- Paralelizar quando possível

### 6.2 Templates
- Estilos diferentes de corte
- Configurações por tipo de conteúdo

### 6.3 Legendas automáticas
- Adicionar legendas nos clips
- Suporte a múltiplos idiomas

---

## O que NÃO fazer agora

❌ Não criar frontend
❌ Não criar banco de dados
❌ Não adicionar autenticação
❌ Não criar API HTTP
❌ Não usar Remotion (ainda)
❌ Não adicionar legendas automáticas (Fase 6)
❌ Não processar múltiplos vídeos (Fase 6)
❌ Não criar sistema de templates (Fase 6)

---

## Métricas de sucesso

### MVP funcionando ✅ (TODAS ATINGIDAS):
1. ✅ Consegue extrair áudio de um vídeo
2. ✅ Consegue transcrever com Whisper (local, sem alucinação)
3. ✅ Consegue identificar 3-5 cortes virais (via Gemini)
4. ✅ Consegue gerar clips MP4
5. ✅ Clips têm qualidade aceitável (áudio limpo, sem cortes errados)
6. ✅ Timestamps são precisos (Whisper + buffer inteligente)
7. ✅ Conteúdo transcrito corresponde ao áudio real (69%+ match)
8. ✅ Script automatizado funciona (run.sh)
9. ✅ Validação automática de output (validate_cuts.py)

---

## Próximos passos imediatos

1. **✅ Skill criada seguindo spec oficial**
2. **✅ GEMINI_API_KEY configurada via .env**
3. **✅ Vídeo de teste validado (535s)**
4. **✅ Fluxo completo testado com sucesso**
5. **✅ Prompts refinados (transcrição + análise)**
6. **✅ Script run.sh criado e funcionando**
7. **✅ Buffer validado (2.0s correto, alinhamento OK)**
8. **✅ Whisper substituiu Gemini para transcrição (sem alucinação)**
9. **✅ Todos os 6 vídeos testados com chunked analysis (cobertura 79-98%)**
10. **✅ Fallback de modelos implementado (2.5-flash → 3-flash → 3.1-flash-lite)**

## Limitação atual

- **Transcrição:** Whisper local (sem custo, sem limite)
- **Análise:** Modelos Flash descobertos dinamicamente via API (~6 chamadas/run), 20 req/dia por modelo no free tier
- **Fallback:** Percorre todos os 9 modelos Flash até encontrar um com quota disponível
- **Retry:** backoff automático para erros 503 (overload)
- **Dependência:** faster-whisper (`pip install --user --break-system-packages faster-whisper`)

---

## Referências

- Skill-creator: `.agents/skills/skill-creator/SKILL.md`
- SKILL.md: `.agents/skills/video-cutter/SKILL.md`
- Script: `.agents/skills/video-cutter/scripts/helper.sh`
- Script: `.agents/skills/video-cutter/scripts/run.sh`
- Contexto: `CONTEXT.md`
