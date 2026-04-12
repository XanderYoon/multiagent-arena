import argparse
from pathlib import Path

try:
    from .reporting import collect_runs, write_report_bundle
except ImportError:
    from reporting import collect_runs, write_report_bundle


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description="Generate section 14 analysis artifacts from completed runs.")
    parser.add_argument(
        "--experiments-root",
        default=str(PROJECT_ROOT / "runs" / "experiment_runs"),
        help="Directory containing run_* experiment outputs.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "reports" / "latest"),
        help="Directory for generated analysis artifacts.",
    )
    args = parser.parse_args()

    runs = collect_runs(args.experiments_root)
    write_report_bundle(args.output_dir, runs)
    print(f"Wrote analysis bundle for {len(runs)} runs to {args.output_dir}")


if __name__ == "__main__":
    main()
