import unittest

from main import build_blotto_baseline_bot
from reproducibility import (
    build_trial_schedule,
    get_model_identity,
    get_runtime_environment,
    stable_seed,
)


class ReproducibilityTests(unittest.TestCase):
    def test_stable_seed_is_deterministic(self):
        first = stable_seed(8803, "phase", 1, "single", "parallel")
        second = stable_seed(8803, "phase", 1, "single", "parallel")
        third = stable_seed(8803, "phase", 2, "single", "parallel")
        self.assertEqual(first, second)
        self.assertNotEqual(first, third)

    def test_trial_schedule_is_deterministic_and_complete(self):
        architectures = [
            {"id": "single"},
            {"id": "parallel"},
            {"id": "hierarchical"},
        ]
        games = {"blotto": {}, "connect4": {}}
        experiment_config = {
            "num_trials": 2,
            "phases": {
                "internal_ai_tournament": True,
                "blotto_vs_bots": True,
                "connect4_oracle_accuracy": True,
            },
        }
        baseline_bots = ["uniform", "random"]

        schedule_one = build_trial_schedule(architectures, games, experiment_config, 8803, baseline_bots)
        schedule_two = build_trial_schedule(architectures, games, experiment_config, 8803, baseline_bots)

        self.assertEqual(schedule_one, schedule_two)
        self.assertEqual(len(schedule_one["schedule"]), 30)
        self.assertEqual(schedule_one["schedule"][0]["phase"], "internal_ai_tournament")

    def test_mock_model_identity_and_runtime_environment_exist(self):
        identity = get_model_identity(
            {
                "backend": "mock",
                "model_name": "mock-deterministic",
                "generation": {"temperature": 0.0},
            }
        )
        environment = get_runtime_environment()

        self.assertEqual(identity["configured_model_name"], "mock-deterministic")
        self.assertEqual(identity["backend"], "mock")
        self.assertIn("python_version", environment)
        self.assertIn("cpu_count", environment)

    def test_random_blotto_bot_uses_seeded_rng(self):
        bot = build_blotto_baseline_bot("random", troop_budget=100, battlefields=3)
        task = {"seed": 1234}
        first = bot["runner"](task)["output"]["move"]
        second = bot["runner"](task)["output"]["move"]
        different = bot["runner"]({"seed": 5678})["output"]["move"]

        self.assertEqual(first, second)
        self.assertNotEqual(first, different)
        self.assertEqual(sum(first), 100)


if __name__ == "__main__":
    unittest.main()
