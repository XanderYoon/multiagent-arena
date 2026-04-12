from collections import Counter

from benchmark.agents import get_runtime


def _build_trace(call_result):
    parsed = call_result["parsed_response"] or {}
    if call_result["parse_failure_reason"]:
        return f"Validation failure: {call_result['parse_failure_reason']}"
    return parsed.get("reasoning", "No reasoning field returned.")


def _render_base_prompts(runtime, task, role_prompt):
    system_prompt = runtime.prompt_manager.render(
        "game_agent_system",
        role_instructions=role_prompt,
    )
    user_prompt = runtime.prompt_manager.render_for_game(
        "game_agent_user",
        task["game"],
        rules=task["rules"],
        state=task["state"],
    )
    return system_prompt, user_prompt


def _resolve_model_alias(architecture_spec, role_name, metadata_suffix):
    metadata_suffix = metadata_suffix or {}
    role_aliases = architecture_spec.get("role_model_aliases", {})
    if role_name in role_aliases:
        assigned = role_aliases[role_name]
        if isinstance(assigned, list):
            if role_name == "voter":
                return assigned[metadata_suffix.get("replica_index", 0) % len(assigned)]
            if role_name == "critic":
                return assigned[metadata_suffix.get("critic_index", 0) % len(assigned)]
            return assigned[0]
        return assigned

    if role_name == "voter" and architecture_spec.get("model_sequence"):
        sequence = architecture_spec["model_sequence"]
        return sequence[metadata_suffix.get("replica_index", 0) % len(sequence)]

    if role_name == "critic" and architecture_spec.get("critic_model_sequence"):
        sequence = architecture_spec["critic_model_sequence"]
        return sequence[metadata_suffix.get("critic_index", 0) % len(sequence)]

    return architecture_spec.get("model_alias")


def _invoke_role(task, architecture_spec, role_name, prompt_template, metadata_suffix=None, user_template=None, **user_context):
    model_alias = _resolve_model_alias(architecture_spec, role_name, metadata_suffix)
    runtime = get_runtime(model_alias)
    role_prompt = runtime.prompt_manager.render(prompt_template)
    if user_template is None:
        system_prompt, user_prompt = _render_base_prompts(runtime, task, role_prompt)
    else:
        system_prompt = runtime.prompt_manager.render(
            "game_agent_system",
            role_instructions=role_prompt,
        )
        user_prompt = runtime.prompt_manager.render_for_game(user_template, task["game"], **user_context)

    metadata = {
        "architecture": architecture_spec["id"],
        "architecture_type": architecture_spec["type"],
        "role": role_name,
        "model_alias": model_alias,
        "model_name": runtime.model_name,
    }
    if metadata_suffix:
        metadata.update(metadata_suffix)

    call_result = runtime.invoke(system_prompt, user_prompt, task, metadata)
    parsed = call_result["parsed_response"]
    return {
        "role": role_name,
        "prompt_template": prompt_template,
        "call_index": call_result["call_index"],
        "model_alias": model_alias,
        "model_name": runtime.model_name,
        "trace": _build_trace(call_result),
        "parsed_response": parsed,
        "parse_failure_reason": call_result["parse_failure_reason"],
        "attempts": call_result["attempts"],
        "valid": call_result["parse_failure_reason"] is None and parsed is not None,
        "prompt_version": call_result["prompt_version"],
    }


def _copy_move(move):
    return list(move) if isinstance(move, list) else move


def _normalize_move_key(move):
    if isinstance(move, list):
        return tuple(move)
    return move


def _resolve_parallel_tie(valid_votes, tie_breaker):
    if not valid_votes:
        return None, "no_valid_votes"

    counts = Counter(vote["move_key"] for vote in valid_votes)
    highest = max(counts.values())
    winners = [move_key for move_key, count in counts.items() if count == highest]
    if len(winners) == 1:
        winner = winners[0]
        selected_vote = next(vote for vote in valid_votes if vote["move_key"] == winner)
        return selected_vote["move"], "majority_vote"

    if tie_breaker == "lowest_move":
        winner = sorted(winners, key=lambda value: repr(value))[0]
        selected_vote = next(vote for vote in valid_votes if vote["move_key"] == winner)
        return selected_vote["move"], "tie_break_lowest_move"

    selected_vote = next(vote for vote in valid_votes if vote["move_key"] in winners)
    return selected_vote["move"], "tie_break_first_valid"


def run_architecture(task, architecture_spec):
    architecture_type = architecture_spec["type"]
    if architecture_type == "single":
        return _run_single(task, architecture_spec)
    if architecture_type == "parallel":
        return _run_parallel(task, architecture_spec)
    if architecture_type == "hierarchical":
        return _run_hierarchical(task, architecture_spec)
    raise ValueError(f"Unsupported architecture type: {architecture_type}")


def _run_single(task, architecture_spec):
    role_template = architecture_spec["role_definitions"][0]["prompt_template"]
    role_result = _invoke_role(task, architecture_spec, "single_agent", role_template)
    parsed = role_result["parsed_response"] or {"move": None}
    parsed["prompt_version"] = role_result["prompt_version"]
    parsed["architecture_metadata"] = {
        "architecture_id": architecture_spec["id"],
        "architecture_name": architecture_spec["display_name"],
        "architecture_type": architecture_spec["type"],
        "model_alias": architecture_spec.get("model_alias"),
        "role_model_aliases": architecture_spec.get("role_model_aliases"),
        "agent_count": architecture_spec["agent_count"],
        "role_definitions": architecture_spec["role_definitions"],
        "aggregation_rule": architecture_spec["aggregation_rule"],
    }
    return {
        "output": parsed,
        "trace": [role_result["trace"]],
        "architecture_metadata": parsed["architecture_metadata"],
        "intermediate_outputs": [role_result],
    }


def _run_parallel(task, architecture_spec):
    voter_template = architecture_spec["role_definitions"][0]["prompt_template"]
    team_size = architecture_spec["agent_count"]
    tie_breaker = architecture_spec.get("tie_breaker", "first_valid")
    intermediate_outputs = []
    valid_votes = []

    for replica_index in range(team_size):
        role_result = _invoke_role(
            task,
            architecture_spec,
            "voter",
            voter_template,
            metadata_suffix={"replica_index": replica_index},
        )
        intermediate_outputs.append(role_result)
        parsed = role_result["parsed_response"]
        if role_result["valid"] and parsed and "move" in parsed:
            valid_votes.append(
                {
                    "replica_index": replica_index,
                    "move": _copy_move(parsed["move"]),
                    "move_key": _normalize_move_key(parsed["move"]),
                    "reasoning": parsed.get("reasoning"),
                }
            )

    final_move, aggregation_outcome = _resolve_parallel_tie(valid_votes, tie_breaker)
    if final_move is None:
        reasoning = "All parallel sub-agents failed validation."
    else:
        reasoning = f"Parallel aggregation selected {final_move} using {aggregation_outcome}."

    output = {
        "move": final_move,
        "reasoning": reasoning,
        "prompt_version": intermediate_outputs[0]["prompt_version"] if intermediate_outputs else None,
        "architecture_metadata": {
            "architecture_id": architecture_spec["id"],
            "architecture_name": architecture_spec["display_name"],
            "architecture_type": architecture_spec["type"],
            "model_sequence": architecture_spec.get("model_sequence"),
            "role_model_aliases": architecture_spec.get("role_model_aliases"),
            "agent_count": architecture_spec["agent_count"],
            "role_definitions": architecture_spec["role_definitions"],
            "aggregation_rule": architecture_spec["aggregation_rule"],
            "tie_breaker": tie_breaker,
        },
    }
    trace = [entry["trace"] for entry in intermediate_outputs]
    trace.append(f"Votes: {[vote['move'] for vote in valid_votes]}")
    trace.append(f"Aggregation: {aggregation_outcome}")
    return {
        "output": output,
        "trace": trace,
        "architecture_metadata": output["architecture_metadata"],
        "intermediate_outputs": intermediate_outputs,
    }


def _run_hierarchical(task, architecture_spec):
    role_templates = {entry["role"]: entry["prompt_template"] for entry in architecture_spec["role_definitions"]}
    critic_count = architecture_spec.get("critic_count", 1)
    include_critic = architecture_spec.get("include_critic", True)
    intermediate_outputs = []

    reasoner_result = _invoke_role(task, architecture_spec, "reasoner", role_templates["reasoner"])
    intermediate_outputs.append(reasoner_result)
    reasoner_output = reasoner_result["parsed_response"]

    critic_results = []
    if include_critic:
        critic_template = role_templates["critic"]
        for critic_index in range(critic_count):
            critic_result = _invoke_role(
                task,
                architecture_spec,
                "critic",
                critic_template,
                metadata_suffix={"critic_index": critic_index},
                user_template="hierarchical_critic_user",
                rules=task["rules"],
                state=task["state"],
                reasoner_output=reasoner_output,
            )
            critic_results.append(critic_result)
            intermediate_outputs.append(critic_result)

    executive_result = _invoke_role(
        task,
        architecture_spec,
        "executive",
        role_templates["executive"],
        user_template="hierarchical_executive_user",
        rules=task["rules"],
        state=task["state"],
        reasoner_output=reasoner_output,
        critic_output=[entry["parsed_response"] for entry in critic_results],
    )
    intermediate_outputs.append(executive_result)

    final_output = executive_result["parsed_response"]
    fallback_source = None
    if final_output is None or "move" not in final_output:
        for critic_result in critic_results:
            if critic_result["valid"] and critic_result["parsed_response"] and "move" in critic_result["parsed_response"]:
                final_output = critic_result["parsed_response"]
                fallback_source = "critic_fallback"
                break
    if final_output is None or "move" not in final_output:
        if reasoner_result["valid"] and reasoner_result["parsed_response"] and "move" in reasoner_result["parsed_response"]:
            final_output = reasoner_result["parsed_response"]
            fallback_source = "reasoner_fallback"
    if final_output is None or "move" not in final_output:
        final_output = {"move": None, "reasoning": "All hierarchical sub-agents failed validation."}
        fallback_source = "no_valid_subagent"

    final_output = dict(final_output)
    final_output["prompt_version"] = executive_result["prompt_version"]
    final_output["architecture_metadata"] = {
        "architecture_id": architecture_spec["id"],
        "architecture_name": architecture_spec["display_name"],
        "architecture_type": architecture_spec["type"],
        "model_alias": architecture_spec.get("model_alias"),
        "role_model_aliases": architecture_spec.get("role_model_aliases"),
        "agent_count": architecture_spec["agent_count"],
        "role_definitions": architecture_spec["role_definitions"],
        "aggregation_rule": architecture_spec["aggregation_rule"],
        "critic_count": critic_count,
        "include_critic": include_critic,
        "fallback_source": fallback_source,
    }

    trace = [f"Reasoner: {reasoner_result['trace']}"]
    for critic_index, critic_result in enumerate(critic_results):
        trace.append(f"Critic {critic_index + 1}: {critic_result['trace']}")
    trace.append(f"Executive: {executive_result['trace']}")
    if fallback_source:
        trace.append(f"Fallback: {fallback_source}")
    return {
        "output": final_output,
        "trace": trace,
        "architecture_metadata": final_output["architecture_metadata"],
        "intermediate_outputs": intermediate_outputs,
    }


def build_architecture_registry(architecture_config, selected_ids):
    selected = []
    selected_id_set = set(selected_ids)
    for spec in architecture_config["architectures"]:
        if spec["id"] in selected_id_set:
            selected.append(spec)
    return selected
