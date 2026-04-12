# Final Report

## Executive Summary

This repository now contains a working benchmark prototype for adversarial-game evaluation, but the stored evidence is mixed. The strongest empirical results come from the live Ollama/Qwen Section 14.3 subset runs, while the direct single-vs-parallel-vs-hierarchical comparisons, prompt-family comparisons, and difficulty runs currently stored in the repo were executed on the `mock-deterministic` backend and should be treated as pipeline-validation results rather than substantive model-behavior evidence.

Using the live Section 14.3 runs, the main conclusion is that orchestration structure matters, but there is no single best architecture across all games and metrics. In the model-scale subset, the best internal-play system was `hierarchical_hhl`, which reached 80% win rate in both Blotto and Connect 4 and achieved the lowest Blotto Nash distance in that suite at `0.071` ([run manifest](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/reports/runs/experiment_runs/run_20260410_215833_032b2a0_dirty/metadata/run_manifest.json), [architecture summaries](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/reports/runs/experiment_runs/run_20260410_215833_032b2a0_dirty/summaries/architecture_summaries.csv)). In the quantization subset, the best Connect 4 internal-play system was `parallel_f16f16q4` at 70% win rate, while the best Connect 4 oracle-agreement system was `hierarchical_f16f16q4` at `33.335%` optimal-move accuracy ([run manifest](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/reports/runs/experiment_runs/run_20260411_002628_032b2a0_dirty/metadata/run_manifest.json), [architecture summaries](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/reports/runs/experiment_runs/run_20260411_002628_032b2a0_dirty/summaries/architecture_summaries.csv)).

The benchmark also captures meaningful robustness behavior. Most live Section 14.3 architectures had zero hallucination rate, but several mixed teams did not: `hierarchical_llh` posted a 10% hallucination rate in model-scale Blotto internal play, `parallel_q4q4f16` reached `13.16%` invalid-move rate in quantized Connect 4 internal play, and `hierarchical_qmix` reached `15.31%` in the same setting. The stored trace notes show both failure and repair dynamics: hierarchical teams sometimes corrected illegal Blotto allocations and full-column Connect 4 moves, but parallel tie-breaking sometimes selected brittle actions despite diverse sub-agent reasoning ([interesting traces](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/reports/final/interesting_trace_notes.md)).

## Evidence Base

This report draws from the following repository artifacts:

- Project proposal: [CSE_Project_Proposal.pdf](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/CSE_Project_Proposal.pdf)
- Main mock-backed architecture comparison: [run_20260410_173224_8bf1db5_dirty summary](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/reports/runs/experiment_runs/run_20260410_173224_8bf1db5_dirty/summaries/summary.json)
- Prompt-family mock runs:
  [minimal](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/reports/runs/experiment_runs/run_20260410_173015_8bf1db5_dirty/summaries/summary.json),
  [chain-of-thought](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/reports/runs/experiment_runs/run_20260410_173043_8bf1db5_dirty/summaries/summary.json),
  [legality-first](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/reports/runs/experiment_runs/run_20260410_173111_8bf1db5_dirty/summaries/summary.json)
- Difficulty mock runs:
  [harder Blotto](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/reports/runs/experiment_runs/run_20260410_173140_8bf1db5_dirty/summaries/summary.json),
  [wider Connect 4](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/reports/runs/experiment_runs/run_20260410_173141_8bf1db5_dirty/summaries/summary.json)
- Live Section 14.3 model-scale subset:
  [run manifest](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/reports/runs/experiment_runs/run_20260410_215833_032b2a0_dirty/metadata/run_manifest.json),
  [summary](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/reports/runs/experiment_runs/run_20260410_215833_032b2a0_dirty/summaries/summary.json),
  [architecture summaries](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/reports/runs/experiment_runs/run_20260410_215833_032b2a0_dirty/summaries/architecture_summaries.csv)
- Live Section 14.3 quantization subset:
  [run manifest](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/reports/runs/experiment_runs/run_20260411_002628_032b2a0_dirty/metadata/run_manifest.json),
  [summary](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/reports/runs/experiment_runs/run_20260411_002628_032b2a0_dirty/summaries/summary.json),
  [architecture summaries](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/reports/runs/experiment_runs/run_20260411_002628_032b2a0_dirty/summaries/architecture_summaries.csv)
- Consolidated Section 14.3 rollup: [reports/latest/section14_3_summary.json](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/reports/latest/section14_3_summary.json)

## Proposal Research Questions

The proposal frames four main empirical themes. Restated as concrete research questions:

1. Does multi-agent orchestration improve strategic performance relative to a single-agent baseline?
2. Do architecture choice, model scale, and quantization change outcomes in adversarial games?
3. Do prompting strategy and game difficulty materially affect legality, consistency, and strategic quality?
4. Do the benchmark logs reveal meaningful hallucination and reasoning-trace patterns rather than just final win/loss outcomes?

## RQ1: Does Multi-Agent Orchestration Beat the Single-Agent Baseline?

The repository does not yet contain a live Ollama/Qwen run that directly compares `single`, `parallel`, and `hierarchical` on the same schedule. The only stored direct architecture comparison is the mock-backed run `run_20260410_173224_8bf1db5_dirty`, so this question is only partially answered.

Within that mock run:

| Setting | Single | Parallel | Hierarchical |
| --- | ---: | ---: | ---: |
| Connect 4 internal AI tournament win rate | 100.0% | 50.0% | 0.0% |
| Blotto vs bots win rate | 27.5% | 52.5% | 35.0% |
| Connect 4 oracle accuracy | 20.0% | 20.0% | 20.0% |
| Blotto Nash distance vs bots | 0.13925 | 0.15575 | 0.15625 |

Those numbers are useful for validating the logging and scoring pipeline, but they are not strong evidence about real LLM orchestration because the backend is `mock-deterministic` ([summary](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/reports/runs/experiment_runs/run_20260410_173224_8bf1db5_dirty/summaries/summary.json), [manifest](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/reports/runs/experiment_runs/run_20260410_173224_8bf1db5_dirty/metadata/run_manifest.json)).

Conclusion for RQ1: the benchmark infrastructure supports this comparison, but the current stored evidence does not yet justify a strong claim that multi-agent orchestration beats a single-agent LLM baseline in live runs.

## RQ2: Do Architecture, Model Scale, and Quantization Matter?

Yes. This is the strongest result in the repository, and it is supported by live Ollama/Qwen runs.

### Model-scale subset

Backend and models:
- Backend: `ollama`
- Prompt family: `structured_reasoning_v1`
- Model aliases: `low=qwen2.5:3b`, `med=qwen2.5:7b`, `high=qwen2.5:14b`
- Run: [run_20260410_215833_032b2a0_dirty](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/reports/runs/experiment_runs/run_20260410_215833_032b2a0_dirty)

Key findings:

| Metric | Best architecture | Value |
| --- | --- | ---: |
| Blotto internal AI tournament win rate | `hierarchical_hhl` | 80.0% |
| Connect 4 internal AI tournament win rate | `hierarchical_hhl` | 80.0% |
| Lowest Blotto Nash distance in internal play | `hierarchical_hhl` | 0.071 |
| Best Blotto vs bots win rate | `parallel_lmh` | 62.5% |
| Best Connect 4 oracle accuracy | `parallel_llh` | 42.855% |

Interpretation:
- Architecture composition changed outcomes substantially. The high-heavy hierarchy `hierarchical_hhl` was the strongest all-around internal competitor.
- More scale did not monotonically improve every metric. The low-heavy parallel team `parallel_llh` achieved the best oracle agreement, outperforming the stronger-looking hierarchies on that metric.
- Consistency also varied by composition. `parallel_hhl` reached `0.8611` per-state agreement in Connect 4 internal play, higher than `hierarchical_hhl` at `0.6528`, even though `hierarchical_hhl` won more often.

### Quantization subset

Backend and models:
- Backend: `ollama`
- Prompt family: `structured_reasoning_v1`
- Model aliases: `q4=qwen2.5:7b-instruct-q4_0`, `q8=qwen2.5:7b-instruct-q8_0`, `f16=qwen2.5:7b-instruct-fp16`
- Run: [run_20260411_002628_032b2a0_dirty](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/reports/runs/experiment_runs/run_20260411_002628_032b2a0_dirty)

Key findings:

| Metric | Best architecture | Value |
| --- | --- | ---: |
| Blotto internal AI tournament win rate | `hierarchical_q4q4f16` | 60.0% |
| Connect 4 internal AI tournament win rate | `parallel_f16f16q4` | 70.0% |
| Best Blotto vs bots win rate | `parallel_q4q4f16` and `hierarchical_qmix` | 75.0% |
| Lowest Blotto Nash distance vs bots | `parallel_q4q4f16` | 0.065 |
| Best Connect 4 oracle accuracy | `hierarchical_f16f16q4` | 33.335% |

Interpretation:
- Quantization choice materially changed results. The `parallel_f16f16q4` team was the strongest quantized Connect 4 internal competitor, but `hierarchical_f16f16q4` was better on oracle agreement.
- Low-precision components were not uniformly harmful. `parallel_q4q4f16` produced the best Blotto-vs-bots win rate and the best Blotto Nash distance in this suite.
- Again, there was no universal winner across all metrics. The best strategy depended on whether the objective was head-to-head win rate, oracle agreement, or equilibrium proximity.

Conclusion for RQ2: supported. The stored live runs show that architecture composition, model scale, and quantization all change benchmark outcomes in measurable ways.

## RQ3: Do Prompting Strategy and Difficulty Matter?

The repository contains dedicated prompt-family and difficulty runs, but they are all mock-backed. As a result, they validate the experiment plumbing but do not provide credible evidence about real LLM behavior.

### Prompt-family runs

Prompt families tested:
- `minimal_v1`
- `chain_of_thought_v1`
- `legality_first_v1`
- `structured_reasoning_v1`

Observed result:
- The stored prompt runs are numerically identical across all metrics because they were executed with `mock-deterministic` ([minimal manifest](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/reports/runs/experiment_runs/run_20260410_173015_8bf1db5_dirty/metadata/run_manifest.json)).

Conclusion:
- The prompt-management system is implemented.
- The current stored prompt results do not answer the proposal's prompt-sensitivity question empirically.

### Difficulty runs

The harder Blotto mock run still shows that the benchmark can detect changed difficulty conditions:

| Blotto vs bots win rate | Baseline mock run | Harder Blotto mock run |
| --- | ---: | ---: |
| Single | 27.5% | 32.5% |
| Parallel | 52.5% | 20.0% |
| Hierarchical | 35.0% | 27.5% |

The equilibrium-proximity metric also worsened under the harder Blotto configuration:

| Internal Blotto Nash distance | Baseline mock run | Harder Blotto mock run |
| --- | ---: | ---: |
| Single | 0.1415 | 0.1847 |
| Parallel | 0.1280 | 0.1553 |
| Hierarchical | 0.1295 | 0.1673 |

This suggests the benchmark is sensitive to difficulty shifts, but because these are mock runs, the result is still infrastructural rather than behavioral.

Conclusion for RQ3: partially answered. The machinery for prompt and difficulty studies exists and logs the right metrics, but the stored artifacts do not yet provide live-model evidence.

## RQ4: What Do the Logs Reveal About Hallucinations, Legality, and Reasoning Traces?

This question is answered well.

Quantitatively:
- Most live Section 14.3 architectures had zero hallucination rate.
- Non-zero failure cases were concentrated in a few mixed teams.
- Model-scale failures:
  `hierarchical_llh` had a 10.0% hallucination rate in Blotto internal play.
- Quantization failures:
  `parallel_q4q4f16` had `13.16%` hallucination rate in Connect 4 internal play.
  `hierarchical_qmix` had `15.31%` hallucination rate in Connect 4 internal play.
  `hierarchical_f16f16q4` had `5.0%` hallucination rate in Connect 4 oracle evaluation.

Qualitatively, the trace notes show several benchmark-relevant patterns:

1. Parallel voting creates real diversity, but the tie-break rule can dominate the final action.
2. Hierarchical critique can repair illegal actions, including wrong-sum Blotto allocations and full-column Connect 4 moves.
3. A hierarchy can produce a good final move while containing flawed intermediate rationale.
4. Full sub-agent request failure appears in traces as a distinct robustness event, not just a bad game move.

Those patterns are documented in [reports/final/interesting_trace_notes.md](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/reports/final/interesting_trace_notes.md) and support the proposal's emphasis on reasoning-trace logging as a first-class analysis artifact.

Conclusion for RQ4: supported. The logs capture meaningful behavior beyond final scores, including legality repair, brittle aggregation, and runtime failure modes.

## Overall Answers to the Proposal

What the repository now supports confidently:
- A reusable benchmark scaffold for adversarial games with structured configs, run manifests, reproducibility metadata, structured logs, CSV summaries, and trace capture.
- Empirical evidence that multi-agent composition matters in live Qwen/Ollama runs.
- Evidence that model size and quantization affect both win rate and oracle agreement.
- Evidence that hallucination behavior is measurable and architecture-dependent.

What remains unresolved:
- A live apples-to-apples comparison of `single`, `parallel`, and `hierarchical` on the same non-mock backend.
- A live prompt-family comparison.
- A live difficulty comparison.
- The proposal's broader planned scope, including Checkers and containerized isolated execution.

## Bottom Line

The benchmark has moved well beyond proposal stage and already produces useful results, but the strongest completed empirical story is narrower than the full proposal. The live evidence shows that mixed multi-agent orchestration is not a simple win-more trick: different team structures excel on different games and metrics, and legality/robustness tradeoffs remain central. The most defensible headline today is:

> Multi-agent composition materially changes adversarial-game performance, but the best orchestration depends on the game, the metric, and the model configuration.

That claim is well supported by the live Section 14.3 runs. Stronger claims about single-agent superiority, prompt effects, or difficulty robustness still require additional non-mock experiments.
