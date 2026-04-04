#!/usr/bin/env bash

if ! command -v podman >/dev/null 2>&1; then
    echo "Error: podman is not installed."
    exit 1
fi

SCRIPT_DIR="$(dirname $(realpath ${BASH_SOURCE[0]}))"

podman build -t reddit-media-webapp "$SCRIPT_DIR"
podman run --name reddit-media -d -e HOST=::0 -p 65010:65010 --replace reddit-media-webapp:latest
sleep 1
xdg-open "http://localhost:65010"
