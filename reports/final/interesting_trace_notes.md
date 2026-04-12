# Interesting Trace Notes

This note highlights trace moments that are especially useful for the benchmark's core research goal: evaluating whether multi-agent orchestration improves strategic decision-making, legality, robustness, and consistency in adversarial games.

Research framing reference:
- Project objective in [reports/final/FINAL_REPORT.md](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/reports/final/FINAL_REPORT.md:3)

## 1. Parallel diversity helps, but the tie-break rule is doing real work

Why this matters:
- The proposal is not only about whether "more agents" help, but whether orchestration structure changes outcomes.
- These traces show that parallel teams are not simply averaging identical reasoning. The voting rule can decide the match.

Evidence:
- In a Blotto match, both parallel teams produced three distinct allocations and then resolved them with `tie_break_lowest_move`.
- The selected allocations were not obvious consensus answers; the aggregation rule effectively chose the final strategy.
- Outcome: the `(Low+Med+High)` team won 85 to 40 after tie-breaking selected `[49, 26, 25]`, while `(High+High+Low)` landed on `[25, 11, 64]`.

References:
- [runs/experiment_runs/run_20260410_214419_032b2a0_dirty/logs/results.txt](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/runs/experiment_runs/run_20260410_214419_032b2a0_dirty/logs/results.txt:7)
- [runs/experiment_runs/run_20260410_214419_032b2a0_dirty/logs/results.txt](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/runs/experiment_runs/run_20260410_214419_032b2a0_dirty/logs/results.txt:13)
- [runs/experiment_runs/run_20260410_214419_032b2a0_dirty/logs/results.txt](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/runs/experiment_runs/run_20260410_214419_032b2a0_dirty/logs/results.txt:21)
- [runs/experiment_runs/run_20260410_214419_032b2a0_dirty/logs/results.txt](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/runs/experiment_runs/run_20260410_214419_032b2a0_dirty/logs/results.txt:24)

## 2. Parallel voting can smooth disagreement, but it can also force a brittle choice

Why this matters:
- This is a good example for the "does parallel voting improve robustness or just smooth randomness?" question.
- The team had substantial disagreement in Connect 4 and the tie-break selected the numerically lowest move, not the most strategically justified one.

Evidence:
- The `(Low+Med+High)` parallel team voted `[0, 3, 4]` in Connect 4.
- Two rationales favored central or blocking-oriented play, but the orchestrator still selected column `0` because the votes tied and the configured rule was `tie_break_lowest_move`.
- Immediate outcome: the team executed column `0`, after which the opposing team immediately answered with unanimous column `3`.

References:
- [runs/experiment_runs/run_20260410_214419_032b2a0_dirty/logs/results.txt](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/runs/experiment_runs/run_20260410_214419_032b2a0_dirty/logs/results.txt:77)
- [runs/experiment_runs/run_20260410_214419_032b2a0_dirty/logs/results.txt](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/runs/experiment_runs/run_20260410_214419_032b2a0_dirty/logs/results.txt:81)
- [runs/experiment_runs/run_20260410_214419_032b2a0_dirty/logs/results.txt](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/runs/experiment_runs/run_20260410_214419_032b2a0_dirty/logs/results.txt:84)
- [runs/experiment_runs/run_20260410_214419_032b2a0_dirty/logs/results.txt](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/runs/experiment_runs/run_20260410_214419_032b2a0_dirty/logs/results.txt:88)

## 3. Hierarchical critique can repair illegal outputs and convert a bad draft into a win

Why this matters:
- This is one of the clearest positive cases for hierarchical orchestration.
- It directly supports the proposal's interest in legality handling and whether role structure improves decision quality.

Evidence:
- The hierarchical `(Low->Med->High)` Blotto team produced a reasoner output with `blotto_wrong_sum`.
- The critic explicitly diagnosed that the proposed allocation summed to `70`, not `100`.
- The executive repaired the move to `[42, 35, 23]`, restoring legality.
- Outcome: the repaired hierarchical move beat the parallel opponent 60 to 11.

References:
- [runs/experiment_runs/run_20260410_215833_032b2a0_dirty/logs/results.txt](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/runs/experiment_runs/run_20260410_215833_032b2a0_dirty/logs/results.txt:424)
- [runs/experiment_runs/run_20260410_215833_032b2a0_dirty/logs/results.txt](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/runs/experiment_runs/run_20260410_215833_032b2a0_dirty/logs/results.txt:425)
- [runs/experiment_runs/run_20260410_215833_032b2a0_dirty/logs/results.txt](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/runs/experiment_runs/run_20260410_215833_032b2a0_dirty/logs/results.txt:427)
- [runs/experiment_runs/run_20260410_215833_032b2a0_dirty/logs/results.txt](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/runs/experiment_runs/run_20260410_215833_032b2a0_dirty/logs/results.txt:429)

## 4. Hierarchical critique also catches illegal Connect 4 moves before they are played

Why this matters:
- This is the Connect 4 analogue of the previous case and is useful for discussing hallucination control.
- It shows the hierarchy doing legality checking at move time rather than only in aggregate metrics.

Evidence:
- The `(Low->High->High)` reasoner proposed column `3`.
- The critic identified that column `3` was already full and suggested column `2`.
- The executive adopted the legal correction and the agent executed column `2`.

References:
- [runs/experiment_runs/run_20260410_215833_032b2a0_dirty/logs/results.txt](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/runs/experiment_runs/run_20260410_215833_032b2a0_dirty/logs/results.txt:698)
- [runs/experiment_runs/run_20260410_215833_032b2a0_dirty/logs/results.txt](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/runs/experiment_runs/run_20260410_215833_032b2a0_dirty/logs/results.txt:700)
- [runs/experiment_runs/run_20260410_215833_032b2a0_dirty/logs/results.txt](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/runs/experiment_runs/run_20260410_215833_032b2a0_dirty/logs/results.txt:703)

## 5. Hierarchical roles can improve a move while still using flawed internal rationale

Why this matters:
- This is a strong cautionary example: the hierarchy won, but part of the critique is internally contradictory.
- It is useful for the proposal's concern with reasoning traces as analysis artifacts rather than as direct evidence of valid strategic understanding.

Evidence:
- In Blotto, the critic says `[52, 17, 31]` is illegal even though it sums to `100`.
- The executive repeats the "sum issue" framing, then adopts `[50, 17, 33]`.
- Outcome: the hierarchical team still wins decisively, 89 to 17.

Interpretation:
- This is a case where the orchestration pipeline reaches a strong final action even though the intermediate rationale is partially confabulated.
- It would be a good example for a writeup section on "trace usefulness vs. trace faithfulness."

References:
- [runs/experiment_runs/run_20260410_215833_032b2a0_dirty/logs/results.txt](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/runs/experiment_runs/run_20260410_215833_032b2a0_dirty/logs/results.txt:631)
- [runs/experiment_runs/run_20260410_215833_032b2a0_dirty/logs/results.txt](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/runs/experiment_runs/run_20260410_215833_032b2a0_dirty/logs/results.txt:633)
- [runs/experiment_runs/run_20260410_215833_032b2a0_dirty/logs/results.txt](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/runs/experiment_runs/run_20260410_215833_032b2a0_dirty/logs/results.txt:637)

## 6. Hierarchical critique sometimes overrules a strong opening heuristic with a weaker one

Why this matters:
- This is the opposite of the legality-repair story above.
- It shows that the critic/executive layer can also degrade strategic quality by second-guessing a standard heuristic.

Evidence:
- In oracle evaluation, the reasoner twice recommends the standard center-opening move in Connect 4.
- The critic and executive overrule that and prefer edge play (`0` or `0/6`) on the empty board.
- In the same trial, the oracle wins; trial stats were `Moves: 8 | Perfect: 2 | Blunders: 6 | Accuracy: 25.0%`.

Why it is especially useful:
- This gives a concrete trace-level example for discussing why hierarchical systems can have worse oracle agreement on some states even when they look "more deliberative."
- The quantization summary still shows this architecture as the best quantized oracle-agreement system overall, which makes the example more interesting, not less: even the best aggregate variant can contain locally poor deliberation patterns.

References:
- Opening disagreement: [runs/experiment_runs/run_20260411_002628_032b2a0_dirty/logs/results.txt](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/runs/experiment_runs/run_20260411_002628_032b2a0_dirty/logs/results.txt:8944)
- Second opening-style override: [runs/experiment_runs/run_20260411_002628_032b2a0_dirty/logs/results.txt](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/runs/experiment_runs/run_20260411_002628_032b2a0_dirty/logs/results.txt:8950)
- Trial outcome: [runs/experiment_runs/run_20260411_002628_032b2a0_dirty/logs/results.txt](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/runs/experiment_runs/run_20260411_002628_032b2a0_dirty/logs/results.txt:8991)
- Aggregate oracle metric for this architecture: [reports/final/tables/section14_3_summary.csv](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/reports/final/tables/section14_3_summary.csv:48)

## 7. Full sub-agent failure is a benchmark-relevant robustness event, not just an infrastructure footnote

Why this matters:
- The proposal is about evaluating orchestration systems under realistic execution conditions.
- A whole hierarchical chain can fail if all three sub-agents fail, and the trace makes that visible in a way aggregate metrics alone do not.

Evidence:
- In one model-scale run, reasoner, critic, and executive all return `Validation failure: request_error`.
- The architecture falls back to `no_valid_subagent`.
- Outcome: the oracle wins, and the trial posts `Moves: 13 | Perfect: 7 | Blunders: 6 | Accuracy: 53.8%`.

Interpretation:
- This is a good trace to cite when discussing robustness and the difference between model reasoning failure and orchestration/runtime failure.
- It may deserve separate treatment from ordinary hallucination or bad strategy because the failure mode is end-to-end request collapse.

References:
- [runs/experiment_runs/run_20260410_215707_032b2a0_dirty/logs/results.txt](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/runs/experiment_runs/run_20260410_215707_032b2a0_dirty/logs/results.txt:10559)
- [runs/experiment_runs/run_20260410_215707_032b2a0_dirty/logs/results.txt](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/runs/experiment_runs/run_20260410_215707_032b2a0_dirty/logs/results.txt:10563)
- [runs/experiment_runs/run_20260410_215707_032b2a0_dirty/logs/results.txt](/NAS/School/CSE8803/ASI-Agent-Architecture-Benchmark/runs/experiment_runs/run_20260410_215707_032b2a0_dirty/logs/results.txt:10579)

## Summary themes worth using in the writeup

- Parallel teams are not merely "more of the same"; their behavior is materially shaped by the aggregation rule.
- Hierarchical teams clearly help with legality repair, especially when the reasoner proposes invalid moves.
- Hierarchical traces are not automatically more trustworthy; some critiques are strategically useful but logically inconsistent.
- Trace-level failures reveal robustness issues that would be easy to miss if analysis only used win rate or oracle accuracy.
