# Metrics Schema

## Schema Id

Run-level aggregate metrics are stored as `metrics_v1` in:

- `runs/experiment_runs/run_{id}/summaries/metrics.json`

CSV table exports are also written for downstream analysis:

- `aggregate_tables.csv`
- `architecture_summaries.csv`
- `model_summaries.csv`
- `prompt_summaries.csv`

## Top-Level Structure

`metrics.json` contains:

- `schema_version`
- `primary_metrics`
- `secondary_metrics`
- `architecture_summaries`
- `model_summaries`
- `prompt_summaries`
- `aggregate_tables`

## Primary Metrics

These should be treated as primary for the final writeup:

- `win_rate`
- `hallucination_rate`
- `connect4_optimal_move_accuracy`
- `blotto_nash_distance`
- `consistency`

## Secondary Metrics

These should be treated as secondary or diagnostic:

- `tie_rate`
- `average_value_gap`
- `blunder_rate`
- `invalid_attempt_rate`
- `outcome_stability`
- `per_state_agreement`

## Summary Row Fields

Each row in the aggregate summaries includes:

- `scope_type`
- `scope_id`
- `experiment_group`
- `game`
- `matches`
- `wins`
- `ties`
- `losses`
- `win_rate`
- `tie_rate`
- `hallucination_rate`
- `legality_rate`
- `connect4_optimal_move_accuracy`
- `average_value_gap`
- `blunder_rate`
- `blotto_nash_distance`
- `consistency`

## Consistency Subfields

The `consistency` object currently includes:

- `variance_across_trials`
- `per_state_agreement`
- `outcome_stability`
- `accuracy_variance`
- `nash_distance_variance`
