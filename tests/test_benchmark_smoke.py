import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import main as benchmark_main


class BenchmarkSmokeTests(unittest.TestCase):
    def test_full_benchmark_run_writes_expected_artifacts(self):
        repo_root = Path(benchmark_main.PROJECT_ROOT)
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            output_root = tmp_path / "experiments"
            latest_results = tmp_path / "latest_results.txt"

            benchmark_config = tmp_path / "benchmark.json"
            experiment_config = tmp_path / "experiment.json"
            model_config = tmp_path / "model.json"

            benchmark_config.write_text(
                json.dumps(
                    {
                        "benchmark_name": "smoke_benchmark",
                        "output_root": str(output_root),
                        "latest_results_path": str(latest_results),
                        "model_config": str(model_config),
                        "prompt_config": str(repo_root / "config/prompts/default_prompts.json"),
                        "architecture_config": str(repo_root / "config/architectures/default_architectures.json"),
                        "game_configs": {
                            "blotto": str(repo_root / "config/games/blotto.json"),
                            "connect4": str(repo_root / "config/games/connect4.json"),
                        },
                        "experiment_config": str(experiment_config),
                    }
                ),
                encoding="utf-8",
            )
            experiment_config.write_text(
                json.dumps(
                    {
                        "run_label": "smoke",
                        "num_trials": 1,
                        "global_seed": 8803,
                        "prompt_family": "structured_reasoning_v1",
                        "architectures": ["single"],
                        "phases": {
                            "internal_ai_tournament": False,
                            "blotto_vs_bots": True,
                            "connect4_oracle_accuracy": True,
                        },
                    }
                ),
                encoding="utf-8",
            )
            model_config.write_text(
                json.dumps(
                    {
                        "backend": "mock",
                        "model_name": "mock-deterministic",
                        "timeout_seconds": 1,
                        "retry_attempts": 1,
                        "generation": {
                            "temperature": 0.0,
                            "top_p": 1.0,
                            "max_tokens": 32,
                        },
                    }
                ),
                encoding="utf-8",
            )

            with patch("sys.argv", ["main.py", "--config", str(benchmark_config)]):
                benchmark_main.main()

            run_dirs = list(output_root.glob("run_*"))
            self.assertEqual(len(run_dirs), 1)
            run_dir = run_dirs[0]

            self.assertTrue((run_dir / "metadata" / "run_manifest.json").exists())
            self.assertTrue((run_dir / "metadata" / "reproducibility.json").exists())
            self.assertTrue((run_dir / "logs" / "llm_calls.jsonl").exists())
            self.assertTrue((run_dir / "logs" / "trial_records.jsonl").exists())
            self.assertTrue((run_dir / "logs" / "turn_records.jsonl").exists())
            self.assertTrue((run_dir / "logs" / "game_outcomes.jsonl").exists())
            self.assertTrue((run_dir / "summaries" / "summary.json").exists())
            self.assertTrue((run_dir / "summaries" / "metrics.json").exists())
            self.assertTrue(latest_results.exists())

            manifest = json.loads((run_dir / "metadata" / "run_manifest.json").read_text(encoding="utf-8"))
            summary = json.loads((run_dir / "summaries" / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["global_seed"], 8803)
            self.assertIn("code_version", manifest)
            self.assertEqual(summary["global_seed"], 8803)
            self.assertTrue(summary["phases"]["blotto_vs_bots"])
            self.assertTrue(summary["phases"]["connect4_oracle_accuracy"])


if __name__ == "__main__":
    unittest.main()
