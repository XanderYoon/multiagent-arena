import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agents import extract_json, validate_agent_response, LLMRuntime


PROMPT_CATALOG = {
    "default_family": "structured_reasoning_v1",
    "internal_reasoning_storage": {"mode": "full"},
    "families": {
        "structured_reasoning_v1": {
            "family": "structured_reasoning",
            "version": "structured_reasoning_v1",
            "template_root": "prompts/structured_reasoning_v1",
            "reasoning_trace_policy": {"decision": "full"},
            "templates": {
                "game_agent_system": "game_agent_system.txt",
                "game_agent_user_blotto": "game_agent_user_blotto.txt",
                "game_agent_user_connect4": "game_agent_user_connect4.txt",
                "single_role": "single_role.txt",
                "parallel_voter_role": "parallel_voter_role.txt",
                "reasoner_role": "reasoner_role.txt",
                "critic_role": "critic_role.txt",
                "executive_role": "executive_role.txt",
                "hierarchical_critic_user": "hierarchical_critic_user.txt",
                "hierarchical_executive_user": "hierarchical_executive_user.txt",
            },
        }
    },
}


class AgentParsingTests(unittest.TestCase):
    def test_extract_json_from_surrounding_text(self):
        parsed = extract_json("analysis...\n{\"move\": 3, \"reasoning\": \"safe\"}\nextra")
        self.assertEqual(parsed["move"], 3)
        self.assertEqual(parsed["reasoning"], "safe")

    def test_validate_blotto_and_connect4_outputs(self):
        blotto_task = {"game": "blotto", "battlefields": 3, "troop_budget": 100}
        connect4_task = {"game": "connect4", "valid_columns": [0, 2, 4]}

        self.assertEqual(validate_agent_response({"move": [20, 30, 50]}, blotto_task), (True, None))
        self.assertEqual(validate_agent_response({"move": [20, 30]}, blotto_task), (False, "blotto_wrong_length"))
        self.assertEqual(validate_agent_response({"move": [20, -1, 81]}, blotto_task), (False, "blotto_non_integer_or_negative"))
        self.assertEqual(validate_agent_response({"move": 2}, connect4_task), (True, None))
        self.assertEqual(validate_agent_response({"move": 1}, connect4_task), (False, "connect4_invalid_column"))

    def test_runtime_retries_malformed_output_then_succeeds(self):
        model_config = {
            "backend": "mock",
            "model_name": "mock-deterministic",
            "retry_attempts": 2,
            "generation": {"temperature": 0.0},
        }
        task = {"game": "connect4", "valid_columns": [0, 1, 2], "role": "player"}
        with tempfile.TemporaryDirectory() as tmp_dir:
            runtime = LLMRuntime(model_config, PROMPT_CATALOG, Path(tmp_dir) / "calls.jsonl")
            with patch.object(runtime, "_send_request", side_effect=[
                ("not json", {"provider_response": None}),
                ("{\"move\": 2, \"reasoning\": \"retry worked\"}", {"provider_response": None}),
            ]):
                result = runtime.invoke("system", "user", task, {"test": True})

        self.assertEqual(result["parsed_response"]["move"], 2)
        self.assertIsNone(result["parse_failure_reason"])
        self.assertEqual(len(result["attempts"]), 2)
        self.assertEqual(result["attempts"][0]["parse_failure_reason"], "parsed_response_not_object")


if __name__ == "__main__":
    unittest.main()
