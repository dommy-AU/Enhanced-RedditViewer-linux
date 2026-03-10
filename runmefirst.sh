#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if ! command -v python3 >/dev/null 2>&1; then
    echo "Error: python3 is not installed."
    exit 1
fi

if [ ! -f "reddit_public_media_viewer.py" ]; then
    echo "Error: reddit_public_media_viewer.py not found in $SCRIPT_DIR"
    exit 1
fi

if [ ! -f "requirements-reddit-public-media-viewer.txt" ]; then
    echo "Error: requirements-reddit-public-media-viewer.txt not found in $SCRIPT_DIR"
    exit 1
fi

if command -v ffmpeg >/dev/null 2>&1; then
    echo "ffmpeg already detected. Skipping install."
else
    echo "ffmpeg not detected."

    if command -v apt-get >/dev/null 2>&1; then
        echo "Installing ffmpeg with apt..."
        sudo apt-get update
        sudo apt-get install -y ffmpeg
    else
        echo "Error: ffmpeg is missing and apt-get is not available on this system."
        echo "Please install ffmpeg manually, then run this script again."
        exit 1
    fi

    if ! command -v ffmpeg >/dev/null 2>&1; then
        echo "Error: ffmpeg installation appears to have failed."
        exit 1
    fi
fi

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

echo "Installing requirements..."
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements-reddit-public-media-viewer.txt

echo "Starting Reddit Public Media Viewer..."
python3 reddit_public_media_viewer.py &
APP_PID=$!

sleep 2
xdg-open "http://127.0.0.1:65010" >/dev/null 2>&1 || true

wait $APP_PID
