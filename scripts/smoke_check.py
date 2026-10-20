#!/usr/bin/env python3
"""Import and CLI smoke check for the SyFlow NDC package.

Confirms the registry, gate table, and ``python -m src`` entry point load.
The validate step writes only under a temporary runs directory.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

EXPECTED_AGENTS = {
    "cso",
    "target_patient",
    "nanobody_epitope",
    "delivery",
    "conjugation_payload",
    "translation_safety",
    "scientific_reviewer",
}
EXPECTED_GATES = {"G0", "G1", "G2", "G3", "G4", "G5"}


def check_imports() -> None:
    from src import __version__
    from src.agents.registry import AGENT_REGISTRY, build_specialist_agents
    from src.schemas.dossier import NDCDossier
    from src.schemas.evidence import EvidenceType
    from src.schemas.gate import GATE_DEFINITIONS, GateID
    from src.utils.plan_runner import validate_plan

    assert __version__
    assert set(AGENT_REGISTRY) == EXPECTED_AGENTS
    assert {gate.value for gate in GATE_DEFINITIONS} == EXPECTED_GATES
    assert {gate.value for gate in GateID} == EXPECTED_GATES
    assert len(EvidenceType) == 5
    assert NDCDossier.__name__ == "NDCDossier"

    plan = {
        "goal": "smoke",
        "steps": [
            {"id": "s1", "agent": "target_patient", "task": "smoke", "depends_on": []},
        ],
    }
    result = validate_plan(plan)
    assert result["valid"], result

    with tempfile.TemporaryDirectory() as tmp:
        agents = build_specialist_agents(Path(tmp))
    names = {agent["name"] for agent in agents}
    assert "cso" not in names
    assert names == EXPECTED_AGENTS - {"cso"}
    print(f"imports ok: {len(AGENT_REGISTRY)} agents, {len(GATE_DEFINITIONS)} gates")


def check_cli() -> None:
    help_run = subprocess.run(
        [sys.executable, "-m", "src", "--help"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if help_run.returncode != 0:
        sys.stderr.write(help_run.stderr)
        raise SystemExit(help_run.returncode)
    if "validate" not in help_run.stdout or "gate" not in help_run.stdout:
        raise SystemExit("CLI --help did not list validate/gate")
    print("python -m src --help ok")

    with tempfile.TemporaryDirectory() as tmp:
        env = os.environ.copy()
        env["SYFLOW_RUNS_DIR"] = tmp
        validate_run = subprocess.run(
            [
                sys.executable,
                "-m",
                "src",
                "validate",
                "--target",
                "egfrviii",
                "--query",
                "Evaluate EGFRvIII as NDC target for GBM",
            ],
            cwd=REPO_ROOT,
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )
        if validate_run.returncode != 0:
            sys.stderr.write(validate_run.stdout)
            sys.stderr.write(validate_run.stderr)
            raise SystemExit(validate_run.returncode)
        if "RUN INITIALIZED" not in validate_run.stdout:
            sys.stderr.write(validate_run.stdout)
            raise SystemExit("validate did not initialize a run")
    print("python -m src validate (temp runs dir) ok")


def main() -> None:
    check_imports()
    check_cli()
    print("smoke check passed")


if __name__ == "__main__":
    main()
