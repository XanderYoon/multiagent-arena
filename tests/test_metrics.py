import unittest

from metrics import aggregate_run_metrics, write_metrics_csv


class MetricsAggregationTests(unittest.TestCase):
    def test_aggregates_blotto_and_connect4_metrics(self):
        summary = {
            "run_id": "run_test",
            "model": "mock-deterministic",
            "prompt_family_id": "structured_reasoning_v1",
            "phases": {
                "internal_ai_tournament": [
                    {
                        "game": "blotto",
                        "players": ["Single Agent", "Parallel Team"],
                        "player_architectures": {
                            "Single Agent": {
                                "architecture_id": "single",
                                "architecture_type": "single",
                            },
                            "Parallel Team": {
                                "architecture_id": "parallel",
                                "architecture_type": "parallel",
                            },
                        },
                        "state_snapshot": {"points": [10, 20, 30]},
                        "moves": {
                            "Single Agent": [20, 30, 50],
                            "Parallel Team": [33, 33, 34],
                        },
                        "nash_distance": {
                            "Single Agent": {"normalized_l1_distance": 0.2},
                            "Parallel Team": {"normalized_l1_distance": 0.1},
                        },
                        "winner": "Single Agent",
                        "invalid_players": [],
                    },
                    {
                        "game": "connect4",
                        "players": ["Single Agent", "Parallel Team"],
                        "player_architectures": {
                            "Single Agent": {"id": "single", "type": "single"},
                            "Parallel Team": {"id": "parallel", "type": "parallel"},
                        },
                        "winner": "Single Agent",
                        "invalid_moves": [{"player": "Parallel Team", "attempted_move": 9}],
                        "turns": [
                            {"player": "Single Agent", "state_snapshot": {"board": []}, "applied_move": 0},
                            {"player": "Parallel Team", "state_snapshot": {"board": []}, "applied_move": 1},
                        ],
                    },
                ],
                "blotto_vs_bots": [],
                "connect4_oracle_accuracy": [
                    {
                        "game": "connect4",
                        "agent": "Single Agent",
                        "architecture_metadata": {"id": "single"},
                        "moves": 4,
                        "invalid_attempts": 1,
                        "accuracy_pct": 50.0,
                        "average_value_gap": 2.5,
                        "blunders": 2,
                        "outcome": "oracle_win",
                        "oracle_records": [
                            {
                                "state_snapshot": {"board": [1]},
                                "chosen_move": 0,
                            },
                            {
                                "state_snapshot": {"board": [1]},
                                "chosen_move": 0,
                            },
                        ],
                    }
                ],
            },
        }

        metrics = aggregate_run_metrics(summary)
        self.assertEqual(metrics["schema_version"], "metrics_v1")
        architecture_rows = {row["scope_id"]: row for row in metrics["architecture_summaries"] if row["game"] == "blotto"}
        self.assertAlmostEqual(architecture_rows["single"]["win_rate"], 1.0)
        self.assertAlmostEqual(architecture_rows["single"]["blotto_nash_distance"], 0.2)

        connect4_rows = [
            row for row in metrics["architecture_summaries"]
            if row["scope_id"] == "single" and row["game"] == "connect4" and row["experiment_group"] == "connect4_oracle_accuracy"
        ]
        self.assertEqual(len(connect4_rows), 1)
        self.assertAlmostEqual(connect4_rows[0]["connect4_optimal_move_accuracy"], 50.0)
        self.assertAlmostEqual(connect4_rows[0]["average_value_gap"], 2.5)
        self.assertAlmostEqual(connect4_rows[0]["hallucination_rate"], 0.25)

    def test_metrics_regression_includes_consistency_fields_and_csv_export(self):
        summary = {
            "run_id": "run_regression",
            "model": "mock-deterministic",
            "prompt_family_id": "minimal_v1",
            "phases": {
                "internal_ai_tournament": [
                    {
                        "game": "blotto",
                        "players": ["Single Agent", "Parallel Team"],
                        "player_architectures": {
                            "Single Agent": {
                                "architecture_id": "single",
                                "architecture_type": "single",
                            },
                            "Parallel Team": {
                                "architecture_id": "parallel",
                                "architecture_type": "parallel",
                            },
                        },
                        "state_snapshot": {"points": [10, 20, 30]},
                        "moves": {
                            "Single Agent": [20, 30, 50],
                            "Parallel Team": [33, 33, 34],
                        },
                        "nash_distance": {
                            "Single Agent": {"normalized_l1_distance": 0.2},
                            "Parallel Team": {"normalized_l1_distance": 0.1},
                        },
                        "winner": "TIE",
                        "invalid_players": [],
                    },
                    {
                        "game": "blotto",
                        "players": ["Single Agent", "Parallel Team"],
                        "player_architectures": {
                            "Single Agent": {
                                "architecture_id": "single",
                                "architecture_type": "single",
                            },
                            "Parallel Team": {
                                "architecture_id": "parallel",
                                "architecture_type": "parallel",
                            },
                        },
                        "state_snapshot": {"points": [10, 20, 30]},
                        "moves": {
                            "Single Agent": [20, 30, 50],
                            "Parallel Team": [33, 33, 34],
                        },
                        "nash_distance": {
                            "Single Agent": {"normalized_l1_distance": 0.2},
                            "Parallel Team": {"normalized_l1_distance": 0.1},
                        },
                        "winner": "Single Agent",
                        "invalid_players": [],
                    },
                ],
                "blotto_vs_bots": [],
                "connect4_oracle_accuracy": [],
            },
        }

        metrics = aggregate_run_metrics(summary)
        single_row = next(
            row for row in metrics["architecture_summaries"]
            if row["scope_id"] == "single" and row["game"] == "blotto"
        )
        self.assertAlmostEqual(single_row["win_rate"], 0.5)
        self.assertAlmostEqual(single_row["tie_rate"], 0.5)
        self.assertAlmostEqual(single_row["consistency"]["per_state_agreement"], 1.0)
        self.assertAlmostEqual(single_row["consistency"]["outcome_stability"], 0.5)

        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "metrics.csv"
            write_metrics_csv(csv_path, metrics["architecture_summaries"])
            contents = csv_path.read_text(encoding="utf-8")

        self.assertIn("consistency_outcome_stability", contents)
        self.assertIn("consistency_per_state_agreement", contents)


if __name__ == "__main__":
    unittest.main()
