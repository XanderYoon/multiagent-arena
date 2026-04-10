import json
import re
import time
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parent
_RUNTIMES = {}
_DEFAULT_RUNTIME_ALIAS = "default"


def extract_json(llm_output):
    try:
        match = re.search(r"\{[\s\S]*\}", llm_output)
        return json.loads(match.group(0)) if match else None
    except Exception:
        return None


def validate_agent_response(data, task):
    if not isinstance(data, dict):
        return False, "parsed_response_not_object"
    if "move" not in data:
        return False, "missing_move"
    if "reasoning" in data and not isinstance(data["reasoning"], str):
        return False, "reasoning_not_string"

    game_name = task.get("game")
    move = data["move"]
    if game_name == "blotto":
        if not isinstance(move, list):
            return False, "blotto_move_not_list"
        if len(move) != task["battlefields"]:
            return False, "blotto_wrong_length"
        if any(not isinstance(value, int) or value < 0 for value in move):
            return False, "blotto_non_integer_or_negative"
        if sum(move) != task["troop_budget"]:
            return False, "blotto_wrong_sum"
        return True, None

    if game_name == "connect4":
        if not isinstance(move, int):
            return False, "connect4_move_not_int"
        valid_columns = task.get("valid_columns")
        if valid_columns is not None and move not in valid_columns:
            return False, "connect4_invalid_column"
        return True, None

    return True, None


class PromptManager:
    def __init__(self, prompt_catalog, selected_family=None):
        self.prompt_catalog = prompt_catalog
        family_id = selected_family or prompt_catalog["default_family"]
        family_config = prompt_catalog["families"][family_id]
        self.prompt_config = family_config
        self.family_id = family_id
        self.family = family_config["family"]
        self.version = family_config["version"]
        self.internal_reasoning_storage = prompt_catalog["internal_reasoning_storage"]
        self.reasoning_trace_policy = family_config["reasoning_trace_policy"]
        self.templates = {}
        template_root = PROJECT_ROOT / family_config["template_root"]

        for name, relative_path in family_config["templates"].items():
            path = template_root / relative_path
            self.templates[name] = path.read_text(encoding="utf-8")

    def render(self, template_name, **context):
        if template_name not in self.templates:
            raise KeyError(f"Unknown prompt template: {template_name}")
        return self.templates[template_name].format(**context)

    def render_for_game(self, template_name, game_name, **context):
        specific_name = f"{template_name}_{game_name}"
        if specific_name in self.templates:
            return self.templates[specific_name].format(**context)
        return self.render(template_name, **context)


class JSONLCallLogger:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text("", encoding="utf-8")

    def log(self, record):
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")


class LLMRuntime:
    def __init__(self, model_config, prompt_config, call_log_path, prompt_family=None):
        self.model_config = model_config
        self.prompt_manager = PromptManager(prompt_config, selected_family=prompt_family)
        self.call_logger = JSONLCallLogger(call_log_path)
        self.backend = model_config["backend"]
        self.model_name = model_config["model_name"]
        self.api_url = model_config.get("api_url")
        self.timeout_seconds = model_config.get("timeout_seconds", 60)
        self.retry_attempts = model_config.get("retry_attempts", 1)
        self.generation = dict(model_config.get("generation", {}))
        self.mock_defaults = dict(model_config.get("mock_defaults", {}))
        self.call_index = 0

    def invoke(self, system_prompt, user_prompt, task, metadata):
        self.call_index += 1
        attempts = []

        for attempt in range(1, self.retry_attempts + 1):
            started_at = time.time()
            try:
                raw_response, backend_details = self._send_request(system_prompt, user_prompt, task)
                request_error = None
            except Exception as exc:
                raw_response = "{}"
                backend_details = {"provider_response": None}
                request_error = str(exc)
            latency_ms = round((time.time() - started_at) * 1000, 3)
            parsed_response = extract_json(raw_response)
            if request_error:
                is_valid = False
                parse_failure_reason = "request_error"
            else:
                is_valid, parse_failure_reason = validate_agent_response(parsed_response, task)
            attempt_record = {
                "attempt": attempt,
                "latency_ms": latency_ms,
                "raw_response": raw_response,
                "parsed_response": parsed_response,
                "parse_failure_reason": parse_failure_reason,
                "request_error": request_error,
                "backend_details": backend_details,
            }
            attempts.append(attempt_record)
            if is_valid:
                break

        final_attempt = attempts[-1]
        self.call_logger.log(
            {
                "call_index": self.call_index,
                "backend": self.backend,
                "model_name": self.model_name,
                "prompt_family_id": self.prompt_manager.family_id,
                "prompt_family": self.prompt_manager.family,
                "prompt_version": self.prompt_manager.version,
                "internal_reasoning_storage": self.prompt_manager.internal_reasoning_storage,
                "metadata": metadata,
                "task": {"game": task.get("game"), "role": task.get("role")},
                "prompt": {"system": system_prompt, "user": user_prompt},
                "attempts": attempts,
                "final_parsed_response": final_attempt["parsed_response"],
                "final_parse_failure_reason": final_attempt["parse_failure_reason"],
            }
        )
        return {
            "call_index": self.call_index,
            "parsed_response": final_attempt["parsed_response"],
            "parse_failure_reason": final_attempt["parse_failure_reason"],
            "attempts": attempts,
            "prompt_family_id": self.prompt_manager.family_id,
            "prompt_family": self.prompt_manager.family,
            "prompt_version": self.prompt_manager.version,
        }

    def _send_request(self, system_prompt, user_prompt, task):
        if self.backend == "ollama":
            return self._send_ollama_request(system_prompt, user_prompt)
        if self.backend == "mock":
            return self._send_mock_response(task)
        raise ValueError(f"Unsupported backend: {self.backend}")

    def _send_ollama_request(self, system_prompt, user_prompt):
        options = dict(self.generation)
        if "max_tokens" in options and "num_predict" not in options:
            options["num_predict"] = options.pop("max_tokens")

        payload = {
            "model": self.model_name,
            "prompt": f"SYSTEM: {system_prompt}\n\nUSER: {user_prompt}",
            "stream": False,
        }
        if options:
            payload["options"] = options

        response = requests.post(self.api_url, json=payload, timeout=self.timeout_seconds)
        response.raise_for_status()
        body = response.json()
        return body.get("response", "{}"), {
            "provider_response": {
                "prompt_eval_count": body.get("prompt_eval_count"),
                "eval_count": body.get("eval_count"),
                "total_duration": body.get("total_duration"),
                "load_duration": body.get("load_duration"),
                "prompt_eval_duration": body.get("prompt_eval_duration"),
                "eval_duration": body.get("eval_duration"),
            }
        }

    def _send_mock_response(self, task):
        reasoning = self.mock_defaults.get("reasoning", "Mock backend produced a deterministic legal move.")
        if task["game"] == "blotto":
            battlefields = task["battlefields"]
            troop_budget = task["troop_budget"]
            move = [troop_budget // battlefields for _ in range(battlefields)]
            move[-1] += troop_budget - sum(move)
        elif task["game"] == "connect4":
            valid_columns = task.get("valid_columns") or [0]
            move = valid_columns[0]
        else:
            move = None
        return json.dumps({"reasoning": reasoning, "move": move}), {
            "provider_response": {"mock_backend": True}
        }


def configure_runtime(model_config, prompt_config, call_log_path, prompt_family=None, alias="default", reset=False):
    global _RUNTIMES, _DEFAULT_RUNTIME_ALIAS
    if reset:
        _RUNTIMES = {}
    _RUNTIMES[alias] = LLMRuntime(model_config, prompt_config, call_log_path, prompt_family=prompt_family)
    if not _RUNTIMES or len(_RUNTIMES) == 1 or alias == "default":
        _DEFAULT_RUNTIME_ALIAS = alias


def configure_runtime_registry(model_configs, prompt_config, call_log_dir, prompt_family=None, default_alias=None):
    global _RUNTIMES, _DEFAULT_RUNTIME_ALIAS
    _RUNTIMES = {}
    call_log_dir = Path(call_log_dir)
    call_log_dir.mkdir(parents=True, exist_ok=True)
    for alias, model_config in model_configs.items():
        _RUNTIMES[alias] = LLMRuntime(
            model_config,
            prompt_config,
            call_log_dir / f"llm_calls_{alias}.jsonl",
            prompt_family=prompt_family,
        )
    _DEFAULT_RUNTIME_ALIAS = default_alias or next(iter(model_configs.keys()))


def get_runtime(alias=None):
    selected_alias = alias or _DEFAULT_RUNTIME_ALIAS
    if selected_alias not in _RUNTIMES:
        raise RuntimeError(f"LLM runtime has not been configured for alias: {selected_alias}")
    return _RUNTIMES[selected_alias]
