import csv
import json
import tempfile
import unittest
from pathlib import Path

from benchmark.experiment_logging import (
    build_game_outcome_records,
    build_trial_metadata_records,
    build_turn_records,
    write_csv,
    write_jsonl,
)


class ExperimentLoggingTests(unittest.TestCase):
    def setUp(self):
        self.summary = {
            "run_id": "run_test",
            "benchmark_name": "benchmark",
            "model": "mock-deterministic",
            "backend": "mock",
            "prompt_family_id": "structured_reasoning_v1",
            "prompt_family": "structured_reasoning",
            "prompt_version": "structured_reasoning_v1",
            "phases": {
                "internal_ai_tournament": [
                    {
                        "trial": 1,
                        "seed": 42,
                        "started_at": "2026-01-01T00:00:00Z",
                        "completed_at": "2026-01-01T00:00:01Z",
                        "duration_ms": 1000,
                        "game": "blotto",
                        "variant_name": "blotto",
                        "game_parameters": {"battlefields": 3, "troop_budget": 100},
                        "players": ["Single Agent", "Parallel Team"],
                        "player_architectures": {
                            "Single Agent": {
                                "architecture_id": "single",
                                "architecture_name": "Single Agent",
                                "architecture_type": "single",
                            },
                            "Parallel Team": {
                                "architecture_id": "parallel",
                                "architecture_name": "Parallel Team",
                                "architecture_type": "parallel",
                            },
                        },
                        "winner": "Single Agent",
                        "invalid_players": [],
                        "scores": {"Single Agent": 30, "Parallel Team": 20},
                        "moves": {"Single Agent": [20, 30, 50], "Parallel Team": [33, 33, 34]},
                        "nash_distance": {
                            "Single Agent": {"normalized_l1_distance": 0.2},
                            "Parallel Team": {"normalized_l1_distance": 0.1},
                        },
                        "metrics_context": {"scores": [30, 20]},
                        "turns": [
                            {
                                "timestamp": "2026-01-01T00:00:01Z",
                                "turn_index": 1,
                                "decision_index": 1,
                                "player": "Single Agent",
                                "player_role": "simultaneous_player",
                                "state_snapshot": {"points": [10, 20, 30]},
                                "valid_actions": {"sum": 100},
                                "architecture_metadata": {
                                    "architecture_id": "single",
                                    "architecture_name": "Single Agent",
                                    "architecture_type": "single",
                                },
                                "intermediate_outputs": [
                                    {
                                        "call_index": 7,
                                        "parsed_response": {"move": [20, 30, 50]},
                                        "attempts": [{"raw_response": "{\"move\": [20, 30, 50]}"}],
                                    }
                                ],
                                "requested_move": [20, 30, 50],
                                "applied_move": [20, 30, 50],
                                "move_valid": True,
                                "invalid_reason": None,
                            }
                        ],
                    }
                ],
                "blotto_vs_bots": [],
                "connect4_oracle_accuracy": [
                    {
                        "trial": 1,
                        "seed": 99,
                        "started_at": "2026-01-01T00:01:00Z",
                        "completed_at": "2026-01-01T00:01:05Z",
                        "duration_ms": 5000,
                        "game": "connect4",
                        "variant_name": "connect4",
                        "game_parameters": {"rows": 6, "columns": 7, "connect_length": 4},
                        "agent": "Single Agent",
                        "architecture_metadata": {
                            "id": "single",
                            "display_name": "Single Agent",
                            "type": "single",
                        },
                        "outcome": "oracle_win",
                        "accuracy_pct": 50.0,
                        "average_value_gap": 2.5,
                        "perfect_moves": 2,
                        "blunders": 1,
                        "moves": 4,
                        "invalid_attempts": 1,
                        "metrics_context": {"turn_count": 4},
                        "turns": [
                            {
                                "timestamp": "2026-01-01T00:01:01Z",
                                "turn_index": 1,
                                "player": "Single Agent",
                                "player_role": "oracle_accuracy_agent",
                                "source": "agent",
                                "state_snapshot": {"board": []},
                                "valid_actions": [0, 1, 2],
                                "architecture_metadata": {
                                    "id": "single",
                                    "display_name": "Single Agent",
                                    "type": "single",
                                },
                                "intermediate_outputs": [
                                    {
                                        "call_index": 8,
                                        "parsed_response": {"move": 0},
                                        "attempts": [{"raw_response": "{\"move\": 0}"}],
                                    }
                                ],
                                "requested_move": 0,
                                "applied_move": 0,
                                "move_valid": True,
                                "invalid_reason": None,
                                "oracle_best_moves": [0, 3],
                                "oracle_best_score": 100,
                            }
                        ],
                    }
                ],
            },
        }

    def test_builds_trial_turn_and_outcome_records(self):
        trial_records = build_trial_metadata_records(self.summary)
        turn_records = build_turn_records(self.summary)
        outcome_records = build_game_outcome_records(self.summary)

        self.assertEqual(len(trial_records), 2)
        self.assertEqual(len(turn_records), 2)
        self.assertEqual(len(outcome_records), 2)

        self.assertEqual(trial_records[0]["architecture_ids"], ["single", "parallel"])
        self.assertEqual(turn_records[0]["call_indices"], [7])
        self.assertEqual(turn_records[1]["oracle_best_moves"], [0, 3])
        self.assertEqual(outcome_records[1]["oracle_accuracy_pct"], 50.0)

    def test_writes_jsonl_and_csv_exports(self):
        trial_records = build_trial_metadata_records(self.summary)
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            jsonl_path = tmp_path / "trial_records.jsonl"
            csv_path = tmp_path / "trial_records.csv"

            write_jsonl(jsonl_path, trial_records)
            write_csv(csv_path, trial_records)

            jsonl_lines = jsonl_path.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(jsonl_lines), 2)
            self.assertEqual(json.loads(jsonl_lines[0])["record_type"], "trial_metadata")

            with csv_path.open("r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["record_type"], "trial_metadata")
            self.assertIn("architecture_ids", rows[0])


if __name__ == "__main__":
    unittest.main()
