import unittest

from game_engine import (
    Connect4Environment,
    minimax_solver,
    oracle_analysis,
)
from main import build_blotto_baseline_bot


class BaselineAndOracleTests(unittest.TestCase):
    def test_blotto_baseline_bots_produce_legal_allocations(self):
        task = {"state_snapshot": {"points": [5, 30, 10]}, "seed": 1234}
        for bot_id in ["uniform", "random", "high_value_targeting", "nash_approx"]:
            bot = build_blotto_baseline_bot(bot_id, troop_budget=100, battlefields=3)
            move = bot["runner"](task)["output"]["move"]
            self.assertEqual(len(move), 3)
            self.assertEqual(sum(move), 100)
            self.assertTrue(all(value >= 0 for value in move))

    def test_high_value_targeting_emphasizes_highest_value_battlefield(self):
        task = {"state_snapshot": {"points": [5, 30, 10]}, "seed": 1234}
        bot = build_blotto_baseline_bot("high_value_targeting", troop_budget=100, battlefields=3)
        move = bot["runner"](task)["output"]["move"]
        self.assertGreater(move[1], move[0])
        self.assertGreater(move[1], move[2])

    def test_oracle_analysis_and_minimax_choose_immediate_win(self):
        env = Connect4Environment(rows=6, columns=7, connect_length=4)
        env.apply_action(0, 1)
        env.apply_action(6, 2)
        env.apply_action(1, 1)
        env.apply_action(6, 2)
        env.apply_action(2, 1)
        env.apply_action(5, 2)

        analysis = oracle_analysis(env.board, depth=4, connect_length=4, max_player=1, min_player=2)
        best_col, _ = minimax_solver(env.board, 4, -float("inf"), float("inf"), True, 4, 1, 2)

        self.assertIn(3, analysis["best_moves"])
        self.assertEqual(best_col, 3)


if __name__ == "__main__":
    unittest.main()
