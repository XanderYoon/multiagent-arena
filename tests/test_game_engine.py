import unittest

from benchmark.game_engine import (
    BlottoEnvironment,
    Connect4Environment,
    approximate_blotto_equilibrium,
    blotto_nash_distance,
    heuristic_high_value_blotto,
    oracle_analysis,
)


class BlottoEnvironmentTests(unittest.TestCase):
    def test_reset_is_deterministic_with_seed(self):
        env1 = BlottoEnvironment(seed=123)
        env2 = BlottoEnvironment(seed=123)
        self.assertEqual(env1.get_state()["snapshot"]["points"], env2.get_state()["snapshot"]["points"])

    def test_invalid_allocation_is_rejected(self):
        env = BlottoEnvironment()
        result = env.apply_action([50, 25], "A")
        self.assertFalse(result["valid"])
        self.assertEqual(result["reason"], "allocation_wrong_length")

    def test_negative_and_non_integer_allocations_are_rejected(self):
        env = BlottoEnvironment()
        negative = env.apply_action([50, -1, 51], "A")
        non_integer = env.apply_action([33, 33, 34.0], "B")
        self.assertFalse(negative["valid"])
        self.assertEqual(negative["reason"], "allocation_negative")
        self.assertFalse(non_integer["valid"])
        self.assertEqual(non_integer["reason"], "allocation_non_integer")

    def test_terminal_after_two_valid_actions(self):
        env = BlottoEnvironment(fixed_points=[10, 20, 30])
        env.apply_action([0, 0, 100], "A")
        env.apply_action([100, 0, 0], "B")
        self.assertTrue(env.is_terminal())
        self.assertEqual(env.get_winner(), "A")
        self.assertEqual(env.get_metrics_context()["scores"], (30, 10))

    def test_fixed_and_random_point_policies_are_supported(self):
        fixed = BlottoEnvironment(point_policy="fixed", fixed_points=[5, 15, 25])
        random_one = BlottoEnvironment(point_policy="random_range", point_range=(1, 3), seed=7)
        random_two = BlottoEnvironment(point_policy="random_range", point_range=(1, 3), seed=7)
        self.assertEqual(fixed.get_state()["snapshot"]["points"], [5, 15, 25])
        self.assertEqual(random_one.get_state()["snapshot"]["points"], random_two.get_state()["snapshot"]["points"])

    def test_equilibrium_distance_and_heuristic_baselines_are_computed(self):
        points = [10, 20, 30]
        equilibrium = approximate_blotto_equilibrium(points, 100)
        heuristic = heuristic_high_value_blotto(points, 100)
        distance = blotto_nash_distance(equilibrium, points, 100)
        self.assertEqual(sum(equilibrium), 100)
        self.assertEqual(sum(heuristic), 100)
        self.assertEqual(distance["l1_distance"], 0)
        self.assertEqual(distance["normalized_l1_distance"], 0.0)


class Connect4EnvironmentTests(unittest.TestCase):
    def test_valid_actions_and_serialized_state_exist(self):
        env = Connect4Environment()
        state = env.get_state()
        self.assertIn("description", state)
        self.assertIn("snapshot", state)
        self.assertEqual(state["snapshot"]["valid_columns"], [0, 1, 2, 3, 4, 5, 6])
        self.assertIn("Orientation: rows are listed top to bottom", state["description"])
        self.assertIn("rendered_board", state["snapshot"])

    def test_out_of_bounds_and_full_column_are_rejected(self):
        env = Connect4Environment(rows=2, columns=2, connect_length=2)
        invalid = env.apply_action(3, 1)
        self.assertFalse(invalid["valid"])
        self.assertEqual(invalid["reason"], "move_out_of_bounds")

        self.assertTrue(env.apply_action(0, 1)["valid"])
        self.assertTrue(env.apply_action(0, 2)["valid"])
        full_column = env.apply_action(0, 1)
        self.assertFalse(full_column["valid"])
        self.assertEqual(full_column["reason"], "column_full")

    def test_horizontal_win_sets_terminal_and_winner(self):
        env = Connect4Environment(rows=4, columns=4, connect_length=4)
        env.apply_action(0, 1)
        env.apply_action(0, 2)
        env.apply_action(1, 1)
        env.apply_action(1, 2)
        env.apply_action(2, 1)
        env.apply_action(2, 2)
        env.apply_action(3, 1)
        self.assertTrue(env.is_terminal())
        self.assertEqual(env.get_winner(), 1)

    def test_state_description_matches_board_orientation(self):
        env = Connect4Environment(rows=4, columns=4, connect_length=4)
        env.apply_action(0, 1)
        env.apply_action(1, 2)
        description = env.get_state()["description"]
        lines = description.splitlines()
        self.assertEqual(lines[0], "Col: 0 1 2 3")
        self.assertEqual(lines[1], "     . . . .")
        self.assertEqual(lines[2], "     . . . .")
        self.assertEqual(lines[4], "     X O . .")
        self.assertTrue(lines[-1].startswith("Valid Columns to play:"))

    def test_oracle_analysis_prefers_immediate_winning_move(self):
        env = Connect4Environment(rows=6, columns=7, connect_length=4)
        env.apply_action(0, 1)
        env.apply_action(6, 2)
        env.apply_action(1, 1)
        env.apply_action(6, 2)
        env.apply_action(2, 1)
        env.apply_action(5, 2)
        analysis = oracle_analysis(env.board, depth=4, connect_length=4, max_player=1, min_player=2)
        self.assertIn(3, analysis["best_moves"])
        self.assertEqual(analysis["move_scores"][3], analysis["best_score"])


if __name__ == "__main__":
    unittest.main()
