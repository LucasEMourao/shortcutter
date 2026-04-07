#!/bin/bash
# run.sh - Automatiza o fluxo completo da skill video-cutter
# Uso: ./scripts/run.sh <video_path> [output_dir] [mode]
#
# Argumentos:
#   video_path  - Caminho do vídeo de entrada (obrigatório)
#   output_dir  - Diretório de output (opcional, padrão: ./output)
#   mode        - Modo de operação: aggressive (padrão) ou conservative
#
# Exemplos:
#   ./scripts/run.sh ./video.mp4
#   ./scripts/run.sh ./video.mp4 ./meus-cortes
#   ./scripts/run.sh ./video.mp4 ./meus-cortes conservative

set -e

# === Configurações ===
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_DIR="$(cd "$SKILL_DIR/../../.." && pwd)"
TEMP_DIR="/tmp/shortcutter_$$"
PADDING_MAX=2.0
MIN_DURATION=15
MAX_DURATION=60
GEMINI_MODEL=""  # Será preenchido dinamicamente pelo analyze_adaptive.py

# === Funções auxiliares ===

log() {
  echo "[$(date +%H:%M:%S)] $1"
}

error() {
  echo "❌ ERRO: $1" >&2
  exit 1
}

warn() {
  echo "⚠️  AVISO: $1" >&2
}

cleanup() {
  rm -rf "$TEMP_DIR"
}

trap cleanup EXIT

# === Verificar dependências ===

check_dependencies() {
  log "Verificando dependências..."
  
  for cmd in ffmpeg ffprobe curl python3 bc; do
    if ! command -v "$cmd" &>/dev/null; then
      error "$cmd não está instalado"
    fi
  done
  
  if [ -z "$GEMINI_API_KEY" ]; then
    # Tentar carregar do .env no diretório do projeto
    if [ -f "$PROJECT_DIR/.env" ]; then
      log "Carregando GEMINI_API_KEY de .env..."
      set -a
      source "$PROJECT_DIR/.env"
      set +a
    fi
    
    if [ -z "$GEMINI_API_KEY" ]; then
      error "GEMINI_API_KEY não configurada. Crie um arquivo .env com GEMINI_API_KEY=sua_chave"
    fi
  fi
  
  log "✓ Todas as dependências OK"
}

# === Passo 1: Validar entrada ===

validate_input() {
  local video="$1"
  
  log "Passo 1: Validando entrada..."
  
  if [ ! -f "$video" ]; then
    error "Vídeo não encontrado: $video"
  fi
  
  # Verificar se tem áudio
  local has_audio=$(ffprobe -v quiet -select_streams a:0 -show_entries stream=codec_name -of default=noprint_wrappers=1:nokey=1 "$video" 2>/dev/null)
  if [ -z "$has_audio" ]; then
    error "Vídeo sem áudio: $video"
  fi
  
  # Obter duração
  VIDEO_DURATION=$(ffprobe -v quiet -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$video")
  
  if (( $(echo "$VIDEO_DURATION < 15" | bc -l) )); then
    error "Vídeo muito curto (${VIDEO_DURATION}s). Mínimo: 15s"
  fi
  
  # Obter info
  VIDEO_NAME=$(basename "$video")
  VIDEO_RES=$(ffprobe -v quiet -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 "$video" 2>/dev/null || echo "N/A")
  
  log "✓ Vídeo: $VIDEO_NAME"
  log "✓ Duração: ${VIDEO_DURATION}s"
  log "✓ Resolução: $VIDEO_RES"
  log "✓ Áudio: $has_audio"
}

# === Passo 2: Extrair áudio ===

extract_audio() {
  local video="$1"
  
  log "Passo 2: Extraindo áudio..."
  
  AUDIO_FILE="$TEMP_DIR/audio.wav"
  ffmpeg -i "$video" -vn -acodec pcm_s16le -ar 16000 -ac 1 "$AUDIO_FILE" -y 2>/dev/null
  
  log "✓ Áudio extraído: $AUDIO_FILE"
}

# === Passo 3: Transcrever com Whisper (local) ===

transcribe_audio() {
  log "Passo 3: Transcrevendo áudio com Whisper..."
  
  # Verificar se faster-whisper está instalado
  if ! python3 -c "from faster_whisper import WhisperModel" 2>/dev/null; then
    error "faster-whisper não instalado. Instale com: pip3 install --user --break-system-packages faster-whisper"
  fi
  
  # Transcrever usando Whisper
  python3 << PYEOF
from faster_whisper import WhisperModel
import json, sys

video_path = "$VIDEO_PATH"
output_path = '$TEMP_DIR/transcription.json'

print("  Carregando modelo Whisper (small)...")
model = WhisperModel("small", device="cpu", compute_type="int8")

print(f"  Transcrevendo: {video_path}")
segments, info = model.transcribe(video_path, language="pt", beam_size=5)

transcription = []
for i, seg in enumerate(segments):
    transcription.append({
        "id": i + 1,
        "start_sec": round(seg.start, 2),
        "end_sec": round(seg.end, 2),
        "text": seg.text.strip()
    })

result = {
    "transcription": transcription,
    "total_duration_sec": round(info.duration, 2),
    "language": info.language,
    "language_probability": round(info.language_probability, 4),
    "method": "whisper",
    "model_size": "small"
}

with open(output_path, 'w') as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

print(f"  Transcrição: {len(transcription)} segmentos")
print(f"  Idioma: {info.language} ({info.language_probability:.2%})")
PYEOF
  
  log "✓ Transcrição concluída"
}

# === Passo 4: Sanitizar timestamps ===

sanitize_timestamps() {
  log "Passo 4: Sanitizando timestamps..."
  
  python3 << PYEOF
import json

with open('$TEMP_DIR/transcription.json') as f:
    transcription = json.load(f)

video_duration = float('$VIDEO_DURATION')
max_ts = max(seg['end_sec'] for seg in transcription['transcription'])
warnings = []

if max_ts > video_duration:
    scale = video_duration / max_ts
    for seg in transcription['transcription']:
        seg['start_sec'] = round(seg['start_sec'] * scale, 3)
        seg['end_sec'] = round(seg['end_sec'] * scale, 3)
    warnings.append(f'Normalização aplicada: escala {scale:.4f}')
    print(f'  Normalização aplicada (escala: {scale:.4f})')

# Remover segmentos inválidos
original_count = len(transcription['transcription'])
transcription['transcription'] = [
    seg for seg in transcription['transcription']
    if seg['start_sec'] >= 0
    and seg['end_sec'] <= video_duration
    and seg['end_sec'] > seg['start_sec']
]
removed = original_count - len(transcription['transcription'])
if removed > 0:
    warnings.append(f'{removed} segmentos removidos por timestamps inválidos')

transcription['sanitization'] = {
    'applied': max_ts > video_duration,
    'original_max_ts': max_ts,
    'warnings': warnings
}

with open('$TEMP_DIR/transcription_sanitized.json', 'w') as f:
    json.dump(transcription, f, indent=2, ensure_ascii=False)

print(f'  Segmentos válidos: {len(transcription["transcription"])}')
PYEOF
  
  log "✓ Sanitização concluída"
}

# === Passo 5: Identificar cortes virais (com chunking) ===

analyze_cuts() {
  log "Passo 5: Analisando cortes virais (adaptativo)..."
  
  # Usar script adaptativo (decide entre análise direta vs chunked baseado na duração)
  local adaptive_script="$SKILL_DIR/scripts/analyze_adaptive.py"
  if [ ! -f "$adaptive_script" ]; then
    error "Script adaptativo não encontrado: $adaptive_script"
  fi
  
  # Executar análise adaptativa (modelo é descoberto dinamicamente via API)
  python3 "$adaptive_script" \
    "$TEMP_DIR/transcription_sanitized.json" \
    "$VIDEO_DURATION" \
    "$MODE" \
    "$TEMP_DIR/analysis.json" \
    "$GEMINI_API_KEY"
  
  if [ $? -ne 0 ]; then
    error "Falha na análise adaptativa"
  fi
  
  # Extrair cortes válidos para o formato esperado pelos próximos passos
  python3 << PYEOF
import json, sys

with open('$TEMP_DIR/analysis.json') as f:
    analysis = json.load(f)

video_duration = float('$VIDEO_DURATION')
valid = []
invalid = []
for cut in analysis['cuts']:
    dur = cut['end_sec'] - cut['start_sec']
    if cut['end_sec'] <= video_duration and cut['start_sec'] >= 0 and 15 <= dur <= 60:
        valid.append(cut)
    else:
        invalid.append(cut)

print(f'Análise: {len(valid)} cortes válidos, {len(invalid)} inválidos')
PYEOF
  
  log "✓ Análise concluída"
}

# === Passo 6: Validar timestamps ===

validate_timestamps() {
  log "Passo 6: Validando timestamps..."
  
  python3 << PYEOF
import json

with open('$TEMP_DIR/analysis.json') as f:
    analysis = json.load(f)

video_duration = float('$VIDEO_DURATION')
valid_cuts = []

for cut in analysis['cuts']:
    dur = cut['end_sec'] - cut['start_sec']
    start_ok = cut['start_sec'] >= 0
    end_ok = cut['end_sec'] <= video_duration
    duration_ok = 15 <= dur <= 60
    order_ok = cut['end_sec'] > cut['start_sec']
    
    if start_ok and end_ok and duration_ok and order_ok:
        valid_cuts.append(cut)
        print(f'  ✓ Cut {cut["id"]}: {cut["start_sec"]:.1f}s - {cut["end_sec"]:.1f}s ({dur:.1f}s)')
    else:
        print(f'  ✗ Cut {cut["id"]}: INVÁLIDO (start={start_ok}, end={end_ok}, dur={duration_ok}, order={order_ok})')

with open('$TEMP_DIR/valid_cuts.json', 'w') as f:
    json.dump(valid_cuts, f, indent=2, ensure_ascii=False)

print(f'\\nCortes válidos: {len(valid_cuts)}')
PYEOF
  
  log "✓ Validação concluída"
}

# === Passo 7: Aplicar buffer inteligente ===

apply_buffer() {
  log "Passo 7: Aplicando buffer inteligente..."
  
  python3 << PYEOF
import json

with open('$TEMP_DIR/transcription_sanitized.json') as f:
    transcription = json.load(f)['transcription']

with open('$TEMP_DIR/valid_cuts.json') as f:
    cuts = json.load(f)

video_duration = float('$VIDEO_DURATION')
max_gap = float('$PADDING_MAX')
fixed_buffer = 2.0  # Buffer fixo quando gap é muito grande
buffer_details = []

for cut in cuts:
    # Encontrar próximo segmento após o fim do corte
    next_seg = None
    for seg in transcription:
        if seg['start_sec'] > cut['end_sec'] + 0.5:
            next_seg = seg
            break
    
    original_end = cut['end_sec']
    
    if next_seg:
        gap = next_seg['start_sec'] - cut['end_sec']
        if gap <= max_gap:
            cut['end_sec'] = round(next_seg['start_sec'], 1)
            detail = {
                'id': cut['id'],
                'original_end': original_end,
                'next_segment_start': next_seg['start_sec'],
                'gap': gap,
                'buffer_applied': gap,
                'reason': 'Estendido até próximo segmento (gap <= 2s)'
            }
        else:
            cut['end_sec'] = round(min(video_duration, cut['end_sec'] + fixed_buffer), 1)
            detail = {
                'id': cut['id'],
                'original_end': original_end,
                'next_segment_start': next_seg['start_sec'],
                'gap': gap,
                'buffer_applied': fixed_buffer,
                'reason': f'Buffer fixo {fixed_buffer}s (gap {gap:.1f}s > {max_gap}s)'
            }
    else:
        cut['end_sec'] = video_duration
        detail = {
            'id': cut['id'],
            'original_end': original_end,
            'next_segment_start': None,
            'gap': None,
            'buffer_applied': video_duration - original_end,
            'reason': 'Último corte - estendido até fim do vídeo'
        }
    
    cut['duration'] = round(cut['end_sec'] - cut['start_sec'], 1)
    buffer_details.append(detail)
    print(f'  Cut {cut["id"]}: {original_end:.1f}s → {cut["end_sec"]:.1f}s ({detail["reason"]})')

# Ordenar por timestamp antes de verificar sobreposições
cuts.sort(key=lambda c: c['start_sec'])

# Verificar sobreposições
for i in range(len(cuts) - 1):
    if cuts[i]['end_sec'] > cuts[i+1]['start_sec']:
        cuts[i]['end_sec'] = cuts[i+1]['start_sec']
        cuts[i]['duration'] = round(cuts[i]['end_sec'] - cuts[i]['start_sec'], 1)
        print(f'  ⚠️  Cut {cuts[i]["id"]}: sobreposição corrigida → {cuts[i]["end_sec"]:.1f}s')

result = {
    'cuts': cuts,
    'buffer_details': buffer_details
}

with open('$TEMP_DIR/final_cuts.json', 'w') as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

print(f'\\nBuffer aplicado: {len(cuts)} cortes finais')
PYEOF
  
  log "✓ Buffer inteligente aplicado"
}

# === Passo 8: Gerar clips ===

generate_clips() {
  log "Passo 8: Gerando clips..."
  
  mkdir -p "$RUN_DIR"
  
  python3 << PYEOF
import json, subprocess, os

with open('$TEMP_DIR/final_cuts.json') as f:
    data = json.load(f)

cuts = data['cuts']
video = "$1"
run_dir = "$RUN_DIR"
helper = "$SKILL_DIR/scripts/helper.sh"

for i, cut in enumerate(cuts):
    start = str(cut['start_sec'])
    end = str(cut['end_sec'])
    nn = f"{i+1:02d}"
    start_int = int(cut['start_sec'])
    end_int = int(cut['end_sec'])
    filename = f"cut_{nn}_{start_int}-{end_int}s.mp4"
    output = os.path.join(run_dir, filename)
    
    cmd = [helper, 'cut', video, start, end, output]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        cut['filename'] = filename
        cut['path'] = f"./output/{os.path.basename(run_dir)}/{filename}"
        print(f'  ✓ {filename} ({cut["duration"]:.1f}s)')
    else:
        print(f'  ✗ {filename}: {result.stderr}')

with open('$TEMP_DIR/final_cuts_with_files.json', 'w') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
PYEOF
  
  log "✓ Clips gerados"
}

# === Passo 9: Gerar cuts.json ===

generate_metadata() {
  log "Passo 9: Gerando metadados..."
  
  python3 << PYEOF
import json
from datetime import datetime

with open('$TEMP_DIR/final_cuts_with_files.json') as f:
    data = json.load(f)

with open('$TEMP_DIR/analysis.json') as f:
    analysis = json.load(f)

with open('$TEMP_DIR/transcription_sanitized.json') as f:
    transcription = json.load(f)

mode = "$MODE"
run_dir_name = "$(basename "$RUN_DIR")"

output = {
    'input_video': "$VIDEO_NAME",
    'output_dir': f"./output/{run_dir_name}",
    'generated_at': datetime.now().isoformat() + 'Z',
    'model': analysis.get('model_used', 'unknown'),
    'mode': mode,
    'buffer_strategy': 'intelligent_gap_2s',
    'analysis': {
        'content_type': analysis['analysis']['content_type'],
        'main_topics': analysis['analysis']['main_topics'],
        'overall_viral_potential': analysis['analysis']['overall_viral_potential']
    },
    'chunking_info': analysis.get('chunking_info', {}),
    'buffer_details': data['buffer_details'],
    'cuts': data['cuts'],
    'total_cuts': len(data['cuts']),
    'quality_warnings': analysis.get('quality_warnings', [])
}

output_path = "$RUN_DIR/cuts.json"
with open(output_path, 'w') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(f'Metadados salvos: {output_path}')
PYEOF
  
  log "✓ Metadados gerados"
}

# === Apresentar resultados ===

show_results() {
  echo ""
  echo "═══════════════════════════════════════════════"
  echo "  ✅ CORTES GERADOS COM SUCESSO"
  echo "═══════════════════════════════════════════════"
  echo ""
  echo "📁 Output: $RUN_DIR"
  echo "🎬 Clips: $1"
  echo "🤖 Modelo: $GEMINI_MODEL"
  echo "🔧 Modo: $MODE"
  echo ""
  echo "📊 Resumo:"
  
  python3 << PYEOF
import json

with open('$RUN_DIR/cuts.json') as f:
    data = json.load(f)

for cut in data['cuts']:
    print(f"  - {cut['filename']} ({cut['duration']:.1f}s) - Score: {cut['viral_score']} - {cut['hook_type']}")
PYEOF
  
  echo ""
  echo "📄 Metadados: $RUN_DIR/cuts.json"
  echo ""
  echo "Para visualizar:"
  echo "  explorer.exe $RUN_DIR"
  echo ""
}

# === Main ===

main() {
  local video="$1"
  local output_dir="${2:-./output}"
  local mode="${3:-aggressive}"
  
  # Validação de argumentos
  if [ -z "$video" ]; then
    echo "Uso: $0 <video_path> [output_dir] [mode]"
    echo ""
    echo "Argumentos:"
    echo "  video_path  - Caminho do vídeo de entrada (obrigatório)"
    echo "  output_dir  - Diretório de output (opcional, padrão: ./output)"
    echo "  mode        - Modo: aggressive (padrão) ou conservative"
    echo ""
    echo "Exemplos:"
    echo "  $0 ./video.mp4"
    echo "  $0 ./video.mp4 ./meus-cortes"
    echo "  $0 ./video.mp4 ./meus-cortes conservative"
    exit 1
  fi
  
  # Configurar variáveis globais
  VIDEO_PATH="$(realpath "$video")"
  OUTPUT_DIR="$(realpath "$output_dir")"
  MODE="$mode"
  RUN_DIR="$OUTPUT_DIR/$(date +%Y%m%d_%H%M)"
  TEMP_DIR="/tmp/shortcutter_$$"
  
  # Criar diretórios
  mkdir -p "$TEMP_DIR" "$OUTPUT_DIR"
  
  # Executar fluxo
  echo ""
  echo "🎬 Video Cutter - Iniciando..."
  echo "   Vídeo: $(basename "$VIDEO_PATH")"
  echo "   Modo: $MODE"
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
  
  # Contar clips gerados
  local clip_count=$(ls -1 "$RUN_DIR"/*.mp4 2>/dev/null | wc -l)
  
  show_results "$clip_count"
}

main "$@"
