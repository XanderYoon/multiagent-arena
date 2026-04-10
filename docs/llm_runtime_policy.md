# LLM Runtime Policy

## Reasoning Trace Decision

For this repository, "reasoning traces" means both:

- Model-visible text: the structured `reasoning` field returned by the model.
- Runtime metadata: the raw response, parsed response, parse failure reason, retry history, and latency or token metadata when available.

This policy is reflected in the prompt config and in per-call runtime logs.

## Backend Policy

The runtime currently supports:

- `ollama` for real local inference
- `mock` for deterministic local validation without a live model server

Additional backends should preserve the same contract: rendered prompts in, raw text plus backend metadata out.
