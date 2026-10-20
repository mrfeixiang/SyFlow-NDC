## Summary

## File moves

| Old path | New path |
|---|---|
| | |

## How to verify

```bash
pip install -e ".[dev]"
ruff check src scripts
python scripts/smoke_check.py
python -m src --help
syflow --help
```

## Open questions

-
