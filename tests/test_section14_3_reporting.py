import csv
import json
import tempfile
import unittest
from pathlib import Path

from reports.scripts.report_section14_3 import (
    build_leaderboard,
    build_section14_3_rows,
    discover_section14_3_runs,
)


class Section143ReportingTests(unittest.TestCase):
    def test_section14_3_configs_include_requested_ensemble_mixes(self):
        repo_root = Path(__file__).resolve().parent.parent

        model_scale_architectures = json.loads(
            (repo_root / "config/architectures/model_scale_architectures.json").read_text(encoding="utf-8")
        )
        quantization_architectures = json.loads(
            (repo_root / "config/architectures/quantization_architectures.json").read_text(encoding="utf-8")
        )
        model_scale_experiment = json.loads(
            (repo_root / "config/experiments/model_scale_flight.json").read_text(encoding="utf-8")
        )
        quantization_experiment = json.loads(
            (repo_root / "config/experiments/quantization_flight.json").read_text(encoding="utf-8")
        )

        model_scale_ids = {spec["id"] for spec in model_scale_architectures["architectures"]}
        quantization_ids = {spec["id"] for spec in quantization_architectures["architectures"]}

        self.assertTrue({"parallel_lmh", "parallel_hhl", "parallel_mmh", "parallel_llh"}.issubset(model_scale_ids))
        self.assertTrue({"hierarchical_lmh", "hierarchical_hhl", "hierarchical_mmh", "hierarchical_llh"}.issubset(model_scale_ids))
        self.assertTrue({"parallel_qmix", "parallel_f16f16q4", "parallel_q8q8f16", "parallel_q4q4f16"}.issubset(quantization_ids))
        self.assertTrue({"hierarchical_qmix", "hierarchical_f16f16q4", "hierarchical_q8q8f16", "hierarchical_q4q4f16"}.issubset(quantization_ids))

        self.assertNotIn("single_med", model_scale_experiment["architectures"])
        self.assertNotIn("single_q8", quantization_experiment["architectures"])
        self.assertEqual(len(model_scale_experiment["architectures"]), 8)
        self.assertEqual(len(quantization_experiment["architectures"]), 8)

    def test_report_builder_discovers_and_summarizes_section14_3_runs(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            run_dir = root / "run_20260410_000000_abc123"
            (run_dir / "metadata").mkdir(parents=True)
            (run_dir / "config").mkdir(parents=True)
            (run_dir / "summaries").mkdir(parents=True)

            (run_dir / "metadata" / "run_manifest.json").write_text(
                json.dumps(
                    {
                        "run_id": run_dir.name,
                        "prompt_family_id": "structured_reasoning_v1",
                    }
                ),
                encoding="utf-8",
            )
            (run_dir / "config" / "experiment.json").write_text(
                json.dumps(
                    {
                        "run_label": "model_scale_flight",
                        "model_group_id": "qwen3_param_count_flight",
                        "comparison_axis": "model_size_and_mixed_team_composition",
                    }
                ),
                encoding="utf-8",
            )
            (run_dir / "config" / "architectures.json").write_text(
                json.dumps(
                    {
                        "architectures": [
                            {
                                "id": "parallel_lmh",
                                "type": "parallel",
                                "display_name": "Parallel Team (Low+Med+High)",
                                "model_sequence": ["low", "med", "high"],
                            },
                            {
                                "id": "hierarchical_lmh",
                                "type": "hierarchical",
                                "display_name": "Hierarchical Team (Low->Med->High)",
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
                        "connect4_optimal_move_accuracy",
                        "blotto_nash_distance",
                        "average_value_gap",
                        "blunder_rate",
                        "consistency_per_state_agreement",
                        "consistency_outcome_stability",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "scope_id": "parallel_lmh",
                        "game": "blotto",
                        "experiment_group": "blotto_vs_bots",
                        "matches": 6,
                        "win_rate": 0.75,
                        "hallucination_rate": 0.0,
                        "connect4_optimal_move_accuracy": "",
                        "blotto_nash_distance": 0.12,
                        "average_value_gap": "",
                        "blunder_rate": "",
                        "consistency_per_state_agreement": 1.0,
                        "consistency_outcome_stability": 0.75,
                    }
                )
                writer.writerow(
                    {
                        "scope_id": "hierarchical_lmh",
                        "game": "connect4",
                        "experiment_group": "connect4_oracle_accuracy",
                        "matches": 3,
                        "win_rate": 0.0,
                        "hallucination_rate": 0.1,
                        "connect4_optimal_move_accuracy": 62.5,
                        "blotto_nash_distance": "",
                        "average_value_gap": 1.25,
                        "blunder_rate": 0.3,
                        "consistency_per_state_agreement": 0.9,
                        "consistency_outcome_stability": 0.6,
                    }
                )

            run_dirs = discover_section14_3_runs(root)
            self.assertEqual(run_dirs, [run_dir])

            rows = build_section14_3_rows(run_dirs)
            self.assertEqual(len(rows), 2)

            parallel_row = next(row for row in rows if row["architecture_id"] == "parallel_lmh")
            self.assertEqual(parallel_row["suite"], "model_scale")
            self.assertEqual(parallel_row["composition_label"], "low+med+high")
            self.assertEqual(parallel_row["composition_signature"], "high:1,low:1,med:1")

            leaderboard = build_leaderboard(rows)
            connect4_leader = next(
                row for row in leaderboard
                if row["game"] == "connect4" and row["experiment_group"] == "connect4_oracle_accuracy"
            )
            self.assertEqual(connect4_leader["primary_metric"], "connect4_optimal_move_accuracy")
            self.assertEqual(connect4_leader["best_architecture_id"], "hierarchical_lmh")


if __name__ == "__main__":
    unittest.main()
