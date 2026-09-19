#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ENV_FILE="$SCRIPT_DIR/.env"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"

if [ ! -f "$ENV_FILE" ]; then
    printf '%s\n' "Missing $ENV_FILE" >&2
    printf '%s\n' "Create it with: cp $SCRIPT_DIR/.env.example $ENV_FILE" >&2
    exit 1
fi

docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d --build
