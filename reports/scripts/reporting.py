import csv
import json
from collections import defaultdict
from pathlib import Path

try:
    from .matplotlib_figures import render_bar_chart_svg, render_heatmap_svg, render_placeholder_svg
except ImportError:
    from matplotlib_figures import render_bar_chart_svg, render_heatmap_svg, render_placeholder_svg


SECTION14_3_COMPARISON_AXES = {
    "model_size_and_mixed_team_composition",
    "quantization_and_mixed_team_composition",
}
PRIMARY_METRICS = {
    ("blotto", "internal_ai_tournament"): "win_rate",
    ("blotto", "blotto_vs_bots"): "win_rate",
    ("connect4", "internal_ai_tournament"): "win_rate",
    ("connect4", "connect4_oracle_accuracy"): "connect4_optimal_move_accuracy",
}


def collect_runs(experiments_root):
    experiments_root = Path(experiments_root)
    runs = []
    for run_dir in sorted(experiments_root.glob("run_*")):
        manifest_path = run_dir / "metadata" / "run_manifest.json"
        summary_path = run_dir / "summaries" / "summary.json"
        metrics_path = run_dir / "summaries" / "metrics.json"
        turn_records_path = run_dir / "logs" / "turn_records.jsonl"
        experiment_path = run_dir / "config" / "experiment.json"
        if not manifest_path.exists() or not summary_path.exists() or not metrics_path.exists():
            continue
        runs.append(
            {
                "run_dir": run_dir,
                "manifest": json.loads(manifest_path.read_text(encoding="utf-8")),
                "summary": json.loads(summary_path.read_text(encoding="utf-8")),
                "metrics": json.loads(metrics_path.read_text(encoding="utf-8")),
                "experiment": json.loads(experiment_path.read_text(encoding="utf-8")) if experiment_path.exists() else {},
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
            combined_row["run_label"] = run["experiment"].get("run_label")
            combined_row["comparison_axis"] = run["experiment"].get("comparison_axis")
            combined_row["is_section14_3"] = is_section14_3_axis(run["experiment"].get("comparison_axis"))
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


def build_invalid_reason_summary(runs):
    buckets = defaultdict(lambda: {"invalid_moves": 0})
    for run in runs:
        for turn in run["turn_records"]:
            if turn.get("move_valid", True):
                continue
            architecture = turn.get("architecture_id") or turn.get("player")
            key = (
                run["summary"].get("run_id"),
                run["experiment"].get("run_label"),
                run["experiment"].get("comparison_axis"),
                turn.get("game"),
                architecture,
                turn.get("invalid_reason") or "unknown",
            )
            buckets[key]["invalid_moves"] += 1

    rows = []
    for (run_id, run_label, comparison_axis, game, architecture, reason), bucket in sorted(buckets.items()):
        rows.append(
            {
                "run_id": run_id,
                "run_label": run_label,
                "comparison_axis": comparison_axis,
                "game": game,
                "architecture": architecture,
                "reason": reason,
                "invalid_moves": bucket["invalid_moves"],
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


def build_run_index(runs):
    rows = []
    for run in runs:
        rows.append(
            {
                "run_id": run["summary"].get("run_id"),
                "run_dir": str(run["run_dir"]),
                "run_label": run["experiment"].get("run_label"),
                "comparison_axis": run["experiment"].get("comparison_axis"),
                "is_section14_3": is_section14_3_axis(run["experiment"].get("comparison_axis")),
                "model": run["summary"].get("model"),
                "prompt_family": run["summary"].get("prompt_family"),
                "backend": run["summary"].get("backend") or run["manifest"].get("backend"),
                "completed_at": run["summary"].get("completed_at"),
            }
        )
    return rows


def build_architecture_overview(combined_rows):
    grouped = defaultdict(lambda: defaultdict(list))
    for row in combined_rows:
        if row.get("scope_type") != "architecture":
            continue
        key = (
            row.get("game"),
            row.get("experiment_group"),
            row.get("scope_id"),
        )
        grouped[key]["run_count"].append(row.get("run_id"))
        grouped[key]["win_rate"].append(row.get("win_rate"))
        grouped[key]["legality_rate"].append(row.get("legality_rate"))
        grouped[key]["hallucination_rate"].append(row.get("hallucination_rate"))
        grouped[key]["connect4_optimal_move_accuracy"].append(row.get("connect4_optimal_move_accuracy"))
        grouped[key]["blotto_nash_distance"].append(row.get("blotto_nash_distance"))

    rows = []
    for (game, experiment_group, architecture), metrics in sorted(grouped.items()):
        rows.append(
            {
                "game": game,
                "experiment_group": experiment_group,
                "architecture": architecture,
                "runs": len(set(metrics["run_count"])),
                "mean_win_rate": _mean(metrics["win_rate"]),
                "mean_legality_rate": _mean(metrics["legality_rate"]),
                "mean_hallucination_rate": _mean(metrics["hallucination_rate"]),
                "mean_connect4_optimal_move_accuracy": _mean(metrics["connect4_optimal_move_accuracy"]),
                "mean_blotto_nash_distance": _mean(metrics["blotto_nash_distance"]),
            }
        )
    return rows


def build_run_label_overview(combined_rows):
    grouped = defaultdict(lambda: defaultdict(list))
    for row in combined_rows:
        if row.get("scope_type") != "architecture":
            continue
        key = (
            row.get("run_label"),
            row.get("comparison_axis") or "baseline_or_smoke",
            row.get("game"),
            row.get("experiment_group"),
        )
        grouped[key]["run_ids"].append(row.get("run_id"))
        metric_name = PRIMARY_METRICS.get((row.get("game"), row.get("experiment_group")), "win_rate")
        grouped[key]["primary_metric"].append(row.get(metric_name))
        grouped[key]["legality_rate"].append(row.get("legality_rate"))
        grouped[key]["hallucination_rate"].append(row.get("hallucination_rate"))

    rows = []
    for (run_label, comparison_axis, game, experiment_group), metrics in sorted(grouped.items()):
        rows.append(
            {
                "run_label": run_label,
                "comparison_axis": comparison_axis,
                "game": game,
                "experiment_group": experiment_group,
                "runs": len(set(metrics["run_ids"])),
                "primary_metric_mean": _mean(metrics["primary_metric"]),
                "legality_rate_mean": _mean(metrics["legality_rate"]),
                "hallucination_rate_mean": _mean(metrics["hallucination_rate"]),
            }
        )
    return rows


def build_prompt_family_overview(combined_rows):
    grouped = defaultdict(lambda: defaultdict(list))
    for row in combined_rows:
        if row.get("scope_type") != "architecture":
            continue
        key = (
            row.get("prompt_family_id"),
            row.get("game"),
            row.get("experiment_group"),
        )
        grouped[key]["run_ids"].append(row.get("run_id"))
        grouped[key]["win_rate"].append(row.get("win_rate"))
        grouped[key]["legality_rate"].append(row.get("legality_rate"))
        grouped[key]["connect4_optimal_move_accuracy"].append(row.get("connect4_optimal_move_accuracy"))

    rows = []
    for (prompt_family_id, game, experiment_group), metrics in sorted(grouped.items()):
        rows.append(
            {
                "prompt_family_id": prompt_family_id,
                "game": game,
                "experiment_group": experiment_group,
                "runs": len(set(metrics["run_ids"])),
                "mean_win_rate": _mean(metrics["win_rate"]),
                "mean_legality_rate": _mean(metrics["legality_rate"]),
                "mean_connect4_optimal_move_accuracy": _mean(metrics["connect4_optimal_move_accuracy"]),
            }
        )
    return rows


def _format_metric(value):
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def write_report_bundle(output_dir, runs):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    combined_rows = build_combined_tables(runs)
    non_section_rows = [row for row in combined_rows if not row.get("is_section14_3")]
    non_section_runs = [run for run in runs if not is_section14_3_axis(run["experiment"].get("comparison_axis"))]
    hallucination_rows = build_hallucination_summary(non_section_runs)
    invalid_reason_rows = build_invalid_reason_summary(non_section_runs)
    claim_map = build_claim_map(non_section_runs, non_section_rows)
    run_index_rows = build_run_index(runs)
    architecture_overview_rows = build_architecture_overview(non_section_rows)
    run_label_rows = build_run_label_overview(non_section_rows)
    prompt_family_rows = build_prompt_family_overview(non_section_rows)

    _write_csv(output_dir / "combined_aggregate_tables.csv", combined_rows)
    _write_csv(output_dir / "non_section14_3_aggregate_tables.csv", non_section_rows)
    _write_csv(output_dir / "hallucination_patterns.csv", hallucination_rows)
    _write_csv(output_dir / "invalid_reason_summary.csv", invalid_reason_rows)
    _write_csv(output_dir / "experiment_run_index.csv", run_index_rows)
    _write_csv(output_dir / "architecture_overview.csv", architecture_overview_rows)
    _write_csv(output_dir / "run_label_overview.csv", run_label_rows)
    _write_csv(output_dir / "prompt_family_overview.csv", prompt_family_rows)
    (output_dir / "combined_runs.json").write_text(json.dumps(_serialize_runs(runs), indent=2), encoding="utf-8")
    (output_dir / "claim_map.json").write_text(json.dumps(claim_map, indent=2), encoding="utf-8")
    (output_dir / "report.md").write_text(
        build_markdown_report(
            runs=runs,
            combined_rows=combined_rows,
            non_section_rows=non_section_rows,
            hallucination_rows=hallucination_rows,
            invalid_reason_rows=invalid_reason_rows,
            claim_map=claim_map,
            run_index_rows=run_index_rows,
            architecture_overview_rows=architecture_overview_rows,
            run_label_rows=run_label_rows,
            prompt_family_rows=prompt_family_rows,
        ),
        encoding="utf-8",
    )

    plots_dir = output_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    for filename, svg in build_svg_plots(
        non_section_rows=non_section_rows,
        run_index_rows=run_index_rows,
        invalid_reason_rows=invalid_reason_rows,
    ).items():
        (plots_dir / filename).write_text(svg, encoding="utf-8")


def build_markdown_report(
    runs,
    combined_rows,
    non_section_rows,
    hallucination_rows,
    invalid_reason_rows,
    claim_map,
    run_index_rows,
    architecture_overview_rows,
    run_label_rows,
    prompt_family_rows,
):
    models = sorted({row.get("model") for row in combined_rows if row.get("model")})
    prompts = sorted({row.get("prompt_family_id") for row in combined_rows if row.get("prompt_family_id")})
    non_section_run_count = sum(1 for row in run_index_rows if not row.get("is_section14_3"))
    omitted_count = len(run_index_rows) - non_section_run_count
    lines = [
        "# Analysis Report",
        "",
        f"- Runs analyzed: {len(runs)}",
        f"- Non-Section 14.3 runs emphasized in tables and plots: {non_section_run_count}",
        f"- Section 14.3 runs intentionally omitted from most figures: {omitted_count}",
        f"- Models observed: {', '.join(models) if models else 'none'}",
        f"- Prompt families observed: {', '.join(prompts) if prompts else 'none'}",
        "",
        "## Summary Tables",
        "",
        "- `combined_aggregate_tables.csv` contains all aggregate rows across runs.",
        "- `non_section14_3_aggregate_tables.csv` isolates the broader experiment set and excludes the dense Section 14.3 suites.",
        "- `hallucination_patterns.csv` contains invalid-move pattern counts by game and architecture.",
        "- `invalid_reason_summary.csv` counts invalid-output reasons by run, game, and architecture.",
        "- `architecture_overview.csv`, `run_label_overview.csv`, and `prompt_family_overview.csv` summarize the non-14.3 experiments at different aggregation levels.",
        "",
        "## Narrative Findings",
        "",
    ]

    if claim_map:
        for claim in claim_map[:10]:
            lines.append(f"- {claim['claim']} Supported by runs: {', '.join(claim['run_ids'])}.")
    else:
        lines.append("- Insufficient run data to generate metric-backed findings.")

    comparison_lines = _build_architecture_comparisons(non_section_rows)
    if comparison_lines:
        lines.extend(["", "## Architecture Comparisons", ""])
        lines.extend([f"- {line}" for line in comparison_lines])

    if run_label_rows:
        lines.extend(["", "## Experiment Groups", ""])
        for row in run_label_rows[:8]:
            lines.append(
                "- "
                f"`{row['run_label']}` / `{row['game']}` / `{row['experiment_group']}` "
                f"has mean primary metric `{_format_metric(row['primary_metric_mean'])}` "
                f"with legality `{_format_metric(row['legality_rate_mean'])}`."
            )

    if prompt_family_rows:
        lines.extend(["", "## Prompt Coverage", ""])
        for row in prompt_family_rows[:6]:
            lines.append(
                "- "
                f"Prompt family `{row['prompt_family_id']}` on `{row['game']}` / `{row['experiment_group']}` "
                f"shows mean win rate `{_format_metric(row['mean_win_rate'])}` and legality `{_format_metric(row['mean_legality_rate'])}`."
            )

    lines.extend(
        [
            "",
            "## Coverage Notes",
            "",
            f"- Model scaling plots outside Section 14.3 {'are' if len({row.get('model') for row in non_section_rows if row.get('model')}) > 1 else 'are not'} supported by the current runs.",
            f"- Prompt comparison plots {'are' if len({row.get('prompt_family_id') for row in non_section_rows if row.get('prompt_family_id')}) > 1 else 'are not'} supported by the non-14.3 runs.",
            f"- Hallucination patterns were {'computed' if hallucination_rows else 'not available'} from turn logs.",
            f"- Invalid reason summaries were {'computed' if invalid_reason_rows else 'not available'} from turn logs.",
        ]
    )
    return "\n".join(lines) + "\n"


def build_svg_plots(non_section_rows, run_index_rows, invalid_reason_rows):
    plots = {}
    plots.update(_build_architecture_plots(non_section_rows))
    plots.update(_build_model_plots(non_section_rows))
    plots.update(_build_prompt_plots(non_section_rows))
    plots.update(_build_run_label_plots(non_section_rows))
    plots.update(_build_coverage_plots(run_index_rows))
    plots.update(_build_invalid_reason_plots(invalid_reason_rows))
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
            by_game[(game, metric)][architecture] = by_game[(game, metric)].get(architecture, []) + [value]

    for (game, metric), values in by_game.items():
        averages = {architecture: _mean(measures) for architecture, measures in values.items()}
        plots[f"architecture_{game}_{metric}.svg"] = _simple_bar_svg(
            title=f"Architecture Comparison: {game}",
            subtitle=f"Mean {metric} across non-14.3 runs",
            values=averages,
        )
    plots.update(_build_architecture_heatmaps(combined_rows))
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
    return {
        "model_scaling.svg": _simple_bar_svg(
            "Model Scaling Outside Section 14.3",
            averages,
            subtitle="Mean architecture win rate across non-14.3 runs",
        )
    }


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
    return {
        "prompt_comparison.svg": _simple_bar_svg(
            "Prompt Comparison",
            averages,
            subtitle="Mean architecture win rate across non-14.3 prompt runs",
        )
    }


def _build_run_label_plots(combined_rows):
    plots = {}
    values = defaultdict(list)
    for row in combined_rows:
        if row.get("scope_type") != "architecture":
            continue
        metric_name = PRIMARY_METRICS.get((row.get("game"), row.get("experiment_group")), "win_rate")
        metric_value = row.get(metric_name)
        if metric_value is None:
            continue
        values[f"{row.get('run_label')}|{row.get('game')}|{row.get('experiment_group')}"].append(metric_value)

    averaged = {label: _mean(metric_values) for label, metric_values in values.items()}
    top_labels = dict(sorted(averaged.items(), key=lambda item: item[1], reverse=True)[:10])
    if top_labels:
        plots["experiment_group_primary_metric_top10.svg"] = _simple_bar_svg(
            "Top Non-14.3 Experiment Groups",
            top_labels,
            subtitle="Highest mean primary metrics across baseline, prompt, difficulty, and final runs",
        )
    return plots


def _build_coverage_plots(run_index_rows):
    plots = {}
    non_section_rows = [row for row in run_index_rows if not row.get("is_section14_3")]
    by_run_label = defaultdict(int)
    by_axis = defaultdict(int)
    for row in non_section_rows:
        by_run_label[row.get("run_label") or "unlabeled"] += 1
        by_axis[row.get("comparison_axis") or "baseline_or_smoke"] += 1
    if by_run_label:
        plots["run_label_coverage.svg"] = _simple_bar_svg(
            "Run Coverage by Label",
            dict(sorted(by_run_label.items(), key=lambda item: (-item[1], item[0]))[:12]),
            subtitle="Completed non-14.3 runs included in the general analysis bundle",
        )
    if by_axis:
        plots["comparison_axis_coverage.svg"] = _simple_bar_svg(
            "Run Coverage by Comparison Axis",
            dict(sorted(by_axis.items(), key=lambda item: (-item[1], item[0]))),
            subtitle="Section 14.3 omitted from this coverage chart",
        )
    return plots


def _build_invalid_reason_plots(invalid_reason_rows):
    plots = {}
    if not invalid_reason_rows:
        plots["invalid_reason_counts.svg"] = _placeholder_svg("Invalid Move Reasons", "No invalid moves recorded")
        return plots

    totals = defaultdict(int)
    for row in invalid_reason_rows:
        totals[row["reason"]] += int(row["invalid_moves"])

    plots["invalid_reason_counts.svg"] = _simple_bar_svg(
        "Invalid Move Reasons",
        dict(sorted(totals.items(), key=lambda item: (-item[1], item[0]))[:10]),
        subtitle="Non-14.3 runs only",
    )
    return plots


def _build_architecture_heatmaps(combined_rows):
    plots = {}
    supported = [
        ("blotto", "internal_ai_tournament", "win_rate"),
        ("blotto", "blotto_vs_bots", "win_rate"),
        ("connect4", "internal_ai_tournament", "win_rate"),
        ("connect4", "connect4_oracle_accuracy", "connect4_optimal_move_accuracy"),
    ]
    for game, experiment_group, metric_name in supported:
        rows = [
            row
            for row in combined_rows
            if row.get("scope_type") == "architecture"
            and row.get("game") == game
            and row.get("experiment_group") == experiment_group
            and row.get(metric_name) is not None
        ]
        if not rows:
            continue
        architectures = sorted({row["scope_id"] for row in rows})
        run_labels = sorted({row.get("run_label") or "unlabeled" for row in rows})
        matrix = []
        annotations = []
        for architecture in architectures:
            matrix_row = []
            annotation_row = []
            for run_label in run_labels:
                matching_values = [
                    row.get(metric_name)
                    for row in rows
                    if row["scope_id"] == architecture and (row.get("run_label") or "unlabeled") == run_label
                ]
                value = _mean(matching_values)
                matrix_row.append(value)
                annotation_row.append("n/a" if value is None else f"{value:.2f}")
            matrix.append(matrix_row)
            annotations.append(annotation_row)
        rendered = render_heatmap_svg(
            title=f"{game} {experiment_group}",
            subtitle=f"Mean {metric_name} by architecture and run label",
            labels=run_labels,
            matrix=matrix,
            annotations=annotations,
            note="rows are architectures",
            x_labels=run_labels,
            y_labels=architectures,
        )
        if rendered is not None:
            plots[f"{game}_{experiment_group}_{metric_name}_heatmap.svg"] = rendered
        else:
            plots[f"{game}_{experiment_group}_{metric_name}_heatmap.svg"] = _placeholder_svg(
                f"{game} {experiment_group}",
                "Matplotlib not available for heatmap rendering",
            )
    return plots


def _simple_bar_svg(title, values, subtitle=""):
    rendered = render_bar_chart_svg(title=title, values=values, subtitle=subtitle)
    if rendered is not None:
        return rendered

    items = list(values.items())
    width = 640
    height = 360
    margin = 40
    chart_height = 220
    bar_width = max(40, int((width - 2 * margin) / max(len(items), 1)) - 20)
    max_value = max(values.values()) if values else 1
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
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


def _mean(values):
    cleaned = [value for value in values if value is not None and value != ""]
    if not cleaned:
        return None
    return sum(cleaned) / len(cleaned)


def is_section14_3_axis(comparison_axis):
    return comparison_axis in SECTION14_3_COMPARISON_AXES


def _placeholder_svg(title, message):
    rendered = render_placeholder_svg(title=title, message=message)
    if rendered is not None:
        return rendered

    return "\n".join(
        [
            '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="240">',
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
                "experiment": run["experiment"],
                "metrics": run["metrics"],
                "turn_record_count": len(run["turn_records"]),
            }
        )
    return serialized
