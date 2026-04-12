import argparse
import csv
import json
import shutil
from collections import defaultdict
from pathlib import Path

try:
    from .report_section14_3 import (
        SECTION14_3_AXES,
        build_leaderboard,
        build_section14_3_rows,
        discover_section14_3_runs,
    )
except ImportError:
    from report_section14_3 import (
        SECTION14_3_AXES,
        build_leaderboard,
        build_section14_3_rows,
        discover_section14_3_runs,
    )


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PRIMARY_METRICS = {
    ("blotto", "internal_ai_tournament"): "win_rate",
    ("blotto", "blotto_vs_bots"): "win_rate",
    ("connect4", "internal_ai_tournament"): "win_rate",
    ("connect4", "connect4_oracle_accuracy"): "connect4_optimal_move_accuracy",
}
KEY_ARTIFACTS = [
    Path("config/benchmark.json"),
    Path("config/experiment.json"),
    Path("config/architectures.json"),
    Path("config/model.json"),
    Path("config/prompt.json"),
    Path("config/prompt_catalog.json"),
    Path("metadata/run_manifest.json"),
    Path("metadata/reproducibility.json"),
    Path("summaries/summary.json"),
    Path("summaries/metrics.json"),
    Path("summaries/architecture_summaries.csv"),
    Path("summaries/aggregate_tables.csv"),
    Path("summaries/model_summaries.csv"),
    Path("summaries/prompt_summaries.csv"),
    Path("summaries/game_outcomes.csv"),
    Path("logs/results.txt"),
]


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_text(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


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


def discover_key_section14_3_runs(experiments_root):
    all_runs = discover_section14_3_runs(experiments_root)
    grouped = defaultdict(list)

    for run_dir in all_runs:
        experiment = load_json(run_dir / "config" / "experiment.json")
        grouped[SECTION14_3_AXES[experiment["comparison_axis"]]].append(run_dir)

    selected = []
    for suite, run_dirs in sorted(grouped.items()):
        selected.append(sorted(run_dirs)[-1])
    return selected


def build_topline_table(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["suite"], row["game"], row["experiment_group"])].append(row)

    topline = []
    for key, group_rows in sorted(grouped.items()):
        suite, game, experiment_group = key
        metric = PRIMARY_METRICS.get((game, experiment_group), "win_rate")
        sorted_rows = sorted(
            group_rows,
            key=lambda row: (
                row.get(metric) is None,
                -(row.get(metric) or 0.0),
                row["architecture_id"],
            ),
        )
        best = sorted_rows[0]
        topline.append(
            {
                "suite": suite,
                "game": game,
                "experiment_group": experiment_group,
                "primary_metric": metric,
                "best_architecture_id": best["architecture_id"],
                "best_architecture_name": best["architecture_name"],
                "best_composition_label": best["composition_label"],
                "best_primary_metric_value": best.get(metric),
                "best_win_rate": best.get("win_rate"),
                "best_hallucination_rate": best.get("hallucination_rate"),
                "best_connect4_optimal_move_accuracy": best.get("connect4_optimal_move_accuracy"),
                "best_blotto_nash_distance": best.get("blotto_nash_distance"),
            }
        )
    return topline


def build_limitations(selected_runs):
    limitations = [
        {
            "title": "Depth-limited oracle limitations",
            "detail": (
                "Connect 4 oracle accuracy is measured against the repository's depth-limited minimax solver. "
                "That is a strong baseline, but it is not a perfect solver, so optimal-move accuracy should be interpreted "
                "as agreement with this oracle rather than proof of globally optimal play."
            ),
        },
        {
            "title": "Single-model backend limitations",
            "detail": (
                "The completed Section 14.3 sweeps stay within the Qwen/Ollama runtime family. "
                "This isolates architecture, parameter-count, and quantization effects, but it does not establish "
                "that the same trends will transfer to other model families or hosted APIs."
            ),
        },
        {
            "title": "Prompt sensitivity",
            "detail": (
                "The final Section 14.3 deliverables summarize runs executed with `structured_reasoning_v1`. "
                "Prompt wording materially affects legality, consistency, and strategy quality, so the reported rankings "
                "should be treated as prompt-conditional rather than universally stable."
            ),
        },
        {
            "title": "Cost and runtime constraints",
            "detail": (
                "Mixed-team ensembles increase wall-clock runtime and local hardware demand because each move may require "
                "multiple model invocations. The benchmark records accuracy and win-rate tradeoffs, but it does not yet "
                "normalize outcomes by latency, GPU memory, or token cost."
            ),
        },
    ]

    backend_names = sorted(
        {
            load_json(run_dir / "metadata" / "run_manifest.json").get("backend")
            for run_dir in selected_runs
            if (run_dir / "metadata" / "run_manifest.json").exists()
        }
    )
    return {
        "backends_observed": backend_names,
        "items": limitations,
    }


def _format_metric(value):
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def build_final_report(selected_runs, rows, topline_rows, limitations):
    run_manifest_rows = []
    for run_dir in selected_runs:
        manifest = load_json(run_dir / "metadata" / "run_manifest.json")
        experiment = load_json(run_dir / "config" / "experiment.json")
        run_manifest_rows.append(
            {
                "run_id": manifest["run_id"],
                "suite": SECTION14_3_AXES[experiment["comparison_axis"]],
                "run_label": experiment.get("run_label"),
                "model_group_id": experiment.get("model_group_id"),
                "prompt_family_id": manifest.get("prompt_family_id"),
                "backend": manifest.get("backend"),
            }
        )

    lines = [
        "# Section 15 Final Deliverables",
        "",
        "## Project Objective",
        "",
        (
            "This benchmark evaluates whether multi-agent LLM orchestration improves strategic decision-making in adversarial games. "
            "The implemented system compares single-turn parallel voting and hierarchical role-based teams on Colonel Blotto and Connect 4, "
            "then measures win rate, legality, hallucination rate, consistency, Blotto Nash-distance, and Connect 4 oracle agreement."
        ),
        "",
        "## Included Experimental Runs",
        "",
    ]

    for row in run_manifest_rows:
        lines.append(
            f"- `{row['suite']}`: `{row['run_id']}` using `{row['model_group_id']}` with prompt family `{row['prompt_family_id']}` on backend `{row['backend']}`."
        )

    lines.extend(
        [
            "",
            "## Final Results",
            "",
        ]
    )

    for row in topline_rows:
        lines.append(
            f"- `{row['suite']}` / `{row['game']}` / `{row['experiment_group']}`: "
            f"`{row['best_architecture_id']}` led on `{row['primary_metric']}` with value `{_format_metric(row['best_primary_metric_value'])}`."
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            (
                "The final tables and figures in this bundle are derived directly from the stored run summaries under `reports/runs/experiment_runs/run_*/`. "
                "They are intended to support the proposal's Section 14.3 claims about model-scale and quantization effects on multi-agent orchestration."
            ),
            "",
            "## Limitations",
            "",
        ]
    )

    for item in limitations["items"]:
        lines.append(f"- {item['title']}: {item['detail']}")

    lines.extend(
        [
            "",
            "## Bundle Contents",
            "",
            "- `RUN_INSTRUCTIONS.md`: reproducible commands for rerunning the benchmark and regenerating this bundle.",
            "- `tables/`: final CSV and JSON summary tables for the selected Section 14.3 runs.",
            "- `figures/`: SVG charts for the key experiment groups.",
            "- `key_runs/`: copied configs, metadata, summaries, and human-readable logs for the selected runs.",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def build_run_instructions(selected_runs):
    lines = [
        "# Reproducible Run Instructions",
        "",
        "## Environment",
        "",
        "```bash",
        "python3 -m venv .venv",
        "source .venv/bin/activate",
        "pip install --upgrade pip",
        "pip install -r requirements.txt",
        "```",
        "",
        "Start Ollama and ensure the required Qwen models are installed:",
        "",
        "```bash",
        "bash tools/install_qwen_models.sh section14_3",
        "ollama serve",
        "```",
        "",
        "## Section 14.3 Runs",
        "",
    ]

    seen_labels = set()
    for run_dir in selected_runs:
        manifest = load_json(run_dir / "metadata" / "run_manifest.json")
        config_path = manifest.get("config_path")
        if config_path and config_path not in seen_labels:
            seen_labels.add(config_path)
            lines.extend(
                [
                    "```bash",
                    f"python3 tools/run_benchmark.py --config {config_path}",
                    "```",
                    "",
                ]
            )

    lines.extend(
        [
            "## Regenerate Final Deliverables",
            "",
            "```bash",
            "python3 tools/generate_final_deliverables.py",
            "```",
            "",
            "## Selected Run IDs",
            "",
        ]
    )

    for run_dir in selected_runs:
        lines.append(f"- `{run_dir.name}`")

    return "\n".join(lines) + "\n"


def copy_key_run_artifacts(selected_runs, output_dir):
    manifest_rows = []
    for run_dir in selected_runs:
        destination = Path(output_dir) / "key_runs" / run_dir.name
        copied = []
        for relative_path in KEY_ARTIFACTS:
            source = run_dir / relative_path
            if not source.exists():
                continue
            target = destination / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            copied.append(str(relative_path))
        manifest_rows.append({"run_id": run_dir.name, "copied_artifacts": copied})
    return manifest_rows


def _sanitize_filename(value):
    return "".join(char if char.isalnum() or char in {"_", "-", "."} else "_" for char in value)


def _coerce_float(value):
    if value in (None, ""):
        return None
    return float(value)


def _mean(values):
    values = [value for value in values if value is not None]
    if not values:
        return None
    return sum(values) / len(values)


def _bar_chart_svg(title, rows, metric):
    width = 920
    height = 420
    margin = 50
    chart_height = 240
    label_gap = 24
    items = [(row["architecture_id"], row.get(metric) or 0.0) for row in rows]
    max_value = max((value for _, value in items), default=1.0)
    if max_value <= 0:
        max_value = 1.0

    bar_width = max(36, int((width - 2 * margin) / max(len(items), 1)) - 16)
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
        f'<text x="{width / 2}" y="28" text-anchor="middle" font-size="20">{title}</text>',
    ]

    for index, (label, value) in enumerate(items):
        x = margin + index * (bar_width + 16)
        bar_height = (value / max_value) * chart_height
        y = height - margin - label_gap - bar_height
        lines.append(f'<rect x="{x}" y="{y}" width="{bar_width}" height="{bar_height}" fill="#1f6aa5" />')
        lines.append(f'<text x="{x + bar_width / 2}" y="{y - 8}" text-anchor="middle" font-size="11">{value:.3f}</text>')
        lines.append(f'<text x="{x + bar_width / 2}" y="{height - margin}" text-anchor="middle" font-size="10">{label}</text>')

    lines.append("</svg>")
    return "\n".join(lines)


def _placeholder_svg(title, message):
    return "\n".join(
        [
            '<svg xmlns="http://www.w3.org/2000/svg" width="920" height="260">',
            '<rect width="920" height="260" fill="#fcfbf7" />',
            f'<text x="460" y="40" text-anchor="middle" font-size="20" font-family="Georgia, serif">{title}</text>',
            f'<text x="460" y="132" text-anchor="middle" font-size="14">{message}</text>',
            "</svg>",
        ]
    )


def _scatter_plot_svg(title, rows, x_metric, y_metric, x_label, y_label, invert_x=False):
    width = 920
    height = 520
    margin_left = 90
    margin_right = 40
    margin_top = 60
    margin_bottom = 80
    plot_width = width - margin_left - margin_right
    plot_height = height - margin_top - margin_bottom
    palette = {"parallel": "#1f6aa5", "hierarchical": "#c65f28", "single": "#3a8f5a"}

    points = []
    for row in rows:
        x_value = _coerce_float(row.get(x_metric))
        y_value = _coerce_float(row.get(y_metric))
        if x_value is None or y_value is None:
            continue
        points.append(
            {
                "label": row["architecture_id"],
                "type": row["architecture_type"],
                "x": x_value,
                "y": y_value,
            }
        )

    if not points:
        return _placeholder_svg(title, "Insufficient data")

    x_values = [point["x"] for point in points]
    y_values = [point["y"] for point in points]
    x_min = min(x_values)
    x_max = max(x_values)
    y_min = min(y_values)
    y_max = max(y_values)

    if x_min == x_max:
        x_min -= 1.0
        x_max += 1.0
    if y_min == y_max:
        y_min -= 1.0
        y_max += 1.0

    x_pad = (x_max - x_min) * 0.08
    y_pad = (y_max - y_min) * 0.12
    x_min -= x_pad
    x_max += x_pad
    y_min -= y_pad
    y_max += y_pad

    def project_x(value):
        fraction = (value - x_min) / (x_max - x_min)
        if invert_x:
            fraction = 1.0 - fraction
        return margin_left + fraction * plot_width

    def project_y(value):
        fraction = (value - y_min) / (y_max - y_min)
        return margin_top + (1.0 - fraction) * plot_height

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
        f'<rect width="{width}" height="{height}" fill="#fcfbf7" />',
        f'<text x="{width / 2}" y="28" text-anchor="middle" font-size="20" font-family="Georgia, serif">{title}</text>',
        f'<line x1="{margin_left}" y1="{margin_top}" x2="{margin_left}" y2="{margin_top + plot_height}" stroke="#333" stroke-width="1.5" />',
        f'<line x1="{margin_left}" y1="{margin_top + plot_height}" x2="{margin_left + plot_width}" y2="{margin_top + plot_height}" stroke="#333" stroke-width="1.5" />',
        f'<text x="{margin_left + plot_width / 2}" y="{height - 24}" text-anchor="middle" font-size="14">{x_label}</text>',
        f'<text x="24" y="{margin_top + plot_height / 2}" text-anchor="middle" font-size="14" transform="rotate(-90 24 {margin_top + plot_height / 2})">{y_label}</text>',
    ]

    for tick in range(5):
        x_tick_value = x_min + ((x_max - x_min) * tick / 4)
        x_tick_position = project_x(x_tick_value)
        y_tick_value = y_min + ((y_max - y_min) * tick / 4)
        y_tick_position = project_y(y_tick_value)
        lines.append(
            f'<line x1="{x_tick_position}" y1="{margin_top}" x2="{x_tick_position}" y2="{margin_top + plot_height}" stroke="#d8d3c8" stroke-width="1" />'
        )
        lines.append(
            f'<line x1="{margin_left}" y1="{y_tick_position}" x2="{margin_left + plot_width}" y2="{y_tick_position}" stroke="#d8d3c8" stroke-width="1" />'
        )
        lines.append(
            f'<text x="{x_tick_position}" y="{margin_top + plot_height + 18}" text-anchor="middle" font-size="11">{x_tick_value:.2f}</text>'
        )
        lines.append(
            f'<text x="{margin_left - 10}" y="{y_tick_position + 4}" text-anchor="end" font-size="11">{y_tick_value:.2f}</text>'
        )

    for point in points:
        color = palette.get(point["type"], "#555")
        x = project_x(point["x"])
        y = project_y(point["y"])
        lines.append(f'<circle cx="{x}" cy="{y}" r="6" fill="{color}" opacity="0.9" />')
        lines.append(f'<text x="{x + 8}" y="{y - 8}" font-size="11">{point["label"]}</text>')

    legend_y = height - 48
    legend_x = margin_left
    for index, (label, color) in enumerate(palette.items()):
        x = legend_x + index * 140
        lines.append(f'<circle cx="{x}" cy="{legend_y}" r="5" fill="{color}" />')
        lines.append(f'<text x="{x + 10}" y="{legend_y + 4}" font-size="11">{label}</text>')

    lines.append("</svg>")
    return "\n".join(lines)


def _grouped_bar_chart_svg(title, rows, category_metric, value_metric, category_label, value_label, lower_is_better=False):
    width = 920
    height = 460
    margin = 60
    chart_height = 250
    label_gap = 44
    palette = {"parallel": "#1f6aa5", "hierarchical": "#c65f28", "single": "#3a8f5a"}

    grouped = defaultdict(list)
    for row in rows:
        value = _coerce_float(row.get(value_metric))
        if value is None:
            continue
        grouped[row[category_metric]].append(value)

    items = []
    for category, values in sorted(grouped.items()):
        mean_value = _mean(values)
        if mean_value is not None:
            items.append((category, mean_value))

    if not items:
        return _placeholder_svg(title, "Insufficient data")

    max_value = max(value for _, value in items)
    if max_value <= 0:
        max_value = 1.0

    bar_width = max(60, int((width - 2 * margin) / max(len(items), 1)) - 36)
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
        f'<rect width="{width}" height="{height}" fill="#fcfbf7" />',
        f'<text x="{width / 2}" y="28" text-anchor="middle" font-size="20" font-family="Georgia, serif">{title}</text>',
        f'<text x="{width / 2}" y="{height - 20}" text-anchor="middle" font-size="13">{category_label}</text>',
        f'<text x="24" y="{margin + chart_height / 2}" text-anchor="middle" font-size="13" transform="rotate(-90 24 {margin + chart_height / 2})">{value_label}</text>',
    ]

    for tick in range(5):
        value = max_value * tick / 4
        y = height - margin - label_gap - ((value / max_value) * chart_height)
        lines.append(f'<line x1="{margin}" y1="{y}" x2="{width - margin}" y2="{y}" stroke="#d8d3c8" stroke-width="1" />')
        lines.append(f'<text x="{margin - 10}" y="{y + 4}" text-anchor="end" font-size="11">{value:.2f}</text>')

    for index, (category, value) in enumerate(items):
        x = margin + index * (bar_width + 36)
        bar_height = (value / max_value) * chart_height
        y = height - margin - label_gap - bar_height
        color = palette.get(category, "#555")
        lines.append(f'<rect x="{x}" y="{y}" width="{bar_width}" height="{bar_height}" fill="{color}" />')
        lines.append(f'<text x="{x + bar_width / 2}" y="{y - 8}" text-anchor="middle" font-size="11">{value:.3f}</text>')
        direction = "lower is better" if lower_is_better else "higher is better"
        lines.append(f'<text x="{x + bar_width / 2}" y="{height - margin + 4}" text-anchor="middle" font-size="11">{category}</text>')
        lines.append(f'<text x="{width - margin}" y="48" text-anchor="end" font-size="11">{direction}</text>')

    lines.append("</svg>")
    return "\n".join(lines)


def build_figures(rows):
    figures = {}
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["suite"], row["game"], row["experiment_group"])].append(row)

    for key, group_rows in sorted(grouped.items()):
        suite, game, experiment_group = key
        metric = PRIMARY_METRICS.get((game, experiment_group), "win_rate")
        title = f"{suite}: {game} / {experiment_group} ({metric})"
        filename = _sanitize_filename(f"{suite}_{game}_{experiment_group}_{metric}.svg")
        figures[filename] = _bar_chart_svg(title, group_rows, metric)

    figures["section14_3_connect4_internal_consistency_vs_win_rate.svg"] = _scatter_plot_svg(
        "Connect 4 Internal Tournament: Consistency vs Win Rate",
        [
            row
            for row in rows
            if row["game"] == "connect4" and row["experiment_group"] == "internal_ai_tournament"
        ],
        "consistency_per_state_agreement",
        "win_rate",
        "Per-state agreement",
        "Win rate",
    )
    figures["section14_3_connect4_oracle_accuracy_vs_blunder_rate.svg"] = _scatter_plot_svg(
        "Connect 4 Oracle Test: Accuracy vs Blunder Rate",
        [
            row
            for row in rows
            if row["game"] == "connect4" and row["experiment_group"] == "connect4_oracle_accuracy"
        ],
        "blunder_rate",
        "connect4_optimal_move_accuracy",
        "Blunder rate",
        "Oracle accuracy",
        invert_x=True,
    )
    figures["section14_3_blotto_win_rate_vs_nash_distance.svg"] = _scatter_plot_svg(
        "Blotto: Win Rate vs Nash Distance",
        [row for row in rows if row["game"] == "blotto"],
        "blotto_nash_distance",
        "win_rate",
        "Blotto Nash distance",
        "Win rate",
        invert_x=True,
    )
    figures["section14_3_hallucination_rate_by_architecture_type.svg"] = _grouped_bar_chart_svg(
        "Hallucination Rate by Architecture Type",
        rows,
        "architecture_type",
        "hallucination_rate",
        "Architecture type",
        "Mean hallucination rate",
        lower_is_better=True,
    )
    return figures


def build_deliverables(experiments_root, output_dir):
    selected_runs = discover_key_section14_3_runs(experiments_root)
    rows = build_section14_3_rows(selected_runs)
    leaderboard = build_leaderboard(rows)
    topline_rows = build_topline_table(rows)
    limitations = build_limitations(selected_runs)

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    copied_artifacts = copy_key_run_artifacts(selected_runs, output_dir)
    figures = build_figures(rows)

    write_json(
        output_dir / "tables" / "section14_3_summary.json",
        {
            "section": "15",
            "selected_runs": [run_dir.name for run_dir in selected_runs],
            "rows": rows,
        },
    )
    write_csv_rows(output_dir / "tables" / "section14_3_summary.csv", rows)
    write_csv_rows(output_dir / "tables" / "section14_3_leaderboard.csv", leaderboard)
    write_csv_rows(output_dir / "tables" / "section15_topline_results.csv", topline_rows)
    write_json(output_dir / "tables" / "section15_limitations.json", limitations)
    write_json(output_dir / "tables" / "key_run_artifacts.json", copied_artifacts)

    for filename, svg in figures.items():
        write_text(output_dir / "figures" / filename, svg)

    write_text(output_dir / "RUN_INSTRUCTIONS.md", build_run_instructions(selected_runs))
    write_text(output_dir / "FINAL_REPORT.md", build_final_report(selected_runs, rows, topline_rows, limitations))

    return {
        "selected_runs": [run_dir.name for run_dir in selected_runs],
        "row_count": len(rows),
        "figure_count": len(figures),
        "output_dir": str(output_dir),
    }


def main():
    parser = argparse.ArgumentParser(description="Build Section 15 final deliverables from completed Section 14.3 runs.")
    parser.add_argument(
        "--experiments-root",
        default=str(PROJECT_ROOT / "experiments"),
        help="Directory containing run_* experiment folders.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "deliverables" / "final"),
        help="Directory for the generated final deliverables bundle.",
    )
    args = parser.parse_args()

    result = build_deliverables(args.experiments_root, args.output_dir)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
