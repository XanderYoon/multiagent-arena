import csv
import json
import tempfile
import unittest
from pathlib import Path

from reports.scripts.final_deliverables import build_deliverables, discover_key_section14_3_runs


class FinalDeliverablesTests(unittest.TestCase):
    def _write_run(self, root, run_name, comparison_axis, run_label, model_group_id, rows):
        run_dir = root / run_name
        for relative_dir in ["config", "metadata", "summaries", "logs"]:
            (run_dir / relative_dir).mkdir(parents=True, exist_ok=True)

        (run_dir / "config" / "experiment.json").write_text(
            json.dumps(
                {
                    "run_label": run_label,
                    "comparison_axis": comparison_axis,
                    "model_group_id": model_group_id,
                }
            ),
            encoding="utf-8",
        )
        (run_dir / "config" / "architectures.json").write_text(
            json.dumps(
                {
                    "architectures": [
                        {
                            "id": "parallel_a",
                            "type": "parallel",
                            "display_name": "Parallel A",
                            "model_sequence": ["low", "med", "high"],
                        },
                        {
                            "id": "hierarchical_a",
                            "type": "hierarchical",
                            "display_name": "Hierarchical A",
                            "role_model_aliases": {
                                "reasoner": "low",
                                "critic": ["med"],
                                "executive": "high",
                            },
                        },
                    ]
                }
            ),
            encoding="utf-8",
        )
        for filename in ["benchmark.json", "model.json", "prompt.json", "prompt_catalog.json"]:
            (run_dir / "config" / filename).write_text("{}", encoding="utf-8")

        (run_dir / "metadata" / "run_manifest.json").write_text(
            json.dumps(
                {
                    "run_id": run_name,
                    "backend": "ollama",
                    "prompt_family_id": "structured_reasoning_v1",
                    "config_path": f"/tmp/{run_label}.json",
                }
            ),
            encoding="utf-8",
        )
        (run_dir / "metadata" / "reproducibility.json").write_text("{}", encoding="utf-8")
        (run_dir / "summaries" / "summary.json").write_text(
            json.dumps({"run_id": run_name, "model": model_group_id, "prompt_family": "structured_reasoning_v1"}),
            encoding="utf-8",
        )
        aggregate_rows = []
        for row in rows:
            aggregate_rows.append(
                {
                    "scope_type": "architecture",
                    "scope_id": row["scope_id"],
                    "experiment_group": row["experiment_group"],
                    "game": row["game"],
                    "model": model_group_id,
                    "prompt_family_id": "structured_reasoning_v1",
                    "matches": row.get("matches"),
                    "wins": row.get("wins"),
                    "ties": row.get("ties"),
                    "losses": row.get("losses"),
                    "win_rate": row.get("win_rate"),
                    "tie_rate": row.get("tie_rate"),
                    "hallucination_rate": row.get("hallucination_rate"),
                    "invalid_attempt_rate": row.get("invalid_attempt_rate"),
                    "legality_rate": row.get("legality_rate"),
                    "connect4_optimal_move_accuracy": row.get("connect4_optimal_move_accuracy"),
                    "average_value_gap": row.get("average_value_gap"),
                    "blunder_rate": row.get("blunder_rate"),
                    "blotto_nash_distance": row.get("blotto_nash_distance"),
                    "consistency": {
                        "variance_across_trials": row.get("consistency_variance_across_trials"),
                        "per_state_agreement": row.get("consistency_per_state_agreement"),
                        "outcome_stability": row.get("consistency_outcome_stability"),
                        "accuracy_variance": row.get("consistency_accuracy_variance"),
                        "nash_distance_variance": row.get("consistency_nash_distance_variance"),
                    },
                }
            )
        (run_dir / "summaries" / "metrics.json").write_text(
            json.dumps({"aggregate_tables": aggregate_rows}),
            encoding="utf-8",
        )
        (run_dir / "summaries" / "aggregate_tables.csv").write_text("scope_id\n", encoding="utf-8")
        (run_dir / "summaries" / "model_summaries.csv").write_text("scope_id\n", encoding="utf-8")
        (run_dir / "summaries" / "prompt_summaries.csv").write_text("scope_id\n", encoding="utf-8")
        (run_dir / "summaries" / "game_outcomes.csv").write_text("game\n", encoding="utf-8")
        (run_dir / "logs" / "results.txt").write_text("results", encoding="utf-8")

        with (run_dir / "summaries" / "architecture_summaries.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "scope_id",
                    "game",
                    "experiment_group",
                    "matches",
                    "win_rate",
                    "hallucination_rate",
                    "invalid_attempt_rate",
                    "legality_rate",
                    "tie_rate",
                    "connect4_optimal_move_accuracy",
                    "blotto_nash_distance",
                    "average_value_gap",
                    "blunder_rate",
                    "consistency_per_state_agreement",
                    "consistency_outcome_stability",
                ],
            )
            writer.writeheader()
            writer.writerows(rows)

        return run_dir

    def test_discover_key_runs_keeps_latest_per_suite(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            self._write_run(
                root,
                "run_20260410_100000_old",
                "model_size_and_mixed_team_composition",
                "model_scale_old",
                "group_a",
                [],
            )
            latest_model = self._write_run(
                root,
                "run_20260410_200000_new",
                "model_size_and_mixed_team_composition",
                "model_scale_new",
                "group_b",
                [],
            )
            latest_quant = self._write_run(
                root,
                "run_20260410_210000_quant",
                "quantization_and_mixed_team_composition",
                "quantization_new",
                "group_c",
                [],
            )

            selected = discover_key_section14_3_runs(root)
            self.assertEqual(selected, [latest_model, latest_quant])

    def test_build_deliverables_writes_report_tables_and_figures(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            self._write_run(
                root,
                "run_20260410_200000_model",
                "model_size_and_mixed_team_composition",
                "model_scale_subset",
                "qwen2_5_param_count_subset",
                [
                    {
                        "scope_id": "parallel_a",
                        "game": "blotto",
                        "experiment_group": "blotto_vs_bots",
                        "matches": 8,
                        "win_rate": 0.75,
                        "hallucination_rate": 0.0,
                        "invalid_attempt_rate": 0.0,
                        "legality_rate": 1.0,
                        "tie_rate": 0.0,
                        "connect4_optimal_move_accuracy": "",
                        "blotto_nash_distance": 0.12,
                        "average_value_gap": "",
                        "blunder_rate": "",
                        "consistency_per_state_agreement": 1.0,
                        "consistency_outcome_stability": 0.75,
                    },
                    {
                        "scope_id": "hierarchical_a",
                        "game": "connect4",
                        "experiment_group": "connect4_oracle_accuracy",
                        "matches": 2,
                        "win_rate": 0.0,
                        "hallucination_rate": 0.05,
                        "invalid_attempt_rate": 0.05,
                        "legality_rate": 0.95,
                        "tie_rate": 0.0,
                        "connect4_optimal_move_accuracy": 37.5,
                        "blotto_nash_distance": "",
                        "average_value_gap": 12.0,
                        "blunder_rate": 0.4,
                        "consistency_per_state_agreement": 0.8,
                        "consistency_outcome_stability": 1.0,
                    },
                ],
            )
            self._write_run(
                root,
                "run_20260410_210000_quant",
                "quantization_and_mixed_team_composition",
                "quantization_subset",
                "qwen2_5_7b_quantization_subset",
                [
                    {
                        "scope_id": "parallel_a",
                        "game": "connect4",
                        "experiment_group": "internal_ai_tournament",
                        "matches": 10,
                        "win_rate": 0.6,
                        "hallucination_rate": 0.0,
                        "invalid_attempt_rate": 0.0,
                        "legality_rate": 1.0,
                        "tie_rate": 0.1,
                        "connect4_optimal_move_accuracy": "",
                        "blotto_nash_distance": "",
                        "average_value_gap": "",
                        "blunder_rate": "",
                        "consistency_per_state_agreement": 0.7,
                        "consistency_outcome_stability": 0.8,
                    }
                ],
            )

            output_dir = root / "deliverables"
            result = build_deliverables(root, output_dir)

            self.assertEqual(len(result["selected_runs"]), 2)
            self.assertTrue((output_dir / "FINAL_REPORT.md").exists())
            self.assertTrue((output_dir / "RUN_INSTRUCTIONS.md").exists())
            self.assertTrue((output_dir / "tables" / "topline_results.csv").exists())
            self.assertTrue((output_dir / "tables" / "study_limitations.json").exists())
            self.assertTrue((output_dir / "figures").exists())
            self.assertTrue((output_dir / "key_runs" / "run_20260410_200000_model" / "summaries" / "architecture_summaries.csv").exists())
            self.assertTrue((output_dir / "figures" / "all_experiments_blotto_architecture_win_rate_matplotlib.svg").exists())
            self.assertTrue((output_dir / "figures" / "all_experiments_run_label_primary_metric_top10_matplotlib.svg").exists())
            self.assertTrue((output_dir / "figures" / "all_experiments_same_model_blotto_architecture_win_rate_heatmap_matplotlib.svg").exists())
            self.assertTrue((output_dir / "figures" / "all_experiments_same_model_connect4_architecture_summary_matplotlib.svg").exists())

            report_text = (output_dir / "FINAL_REPORT.md").read_text(encoding="utf-8")
            self.assertIn("Depth-limited oracle limitations", report_text)
            self.assertIn("Prompt sensitivity", report_text)
            self.assertIn("broader non-Section 14.3", report_text)


if __name__ == "__main__":
    unittest.main()
