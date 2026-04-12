# Section 15 Final Deliverables

## Project Objective

This benchmark evaluates whether multi-agent LLM orchestration improves strategic decision-making in adversarial games. The implemented system compares single-turn parallel voting and hierarchical role-based teams on Colonel Blotto and Connect 4, then measures win rate, legality, hallucination rate, consistency, Blotto Nash-distance, and Connect 4 oracle agreement.

## Included Experimental Runs


## Final Results


## Interpretation

The final tables and figures in this bundle are derived directly from the stored run summaries under `reports/runs/experiment_runs/run_*/`. They are intended to support the proposal's Section 14.3 claims about model-scale and quantization effects on multi-agent orchestration.

## Limitations

- Depth-limited oracle limitations: Connect 4 oracle accuracy is measured against the repository's depth-limited minimax solver. That is a strong baseline, but it is not a perfect solver, so optimal-move accuracy should be interpreted as agreement with this oracle rather than proof of globally optimal play.
- Single-model backend limitations: The completed Section 14.3 sweeps stay within the Qwen/Ollama runtime family. This isolates architecture, parameter-count, and quantization effects, but it does not establish that the same trends will transfer to other model families or hosted APIs.
- Prompt sensitivity: The final Section 14.3 deliverables summarize runs executed with `structured_reasoning_v1`. Prompt wording materially affects legality, consistency, and strategy quality, so the reported rankings should be treated as prompt-conditional rather than universally stable.
- Cost and runtime constraints: Mixed-team ensembles increase wall-clock runtime and local hardware demand because each move may require multiple model invocations. The benchmark records accuracy and win-rate tradeoffs, but it does not yet normalize outcomes by latency, GPU memory, or token cost.

## Bundle Contents

- `RUN_INSTRUCTIONS.md`: reproducible commands for rerunning the benchmark and regenerating this bundle.
- `tables/`: final CSV and JSON summary tables for the selected Section 14.3 runs.
- `figures/`: SVG charts for the key experiment groups.
- `key_runs/`: copied configs, metadata, summaries, and human-readable logs for the selected runs.

