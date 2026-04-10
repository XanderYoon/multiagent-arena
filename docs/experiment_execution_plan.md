# Experiment Execution Plan

## Purpose

This document turns the proposal and experimental spec into a concrete execution plan for benchmark runs in this repository.

It defines:

- The exact experiment matrix currently intended for execution
- The minimum trial counts for pilot and final runs
- Which runs are pilots versus final architecture-comparison runs
- The run sheet identifiers that map directly to config files

This plan is intentionally scoped to the repository's current implemented surface:

- Games: Blotto and Connect 4
- Architectures: `single`, `parallel`, `hierarchical`
- Model: one currently configured backend/model at a time
- Prompt family: one selected prompt family per run config

## Experiment Matrix

The current required matrix is:

- Architecture comparison on Blotto
- Architecture comparison on Connect 4
- Baseline-opponent validation on Blotto
- Oracle-accuracy validation on Connect 4

The current default prompt family for execution is:

- `structured_reasoning_v1`

The current required architecture set is:

- `single`
- `parallel`
- `hierarchical`

## Minimum Trial Counts

Use the following minimums unless a later report-specific override is added.

- Pilot runs: `3` trials per configuration
- Final architecture runs: `10` trials per configuration

These counts are meant to balance runtime cost with enough repetition to inspect legality, consistency, and obvious failure modes before larger sweeps.

## Pilot Runs

Pilot runs are intended to validate:

- Logging correctness
- Metric correctness
- Seed scheduling and reproducibility
- Obvious prompt or parsing failures

Required pilot configs:

- [pilot_architecture_comparison.json](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/configs/experiments/pilot_architecture_comparison.json)

Pilot acceptance checks:

- Structured logs are written for every run
- Metrics files are non-empty and parseable
- No silent trial drops occur
- Invalid-output handling behaves as expected

## Final Architecture Runs

Final architecture-comparison runs are the repository's current "main" execution target.

Required final configs:

- [final_architecture_comparison.json](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/configs/experiments/final_architecture_comparison.json)

These runs are expected to support:

- Internal architecture tournaments on both games
- Blotto baseline-opponent evaluation
- Connect 4 oracle-accuracy evaluation
- Matched seeds through the deterministic trial schedule

## Run Sheet

The canonical run sheet for the current repository state is:

- [execution_plan.json](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/configs/experiments/execution_plan.json)
- [run_sheet.csv](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/configs/experiments/run_sheet.csv)

The JSON file is the machine-readable source of truth. The CSV file is the quick-reference operator sheet.

## Current Scope Boundaries

This section 13 implementation does not yet define:

- Multi-model sweeps
- Prompt-family sweeps
- Difficulty sweeps beyond the current default game configs
- Checkers execution

Those should be added as new matrix entries instead of changing the meaning of the existing run IDs.
