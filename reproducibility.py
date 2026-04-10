import json
import os
import platform
import random
import socket
import subprocess
import sys
from pathlib import Path


def seed_global_randomness(seed):
    random.seed(seed)


def get_git_metadata(project_root):
    project_root = Path(project_root)
    metadata = {
        "commit": "unknown",
        "short_commit": "unknown",
        "branch": "unknown",
        "dirty": None,
    }
    try:
        metadata["commit"] = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=project_root,
            text=True,
        ).strip()
        metadata["short_commit"] = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=project_root,
            text=True,
        ).strip()
        metadata["branch"] = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=project_root,
            text=True,
        ).strip()
        metadata["dirty"] = bool(
            subprocess.check_output(
                ["git", "status", "--porcelain"],
                cwd=project_root,
                text=True,
            ).strip()
        )
    except Exception as exc:
        metadata["error"] = str(exc)
    return metadata


def get_runtime_environment():
    return {
        "python_version": sys.version,
        "python_implementation": platform.python_implementation(),
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "hostname": socket.gethostname(),
        "cpu_count": os.cpu_count(),
    }


def get_model_identity(model_config):
    identity = {
        "backend": model_config["backend"],
        "configured_model_name": model_config["model_name"],
        "configured_model_digest": model_config.get("model_digest"),
        "generation": dict(model_config.get("generation", {})),
    }

    if model_config["backend"] != "ollama":
        return identity

    try:
        body = subprocess.check_output(
            ["ollama", "show", "--json", model_config["model_name"]],
            text=True,
            timeout=10,
        )
        payload = json.loads(body)
        identity["provider_metadata"] = payload
        identity["resolved_model_digest"] = _find_first_key(payload, {"digest", "model_digest"})
    except Exception as exc:
        identity["provider_lookup_error"] = str(exc)
    return identity


def build_trial_schedule(architectures, games, experiment_config, global_seed, baseline_bots):
    schedule = []
    num_trials = experiment_config["num_trials"]
    phases = experiment_config["phases"]
    enabled_games = set(experiment_config.get("enabled_games", games.keys()))

    if phases.get("internal_ai_tournament"):
        for trial in range(1, num_trials + 1):
            for left_index in range(len(architectures)):
                for right_index in range(left_index + 1, len(architectures)):
                    arch1 = architectures[left_index]
                    arch2 = architectures[right_index]
                    if "blotto" in enabled_games:
                        schedule.append(
                            {
                                "phase": "internal_ai_tournament",
                                "trial": trial,
                                "game": "blotto",
                                "seed": stable_seed(global_seed, "blotto_match", trial, arch1["id"], arch2["id"]),
                                "participants": [arch1["id"], arch2["id"]],
                            }
                        )
                    if "connect4" in enabled_games:
                        schedule.append(
                            {
                                "phase": "internal_ai_tournament",
                                "trial": trial,
                                "game": "connect4",
                                "seed": stable_seed(global_seed, "connect4_match", trial, arch1["id"], arch2["id"]),
                                "participants": [arch1["id"], arch2["id"]],
                            }
                        )

    if phases.get("blotto_vs_bots") and "blotto" in enabled_games:
        for trial in range(1, num_trials + 1):
            for architecture_spec in architectures:
                for baseline_bot in baseline_bots:
                    schedule.append(
                        {
                            "phase": "blotto_vs_bots",
                            "trial": trial,
                            "game": "blotto",
                            "seed": stable_seed(global_seed, baseline_bot, trial, architecture_spec["id"]),
                            "participants": [architecture_spec["id"], baseline_bot],
                        }
                    )

    if phases.get("connect4_oracle_accuracy") and "connect4" in enabled_games:
        for trial in range(1, num_trials + 1):
            for architecture_spec in architectures:
                schedule.append(
                    {
                        "phase": "connect4_oracle_accuracy",
                        "trial": trial,
                        "game": "connect4",
                        "seed": stable_seed(global_seed, "oracle_accuracy", trial, architecture_spec["id"]),
                        "participants": [architecture_spec["id"], "oracle"],
                    }
                )

    return {
        "global_seed": global_seed,
        "seed_function": "stable_seed(global_seed, *parts) using sha256(parts)[:8]",
        "schedule": schedule,
        "games": sorted(enabled_games),
    }


def stable_seed(global_seed, *parts):
    joined = "::".join(str(part) for part in parts)
    digest = __import__("hashlib").sha256(joined.encode("utf-8")).hexdigest()
    return (global_seed + int(digest[:8], 16)) % (2 ** 32)


def _find_first_key(value, keys):
    if isinstance(value, dict):
        for key, nested in value.items():
            if key in keys:
                return nested
            found = _find_first_key(nested, keys)
            if found is not None:
                return found
    elif isinstance(value, list):
        for nested in value:
            found = _find_first_key(nested, keys)
            if found is not None:
                return found
    return None
