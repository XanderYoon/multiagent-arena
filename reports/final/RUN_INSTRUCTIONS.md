# Reproducible Run Instructions

## Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Start Ollama and ensure the required Qwen models are installed:

```bash
bash tools/install_qwen_models.sh section14_3
ollama serve
```

## Section 14.3 Runs

## Regenerate Final Deliverables

```bash
python3 tools/generate_final_deliverables.py
```

## Selected Run IDs
