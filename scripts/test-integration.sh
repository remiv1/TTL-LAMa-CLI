#!/usr/bin/env bash
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
RESET='\033[0m'
COMPOSE_FILE='compose.test.yml'
LOG_FILE='build.log'
ONLY_SQLITE=false
WITHOUT_OIDC=false
TEST_SELECTORS=()
CONTAINERS_TO_DOWN=''
export PODMAN_COMPOSE_WARNING_LOGS=false
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
CLI_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="$CLI_DIR/compose.test.yml"
PROJECT_NAME="ttlama-cli-integration-${USER:-user}-$$"
COMPOSE=(podman compose --project-name "$PROJECT_NAME" --file "$COMPOSE_FILE")

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
  local color="$1"
  local title="$2"
  len=${#title}
  left_and_right=3
  total=80
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

launch_tests() {
  # Launch only the test container with the requested pytest selection.
  local -a pytest_args=("-v" "--color=yes" "-ra" "-p" "no:cacheprovider")
  local -a compose_args=(run --rm --no-deps)
  pytest_args+=("${TEST_SELECTORS[@]}")
  podman compose -f "$COMPOSE_FILE" "${compose_args[@]}" tests \
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
  exit "$exit_code"
}

pull_server_image() {
  "${COMPOSE[@]}" pull server
}

trap cleanup EXIT

printf "\n"
section "${GREEN}" "Pulling server image"
result "pull_server_image" "Server image pulled successfully" "Failed to pull server image"
printf "\n"

section "${RED}" "Running CLI tests"
result "launch_tests" "CLI tests passed successfully" "CLI tests failed"
printf "\n"

section "${YELLOW}" "Cleanup"
result "cleanup" "Cleanup completed successfully" "Cleanup failed"
printf "\n"
