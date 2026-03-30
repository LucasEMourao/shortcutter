# Exemplos de uso

## Referências de qualidade (genéricas para qualquer vídeo)

### Padrões de hook (adapte ao conteúdo)
- `curiosity_gap`: Pergunta que cria lacuna mental → "O que acontece quando...", "Você sabia que..."
- `result_first`: Mostra resultado primeiro → "Olha o resultado...", "Veja o que acontece quando..."
- `pattern_interrupt`: Começa no meio da ação, sem introdução → [execução direta, sem "olá pessoal"]
- `pain_point`: Identifica problema comum → "Se você tem esse problema...", "Se isso acontece com você..."
- `fomo`: Cria urgência → "Você precisa saber isso antes de...", "Não faça isso sem saber..."

### Indicadores de qualidade (independente de conteúdo)
- `hook_power 8+`: Para de scrollar nos primeiros 3s
- `retention_potential 8+`: Mantém atenção do início ao fim
- `shareability 7+`: Vale enviar pra um amigo
- `viral_score 7.5+`: Combinado dos três acima

### Duração ideal por tipo
- **15-25s**: Dica rápida, conceito único
- **25-40s**: Tutorial, explicação
- **40-60s**: História, review detalhado

### O que NÃO fazer
- Cortar no meio de uma frase
- Silêncio > 1.5s dentro do corte
- Hook fraco nos primeiros 3s
- Duração > 60s (perde atenção)
- Sem CTA ou frase de efeito

---

## Como usar a skill

**Comando básico:**
```
Analise o vídeo ./video.mp4 e gere cortes para TikTok
```

**Comando com script:**
```bash
./.agents/skills/video-cutter/scripts/run.sh ./video.mp4
```

**Modo conservador:**
```
Gere cortes do vídeo ./tutorial.mp4 em modo conservador
```

Ou via script:
```bash
./.agents/skills/video-cutter/scripts/run.sh ./video.mp4 ./output conservative
```

**Output específico:**
```
Cortar ./vlog.mp4 e salvar em ./meus-cortes/
```

---

## Erro: vídeo não encontrado

**Saída:**
```
❌ ERRO: Vídeo não encontrado: ./video-nao-existe.mp4
```

---

## Erro: API key não configurada

**Saída:**
```
❌ ERRO: GEMINI_API_KEY não configurada. Crie um arquivo .env com GEMINI_API_KEY=sua_chave
```
