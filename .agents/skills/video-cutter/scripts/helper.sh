#!/bin/bash
# helper.sh - Utilitarios FFmpeg para video-cutter
# Uso: scripts/helper.sh <comando> [argumentos]

set -e

SHORTCUTTER_VIDEO_CODEC="${SHORTCUTTER_VIDEO_CODEC:-libx264}"
SHORTCUTTER_AUDIO_CODEC="${SHORTCUTTER_AUDIO_CODEC:-aac}"
SHORTCUTTER_FFMPEG_PRESET="${SHORTCUTTER_FFMPEG_PRESET:-ultrafast}"
SHORTCUTTER_FFMPEG_CRF="${SHORTCUTTER_FFMPEG_CRF:-23}"
SHORTCUTTER_PIX_FMT="${SHORTCUTTER_PIX_FMT:-yuv420p}"

usage() {
  echo "Uso: $0 <comando> [argumentos]"
  echo ""
  echo "Comandos:"
  echo "  info <video>                    - Mostra informacoes do video"
  echo "  extract-audio <video> [output]  - Extrai audio para analise"
  echo "  cut <video> <start> <end> <out> - Corta um segmento"
  echo "  encoding-config                 - Mostra config atual de encoding"
  echo "  validate <video> <start> <end>  - Valida timestamps"
  echo ""
}

validate_encoding_settings() {
  if ! [[ "$SHORTCUTTER_FFMPEG_CRF" =~ ^[0-9]+$ ]]; then
    echo "Erro: SHORTCUTTER_FFMPEG_CRF deve ser inteiro entre 0 e 51"
    exit 1
  fi

  if (( SHORTCUTTER_FFMPEG_CRF < 0 || SHORTCUTTER_FFMPEG_CRF > 51 )); then
    echo "Erro: SHORTCUTTER_FFMPEG_CRF deve estar entre 0 e 51"
    exit 1
  fi
}

cmd_info() {
  local video="$1"
  [ -z "$video" ] && { echo "Erro: Caminho do video nao fornecido"; exit 1; }
  [ ! -f "$video" ] && { echo "Erro: Arquivo nao encontrado: $video"; exit 1; }

  echo "=== Informacoes do Video ==="
  echo "Arquivo: $(basename "$video")"
  echo "Duracao: $(ffprobe -v quiet -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$video")s"
  echo "Resolucao: $(ffprobe -v quiet -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 "$video")"
  echo "FPS: $(ffprobe -v quiet -select_streams v:0 -show_entries stream=r_frame_rate -of default=noprint_wrappers=1:nokey=1 "$video")"
  echo "Tem audio: $(ffprobe -v quiet -select_streams a:0 -show_entries stream=codec_name -of default=noprint_wrappers=1:nokey=1 "$video" | grep -q . && echo 'Sim' || echo 'Nao')"
}

cmd_extract_audio() {
  local video="$1"
  local output="${2:-/tmp/shortcutter_audio_${RANDOM}.wav}"

  [ -z "$video" ] && { echo "Erro: Caminho do video nao fornecido"; exit 1; }
  [ ! -f "$video" ] && { echo "Erro: Arquivo nao encontrado: $video"; exit 1; }

  echo "Extraindo audio..."
  ffmpeg -i "$video" -vn -acodec pcm_s16le -ar 16000 -ac 1 "$output" -y 2>/dev/null

  if [ $? -eq 0 ]; then
    echo "Audio extraido: $output"
    echo "$output"
  else
    echo "Erro ao extrair audio"
    exit 1
  fi
}

cmd_cut() {
  local video="$1" start="$2" end="$3" output="$4"

  [ -z "$video" ] || [ -z "$start" ] || [ -z "$end" ] || [ -z "$output" ] && {
    echo "Erro: Argumentos insuficientes"
    echo "Uso: $0 cut <video> <start> <end> <output>"
    exit 1
  }

  [ ! -f "$video" ] && { echo "Erro: Arquivo nao encontrado: $video"; exit 1; }

  local duration
  duration=$(echo "$end - $start" | bc)
  mkdir -p "$(dirname "$output")"

  echo "Cortando: ${start}s - ${end}s (${duration}s)"
  ffmpeg -ss "$start" -i "$video" -t "$duration" \
    -c:v "$SHORTCUTTER_VIDEO_CODEC" -preset "$SHORTCUTTER_FFMPEG_PRESET" -crf "$SHORTCUTTER_FFMPEG_CRF" \
    -c:a "$SHORTCUTTER_AUDIO_CODEC" -movflags +faststart -pix_fmt "$SHORTCUTTER_PIX_FMT" \
    "$output" -y 2>/dev/null

  if [ $? -eq 0 ]; then
    echo "Corte gerado: $output"
  else
    echo "Erro ao cortar video"
    exit 1
  fi
}

cmd_encoding_config() {
  echo "{"
  echo "  \"video_codec\": \"$SHORTCUTTER_VIDEO_CODEC\","
  echo "  \"audio_codec\": \"$SHORTCUTTER_AUDIO_CODEC\","
  echo "  \"preset\": \"$SHORTCUTTER_FFMPEG_PRESET\","
  echo "  \"crf\": $SHORTCUTTER_FFMPEG_CRF,"
  echo "  \"pix_fmt\": \"$SHORTCUTTER_PIX_FMT\""
  echo "}"
}

cmd_validate() {
  local video="$1" start="$2" end="$3"

  [ -z "$video" ] || [ -z "$start" ] || [ -z "$end" ] && {
    echo "Erro: Argumentos insuficientes"
    echo "Uso: $0 validate <video> <start> <end>"
    exit 1
  }

  [ ! -f "$video" ] && { echo "INVALID: Arquivo nao encontrado"; exit 1; }

  local video_duration
  video_duration=$(ffprobe -v quiet -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$video")

  if (( $(echo "$start < 0" | bc -l) )); then
    echo "INVALID: start_sec ($start) < 0"; exit 1
  fi

  if (( $(echo "$end > $video_duration" | bc -l) )); then
    echo "INVALID: end_sec ($end) > duracao ($video_duration)"; exit 1
  fi

  if (( $(echo "$end <= $start" | bc -l) )); then
    echo "INVALID: end_sec ($end) <= start_sec ($start)"; exit 1
  fi

  local duration
  duration=$(echo "$end - $start" | bc)
  if (( $(echo "$duration < 15" | bc -l) )); then
    echo "INVALID: duracao ($duration) < 15s minimo"; exit 1
  fi

  if (( $(echo "$duration > 60" | bc -l) )); then
    echo "INVALID: duracao ($duration) > 60s maximo"; exit 1
  fi

  echo "VALID: ${start}s - ${end}s (${duration}s)"
}

check_dependencies() {
  validate_encoding_settings

  for cmd in ffmpeg ffprobe bc; do
    if ! command -v "$cmd" &> /dev/null; then
      echo "Erro: $cmd nao esta instalado"
      echo "Instale com: sudo apt install $cmd"
      exit 1
    fi
  done
}

check_dependencies

case "${1:-help}" in
  info)            cmd_info "$2" ;;
  extract-audio)   cmd_extract_audio "$2" "$3" ;;
  cut)             cmd_cut "$2" "$3" "$4" "$5" ;;
  encoding-config) cmd_encoding_config ;;
  validate)        cmd_validate "$2" "$3" "$4" ;;
  help|--help|-h)  usage ;;
  *)
    echo "Erro: Comando desconhecido: $1"
    usage
    exit 1
    ;;
esac
