import csv
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path


PRIMARY_METRICS = [
    "win_rate",
    "hallucination_rate",
    "connect4_optimal_move_accuracy",
    "blotto_nash_distance",
    "consistency",
]

SECONDARY_METRICS = [
    "tie_rate",
    "average_value_gap",
    "blunder_rate",
    "invalid_attempt_rate",
    "outcome_stability",
    "per_state_agreement",
]


def _safe_mean(values):
    return statistics.mean(values) if values else None


def _safe_pvariance(values):
    if not values:
        return None
    if len(values) == 1:
        return 0.0
    return statistics.pvariance(values)


def _serialize_state(snapshot):
    return json.dumps(snapshot, sort_keys=True)


def _base_bucket():
    return {
        "matches": 0,
        "wins": 0,
        "ties": 0,
        "losses": 0,
        "outcomes": [],
        "outcome_scores": [],
        "invalid_attempts": 0,
        "invalid_denominator": 0,
        "accuracy_values": [],
        "value_gap_values": [],
        "blunder_values": [],
        "nash_distance_values": [],
        "state_move_map": defaultdict(list),
    }


def _register_outcome(bucket, outcome_label):
    bucket["outcomes"].append(outcome_label)
    if outcome_label == "win":
        bucket["wins"] += 1
        bucket["outcome_scores"].append(1.0)
    elif outcome_label == "tie":
        bucket["ties"] += 1
        bucket["outcome_scores"].append(0.5)
    else:
        bucket["losses"] += 1
        bucket["outcome_scores"].append(0.0)
    bucket["matches"] += 1


def _compute_per_state_agreement(state_move_map):
    agreements = []
    for moves in state_move_map.values():
        if len(moves) < 2:
            continue
        counts = Counter(moves)
        agreements.append(max(counts.values()) / len(moves))
    return _safe_mean(agreements)


def _compute_outcome_stability(outcomes):
    if not outcomes:
        return None
    counts = Counter(outcomes)
    return max(counts.values()) / len(outcomes)


def _finalize_bucket(bucket):
    matches = bucket["matches"]
    invalid_denominator = bucket["invalid_denominator"]
    accuracy_values = bucket["accuracy_values"]
    value_gap_values = bucket["value_gap_values"]
    nash_distance_values = bucket["nash_distance_values"]
    blunder_values = bucket["blunder_values"]

    return {
        "matches": matches,
        "wins": bucket["wins"],
        "ties": bucket["ties"],
        "losses": bucket["losses"],
        "win_rate": (bucket["wins"] / matches) if matches else None,
        "tie_rate": (bucket["ties"] / matches) if matches else None,
        "hallucination_rate": (bucket["invalid_attempts"] / invalid_denominator) if invalid_denominator else None,
        "invalid_attempt_rate": (bucket["invalid_attempts"] / invalid_denominator) if invalid_denominator else None,
        "legality_rate": (1 - (bucket["invalid_attempts"] / invalid_denominator)) if invalid_denominator else None,
        "connect4_optimal_move_accuracy": _safe_mean(accuracy_values),
        "average_value_gap": _safe_mean(value_gap_values),
        "blunder_rate": _safe_mean(blunder_values),
        "blotto_nash_distance": _safe_mean(nash_distance_values),
        "consistency": {
            "variance_across_trials": _safe_pvariance(bucket["outcome_scores"]),
            "per_state_agreement": _compute_per_state_agreement(bucket["state_move_map"]),
            "outcome_stability": _compute_outcome_stability(bucket["outcomes"]),
            "accuracy_variance": _safe_pvariance(accuracy_values),
            "nash_distance_variance": _safe_pvariance(nash_distance_values),
        },
    }


def aggregate_run_metrics(summary):
    architecture_buckets = defaultdict(_base_bucket)
    model_buckets = defaultdict(_base_bucket)
    prompt_buckets = defaultdict(_base_bucket)

    model_id = summary["model"]
    prompt_id = summary["prompt_family_id"]

    def update_bucket(bucket_key, experiment_group, game, architecture_id=None):
        if architecture_id is not None:
            return architecture_buckets[(experiment_group, game, architecture_id)]
        raise RuntimeError("architecture_id required for direct bucket updates")

    for experiment_group, records in summary["phases"].items():
        for record in records:
            game = record["game"]
            if game == "blotto":
                for player in record["players"]:
                    architecture_meta = record["player_architectures"][player]
                    if architecture_meta["architecture_type"] == "baseline_bot":
                        continue
                    arch_id = architecture_meta["architecture_id"]
                    bucket = update_bucket(architecture_buckets, experiment_group, game, arch_id)
                    bucket["invalid_denominator"] += 1
                    if player in record["invalid_players"]:
                        bucket["invalid_attempts"] += 1
                    nash = record["nash_distance"][player]
                    if nash is not None:
                        bucket["nash_distance_values"].append(nash["normalized_l1_distance"])
                    bucket["state_move_map"][_serialize_state(record["state_snapshot"])].append(
                        json.dumps(record["moves"][player])
                    )
                    if record["winner"] == "TIE":
                        _register_outcome(bucket, "tie")
                    elif record["winner"] == player:
                        _register_outcome(bucket, "win")
                    else:
                        _register_outcome(bucket, "loss")

            elif game == "connect4" and "players" in record:
                for player in record["players"]:
                    architecture_meta = record["player_architectures"][player]
                    if architecture_meta["type"] == "baseline_bot" or architecture_meta.get("architecture_type") == "baseline_bot":
                        continue
                    arch_id = architecture_meta.get("id", architecture_meta.get("architecture_id"))
                    bucket = update_bucket(architecture_buckets, experiment_group, game, arch_id)
                    player_turns = [turn for turn in record["turns"] if turn["player"] == player]
                    bucket["invalid_denominator"] += len(player_turns)
                    bucket["invalid_attempts"] += sum(1 for invalid in record["invalid_moves"] if invalid["player"] == player)
                    for turn in player_turns:
                        bucket["state_move_map"][_serialize_state(turn["state_snapshot"])].append(
                            json.dumps(turn["applied_move"])
                        )
                    if record["winner"] == "DRAW":
                        _register_outcome(bucket, "tie")
                    elif record["winner"] == player:
                        _register_outcome(bucket, "win")
                    else:
                        _register_outcome(bucket, "loss")

            elif game == "connect4" and "agent" in record:
                architecture_meta = record["architecture_metadata"]
                arch_id = architecture_meta["id"]
                bucket = update_bucket(architecture_buckets, experiment_group, game, arch_id)
                bucket["invalid_denominator"] += record["moves"]
                bucket["invalid_attempts"] += record.get("invalid_attempts", 0)
                bucket["accuracy_values"].append(record["accuracy_pct"])
                bucket["value_gap_values"].append(record["average_value_gap"])
                bucket["blunder_values"].append((record["blunders"] / record["moves"]) if record["moves"] else 0.0)
                for oracle_record in record["oracle_records"]:
                    bucket["state_move_map"][_serialize_state(oracle_record["state_snapshot"])].append(
                        json.dumps(oracle_record["chosen_move"])
                    )
                if record["outcome"] == "agent_win":
                    _register_outcome(bucket, "win")
                elif record["outcome"] == "DRAW":
                    _register_outcome(bucket, "tie")
                else:
                    _register_outcome(bucket, "loss")

    architecture_rows = []
    for (experiment_group, game, architecture_id), bucket in architecture_buckets.items():
        row = {
            "scope_type": "architecture",
            "scope_id": architecture_id,
            "experiment_group": experiment_group,
            "game": game,
            "model": model_id,
            "prompt_family_id": prompt_id,
        }
        row.update(_finalize_bucket(bucket))
        architecture_rows.append(row)

        model_bucket = model_buckets[(experiment_group, game, model_id)]
        prompt_bucket = prompt_buckets[(experiment_group, game, prompt_id)]
        for target in (model_bucket, prompt_bucket):
            target["matches"] += bucket["matches"]
            target["wins"] += bucket["wins"]
            target["ties"] += bucket["ties"]
            target["losses"] += bucket["losses"]
            target["outcomes"].extend(bucket["outcomes"])
            target["outcome_scores"].extend(bucket["outcome_scores"])
            target["invalid_attempts"] += bucket["invalid_attempts"]
            target["invalid_denominator"] += bucket["invalid_denominator"]
            target["accuracy_values"].extend(bucket["accuracy_values"])
            target["value_gap_values"].extend(bucket["value_gap_values"])
            target["blunder_values"].extend(bucket["blunder_values"])
            target["nash_distance_values"].extend(bucket["nash_distance_values"])
            for key, values in bucket["state_move_map"].items():
                target["state_move_map"][key].extend(values)

    model_rows = []
    for (experiment_group, game, scope_id), bucket in model_buckets.items():
        row = {
            "scope_type": "model",
            "scope_id": scope_id,
            "experiment_group": experiment_group,
            "game": game,
        }
        row.update(_finalize_bucket(bucket))
        model_rows.append(row)

    prompt_rows = []
    for (experiment_group, game, scope_id), bucket in prompt_buckets.items():
        row = {
            "scope_type": "prompt",
            "scope_id": scope_id,
            "experiment_group": experiment_group,
            "game": game,
        }
        row.update(_finalize_bucket(bucket))
        prompt_rows.append(row)

    return {
        "schema_version": "metrics_v1",
        "primary_metrics": PRIMARY_METRICS,
        "secondary_metrics": SECONDARY_METRICS,
        "architecture_summaries": architecture_rows,
        "model_summaries": model_rows,
        "prompt_summaries": prompt_rows,
        "aggregate_tables": architecture_rows + model_rows + prompt_rows,
    }


def write_metrics_csv(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    flattened_rows = []
    for row in rows:
        flat = dict(row)
        consistency = flat.pop("consistency", {})
        for key, value in consistency.items():
            flat[f"consistency_{key}"] = value
        flattened_rows.append(flat)

    if not flattened_rows:
        path.write_text("", encoding="utf-8")
        return

    fieldnames = sorted({key for row in flattened_rows for key in row.keys()})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(flattened_rows)
