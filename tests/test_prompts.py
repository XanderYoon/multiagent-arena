import unittest

from agents import PromptManager


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
                "hierarchical_executive_user": "hierarchical_executive_user.txt"
            }
        },
        "minimal_v1": {
            "family": "minimal",
            "version": "minimal_v1",
            "template_root": "prompts/minimal_v1",
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
                "hierarchical_executive_user": "hierarchical_executive_user.txt"
            }
        }
    }
}


class PromptManagerTests(unittest.TestCase):
    def test_selects_requested_family(self):
        manager = PromptManager(PROMPT_CATALOG, selected_family="minimal_v1")
        self.assertEqual(manager.family, "minimal")
        self.assertEqual(manager.version, "minimal_v1")

    def test_renders_game_specific_template(self):
        manager = PromptManager(PROMPT_CATALOG, selected_family="structured_reasoning_v1")
        rendered = manager.render_for_game(
            "game_agent_user",
            "connect4",
            rules="Rule text",
            state="Board text",
        )
        self.assertIn("Rule text", rendered)
        self.assertIn("Board text", rendered)
        self.assertIn("tactical threats", rendered)


if __name__ == "__main__":
    unittest.main()
