import argparse
import copy
import json
import random
from datetime import UTC, datetime
from pathlib import Path

from agents import configure_runtime_registry
from architectures import build_architecture_registry, run_architecture
from config_loader import load_benchmark_bundle
from experiment_logging import (
    build_game_outcome_records,
    build_trial_metadata_records,
    build_turn_records,
    write_csv,
    write_jsonl,
)
from game_engine import (
    BlottoEnvironment,
    Connect4Environment,
    oracle_analysis,
    check_win,
    get_random_blotto,
    approximate_blotto_equilibrium,
    blotto_nash_distance,
    heuristic_high_value_blotto,
    minimax_solver,
)
from metrics import aggregate_run_metrics, write_metrics_csv
from reproducibility import (
    build_trial_schedule,
    get_git_metadata,
    get_model_identity,
    get_runtime_environment,
    seed_global_randomness,
)

PROJECT_ROOT = Path(__file__).resolve().parent


class RunLogger:
    def __init__(self, latest_log_path, run_log_path):
        self.log_paths = [Path(latest_log_path), Path(run_log_path)]
        for path in self.log_paths:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("", encoding="utf-8")

    def log(self, txt):
        line = str(txt)
        for path in self.log_paths:
            with path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
        print(line)


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def now_iso():
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def duration_ms(started_at, completed_at):
    started = datetime.fromisoformat(started_at.rstrip("Z"))
    completed = datetime.fromisoformat(completed_at.rstrip("Z"))
    return max(0, round((completed - started).total_seconds() * 1000))


def get_selected_prompt_bundle(prompt_catalog, prompt_family_id):
    selected_id = prompt_family_id or prompt_catalog["default_family"]
    selected = dict(prompt_catalog["families"][selected_id])
    return {
        "selected_family_id": selected_id,
        "internal_reasoning_storage": prompt_catalog["internal_reasoning_storage"],
        "family_config": selected,
    }


def build_run_id(git_metadata):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    short_commit = git_metadata.get("short_commit", "unknown")
    dirty_suffix = "_dirty" if git_metadata.get("dirty") else ""
    return f"run_{timestamp}_{short_commit}{dirty_suffix}"


def format_trace(logger, name, trace):
    logger.log(f"\n[ REASONING TRACE FOR {name} ]")
    for step in trace:
        logger.log(f"  -> {step}")
    logger.log("-" * 40)


def execute_architecture(task, architecture_spec):
    if "runner" in architecture_spec:
        return architecture_spec["runner"](task)
    return run_architecture(task, architecture_spec)


def build_blotto_baseline_bot(bot_id, troop_budget, battlefields):
    bot_specs = {
        "uniform": {
            "id": "uniform_bot",
            "display_name": "Uniform Bot",
            "aggregation_rule": "fixed_move",
            "runner": lambda task: {
                "output": {"move": approximate_blotto_equilibrium([1] * battlefields, troop_budget)},
                "trace": ["Uniform allocation across battlefields."],
                "architecture_metadata": {
                    "architecture_id": "uniform_bot",
                    "architecture_name": "Uniform Bot",
                    "architecture_type": "baseline_bot",
                    "agent_count": 0,
                    "role_definitions": [],
                    "aggregation_rule": "fixed_move",
                },
                "intermediate_outputs": [],
            },
        },
        "random": {
            "id": "random_bot",
            "display_name": "Random Bot",
            "aggregation_rule": "random_move",
            "runner": lambda task, budget=troop_budget, zones=battlefields: {
                "output": {"move": get_random_blotto(budget, zones, random.Random(task["seed"]))},
                "trace": ["Random feasible allocation."],
                "architecture_metadata": {
                    "architecture_id": "random_bot",
                    "architecture_name": "Random Bot",
                    "architecture_type": "baseline_bot",
                    "agent_count": 0,
                    "role_definitions": [],
                    "aggregation_rule": "random_move",
                },
                "intermediate_outputs": [],
            },
        },
        "high_value_targeting": {
            "id": "high_value_targeting_bot",
            "display_name": "High-Value Targeting Bot",
            "aggregation_rule": "heuristic_high_value_targeting",
            "runner": lambda task, budget=troop_budget: {
                "output": {
                    "move": heuristic_high_value_blotto(
                        task["state_snapshot"]["points"],
                        budget,
                    )
                },
                "trace": ["Heuristic allocation emphasizing high-value battlefields."],
                "architecture_metadata": {
                    "architecture_id": "high_value_targeting_bot",
                    "architecture_name": "High-Value Targeting Bot",
                    "architecture_type": "baseline_bot",
                    "agent_count": 0,
                    "role_definitions": [],
                    "aggregation_rule": "heuristic_high_value_targeting",
                },
                "intermediate_outputs": [],
            },
        },
        "nash_approx": {
            "id": "nash_approx_bot",
            "display_name": "Nash-Approx Bot",
            "aggregation_rule": "equilibrium_approximation",
            "runner": lambda task, budget=troop_budget: {
                "output": {
                    "move": approximate_blotto_equilibrium(
                        task["state_snapshot"]["points"],
                        budget,
                    )
                },
                "trace": ["Allocation proportional to battlefield values as an equilibrium approximation."],
                "architecture_metadata": {
                    "architecture_id": "nash_approx_bot",
                    "architecture_name": "Nash-Approx Bot",
                    "architecture_type": "baseline_bot",
                    "agent_count": 0,
                    "role_definitions": [],
                    "aggregation_rule": "equilibrium_approximation",
                },
                "intermediate_outputs": [],
            },
        },
    }
    spec = bot_specs[bot_id]
    return {
        "id": spec["id"],
        "display_name": spec["display_name"],
        "type": "baseline_bot",
        "agent_count": 0,
        "aggregation_rule": spec["aggregation_rule"],
        "role_definitions": [],
        "runner": spec["runner"],
    }


def blotto_match(arch1, arch2, trial, logger, game_config, seed):
    started_at = now_iso()
    n1 = arch1["display_name"]
    n2 = arch2["display_name"]
    env = BlottoEnvironment(
        battlefields=game_config["battlefields"],
        troop_budget=game_config["troop_budget"],
        point_range=tuple(game_config["point_range"]),
        fixed_points=game_config.get("fixed_points"),
        point_policy=game_config.get("point_policy", "random_range"),
        discrete=game_config.get("discrete", True),
        seed=seed,
    )
    env.reset(seed=seed)
    state = env.get_state()
    metrics_context = env.get_metrics_context()
    battlefields = game_config["battlefields"]
    troop_budget = game_config["troop_budget"]
    valid_actions = env.get_valid_actions()

    logger.log(f"\n" + "=" * 50)
    logger.log(
        f"--- {n1} vs {n2} ({game_config['display_name']}) | TRIAL {trial} | SEED {seed} ---")

    rules = (
        f"You are playing a simultaneous resource allocation game. "
        f"You have exactly {troop_budget} units. You must distribute ALL of them across {battlefields} distinct zones. "
        f"FATAL CONSTRAINT: Your output must be a list of exactly {battlefields} integers. "
        f"MATH CHECK: You MUST verify that the values sum to EXACTLY {troop_budget}. Do not fail this math check."
    )
    task = {
        "game": "blotto",
        "role": "player",
        "battlefields": battlefields,
        "troop_budget": troop_budget,
        "seed": seed,
        "rules": rules,
        "state": state["description"],
        "state_snapshot": state["snapshot"],
    }

    result1 = execute_architecture(dict(task), arch1)
    out1, trace1 = result1["output"], result1["trace"]
    m1 = out1.get("move") if out1 else None
    format_trace(logger, n1, trace1)

    result2 = execute_architecture(dict(task), arch2)
    out2, trace2 = result2["output"], result2["trace"]
    m2 = out2.get("move") if out2 else None
    if n2 not in {"Uniform Bot", "Random Bot"}:
        format_trace(logger, n2, trace2)

    invalid_players = []
    apply1 = env.apply_action(m1, n1)
    if not apply1["valid"]:
        logger.log(f"HALLUCINATION PENALTY: {n1} invalid {m1}")
        invalid_players.append(n1)
        valid_m1 = [0] * battlefields
    else:
        valid_m1 = list(m1)

    apply2 = env.apply_action(m2, n2)
    if not apply2["valid"]:
        logger.log(f"HALLUCINATION PENALTY: {n2} invalid {m2}")
        invalid_players.append(n2)
        valid_m2 = [0] * battlefields
    else:
        valid_m2 = list(m2)

    metrics_context = env.get_metrics_context()
    scores = metrics_context["scores"] or (0, 0)
    s1, s2 = scores
    logger.log(f"Board Points: {state['snapshot']['points']}")
    logger.log(f"{n1}: {valid_m1} (Score: {s1}) | {n2}: {valid_m2} (Score: {s2})")

    winner = env.get_winner() or "TIE"
    logger.log(f">>> WINNER: {winner} <<<")
    completed_at = now_iso()

    return {
        "trial": trial,
        "seed": seed,
        "started_at": started_at,
        "completed_at": completed_at,
        "game": "blotto",
        "variant_name": game_config.get("variant_name", "blotto"),
        "game_parameters": copy.deepcopy(game_config),
        "players": [n1, n2],
        "player_architectures": {
            n1: result1["architecture_metadata"],
            n2: result2["architecture_metadata"],
        },
        "state_snapshot": state["snapshot"],
        "intermediate_outputs": {
            n1: result1["intermediate_outputs"],
            n2: result2["intermediate_outputs"],
        },
        "turns": [
            {
                "timestamp": completed_at,
                "turn_index": 1,
                "decision_index": 1,
                "player": n1,
                "player_role": "simultaneous_player",
                "state_snapshot": state["snapshot"],
                "valid_actions": valid_actions,
                "architecture_metadata": result1["architecture_metadata"],
                "intermediate_outputs": result1["intermediate_outputs"],
                "requested_move": m1,
                "applied_move": valid_m1,
                "move_valid": apply1["valid"],
                "invalid_reason": apply1["reason"],
            },
            {
                "timestamp": completed_at,
                "turn_index": 1,
                "decision_index": 2,
                "player": n2,
                "player_role": "simultaneous_player",
                "state_snapshot": state["snapshot"],
                "valid_actions": valid_actions,
                "architecture_metadata": result2["architecture_metadata"],
                "intermediate_outputs": result2["intermediate_outputs"],
                "requested_move": m2,
                "applied_move": valid_m2,
                "move_valid": apply2["valid"],
                "invalid_reason": apply2["reason"],
            },
        ],
        "points": state["snapshot"]["points"],
        "moves": {n1: valid_m1, n2: valid_m2},
        "nash_distance": {
            n1: blotto_nash_distance(valid_m1, state["snapshot"]["points"], troop_budget),
            n2: blotto_nash_distance(valid_m2, state["snapshot"]["points"], troop_budget),
        },
        "scores": {n1: s1, n2: s2},
        "winner": winner,
        "invalid_players": invalid_players,
        "metrics_context": metrics_context,
        "duration_ms": duration_ms(started_at, completed_at),
    }


def connect4_ai_vs_ai(arch1, arch2, trial, logger, game_config, seed):
    started_at = now_iso()
    n1 = arch1["display_name"]
    n2 = arch2["display_name"]
    fallback_rng = random.Random(seed)
    env = Connect4Environment(
        rows=game_config["rows"],
        columns=game_config["columns"],
        connect_length=game_config["connect_length"],
        seed=seed,
    )
    env.reset(seed=seed)
    rows = game_config["rows"]
    cols = game_config["columns"]
    connect_length = game_config["connect_length"]

    logger.log(f"\n" + "=" * 50)
    logger.log(
        f"--- {n1} vs {n2} ({game_config['display_name']}) | TRIAL {trial} | SEED {seed} ---")

    rules = (
        f"You are playing a sequential gravity-grid game on a {cols}-column by {rows}-row board. "
        f"IMPORTANT ALIGNMENT: The columns are 0-indexed from 0 through {cols - 1}. "
        f"Players alternate dropping a single token into one available column. "
        f"The token falls straight down to the lowest available empty slot. "
        f"Your goal is to connect {connect_length} of your own tokens horizontally, vertically, or diagonally. "
        f"Constraint: You must output a single integer between 0 and {cols - 1} representing your chosen column."
    )

    invalid_moves = []
    turns = []
    while True:
        state = env.get_state()
        valid = env.get_valid_actions()
        if env.is_terminal() and env.get_winner() == "DRAW":
            logger.log(">>> WINNER: DRAW (Board Full) <<<")
            completed_at = now_iso()
            return {
                "trial": trial,
                "seed": seed,
                "started_at": started_at,
                "completed_at": completed_at,
                "game": "connect4",
                "variant_name": game_config.get("variant_name", "connect4"),
                "game_parameters": copy.deepcopy(game_config),
                "players": [n1, n2],
                "player_architectures": {
                    n1: arch1,
                    n2: arch2,
                },
                "winner": "DRAW",
                "invalid_moves": invalid_moves,
                "turns": turns,
                "state_snapshot": state["snapshot"],
                "metrics_context": env.get_metrics_context(),
                "duration_ms": duration_ms(started_at, completed_at),
            }
        if not valid:
            logger.log(">>> WINNER: DRAW (Board Full) <<<")
            completed_at = now_iso()
            return {
                "trial": trial,
                "seed": seed,
                "started_at": started_at,
                "completed_at": completed_at,
                "game": "connect4",
                "variant_name": game_config.get("variant_name", "connect4"),
                "game_parameters": copy.deepcopy(game_config),
                "players": [n1, n2],
                "player_architectures": {
                    n1: arch1,
                    n2: arch2,
                },
                "winner": "DRAW",
                "invalid_moves": invalid_moves,
                "turns": turns,
                "state_snapshot": state["snapshot"],
                "metrics_context": env.get_metrics_context(),
                "duration_ms": duration_ms(started_at, completed_at),
            }

        turn = env.current_player
        curr_name, curr_arch = (n1, arch1) if turn == 1 else (n2, arch2)
        turn_rules = rules + f" You are Player {turn}."
        task = {
            "game": "connect4",
            "role": "player",
            "rows": rows,
            "columns": cols,
            "connect_length": connect_length,
            "valid_columns": valid,
            "seed": seed,
            "rules": turn_rules,
            "state": state["description"],
            "state_snapshot": state["snapshot"],
        }
        architecture_result = execute_architecture(task, curr_arch)
        out, trace = architecture_result["output"], architecture_result["trace"]
        move = out.get("move", -1) if out else -1

        logger.log(f"\nTurn {turn} - {curr_name} thinking...")
        format_trace(logger, curr_name, trace)

        original_move = move
        invalid_reason = None
        if move not in valid:
            logger.log(f"HALLUCINATION: {curr_name} tried invalid {move}")
            invalid_moves.append({"player": curr_name, "attempted_move": move})
            invalid_reason = "invalid_column"
            move = fallback_rng.choice(valid)

        env.apply_action(move, turn)
        turns.append(
            {
                "timestamp": now_iso(),
                "turn_index": len(turns) + 1,
                "player": curr_name,
                "player_role": f"player_{turn}",
                "state_snapshot": state["snapshot"],
                "valid_actions": valid,
                "architecture_metadata": architecture_result["architecture_metadata"],
                "intermediate_outputs": architecture_result["intermediate_outputs"],
                "requested_move": original_move,
                "applied_move": move,
                "move_valid": invalid_reason is None,
                "invalid_reason": invalid_reason,
            }
        )
        logger.log(f"{curr_name} executes move: Column {move}")

        if env.is_terminal() and env.get_winner() == turn:
            logger.log(env.get_state()["description"].split("\nCurrent Player:")[0])
            logger.log(f">>> WINNER: {curr_name} <<<")
            completed_at = now_iso()
            return {
                "trial": trial,
                "seed": seed,
                "started_at": started_at,
                "completed_at": completed_at,
                "game": "connect4",
                "variant_name": game_config.get("variant_name", "connect4"),
                "game_parameters": copy.deepcopy(game_config),
                "players": [n1, n2],
                "player_architectures": {
                    n1: arch1,
                    n2: arch2,
                },
                "winner": curr_name,
                "invalid_moves": invalid_moves,
                "turns": turns,
                "state_snapshot": env.get_state()["snapshot"],
                "metrics_context": env.get_metrics_context(),
                "duration_ms": duration_ms(started_at, completed_at),
            }


def test_connect4_accuracy(architecture_spec, trial, logger, game_config, seed):
    started_at = now_iso()
    name = architecture_spec["display_name"]
    fallback_rng = random.Random(seed)
    env = Connect4Environment(
        rows=game_config["rows"],
        columns=game_config["columns"],
        connect_length=game_config["connect_length"],
        seed=seed,
    )
    env.reset(seed=seed)
    rows = game_config["rows"]
    cols = game_config["columns"]
    connect_length = game_config["connect_length"]
    oracle_depth = game_config["oracle_depth"]
    oracle_metric = game_config.get("oracle_metric", {})
    turn, perfects, blunders, moves = 1, 0, 0, 0
    total_value_gap = 0
    oracle_records = []
    invalid_attempts = 0
    turns = []

    logger.log(f"\n" + "=" * 50)
    logger.log(f"=== ACCURACY TEST: {name} vs Minimax Oracle | TRIAL {trial} | SEED {seed} ===")
    rules = (
        f"Gravity Grid Game ({cols}x{rows}). Drop token in column (0-{cols - 1}). "
        f"Token falls to bottom. Connect {connect_length} to win. Output a single integer."
    )

    while True:
        state = env.get_state()
        valid = env.get_valid_actions()
        if not valid:
            outcome = "DRAW"
            break

        analysis = oracle_analysis(
            copy.deepcopy(env.board),
            oracle_depth,
            connect_length,
            max_player=2 if turn == 2 else 1,
            min_player=1 if turn == 2 else 2,
        )
        best_moves = analysis["best_moves"]
        best_score = analysis["best_score"]

        if turn == 1:
            task = {
                "game": "connect4",
                "role": "oracle_accuracy_agent",
                "rows": rows,
                "columns": cols,
                "connect_length": connect_length,
                "valid_columns": valid,
                "seed": seed,
                "rules": rules,
                "state": state["description"],
                "state_snapshot": state["snapshot"],
            }
            architecture_result = execute_architecture(task, architecture_spec)
            out, trace = architecture_result["output"], architecture_result["trace"]
            move = out.get("move", -1) if out else -1
            moves += 1
            format_trace(logger, name, trace)

            chosen_move = move if move in valid else random.choice(valid)
            if move not in valid:
                chosen_move = fallback_rng.choice(valid)
            invalid_reason = None
            if move not in valid:
                invalid_attempts += 1
                invalid_reason = "invalid_column"
            chosen_score = analysis["move_scores"].get(chosen_move)
            if chosen_move in best_moves:
                perfects += 1
            else:
                value_gap = best_score - chosen_score if chosen_score is not None else best_score
                total_value_gap += value_gap
                if value_gap > 0:
                    blunders += 1
            oracle_records.append(
                {
                    "state_snapshot": state["snapshot"],
                    "best_moves": best_moves,
                    "best_score": best_score,
                    "move_scores": analysis["move_scores"],
                    "chosen_move": chosen_move,
                    "chosen_move_score": chosen_score,
                    "matched_any_optimal_move": chosen_move in best_moves,
                    "value_gap": 0 if chosen_move in best_moves else (best_score - chosen_score if chosen_score is not None else best_score),
                }
            )

            if move not in valid:
                move = chosen_move
            turns.append(
                {
                    "timestamp": now_iso(),
                    "turn_index": len(turns) + 1,
                    "player": name,
                    "player_role": "oracle_accuracy_agent",
                    "source": "agent",
                    "state_snapshot": state["snapshot"],
                    "valid_actions": valid,
                    "architecture_metadata": architecture_result["architecture_metadata"],
                    "intermediate_outputs": architecture_result["intermediate_outputs"],
                    "requested_move": out.get("move", -1) if out else -1,
                    "applied_move": move,
                    "move_valid": invalid_reason is None,
                    "invalid_reason": invalid_reason,
                    "oracle_best_moves": best_moves,
                    "oracle_best_score": best_score,
                }
            )
            env.apply_action(move, 1)
            if env.is_terminal() and env.get_winner() == 1:
                logger.log(f">>> {name} BEAT THE ORACLE! <<<")
                outcome = "agent_win"
                break
            turn = 2
        else:
            oracle_move = best_moves[0]
            turns.append(
                {
                    "timestamp": now_iso(),
                    "turn_index": len(turns) + 1,
                    "player": "oracle",
                    "player_role": "oracle",
                    "source": "oracle",
                    "state_snapshot": state["snapshot"],
                    "valid_actions": valid,
                    "architecture_metadata": {"id": "oracle", "display_name": "Oracle", "type": "baseline_bot"},
                    "intermediate_outputs": [],
                    "requested_move": oracle_move,
                    "applied_move": oracle_move,
                    "move_valid": True,
                    "invalid_reason": None,
                    "oracle_best_moves": best_moves,
                    "oracle_best_score": best_score,
                }
            )
            env.apply_action(oracle_move, 2)
            if env.is_terminal() and env.get_winner() == 2:
                logger.log(">>> ORACLE WINS <<<")
                outcome = "oracle_win"
                break
            turn = 1

    acc = (perfects / moves) * 100 if moves > 0 else 0
    avg_value_gap = (total_value_gap / moves) if moves > 0 else 0
    logger.log(
        f"[{name} Trial {trial} Stats] Moves: {moves} | Perfect: {perfects} | Blunders: {blunders} | Accuracy: {acc:.1f}% | Avg Value Gap: {avg_value_gap:.2f}")
    completed_at = now_iso()
    return {
        "trial": trial,
        "seed": seed,
        "started_at": started_at,
        "completed_at": completed_at,
        "game": "connect4",
        "variant_name": game_config.get("variant_name", "connect4"),
        "game_parameters": copy.deepcopy(game_config),
        "agent": name,
        "architecture_metadata": architecture_spec,
        "intermediate_outputs": architecture_result["intermediate_outputs"] if moves > 0 else [],
        "state_snapshot": env.get_state()["snapshot"],
        "metrics_context": env.get_metrics_context(),
        "oracle_metric": oracle_metric,
        "oracle_records": oracle_records,
        "turns": turns,
        "moves": moves,
        "invalid_attempts": invalid_attempts,
        "perfect_moves": perfects,
        "blunders": blunders,
        "accuracy_pct": round(acc, 2),
        "average_value_gap": round(avg_value_gap, 4),
        "outcome": outcome,
        "duration_ms": duration_ms(started_at, completed_at),
    }


def export_structured_run_logs(run_dir, summary):
    log_dir = run_dir / "logs"
    summary_dir = run_dir / "summaries"

    trial_records = build_trial_metadata_records(summary)
    turn_records = build_turn_records(summary)
    outcome_records = build_game_outcome_records(summary)

    write_jsonl(log_dir / "trial_records.jsonl", trial_records)
    write_jsonl(log_dir / "turn_records.jsonl", turn_records)
    write_jsonl(log_dir / "game_outcomes.jsonl", outcome_records)

    write_csv(summary_dir / "trial_records.csv", trial_records)
    write_csv(summary_dir / "turn_records.csv", turn_records)
    write_csv(summary_dir / "game_outcomes.csv", outcome_records)


def save_run_artifacts(run_dir, bundle):
    config_dir = run_dir / "config"
    write_json(config_dir / "benchmark.json", bundle["benchmark"])
    write_json(config_dir / "model.json", bundle["model"])
    for alias, model_config in bundle.get("models", {}).items():
        write_json(config_dir / "models" / f"{alias}.json", model_config)
    write_json(config_dir / "prompt_catalog.json", bundle["prompt"])
    write_json(config_dir / "prompt.json", bundle["selected_prompt"])
    write_json(config_dir / "architectures.json", bundle["architectures"])
    write_json(config_dir / "experiment.json", bundle["experiment"])
    for game_name, game_config in bundle["games"].items():
        write_json(config_dir / "games" / f"{game_name}.json", game_config)


def main():
    parser = argparse.ArgumentParser(description="Run the multi-agent game benchmark.")
    parser.add_argument(
        "--config",
        default="configs/benchmark.json",
        help="Path to the benchmark config file.",
    )
    args = parser.parse_args()

    bundle = load_benchmark_bundle(args.config)
    benchmark_config = bundle["benchmark"]
    experiment_config = bundle["experiment"]
    model_config = bundle["model"]
    model_configs = bundle.get("models", {bundle.get("default_model_alias", "default"): model_config})
    prompt_config = bundle["prompt"]
    architecture_config = bundle["architectures"]
    games = bundle["games"]
    selected_prompt = get_selected_prompt_bundle(prompt_config, experiment_config.get("prompt_family"))
    bundle["selected_prompt"] = selected_prompt

    git_metadata = get_git_metadata(PROJECT_ROOT)
    run_id = build_run_id(git_metadata)
    output_root = PROJECT_ROOT / benchmark_config["output_root"]
    run_dir = output_root / run_id
    configure_runtime_registry(
        model_configs,
        prompt_config,
        run_dir / "logs",
        prompt_family=selected_prompt["selected_family_id"],
        default_alias=bundle.get("default_model_alias"),
    )
    logger = RunLogger(
        PROJECT_ROOT / benchmark_config["latest_results_path"],
        run_dir / "logs" / "results.txt",
    )
    save_run_artifacts(run_dir, bundle)

    architectures = build_architecture_registry(architecture_config, experiment_config["architectures"])
    global_seed = experiment_config["global_seed"]
    seed_global_randomness(global_seed)
    baseline_bots = games["blotto"].get("baseline_bots", ["uniform", "random"])
    trial_schedule = build_trial_schedule(architectures, games, experiment_config, global_seed, baseline_bots)
    model_identity = {
        alias: get_model_identity(config)
        for alias, config in model_configs.items()
    }
    runtime_environment = get_runtime_environment()
    primary_model_label = experiment_config.get("model_group_id", model_config["model_name"])

    metadata = {
        "run_id": run_id,
        "started_at": now_iso(),
        "benchmark_name": benchmark_config["benchmark_name"],
        "config_path": str(bundle["paths"]["benchmark"]),
        "global_seed": global_seed,
        "seed_policy": {
            "global_seed": global_seed,
            "child_seed_strategy": trial_schedule["seed_function"],
        },
        "model": primary_model_label,
        "backend": model_config["backend"],
        "default_model_alias": bundle.get("default_model_alias"),
        "model_aliases": sorted(model_configs.keys()),
        "model_identity": model_identity,
        "code_version": git_metadata,
        "runtime_environment": runtime_environment,
        "prompt_family_id": selected_prompt["selected_family_id"],
        "prompt_family": selected_prompt["family_config"]["family"],
        "prompt_version": selected_prompt["family_config"]["version"],
        "internal_reasoning_storage": selected_prompt["internal_reasoning_storage"],
        "trial_schedule": trial_schedule["schedule"],
        "output_dir": str(run_dir),
    }
    write_json(run_dir / "metadata" / "run_manifest.json", metadata)
    write_json(
        run_dir / "metadata" / "reproducibility.json",
        {
            "global_seed": global_seed,
            "seed_policy": trial_schedule["seed_function"],
            "trial_schedule": trial_schedule["schedule"],
            "code_version": git_metadata,
            "model_identity": model_identity,
            "runtime_environment": runtime_environment,
        },
    )
    summary = {
        "run_id": run_id,
        "benchmark_name": benchmark_config["benchmark_name"],
        "model": primary_model_label,
        "backend": model_config["backend"],
        "global_seed": global_seed,
        "code_version": git_metadata,
        "model_identity": model_identity,
        "runtime_environment": runtime_environment,
        "prompt_family_id": selected_prompt["selected_family_id"],
        "prompt_family": selected_prompt["family_config"]["family"],
        "prompt_version": selected_prompt["family_config"]["version"],
        "internal_reasoning_storage": selected_prompt["internal_reasoning_storage"],
        "trial_schedule": trial_schedule,
        "phases": {
            "internal_ai_tournament": [],
            "blotto_vs_bots": [],
            "connect4_oracle_accuracy": [],
        },
    }

    if experiment_config["phases"]["internal_ai_tournament"]:
        logger.log("\n" + "#" * 60)
        logger.log("PHASE 1: INTERNAL AI vs AI TOURNAMENT")
        logger.log("#" * 60)
        for entry in trial_schedule["schedule"]:
            if entry["phase"] != "internal_ai_tournament":
                continue
            arch1 = next(arch for arch in architectures if arch["id"] == entry["participants"][0])
            arch2 = next(arch for arch in architectures if arch["id"] == entry["participants"][1])
            if entry["game"] == "blotto":
                summary["phases"]["internal_ai_tournament"].append(
                    blotto_match(arch1, arch2, entry["trial"], logger, games["blotto"], entry["seed"]))
            elif entry["game"] == "connect4":
                summary["phases"]["internal_ai_tournament"].append(
                    connect4_ai_vs_ai(arch1, arch2, entry["trial"], logger, games["connect4"], entry["seed"]))

    if experiment_config["phases"]["blotto_vs_bots"]:
        logger.log("\n" + "#" * 60)
        logger.log("PHASE 2: AI vs STANDARD BOTS (RESOURCE ALLOCATION)")
        logger.log("#" * 60)
        troop_budget = games["blotto"]["troop_budget"]
        battlefields = games["blotto"]["battlefields"]
        for entry in trial_schedule["schedule"]:
            if entry["phase"] != "blotto_vs_bots":
                continue
            architecture_spec = next(arch for arch in architectures if arch["id"] == entry["participants"][0])
            baseline_bot = entry["participants"][1]
            summary["phases"]["blotto_vs_bots"].append(
                blotto_match(
                    architecture_spec,
                    build_blotto_baseline_bot(baseline_bot, troop_budget, battlefields),
                    entry["trial"],
                    logger,
                    games["blotto"],
                    entry["seed"],
                )
            )

    if experiment_config["phases"]["connect4_oracle_accuracy"]:
        logger.log("\n" + "#" * 60)
        logger.log("PHASE 3: GRAVITY GRID OPTIMAL ACCURACY")
        logger.log("#" * 60)
        for entry in trial_schedule["schedule"]:
            if entry["phase"] != "connect4_oracle_accuracy":
                continue
            architecture_spec = next(arch for arch in architectures if arch["id"] == entry["participants"][0])
            summary["phases"]["connect4_oracle_accuracy"].append(
                test_connect4_accuracy(architecture_spec, entry["trial"], logger, games["connect4"], entry["seed"]))

    summary["completed_at"] = now_iso()
    write_json(run_dir / "summaries" / "summary.json", summary)
    export_structured_run_logs(run_dir, summary)
    metrics_summary = aggregate_run_metrics(summary)
    write_json(run_dir / "summaries" / "metrics.json", metrics_summary)
    write_metrics_csv(run_dir / "summaries" / "aggregate_tables.csv", metrics_summary["aggregate_tables"])
    write_metrics_csv(run_dir / "summaries" / "architecture_summaries.csv", metrics_summary["architecture_summaries"])
    write_metrics_csv(run_dir / "summaries" / "model_summaries.csv", metrics_summary["model_summaries"])
    write_metrics_csv(run_dir / "summaries" / "prompt_summaries.csv", metrics_summary["prompt_summaries"])


if __name__ == "__main__":
    main()
