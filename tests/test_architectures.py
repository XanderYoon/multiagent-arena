import unittest
from unittest.mock import patch

from benchmark.architectures import run_architecture


class ArchitectureBehaviorTests(unittest.TestCase):
    def test_parallel_tie_break_lowest_move(self):
        spec = {
            "id": "parallel",
            "type": "parallel",
            "display_name": "Parallel Team",
            "agent_count": 2,
            "aggregation_rule": "majority_vote",
            "tie_breaker": "lowest_move",
            "role_definitions": [{"role": "voter", "prompt_template": "parallel_voter_role"}],
        }
        task = {"game": "connect4"}
        side_effect = [
            {
                "role": "voter",
                "prompt_template": "parallel_voter_role",
                "call_index": 1,
                "trace": "vote 3",
                "parsed_response": {"move": 3, "reasoning": "a"},
                "parse_failure_reason": None,
                "attempts": [],
                "valid": True,
                "prompt_version": "v1",
            },
            {
                "role": "voter",
                "prompt_template": "parallel_voter_role",
                "call_index": 2,
                "trace": "vote 1",
                "parsed_response": {"move": 1, "reasoning": "b"},
                "parse_failure_reason": None,
                "attempts": [],
                "valid": True,
                "prompt_version": "v1",
            },
        ]
        with patch("benchmark.architectures._invoke_role", side_effect=side_effect):
            result = run_architecture(task, spec)

        self.assertEqual(result["output"]["move"], 1)
        self.assertIn("tie_break_lowest_move", result["trace"][-1])

    def test_parallel_handles_all_invalid_votes(self):
        spec = {
            "id": "parallel",
            "type": "parallel",
            "display_name": "Parallel Team",
            "agent_count": 2,
            "aggregation_rule": "majority_vote",
            "tie_breaker": "first_valid",
            "role_definitions": [{"role": "voter", "prompt_template": "parallel_voter_role"}],
        }
        invalid_result = {
            "role": "voter",
            "prompt_template": "parallel_voter_role",
            "call_index": 1,
            "trace": "invalid",
            "parsed_response": None,
            "parse_failure_reason": "missing_move",
            "attempts": [],
            "valid": False,
            "prompt_version": "v1",
        }
        with patch(
            "benchmark.architectures._invoke_role",
            side_effect=[invalid_result, dict(invalid_result, call_index=2)],
        ):
            result = run_architecture({"game": "connect4"}, spec)

        self.assertIsNone(result["output"]["move"])
        self.assertIn("All parallel sub-agents failed validation.", result["output"]["reasoning"])

    def test_hierarchical_falls_back_to_critic_when_executive_invalid(self):
        spec = {
            "id": "hierarchical",
            "type": "hierarchical",
            "display_name": "Hierarchical Team",
            "agent_count": 3,
            "aggregation_rule": "executive_audit",
            "critic_count": 1,
            "include_critic": True,
            "role_definitions": [
                {"role": "reasoner", "prompt_template": "reasoner_role"},
                {"role": "critic", "prompt_template": "critic_role"},
                {"role": "executive", "prompt_template": "executive_role"},
            ],
        }

        def invoke_side_effect(task, architecture_spec, role_name, *args, **kwargs):
            if role_name == "reasoner":
                return {
                    "role": role_name,
                    "prompt_template": "reasoner_role",
                    "call_index": 1,
                    "trace": "reasoner",
                    "parsed_response": {"move": 2, "reasoning": "reasoner"},
                    "parse_failure_reason": None,
                    "attempts": [],
                    "valid": True,
                    "prompt_version": "v1",
                }
            if role_name == "critic":
                return {
                    "role": role_name,
                    "prompt_template": "critic_role",
                    "call_index": 2,
                    "trace": "critic",
                    "parsed_response": {"move": 4, "reasoning": "critic"},
                    "parse_failure_reason": None,
                    "attempts": [],
                    "valid": True,
                    "prompt_version": "v1",
                }
            return {
                "role": role_name,
                "prompt_template": "executive_role",
                "call_index": 3,
                "trace": "executive failed",
                "parsed_response": None,
                "parse_failure_reason": "missing_move",
                "attempts": [],
                "valid": False,
                "prompt_version": "v1",
            }

        task = {
            "game": "connect4",
            "rules": "choose a legal column",
            "state": "board",
            "state_snapshot": {"board": []},
        }
        with patch("benchmark.architectures._invoke_role", side_effect=invoke_side_effect):
            result = run_architecture(task, spec)

        self.assertEqual(result["output"]["move"], 4)
        self.assertEqual(result["architecture_metadata"]["fallback_source"], "critic_fallback")


if __name__ == "__main__":
    unittest.main()
