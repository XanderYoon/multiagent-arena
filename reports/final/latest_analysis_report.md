# Analysis Report

- Runs analyzed: 17
- Non-Section 14.3 runs emphasized in tables and plots: 13
- Section 14.3 runs intentionally omitted from most figures: 4
- Models observed: mock-deterministic, qwen2_5_7b_quantization_subset, qwen2_5_param_count_subset
- Prompt families observed: chain_of_thought_v1, legality_first_v1, minimal_v1, structured_reasoning_v1

## Summary Tables

- `combined_aggregate_tables.csv` contains all aggregate rows across runs.
- `non_section14_3_aggregate_tables.csv` isolates the broader experiment set and excludes the dense Section 14.3 suites.
- `hallucination_patterns.csv` contains invalid-move pattern counts by game and architecture.
- `invalid_reason_summary.csv` counts invalid-output reasons by run, game, and architecture.
- `architecture_overview.csv`, `run_label_overview.csv`, and `prompt_family_overview.csv` summarize the non-14.3 experiments at different aggregation levels.

## Narrative Findings

- hierarchical achieved mean win rate 0.151 on blotto. Supported by runs: run_20260410_170138_8bf1db5_dirty, run_20260410_172912_8bf1db5_dirty, run_20260410_172920_8bf1db5_dirty, run_20260410_172948_8bf1db5_dirty, run_20260410_173015_8bf1db5_dirty, run_20260410_173043_8bf1db5_dirty, run_20260410_173111_8bf1db5_dirty, run_20260410_173140_8bf1db5_dirty, run_20260410_173224_8bf1db5_dirty, run_20260411_213908_032b2a0_dirty, run_20260411_214117_032b2a0_dirty, run_20260411_214609_032b2a0_dirty.
- hierarchical achieved mean legality rate 1.0 on blotto. Supported by runs: run_20260410_170138_8bf1db5_dirty, run_20260410_172912_8bf1db5_dirty, run_20260410_172920_8bf1db5_dirty, run_20260410_172948_8bf1db5_dirty, run_20260410_173015_8bf1db5_dirty, run_20260410_173043_8bf1db5_dirty, run_20260410_173111_8bf1db5_dirty, run_20260410_173140_8bf1db5_dirty, run_20260410_173224_8bf1db5_dirty, run_20260411_213908_032b2a0_dirty, run_20260411_214117_032b2a0_dirty, run_20260411_214609_032b2a0_dirty.
- parallel achieved mean win rate 0.2194 on blotto. Supported by runs: run_20260410_170138_8bf1db5_dirty, run_20260410_172912_8bf1db5_dirty, run_20260410_172920_8bf1db5_dirty, run_20260410_172948_8bf1db5_dirty, run_20260410_173015_8bf1db5_dirty, run_20260410_173043_8bf1db5_dirty, run_20260410_173111_8bf1db5_dirty, run_20260410_173140_8bf1db5_dirty, run_20260410_173224_8bf1db5_dirty, run_20260411_213908_032b2a0_dirty, run_20260411_214117_032b2a0_dirty, run_20260411_214609_032b2a0_dirty.
- parallel achieved mean legality rate 1.0 on blotto. Supported by runs: run_20260410_170138_8bf1db5_dirty, run_20260410_172912_8bf1db5_dirty, run_20260410_172920_8bf1db5_dirty, run_20260410_172948_8bf1db5_dirty, run_20260410_173015_8bf1db5_dirty, run_20260410_173043_8bf1db5_dirty, run_20260410_173111_8bf1db5_dirty, run_20260410_173140_8bf1db5_dirty, run_20260410_173224_8bf1db5_dirty, run_20260411_213908_032b2a0_dirty, run_20260411_214117_032b2a0_dirty, run_20260411_214609_032b2a0_dirty.
- single achieved mean win rate 0.1205 on blotto. Supported by runs: run_20260410_170138_8bf1db5_dirty, run_20260410_172912_8bf1db5_dirty, run_20260410_172920_8bf1db5_dirty, run_20260410_172948_8bf1db5_dirty, run_20260410_173015_8bf1db5_dirty, run_20260410_173043_8bf1db5_dirty, run_20260410_173111_8bf1db5_dirty, run_20260410_173140_8bf1db5_dirty, run_20260410_173224_8bf1db5_dirty, run_20260411_213908_032b2a0_dirty, run_20260411_214117_032b2a0_dirty, run_20260411_214609_032b2a0_dirty.
- single achieved mean legality rate 1.0 on blotto. Supported by runs: run_20260410_170138_8bf1db5_dirty, run_20260410_172912_8bf1db5_dirty, run_20260410_172920_8bf1db5_dirty, run_20260410_172948_8bf1db5_dirty, run_20260410_173015_8bf1db5_dirty, run_20260410_173043_8bf1db5_dirty, run_20260410_173111_8bf1db5_dirty, run_20260410_173140_8bf1db5_dirty, run_20260410_173224_8bf1db5_dirty, run_20260411_213908_032b2a0_dirty, run_20260411_214117_032b2a0_dirty, run_20260411_214609_032b2a0_dirty.
- hierarchical achieved mean win rate 0.0 on connect4. Supported by runs: run_20260410_170138_8bf1db5_dirty, run_20260410_172912_8bf1db5_dirty, run_20260410_172920_8bf1db5_dirty, run_20260410_172948_8bf1db5_dirty, run_20260410_173015_8bf1db5_dirty, run_20260410_173043_8bf1db5_dirty, run_20260410_173111_8bf1db5_dirty, run_20260410_173141_8bf1db5_dirty, run_20260410_173224_8bf1db5_dirty, run_20260411_213908_032b2a0_dirty, run_20260411_214117_032b2a0_dirty, run_20260411_214609_032b2a0_dirty.
- hierarchical achieved mean legality rate 1.0 on connect4. Supported by runs: run_20260410_170138_8bf1db5_dirty, run_20260410_172912_8bf1db5_dirty, run_20260410_172920_8bf1db5_dirty, run_20260410_172948_8bf1db5_dirty, run_20260410_173015_8bf1db5_dirty, run_20260410_173043_8bf1db5_dirty, run_20260410_173111_8bf1db5_dirty, run_20260410_173141_8bf1db5_dirty, run_20260410_173224_8bf1db5_dirty, run_20260411_213908_032b2a0_dirty, run_20260411_214117_032b2a0_dirty, run_20260411_214609_032b2a0_dirty.
- parallel achieved mean win rate 0.25 on connect4. Supported by runs: run_20260410_170138_8bf1db5_dirty, run_20260410_172912_8bf1db5_dirty, run_20260410_172920_8bf1db5_dirty, run_20260410_172948_8bf1db5_dirty, run_20260410_173015_8bf1db5_dirty, run_20260410_173043_8bf1db5_dirty, run_20260410_173111_8bf1db5_dirty, run_20260410_173141_8bf1db5_dirty, run_20260410_173224_8bf1db5_dirty, run_20260411_213908_032b2a0_dirty, run_20260411_214117_032b2a0_dirty, run_20260411_214609_032b2a0_dirty.
- parallel achieved mean legality rate 1.0 on connect4. Supported by runs: run_20260410_170138_8bf1db5_dirty, run_20260410_172912_8bf1db5_dirty, run_20260410_172920_8bf1db5_dirty, run_20260410_172948_8bf1db5_dirty, run_20260410_173015_8bf1db5_dirty, run_20260410_173043_8bf1db5_dirty, run_20260410_173111_8bf1db5_dirty, run_20260410_173141_8bf1db5_dirty, run_20260410_173224_8bf1db5_dirty, run_20260411_213908_032b2a0_dirty, run_20260411_214117_032b2a0_dirty, run_20260411_214609_032b2a0_dirty.

## Architecture Comparisons

- On blotto, `parallel` mean win rate was 0.2194 versus `single` at 0.1205.
- On blotto, `hierarchical` mean win rate was 0.151 versus `single` at 0.1205.
- On connect4, `parallel` mean win rate was 0.25 versus `single` at 0.5.
- On connect4, `hierarchical` mean win rate was 0.0 versus `single` at 0.5.

## Experiment Groups

- `baseline_architecture_benchmark` / `blotto` / `blotto_vs_bots` has mean primary metric `0.278` with legality `1.000`.
- `baseline_architecture_benchmark` / `blotto` / `internal_ai_tournament` has mean primary metric `0.000` with legality `1.000`.
- `baseline_architecture_benchmark` / `connect4` / `connect4_oracle_accuracy` has mean primary metric `20.000` with legality `1.000`.
- `baseline_architecture_benchmark` / `connect4` / `internal_ai_tournament` has mean primary metric `0.500` with legality `1.000`.
- `difficulty_blotto_harder` / `blotto` / `blotto_vs_bots` has mean primary metric `0.267` with legality `1.000`.
- `difficulty_blotto_harder` / `blotto` / `internal_ai_tournament` has mean primary metric `0.000` with legality `1.000`.
- `difficulty_connect4_wide` / `connect4` / `connect4_oracle_accuracy` has mean primary metric `20.000` with legality `1.000`.
- `difficulty_connect4_wide` / `connect4` / `internal_ai_tournament` has mean primary metric `0.500` with legality `1.000`.

## Prompt Coverage

- Prompt family `chain_of_thought_v1` on `blotto` / `blotto_vs_bots` shows mean win rate `0.383` and legality `1.000`.
- Prompt family `chain_of_thought_v1` on `blotto` / `internal_ai_tournament` shows mean win rate `0.000` and legality `1.000`.
- Prompt family `chain_of_thought_v1` on `connect4` / `connect4_oracle_accuracy` shows mean win rate `0.000` and legality `1.000`.
- Prompt family `chain_of_thought_v1` on `connect4` / `internal_ai_tournament` shows mean win rate `0.500` and legality `1.000`.
- Prompt family `legality_first_v1` on `blotto` / `blotto_vs_bots` shows mean win rate `0.383` and legality `1.000`.
- Prompt family `legality_first_v1` on `blotto` / `internal_ai_tournament` shows mean win rate `0.000` and legality `1.000`.

## Coverage Notes

- Model scaling plots outside Section 14.3 are not supported by the current runs.
- Prompt comparison plots are supported by the non-14.3 runs.
- Hallucination patterns were computed from turn logs.
- Invalid reason summaries were not available from turn logs.
