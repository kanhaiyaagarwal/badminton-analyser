#!/usr/bin/env bash
# Download the Vosk small English model for offline voice command recognition.
# Stored at weights/vosk-model-small-en-us/ (~40MB).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
MODEL_DIR="$PROJECT_ROOT/weights/vosk-model-small-en-us"

if [ -d "$MODEL_DIR" ]; then
  echo "Vosk model already exists at $MODEL_DIR"
  exit 0
fi

mkdir -p "$PROJECT_ROOT/weights"

echo "Downloading vosk-model-small-en-us-0.15..."
curl -Lo /tmp/vosk-model.zip https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip

echo "Extracting..."
unzip -q /tmp/vosk-model.zip -d "$PROJECT_ROOT/weights/"
mv "$PROJECT_ROOT/weights/vosk-model-small-en-us-0.15" "$MODEL_DIR"

rm -f /tmp/vosk-model.zip
echo "Done — model at $MODEL_DIR"
