#!/usr/bin/env python3
"""Small-molecule inhibitor Go/No-Go commands.

Usage:
    syflow smi validate --target pnpla3
    python -m src.smi validate --target pnpla3
    python -m src.smi gate --target pnpla3 --gate M0 --dossier targets/pnpla3/smi_dossier.yaml

``validate`` and ``gate`` initialize a run. They do not call a model and
they do not assign Go, Hold, or No-Go.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from importlib.resources import files
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.smi.registry import AGENT_REGISTRY, build_specialist_agents
from src.smi.schemas.gate import SMI_GATE_DEFINITIONS, SMIGateID
from src.utils.paths import runs_directory, workspace_root
from src.utils.plan_runner import PlanRunner, validate_plan
from src.utils.session_audit import SessionAudit

TARGETS = yaml.safe_load(files("src.smi").joinpath("config/targets.yaml").read_text())["targets"]
PLATFORM = "syflow_smi"


def generate_run_id(target: str) -> str:
    """Generate YYYYMMDD_<target>_NNN under the writable runs directory."""
    date_str = datetime.now().strftime("%Y%m%d")
    prefix = f"{date_str}_{target}_"
    runs_dir = runs_directory()
    existing = sorted(runs_dir.glob(f"{prefix}*")) if runs_dir.exists() else []
    return f"{prefix}{len(existing) + 1:03d}"


def create_run_directory(run_id: str) -> Path:
    run_dir = runs_directory() / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "work").mkdir(exist_ok=True)
    (run_dir / "inputs").mkdir(exist_ok=True)
    return run_dir


def load_smi_dossier(target: str, dossier_path: str | None = None) -> dict:
    """Load a small-molecule dossier. Requires target_profile.gene_symbol."""
    if dossier_path:
        path = Path(dossier_path)
    else:
        path = workspace_root() / TARGETS[target]["dossier"]

    if not path.exists():
        raise ValueError(f"Dossier not found: {path}. Supply --dossier or SYFLOW_PROJECT_ROOT.")

    with open(path) as handle:
        dossier = yaml.safe_load(handle)
    profile = dossier.get("target_profile") if isinstance(dossier, dict) else None
    gene_symbol = profile.get("gene_symbol") if isinstance(profile, dict) else None
    if not isinstance(gene_symbol, str) or not gene_symbol.strip():
        raise ValueError(f"Dossier must contain target_profile.gene_symbol: {path}")
    return dossier


def build_smi_plan(target: str, dossier: dict) -> dict:
    """Build the M0–M5 analysis DAG.

    A ``compound`` mapping means one batch is in scope, so chemistry can
    start beside target biology. Recorded structures without that mapping
    stay a landscape review that waits for M0.
    """
    has_compound = isinstance(dossier.get("compound"), dict)
    steps: list[dict] = [{
        "id": "s1_target",
        "agent": "target_biology",
        "task": (
            f"Assess {target} as a small-molecule inhibitor target: "
            "patient subset, protein-level disease relevance, and on-target safety biology"
        ),
        "depends_on": [],
        "expected_outputs": ["target_biology.md"],
    }]

    if has_compound:
        chemistry_task = f"Assess identity, purity, and stability for the recorded {target} compound batch"
        chemistry_depends: list[str] = []
        chemistry_outputs = ["chemical_matter.md"]
    else:
        chemistry_task = (
            f"Review published chemical matter for {target}. "
            "Do not treat a SMILES string or a model score as a confirmed batch"
        )
        chemistry_depends = ["s1_target"]
        chemistry_outputs = ["chemical_landscape.md"]

    steps.append({
        "id": "s2_chemistry",
        "agent": "ligand_chemistry",
        "task": chemistry_task,
        "depends_on": chemistry_depends,
        "expected_outputs": chemistry_outputs,
    })
    steps.append({
        "id": "s3_potency",
        "agent": "pharmacology",
        "task": f"Assess orthogonal biochemical potency, selectivity, and mode for {target}",
        "depends_on": ["s2_chemistry"],
        "expected_outputs": ["biochemical_pharmacology.md"],
    })
    steps.append({
        "id": "s4_cellular",
        "agent": "pharmacology",
        "task": f"Assess cellular target engagement for {target}, separated from nonspecific cytotoxicity",
        "depends_on": ["s3_potency"],
        "expected_outputs": ["cellular_engagement.md"],
    })
    steps.append({
        "id": "s5_adme",
        "agent": "adme_exposure",
        "task": f"Assess measured ADME and whether exposure can meet a pre-registered free concentration for {target}",
        "depends_on": ["s2_chemistry"],
        "expected_outputs": ["adme_exposure.md"],
    })
    steps.append({
        "id": "s6_safety",
        "agent": "safety_translation",
        "task": f"Assess the pre-registered safety panel and therapeutic window for {target}",
        "depends_on": [step["id"] for step in steps],
        "expected_outputs": ["safety_window.md"],
    })
    steps.append({
        "id": "s7_review",
        "agent": "scientific_reviewer",
        "task": "Review all specialist outputs, identify gaps and conflicts, and withhold a verdict until evidence is sufficient",
        "depends_on": [step["id"] for step in steps],
        "expected_outputs": ["review_report.md"],
    })

    plan = {
        "module": "small_molecule_inhibitor",
        "goal": f"Validate {target} as a small-molecule inhibitor target and assess Go/No-Go status",
        "steps": steps,
    }
    validation = validate_plan(plan)
    if not validation["valid"]:
        print(f"Error: Invalid plan — {validation['error']}")
        sys.exit(1)
    plan["valid_order"] = validation["valid_order"]
    plan["parallel_groups"] = validation["parallel_groups"]
    return plan


def _write_inputs(run_dir: Path, dossier: dict, plan: dict, query: str | None = None) -> None:
    with open(run_dir / "inputs" / "dossier.yaml", "w") as handle:
        yaml.dump(dossier, handle, default_flow_style=False)
    with open(run_dir / "inputs" / "plan.json", "w") as handle:
        json.dump(plan, handle, indent=2)
    if query is not None:
        (run_dir / "inputs" / "query.txt").write_text(query)


def _prepare_tasks(run_dir: Path, run_id: str, target: str, plan: dict, audit: SessionAudit) -> None:
    step_map = {step["id"]: step for step in plan["steps"]}
    for group_idx, group in enumerate(plan["parallel_groups"]):
        print(f"\nPhase {group_idx + 1}: {group}")
        for step_id in group:
            step = step_map[step_id]
            agent_name = step["agent"]
            task = step["task"]
            print(f"  Preparing task for {agent_name}: {task[:60]}...")
            agent_workspace = run_dir / "work" / agent_name / "results"
            agent_workspace.mkdir(parents=True, exist_ok=True)
            task_file = agent_workspace / "task.md"
            task_file.write_text(
                f"# Task for {agent_name}\n\n{task}\n\n"
                f"Target: {target}\n"
                f"Module: small_molecule_inhibitor\n"
                f"Gate context: {AGENT_REGISTRY.get(agent_name, {}).get('description', '')}\n"
                f"Run: {run_id}\n"
            )
            audit.on_file_write(
                "cli_initializer", str(task_file), "report", f"Task description for {agent_name}"
            )


def cmd_validate(args: argparse.Namespace) -> None:
    """Initialize a small-molecule validation plan without executing agents."""
    target = args.target
    dossier = load_smi_dossier(target, args.dossier)
    run_id = generate_run_id(target)
    run_dir = create_run_directory(run_id)

    print(f"SyFlow SMI Validation: {target}")
    print(f"Run ID: {run_id}")
    print(f"Run directory: {run_dir}")
    print()

    plan = build_smi_plan(target, dossier)
    query = args.query or f"Evaluate {target} as a small-molecule inhibitor target"
    _write_inputs(run_dir, dossier, plan, query)

    print(f"Analysis plan: {len(plan['steps'])} steps")
    print(f"Parallel groups: {plan['parallel_groups']}")
    print()

    audit = SessionAudit(run_dir, run_id, platform=PLATFORM)
    audit.plan = PlanRunner.load(run_dir)
    agents = build_specialist_agents(run_dir)
    print(f"Agents ready: {[agent['name'] for agent in agents]}")
    print()
    print("=" * 60)
    print("PLAN INITIALIZATION (no model calls or gate decisions)")
    print("=" * 60)
    _prepare_tasks(run_dir, run_id, target, plan, audit)

    print()
    print("=" * 60)
    print("RUN INITIALIZED")
    print("=" * 60)
    print(f"\nRun directory: {run_dir}")
    print(f"Query: {query}")
    print("\nAgent SDK execution is not implemented; task files require a separate executor.")
    print("\nTo verify after completion:")
    print(f"  python -m src verify --run-id {run_id}")
    audit.finish_run("initialized")
    print(f"\nAudit saved: {run_dir / 'audit.json'}")


def cmd_gate(args: argparse.Namespace) -> None:
    """Initialize one M-gate assessment without assigning a verdict."""
    target = args.target
    gate_id = SMIGateID(args.gate)
    gate_def = SMI_GATE_DEFINITIONS[gate_id]
    dossier = load_smi_dossier(target, args.dossier)

    print(f"SyFlow SMI Gate Assessment: {gate_id.value} — {gate_def['name']}")
    print(f"Target: {target}")
    print(f"Required evidence: {gate_def['required_evidence']}")
    print(f"Hold triggers: {gate_def['hold_triggers']}")
    print(f"No-Go triggers: {gate_def['nogo_triggers']}")
    print(f"Primary agent: {gate_def['agent']}")
    print()

    run_id = generate_run_id(f"{target}_{args.gate}")
    run_dir = create_run_directory(run_id)
    plan = {
        "module": "small_molecule_inhibitor",
        "goal": f"Assess gate {gate_id.value} ({gate_def['name']}) for {target}",
        "steps": [
            {
                "id": "s1_specialist",
                "agent": gate_def["agent"],
                "task": f"Gather evidence for gate {gate_id.value}: {', '.join(gate_def['required_evidence'])}",
                "depends_on": [],
            },
            {
                "id": "s2_review",
                "agent": "scientific_reviewer",
                "task": f"Review evidence for gate {gate_id.value} and recommend a verdict only if required evidence is present",
                "depends_on": ["s1_specialist"],
            },
        ],
    }
    _write_inputs(run_dir, dossier, plan)
    audit = SessionAudit(run_dir, run_id, platform=PLATFORM)
    audit.plan = PlanRunner.load(run_dir)
    audit.finish_run("initialized")
    print(f"Gate assessment run initialized: {run_id}")
    print(f"Run directory: {run_dir}")


def add_commands(subparsers: argparse._SubParsersAction) -> None:
    """Attach validate and gate to a subparser collection."""
    validate = subparsers.add_parser(
        "validate", help="Initialize a small-molecule validation plan (no model execution)"
    )
    validate.add_argument("--target", required=True, choices=sorted(TARGETS))
    validate.add_argument("--query", help="Analysis query (default: auto-generated)")
    validate.add_argument("--dossier", help="Path to dossier YAML")
    validate.set_defaults(func=cmd_validate)

    gate = subparsers.add_parser(
        "gate", help="Initialize one M-gate assessment (no verdict)"
    )
    gate.add_argument("--target", required=True, choices=sorted(TARGETS))
    gate.add_argument("--gate", required=True, choices=[gate_id.value for gate_id in SMIGateID])
    gate.add_argument("--dossier", help="Path to dossier YAML")
    gate.set_defaults(func=cmd_gate)


def register_commands(subparsers: argparse._SubParsersAction) -> None:
    """Add ``smi`` under the top-level SyFlow parser."""
    parser = subparsers.add_parser(
        "smi",
        help="Small-molecule inhibitor Go/No-Go module",
        description="Initialize M0–M5 plans for a small-molecule inhibitor dossier.",
    )
    nested = parser.add_subparsers(dest="smi_command", required=True)
    add_commands(nested)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="syflow smi",
        description="SyFlow small-molecule inhibitor Go/No-Go module",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s validate --target pnpla3
  %(prog)s gate --target pnpla3 --gate M0
        """,
    )
    subparsers = parser.add_subparsers(dest="smi_command", required=True)
    add_commands(subparsers)
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        args.func(args)
    except ValueError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
