# AGENTS.md — Multi-Agent LLM Game Benchmarking

## Project Status

This repository is no longer just a proposal scaffold. It contains a working prototype benchmark for evaluating single-agent and multi-agent LLM orchestration in adversarial games.

The current implementation covers:

- A local LLM interface using Ollama and `qwen2.5:7b`
- Three agent architectures:
  - Single-agent baseline
  - Parallel multi-agent voting
  - Hierarchical reasoner -> critic -> executive flow
- Two game environments:
  - Simplified Colonel Blotto / simultaneous resource allocation
  - Connect 4 / "gravity-grid" game
- A depth-limited minimax oracle for Connect 4
- Repeated-trial experiment execution
- Logging of game outcomes and reasoning traces to `runs/latest/results.txt`

The current implementation does not yet cover the full desired scope. Model sweeps, structured experiment storage, formal summary metrics, and containerized orchestration are still missing.

## Implemented Files

### `agents.py`

Implemented:

- Sends prompts to a local Ollama server at `http://localhost:11434/api/generate`
- Uses `qwen2.5:7b` as the configured model
- Extracts JSON responses from model output with a regex-based parser

Current role:

- This is the only LLM integration layer in the repo.
- It assumes Ollama is already running locally and the configured model is already available.

### `architectures.py`

Implemented:

- `run_single_agent`
  - One LLM call, one final move
- `run_parallel_agent`
  - Three independent LLM calls
  - Aggregates outputs by majority vote
- `run_hierarchical_agent`
  - Reasoner proposes a move
  - Critic reviews legality and strategy
  - Executive auditor makes the final decision

Current role:

- This file implements the proposal's three core orchestration strategies in a simple functional form.
- The prompt contract is JSON-only and task-specific.

### `game_engine.py`

Implemented:

- Simplified Colonel Blotto mechanics
  - Random point generation for 3 zones
  - Fixed troop budget of 100
  - Score evaluation
  - Random baseline allocation generator
- Connect 4 engine
  - Board creation
  - Move legality via valid-column checks
  - Piece dropping
  - Win detection
  - Text board rendering
- Minimax oracle
  - Alpha-beta pruning
  - Depth-limited search

Current role:

- This is the environment layer for the currently supported games.
- Connect 4 is implemented on the standard 7x6 board, not a non-standard board size.
- The minimax baseline is strong but not a guaranteed perfect solver because it is depth-limited.

### `main.py`

Implemented:

- Logging helper that writes to `runs/latest/results.txt`
- Reasoning trace formatting
- Blotto head-to-head matches between architectures
- Connect 4 head-to-head matches between architectures
- Blotto matches against baseline bots
  - Uniform bot
  - Random bot
- Connect 4 accuracy test against the minimax oracle
- Repeated trials across all experiments

Current experiment phases:

1. Internal AI vs AI tournament
2. AI vs standard bots for Blotto
3. AI vs minimax oracle for Connect 4

Current metrics/output behavior:

- Logs winners and raw outcomes
- Penalizes invalid Blotto outputs by zeroing the move
- Detects invalid Connect 4 moves and replaces them with a random valid move
- Logs reasoning traces for analysis
- Tracks Connect 4 oracle-match accuracy and blunders during the oracle test

### `runs/latest/results.txt`

Observed:

- The file contains prior experimental runs
- It shows that the prototype has already been executed successfully at least once
- It captures reasoning traces, move choices, winners, and oracle accuracy summaries

## What Has Been Done Relative to the Proposal

Completed or partially completed:

- Built a benchmark prototype for adversarial game evaluation
- Implemented the three target decision architectures
- Implemented two of the proposed game families
- Added a central orchestrator script for repeated experiments
- Added reasoning trace logging
- Added baseline bot comparisons for Blotto
- Added an oracle-style comparison for Connect 4
- Added basic hallucination handling for illegal/invalid moves

Partially aligned but simplified:

- The games are described abstractly in prompts, but Connect 4 still uses the standard 7x6 board
- The architecture comparison exists, but there is only one model configuration
- Accuracy evaluation exists for Connect 4, but not for all games
- Consistency can be inferred from repeated trials, but there is no formal reporting or variance analysis layer
- Hallucinations are logged and penalized, but not summarized into a dedicated metric report

Not yet implemented:

- Non-standard board sizes for Connect 4
- Nash distance for Blotto
- Formal experiment config system
- Structured output folders such as `runs/experiment_runs/run_{id}/...`
- Batch analysis and result aggregation
- Visualization and plots
- Multiple model comparisons
- Prompting strategy sweeps
- Containerized isolated agent execution

## Current Runtime Assumptions

- Python is used as the execution environment
- The `requests` package must be available
- Ollama must be running locally
- The model `qwen2.5:7b` must be installed in Ollama
- Running `python3 main.py` clears and rewrites `runs/latest/results.txt`

## Recommended Interpretation

This repository should currently be treated as:

- A working proof-of-concept benchmark
- A prototype for comparing orchestration styles
- A partial implementation of the project proposal

It should not yet be treated as:

- A complete evaluation framework
- A finalized experimental pipeline
- A full realization of the proposal's scope

## Next Major Gaps

If development continues toward the original proposal, the highest-value missing work is:

- Add formal metric aggregation and summary reporting
- Add experiment configuration and structured output directories
- Support multiple model and prompt settings
- Add Blotto Nash-distance evaluation
- Add non-standard board-size experiments

## Comprehensive Implementation Checklist

This checklist is intended to track all work required to deliver the project described in `docs/proposal/CSE_Project_Proposal.pdf`. It includes both engineering work to build the benchmark testbed and research workflow steps to run and analyze experiments.

### 1. Project Framing and Experimental Spec

- [x] Convert the proposal into a concrete experimental specification document
- [x] Define the exact research questions to answer
- [x] Define the primary comparison axes
  - [x] Architecture comparison
  - [x] Model-size comparison
  - [x] Prompting-strategy comparison
  - [x] Game-difficulty comparison
- [x] Define which results are required for the final report or presentation
- [x] Define success criteria for a "complete" benchmark run
- [x] Define a reproducibility policy
  - [x] Seed handling
  - [x] Version pinning
  - [x] Config capture
- [x] Define naming conventions for experiments, runs, models, prompts, and architectures

### 2. Repository and Testbed Structure

- [x] Introduce a clear project layout for benchmark code, configs, logs, and analysis
- [x] Add a machine-readable config system
  - [x] Global benchmark config
  - [x] Per-game config
  - [x] Per-model config
  - [x] Per-experiment config
- [x] Add a consistent experiment output layout such as `runs/experiment_runs/run_{id}/`
- [x] Add environment setup documentation
- [x] Add run instructions for local execution
- [x] Add dependency declaration and installation steps
- [x] Add pinned runtime requirements for Python and libraries
- [x] Add a `.gitignore` policy for generated experiment outputs

### 3. LLM Runtime and Agent Interface

- [x] Generalize the agent wrapper beyond the current hardcoded Ollama model
- [x] Support multiple model backends or multiple Ollama model variants
- [x] Add configurable decoding options
  - [x] Temperature
  - [x] Top-p
  - [x] Max tokens
- [x] Add prompt template management
- [x] Add prompt-version identifiers to all experiment outputs
- [x] Add structured agent response validation
- [x] Add retry handling for malformed model outputs
- [x] Add timeout handling for model calls
- [x] Add per-call logging
  - [x] Prompt
  - [x] Raw response
  - [x] Parsed response
  - [x] Parse failure reason
- [x] Add token usage and latency tracking if the backend supports it
- [x] Decide whether "reasoning traces" means model-visible text, metadata, or both

### 4. Multi-Agent Orchestration Layer

- [x] Refactor the architecture implementations into a cleaner orchestration interface
- [x] Define a common interface for all architectures
- [x] Support configurable team size for parallel systems
- [x] Support configurable role prompts for hierarchical systems
- [x] Log all intermediate agent outputs in structured form
- [x] Add architecture-level metadata to outputs
  - [x] Architecture name
  - [x] Agent count
  - [x] Role definitions
  - [x] Aggregation rule
- [x] Add failure handling when one or more sub-agents return invalid outputs
- [x] Add optional tie-breaking rules for parallel voting
- [x] Add optional ablations
  - [x] Two-agent parallel
  - [x] Three-agent parallel
  - [x] Hierarchical without critic
  - [x] Hierarchical with multiple critics

### 5. Game Engine: Common Requirements

- [x] Define a common game environment interface
  - [x] `reset()`
  - [x] `get_state()`
  - [x] `get_valid_actions()`
  - [x] `apply_action()`
  - [x] `is_terminal()`
  - [x] `get_winner()`
  - [x] `get_metrics_context()`
- [x] Ensure each game can produce a natural-language state description
- [x] Ensure each game can produce a structured machine-readable state snapshot
- [x] Add deterministic seeding support to all games
- [x] Add explicit legality validation for all actions
- [x] Add game-level tests for move legality and termination logic
- [x] Add serialization support for game states in logs

### 6. Colonel Blotto Implementation

- [x] Confirm the exact Blotto variant to evaluate
  - [x] Number of battlefields
  - [x] Troop budget
  - [x] Discrete vs continuous
  - [x] Point generation policy
- [x] Decide whether the current 3-zone setup is sufficient or must be generalized
- [x] Support configurable battlefield counts
- [x] Support configurable troop budgets
- [x] Support fixed and randomized payoff vectors
- [x] Validate allocations robustly
  - [x] Integer enforcement
  - [x] Length enforcement
  - [x] Sum enforcement
  - [x] Non-negative values
- [x] Add baseline Blotto opponents
  - [x] Uniform allocation
  - [x] Random allocation
  - [x] Heuristic high-value targeting bot
  - [x] Nash-inspired or equilibrium approximation bot
- [x] Implement Nash distance or a principled approximation if exact computation is infeasible
- [x] Define how Blotto consistency will be measured across repeated trials
- [x] Add tests for scoring and allocation validation

### 7. Connect 4 Implementation

- [x] Decide whether to keep the current standard 7x6 board or add the proposal's non-standard variants
- [x] Support configurable board dimensions if non-standard variants are required
- [x] Support configurable connect length if needed
- [x] Confirm prompt wording for abstract "gravity-grid" representation
- [x] Validate that state descriptions correctly match board orientation and valid columns
- [x] Strengthen the baseline solver
  - [x] Confirm whether depth-limited minimax is sufficient
  - [x] Increase depth or add heuristics if needed
  - [x] Decide whether a stronger external solver is necessary
- [x] Define the exact "optimal move accuracy" metric
  - [x] Match top-1 oracle move
  - [x] Match any oracle-equivalent move
  - [x] Score by value gap
- [x] Add test coverage for win detection, move legality, and solver correctness

### 8. Prompting Strategy Support

- [x] Define the prompt families to compare
  - [x] Minimal zero-shot
  - [x] Structured reasoning
  - [x] Chain-of-thought style
  - [x] Rule-heavy legality-first prompts
- [x] Version-control all prompt templates
- [x] Add game-specific prompt templates
- [x] Add architecture-specific prompt templates
- [x] Add prompt metadata to experiment outputs
- [x] Decide whether internal reasoning text should be stored in full or summarized

### 9. Evaluation Metrics and Analytics

- [x] Define a formal schema for all metrics
- [x] Implement win-rate calculation
- [x] Implement per-game legality or hallucination-rate calculation
- [x] Implement Connect 4 optimal-move accuracy
- [x] Implement Blotto Nash-distance metric
- [x] Implement consistency metrics
  - [x] Variance across trials
  - [x] Per-state agreement
  - [x] Outcome stability
- [x] Implement architecture-level summaries
- [x] Implement per-model summaries
- [x] Implement per-prompt summaries
- [x] Add aggregate tables across all experiment groups
- [x] Define which metrics are primary for the final writeup and which are secondary

### 10. Logging, Persistence, and Outputs

- [x] Replace or supplement `runs/latest/results.txt` with structured experiment logging
- [x] Log run configuration for every experiment
- [x] Log per-trial metadata
  - [x] Seed
  - [x] Timestamp
  - [x] Model
  - [x] Prompt version
  - [x] Architecture
  - [x] Game parameters
- [x] Log per-turn information
  - [x] State
  - [x] Valid actions
  - [x] Raw model output
  - [x] Parsed action
  - [x] Whether the action was valid
- [x] Log per-game outcomes
- [x] Log aggregate metrics per run
- [x] Save outputs in JSON, CSV, or parquet for downstream analysis
- [x] Preserve human-readable summaries for quick inspection

### 11. Reproducibility and Benchmark Controls

- [x] Add global seeding control
- [x] Add per-run seed capture
- [x] Make randomized game generation reproducible
- [x] Make trial scheduling reproducible
- [x] Record exact model name and model digest if available
- [x] Record code version or git commit for each run
- [x] Record hardware/runtime environment details where relevant

### 12. Validation and Testing

- [x] Add unit tests for all game engines
- [x] Add tests for agent output parsing
- [x] Add tests for invalid-output handling
- [x] Add tests for architecture aggregation logic
- [x] Add smoke tests for a full benchmark run
- [x] Add regression tests for key metrics calculations
- [x] Add sanity checks that bots and oracles behave as expected

### 13. Experiment Execution Plan

- [x] Define the exact experiment matrix before running large batches
- [x] Decide the minimum number of trials per configuration
- [x] Decide which runs are pilot runs and which are final runs
- [x] Create a run sheet that maps all intended experiments

#### 14.1 Pilot Experiments

- [x] Run a small architecture-comparison pilot on Blotto
- [x] Run a small architecture-comparison pilot on Connect 4
- [x] Verify that logs, metrics, and outputs are correct
- [x] Inspect failure cases manually

#### 14.2 Main Architecture Comparison

- [x] Run Single-Agent vs Parallel vs Hierarchical on Blotto
- [x] Run Single-Agent vs Parallel vs Hierarchical on Connect 4
- [x] Use matched seeds and matched game instances where appropriate
- [x] Compute win rate, legality rate, and consistency for each architecture

#### 14.3 Model Scaling Experiments

- [x] Select the exact model variants to compare
- [x] Run the architecture comparison at multiple model sizes
- [x] Hold prompts and game settings constant
- [x] Determine whether orchestration gains persist across model scale

#### 14.4 Prompting Experiments

- [x] Run fixed-architecture comparisons across multiple prompt strategies
- [x] Hold model and game settings constant
- [x] Compare whether prompting changes legality, consistency, and strategic quality

#### 14.5 Difficulty and Robustness Experiments

- [x] Run Blotto with multiple payoff structures or battlefield settings
- [x] Run Connect 4 with multiple board settings if non-standard boards are implemented
- [x] Measure whether architecture advantages persist as complexity increases

#### 14.6 Adversary and Baseline Experiments

- [x] Run Blotto against random and uniform baselines
- [x] Add stronger Blotto baselines and compare against them
- [x] Run Connect 4 against the oracle or strongest available solver
- [x] Quantify how often each architecture beats weak baselines and how badly it loses to strong baselines

### 14. Analysis and Reporting

- [x] Produce summary tables for all experiment groups
- [x] Produce plots comparing architectures
- [x] Produce plots comparing model size vs orchestration
- [x] Produce plots comparing prompting strategies
- [x] Analyze hallucination or illegal-move patterns
- [x] Analyze where hierarchical agents help and where they fail
- [x] Analyze whether parallel voting improves robustness or just smooths randomness
- [x] Write a concise narrative of the major findings
- [x] Map each reported claim back to a concrete metric and run set

### 15. Final Deliverables

- [x] Clean benchmark codebase
- [x] Reproducible run instructions
- [x] Stored configs and outputs for key experiments
- [x] Final result tables and figures
- [x] Proposal-aligned writeup or presentation
- [x] Discussion of limitations
  - [x] Depth-limited oracle limitations
  - [x] Single-model backend limitations
  - [x] Prompt sensitivity
  - [x] Cost and runtime constraints
