import argparse
import csv
import json
import math
import shutil
from collections import defaultdict
from html import escape
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


def load_csv(path):
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


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


def _escape(value):
    return escape(str(value), quote=True)


def _svg_style_block():
    return """
<defs>
  <linearGradient id="bgGradient" x1="0%" x2="100%" y1="0%" y2="100%">
    <stop offset="0%" stop-color="#f6f1e8" />
    <stop offset="100%" stop-color="#fffdf9" />
  </linearGradient>
</defs>
<style>
  .title { font: 700 24px Georgia, serif; fill: #1f1b16; }
  .subtitle { font: 12px Menlo, Consolas, monospace; fill: #6c6256; letter-spacing: 0.04em; text-transform: uppercase; }
  .axis-label { font: 13px Menlo, Consolas, monospace; fill: #4d4439; }
  .tick { font: 11px Menlo, Consolas, monospace; fill: #6c6256; }
  .cell-label { font: 11px Menlo, Consolas, monospace; fill: #2f2a24; }
  .note { font: 11px Menlo, Consolas, monospace; fill: #7e7467; }
</style>
""".strip()


def _svg_open(width, height, title, subtitle):
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        _svg_style_block(),
        f'<rect width="{width}" height="{height}" rx="24" fill="url(#bgGradient)" />',
        f'<text class="title" x="36" y="42">{_escape(title)}</text>',
        f'<text class="subtitle" x="36" y="64">{_escape(subtitle)}</text>',
    ]
    return lines


def _placeholder_svg(title, message, subtitle="Section 14.3 figure"):
    lines = _svg_open(960, 260, title, subtitle)
    lines.extend(
        [
            '<rect x="34" y="86" width="892" height="136" rx="18" fill="#f1ebe1" stroke="#d9cfbf" />',
            f'<text class="axis-label" x="480" y="158" text-anchor="middle">{_escape(message)}</text>',
            "</svg>",
        ]
    )
    return "\n".join(lines)


def _color_mix(start_hex, end_hex, fraction):
    fraction = max(0.0, min(1.0, fraction))
    start = tuple(int(start_hex[index : index + 2], 16) for index in (1, 3, 5))
    end = tuple(int(end_hex[index : index + 2], 16) for index in (1, 3, 5))
    mixed = tuple(round(start_value + (end_value - start_value) * fraction) for start_value, end_value in zip(start, end))
    return "#" + "".join(f"{value:02x}" for value in mixed)


def _sequential_heat_color(value):
    if value is None:
        return "#ece4d7"
    if value <= 0.5:
        return _color_mix("#aa3f2d", "#efe4d0", value / 0.5)
    return _color_mix("#efe4d0", "#2c7a56", (value - 0.5) / 0.5)


def _ordered_architecture_rows(rows):
    return sorted(
        rows,
        key=lambda row: (
            row.get("architecture_type", ""),
            row.get("composition_quality_score") is None,
            row.get("composition_quality_score") or 0.0,
            row["architecture_id"],
        ),
    )


def _format_quality_score(value):
    if value is None:
        return "n/a"
    return f"{value:.2f}"


def _build_matchup_heatmap_svg(title, subtitle, architecture_rows, matchup_rows):
    if not architecture_rows or not matchup_rows:
        return _placeholder_svg(title, "Insufficient internal tournament data", subtitle)

    ordered_rows = _ordered_architecture_rows(architecture_rows)
    labels = [row["architecture_id"] for row in ordered_rows]
    totals = defaultdict(int)
    scores = defaultdict(float)
    for matchup in matchup_rows:
        scores[(matchup["row_id"], matchup["col_id"])] += matchup["score"]
        totals[(matchup["row_id"], matchup["col_id"])] += matchup["count"]

    if not totals:
        return _placeholder_svg(title, "No pairwise outcomes available", subtitle)

    width = 1040
    height = 180 + (len(labels) * 64)
    margin_left = 260
    margin_top = 150
    cell = 64
    lines = _svg_open(width, height, title, subtitle)
    lines.append(f'<text class="note" x="{width - 36}" y="42" text-anchor="end">cell value = expected head-to-head score</text>')

    for index, label in enumerate(labels):
        x = margin_left + index * cell + cell / 2
        y = margin_top + index * cell + cell / 2
        lines.append(f'<text class="tick" x="{x}" y="{margin_top - 16}" text-anchor="middle" transform="rotate(-35 {x} {margin_top - 16})">{_escape(label)}</text>')
        lines.append(f'<text class="tick" x="{margin_left - 14}" y="{y + 4}" text-anchor="end">{_escape(label)}</text>')

    for row_index, row_label in enumerate(labels):
        for col_index, col_label in enumerate(labels):
            x = margin_left + col_index * cell
            y = margin_top + row_index * cell
            if row_label == col_label:
                fill = "#e7ded0"
                text = "self"
            else:
                total = totals.get((row_label, col_label), 0)
                value = (scores[(row_label, col_label)] / total) if total else None
                fill = _sequential_heat_color(value)
                text = "n/a" if value is None else f"{value:.2f}"
            lines.append(f'<rect x="{x}" y="{y}" width="{cell - 4}" height="{cell - 4}" rx="10" fill="{fill}" stroke="#f8f4ec" />')
            lines.append(f'<text class="cell-label" x="{x + (cell - 4) / 2}" y="{y + cell / 2}" text-anchor="middle">{_escape(text)}</text>')

    legend_x = margin_left
    legend_y = height - 34
    for step in range(5):
        value = step / 4
        x = legend_x + step * 120
        lines.append(f'<rect x="{x}" y="{legend_y}" width="96" height="16" rx="8" fill="{_sequential_heat_color(value)}" />')
        lines.append(f'<text class="tick" x="{x + 48}" y="{legend_y + 31}" text-anchor="middle">{value:.2f}</text>')

    lines.append("</svg>")
    return "\n".join(lines)


def _build_quality_progression_svg(title, subtitle, rows, metric, y_label):
    filtered_rows = [
        row
        for row in rows
        if row.get("composition_quality_score") is not None and _coerce_float(row.get(metric)) is not None
    ]
    if not filtered_rows:
        return _placeholder_svg(title, "Insufficient quality progression data", subtitle)

    grouped = defaultdict(list)
    for row in filtered_rows:
        grouped[row["architecture_type"]].append(
            {
                "label": row["architecture_id"],
                "x": row["composition_quality_score"],
                "y": _coerce_float(row.get(metric)),
            }
        )

    width = 980
    height = 560
    margin_left = 86
    margin_right = 42
    margin_top = 110
    margin_bottom = 82
    plot_width = width - margin_left - margin_right
    plot_height = height - margin_top - margin_bottom
    palette = {"parallel": "#215f8b", "hierarchical": "#c25b32"}

    x_values = [point["x"] for points in grouped.values() for point in points]
    y_values = [point["y"] for points in grouped.values() for point in points]
    x_min = min(x_values) - 0.15
    x_max = max(x_values) + 0.15
    y_min = min(0.0, min(y_values) * 0.95)
    y_max = max(y_values) * 1.08 if max(y_values) != 0 else 1.0
    if math.isclose(y_min, y_max):
        y_max = y_min + 1.0

    def project_x(value):
        return margin_left + ((value - x_min) / (x_max - x_min)) * plot_width

    def project_y(value):
        return margin_top + (1.0 - ((value - y_min) / (y_max - y_min))) * plot_height

    lines = _svg_open(width, height, title, subtitle)
    lines.extend(
        [
            f'<line x1="{margin_left}" y1="{margin_top}" x2="{margin_left}" y2="{margin_top + plot_height}" stroke="#53483c" stroke-width="1.4" />',
            f'<line x1="{margin_left}" y1="{margin_top + plot_height}" x2="{margin_left + plot_width}" y2="{margin_top + plot_height}" stroke="#53483c" stroke-width="1.4" />',
            f'<text class="axis-label" x="{margin_left + plot_width / 2}" y="{height - 24}" text-anchor="middle">Mean team quality score (low/q4=1, med/q8=2, high/f16=3)</text>',
            f'<text class="axis-label" x="26" y="{margin_top + plot_height / 2}" text-anchor="middle" transform="rotate(-90 26 {margin_top + plot_height / 2})">{_escape(y_label)}</text>',
        ]
    )

    for tick in range(5):
        x_value = x_min + ((x_max - x_min) * tick / 4)
        y_value = y_min + ((y_max - y_min) * tick / 4)
        x = project_x(x_value)
        y = project_y(y_value)
        lines.append(f'<line x1="{x}" y1="{margin_top}" x2="{x}" y2="{margin_top + plot_height}" stroke="#ddd2c4" stroke-width="1" />')
        lines.append(f'<line x1="{margin_left}" y1="{y}" x2="{margin_left + plot_width}" y2="{y}" stroke="#ddd2c4" stroke-width="1" />')
        lines.append(f'<text class="tick" x="{x}" y="{margin_top + plot_height + 20}" text-anchor="middle">{x_value:.2f}</text>')
        lines.append(f'<text class="tick" x="{margin_left - 10}" y="{y + 4}" text-anchor="end">{y_value:.2f}</text>')

    for architecture_type, points in sorted(grouped.items()):
        points = sorted(points, key=lambda point: (point["x"], point["label"]))
        color = palette.get(architecture_type, "#555")
        path = " ".join(
            f"{'M' if index == 0 else 'L'} {project_x(point['x']):.2f} {project_y(point['y']):.2f}"
            for index, point in enumerate(points)
        )
        lines.append(f'<path d="{path}" fill="none" stroke="{color}" stroke-width="3" stroke-linecap="round" />')
        for point in points:
            x = project_x(point["x"])
            y = project_y(point["y"])
            lines.append(f'<circle cx="{x}" cy="{y}" r="7" fill="{color}" stroke="#fffaf2" stroke-width="2" />')
            lines.append(f'<text class="tick" x="{x + 8}" y="{y - 10}">{_escape(point["label"])}</text>')

    legend_x = margin_left
    legend_y = 80
    for index, (label, color) in enumerate(sorted(palette.items())):
        x = legend_x + index * 170
        lines.append(f'<line x1="{x}" y1="{legend_y}" x2="{x + 28}" y2="{legend_y}" stroke="{color}" stroke-width="3" />')
        lines.append(f'<circle cx="{x + 14}" cy="{legend_y}" r="6" fill="{color}" stroke="#fffaf2" stroke-width="2" />')
        lines.append(f'<text class="tick" x="{x + 38}" y="{legend_y + 4}">{_escape(label)}</text>')

    lines.append("</svg>")
    return "\n".join(lines)


def _build_tradeoff_bubble_svg(title, subtitle, rows, x_metric, y_metric, size_metric, x_label, y_label, invert_x=False):
    points = []
    suite_palette = {"model_scale": "#205f8f", "quantization": "#b65433"}
    for row in rows:
        x_value = _coerce_float(row.get(x_metric))
        y_value = _coerce_float(row.get(y_metric))
        size_value = _coerce_float(row.get(size_metric))
        if x_value is None or y_value is None:
            continue
        points.append(
            {
                "label": row["architecture_id"],
                "suite": row["suite"],
                "x": x_value,
                "y": y_value,
                "size": size_value if size_value is not None else 0.5,
            }
        )

    if not points:
        return _placeholder_svg(title, "Insufficient tradeoff data", subtitle)

    width = 980
    height = 560
    margin_left = 88
    margin_right = 42
    margin_top = 104
    margin_bottom = 82
    plot_width = width - margin_left - margin_right
    plot_height = height - margin_top - margin_bottom

    x_values = [point["x"] for point in points]
    y_values = [point["y"] for point in points]
    size_values = [point["size"] for point in points]
    x_min = min(x_values)
    x_max = max(x_values)
    y_min = min(0.0, min(y_values) * 0.95)
    y_max = max(y_values) * 1.08 if max(y_values) != 0 else 1.0
    if math.isclose(x_min, x_max):
        x_min -= 1.0
        x_max += 1.0
    if math.isclose(y_min, y_max):
        y_max = y_min + 1.0
    x_pad = (x_max - x_min) * 0.08
    x_min -= x_pad
    x_max += x_pad
    size_min = min(size_values)
    size_max = max(size_values)

    def radius(value):
        if math.isclose(size_min, size_max):
            return 12.0
        return 8.0 + ((value - size_min) / (size_max - size_min)) * 14.0

    def project_x(value):
        fraction = (value - x_min) / (x_max - x_min)
        if invert_x:
            fraction = 1.0 - fraction
        return margin_left + fraction * plot_width

    def project_y(value):
        return margin_top + (1.0 - ((value - y_min) / (y_max - y_min))) * plot_height

    lines = _svg_open(width, height, title, subtitle)
    lines.extend(
        [
            f'<line x1="{margin_left}" y1="{margin_top}" x2="{margin_left}" y2="{margin_top + plot_height}" stroke="#53483c" stroke-width="1.4" />',
            f'<line x1="{margin_left}" y1="{margin_top + plot_height}" x2="{margin_left + plot_width}" y2="{margin_top + plot_height}" stroke="#53483c" stroke-width="1.4" />',
            f'<text class="axis-label" x="{margin_left + plot_width / 2}" y="{height - 24}" text-anchor="middle">{_escape(x_label)}</text>',
            f'<text class="axis-label" x="26" y="{margin_top + plot_height / 2}" text-anchor="middle" transform="rotate(-90 26 {margin_top + plot_height / 2})">{_escape(y_label)}</text>',
            f'<text class="note" x="{width - 36}" y="42" text-anchor="end">bubble size = { _escape(size_metric) }</text>',
        ]
    )

    for tick in range(5):
        x_value = x_min + ((x_max - x_min) * tick / 4)
        y_value = y_min + ((y_max - y_min) * tick / 4)
        x = project_x(x_value)
        y = project_y(y_value)
        lines.append(f'<line x1="{x}" y1="{margin_top}" x2="{x}" y2="{margin_top + plot_height}" stroke="#ddd2c4" stroke-width="1" />')
        lines.append(f'<line x1="{margin_left}" y1="{y}" x2="{margin_left + plot_width}" y2="{y}" stroke="#ddd2c4" stroke-width="1" />')
        lines.append(f'<text class="tick" x="{x}" y="{margin_top + plot_height + 20}" text-anchor="middle">{x_value:.2f}</text>')
        lines.append(f'<text class="tick" x="{margin_left - 10}" y="{y + 4}" text-anchor="end">{y_value:.2f}</text>')

    for point in points:
        x = project_x(point["x"])
        y = project_y(point["y"])
        r = radius(point["size"])
        fill = suite_palette.get(point["suite"], "#555")
        lines.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" fill-opacity="0.76" stroke="#fffaf2" stroke-width="2.2" />')
        lines.append(f'<text class="tick" x="{x + r + 6}" y="{y - r - 2}">{_escape(point["label"])}</text>')

    legend_y = 80
    for index, (suite, color) in enumerate(sorted(suite_palette.items())):
        x = margin_left + index * 180
        lines.append(f'<circle cx="{x}" cy="{legend_y}" r="10" fill="{color}" fill-opacity="0.76" stroke="#fffaf2" stroke-width="2.2" />')
        lines.append(f'<text class="tick" x="{x + 18}" y="{legend_y + 4}">{_escape(suite)}</text>')

    lines.append("</svg>")
    return "\n".join(lines)


def _load_matchup_rows(selected_runs, summary_rows):
    name_lookup = {
        (row["run_id"], row["architecture_name"]): row["architecture_id"]
        for row in summary_rows
    }
    matchup_rows = []
    for run_dir in selected_runs:
        manifest = load_json(run_dir / "metadata" / "run_manifest.json")
        experiment = load_json(run_dir / "config" / "experiment.json")
        suite = SECTION14_3_AXES[experiment["comparison_axis"]]
        outcomes_path = run_dir / "summaries" / "game_outcomes.csv"
        if not outcomes_path.exists():
            continue
        for outcome in load_csv(outcomes_path):
            if outcome.get("experiment_group") != "internal_ai_tournament":
                continue
            try:
                players = json.loads(outcome.get("players") or "[]")
            except json.JSONDecodeError:
                continue
            if len(players) != 2:
                continue
            row_id = name_lookup.get((manifest["run_id"], players[0]))
            col_id = name_lookup.get((manifest["run_id"], players[1]))
            if not row_id or not col_id:
                continue
            winner = outcome.get("winner")
            if winner == "TIE":
                first_score = 0.5
                second_score = 0.5
            elif winner == players[0]:
                first_score = 1.0
                second_score = 0.0
            elif winner == players[1]:
                first_score = 0.0
                second_score = 1.0
            else:
                continue
            matchup_rows.append(
                {
                    "suite": suite,
                    "game": outcome.get("game"),
                    "row_id": row_id,
                    "col_id": col_id,
                    "score": first_score,
                    "count": 1,
                }
            )
            matchup_rows.append(
                {
                    "suite": suite,
                    "game": outcome.get("game"),
                    "row_id": col_id,
                    "col_id": row_id,
                    "score": second_score,
                    "count": 1,
                }
            )
    return matchup_rows


def build_figures(selected_runs, rows):
    figures = {}
    matchup_rows = _load_matchup_rows(selected_runs, rows)

    for suite in sorted({row["suite"] for row in rows}):
        for game in ("blotto", "connect4"):
            architecture_rows = []
            seen_architecture_ids = set()
            for row in rows:
                if row["suite"] != suite or row["game"] != game or row["experiment_group"] != "internal_ai_tournament":
                    continue
                if row["architecture_id"] in seen_architecture_ids:
                    continue
                seen_architecture_ids.add(row["architecture_id"])
                architecture_rows.append(row)
            figures[f"section14_3_{suite}_{game}_head_to_head_heatmap.svg"] = _build_matchup_heatmap_svg(
                f"{suite.replace('_', ' ').title()} {game.title()} Matchup Heatmap",
                "Research question: which ensemble compositions beat which alternatives in direct play?",
                architecture_rows,
                [row for row in matchup_rows if row["suite"] == suite and row["game"] == game],
            )

    progression_specs = [
        ("model_scale", "blotto", "blotto_vs_bots", "win_rate", "Blotto baseline win rate"),
        ("model_scale", "connect4", "connect4_oracle_accuracy", "connect4_optimal_move_accuracy", "Connect 4 oracle agreement (%)"),
        ("quantization", "blotto", "blotto_vs_bots", "win_rate", "Blotto baseline win rate"),
        ("quantization", "connect4", "connect4_oracle_accuracy", "connect4_optimal_move_accuracy", "Connect 4 oracle agreement (%)"),
    ]
    for suite, game, experiment_group, metric, y_label in progression_specs:
        filtered_rows = [
            row
            for row in rows
            if row["suite"] == suite and row["game"] == game and row["experiment_group"] == experiment_group
        ]
        figures[f"section14_3_{suite}_{game}_{experiment_group}_quality_progression.svg"] = _build_quality_progression_svg(
            f"{suite.replace('_', ' ').title()} {game.title()} Quality Progression",
            f"Research question: do better model mixes improve {y_label.lower()}?",
            filtered_rows,
            metric,
            y_label,
        )

    figures["section14_3_connect4_oracle_tradeoff_bubble.svg"] = _build_tradeoff_bubble_svg(
        "Connect 4 Oracle Tradeoff Map",
        "Research question: which teams improve accuracy without increasing blunders?",
        [row for row in rows if row["game"] == "connect4" and row["experiment_group"] == "connect4_oracle_accuracy"],
        "blunder_rate",
        "connect4_optimal_move_accuracy",
        "consistency_per_state_agreement",
        "Blunder rate (left is better)",
        "Oracle agreement (%)",
        invert_x=True,
    )
    figures["section14_3_blotto_strategy_tradeoff_bubble.svg"] = _build_tradeoff_bubble_svg(
        "Blotto Strategy Tradeoff Map",
        "Research question: which teams stay near equilibrium while still beating baselines?",
        [row for row in rows if row["game"] == "blotto" and row["experiment_group"] == "blotto_vs_bots"],
        "blotto_nash_distance",
        "win_rate",
        "consistency_outcome_stability",
        "Nash distance (left is better)",
        "Baseline win rate",
        invert_x=True,
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
    for generated_dir in ("tables", "figures", "key_runs"):
        generated_path = output_dir / generated_dir
        if generated_path.exists():
            shutil.rmtree(generated_path)

    copied_artifacts = copy_key_run_artifacts(selected_runs, output_dir)
    figures = build_figures(selected_runs, rows)

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
