# Multi-Agent LLM Game Benchmark

This repository contains a prototype benchmark for comparing single-agent and multi-agent LLM orchestration on adversarial games.

## Repository Layout

The repository is now organized around code, machine-readable configs, generated run artifacts, and analysis outputs.

```text
.
├── agents.py
├── architectures.py
├── config_loader.py
├── configs/
│   ├── benchmark.json
│   ├── experiments/
│   ├── games/
│   └── models/
├── docs/
├── experiments/
├── analysis/
├── game_engine.py
├── main.py
├── requirements.txt
└── results.txt
```

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

The benchmark expects a local Ollama server and the default model configured in [configs/models/ollama_qwen2_5_7b.json](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/configs/models/ollama_qwen2_5_7b.json):

```bash
ollama pull qwen2.5:7b
ollama serve
```

## Running Locally

Run the default benchmark:

```bash
python3 main.py --config configs/benchmark.json
```

Run with a different benchmark config:

```bash
python3 main.py --config path/to/benchmark.json
```

Current execution-plan configs:

- Pilot architecture run: [configs/experiments/pilot_architecture_comparison.json](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/configs/experiments/pilot_architecture_comparison.json)
- Final architecture run: [configs/experiments/final_architecture_comparison.json](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/configs/experiments/final_architecture_comparison.json)
- Machine-readable run matrix: [configs/experiments/execution_plan.json](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/configs/experiments/execution_plan.json)
- Operator run sheet: [configs/experiments/run_sheet.csv](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/configs/experiments/run_sheet.csv)
- Narrative plan: [docs/experiment_execution_plan.md](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/docs/experiment_execution_plan.md)

Section 14 experiment and reporting tooling:

- Batch experiment matrix: [configs/experiments/section14_run_matrix.json](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/configs/experiments/section14_run_matrix.json)
- Local mock benchmark entrypoint: [configs/benchmark_mock.json](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/configs/benchmark_mock.json)
- Batch runner: `python3 analysis/execute_plan.py --dry-run`
- Analysis bundle generator: `python3 analysis/report_runs.py`

## Config System

The runner now reads machine-readable JSON config files for:

- Global benchmark settings: [configs/benchmark.json](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/configs/benchmark.json)
- Per-game settings: [configs/games/blotto.json](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/configs/games/blotto.json), [configs/games/connect4.json](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/configs/games/connect4.json)
- Per-model settings: [configs/models/ollama_qwen2_5_7b.json](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/configs/models/ollama_qwen2_5_7b.json)
- Prompt settings and template versions: [configs/prompts/default_prompts.json](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/configs/prompts/default_prompts.json)
- Architecture settings and ablations: [configs/architectures/default_architectures.json](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/configs/architectures/default_architectures.json)
- Per-experiment settings: [configs/experiments/default_benchmark.json](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/configs/experiments/default_benchmark.json)

`main.py` resolves these configs, snapshots them into each run directory, and uses them to determine model selection, prompt family/version, output paths, trial counts, seeds, enabled phases, and game parameters currently supported by the prototype.

## Experiment Output Layout

Each run is written to `experiments/run_{timestamp}_{commit}/` with this structure:

```text
experiments/run_YYYYMMDD_HHMMSS_commit/
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

For convenience, the latest run log is also mirrored to the top-level [results.txt](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/results.txt).

The structured logs now supplement `results.txt` with:

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

Reasoning traces are defined as both model-visible `reasoning` text and runtime metadata. The policy is documented in [docs/llm_runtime_policy.md](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/docs/llm_runtime_policy.md).

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

Blotto is now specified more explicitly with configurable variant parameters, stronger baseline bots, and an equilibrium-distance approximation. The current repository policy is documented in [docs/blotto_spec.md](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/docs/blotto_spec.md).

## Connect 4

Connect 4 remains the default gravity-grid benchmark, with configurable board dimensions and connect length, a stronger heuristic minimax oracle, and a formal oracle-accuracy metric based on matching any optimal move plus recording value gap. The policy is documented in [docs/connect4_spec.md](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/docs/connect4_spec.md).

## Prompt Families

Prompt-family support is now built into the runtime. The repository supports `minimal_v1`, `structured_reasoning_v1`, `chain_of_thought_v1`, and `legality_first_v1`, with experiment-level selection through `prompt_family` in the experiment config. The policy is documented in [docs/prompting_spec.md](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/docs/prompting_spec.md).

## Metrics

Run-level aggregate metrics are now computed automatically and written as both JSON and CSV summaries. The schema and the distinction between primary and secondary metrics are documented in [docs/metrics_schema.md](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/docs/metrics_schema.md).

## Notes

- The current implementation still covers Blotto and Connect 4 only.
- The new structure is intended to support later work on metrics, analysis, and reproducibility without breaking the existing prototype flow.
