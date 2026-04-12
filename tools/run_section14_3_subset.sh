#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}"

echo "[section14_3_subset] starting model-scale subset at $(date -Is)"
python3 tools/run_benchmark.py --config config/benchmark_model_scale_subset.json

sleep 2

echo "[section14_3_subset] starting quantization subset at $(date -Is)"
python3 tools/run_benchmark.py --config config/benchmark_quantization_subset.json

echo "[section14_3_subset] generating summary report at $(date -Is)"
python3 tools/generate_section14_3_report.py

echo "[section14_3_subset] completed at $(date -Is)"
