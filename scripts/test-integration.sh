#!/usr/bin/env bash

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
RESET='\033[0m'

# Configuration
COMPOSE_FILE='compose.test.yml'
LOG_FILE='build.log'
TEST_SELECTORS=()
export PODMAN_COMPOSE_WARNING_LOGS=false

# Directories
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
CLI_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="$CLI_DIR/compose.test.yml"

# Compose command
COMPOSE=(podman compose -f "$COMPOSE_FILE")

usage() {
  printf 'Usage: %s [-t tests.module::test_name]\n' "$0"
}

while (($#)); do
  case "$1" in
    -t)
      if (($# < 2)) || [[ -z "$2" || "$2" == -* ]]; then
        usage
        exit 2
      fi
      TEST_SELECTORS+=("$2")
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'Option inconnue : %s\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

# Helper to print section headers with colors
section() {
  printf "\n"
  local color="$1"
  local title="$2"
  len=${#title}
  left_and_right=3
  total=$(tput cols)
  spaces=$(( (total - len - 2 * left_and_right - 2) / 2 ))
  added=$((len % 2))
  printf -- "${color}%*s\n" "$total" '' | tr ' ' '='
  printf "%*s" "$left_and_right" '' | tr ' ' '='
  printf "‖%*s" "${spaces}" ''
  printf "%s" "$title"
  printf "%*s" $((spaces + added)) ''
  printf "‖"
  printf "%*s\n" "$left_and_right" '' | tr ' ' '='
  printf -- "%*s\n${RESET}" "$total" '' | tr ' ' '='
}

# Display the result of a function execution with colored messages
result() {
  # result "function_name" "message_if_ok" "message_if_nok"
  local function_name="$1"
  local if_ok="$2"
  local if_nok="$3"
 $function_name
  code=$?
  if (( code == 0 )); then
    printf "${GREEN}%s${RESET}\n" "$if_ok"
  else
    printf "${RED}%s${RESET}\n" "$if_nok"
  fi
}

prepare_environment() {
  if [[ ! -f "$COMPOSE_FILE" ]]; then
    printf "${RED}%s${RESET}\n" "Compose file $COMPOSE_FILE not found."
    exit 1
  fi
  if ! command -v podman &> /dev/null; then
    printf "${RED}%s${RESET}\n" "Podman is not installed."
    exit 1
  fi
  ${COMPOSE[@]} up -d server > "$LOG_FILE" 2>&1

  if (( $? != 0 )); then
    printf "${RED}%s${RESET}\n" "Failed to pull server image. See $LOG_FILE for details."
    cat "$LOG_FILE"
    rm -f "$LOG_FILE"
    exit 1
  fi
}

launch_tests() {
  # Launch only the test container with the requested pytest selection.
  local -a pytest_args=("-v" "--color=yes" "-ra" "-p" "no:cacheprovider")
  local -a compose_args=(run --rm --no-deps)
  pytest_args+=("${TEST_SELECTORS[@]}")
  podman compose -f "$COMPOSE_FILE" "${compose_args[@]}" cli-tests \
    python -m pytest "${pytest_args[@]}"
  code=$?
  if (( code != 0 )); then
    echo "Erreur lors du lancement des tests. Voir $LOG_FILE pour les détails."
    cat "$LOG_FILE"
    rm -f "$LOG_FILE"
    exit "$code"
  fi
  rm -f "$LOG_FILE"
}

cleanup() {
  local exit_code=$?
  trap - EXIT
  "${COMPOSE[@]}" down --remove-orphans >/dev/null 2>&1 || true
  rm -f "$LOG_FILE"
  printf "\n"
  printf "${YELLOW}%s${RESET}\n" "Cleanup completed."
  printf "\n"
  exit "$exit_code"
}

trap cleanup EXIT

printf "\n"
section "${GREEN}" "Preparing environment"
result "prepare_environment" "Environment prepared successfully" "Failed to prepare environment"
printf "\n"

section "${RED}" "Running CLI tests"
result "launch_tests" "CLI tests passed successfully" "CLI tests failed"
printf "\n"

section "${YELLOW}" "Cleanup"
result "cleanup" "Cleanup completed successfully" "Cleanup failed"
printf "\n"
