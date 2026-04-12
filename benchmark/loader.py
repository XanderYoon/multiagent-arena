import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def resolve_repo_path(path_value):
    path = Path(path_value)
    if path.is_absolute():
        return path
    return (PROJECT_ROOT / path).resolve()


def load_json(path_value):
    path = resolve_repo_path(path_value)
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle), path


def load_benchmark_bundle(config_path):
    benchmark_config, benchmark_path = load_json(config_path)
    model_configs = {}
    model_paths = {}
    default_model_alias = benchmark_config.get("default_model_alias", "default")
    if "model_configs" in benchmark_config:
        for alias, model_path in benchmark_config["model_configs"].items():
            model_configs[alias], model_paths[alias] = load_json(model_path)
    else:
        model_configs[default_model_alias], model_paths[default_model_alias] = load_json(benchmark_config["model_config"])
    experiment_config, experiment_path = load_json(benchmark_config["experiment_config"])
    prompt_config, prompt_path = load_json(benchmark_config["prompt_config"])
    architecture_config, architecture_path = load_json(benchmark_config["architecture_config"])

    games = {}
    game_paths = {}
    for game_name, game_path in benchmark_config["game_configs"].items():
        games[game_name], game_paths[game_name] = load_json(game_path)

    return {
        "benchmark": benchmark_config,
        "model": model_configs[default_model_alias],
        "models": model_configs,
        "default_model_alias": default_model_alias,
        "prompt": prompt_config,
        "architectures": architecture_config,
        "experiment": experiment_config,
        "games": games,
        "paths": {
            "benchmark": benchmark_path,
            "model": model_paths[default_model_alias],
            "models": model_paths,
            "prompt": prompt_path,
            "architectures": architecture_path,
            "experiment": experiment_path,
            "games": game_paths,
        },
    }
