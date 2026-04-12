import csv
import json
from collections import defaultdict
from pathlib import Path


def collect_runs(experiments_root):
    experiments_root = Path(experiments_root)
    runs = []
    for run_dir in sorted(experiments_root.glob("run_*")):
        manifest_path = run_dir / "metadata" / "run_manifest.json"
        summary_path = run_dir / "summaries" / "summary.json"
        metrics_path = run_dir / "summaries" / "metrics.json"
        turn_records_path = run_dir / "logs" / "turn_records.jsonl"
        if not manifest_path.exists() or not summary_path.exists() or not metrics_path.exists():
            continue
        runs.append(
            {
                "run_dir": run_dir,
                "manifest": json.loads(manifest_path.read_text(encoding="utf-8")),
                "summary": json.loads(summary_path.read_text(encoding="utf-8")),
                "metrics": json.loads(metrics_path.read_text(encoding="utf-8")),
                "turn_records": _read_jsonl(turn_records_path) if turn_records_path.exists() else [],
            }
        )
    return runs


def build_combined_tables(runs):
    combined = []
    for run in runs:
        run_id = run["summary"]["run_id"]
        for row in run["metrics"]["aggregate_tables"]:
            combined_row = dict(row)
            combined_row["run_id"] = run_id
            combined_row["prompt_family"] = run["summary"].get("prompt_family")
            combined_row["model"] = run["summary"].get("model")
            combined.append(combined_row)
    return combined


def build_hallucination_summary(runs):
    buckets = defaultdict(lambda: {"invalid_moves": 0, "total_turns": 0})
    for run in runs:
        for turn in run["turn_records"]:
            architecture = turn.get("architecture_id") or turn.get("player")
            game = turn.get("game")
            key = (game, architecture, turn.get("invalid_reason") or "valid")
            buckets[key]["total_turns"] += 1
            if not turn.get("move_valid", True):
                buckets[key]["invalid_moves"] += 1

    rows = []
    for (game, architecture, reason), bucket in sorted(buckets.items()):
        rows.append(
            {
                "game": game,
                "architecture": architecture,
                "reason": reason,
                "invalid_moves": bucket["invalid_moves"],
                "total_turns": bucket["total_turns"],
            }
        )
    return rows


def build_claim_map(runs, combined_rows):
    claims = []
    grouped = defaultdict(list)
    for row in combined_rows:
        if row.get("scope_type") != "architecture":
            continue
        grouped[(row.get("game"), row.get("scope_id"))].append(row)

    for (game, architecture), rows in sorted(grouped.items()):
        win_rates = [row["win_rate"] for row in rows if row.get("win_rate") is not None]
        legality_rates = [row["legality_rate"] for row in rows if row.get("legality_rate") is not None]
        if win_rates:
            claims.append(
                {
                    "claim": f"{architecture} achieved mean win rate {round(sum(win_rates) / len(win_rates), 4)} on {game}.",
                    "metric": "win_rate",
                    "game": game,
                    "architecture": architecture,
                    "run_ids": sorted({row["run_id"] for row in rows}),
                }
            )
        if legality_rates:
            claims.append(
                {
                    "claim": f"{architecture} achieved mean legality rate {round(sum(legality_rates) / len(legality_rates), 4)} on {game}.",
                    "metric": "legality_rate",
                    "game": game,
                    "architecture": architecture,
                    "run_ids": sorted({row["run_id"] for row in rows}),
                }
            )
    return claims


def write_report_bundle(output_dir, runs):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    combined_rows = build_combined_tables(runs)
    hallucination_rows = build_hallucination_summary(runs)
    claim_map = build_claim_map(runs, combined_rows)

    _write_csv(output_dir / "combined_aggregate_tables.csv", combined_rows)
    _write_csv(output_dir / "hallucination_patterns.csv", hallucination_rows)
    (output_dir / "combined_runs.json").write_text(json.dumps(_serialize_runs(runs), indent=2), encoding="utf-8")
    (output_dir / "claim_map.json").write_text(json.dumps(claim_map, indent=2), encoding="utf-8")
    (output_dir / "report.md").write_text(build_markdown_report(runs, combined_rows, hallucination_rows, claim_map), encoding="utf-8")

    plots_dir = output_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    for filename, svg in build_svg_plots(combined_rows).items():
        (plots_dir / filename).write_text(svg, encoding="utf-8")


def build_markdown_report(runs, combined_rows, hallucination_rows, claim_map):
    models = sorted({row.get("model") for row in combined_rows if row.get("model")})
    prompts = sorted({row.get("prompt_family_id") for row in combined_rows if row.get("prompt_family_id")})
    lines = [
        "# Analysis Report",
        "",
        f"- Runs analyzed: {len(runs)}",
        f"- Models observed: {', '.join(models) if models else 'none'}",
        f"- Prompt families observed: {', '.join(prompts) if prompts else 'none'}",
        "",
        "## Summary Tables",
        "",
        "- `combined_aggregate_tables.csv` contains all aggregate rows across runs.",
        "- `hallucination_patterns.csv` contains invalid-move pattern counts by game and architecture.",
        "",
        "## Narrative Findings",
        "",
    ]

    if claim_map:
        for claim in claim_map[:10]:
            lines.append(f"- {claim['claim']} Supported by runs: {', '.join(claim['run_ids'])}.")
    else:
        lines.append("- Insufficient run data to generate metric-backed findings.")

    comparison_lines = _build_architecture_comparisons(combined_rows)
    if comparison_lines:
        lines.extend(["", "## Architecture Comparisons", ""])
        lines.extend([f"- {line}" for line in comparison_lines])

    lines.extend(
        [
            "",
            "## Coverage Notes",
            "",
            f"- Model scaling plots {'are' if len(models) > 1 else 'are not'} supported by the current runs.",
            f"- Prompt comparison plots {'are' if len(prompts) > 1 else 'are not'} supported by the current runs.",
            f"- Hallucination patterns were {'computed' if hallucination_rows else 'not available'} from turn logs.",
        ]
    )
    return "\n".join(lines) + "\n"


def build_svg_plots(combined_rows):
    plots = {}
    plots.update(_build_architecture_plots(combined_rows))
    plots.update(_build_model_plots(combined_rows))
    plots.update(_build_prompt_plots(combined_rows))
    return plots


def _build_architecture_plots(combined_rows):
    plots = {}
    by_game = defaultdict(dict)
    for row in combined_rows:
        if row.get("scope_type") != "architecture":
            continue
        game = row.get("game")
        architecture = row.get("scope_id")
        metric = "win_rate" if game == "blotto" else "connect4_optimal_move_accuracy"
        value = row.get(metric)
        if value is not None:
            by_game[game][architecture] = value

    for game, values in by_game.items():
        plots[f"architecture_{game}.svg"] = _simple_bar_svg(
            title=f"Architecture Comparison: {game}",
            values=values,
        )
    return plots


def _build_model_plots(combined_rows):
    values = defaultdict(list)
    for row in combined_rows:
        if row.get("scope_type") != "architecture":
            continue
        if row.get("win_rate") is not None:
            values[row.get("model")].append(row["win_rate"])

    averages = {
        model: sum(model_values) / len(model_values)
        for model, model_values in values.items()
        if model and model_values
    }
    if len(averages) < 2:
        return {"model_scaling.svg": _placeholder_svg("Model Scaling", "Insufficient multi-model data")}
    return {"model_scaling.svg": _simple_bar_svg("Model Scaling", averages)}


def _build_prompt_plots(combined_rows):
    values = defaultdict(list)
    for row in combined_rows:
        if row.get("scope_type") != "architecture":
            continue
        if row.get("win_rate") is not None:
            values[row.get("prompt_family_id")].append(row["win_rate"])

    averages = {
        prompt: sum(prompt_values) / len(prompt_values)
        for prompt, prompt_values in values.items()
        if prompt and prompt_values
    }
    if len(averages) < 2:
        return {"prompt_comparison.svg": _placeholder_svg("Prompt Comparison", "Insufficient multi-prompt data")}
    return {"prompt_comparison.svg": _simple_bar_svg("Prompt Comparison", averages)}


def _simple_bar_svg(title, values):
    items = list(values.items())
    width = 640
    height = 360
    margin = 40
    chart_height = 220
    bar_width = max(40, int((width - 2 * margin) / max(len(items), 1)) - 20)
    max_value = max(values.values()) if values else 1
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
        f'<text x="{width/2}" y="24" text-anchor="middle" font-size="18">{title}</text>',
    ]
    for index, (label, value) in enumerate(items):
        x = margin + index * (bar_width + 20)
        bar_height = 0 if max_value == 0 else (value / max_value) * chart_height
        y = height - margin - bar_height
        lines.append(f'<rect x="{x}" y="{y}" width="{bar_width}" height="{bar_height}" fill="#2f6db3" />')
        lines.append(f'<text x="{x + bar_width/2}" y="{height - margin + 16}" text-anchor="middle" font-size="10">{label}</text>')
        lines.append(f'<text x="{x + bar_width/2}" y="{y - 6}" text-anchor="middle" font-size="10">{round(value, 3)}</text>')
    lines.append("</svg>")
    return "\n".join(lines)


def _placeholder_svg(title, message):
    return "\n".join(
        [
            '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="240">',
            f'<text x="320" y="40" text-anchor="middle" font-size="18">{title}</text>',
            f'<text x="320" y="120" text-anchor="middle" font-size="14">{message}</text>',
            "</svg>",
        ]
    )


def _build_architecture_comparisons(combined_rows):
    buckets = defaultdict(list)
    for row in combined_rows:
        if row.get("scope_type") == "architecture" and row.get("win_rate") is not None:
            buckets[(row.get("game"), row.get("scope_id"))].append(row["win_rate"])

    comparisons = []
    for game in sorted({game for game, _ in buckets.keys()}):
        single = buckets.get((game, "single"))
        parallel = buckets.get((game, "parallel"))
        hierarchical = buckets.get((game, "hierarchical"))
        if single and parallel:
            comparisons.append(
                f"On {game}, `parallel` mean win rate was {round(sum(parallel)/len(parallel), 4)} versus `single` at {round(sum(single)/len(single), 4)}."
            )
        if single and hierarchical:
            comparisons.append(
                f"On {game}, `hierarchical` mean win rate was {round(sum(hierarchical)/len(hierarchical), 4)} versus `single` at {round(sum(single)/len(single), 4)}."
            )
    return comparisons


def _write_csv(path, rows):
    path = Path(path)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = sorted({key for row in rows for key in row.keys()})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _read_jsonl(path):
    rows = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _serialize_runs(runs):
    serialized = []
    for run in runs:
        serialized.append(
            {
                "run_dir": str(run["run_dir"]),
                "manifest": run["manifest"],
                "summary": run["summary"],
                "metrics": run["metrics"],
                "turn_record_count": len(run["turn_records"]),
            }
        )
    return serialized
