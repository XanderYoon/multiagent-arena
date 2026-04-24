# Multi-Agent LLM Game Benchmark

This repository contains a prototype benchmark for comparing single-agent and multi-agent LLM orchestration on adversarial games.

## Repository Layout

The repository is now organized around code, machine-readable configs, generated run artifacts, and analysis outputs.

```text
.
├── benchmark/
│   ├── agents.py
│   ├── architectures.py
│   ├── experiment_logging.py
│   ├── game_engine.py
│   ├── loader.py
│   ├── main.py
│   ├── metrics.py
│   └── reproducibility.py
├── config/
│   ├── benchmark.json
│   ├── benchmark_mock.json
│   ├── benchmark_model_scale.json
│   ├── benchmark_model_scale_subset.json
│   ├── benchmark_quantization.json
│   ├── benchmark_quantization_subset.json
│   ├── architectures/
│   ├── experiments/
│   ├── games/
│   ├── models/
│   ├── prompts/
│   └── specs/
│       └── templates/
├── docs/
│   ├── plans/
│   └── proposal/
├── reports/
│   ├── final/
│   ├── latest/
│   ├── notes/
│   ├── runs/
│   └── scripts/
├── runs/
│   ├── experiment_runs/
│   └── latest/
├── tools/
│   ├── run_benchmark.py
│   ├── execute_experiment_plan.py
│   ├── resume_experiment_run.py
│   ├── generate_analysis_report.py
│   ├── generate_section14_3_report.py
│   ├── generate_final_deliverables.py
│   └── run_section14_3_subset.sh
├── tests/
├── main.py
├── requirements.txt
└── AGENTS.md
```

Core benchmark code now lives directly under `benchmark/`, with one module per major subsystem. Runnable commands are consolidated under `tools/`, reporting implementations live under `reports/scripts/`, generated analysis bundles live under `reports/latest/` and `reports/final/`, and persistent run artifacts remain under `reports/runs/`.

## Environment Setup

Runtime target:

- Python `3.14.2` via [`.python-version`](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/.python-version)
- Dependencies pinned in [requirements.txt](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/requirements.txt)

Create an environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

The benchmark expects a local Ollama server and the default model configured in [config/models/ollama_qwen2_5_7b.json](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/config/models/ollama_qwen2_5_7b.json):

```bash
ollama pull qwen2.5:7b
ollama serve
```

To install the exact Qwen model sets used by this repository, use [tools/install_qwen_models.sh](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/tools/install_qwen_models.sh):

```bash
bash tools/install_qwen_models.sh baseline
bash tools/install_qwen_models.sh model-scale
bash tools/install_qwen_models.sh quantization
bash tools/install_qwen_models.sh section14_3
```

Model mapping:

- `baseline`: `qwen2.5:7b`
- `model-scale`: `qwen2.5:3b`, `qwen2.5:7b`, `qwen2.5:14b`
- `quantization`: `qwen2.5:7b-instruct-q4_0`, `qwen2.5:7b-instruct-q8_0`, `qwen2.5:7b-instruct-fp16`

Recommended hardware interpretation for the Parameter Count/Quanitzation sweeps:

- `qwen2.5:7b` is the medium model and matches the project baseline.
- `qwen2.5:3b` is the smaller variant for the model-scale suite.
- `qwen2.5:14b` is the larger variant. On a 16 GB GPU it is more realistic than moving farther up the size ladder, though it may still run slower and may partially offload depending on your Ollama/GPU settings.
- The quantization suite stays on `qwen2.5` 7B and uses the currently published Ollama instruction-tuned quantized tags: `q4_0`, `q8_0`, and `fp16`.

## Running Locally

Run the default benchmark:

```bash
python3 tools/run_benchmark.py --config config/benchmark.json
```

Run with a different benchmark config:

```bash
python3 tools/run_benchmark.py --config path/to/benchmark.json
```

Current execution-plan configs:

- Pilot architecture run: [config/experiments/pilot_architecture_comparison.json](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/config/experiments/pilot_architecture_comparison.json)
- Final architecture run: [config/experiments/final_architecture_comparison.json](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/config/experiments/final_architecture_comparison.json)
- Machine-readable run matrix: [config/experiments/execution_plan.json](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/config/experiments/execution_plan.json)
- Operator run sheet: [config/experiments/run_sheet.csv](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/config/experiments/run_sheet.csv)
- Narrative plan: [docs/plans/experiment_execution_plan.md](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/docs/plans/experiment_execution_plan.md)

Section 14 experiment and reporting tooling:

- Batch experiment matrix: [config/experiments/section14_run_matrix.json](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/config/experiments/section14_run_matrix.json)
- Local mock benchmark entrypoint: [config/benchmark_mock.json](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/config/benchmark_mock.json)
- Batch runner: `python3 tools/execute_experiment_plan.py --dry-run`
- Analysis bundle generator: `python3 tools/generate_analysis_report.py`

Qwen ensemble sweeps:

- Model-scale suite: `python3 tools/run_benchmark.py --config config/benchmark_model_scale.json`
- Quantization suite: `python3 tools/run_benchmark.py --config config/benchmark_quantization.json`
- Smaller model-scale suite: `python3 tools/run_benchmark.py --config config/benchmark_model_scale_subset.json`
- Smaller quantization suite: `python3 tools/run_benchmark.py --config config/benchmark_quantization_subset.json`
- One-command subset runner: `bash tools/run_section14_3_subset.sh`
- Parameter Count/Quantization summary report: `python3 tools/generate_section14_3_report.py`
- Section 15 final deliverables bundle: `python3 tools/generate_final_deliverables.py`

The subset configs intentionally keep only six architectures per suite:

- Model scale: balanced, large-heavy, and small-heavy variants for both parallel and hierarchical teams
- Quantization: balanced, high-quality-heavy, and low-quality-heavy variants for both parallel and hierarchical teams

`main.py` now prints progress lines in the form `[PROGRESS] Finished X/Y (...)`, so running either CLI directly shows how much of the schedule is done.

## Final Deliverables

Generate the final handoff bundle with:

```bash
python3 tools/generate_final_deliverables.py
```

This writes a self-contained package under `reports/final/` containing:

- `FINAL_REPORT.md` with a proposal-aligned writeup of objectives, results, and limitations
- `RUN_INSTRUCTIONS.md` with reproducible rerun commands
- `tables/` with summary and topline CSV/JSON outputs
- `figures/` with SVG result charts
- `key_runs/` with copied configs, metadata, summaries, and readable logs for the selected final runs

## Config System

The runner now reads machine-readable JSON config files for:

- Global benchmark settings: [config/benchmark.json](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/config/benchmark.json)
- Per-game settings: [config/games/blotto.json](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/config/games/blotto.json), [config/games/connect4.json](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/config/games/connect4.json)
- Per-model settings: [config/models/ollama_qwen2_5_7b.json](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/config/models/ollama_qwen2_5_7b.json)
- Prompt settings and template versions: [config/prompts/default_prompts.json](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/config/prompts/default_prompts.json)
- Architecture settings and ablations: [config/architectures/default_architectures.json](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/config/architectures/default_architectures.json)
- Per-experiment settings: [config/experiments/default_benchmark.json](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/config/experiments/default_benchmark.json)

`main.py` resolves these configs, snapshots them into each run directory, and uses them to determine model selection, prompt family/version, output paths, trial counts, seeds, enabled phases, and game parameters currently supported by the prototype.

## Experiment Output Layout

Each run is written to `runs/experiment_runs/run_{timestamp}_{commit}/` with this structure:

```text
runs/experiment_runs/run_YYYYMMDD_HHMMSS_commit/
├── config/
│   ├── benchmark.json
│   ├── architectures.json
│   ├── experiment.json
│   ├── model.json
│   ├── prompt.json
│   └── games/
├── logs/
│   ├── game_outcomes.jsonl
│   ├── llm_calls.jsonl
│   ├── trial_records.jsonl
│   ├── turn_records.jsonl
│   └── results.txt
├── metadata/
│   ├── reproducibility.json
│   └── run_manifest.json
└── summaries/
    ├── game_outcomes.csv
    ├── trial_records.csv
    ├── turn_records.csv
    └── summary.json
```

For convenience, the latest run log is also mirrored to [runs/latest/results.txt](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/runs/latest/results.txt).

The structured logs now supplement `runs/latest/results.txt` with:

- Per-trial metadata including seed, model, prompt version, architectures, timestamps, and game parameters
- Per-turn decision records including state snapshots, valid actions, raw model outputs, parsed responses, and legality flags
- Per-game outcome records including winners, scores, invalid attempts, and oracle-accuracy summaries when applicable

Each run also records reproducibility metadata including the global seed, deterministic child-seed schedule, git revision, runtime environment, and model identity details when available from the backend.

## LLM Runtime

The LLM interface now supports:

- Configurable backend selection via model config
- Multiple backends: `ollama` and `mock`
- Configurable decoding controls such as temperature, top-p, and max token limit
- Prompt template management with prompt family and version identifiers
- Structured response validation
- Retry handling for malformed or invalid outputs
- Timeout handling for model calls
- Per-call JSONL logging of prompts, raw responses, parsed responses, parse failures, latency, and backend token metadata when available

Reasoning traces are defined as both model-visible `reasoning` text and runtime metadata. The policy is documented in [config/specs/llm_runtime_policy.md](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/config/specs/llm_runtime_policy.md).

## Orchestration Layer

Architectures are now config-driven instead of hardcoded. The orchestration layer supports:

- A common architecture execution interface
- Configurable parallel team size
- Configurable hierarchical role prompts
- Structured intermediate outputs for each sub-agent
- Architecture metadata in run outputs
- Failure handling when sub-agents return invalid outputs
- Configurable tie-breaking for parallel voting
- Ablation variants including `parallel_2`, `parallel`, `hierarchical_no_critic`, and `hierarchical_multi_critic`

## Game Environment Interface

The environment layer now uses shared game objects instead of only standalone helper functions. Current environments implement:

- `reset()`
- `get_state()`
- `get_valid_actions()`
- `apply_action()`
- `is_terminal()`
- `get_winner()`
- `get_metrics_context()`

Each environment provides:

- Natural-language state descriptions for prompting
- Machine-readable state snapshots for logs and summaries
- Deterministic seeding support
- Explicit legality validation for actions

Game-engine tests live in [tests/test_game_engine.py](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/tests/test_game_engine.py).

## Blotto

Blotto is now specified more explicitly with configurable variant parameters, stronger baseline bots, and an equilibrium-distance approximation. The current repository policy is documented in [config/specs/blotto_spec.md](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/config/specs/blotto_spec.md).

## Connect 4

Connect 4 remains the default gravity-grid benchmark, with configurable board dimensions and connect length, a stronger heuristic minimax oracle, and a formal oracle-accuracy metric based on matching any optimal move plus recording value gap. The policy is documented in [config/specs/connect4_spec.md](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/config/specs/connect4_spec.md).

## Prompt Families

Prompt-family support is now built into the runtime. The repository supports `minimal_v1`, `structured_reasoning_v1`, `chain_of_thought_v1`, and `legality_first_v1`, with experiment-level selection through `prompt_family` in the experiment config. The policy is documented in [config/specs/prompting_spec.md](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/config/specs/prompting_spec.md).

## Metrics

Run-level aggregate metrics are now computed automatically and written as both JSON and CSV summaries. The schema and the distinction between primary and secondary metrics are documented in [config/specs/metrics_schema.md](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/config/specs/metrics_schema.md).

## Notes

- The current implementation still covers Blotto and Connect 4 only.
- The new structure is intended to support later work on metrics, analysis, and reproducibility without breaking the existing prototype flow.
