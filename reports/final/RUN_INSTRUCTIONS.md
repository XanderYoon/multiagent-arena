# Reproducible Run Instructions

## Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Start Ollama and ensure the required Qwen models are installed:

```bash
bash tools/install_qwen_models.sh section14_3
ollama serve
```

## Section 14.3 Runs

```bash
python3 tools/run_benchmark.py --config /NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/configs/benchmark_model_scale_subset.json
```

```bash
python3 tools/run_benchmark.py --config /NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/configs/benchmark_quantization_subset.json
```

## Regenerate Final Deliverables

```bash
python3 tools/generate_final_deliverables.py
```

## Selected Run IDs

- `run_20260410_215833_032b2a0_dirty`
- `run_20260411_002628_032b2a0_dirty`
