# Contributing

Thanks for helping improve the SyFlow NDC Go/No-Go platform.

## Setup

```bash
conda env create -f environment.yml
conda activate syflow-ndc
pip install -e ".[dev]"
cp .env.example .env
```

Python 3.11 matches `environment.yml`. The CLI resolves `targets/` and the default `runs/` directory from the repository root, so use an editable install (`pip install -e .`).

## Checks

```bash
ruff check src scripts
python scripts/smoke_check.py
python -m src --help
```

`ruff` is configured in `pyproject.toml`. Fix lint issues that do not change behavior. Do not change gate thresholds, dossier expectations, or agent tool allowlists unless that change is the point of the pull request.

## Pull requests

- Open a pull request against `main`.
- Describe what changed and how you verified it.
- Keep claims tied to a file, command, or dossier field. Do not add measured results that are not already in the repository.
- Gate thresholds stay frozen before an experiment. A model score does not replace a missing assay.
- Wet-lab claims need an ELN or LIMS batch id.

## Layout

- CLI: `src/cli.py` (`syflow`, `python -m src`)
- Helper scripts: `scripts/`
- Slide decks: `docs/slides/`
- Agent prompts: `src/agents/<name>/system_prompt.md`
