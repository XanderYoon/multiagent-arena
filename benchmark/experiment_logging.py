import csv
import json
from pathlib import Path


def write_jsonl(path, records):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record) + "\n")


def write_csv(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    flattened_rows = [_flatten_row(row) for row in rows]
    fieldnames = sorted({key for row in flattened_rows for key in row.keys()})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(flattened_rows)


def build_trial_metadata_records(summary):
    records = []
    for experiment_group, phase_records in summary["phases"].items():
        for record in phase_records:
            architectures = _extract_architectures(record)
            common = _common_record(summary, experiment_group, record)
            records.append(
                {
                    **common,
                    "record_type": "trial_metadata",
                    "architecture_ids": [_architecture_id(entry) for entry in architectures],
                    "architecture_names": [_architecture_name(entry) for entry in architectures],
                    "architecture_types": [_architecture_type(entry) for entry in architectures],
                    "game_parameters": record.get("game_parameters"),
                    "outcome_label": record.get("winner", record.get("outcome")),
                }
            )
    return records


def build_turn_records(summary):
    records = []
    for experiment_group, phase_records in summary["phases"].items():
        for record in phase_records:
            common = _common_record(summary, experiment_group, record)
            for turn in record.get("turns", []):
                records.append(
                    {
                        **common,
                        "record_type": "turn",
                        "timestamp": turn.get("timestamp"),
                        "turn_index": turn.get("turn_index"),
                        "decision_index": turn.get("decision_index"),
                        "player": turn.get("player"),
                        "player_role": turn.get("player_role"),
                        "source": turn.get("source", "agent"),
                        "architecture_id": _architecture_id(turn.get("architecture_metadata", {})),
                        "architecture_name": _architecture_name(turn.get("architecture_metadata", {})),
                        "architecture_type": _architecture_type(turn.get("architecture_metadata", {})),
                        "state_snapshot": turn.get("state_snapshot"),
                        "valid_actions": turn.get("valid_actions"),
                        "requested_move": turn.get("requested_move"),
                        "applied_move": turn.get("applied_move"),
                        "move_valid": turn.get("move_valid"),
                        "invalid_reason": turn.get("invalid_reason"),
                        "call_indices": _extract_call_indices(turn.get("intermediate_outputs", [])),
                        "raw_model_outputs": _extract_raw_model_outputs(turn.get("intermediate_outputs", [])),
                        "parsed_responses": _extract_parsed_responses(turn.get("intermediate_outputs", [])),
                        "intermediate_outputs": turn.get("intermediate_outputs"),
                        "oracle_best_moves": turn.get("oracle_best_moves"),
                        "oracle_best_score": turn.get("oracle_best_score"),
                    }
                )
    return records


def build_game_outcome_records(summary):
    records = []
    for experiment_group, phase_records in summary["phases"].items():
        for record in phase_records:
            common = _common_record(summary, experiment_group, record)
            outcome_record = {
                **common,
                "record_type": "game_outcome",
                "players": record.get("players", [record.get("agent"), "oracle"] if record.get("agent") else []),
                "winner": record.get("winner"),
                "outcome": record.get("outcome"),
                "invalid_players": record.get("invalid_players"),
                "invalid_moves": record.get("invalid_moves"),
                "scores": record.get("scores"),
                "moves": record.get("moves"),
                "nash_distance": record.get("nash_distance"),
                "oracle_accuracy_pct": record.get("accuracy_pct"),
                "oracle_average_value_gap": record.get("average_value_gap"),
                "oracle_blunders": record.get("blunders"),
                "oracle_perfect_moves": record.get("perfect_moves"),
                "metrics_context": record.get("metrics_context"),
            }
            records.append(outcome_record)
    return records


def _common_record(summary, experiment_group, record):
    variant_name = record.get("variant_name", record.get("game"))
    trial = record.get("trial")
    seed = record.get("seed")
    return {
        "run_id": summary["run_id"],
        "benchmark_name": summary["benchmark_name"],
        "experiment_group": experiment_group,
        "trial": trial,
        "trial_id": f"{summary['run_id']}::{experiment_group}::{record['game']}::{trial}::{seed}",
        "seed": seed,
        "game": record["game"],
        "variant_name": variant_name,
        "started_at": record.get("started_at"),
        "completed_at": record.get("completed_at"),
        "duration_ms": record.get("duration_ms"),
        "model": summary["model"],
        "backend": summary["backend"],
        "prompt_family_id": summary["prompt_family_id"],
        "prompt_family": summary["prompt_family"],
        "prompt_version": summary["prompt_version"],
    }


def _extract_architectures(record):
    if "player_architectures" in record:
        return list(record["player_architectures"].values())
    if "architecture_metadata" in record:
        return [record["architecture_metadata"]]
    return []


def _architecture_id(metadata):
    return metadata.get("id") or metadata.get("architecture_id")


def _architecture_name(metadata):
    return metadata.get("display_name") or metadata.get("architecture_name")


def _architecture_type(metadata):
    return metadata.get("type") or metadata.get("architecture_type")


def _extract_call_indices(intermediate_outputs):
    return [output.get("call_index") for output in intermediate_outputs if output.get("call_index") is not None]


def _extract_raw_model_outputs(intermediate_outputs):
    outputs = []
    for output in intermediate_outputs:
        for attempt in output.get("attempts", []):
            outputs.append(attempt.get("raw_response"))
    return outputs


def _extract_parsed_responses(intermediate_outputs):
    responses = []
    for output in intermediate_outputs:
        parsed = output.get("parsed_response")
        if parsed is not None:
            responses.append(parsed)
    return responses


def _flatten_row(row):
    flattened = {}
    for key, value in row.items():
        if isinstance(value, (dict, list)):
            flattened[key] = json.dumps(value, sort_keys=True)
        else:
            flattened[key] = value
    return flattened
