#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: tools/install_qwen_models.sh [suite]

Suites:
  baseline       Install the default project baseline model only.
  model-scale    Install Qwen models used for the Section 14.3 parameter-count suite.
  quantization   Install Qwen models used for the Section 14.3 quantization suite.
  section14_3    Install both Section 14.3 suites.
  all            Install baseline plus both Section 14.3 suites.

If no suite is provided, defaults to `all`.
EOF
}

require_ollama() {
  if ! command -v ollama >/dev/null 2>&1; then
    echo "Error: `ollama` is not installed or not on PATH." >&2
    exit 1
  fi
}

pull_models() {
  for model in "$@"; do
    echo "Pulling ${model}..."
    ollama pull "${model}"
  done
}

main() {
  local suite="${1:-all}"
  require_ollama

  case "${suite}" in
    baseline)
      pull_models "qwen2.5:7b"
      ;;
    model-scale)
      pull_models "qwen2.5:3b" "qwen2.5:7b" "qwen2.5:14b"
      ;;
    quantization)
      pull_models "qwen2.5:7b-instruct-q4_0" "qwen2.5:7b-instruct-q8_0" "qwen2.5:7b-instruct-fp16"
      ;;
    section14_3)
      pull_models "qwen2.5:3b" "qwen2.5:7b" "qwen2.5:14b" "qwen2.5:7b-instruct-q4_0" "qwen2.5:7b-instruct-q8_0" "qwen2.5:7b-instruct-fp16"
      ;;
    all)
      pull_models "qwen2.5:3b" "qwen2.5:7b" "qwen2.5:14b" "qwen2.5:7b-instruct-q4_0" "qwen2.5:7b-instruct-q8_0" "qwen2.5:7b-instruct-fp16"
      ;;
    -h|--help|help)
      usage
      ;;
    *)
      echo "Unknown suite: ${suite}" >&2
      usage >&2
      exit 1
      ;;
  esac
}

main "$@"
