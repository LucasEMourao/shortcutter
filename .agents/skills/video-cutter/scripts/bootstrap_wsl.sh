#!/bin/bash
# bootstrap_wsl.sh - Normaliza scripts e docs principais para execucao no WSL

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_DIR="$(cd "$SKILL_DIR/../../.." && pwd)"

normalize_files() {
  local target_dir="$1"
  shift

  find "$target_dir" "$@" -type f -print0 | while IFS= read -r -d '' file; do
    sed -i 's/\r$//' "$file"
  done
}

normalize_files "$SCRIPT_DIR" \( -name "*.sh" -o -name "*.py" \)
normalize_files "$SKILL_DIR" \( -name "*.md" -o -name "*.json" \)
normalize_files "$PROJECT_DIR" -maxdepth 1 \( -name "*.md" -o -name "requirements.txt" -o -name ".gitattributes" \)

chmod +x "$SCRIPT_DIR"/*.sh

echo "Workspace do video-cutter normalizado para WSL."
