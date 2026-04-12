import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


SECTION14_3_AXES = {
    "model_size_and_mixed_team_composition": "model_scale",
    "quantization_and_mixed_team_composition": "quantization",
}


def load_json(path):
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_csv(path):
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _architecture_signature(spec):
    architecture_type = spec.get("type")
    if architecture_type == "parallel":
        sequence = spec.get("model_sequence", [])
        counts = defaultdict(int)
        for alias in sequence:
            counts[alias] += 1
        composition = ",".join(f"{alias}:{counts[alias]}" for alias in sorted(counts))
        return {
            "architecture_type": architecture_type,
            "composition_label": "+".join(sequence),
            "composition_signature": composition,
        }

    if architecture_type == "hierarchical":
        aliases = spec.get("role_model_aliases", {})
        critic_aliases = aliases.get("critic", [])
        if not isinstance(critic_aliases, list):
            critic_aliases = [critic_aliases]
        composition = [
            f"reasoner:{aliases.get('reasoner')}",
            f"critic:{'+'.join(critic_aliases)}",
            f"executive:{aliases.get('executive')}",
        ]
        count_aliases = [aliases.get("reasoner"), *critic_aliases, aliases.get("executive")]
        counts = defaultdict(int)
        for alias in count_aliases:
            counts[alias] += 1
        return {
            "architecture_type": architecture_type,
            "composition_label": " -> ".join(composition),
            "composition_signature": ",".join(f"{alias}:{counts[alias]}" for alias in sorted(counts)),
        }

    return {
        "architecture_type": architecture_type,
        "composition_label": spec.get("display_name", spec.get("id")),
        "composition_signature": spec.get("id"),
    }


def _numeric(value):
    if value in {"", None}:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def discover_section14_3_runs(experiments_root):
    run_dirs = []
    for run_dir in sorted(Path(experiments_root).glob("run_*")):
        experiment_path = run_dir / "config" / "experiment.json"
        manifest_path = run_dir / "metadata" / "run_manifest.json"
        architecture_path = run_dir / "config" / "architectures.json"
        summary_path = run_dir / "summaries" / "architecture_summaries.csv"
        if not experiment_path.exists():
            continue
        if not manifest_path.exists() or not architecture_path.exists() or not summary_path.exists():
            continue
        experiment_config = load_json(experiment_path)
        comparison_axis = experiment_config.get("comparison_axis")
        if comparison_axis not in SECTION14_3_AXES:
            continue
        run_dirs.append(run_dir)
    return run_dirs


def build_section14_3_rows(run_dirs):
    rows = []
    for run_dir in run_dirs:
        manifest = load_json(run_dir / "metadata" / "run_manifest.json")
        experiment_config = load_json(run_dir / "config" / "experiment.json")
        architecture_config = load_json(run_dir / "config" / "architectures.json")
        summaries = load_csv(run_dir / "summaries" / "architecture_summaries.csv")
        architecture_specs = {spec["id"]: spec for spec in architecture_config["architectures"]}
        suite = SECTION14_3_AXES[experiment_config["comparison_axis"]]

        for row in summaries:
            architecture_id = row["scope_id"]
            spec = architecture_specs.get(architecture_id)
            if not spec:
                continue
            if spec.get("type") not in {"parallel", "hierarchical"}:
                continue

            signature = _architecture_signature(spec)
            rows.append(
                {
                    "run_id": manifest["run_id"],
                    "suite": suite,
                    "comparison_axis": experiment_config["comparison_axis"],
                    "run_label": experiment_config.get("run_label"),
                    "model_group_id": experiment_config.get("model_group_id"),
                    "prompt_family_id": manifest.get("prompt_family_id"),
                    "game": row["game"],
                    "experiment_group": row["experiment_group"],
                    "architecture_id": architecture_id,
                    "architecture_name": spec.get("display_name"),
                    "architecture_type": signature["architecture_type"],
                    "composition_label": signature["composition_label"],
                    "composition_signature": signature["composition_signature"],
                    "matches": _numeric(row.get("matches")),
                    "win_rate": _numeric(row.get("win_rate")),
                    "hallucination_rate": _numeric(row.get("hallucination_rate")),
                    "connect4_optimal_move_accuracy": _numeric(row.get("connect4_optimal_move_accuracy")),
                    "blotto_nash_distance": _numeric(row.get("blotto_nash_distance")),
                    "average_value_gap": _numeric(row.get("average_value_gap")),
                    "blunder_rate": _numeric(row.get("blunder_rate")),
                    "consistency_per_state_agreement": _numeric(row.get("consistency_per_state_agreement")),
                    "consistency_outcome_stability": _numeric(row.get("consistency_outcome_stability")),
                }
            )
    return rows


def build_leaderboard(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["suite"], row["game"], row["experiment_group"], row["architecture_type"])].append(row)

    leaderboard = []
    for key, group_rows in sorted(grouped.items()):
        suite, game, experiment_group, architecture_type = key
        primary_metric = "connect4_optimal_move_accuracy" if game == "connect4" and experiment_group == "connect4_oracle_accuracy" else "win_rate"
        sorted_rows = sorted(
            group_rows,
            key=lambda row: (
                row.get(primary_metric) is None,
                -(row.get(primary_metric) or 0.0),
                row["architecture_id"],
            ),
        )
        best = sorted_rows[0]
        leaderboard.append(
            {
                "suite": suite,
                "game": game,
                "experiment_group": experiment_group,
                "architecture_type": architecture_type,
                "primary_metric": primary_metric,
                "best_architecture_id": best["architecture_id"],
                "best_architecture_name": best["architecture_name"],
                "best_composition_label": best["composition_label"],
                "best_primary_metric_value": best.get(primary_metric),
            }
        )
    return leaderboard


def write_csv_rows(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Summarize completed Section 14.3 model-scale and quantization runs.")
    parser.add_argument(
        "--experiments-root",
        default="reports/runs/experiment_runs",
        help="Directory containing run_* folders.",
    )
    parser.add_argument(
        "--output-dir",
        default="reports/latest",
        help="Directory for the generated Section 14.3 report artifacts.",
    )
    args = parser.parse_args()

    run_dirs = discover_section14_3_runs(args.experiments_root)
    rows = build_section14_3_rows(run_dirs)
    leaderboard = build_leaderboard(rows)
    payload = {
        "section": "14.3",
        "run_count": len(run_dirs),
        "runs": [run_dir.name for run_dir in run_dirs],
        "rows": rows,
        "leaderboard": leaderboard,
    }

    output_dir = Path(args.output_dir)
    write_json(output_dir / "section14_3_summary.json", payload)
    write_csv_rows(output_dir / "section14_3_summary.csv", rows)
    write_csv_rows(output_dir / "section14_3_leaderboard.csv", leaderboard)


if __name__ == "__main__":
    main()
