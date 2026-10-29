#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
CLI_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="$CLI_DIR/compose.test.yml"
PROJECT_NAME="ttlama-cli-integration-${USER:-user}-$$"
COMPOSE=(podman compose --project-name "$PROJECT_NAME" --file "$COMPOSE_FILE")

cleanup() {
  local exit_code=$?
  trap - EXIT
  "${COMPOSE[@]}" down --remove-orphans >/dev/null 2>&1 || true
  exit "$exit_code"
}

trap cleanup EXIT

"${COMPOSE[@]}" pull server
"${COMPOSE[@]}" run --build --rm cli-tests