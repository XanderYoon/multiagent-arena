# Results and Conclusion

## Overview

This project set out to evaluate whether multi-agent LLM orchestration improves strategic decision-making in adversarial games, and whether those gains depend on architecture design, model configuration, prompting, and game setting. The implemented benchmark now supports those comparisons through structured runs, reproducibility metadata, per-turn logging, and aggregate metrics including win rate, hallucination rate, legality, consistency, Connect 4 oracle agreement, and Colonel Blotto Nash-distance.

The strongest empirical evidence in the repository comes from the live Section 14.3 Ollama/Qwen runs stored under [reports/runs/experiment_runs/run_20260410_215833_032b2a0_dirty](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/reports/runs/experiment_runs/run_20260410_215833_032b2a0_dirty) and [reports/runs/experiment_runs/run_20260411_002628_032b2a0_dirty](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/reports/runs/experiment_runs/run_20260411_002628_032b2a0_dirty). These runs directly address the proposal's questions about model scale and quantization within multi-agent systems. By contrast, the stored single-vs-parallel-vs-hierarchical, prompting, and difficulty runs were executed with the `mock-deterministic` backend and are best interpreted as pipeline-validation results rather than substantive evidence about real LLM strategic behavior.

The central result is that orchestration does matter, but not in a universal way. There is no single architecture that dominates across both games and all metrics. Instead, performance depends on the interaction between architecture type, model composition, game, and evaluation objective. Some teams were strongest in head-to-head tournament play, others were best at matching the Connect 4 oracle, and others stayed closest to Blotto equilibrium while sacrificing some direct win rate. That pattern is itself important: it shows the benchmark is measuring distinct aspects of strategic competence rather than collapsing everything into a single score.

## Evidence Base and Experimental Scope

This section draws primarily from:

- [reports/final/tables/section14_3_summary.csv](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/reports/final/tables/section14_3_summary.csv)
- [reports/final/tables/section15_topline_results.csv](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/reports/final/tables/section15_topline_results.csv)
- [reports/final/figures/section14_3_model_scale_blotto_head_to_head_heatmap.svg](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/reports/final/figures/section14_3_model_scale_blotto_head_to_head_heatmap.svg)
- [reports/final/figures/section14_3_model_scale_connect4_head_to_head_heatmap.svg](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/reports/final/figures/section14_3_model_scale_connect4_head_to_head_heatmap.svg)
- [reports/final/figures/section14_3_quantization_blotto_head_to_head_heatmap.svg](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/reports/final/figures/section14_3_quantization_blotto_head_to_head_heatmap.svg)
- [reports/final/figures/section14_3_quantization_connect4_head_to_head_heatmap.svg](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/reports/final/figures/section14_3_quantization_connect4_head_to_head_heatmap.svg)
- [reports/final/figures/section14_3_connect4_oracle_tradeoff_bubble.svg](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/reports/final/figures/section14_3_connect4_oracle_tradeoff_bubble.svg)
- [reports/final/figures/section14_3_blotto_strategy_tradeoff_bubble.svg](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/reports/final/figures/section14_3_blotto_strategy_tradeoff_bubble.svg)
- [reports/final/interesting_trace_notes.md](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/reports/final/interesting_trace_notes.md)
- [CSE_Project_Proposal.pdf](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/CSE_Project_Proposal.pdf)

The live Section 14.3 subset covers two proposal-aligned factors:

- Model-scale compositions using `qwen2.5:3b`, `qwen2.5:7b`, and `qwen2.5:14b`
- Quantization compositions using `qwen2.5:7b-instruct-q4_0`, `qwen2.5:7b-instruct-q8_0`, and `qwen2.5:7b-instruct-fp16`

In both cases, the prompt family was `structured_reasoning_v1`, and the comparison was restricted to mixed parallel and hierarchical teams. That means the strongest current conclusions concern proposal Section 14.3 specifically: how model quality and model composition affect multi-agent systems.

## Results

## 1. Model-Scale Results

The model-scale suite provides the clearest evidence that architecture composition materially changes outcomes. The strongest overall internal competitor was `hierarchical_hhl`, a hierarchy with a low-capacity reasoner and high-capacity critic and executive. It achieved:

- `0.800` win rate in Blotto internal tournament play
- `0.071` Blotto Nash distance in that same internal tournament, the lowest value in the suite
- `0.800` win rate in Connect 4 internal tournament play

Those results matter because they show that a hierarchy can outperform other mixed teams even when the first stage uses the weaker model. In other words, the ordering of model quality across roles matters, not just the average capacity of the team.

At the same time, the best model-scale team was not the same for every task. In Blotto against baseline bots, the top win-rate system was `parallel_lmh` at `0.625`, not the hierarchy that dominated internal play. In Connect 4 oracle evaluation, the best system was `parallel_llh`, which reached `42.855%` optimal-move agreement, outperforming all model-scale hierarchies and even the more high-heavy parallel team `parallel_hhl` at `33.635%`. This is a strong example of why the proposal's metric design was necessary. Tournament strength, strategic equilibrium quality, and oracle agreement are related but not interchangeable.

The detailed model-scale results are:

| Setting | Best architecture | Value |
| --- | --- | ---: |
| Blotto internal tournament win rate | `hierarchical_hhl` | `0.800` |
| Blotto internal tournament Nash distance | `hierarchical_hhl` | `0.071` |
| Blotto vs bots win rate | `parallel_lmh` | `0.625` |
| Connect 4 internal tournament win rate | `hierarchical_hhl` | `0.800` |
| Connect 4 oracle agreement | `parallel_llh` | `42.855%` |
| Lowest Connect 4 oracle blunder rate | `parallel_llh` | `0.5714` |

Two additional patterns stand out.

First, more model quality did not produce monotonic gains. `parallel_llh`, whose mean team quality score was `1.67`, outperformed `parallel_hhl` and all hierarchies on Connect 4 oracle agreement despite using fewer high-capacity components. Second, consistency and win rate were related but not identical. `parallel_hhl` posted the highest Connect 4 internal per-state agreement in the model-scale suite at `0.8611`, while `hierarchical_hhl` won more games at `0.800`. This suggests that stable local decision-making does not always translate directly to the strongest match outcomes.

The model-scale figures make these tradeoffs visible. The head-to-head heatmaps show that `hierarchical_hhl` was broadly dominant in internal tournaments, while the quality-progression chart for Connect 4 oracle evaluation shows that higher average team quality did not cleanly map onto higher oracle agreement. The best point on that curve is the low-heavy parallel team, not the high-heavy alternatives.

## 2. Quantization Results

The quantization suite reinforces the same broad conclusion: composition matters, but the best composition depends on the metric.

In internal tournament play:

- `hierarchical_q4q4f16` was the best Blotto architecture at `0.600` win rate
- `parallel_f16f16q4` was the best Connect 4 architecture at `0.700` win rate

In evaluation against stronger references:

- `hierarchical_qmix` and `parallel_q4q4f16` tied for the best Blotto-vs-bots win rate at `0.750`
- `parallel_q4q4f16` achieved the best Blotto-vs-bots Nash distance at `0.065`
- `hierarchical_f16f16q4` achieved the best Connect 4 oracle agreement at `33.335%`

These results are notable because they show that lower-precision components are not uniformly harmful. In Blotto, the low-heavy `parallel_q4q4f16` configuration was not merely competitive; it was one of the strongest systems in the entire quantization suite, combining the highest baseline-bot win rate with the best equilibrium-proximity score. Meanwhile, the hierarchy `hierarchical_f16f16q4` was strongest on the Connect 4 oracle metric, suggesting that higher-precision critics and executives are especially helpful when the task is local tactical correctness rather than general head-to-head play.

The detailed quantization results are:

| Setting | Best architecture | Value |
| --- | --- | ---: |
| Blotto internal tournament win rate | `hierarchical_q4q4f16` | `0.600` |
| Blotto vs bots win rate | `parallel_q4q4f16` and `hierarchical_qmix` | `0.750` |
| Blotto vs bots Nash distance | `parallel_q4q4f16` | `0.065` |
| Connect 4 internal tournament win rate | `parallel_f16f16q4` | `0.700` |
| Connect 4 oracle agreement | `hierarchical_f16f16q4` | `33.335%` |
| Best Connect 4 oracle blunder rate | `hierarchical_f16f16q4` and `parallel_qmix` were among the strongest tradeoff points | see figure |

This suite also makes the proposal's "mixed-team composition" idea look worthwhile. The strongest systems were not homogeneous all-F16 or all-Q4 teams. Instead, the best results tended to come from mixed allocations of precision across parallel voters or hierarchical roles. That supports the proposal's claim that orchestration is not only about the number of agents, but also about how capabilities are distributed within the team.

## 3. Cross-Game and Cross-Metric Interpretation

A consistent finding across both suites is that no architecture dominates all tasks.

In Blotto:

- Internal tournament success favored certain hierarchies, especially `hierarchical_hhl` in the model-scale suite.
- Baseline-bot performance sometimes favored parallel teams, especially `parallel_lmh` in model scale and `parallel_q4q4f16` in quantization.
- Low Nash distance did not always align with highest win rate. For example, in quantization, `hierarchical_qmix` matched the best Blotto-vs-bots win rate at `0.750`, but its Nash distance was `0.280`, much worse than `parallel_q4q4f16` at `0.065`.

In Connect 4:

- Internal tournaments favored one set of systems, such as `hierarchical_hhl` and `parallel_f16f16q4`.
- Oracle agreement favored different systems, such as `parallel_llh` and `hierarchical_f16f16q4`.
- Blunder rate was often more informative than win rate for understanding oracle performance. For example, `parallel_llh` combined the highest model-scale oracle agreement (`42.855%`) with the lowest blunder rate (`0.5714`) in that suite.

This is one of the benchmark's most important results. The proposal emphasized evaluating LLMs with analytically meaningful games rather than relying on a single outcome metric. The current evidence supports that design choice. If only win rate had been measured, the story would have been incomplete. If only oracle agreement had been measured, internal tournament strength would have been obscured. By including both strategic and robustness-oriented metrics, the benchmark reveals real tradeoffs in how multi-agent systems behave.

## 4. Hallucination, Legality, and Robustness

The proposal also emphasized hallucination and legality as first-class benchmark outcomes, and the repository now captures those signals well.

Most live Section 14.3 configurations achieved perfect legality in several settings, but failures were not uniformly absent. The main non-zero hallucination cases include:

- `hierarchical_llh` with `0.100` hallucination rate in model-scale Blotto internal play
- `hierarchical_f16f16q4` with `0.100` hallucination rate in quantized Blotto internal play
- `parallel_q4q4f16` with `0.1316` hallucination rate in quantized Connect 4 internal play
- `hierarchical_qmix` with `0.1531` hallucination rate in quantized Connect 4 internal play
- `hierarchical_f16f16q4` with `0.050` hallucination rate in quantized Connect 4 oracle evaluation

These are not just minor implementation details. They show that legality failures remain architecture-dependent even in systems that can otherwise perform well strategically. In fact, `hierarchical_qmix` achieved the best quantized Blotto-vs-bots win rate and still exhibited the highest hallucination rate among quantized Connect 4 internal-play systems. That kind of split result is exactly the type of phenomenon the proposal aimed to uncover.

The qualitative trace analysis supports the same conclusion. The notes in [interesting_trace_notes.md](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/reports/final/interesting_trace_notes.md) show:

- hierarchical repair of illegal Blotto allocations and illegal Connect 4 column choices
- cases where intermediate reasoning was flawed but the final decision was corrected
- cases where parallel diversity existed, but the tie-break rule produced a brittle final action anyway
- sub-agent request failures that surfaced as structured robustness events rather than silently disappearing

Taken together, the quantitative and qualitative evidence shows that this benchmark is not merely logging final outcomes. It is measuring procedural reliability, which is essential if the goal is to understand whether multi-agent systems are genuinely more robust or only occasionally more accurate.

## 5. Consistency and Stability

The proposal defined consistency as a core metric, and the live runs show that consistency behaves differently across games and architectures.

For Connect 4 internal play in the model-scale suite:

- `parallel_hhl` achieved the highest per-state agreement at `0.8611`
- `parallel_lmh` followed at `0.7917`
- `hierarchical_hhl`, despite the highest win rate, had lower per-state agreement at `0.6528`

For Connect 4 oracle evaluation:

- `parallel_lmh` reached perfect per-state agreement at `1.000` in the model-scale suite, but its oracle agreement was only `16.67%`
- `parallel_llh` reached lower per-state agreement at `0.750`, yet had the best oracle agreement at `42.855%`

This is a useful negative result. It suggests that consistency alone should not be interpreted as evidence of strategic quality. A system can be extremely stable while being stably wrong. That distinction is important for the proposal's broader research framing, which concerns adversarial strategic reasoning rather than simple output determinism.

Outcome stability tells a similar story. Many oracle-evaluation configurations had `1.000` outcome stability because the outcome structure of those tests is fixed, but tournament settings showed more variation. For example, `hierarchical_hhl` in model-scale Blotto internal play reached `0.800` outcome stability, while several other teams remained in the `0.500` to `0.700` range. This indicates that the strongest tournament systems were not only better on average, but also more reliable across repeated trials.

## 6. What the Current Results Say About the Proposal

Relative to the proposal's intended claims, the present evidence supports several conclusions strongly.

Supported by live evidence:

- Multi-agent composition materially changes performance in adversarial games.
- Mixed-team architecture design matters, including the placement of stronger and weaker models within a hierarchy.
- Model scale and quantization both affect strategic quality, oracle agreement, and robustness.
- Hallucination and legality failures remain measurable and architecture-dependent even when overall play quality is high.
- Different metrics reveal different strengths, so evaluating only win rate or only oracle agreement would miss important behavior.

Only partially supported by current stored evidence:

- The proposal's claim that multi-agent orchestration outperforms a single-agent baseline in live play is not yet fully established in this repository because the stored direct single-vs-parallel-vs-hierarchical comparison is mock-backed.
- Prompt-family effects are implemented but not yet demonstrated with live-model runs.
- Difficulty-robustness experiments are scaffolded but currently backed by mock runs rather than the live Ollama/Qwen setup.
- The proposal's broader scope, including additional games such as Checkers and containerized isolated execution, remains outside the current empirical record.

That distinction matters. The benchmark is already successful as a functioning evaluation framework, and it already provides real results for the Section 14.3 question. But the full proposal-level empirical story is not yet complete.

## Conclusion

The most defensible conclusion from the current benchmark is that multi-agent orchestration changes strategic performance in meaningful and measurable ways, but the gains are conditional rather than universal. In the live Section 14.3 runs, some hierarchies dominated internal tournaments, some parallel teams matched the Connect 4 oracle more often, and some low-heavy or mixed-precision teams achieved the best Blotto equilibrium behavior. This means there is no single "best" orchestration pattern independent of objective. Instead, the architecture must be matched to the target behavior: direct competition, local tactical accuracy, equilibrium-oriented planning, or robustness under repeated play.

This is an important result for the original project proposal. The proposal did not only ask whether multi-agent systems can be better; it asked how orchestration structure, model configuration, and prompting influence strategic reasoning in adversarial settings. The current benchmark already shows that those factors matter and that their effects are nuanced. The head-to-head heatmaps, quality-progression charts, and tradeoff plots make that clear: stronger average models do not always produce the strongest teams, parallel and hierarchical systems fail in different ways, and robustness metrics can diverge sharply from raw win-rate metrics.

At the same time, the results also impose a limit on interpretation. The repository does not yet justify a blanket claim that hierarchical or parallel systems are categorically superior to single-agent systems, because the strongest stored evidence is concentrated in multi-agent-only Section 14.3 subsets. Likewise, prompt-family and difficulty conclusions remain provisional until they are rerun with live backends. The benchmark is therefore best viewed as a successful partial realization of the proposal: it already produces meaningful empirical findings, and it has the infrastructure needed to answer the remaining questions once those additional live runs are completed.

In paper-style terms, the main take-away is:

> Multi-agent LLM orchestration is not a universally dominant strategy, but it is a consequential design variable. Team structure, capability allocation, and evaluation metric all materially shape adversarial-game performance.

That conclusion is well supported by the current live evidence, and it is exactly the kind of nuanced outcome the project proposal was designed to investigate.
