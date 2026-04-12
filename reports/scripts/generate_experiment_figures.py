import csv
import json
import math
from collections import defaultdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXPERIMENTS_ROOT = PROJECT_ROOT / "runs" / "experiment_runs"
OUTPUT_DIR = PROJECT_ROOT / "figures"

PRIMARY_METRICS = {
    ("blotto", "internal_ai_tournament"): ("win_rate", "Win rate"),
    ("blotto", "blotto_vs_bots"): ("win_rate", "Win rate"),
    ("connect4", "internal_ai_tournament"): ("win_rate", "Win rate"),
    ("connect4", "connect4_oracle_accuracy"): ("connect4_optimal_move_accuracy", "Oracle agreement (%)"),
}
EXPERIMENT_LABELS = {
    "baseline_architecture_benchmark": "architecture_benchmark",
    "pilot_architecture_comparison": "pilot_architecture_comparison",
    "final_architecture_comparison": "architecture_comparison",
    "prompt_minimal_architecture_comparison": "prompt_minimal_architecture_comparison",
    "prompt_chain_of_thought_architecture_comparison": "prompt_chain_of_thought_architecture_comparison",
    "prompt_legality_first_architecture_comparison": "prompt_legality_first_architecture_comparison",
    "difficulty_blotto_harder": "blotto_harder_difficulty",
    "difficulty_connect4_wide": "connect4_wide_difficulty",
    "model_scale_subset": "model_scale_subset",
    "model_scale_flight": "model_scale_flight",
    "quantization_subset": "quantization_subset",
    "metrics_section9_smoke": "metrics_validation",
}
ARCHITECTURE_ORDER = {
    "single": 0,
    "single_low": 0,
    "single_med": 1,
    "single_high": 2,
    "parallel": 10,
    "parallel_lmh": 10,
    "parallel_mmh": 11,
    "parallel_hhl": 12,
    "parallel_llh": 13,
    "parallel_qmix": 14,
    "parallel_f16f16q4": 15,
    "parallel_q4q4f16": 16,
    "hierarchical": 20,
    "hierarchical_lmh": 20,
    "hierarchical_mmh": 21,
    "hierarchical_hhl": 22,
    "hierarchical_llh": 23,
    "hierarchical_qmix": 24,
    "hierarchical_f16f16q4": 25,
    "hierarchical_q4q4f16": 26,
}
ARCHITECTURE_COLORS = {
    "single": "#4C78A8",
    "parallel": "#F58518",
    "hierarchical": "#54A24B",
}
PROMPT_LABELS = {
    "minimal_v1": "Minimal",
    "chain_of_thought_v1": "Chain of Thought",
    "legality_first_v1": "Legality First",
    "structured_reasoning_v1": "Structured Reasoning",
}
QUALITY_SCORE_BY_ALIAS = {
    "low": 1.0,
    "q4": 1.0,
    "med": 2.0,
    "q8": 2.0,
    "high": 3.0,
    "f16": 3.0,
}
METRIC_COLUMNS = [
    ("win_rate", "Win"),
    ("legality_rate", "Legal"),
    ("hallucination_rate", "Halluc."),
    ("blotto_nash_distance", "Nash dist."),
    ("connect4_optimal_move_accuracy", "Oracle %"),
    ("blunder_rate", "Blunder"),
]


def _load_matplotlib():
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib import colors, pyplot

    return pyplot, colors


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_csv(path):
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def slugify(value):
    cleaned = []
    for char in value.lower():
        if char.isalnum():
            cleaned.append(char)
        else:
            cleaned.append("_")
    slug = "".join(cleaned)
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug.strip("_")


def prettify_architecture(scope_id):
    if scope_id in {"single", "parallel", "hierarchical"}:
        return {
            "single": "Single",
            "parallel": "Parallel",
            "hierarchical": "Hierarchical",
        }[scope_id]
    if scope_id.startswith("single_"):
        alias = scope_id.split("_", 1)[1].upper()
        return f"Single {alias}"
    if scope_id.startswith("parallel_"):
        return f"Parallel {scope_id.split('_', 1)[1].upper()}"
    if scope_id.startswith("hierarchical_"):
        return f"Hier. {scope_id.split('_', 1)[1].upper()}"
    return scope_id.replace("_", " ")


def architecture_family(scope_id):
    if scope_id.startswith("single"):
        return "single"
    if scope_id.startswith("parallel"):
        return "parallel"
    if scope_id.startswith("hierarchical"):
        return "hierarchical"
    return "single"


def safe_float(value):
    if value in {"", None}:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def mean(values):
    values = [value for value in values if value is not None]
    if not values:
        return None
    return sum(values) / len(values)


def architecture_metadata(spec):
    architecture_type = spec.get("type")
    if architecture_type == "parallel":
        aliases = list(spec.get("model_sequence", []))
    elif architecture_type == "hierarchical":
        role_aliases = spec.get("role_model_aliases", {})
        critic_aliases = role_aliases.get("critic", [])
        if not isinstance(critic_aliases, list):
            critic_aliases = [critic_aliases]
        aliases = [role_aliases.get("reasoner"), *critic_aliases, role_aliases.get("executive")]
    else:
        aliases = [spec.get("model_alias")] if spec.get("model_alias") else []

    scores = [QUALITY_SCORE_BY_ALIAS[alias] for alias in aliases if alias in QUALITY_SCORE_BY_ALIAS]
    return {
        "composition_aliases": aliases,
        "composition_quality_score": (sum(scores) / len(scores)) if scores else None,
    }


def collect_architecture_rows():
    rows = []
    for run_dir in sorted(EXPERIMENTS_ROOT.glob("run_*")):
        experiment_path = run_dir / "config" / "experiment.json"
        architectures_path = run_dir / "config" / "architectures.json"
        summary_path = run_dir / "summaries" / "architecture_summaries.csv"
        if not experiment_path.exists() or not summary_path.exists() or not architectures_path.exists():
            continue
        experiment = load_json(experiment_path)
        architecture_specs = {
            spec["id"]: spec
            for spec in load_json(architectures_path).get("architectures", [])
        }
        run_label = experiment.get("run_label")
        if run_label not in EXPERIMENT_LABELS:
            continue
        for row in load_csv(summary_path):
            if row.get("scope_type") != "architecture":
                continue
            spec = architecture_specs.get(row.get("scope_id"), {})
            meta = architecture_metadata(spec)
            rows.append(
                {
                    "run_id": run_dir.name,
                    "run_label": run_label,
                    "comparison_axis": experiment.get("comparison_axis"),
                    "prompt_family": experiment.get("prompt_family"),
                    "game": row.get("game"),
                    "experiment_group": row.get("experiment_group"),
                    "scope_id": row.get("scope_id"),
                    "architecture_label": prettify_architecture(row.get("scope_id", "")),
                    "architecture_family": architecture_family(row.get("scope_id", "")),
                    "composition_quality_score": meta.get("composition_quality_score"),
                    "composition_aliases": meta.get("composition_aliases"),
                    "win_rate": safe_float(row.get("win_rate")),
                    "legality_rate": safe_float(row.get("legality_rate")),
                    "hallucination_rate": safe_float(row.get("hallucination_rate")),
                    "blotto_nash_distance": safe_float(row.get("blotto_nash_distance")),
                    "connect4_optimal_move_accuracy": safe_float(row.get("connect4_optimal_move_accuracy")),
                    "blunder_rate": safe_float(row.get("blunder_rate")),
                }
            )
    return rows


def aggregate_rows(rows, key_fields):
    buckets = defaultdict(list)
    for row in rows:
        key = tuple(row[field] for field in key_fields)
        buckets[key].append(row)

    aggregated = []
    for key, group in sorted(buckets.items()):
        item = {field: value for field, value in zip(key_fields, key)}
        for metric, _ in METRIC_COLUMNS:
            item[metric] = mean([row.get(metric) for row in group])
        item["run_count"] = len({row["run_id"] for row in group})
        aggregated.append(item)
    return aggregated


def sort_architecture_rows(rows):
    return sorted(
        rows,
        key=lambda row: (
            ARCHITECTURE_ORDER.get(row["scope_id"], 999),
            row["scope_id"],
        ),
    )


def sort_prompt_rows(rows):
    prompt_order = {
        "minimal_v1": 0,
        "structured_reasoning_v1": 1,
        "chain_of_thought_v1": 2,
        "legality_first_v1": 3,
    }
    return sorted(rows, key=lambda row: (prompt_order.get(row["prompt_family"], 999), row["prompt_family"]))


def metric_bounds(metric):
    if metric in {"win_rate", "legality_rate", "hallucination_rate", "blunder_rate"}:
        return 0.0, 1.0
    if metric == "blotto_nash_distance":
        return 0.0, 0.30
    if metric == "connect4_optimal_move_accuracy":
        return 0.0, 100.0
    return None, None


def format_metric(metric, value):
    if value is None:
        return ""
    if metric == "connect4_optimal_move_accuracy":
        return f"{value:.1f}"
    if metric == "blotto_nash_distance":
        return f"{value:.3f}"
    return f"{value:.2f}"


def save_grouped_bar_chart(path, rows, metric, y_label):
    pyplot, _ = _load_matplotlib()
    rows = sort_architecture_rows(rows)
    labels = [row["architecture_label"] for row in rows]
    values = [row.get(metric) for row in rows]
    colors = [ARCHITECTURE_COLORS.get(row["architecture_family"], "#4C78A8") for row in rows]

    fig_width = max(6.0, 1.25 * len(labels) + 1.8)
    fig, ax = pyplot.subplots(figsize=(fig_width, 4.2))
    bars = ax.bar(range(len(labels)), values, color=colors, width=0.72, edgecolor="#F7F7F5", linewidth=0.8)

    ymin, ymax = metric_bounds(metric)
    if ymin is not None and ymax is not None:
        ax.set_ylim(ymin, ymax)
    ax.set_ylabel(y_label)
    ax.set_xticks(range(len(labels)), labels, rotation=25, ha="right")
    ax.grid(axis="y", color="#D9D9D9", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#8F8F8F")
    ax.spines["bottom"].set_color("#8F8F8F")
    ax.tick_params(axis="both", labelsize=9)

    top = ymax if ymax is not None else max(values)
    offset = (top - (ymin or 0.0)) * 0.02 if top is not None else 0.02
    for bar, value in zip(bars, values):
        if value is None:
            continue
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + offset,
            format_metric(metric, value),
            ha="center",
            va="bottom",
            fontsize=8,
            color="#333333",
        )

    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, format="pdf", bbox_inches="tight")
    pyplot.close(fig)


def save_metric_heatmap(path, rows, columns, display_rows=None, vmin=0.0, vmax=1.0):
    pyplot, colors = _load_matplotlib()
    rows = sort_architecture_rows(rows)
    display_rows = sort_architecture_rows(display_rows or rows)
    labels = [row["architecture_label"] for row in rows]

    matrix = []
    annotations = []
    for row, display_row in zip(rows, display_rows):
        matrix_row = []
        annotation_row = []
        for metric, _ in columns:
            value = row.get(metric)
            matrix_row.append(float("nan") if value is None else value)
            annotation_row.append(format_metric(metric, display_row.get(metric)))
        matrix.append(matrix_row)
        annotations.append(annotation_row)

    fig_width = max(5.8, len(columns) * 1.1 + 1.8)
    fig_height = max(2.6, len(labels) * 0.48 + 1.2)
    fig, ax = pyplot.subplots(figsize=(fig_width, fig_height))

    norm = colors.Normalize(vmin=vmin, vmax=vmax)
    image = ax.imshow(matrix, cmap="Greys", norm=norm, aspect="auto")
    ax.set_xticks(range(len(columns)), [label for _, label in columns], rotation=20, ha="right")
    ax.set_yticks(range(len(labels)), labels)
    ax.tick_params(axis="both", labelsize=9)
    for row_index, annotation_row in enumerate(annotations):
        for col_index, text in enumerate(annotation_row):
            ax.text(col_index, row_index, text, ha="center", va="center", fontsize=8, color="#111111")
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_xticks([index - 0.5 for index in range(1, len(columns))], minor=True)
    ax.set_yticks([index - 0.5 for index in range(1, len(labels))], minor=True)
    ax.grid(which="minor", color="#FFFFFF", linewidth=1.0)
    ax.tick_params(which="minor", bottom=False, left=False)

    colorbar = fig.colorbar(image, ax=ax, fraction=0.035, pad=0.03)
    colorbar.outline.set_visible(False)
    colorbar.ax.tick_params(labelsize=8)

    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, format="pdf", bbox_inches="tight")
    pyplot.close(fig)


def rescale_for_heatmap(metric, value):
    if value is None:
        return None
    if metric == "blotto_nash_distance":
        return max(0.0, min(1.0, 1.0 - (value / 0.30)))
    if metric == "connect4_optimal_move_accuracy":
        return max(0.0, min(1.0, value / 100.0))
    return value


def save_composite_heatmap(path, rows):
    heatmap_rows = []
    for row in rows:
        converted = dict(row)
        for metric, _ in METRIC_COLUMNS:
            converted[metric] = rescale_for_heatmap(metric, row.get(metric))
        heatmap_rows.append(converted)
    save_metric_heatmap(path, heatmap_rows, METRIC_COLUMNS, display_rows=rows, vmin=0.0, vmax=1.0)


def save_prompt_heatmap(path, rows, metric):
    pyplot, colors = _load_matplotlib()
    rows = sort_prompt_rows(rows)
    prompt_labels = [PROMPT_LABELS.get(row["prompt_family"], row["prompt_family"]) for row in rows]
    architecture_labels = [row["architecture_label"] for row in rows]

    unique_prompts = []
    unique_architectures = []
    for row in rows:
        prompt_name = PROMPT_LABELS.get(row["prompt_family"], row["prompt_family"])
        if prompt_name not in unique_prompts:
            unique_prompts.append(prompt_name)
        if row["architecture_label"] not in unique_architectures:
            unique_architectures.append(row["architecture_label"])

    prompt_index = {name: idx for idx, name in enumerate(unique_prompts)}
    architecture_index = {name: idx for idx, name in enumerate(unique_architectures)}
    matrix = [[float("nan") for _ in unique_prompts] for _ in unique_architectures]
    annotations = [["" for _ in unique_prompts] for _ in unique_architectures]
    for row in rows:
        value = row.get(metric)
        x_idx = prompt_index[PROMPT_LABELS.get(row["prompt_family"], row["prompt_family"])]
        y_idx = architecture_index[row["architecture_label"]]
        matrix[y_idx][x_idx] = value
        annotations[y_idx][x_idx] = format_metric(metric, value)

    ymin, ymax = metric_bounds(metric)
    fig_width = max(5.6, len(unique_prompts) * 1.25 + 1.2)
    fig_height = max(2.8, len(unique_architectures) * 0.55 + 1.2)
    fig, ax = pyplot.subplots(figsize=(fig_width, fig_height))
    cmap = colors.LinearSegmentedColormap.from_list("prompt_metric", ["#F2F2F2", "#525252"])
    image = ax.imshow(matrix, cmap=cmap, vmin=ymin, vmax=ymax, aspect="auto")
    ax.set_xticks(range(len(unique_prompts)), unique_prompts)
    ax.set_yticks(range(len(unique_architectures)), unique_architectures)
    ax.tick_params(axis="x", rotation=20, labelsize=9)
    ax.tick_params(axis="y", labelsize=9)
    ax.set_xlabel("Prompt family")
    for y_idx, annotation_row in enumerate(annotations):
        for x_idx, text in enumerate(annotation_row):
            ax.text(x_idx, y_idx, text, ha="center", va="center", fontsize=8, color="#111111")
    for spine in ax.spines.values():
        spine.set_visible(False)
    colorbar = fig.colorbar(image, ax=ax, fraction=0.035, pad=0.03)
    colorbar.outline.set_visible(False)
    colorbar.ax.tick_params(labelsize=8)

    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, format="pdf", bbox_inches="tight")
    pyplot.close(fig)


def save_scatter(path, rows, x_metric, y_metric, x_label, y_label):
    pyplot, _ = _load_matplotlib()
    rows = sort_architecture_rows(rows)
    fig, ax = pyplot.subplots(figsize=(6.4, 4.4))
    for row in rows:
        x_value = row.get(x_metric)
        y_value = row.get(y_metric)
        if x_value is None or y_value is None:
            continue
        color = ARCHITECTURE_COLORS.get(row["architecture_family"], "#4C78A8")
        ax.scatter(
            [x_value],
            [y_value],
            s=110,
            color=color,
            edgecolors="#FFFFFF",
            linewidths=0.8,
            zorder=3,
        )
        ax.annotate(row["architecture_label"], (x_value, y_value), xytext=(6, 6), textcoords="offset points", fontsize=8)
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.grid(color="#D9D9D9", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#8F8F8F")
    ax.spines["bottom"].set_color("#8F8F8F")
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, format="pdf", bbox_inches="tight")
    pyplot.close(fig)


def save_line_chart(path, rows, metric, y_label):
    pyplot, _ = _load_matplotlib()
    grouped = defaultdict(list)
    for row in rows:
        if row.get("composition_quality_score") is None:
            continue
        grouped[row["architecture_family"]].append(row)

    fig, ax = pyplot.subplots(figsize=(6.6, 4.4))
    for family in ["single", "parallel", "hierarchical"]:
        family_rows = grouped.get(family, [])
        if not family_rows:
            continue
        ordered = sorted(
            family_rows,
            key=lambda row: (
                row.get("composition_quality_score"),
                ARCHITECTURE_ORDER.get(row["scope_id"], 999),
                row["scope_id"],
            ),
        )
        xs = [row["composition_quality_score"] for row in ordered]
        ys = [row.get(metric) for row in ordered]
        ax.plot(
            xs,
            ys,
            marker="o",
            color=ARCHITECTURE_COLORS.get(family, "#4C78A8"),
            linewidth=1.8,
            markersize=5.5,
        )
        for row in ordered:
            ax.annotate(
                row["architecture_label"],
                (row["composition_quality_score"], row.get(metric)),
                xytext=(5, 5),
                textcoords="offset points",
                fontsize=7.5,
            )

    ymin, ymax = metric_bounds(metric)
    if ymin is not None and ymax is not None:
        ax.set_ylim(ymin, ymax)
    ax.set_xlabel("Composition quality score")
    ax.set_ylabel(y_label)
    ax.set_xticks([1.0, 1.5, 2.0, 2.5, 3.0])
    ax.grid(color="#D9D9D9", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#8F8F8F")
    ax.spines["bottom"].set_color("#8F8F8F")
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, format="pdf", bbox_inches="tight")
    pyplot.close(fig)


def normalize_proposal(move):
    if move in (None, "", {}, []):
        return None
    return json.dumps(move, sort_keys=True)


def collect_parallel_agreement_rows():
    rows = []
    for run_dir in sorted(EXPERIMENTS_ROOT.glob("run_*")):
        experiment_path = run_dir / "config" / "experiment.json"
        turn_records_path = run_dir / "summaries" / "turn_records.csv"
        if not experiment_path.exists() or not turn_records_path.exists():
            continue
        experiment = load_json(experiment_path)
        run_label = experiment.get("run_label")
        if run_label not in {"model_scale_subset", "quantization_subset"}:
            continue

        for row in load_csv(turn_records_path):
            if row.get("architecture_type") != "parallel":
                continue
            try:
                outputs = json.loads(row.get("intermediate_outputs") or "[]")
            except json.JSONDecodeError:
                continue

            parsed = []
            for output in outputs:
                alias = output.get("model_alias")
                proposal = normalize_proposal((output.get("parsed_response") or {}).get("move"))
                parsed.append((alias, proposal))

            for index, (left_alias, left_proposal) in enumerate(parsed):
                for right_alias, right_proposal in parsed[index + 1:]:
                    if left_alias is None or right_alias is None:
                        continue
                    alias_pair = tuple(sorted((left_alias, right_alias)))
                    valid_pair = left_proposal is not None and right_proposal is not None
                    rows.append(
                        {
                            "run_label": run_label,
                            "game": row.get("game"),
                            "left_alias": alias_pair[0],
                            "right_alias": alias_pair[1],
                            "valid_pair": valid_pair,
                            "agree": valid_pair and left_proposal == right_proposal,
                        }
                    )
    return rows


def save_agreement_heatmap(path, rows):
    pyplot, colors = _load_matplotlib()
    aliases = sorted({row["left_alias"] for row in rows} | {row["right_alias"] for row in rows}, key=lambda alias: QUALITY_SCORE_BY_ALIAS.get(alias, 999))
    alias_index = {alias: index for index, alias in enumerate(aliases)}
    matrix = [[float("nan") for _ in aliases] for _ in aliases]
    annotations = [["" for _ in aliases] for _ in aliases]

    pair_buckets = defaultdict(lambda: {"agree": 0, "valid": 0})
    for row in rows:
        key = (row["left_alias"], row["right_alias"])
        if row["valid_pair"]:
            pair_buckets[key]["valid"] += 1
            if row["agree"]:
                pair_buckets[key]["agree"] += 1

    for alias in aliases:
        idx = alias_index[alias]
        matrix[idx][idx] = 1.0
        annotations[idx][idx] = alias.upper()

    for (left_alias, right_alias), bucket in pair_buckets.items():
        left_idx = alias_index[left_alias]
        right_idx = alias_index[right_alias]
        value = None if bucket["valid"] == 0 else bucket["agree"] / bucket["valid"]
        display = "" if value is None else f"{value:.2f}\n{bucket['valid']}"
        for row_idx, col_idx in ((left_idx, right_idx), (right_idx, left_idx)):
            matrix[row_idx][col_idx] = float("nan") if value is None else value
            annotations[row_idx][col_idx] = display

    fig_width = max(4.6, len(aliases) * 1.1 + 1.2)
    fig_height = fig_width
    fig, ax = pyplot.subplots(figsize=(fig_width, fig_height))
    cmap = colors.LinearSegmentedColormap.from_list("agreement", ["#F2F2F2", "#4D4D4D"])
    image = ax.imshow(matrix, cmap=cmap, vmin=0.0, vmax=1.0, aspect="equal")
    ax.set_xticks(range(len(aliases)), [alias.upper() for alias in aliases])
    ax.set_yticks(range(len(aliases)), [alias.upper() for alias in aliases])
    ax.tick_params(axis="both", labelsize=9)
    for row_index, annotation_row in enumerate(annotations):
        for col_index, text in enumerate(annotation_row):
            ax.text(col_index, row_index, text, ha="center", va="center", fontsize=8, color="#111111")
    for spine in ax.spines.values():
        spine.set_visible(False)
    colorbar = fig.colorbar(image, ax=ax, fraction=0.04, pad=0.03)
    colorbar.outline.set_visible(False)
    colorbar.ax.tick_params(labelsize=8)

    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, format="pdf", bbox_inches="tight")
    pyplot.close(fig)


def build_standard_experiment_figures(rows):
    figures = []
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["run_label"]].append(row)

    for run_label, run_rows in sorted(grouped.items()):
        if run_label in {"model_scale_subset", "model_scale_flight", "quantization_subset"}:
            continue
        label_prefix = EXPERIMENT_LABELS[run_label]
        aggregated = aggregate_rows(run_rows, ["run_label", "game", "experiment_group", "scope_id", "architecture_label", "architecture_family"])
        by_group = defaultdict(list)
        for row in aggregated:
            by_group[(row["game"], row["experiment_group"])].append(row)

        for (game, experiment_group), group_rows in sorted(by_group.items()):
            metric, metric_label = PRIMARY_METRICS[(game, experiment_group)]
            figures.append(
                (
                    OUTPUT_DIR / f"{label_prefix}_{game}_{experiment_group}_{slugify(metric_label)}.pdf",
                    "bar",
                    group_rows,
                    metric,
                    metric_label,
                )
            )
            figures.append(
                (
                    OUTPUT_DIR / f"{label_prefix}_{game}_{experiment_group}_metric_heatmap.pdf",
                    "composite_heatmap",
                    group_rows,
                    None,
                    None,
                )
            )
    return figures


def build_prompt_family_figures(rows):
    prompt_rows = [
        row for row in rows
        if row["run_label"].startswith("prompt_")
    ]
    if not prompt_rows:
        return []

    aggregated = aggregate_rows(prompt_rows, ["prompt_family", "game", "experiment_group", "scope_id", "architecture_label"])
    figures = []
    by_group = defaultdict(list)
    for row in aggregated:
        by_group[(row["game"], row["experiment_group"])].append(row)

    for (game, experiment_group), group_rows in sorted(by_group.items()):
        metric, metric_label = PRIMARY_METRICS[(game, experiment_group)]
        figures.append(
            (
                    OUTPUT_DIR / f"prompt_family_{game}_{experiment_group}_{slugify(metric_label)}_heatmap.pdf",
                    "prompt_heatmap",
                    group_rows,
                    metric,
                    None,
                )
            )
        if game == "blotto":
            figures.append(
                (
                    OUTPUT_DIR / f"prompt_family_{game}_{experiment_group}_nash_distance_heatmap.pdf",
                    "prompt_heatmap",
                    group_rows,
                    "blotto_nash_distance",
                    None,
                )
            )
    return figures


def build_mixed_team_figures(rows):
    mixed_rows = [
        row for row in rows
        if row["run_label"] in {"model_scale_subset", "model_scale_flight", "quantization_subset"}
    ]
    if not mixed_rows:
        return []

    aggregated = aggregate_rows(
        mixed_rows,
        ["run_label", "game", "experiment_group", "scope_id", "architecture_label", "architecture_family"],
    )
    figures = []
    by_label = defaultdict(list)
    for row in aggregated:
        by_label[row["run_label"]].append(row)

    for run_label, group in sorted(by_label.items()):
        label_prefix = EXPERIMENT_LABELS[run_label]
        by_group = defaultdict(list)
        for row in group:
            by_group[(row["game"], row["experiment_group"])].append(row)
        for (game, experiment_group), rows_for_group in sorted(by_group.items()):
            metric, metric_label = PRIMARY_METRICS[(game, experiment_group)]
            figures.append(
                (
                    OUTPUT_DIR / f"{label_prefix}_{game}_{experiment_group}_{slugify(metric_label)}.pdf",
                    "bar",
                    rows_for_group,
                    metric,
                    metric_label,
                )
            )
            figures.append(
                (
                    OUTPUT_DIR / f"{label_prefix}_{game}_{experiment_group}_{slugify(metric_label)}_line.pdf",
                    "line",
                    rows_for_group,
                    metric,
                    metric_label,
                )
            )
        if any(row.get("legality_rate") is not None and row.get("hallucination_rate") is not None for row in group):
            figures.append(
                (
                    OUTPUT_DIR / f"{label_prefix}_legality_vs_hallucination.pdf",
                    "scatter",
                    group,
                    "hallucination_rate",
                    "legality_rate",
                )
            )
    return figures


def build_parallel_agreement_figures():
    rows = collect_parallel_agreement_rows()
    figures = []
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["run_label"], row["game"])].append(row)
    for (run_label, game), group_rows in sorted(grouped.items()):
        label_prefix = EXPERIMENT_LABELS.get(run_label, run_label)
        figures.append(
            (
                OUTPUT_DIR / f"{label_prefix}_{game}_parallel_model_agreement_heatmap.pdf",
                "agreement_heatmap",
                group_rows,
                None,
                None,
            )
        )
    return figures


def render_figure(spec):
    path, kind, rows, metric, label = spec
    if kind == "bar":
        save_grouped_bar_chart(path, rows, metric, label)
        return
    if kind == "composite_heatmap":
        save_composite_heatmap(path, rows)
        return
    if kind == "prompt_heatmap":
        save_prompt_heatmap(path, rows, metric)
        return
    if kind == "scatter":
        save_scatter(path, rows, metric, label, "Hallucination rate", "Legality rate")
        return
    if kind == "line":
        save_line_chart(path, rows, metric, label)
        return
    if kind == "agreement_heatmap":
        save_agreement_heatmap(path, rows)
        return
    raise ValueError(f"Unknown figure kind: {kind}")


def main():
    rows = collect_architecture_rows()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    figures = []
    figures.extend(build_standard_experiment_figures(rows))
    figures.extend(build_prompt_family_figures(rows))
    figures.extend(build_mixed_team_figures(rows))
    figures.extend(build_parallel_agreement_figures())

    written = []
    for spec in figures:
        render_figure(spec)
        written.append(spec[0])

    manifest = {
        "figure_count": len(written),
        "figures": [str(path.relative_to(PROJECT_ROOT)) for path in written],
    }
    (OUTPUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
