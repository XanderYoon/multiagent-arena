import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from reports.scripts.final_deliverables import build_figures, discover_key_section14_3_runs
from reports.scripts.report_section14_3 import build_section14_3_rows


def _ensure_matplotlib_available():
    try:
        import matplotlib  # noqa: F401
    except ImportError as exc:
        raise SystemExit(
            "matplotlib is required for this one-time export. Install dependencies from requirements.txt first."
        ) from exc


def generate_matplotlib_final_figures(experiments_root, figures_dir, suffix):
    _ensure_matplotlib_available()

    selected_runs = discover_key_section14_3_runs(experiments_root)
    rows = build_section14_3_rows(selected_runs)
    figures = build_figures(selected_runs, rows)

    figures_dir = Path(figures_dir)
    figures_dir.mkdir(parents=True, exist_ok=True)

    written = []
    for filename, svg in figures.items():
        target_name = filename.replace(".svg", f"{suffix}.svg")
        target_path = figures_dir / target_name
        target_path.write_text(svg, encoding="utf-8")
        written.append(str(target_path))

    return {
        "selected_runs": [run_dir.name for run_dir in selected_runs],
        "figure_count": len(written),
        "figures_dir": str(figures_dir),
        "written_files": written,
    }


def main():
    parser = argparse.ArgumentParser(
        description="One-time matplotlib export for the Section 14.3 final figures."
    )
    parser.add_argument(
        "--experiments-root",
        default=str(PROJECT_ROOT / "reports" / "runs" / "experiment_runs"),
        help="Directory containing run_* experiment folders.",
    )
    parser.add_argument(
        "--figures-dir",
        default=str(PROJECT_ROOT / "reports" / "final" / "figures"),
        help="Directory where matplotlib-rendered figure copies should be written.",
    )
    parser.add_argument(
        "--suffix",
        default="_matplotlib",
        help="Suffix inserted before .svg for generated matplotlib copies.",
    )
    args = parser.parse_args()

    result = generate_matplotlib_final_figures(
        experiments_root=args.experiments_root,
        figures_dir=args.figures_dir,
        suffix=args.suffix,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
