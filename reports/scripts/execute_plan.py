import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_json(path_value):
    path = Path(path_value)
    if not path.is_absolute():
        path = (PROJECT_ROOT / path).resolve()
    return json.loads(path.read_text(encoding="utf-8")), path


def build_benchmark_config(plan_entry, template_config):
    merged = json.loads(json.dumps(template_config))
    overrides = plan_entry.get("benchmark_overrides", {})
    for key, value in overrides.items():
        if key == "game_configs":
            merged.setdefault("game_configs", {}).update(value)
        else:
            merged[key] = value
    return merged


def execute_plan(plan_path, run_filter=None, dry_run=False):
    plan, _ = load_json(plan_path)
    template_config, _ = load_json(plan["benchmark_template"])
    selected = [
        entry for entry in plan["runs"]
        if run_filter is None or entry["run_id"] in run_filter
    ]

    results = []
    for entry in selected:
        benchmark_config = build_benchmark_config(entry, template_config)
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as handle:
            temp_path = Path(handle.name)
            handle.write(json.dumps(benchmark_config, indent=2))

        command = [sys.executable, str(PROJECT_ROOT / "main.py"), "--config", str(temp_path)]
        result = {
            "run_id": entry["run_id"],
            "stage": entry.get("stage"),
            "benchmark_config_path": str(temp_path),
            "command": command,
        }

        if dry_run:
            result["status"] = "dry_run"
        else:
            completed = subprocess.run(command, cwd=PROJECT_ROOT)
            result["status"] = "ok" if completed.returncode == 0 else "failed"
            result["returncode"] = completed.returncode
        results.append(result)
    return results


def main():
    parser = argparse.ArgumentParser(description="Execute the section 14 experiment plan.")
    parser.add_argument(
        "--plan",
        default="config/experiments/section14_run_matrix.json",
        help="Path to the machine-readable run plan.",
    )
    parser.add_argument(
        "--run-id",
        action="append",
        default=None,
        help="Optional run_id filter. Can be provided multiple times.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the resolved run commands without executing them.",
    )
    args = parser.parse_args()

    results = execute_plan(args.plan, run_filter=set(args.run_id) if args.run_id else None, dry_run=args.dry_run)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
