---
name: video-cutter
description: Corta vídeos automaticamente em clips curtos para Reels, TikTok e YouTube Shorts usando IA. Transcreve o áudio com Whisper (local), identifica os melhores momentos virais com Gemini e gera MP4s prontos para publicação. Use quando o usuário mencionar cortar vídeo, gerar clips, analisar vídeo, encontrar momentos virais, criar Reels, TikTok ou Shorts.
disable-model-invocation: true
allowed-tools: Bash, Read, Write
---

# Video Cutter

Gera cortes automáticos de vídeos curtos (Reels, TikTok, Shorts) usando Whisper para transcrição local, Gemini para análise viral e FFmpeg para processamento.

**Transcrição:** faster-whisper small (local, CPU, sem API)
**Análise:** Modelos Flash descobertos dinamicamente via API (/v1beta/models)

## Quick Start

### Automação (recomendado)
```bash
# Modo agressivo (padrão)
./.agents/skills/video-cutter/scripts/run.sh ./video.mp4

# Modo conservador
./.agents/skills/video-cutter/scripts/run.sh ./video.mp4 ./output conservative

# Output customizado
./.agents/skills/video-cutter/scripts/run.sh ./video.mp4 ./meus-cortes
```

### Manual (avançado)
Dizer ao agente:
```
Analise o vídeo ./video.mp4 e gere cortes para TikTok
```

## Pré-requisitos

| Dependência | Verificação |
|-------------|-------------|
| FFmpeg | `command -v ffmpeg` |
| GEMINI_API_KEY | `echo $GEMINI_API_KEY` |
| Vídeo válido | `test -f <caminho>` |

Se algo faltar, pare e oriente o usuário.

## Fluxo

### 1. Validar entrada
- Verificar se o vídeo existe e tem áudio
- Obter duração com `ffprobe`
- Verificar FFmpeg e API key

Use `scripts/helper.sh info <video>` para diagnóstico rápido.

### 2. Extrair áudio
```bash
ffmpeg -i <video> -vn -acodec pcm_s16le -ar 16000 -ac 1 /tmp/shortcutter_audio.wav -y
```

### 3. Transcrever com Whisper (local)
```bash
python3 -c "
from faster_whisper import WhisperModel
model = WhisperModel('small', device='cpu', compute_type='int8')
segments, info = model.transcribe('audio.wav', language='pt', beam_size=5)
# Salvar segmentos com start_sec, end_sec, text em JSON
"
```

Transcrição local, sem API, sem custo, sem alucinação.
**Referência:** `scripts/run.sh` § transcribe_audio

### 4. Sanitizar timestamps
O Gemini frequentemente gera timestamps acima da duração real do vídeo (ex: 854s para vídeo de 535s). Sanitizar é OBRIGATÓRIO.

**Sanitização em código (Python):**
```python
video_duration = <DURAÇÃO>
max_ts = max(seg['end_sec'] for seg in transcription)

if max_ts > video_duration:
    # Normalização proporcional
    scale = video_duration / max_ts
    for seg in transcription:
        seg['start_sec'] = round(seg['start_sec'] * scale, 3)
        seg['end_sec'] = round(seg['end_sec'] * scale, 3)

# Remover segmentos inválidos
transcription = [
    seg for seg in transcription
    if seg['start_sec'] >= 0
    and seg['end_sec'] <= video_duration
    and seg['end_sec'] > seg['start_sec']
]
```

### 5. Identificar cortes virais (análise adaptativa)

**Estratégia automática por duração:**
- `< 5min` → análise direta (1 chamada API)
- `5-10min` → chunks de 4min (2-3 chamadas)
- `> 10min` → chunks de 3min (4-6 chamadas)

**Modelos:** descobertos dinamicamente via `/v1beta/models`, fallback automático entre todos os Flash disponíveis.

```bash
python3 scripts/analyze_adaptive.py transcription.json <duration> <mode> output.json <api_key>
```

**Referência:** `scripts/analyze_adaptive.py`

### 6. Validar timestamps dos cortes
Para cada corte, validar:
- `start_sec >= 0`
- `end_sec <= duração_total`
- `end_sec > start_sec`
- `15 <= duração <= 60` segundos

Use `scripts/helper.sh validate <video> <start> <end>` para validação automática.

### 7. Aplicar buffer inteligente final
Dois parâmetros:
- **MAX_GAP (2.0s):** Se o gap até o próximo segmento for ≤ 2.0s, estende até ele
- **BUFFER (2.0s):** Se o gap for > 2.0s, adiciona buffer fixo de 2.0s

Princípio: É melhor ter um pouco mais do que cortar demais. O usuário pode cortar o excesso, mas não pode adicionar o que foi cortado.

```python
MAX_GAP = 2.0
FIXED_BUFFER = 2.0
for cut in cuts:
    next_seg = find next segment after cut['end_sec']
    if next_seg:
        gap = next_seg['start_sec'] - cut['end_sec']
        if gap <= MAX_GAP:
            cut['end_sec'] = next_seg['start_sec']  # Estende até próximo segmento
        else:
            cut['end_sec'] = min(video_duration, cut['end_sec'] + FIXED_BUFFER)  # Buffer fixo
    else:
        cut['end_sec'] = video_duration  # Último corte vai até o fim
```

### 8. Gerar clips
Criar subdiretório único por run para evitar conflitos:
```bash
RUN_DIR="./output/$(date +%Y%m%d_%H%M)"
mkdir -p "$RUN_DIR"
```

Gerar cada corte válido:
```bash
ffmpeg -i <video> -ss <start> -to <end> \
  -c:v libx264 -preset ultrafast -crf 23 \
  -c:a aac -movflags +faststart -pix_fmt yuv420p \
  "$RUN_DIR/cut_<NN>_<START>-<END>s.mp4" -y
```

**Nota:** `preset ultrafast` garante precisão de corte (vs `fast` que pode timeout). Trade-off: arquivos 5-24x maiores que `preset fast`.

### 9. Gerar metadados
Criar `$RUN_DIR/cuts.json` com todos os cortes e scores.

**Referência:** [references/prompts.md](references/prompts.md) § Output JSON

### 10. Apresentar resultados
Resumo com: quantidade de clips, viral score de cada um, caminho dos arquivos.

## Modos de operação

| Modo | Cortes | Duração mín | Foco |
|------|--------|-------------|------|
| Agressivo (padrão) | 3-8 | 15s | Viralidade, hooks |
| Conservador | 1-3 | 20s | Narrativa, valor |

Para modo conservador, adicionar: `MODO CONSERVADOR: 1-3 cortes, narrativa completa, duração mín 20s`

## Erros

| Erro | Ação |
|------|------|
| Vídeo não encontrado | Informar, sugerir verificar caminho |
| FFmpeg ausente | `sudo apt install ffmpeg` |
| API key ausente | Orientar configuração |
| Whisper não instalado | `pip install faster-whisper` |
| Sem áudio | Informar, sugerir narração |
| Timestamp inválido | Descartar corte, continuar |
| FFmpeg falha | Pular corte, tentar próximo |
| 429 (quota) | Fallback para próximo modelo Flash |
| 503 (overload) | Retry com backoff (10s/20s/30s) |

## Reference files

- [references/prompts.md](references/prompts.md) — Prompts detalhados para Gemini
- [references/ffmpeg.md](references/ffmpeg.md) — Comandos FFmpeg completos
- [examples/examples.md](examples/examples.md) — Exemplos de uso

## Scripts

- `scripts/run.sh` — Automação completa do fluxo (validação → Whisper → sanitização → análise adaptativa → buffer → clips)
- `scripts/helper.sh` — Validação, extração de áudio e corte de vídeo
- `scripts/analyze_adaptive.py` — Análise adaptativa (direta <5min, chunked >5min) com fallback de modelos
- `scripts/validate_cuts.py` — Validação estrutural e de conteúdo dos cortes gerados
