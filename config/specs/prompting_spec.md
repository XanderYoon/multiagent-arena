# Prompting Specification

## Prompt Families

The repository now supports these prompt families:

- `minimal_v1`
- `structured_reasoning_v1`
- `chain_of_thought_v1`
- `legality_first_v1`

Each family is versioned and selected at the experiment level through `prompt_family` in the experiment config.

## Template Structure

Prompt templates are version-controlled under `config/prompts/templates/{family_version}/`.

The system now distinguishes:

- Game-specific templates:
  - `game_agent_user_blotto`
  - `game_agent_user_connect4`
- Architecture-specific templates:
  - `single_role`
  - `parallel_voter_role`
  - `reasoner_role`
  - `critic_role`
  - `executive_role`

Hierarchical review prompts are also versioned:

- `hierarchical_critic_user`
- `hierarchical_executive_user`

## Prompt Metadata

Run artifacts now record:

- `prompt_family_id`
- `prompt_family`
- `prompt_version`
- internal reasoning storage policy

## Internal Reasoning Storage Policy

The repository currently stores internal reasoning text in full.

Rationale:

- reasoning traces are part of the benchmark signal
- prompt-family comparison requires preserving the model-visible reasoning field
- runtime metadata is already recorded separately in `llm_calls.jsonl`
