#!/bin/bash
# run.sh - Automatiza o fluxo completo da skill video-cutter
# Uso: ./scripts/run.sh <video_path> [output_dir] [mode]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_DIR="$(cd "$SKILL_DIR/../../.." && pwd)"
TEMP_DIR="/tmp/shortcutter_$$"

log() {
  echo "[$(date +%H:%M:%S)] $1"
}

error() {
  echo "ERRO: $1" >&2
  exit 1
}

warn() {
  echo "AVISO: $1" >&2
}

cleanup() {
  rm -rf "$TEMP_DIR"
}

trap cleanup EXIT

check_dependencies() {
  log "Verificando dependencias..."

  for cmd in ffmpeg ffprobe python3 bc; do
    if ! command -v "$cmd" &>/dev/null; then
      error "$cmd nao esta instalado"
    fi
  done

  if [ -z "$GEMINI_API_KEY" ]; then
    if [ -f "$PROJECT_DIR/.env" ]; then
      log "Carregando GEMINI_API_KEY de .env..."
      set -a
      source "$PROJECT_DIR/.env"
      set +a
    fi

    if [ -z "$GEMINI_API_KEY" ]; then
      error "GEMINI_API_KEY nao configurada. Crie um arquivo .env com GEMINI_API_KEY=sua_chave"
    fi
  fi

  log "OK dependencias verificadas"
}

validate_input() {
  local video="$1"

  log "Passo 1: Validando entrada..."

  if [ ! -f "$video" ]; then
    error "Video nao encontrado: $video"
  fi

  local has_audio
  has_audio=$(ffprobe -v quiet -select_streams a:0 -show_entries stream=codec_name -of default=noprint_wrappers=1:nokey=1 "$video" 2>/dev/null)
  if [ -z "$has_audio" ]; then
    error "Video sem audio: $video"
  fi

  VIDEO_DURATION=$(ffprobe -v quiet -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$video")
  if (( $(echo "$VIDEO_DURATION < 15" | bc -l) )); then
    error "Video muito curto (${VIDEO_DURATION}s). Minimo: 15s"
  fi

  VIDEO_NAME=$(basename "$video")
  VIDEO_RES=$(ffprobe -v quiet -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 "$video" 2>/dev/null || echo "N/A")

  log "Video: $VIDEO_NAME"
  log "Duracao: ${VIDEO_DURATION}s"
  log "Resolucao: $VIDEO_RES"
  log "Audio: $has_audio"
}

extract_audio() {
  local video="$1"

  log "Passo 2: Extraindo audio..."

  AUDIO_FILE="$TEMP_DIR/audio.wav"
  ffmpeg -i "$video" -vn -acodec pcm_s16le -ar 16000 -ac 1 "$AUDIO_FILE" -y 2>/dev/null

  log "Audio extraido: $AUDIO_FILE"
}

transcribe_audio() {
  log "Passo 3: Transcrevendo audio com Whisper..."

  if ! python3 -c "from faster_whisper import WhisperModel" 2>/dev/null; then
    error "faster-whisper nao instalado. Instale com: pip3 install --user --break-system-packages faster-whisper"
  fi

  python3 "$SCRIPT_DIR/transcribe_audio.py" \
    "$AUDIO_FILE" \
    "$TEMP_DIR/transcription.json"

  log "Transcricao concluida"
}

sanitize_timestamps() {
  log "Passo 4: Sanitizando timestamps..."

  python3 "$SCRIPT_DIR/sanitize_transcription.py" \
    "$TEMP_DIR/transcription.json" \
    "$VIDEO_DURATION" \
    "$TEMP_DIR/transcription_sanitized.json"

  log "Sanitizacao concluida"
}

analyze_cuts() {
  log "Passo 5: Analisando cortes virais (adaptativo)..."

  local adaptive_script="$SCRIPT_DIR/analyze_adaptive.py"
  if [ ! -f "$adaptive_script" ]; then
    error "Script adaptativo nao encontrado: $adaptive_script"
  fi

  python3 "$adaptive_script" \
    "$TEMP_DIR/transcription_sanitized.json" \
    "$VIDEO_DURATION" \
    "$MODE" \
    "$TEMP_DIR/analysis.json" \
    "$GEMINI_API_KEY"

  log "Analise concluida"
}

validate_timestamps() {
  log "Passo 6: Validando timestamps..."

  python3 "$SCRIPT_DIR/validate_analysis_cuts.py" \
    "$TEMP_DIR/analysis.json" \
    "$VIDEO_DURATION" \
    "$MODE" \
    "$TEMP_DIR/valid_cuts.json"

  log "Validacao concluida"
}

apply_buffer() {
  log "Passo 7: Aplicando buffer inteligente..."

  python3 "$SCRIPT_DIR/apply_buffer.py" \
    "$TEMP_DIR/transcription_sanitized.json" \
    "$TEMP_DIR/valid_cuts.json" \
    "$VIDEO_DURATION" \
    "$MODE" \
    "$TEMP_DIR/final_cuts.json"

  log "Buffer inteligente aplicado"
}

generate_clips() {
  local video="$1"

  log "Passo 8: Gerando clips..."
  mkdir -p "$RUN_DIR"

  python3 "$SCRIPT_DIR/generate_clips.py" \
    "$TEMP_DIR/final_cuts.json" \
    "$video" \
    "$RUN_DIR" \
    "$SCRIPT_DIR/helper.sh" \
    "$PROJECT_DIR" \
    "$TEMP_DIR/final_cuts_with_files.json"

  log "Clips gerados"
}

generate_metadata() {
  log "Passo 9: Gerando metadados..."

  python3 "$SCRIPT_DIR/generate_metadata.py" \
    "$TEMP_DIR/final_cuts_with_files.json" \
    "$TEMP_DIR/analysis.json" \
    "$MODE" \
    "$RUN_DIR" \
    "$PROJECT_DIR" \
    "$VIDEO_NAME" \
    "$RUN_DIR/cuts.json"

  log "Metadados gerados"
}

show_results() {
  python3 "$SCRIPT_DIR/print_run_summary.py" "$RUN_DIR/cuts.json"
}

usage() {
  echo "Uso: $0 <video_path> [output_dir] [mode]"
  echo ""
  echo "Argumentos:"
  echo "  video_path  - Caminho do video de entrada (obrigatorio)"
  echo "  output_dir  - Diretorio de output (opcional, padrao: ./output)"
  echo "  mode        - Modo: aggressive (padrao) ou conservative"
  echo ""
  echo "Exemplos:"
  echo "  $0 ./video.mp4"
  echo "  $0 ./video.mp4 ./meus-cortes"
  echo "  $0 ./video.mp4 ./meus-cortes conservative"
}

main() {
  local video="$1"
  local output_dir="${2:-./output}"
  local mode="${3:-aggressive}"

  if [ -z "$video" ]; then
    usage
    exit 1
  fi

  if [ "$mode" != "aggressive" ] && [ "$mode" != "conservative" ]; then
    error "Modo invalido: $mode. Use aggressive ou conservative"
  fi

  VIDEO_PATH="$(realpath "$video")"
  OUTPUT_DIR="$(realpath -m "$output_dir")"
  MODE="$mode"
  RUN_DIR="$OUTPUT_DIR/$(date +%Y%m%d_%H%M)"
  TEMP_DIR="/tmp/shortcutter_$$"

  mkdir -p "$TEMP_DIR" "$OUTPUT_DIR"

  echo ""
  echo "Video Cutter - Iniciando..."
  echo "  Video: $(basename "$VIDEO_PATH")"
  echo "  Modo: $MODE"
  echo ""

  check_dependencies
  validate_input "$VIDEO_PATH"
  extract_audio "$VIDEO_PATH"
  transcribe_audio
  sanitize_timestamps
  analyze_cuts
  validate_timestamps
  apply_buffer
  generate_clips "$VIDEO_PATH"
  generate_metadata
  show_results
}

main "$@"
