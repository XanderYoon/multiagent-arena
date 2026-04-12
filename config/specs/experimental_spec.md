# Experimental Specification

## Purpose

This document converts the project proposal into a concrete benchmark specification for this repository. It defines the research questions, experiment dimensions, required outputs, and reproducibility rules that should govern implementation and benchmark execution.

It is written against the current repository state:

- Implemented today: single-agent, parallel-vote, and hierarchical architectures; Colonel Blotto; Connect 4; Ollama-backed local inference; repeated trial execution; plain-text logging.
- Not yet implemented: Checkers, multi-model sweeps, prompt sweeps, structured experiment storage, formal aggregation, and containerized execution.

The goal is to make the benchmark build-out and final evaluation defensible and reproducible rather than ad hoc.

## Benchmark Scope

The benchmark evaluates whether multi-agent LLM orchestration improves strategic decision-making in adversarial games relative to a single-agent baseline, and how those gains vary with model size, prompting style, and game difficulty.

Target game families:

- Colonel Blotto / simultaneous resource allocation
- Connect 4 / gravity-grid game
- Checkers

Target decision architectures:

- Single-agent baseline
- Parallel multi-agent voting
- Hierarchical reasoner -> critic -> executive

Target independent variables:

- Architecture
- Model configuration
- Prompt family
- Game and game difficulty setting

## Research Questions

The benchmark should answer the following questions.

### RQ1: Architecture Effect

Do multi-agent orchestration strategies outperform a single-agent baseline on adversarial games when evaluated by win rate, legality, consistency, and oracle-aligned accuracy?

### RQ2: Model Scale Interaction

Do orchestration gains persist across model sizes, or do they shrink as the underlying model becomes stronger?

### RQ3: Prompting Interaction

How sensitive are architecture outcomes to prompting strategy, especially for legality-heavy environments and games requiring deeper planning?

### RQ4: Difficulty Robustness

Do architecture advantages remain stable as game complexity increases, such as stronger baselines, larger boards, non-standard variants, or more difficult payoff structures?

### RQ5: Failure Mode Characterization

Which architectures most reduce illegal moves, malformed outputs, and strategically poor decisions, and in which games do those reductions matter most?

## Primary Comparison Axes

Each benchmark run must explicitly identify values on the following axes.

### Architecture Comparison

Core comparison set:

- `single`
- `parallel`
- `hierarchical`

Future ablations:

- `parallel-2`
- `parallel-3`
- `hierarchical-no-critic`
- `hierarchical-multi-critic`

### Model-Size Comparison

The benchmark should compare at least three model settings once backend generalization is implemented:

- Small
- Medium
- Large

For Ollama-based experiments, each model setting should record:

- Provider/backend name
- Model name
- Parameter scale or published size
- Quantization tag if applicable

Current prototype default:

- `ollama/qwen2.5:7b`

### Prompting-Strategy Comparison

Prompt families to support:

- `minimal`
- `structured_reasoning`
- `legality_first`
- `deliberative`

Each prompt family must have a version identifier, and game-specific variants must preserve equivalent task information across architectures as much as possible.

### Game-Difficulty Comparison

Difficulty is game-specific.

Blotto difficulty dimensions:

- Battlefield count
- Troop budget
- Payoff vector policy
- Opponent strength

Connect 4 difficulty dimensions:

- Board dimensions
- Connect length
- Oracle depth/strength
- Opponent strength

Checkers difficulty dimensions:

- Board size and rule variant
- Engine strength
- Starting position selection if varied

## Required Results For Final Report

The final report or presentation must include the following outputs.

### Core Tables

- Win rate by architecture and game
- Illegal-move or hallucination rate by architecture and game
- Consistency summary by architecture and game
- Oracle-aligned move accuracy for Connect 4 and Checkers
- Blotto equilibrium-distance metric summary

### Interaction Tables

- Architecture x model summary
- Architecture x prompt summary
- Architecture x difficulty summary

### Visuals

- Architecture comparison plots for each game
- Model-size trend plot
- Prompt-family comparison plot
- Difficulty robustness plot

### Qualitative Analysis

- Representative illegal-move cases
- Representative cases where hierarchical review corrected a flawed initial move
- Representative cases where voting helped or failed

### Reproducibility Appendix

- Exact configs used for all reported runs
- Code version identifiers
- Model identifiers
- Seed policy and seed lists

## Success Criteria For A Complete Benchmark Run

A benchmark run is considered complete only if all of the following hold.

### Per-Run Requirements

- Every trial has a run identifier and trial identifier.
- The full experiment configuration is saved.
- The model, prompt family, architecture, game, and seed are recorded.
- Raw agent outputs and parsed actions are recorded.
- Legality validation results are recorded.
- Final game outcomes and aggregate metrics are recorded.

### Experimental Coverage Requirements

- All three core architectures are evaluated on every enabled game.
- Every comparison group uses matched seeds or matched game instances where appropriate.
- Baseline opponents are included for each game family.
- Oracle or engine comparisons are included for games where optimal-move evaluation is defined.

### Reporting Requirements

- Aggregate metrics are produced in machine-readable form.
- A human-readable summary is produced for quick inspection.
- Missing or failed trials are reported explicitly rather than silently skipped.

### Minimum Acceptance Threshold For Repository Milestone

Before claiming the benchmark is "complete" relative to the proposal, the repository must support:

- Blotto, Connect 4, and Checkers
- Structured output directories
- Multi-model evaluation
- Prompt-family evaluation
- Formal metric aggregation
- Reproducible reruns from saved configs

The current prototype does not yet satisfy this threshold.

## Reproducibility Policy

All experiments must follow the policy below.

### Seed Handling

- Every top-level run has a `global_seed`.
- Each trial derives deterministic child seeds from `global_seed` plus trial index.
- Randomized game generation must use recorded seeds.
- If an external backend is nondeterministic despite fixed decoding settings, that limitation must be logged in the run metadata.

### Version Pinning

At minimum, each run must record:

- Git commit hash or `dirty` working-tree marker
- Python version
- Dependency versions
- Backend name and version if available
- Exact model identifier and digest if available
- Prompt version identifiers

### Config Capture

Every run must save:

- Benchmark config
- Game config
- Model config
- Prompt config
- Architecture config
- Trial schedule metadata

Saved config artifacts must be sufficient to rerun the benchmark without inferring hidden defaults.

## Naming Conventions

The benchmark should use stable, machine-readable names.

### Experiments

Format:

`{game}__{objective}__{comparison}`

Examples:

- `blotto__winrate__architecture`
- `connect4__oracle_accuracy__architecture_model`
- `checkers__legality__prompt`

### Runs

Format:

`run_{YYYYMMDD_HHMMSS}_{short_commit}`

Example:

- `run_20260406_153000_a1b2c3d`

### Models

Format:

`{backend}/{model_name}[/{variant}]`

Examples:

- `ollama/qwen2.5:7b`
- `ollama/qwen3:14b/q4_K_M`

### Prompt Families

Format:

`{family}_v{major}`

Examples:

- `minimal_v1`
- `legality_first_v2`

### Architectures

Canonical architecture identifiers:

- `single`
- `parallel`
- `hierarchical`

### Games

Canonical game identifiers:

- `blotto`
- `connect4`
- `checkers`

### Trials

Format:

`trial_{index:04d}`

Example:

- `trial_0007`

## Initial Execution Plan

The implementation should proceed in phases.

### Phase 1: Prototype Hardening

- Add config files and structured run outputs.
- Add structured logging and metric aggregation.
- Add validation, retry, and timeout handling for model calls.
- Add tests for current games and orchestration logic.

### Phase 2: Proposal Alignment

- Implement Checkers.
- Add prompt-family support.
- Add multi-model support.
- Add difficulty variants.

### Phase 3: Final Benchmark Matrix

- Run architecture comparisons across all games.
- Run model-size sweeps.
- Run prompt-family sweeps.
- Run difficulty robustness experiments.
- Produce final tables, plots, and narrative analysis.

## Decisions Locked In By This Spec

These decisions should be treated as the current default unless deliberately revised:

- The benchmark compares three primary architectures: single, parallel, hierarchical.
- The benchmark targets three games: Blotto, Connect 4, and Checkers.
- Reported primary metrics are win rate, hallucination rate, consistency, oracle-move accuracy, and Blotto equilibrium distance.
- Reproducibility requires saved configs, saved seeds, and recorded code/model versions.
- The repository should evolve from plain-text logging toward structured experiment artifacts and summary outputs.
