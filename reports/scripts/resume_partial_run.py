import argparse
import json
import re
from collections import Counter
from pathlib import Path

import benchmark.agents as runtime_agents
from benchmark.agents import PromptManager, configure_runtime_registry
from benchmark.architectures import build_architecture_registry
from benchmark.loader import load_json
from benchmark.experiment_logging import (
    build_game_outcome_records,
    build_trial_metadata_records,
    build_turn_records,
    write_csv,
    write_jsonl,
)
from benchmark.game_engine import BlottoEnvironment, Connect4Environment
from main import (
    PROJECT_ROOT,
    ProgressTracker,
    blotto_match,
    build_blotto_baseline_bot,
    connect4_ai_vs_ai,
    now_iso,
    test_connect4_accuracy,
    write_json,
)
from benchmark.metrics import aggregate_run_metrics, write_metrics_csv


PROGRESS_PATTERN = re.compile(r"^\[PROGRESS\] Finished (\d+)/(\d+)", re.M)


class NullLogger:
    def log(self, _txt):
        return None


class AppendLogger:
    def __init__(self, paths):
        self.paths = [Path(path) for path in paths]
        for path in self.paths:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()

    def log(self, txt):
        line = str(txt)
        for path in self.paths:
            with path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
        print(line)


class ResumeProgressTracker(ProgressTracker):
    def __init__(self, trial_schedule, completed_entries):
        super().__init__(trial_schedule)
        self.completed = completed_entries
        counts = Counter(entry["phase"] for entry in trial_schedule["schedule"][:completed_entries])
        for phase, count in counts.items():
            self.phase_completed[phase] = count


class ReplayRuntime:
    def __init__(self, model_config, prompt_catalog, records, prompt_family):
        self.model_name = model_config["model_name"]
        self.prompt_manager = PromptManager(prompt_catalog, selected_family=prompt_family)
        self.records = records
        self.cursor = 0

    def invoke(self, system_prompt, user_prompt, task, metadata):
        if self.cursor >= len(self.records):
            raise RuntimeError(
                f"Replay log exhausted for model {self.model_name} at cursor {self.cursor + 1}"
            )
        record = self.records[self.cursor]
        self.cursor += 1
        return {
            "call_index": record["call_index"],
            "parsed_response": record["final_parsed_response"],
            "parse_failure_reason": record["final_parse_failure_reason"],
            "attempts": record["attempts"],
            "prompt_family_id": record["prompt_family_id"],
            "prompt_family": record["prompt_family"],
            "prompt_version": record["prompt_version"],
        }


def load_run_config(run_dir):
    config_dir = Path(run_dir) / "config"
    benchmark, _ = load_json(config_dir / "benchmark.json")
    prompt_catalog, _ = load_json(config_dir / "prompt_catalog.json")
    architecture_config, _ = load_json(config_dir / "architectures.json")
    experiment_config, _ = load_json(config_dir / "experiment.json")
    model_config, _ = load_json(config_dir / "model.json")
    games = {}
    models = {}

    models_dir = config_dir / "models"
    if models_dir.exists():
        for model_path in sorted(models_dir.glob("*.json")):
            models[model_path.stem], _ = load_json(model_path)
    else:
        models["default"] = model_config

    games_dir = config_dir / "games"
    for game_path in sorted(games_dir.glob("*.json")):
        games[game_path.stem], _ = load_json(game_path)

    return {
        "benchmark": benchmark,
        "prompt_catalog": prompt_catalog,
        "architectures": architecture_config,
        "experiment": experiment_config,
        "model": model_config,
        "models": models,
        "games": games,
    }


def load_replay_records(log_dir):
    records = {}
    for path in sorted(Path(log_dir).glob("llm_calls_*.jsonl")):
        alias = path.stem.removeprefix("llm_calls_")
        with path.open("r", encoding="utf-8") as handle:
            records[alias] = [json.loads(line) for line in handle if line.strip()]
    return records


def detect_completed_entries(results_path):
    text = Path(results_path).read_text(encoding="utf-8", errors="ignore")
    matches = PROGRESS_PATTERN.findall(text)
    if not matches:
        return 0, None
    completed, total = matches[-1]
    return int(completed), int(total)


def trim_results_log(path, completed_entries):
    text = Path(path).read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()
    target = f"[PROGRESS] Finished {completed_entries}/"
    cutoff = None
    for index, line in enumerate(lines):
        if line.startswith(target):
            cutoff = index
    if cutoff is None:
        return
    trimmed = "\n".join(lines[: cutoff + 1])
    if trimmed:
        trimmed += "\n"
    Path(path).write_text(trimmed, encoding="utf-8")


def truncate_jsonl(path, keep_lines):
    jsonl_path = Path(path)
    lines = jsonl_path.read_text(encoding="utf-8").splitlines()
    if len(lines) <= keep_lines:
        return
    trimmed = "\n".join(lines[:keep_lines])
    if trimmed:
        trimmed += "\n"
    jsonl_path.write_text(trimmed, encoding="utf-8")


def install_replay_runtimes(models, prompt_catalog, prompt_family, replay_records):
    runtime_agents._RUNTIMES = {}
    for alias, model_config in models.items():
        runtime_agents._RUNTIMES[alias] = ReplayRuntime(
            model_config,
            prompt_catalog,
            replay_records.get(alias, []),
            prompt_family,
        )
    runtime_agents._DEFAULT_RUNTIME_ALIAS = next(iter(models.keys()))


def execute_entry(entry, architectures, games, logger):
    if entry["phase"] == "internal_ai_tournament":
        arch1 = next(arch for arch in architectures if arch["id"] == entry["participants"][0])
        arch2 = next(arch for arch in architectures if arch["id"] == entry["participants"][1])
        if entry["game"] == "blotto":
            return blotto_match(arch1, arch2, entry["trial"], logger, games["blotto"], entry["seed"])
        return connect4_ai_vs_ai(arch1, arch2, entry["trial"], logger, games["connect4"], entry["seed"])

    if entry["phase"] == "blotto_vs_bots":
        troop_budget = games["blotto"]["troop_budget"]
        battlefields = games["blotto"]["battlefields"]
        architecture_spec = next(arch for arch in architectures if arch["id"] == entry["participants"][0])
        baseline_bot = entry["participants"][1]
        return blotto_match(
            architecture_spec,
            build_blotto_baseline_bot(baseline_bot, troop_budget, battlefields),
            entry["trial"],
            logger,
            games["blotto"],
            entry["seed"],
        )

    if entry["phase"] == "connect4_oracle_accuracy":
        architecture_spec = next(arch for arch in architectures if arch["id"] == entry["participants"][0])
        return test_connect4_accuracy(architecture_spec, entry["trial"], logger, games["connect4"], entry["seed"])

    raise ValueError(f"Unsupported phase: {entry['phase']}")


def append_summary_record(summary, entry, record):
    summary["phases"][entry["phase"]].append(record)


def export_structured_run_logs(run_dir, summary):
    log_dir = Path(run_dir) / "logs"
    summary_dir = Path(run_dir) / "summaries"

    trial_records = build_trial_metadata_records(summary)
    turn_records = build_turn_records(summary)
    outcome_records = build_game_outcome_records(summary)

    write_jsonl(log_dir / "trial_records.jsonl", trial_records)
    write_jsonl(log_dir / "turn_records.jsonl", turn_records)
    write_jsonl(log_dir / "game_outcomes.jsonl", outcome_records)

    write_csv(summary_dir / "trial_records.csv", trial_records)
    write_csv(summary_dir / "turn_records.csv", turn_records)
    write_csv(summary_dir / "game_outcomes.csv", outcome_records)


def main():
    parser = argparse.ArgumentParser(description="Resume a partially completed benchmark run in place.")
    parser.add_argument("--run-dir", required=True, help="Path to the existing run_* directory.")
    args = parser.parse_args()

    run_dir = (PROJECT_ROOT / args.run_dir).resolve() if not Path(args.run_dir).is_absolute() else Path(args.run_dir)
    run_config = load_run_config(run_dir)
    manifest_path = run_dir / "metadata" / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    schedule = manifest["trial_schedule"]
    completed_entries, total_entries = detect_completed_entries(run_dir / "logs" / "results.txt")
    if total_entries is None:
        raise RuntimeError("Could not detect completed progress from results log.")
    if completed_entries >= total_entries:
        raise RuntimeError(f"Run already complete: {completed_entries}/{total_entries}.")

    replay_records = load_replay_records(run_dir / "logs")
    prompt_family = manifest["prompt_family_id"]
    install_replay_runtimes(run_config["models"], run_config["prompt_catalog"], prompt_family, replay_records)

    architectures = build_architecture_registry(
        run_config["architectures"],
        run_config["experiment"]["architectures"],
    )
    summary = {
        "run_id": manifest["run_id"],
        "benchmark_name": manifest["benchmark_name"],
        "model": manifest["model"],
        "backend": manifest["backend"],
        "global_seed": manifest["global_seed"],
        "code_version": manifest["code_version"],
        "model_identity": manifest["model_identity"],
        "runtime_environment": manifest["runtime_environment"],
        "prompt_family_id": manifest["prompt_family_id"],
        "prompt_family": manifest["prompt_family"],
        "prompt_version": manifest["prompt_version"],
        "internal_reasoning_storage": manifest["internal_reasoning_storage"],
        "trial_schedule": {
            "global_seed": manifest["seed_policy"]["global_seed"],
            "seed_function": manifest["seed_policy"]["child_seed_strategy"],
            "schedule": schedule,
            "games": sorted(run_config["games"].keys()),
        },
        "phases": {
            "internal_ai_tournament": [],
            "blotto_vs_bots": [],
            "connect4_oracle_accuracy": [],
        },
    }

    replay_logger = NullLogger()
    for entry in schedule[:completed_entries]:
        record = execute_entry(entry, architectures, run_config["games"], replay_logger)
        append_summary_record(summary, entry, record)

    consumed_counts = {}
    for alias, runtime in runtime_agents._RUNTIMES.items():
        consumed_counts[alias] = runtime.cursor

    for alias, keep_lines in consumed_counts.items():
        truncate_jsonl(run_dir / "logs" / f"llm_calls_{alias}.jsonl", keep_lines)

    trim_results_log(run_dir / "logs" / "results.txt", completed_entries)
    benchmark_latest = PROJECT_ROOT / run_config["benchmark"]["latest_results_path"]
    if benchmark_latest.exists():
        trim_results_log(benchmark_latest, completed_entries)

    configure_runtime_registry(
        run_config["models"],
        run_config["prompt_catalog"],
        run_dir / "logs",
        prompt_family=prompt_family,
        default_alias=manifest.get("default_model_alias"),
        append=True,
    )

    logger = AppendLogger([run_dir / "logs" / "results.txt", benchmark_latest])
    progress = ResumeProgressTracker({"schedule": schedule}, completed_entries)

    for entry in schedule[completed_entries:]:
        progress.start(logger, entry)
        record = execute_entry(entry, architectures, run_config["games"], logger)
        append_summary_record(summary, entry, record)
        progress.finish(logger, entry)

    summary["completed_at"] = now_iso()
    write_json(run_dir / "summaries" / "summary.json", summary)
    export_structured_run_logs(run_dir, summary)

    metrics_summary = aggregate_run_metrics(summary)
    write_json(run_dir / "summaries" / "metrics.json", metrics_summary)
    write_metrics_csv(run_dir / "summaries" / "aggregate_tables.csv", metrics_summary["aggregate_tables"])
    write_metrics_csv(run_dir / "summaries" / "architecture_summaries.csv", metrics_summary["architecture_summaries"])
    write_metrics_csv(run_dir / "summaries" / "model_summaries.csv", metrics_summary["model_summaries"])
    write_metrics_csv(run_dir / "summaries" / "prompt_summaries.csv", metrics_summary["prompt_summaries"])


if __name__ == "__main__":
    main()
