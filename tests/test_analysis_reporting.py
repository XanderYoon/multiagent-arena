import json
import tempfile
import unittest
from pathlib import Path

from analysis.reporting import collect_runs, write_report_bundle
from reproducibility import build_trial_schedule


class AnalysisReportingTests(unittest.TestCase):
    def test_build_trial_schedule_respects_enabled_games(self):
        architectures = [{"id": "single"}, {"id": "parallel"}, {"id": "hierarchical"}]
        games = {"blotto": {}, "connect4": {}}
        experiment_config = {
            "num_trials": 2,
            "enabled_games": ["blotto"],
            "phases": {
                "internal_ai_tournament": True,
                "blotto_vs_bots": True,
                "connect4_oracle_accuracy": True,
            },
        }
        schedule = build_trial_schedule(architectures, games, experiment_config, 8803, ["uniform", "random"])

        self.assertTrue(all(entry["game"] == "blotto" for entry in schedule["schedule"]))
        self.assertEqual(len(schedule["schedule"]), 18)

    def test_report_bundle_is_generated_from_completed_runs(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            run_dir = tmp_path / "experiments" / "run_test"
            (run_dir / "metadata").mkdir(parents=True)
            (run_dir / "summaries").mkdir(parents=True)
            (run_dir / "logs").mkdir(parents=True)

            (run_dir / "metadata" / "run_manifest.json").write_text(
                json.dumps({"run_id": "run_test", "model": "mock-deterministic"}),
                encoding="utf-8",
            )
            (run_dir / "summaries" / "summary.json").write_text(
                json.dumps(
                    {
                        "run_id": "run_test",
                        "model": "mock-deterministic",
                        "prompt_family": "structured_reasoning",
                        "phases": {},
                    }
                ),
                encoding="utf-8",
            )
            (run_dir / "summaries" / "metrics.json").write_text(
                json.dumps(
                    {
                        "aggregate_tables": [
                            {
                                "scope_type": "architecture",
                                "scope_id": "single",
                                "game": "blotto",
                                "prompt_family_id": "structured_reasoning_v1",
                                "win_rate": 0.5,
                                "legality_rate": 1.0,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (run_dir / "logs" / "turn_records.jsonl").write_text(
                json.dumps(
                    {
                        "game": "blotto",
                        "architecture_id": "single",
                        "move_valid": False,
                        "invalid_reason": "allocation_wrong_sum",
                    }
                ) + "\n",
                encoding="utf-8",
            )

            runs = collect_runs(tmp_path / "experiments")
            self.assertEqual(len(runs), 1)

            output_dir = tmp_path / "analysis"
            write_report_bundle(output_dir, runs)

            self.assertTrue((output_dir / "combined_aggregate_tables.csv").exists())
            self.assertTrue((output_dir / "hallucination_patterns.csv").exists())
            self.assertTrue((output_dir / "claim_map.json").exists())
            self.assertTrue((output_dir / "report.md").exists())
            self.assertTrue((output_dir / "plots" / "architecture_blotto.svg").exists())


if __name__ == "__main__":
    unittest.main()
