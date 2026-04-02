#!/bin/bash
# helper.sh - Utilitários FFmpeg para video-cutter skill
# Uso: scripts/helper.sh <comando> [argumentos]

set -e

# Funções
usage() {
  echo "Uso: $0 <comando> [argumentos]"
  echo ""
  echo "Comandos:"
  echo "  info <video>                    - Mostra informações do vídeo"
  echo "  extract-audio <video> [output]  - Extrai áudio para análise"
  echo "  cut <video> <start> <end> <out> - Corta um segmento"
  echo "  validate <video> <start> <end>  - Valida timestamps"
  echo ""
}

cmd_info() {
  local video="$1"
  [ -z "$video" ] && { echo "Erro: Caminho do vídeo não fornecido"; exit 1; }
  [ ! -f "$video" ] && { echo "Erro: Arquivo não encontrado: $video"; exit 1; }

  echo "=== Informações do Vídeo ==="
  echo "Arquivo: $(basename "$video")"
  echo "Duração: $(ffprobe -v quiet -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$video")s"
  echo "Resolução: $(ffprobe -v quiet -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 "$video")"
  echo "FPS: $(ffprobe -v quiet -select_streams v:0 -show_entries stream=r_frame_rate -of default=noprint_wrappers=1:nokey=1 "$video")"
  echo "Tem áudio: $(ffprobe -v quiet -select_streams a:0 -show_entries stream=codec_name -of default=noprint_wrappers=1:nokey=1 "$video" | grep -q . && echo 'Sim' || echo 'Não')"
}

cmd_extract_audio() {
  local video="$1"
  local output="${2:-/tmp/shortcutter_audio_${RANDOM}.wav}"

  [ -z "$video" ] && { echo "Erro: Caminho do vídeo não fornecido"; exit 1; }
  [ ! -f "$video" ] && { echo "Erro: Arquivo não encontrado: $video"; exit 1; }

  echo "Extraindo áudio..."
  ffmpeg -i "$video" -vn -acodec pcm_s16le -ar 16000 -ac 1 "$output" -y 2>/dev/null

  if [ $? -eq 0 ]; then
    echo "Áudio extraído: $output"
    echo "$output"
  else
    echo "Erro ao extrair áudio"
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

  [ ! -f "$video" ] && { echo "Erro: Arquivo não encontrado: $video"; exit 1; }

  local duration=$(echo "$end - $start" | bc)
  mkdir -p "$(dirname "$output")"

  echo "Cortando: ${start}s - ${end}s (${duration}s)"
  ffmpeg -ss "$start" -i "$video" -to "$end" \
    -c:v libx264 -preset ultrafast -crf 23 \
    -c:a aac -movflags +faststart -pix_fmt yuv420p \
    "$output" -y 2>/dev/null

  if [ $? -eq 0 ]; then
    echo "Corte gerado: $output"
  else
    echo "Erro ao cortar vídeo"
    exit 1
  fi
}

cmd_validate() {
  local video="$1" start="$2" end="$3"

  [ -z "$video" ] || [ -z "$start" ] || [ -z "$end" ] && {
    echo "Erro: Argumentos insuficientes"
    echo "Uso: $0 validate <video> <start> <end>"
    exit 1
  }

  [ ! -f "$video" ] && { echo "INVALID: Arquivo não encontrado"; exit 1; }

  local video_duration=$(ffprobe -v quiet -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$video")

  if (( $(echo "$start < 0" | bc -l) )); then
    echo "INVALID: start_sec ($start) < 0"; exit 1
  fi

  if (( $(echo "$end > $video_duration" | bc -l) )); then
    echo "INVALID: end_sec ($end) > duração ($video_duration)"; exit 1
  fi

  if (( $(echo "$end <= $start" | bc -l) )); then
    echo "INVALID: end_sec ($end) <= start_sec ($start)"; exit 1
  fi

  local duration=$(echo "$end - $start" | bc)
  if (( $(echo "$duration < 15" | bc -l) )); then
    echo "INVALID: duração ($duration) < 15s mínimo"; exit 1
  fi

  if (( $(echo "$duration > 60" | bc -l) )); then
    echo "INVALID: duração ($duration) > 60s máximo"; exit 1
  fi

  echo "VALID: ${start}s - ${end}s (${duration}s)"
}

# Verificar dependências
check_dependencies() {
  for cmd in ffmpeg ffprobe bc; do
    if ! command -v "$cmd" &> /dev/null; then
      echo "Erro: $cmd não está instalado"
      echo "Instale com: sudo apt install $cmd"
      exit 1
    fi
  done
}

# Main
check_dependencies

case "${1:-help}" in
  info)          cmd_info "$2" ;;
  extract-audio) cmd_extract_audio "$2" "$3" ;;
  cut)           cmd_cut "$2" "$3" "$4" "$5" ;;
  validate)      cmd_validate "$2" "$3" "$4" ;;
  help|--help|-h) usage ;;
  *)
    echo "Erro: Comando desconhecido: $1"
    usage
    exit 1
    ;;
esac
