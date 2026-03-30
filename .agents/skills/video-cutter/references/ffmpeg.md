# Referência FFmpeg

## Índice

- [Informações do vídeo](#informações-do-vídeo)
- [Extração de áudio](#extração-de-áudio)
- [Cortar vídeo](#cortar-vídeo)
- [Validação](#validação)

---

## Informações do vídeo

```bash
# Duração
ffprobe -v quiet -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 <video>

# Resolução
ffprobe -v quiet -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 <video>

# FPS
ffprobe -v quiet -select_streams v:0 -show_entries stream=r_frame_rate -of default=noprint_wrappers=1:nokey=1 <video>

# Verificar se tem áudio
ffprobe -v quiet -select_streams a:0 -show_entries stream=codec_name -of default=noprint_wrappers=1:nokey=1 <video>
```

Ou usar o helper:
```bash
scripts/helper.sh info <video>
```

---

## Extração de áudio

```bash
ffmpeg -i <video> -vn -acodec pcm_s16le -ar 16000 -ac 1 <output>.wav -y
```

Parâmetros:
- `-vn` — sem vídeo
- `-acodec pcm_s16le` — formato PCM 16-bit (compatível com Gemini)
- `-ar 16000` — sample rate 16kHz
- `-ac 1` — mono
- `-y` — sobrescrever sem perguntar

---

## Cortar vídeo

```bash
ffmpeg -i <video> -ss <start> -t <duration> \
  -c:v libx264 -preset fast -crf 23 \
  -c:a aac -movflags +faststart -pix_fmt yuv420p \
  <output>.mp4 -y
```

Parâmetros:
- `-ss <start>` — segundo inicial
- `-t <duration>` — duração do corte (não segundo final)
- `-c:v libx264` — codec H.264
- `-preset fast` — velocidade de codificação
- `-crf 23` — qualidade (18=alto, 23=padrão, 28=baixo)
- `-c:a aac` — codec de áudio AAC
- `-movflags +faststart` — otimizado para streaming
- `-pix_fmt yuv420p` — compatibilidade ampla

---

## Validação

Validar se timestamps são válidos para um vídeo:

```bash
scripts/helper.sh validate <video> <start> <end>
```

Retorna:
- `VALID: 12.5s - 38.2s (25.7s)` — timestamps válidos
- `INVALID: ...` — motivo da invalidez
