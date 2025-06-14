#!/bin/bash

# === CONFIGURATION ===
VENV_PATH="/Users/mickey/tovia_ai_assistant/mimic3_env"
PYTHON_SCRIPT="/Users/mickey/tovia_ai_assistant/basic_tts_assist.py"
VOICE_SERVER_LOG="mimic3.log"

# === ACTIVATE VIRTUAL ENVIRONMENT ===
source "$VENV_PATH/bin/activate"

# === START MIMIC3 SERVER IN BACKGROUND ===
echo "Starting Mimic3 server..."
mimic3-server > "$VOICE_SERVER_LOG" 2>&1 &
MIMIC_PID=$!

# === START OLLAMA SERVER IN BACKGROUND ===
echo "Starting Ollama server..."
ollama serve > /dev/null 2>&1 &
OLLAMA_PID=$!

# === HANDLE CLEAN EXIT ===
trap "echo -e '\nShutting down Tovia...'; kill $MIMIC_PID $OLLAMA_PID; deactivate; exit" SIGINT

# === RUN YOUR ASSISTANT ===
echo "Launching Tovia..."
python3 "$PYTHON_SCRIPT"

# === CLEANUP ===
if ps -p $MIMIC_PID > /dev/null; then
    kill $MIMIC_PID
fi

if ps -p $OLLAMA_PID > /dev/null; then
    kill $OLLAMA_PID
fi
deactivate
