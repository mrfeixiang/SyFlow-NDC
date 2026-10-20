# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `pyproject.toml` with the `syflow` console script, dependencies aligned with `environment.yml`, and Ruff settings.
- MIT `LICENSE`, `CITATION.cff`, `CONTRIBUTING.md`, and this changelog.
- GitHub Actions workflow that runs Ruff and `scripts/smoke_check.py`.
- Bug and feature issue templates, and a pull request template.

### Changed

- Moved the CLI from `run_syflow.py` to `src/cli.py` (`python -m src` and `syflow`).
- Moved helper scripts into `scripts/`.
- Moved the English and Korean slide decks into `docs/slides/`.
- Pointed README, `CLAUDE.md`, and `.claude/skills/run-organization/SKILL.md` at the new paths.

## [0.1.0] - 2026-10-20

### Added

- Initial SyFlow NDC Go/No-Go platform: agent registry, G0–G5 gate definitions, dossier schemas, provenance utilities, and target dossiers.
