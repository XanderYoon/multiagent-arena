import io
import re
from collections import defaultdict


def _load_matplotlib():
    try:
        import matplotlib

        matplotlib.use("Agg")
        from matplotlib import colors, pyplot

        return matplotlib, pyplot, colors
    except ImportError:
        return None, None, None


def _figure_to_svg(fig):
    buffer = io.StringIO()
    fig.savefig(buffer, format="svg", bbox_inches="tight")
    svg = buffer.getvalue()
    buffer.close()
    svg = re.sub(r"<metadata>.*?</metadata>", "", svg, flags=re.DOTALL)
    svg = re.sub(r"<!--.*?-->", "", svg, flags=re.DOTALL)
    svg = re.sub(r"<title>.*?</title>", "", svg, flags=re.DOTALL)
    return svg


def render_placeholder_svg(title, message, subtitle="", size=(9.6, 2.6)):
    _, pyplot, _ = _load_matplotlib()
    if pyplot is None:
        return None

    fig, ax = pyplot.subplots(figsize=size)
    fig.patch.set_facecolor("#fffdf9")
    ax.set_axis_off()
    ax.text(
        0.5,
        0.5,
        message,
        ha="center",
        va="center",
        fontsize=13,
        color="#4d4439",
        bbox={"boxstyle": "round,pad=0.6", "facecolor": "#f1ebe1", "edgecolor": "#d9cfbf"},
        transform=ax.transAxes,
    )
    svg = _figure_to_svg(fig)
    pyplot.close(fig)
    return svg


def render_bar_chart_svg(title, values, subtitle="", x_label="", y_label="", size=(6.4, 3.6)):
    _, pyplot, _ = _load_matplotlib()
    if pyplot is None:
        return None

    labels = list(values.keys())
    numbers = list(values.values())
    fig, ax = pyplot.subplots(figsize=size)
    fig.patch.set_facecolor("#fffdf9")
    ax.set_facecolor("#fffaf2")
    bars = ax.bar(labels, numbers, color="#215f8b", edgecolor="#17384f", width=0.65)
    if x_label:
        ax.set_xlabel(x_label, color="#4d4439")
    if y_label:
        ax.set_ylabel(y_label, color="#4d4439")
    ax.grid(axis="y", linestyle="--", alpha=0.25, color="#8f8578")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#8f8578")
    ax.spines["bottom"].set_color("#8f8578")
    ax.tick_params(axis="x", rotation=20, labelsize=9, colors="#4d4439")
    ax.tick_params(axis="y", colors="#4d4439")
    for bar, value in zip(bars, numbers):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{value:.3f}",
            ha="center",
            va="bottom",
            fontsize=9,
            color="#2f2a24",
        )
    svg = _figure_to_svg(fig)
    pyplot.close(fig)
    return svg


def render_heatmap_svg(title, subtitle, labels, matrix, annotations, note="", x_labels=None, y_labels=None):
    _, pyplot, colors = _load_matplotlib()
    if pyplot is None:
        return None

    x_labels = x_labels or labels
    y_labels = y_labels or labels
    cmap = colors.LinearSegmentedColormap.from_list("benchmark_heat", ["#aa3f2d", "#efe4d0", "#2c7a56"])
    cmap.set_bad("#e7ded0")
    fig_width = max(8.8, 2.8 + len(x_labels) * 0.9)
    fig_height = max(4.2, 2.8 + len(y_labels) * 0.7)
    fig, ax = pyplot.subplots(figsize=(fig_width, fig_height))
    fig.patch.set_facecolor("#fffdf9")
    ax.set_facecolor("#fffaf2")
    masked = []
    for row in matrix:
        masked.append([value if value is not None else float("nan") for value in row])
    image = ax.imshow(masked, cmap=cmap, vmin=0.0, vmax=1.0)
    ax.set_xticks(range(len(x_labels)), labels=x_labels, rotation=35, ha="right")
    ax.set_yticks(range(len(y_labels)), labels=y_labels)
    ax.tick_params(axis="both", labelsize=9, colors="#4d4439")
    for row_index, row in enumerate(annotations):
        for col_index, text in enumerate(row):
            ax.text(col_index, row_index, text, ha="center", va="center", fontsize=8, color="#2f2a24")
    colorbar = fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    colorbar.ax.tick_params(labelsize=8, colors="#4d4439")
    colorbar.outline.set_edgecolor("#8f8578")
    svg = _figure_to_svg(fig)
    pyplot.close(fig)
    return svg


def render_quality_progression_svg(title, subtitle, rows, metric, y_label, palette):
    _, pyplot, _ = _load_matplotlib()
    if pyplot is None:
        return None

    grouped = defaultdict(list)
    for row in rows:
        grouped[row["architecture_type"]].append(
            (row["composition_quality_score"], float(row[metric]), row["architecture_id"])
        )

    fig, ax = pyplot.subplots(figsize=(9.8, 5.6))
    fig.patch.set_facecolor("#fffdf9")
    ax.set_facecolor("#fffaf2")
    for architecture_type, points in grouped.items():
        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        labels = [point[2] for point in points]
        ax.scatter(
            xs,
            ys,
            s=90,
            color=palette.get(architecture_type, "#555555"),
            edgecolors="#fffaf2",
            linewidths=1.5,
            label=architecture_type.title(),
            zorder=3,
        )
        if len(points) > 1:
            ordered = sorted(points, key=lambda point: (point[0], point[1], point[2]))
            ax.plot(
                [point[0] for point in ordered],
                [point[1] for point in ordered],
                color=palette.get(architecture_type, "#555555"),
                alpha=0.45,
                linewidth=1.6,
                zorder=2,
            )
        for x_value, y_value, label in zip(xs, ys, labels):
            ax.annotate(label, (x_value, y_value), xytext=(6, 6), textcoords="offset points", fontsize=8, color="#2f2a24")
    ax.set_xlabel("Mean team quality score (low/q4=1, med/q8=2, high/f16=3)", color="#4d4439")
    ax.set_ylabel(y_label, color="#4d4439")
    ax.grid(True, linestyle="--", alpha=0.25, color="#8f8578")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(frameon=False, fontsize=9, loc="best")
    svg = _figure_to_svg(fig)
    pyplot.close(fig)
    return svg


def render_tradeoff_bubble_svg(
    title,
    subtitle,
    points,
    x_label,
    y_label,
    size_label,
    invert_x=False,
    suite_palette=None,
):
    _, pyplot, _ = _load_matplotlib()
    if pyplot is None:
        return None

    suite_palette = suite_palette or {}
    fig, ax = pyplot.subplots(figsize=(9.8, 5.6))
    fig.patch.set_facecolor("#fffdf9")
    ax.set_facecolor("#fffaf2")

    size_values = [point["size"] for point in points]
    size_min = min(size_values)
    size_max = max(size_values)

    def scale_size(value):
        if size_max == size_min:
            return 180.0
        return 120.0 + ((value - size_min) / (size_max - size_min)) * 320.0

    for point in points:
        color = suite_palette.get(point["suite"], "#555555")
        x_value = -point["x"] if invert_x else point["x"]
        ax.scatter(
            [x_value],
            [point["y"]],
            s=scale_size(point["size"]),
            color=color,
            alpha=0.78,
            edgecolors="#fffaf2",
            linewidths=1.8,
            zorder=3,
        )
        ax.annotate(point["label"], (x_value, point["y"]), xytext=(8, 8), textcoords="offset points", fontsize=8, color="#2f2a24")

    ax.set_xlabel(x_label, color="#4d4439")
    ax.set_ylabel(y_label, color="#4d4439")
    ax.grid(True, linestyle="--", alpha=0.25, color="#8f8578")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    if invert_x:
        ticks = ax.get_xticks()
        ax.set_xticks(ticks)
        ax.set_xticklabels([f"{abs(tick):.2f}" for tick in ticks])

    handles = []
    labels = []
    for suite, color in sorted(suite_palette.items()):
        handle = pyplot.Line2D([0], [0], marker="o", color="none", markerfacecolor=color, markeredgecolor="#fffaf2", markersize=8)
        handles.append(handle)
        labels.append(suite)
    if handles:
        ax.legend(handles, labels, frameon=False, fontsize=9, loc="best")

    svg = _figure_to_svg(fig)
    pyplot.close(fig)
    return svg
