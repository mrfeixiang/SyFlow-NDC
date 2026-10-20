#!/usr/bin/env python3
"""SyFlow NDC Go/No-Go Platform — Main Runner

Usage:
    syflow validate --target egfrviii --query "Evaluate EGFRvIII as NDC target"
    python -m src validate --target egfrviii --query "Evaluate EGFRvIII as NDC target"
    python -m src gate --target egfrviii --gate G1 --dossier targets/egfrviii/dossier.yaml
    python -m src verify --run-id 20260928_egfrviii_001
    python -m src replay --run-id 20260928_egfrviii_001

Adapted from Virtual Biotech run_vbt.py pattern.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import yaml

# Repository root (parent of the src package). Keeps dossier and run paths
# stable whether the CLI is launched as `python -m src` or `python src/cli.py`.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agents.registry import AGENT_REGISTRY, build_specialist_agents
from src.schemas.gate import GATE_DEFINITIONS, GateID
from src.utils.plan_runner import PlanRunner, validate_plan
from src.utils.provenance import Provenance
from src.utils.run_manifest import RunManifest
from src.utils.session_audit import SessionAudit

RUNS_DIR = Path(os.getenv("SYFLOW_RUNS_DIR", PROJECT_ROOT / "runs"))


def generate_run_id(target: str) -> str:
    """Generate a unique run ID: YYYYMMDD_target_NNN."""
    date_str = datetime.now().strftime("%Y%m%d")
    prefix = f"{date_str}_{target}_"

    existing = sorted(RUNS_DIR.glob(f"{prefix}*")) if RUNS_DIR.exists() else []
    next_num = len(existing) + 1
    return f"{prefix}{next_num:03d}"


def create_run_directory(run_id: str) -> Path:
    """Create the run directory skeleton."""
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "work").mkdir(exist_ok=True)
    (run_dir / "inputs").mkdir(exist_ok=True)
    return run_dir


def load_target_dossier(target: str, dossier_path: str | None = None) -> dict:
    """Load target dossier configuration."""
    if dossier_path:
        path = Path(dossier_path)
    else:
        path = PROJECT_ROOT / "targets" / target / "dossier.yaml"

    if not path.exists():
        print(f"Warning: Dossier not found at {path}, using defaults")
        return {"target": target}

    with open(path) as f:
        return yaml.safe_load(f)


def build_validation_plan(target: str, dossier: dict) -> dict:
    """Build an analysis plan DAG for target validation."""
    target_config = dossier.get("target_profile", {})
    is_surface = target_config.get("is_surface_protein", True)
    has_vhh = "vhh" in dossier
    has_conjugate = "conjugate" in dossier

    steps = []

    # G0: Target assessment (always first)
    steps.append({
        "id": "s1_target",
        "agent": "target_patient",
        "task": f"Assess {target} as NDC target: membrane accessibility, tumor expression, normal-tissue window",
        "depends_on": [],
        "expected_outputs": ["target_assessment.md", "expression_data.csv"],
    })

    # G1: Nanobody assessment (parallel with target if VHH exists)
    if has_vhh:
        steps.append({
            "id": "s2_nanobody",
            "agent": "nanobody_epitope",
            "task": f"Assess VHH binding and selectivity for {target}",
            "depends_on": [],
            "expected_outputs": ["vhh_assessment.md", "binding_data.csv"],
        })
    else:
        steps.append({
            "id": "s2_nanobody",
            "agent": "nanobody_epitope",
            "task": f"Review published nanobodies against {target} and assess binding landscape",
            "depends_on": ["s1_target"],
            "expected_outputs": ["nanobody_landscape.md"],
        })

    # G2: Delivery assessment (depends on G1)
    if is_surface:
        steps.append({
            "id": "s3_delivery",
            "agent": "delivery",
            "task": f"Assess internalization and trafficking for {target}-binding VHH",
            "depends_on": ["s2_nanobody"],
            "expected_outputs": ["delivery_assessment.md"],
        })

    # G3/G4: Conjugation and killing (depends on G2)
    if has_conjugate:
        steps.append({
            "id": "s4_conjugation",
            "agent": "conjugation_payload",
            "task": "Assess conjugate product quality and antigen-dependent killing",
            "depends_on": ["s3_delivery"] if is_surface else ["s2_nanobody"],
            "expected_outputs": ["conjugate_assessment.md", "cytotoxicity_data.csv"],
        })

    # G5: Translation (depends on G3/G4)
    steps.append({
        "id": "s5_translation",
        "agent": "translation_safety",
        "task": f"Assess PK/PD, exposure window, and safety for {target} NDC",
        "depends_on": [s["id"] for s in steps if s["id"] != "s5_translation"],
        "expected_outputs": ["translation_assessment.md"],
    })

    # Review: always last
    steps.append({
        "id": "s6_review",
        "agent": "scientific_reviewer",
        "task": "Review all specialist outputs, identify gaps and conflicts",
        "depends_on": [s["id"] for s in steps],
        "expected_outputs": ["review_report.md"],
    })

    plan = {
        "goal": f"Validate {target} as NDC target and assess Go/No-Go status",
        "steps": steps,
    }

    # Validate the DAG
    validation = validate_plan(plan)
    if not validation["valid"]:
        print(f"Error: Invalid plan — {validation['error']}")
        sys.exit(1)

    plan["valid_order"] = validation["valid_order"]
    plan["parallel_groups"] = validation["parallel_groups"]
    return plan


def cmd_validate(args: argparse.Namespace) -> None:
    """Run a full target validation."""
    target = args.target
    run_id = generate_run_id(target)
    run_dir = create_run_directory(run_id)

    print(f"SyFlow NDC Validation: {target}")
    print(f"Run ID: {run_id}")
    print(f"Run directory: {run_dir}")
    print()

    # Load dossier
    dossier = load_target_dossier(target, args.dossier)

    # Save dossier to inputs
    with open(run_dir / "inputs" / "dossier.yaml", "w") as f:
        yaml.dump(dossier, f, default_flow_style=False)

    # Build and save plan
    plan = build_validation_plan(target, dossier)
    with open(run_dir / "inputs" / "plan.json", "w") as f:
        json.dump(plan, f, indent=2)

    print(f"Analysis plan: {len(plan['steps'])} steps")
    print(f"Parallel groups: {plan['parallel_groups']}")
    print()

    # Initialize audit
    audit = SessionAudit(run_dir, run_id)

    # Build specialist agents
    agents = build_specialist_agents(run_dir)
    print(f"Agents ready: {[a['name'] for a in agents]}")
    print()

    # Execute plan
    print("=" * 60)
    print("PLAN EXECUTION")
    print("=" * 60)

    for group_idx, group in enumerate(plan["parallel_groups"]):
        print(f"\nPhase {group_idx + 1}: {group}")
        step_map = {s["id"]: s for s in plan["steps"]}

        for step_id in group:
            step = step_map[step_id]
            agent_name = step["agent"]
            task = step["task"]

            print(f"  → Dispatching {agent_name}: {task[:60]}...")
            audit.on_agent_start(agent_name, task)

            # In a full implementation, this would dispatch to the Claude Agent SDK.
            # For now, we create the workspace and record the dispatch.
            agent_workspace = run_dir / "work" / agent_name / "results"
            agent_workspace.mkdir(parents=True, exist_ok=True)

            # Placeholder: write task description for manual or future automated execution
            task_file = agent_workspace / "task.md"
            task_file.write_text(f"# Task for {agent_name}\n\n{task}\n\n"
                                f"Target: {target}\n"
                                f"Gate: {AGENT_REGISTRY.get(agent_name, {}).get('description', '')}\n"
                                f"Run: {run_id}\n")

            audit.on_file_write(agent_name, str(task_file), "report", f"Task description for {agent_name}")
            audit.on_agent_stop(agent_name, "dispatched")

    # Query string for interactive execution
    query = args.query or f"Evaluate {target} as a target for nanobody-drug conjugate development"

    # Save the query
    with open(run_dir / "inputs" / "query.txt", "w") as f:
        f.write(query)

    print()
    print("=" * 60)
    print("RUN INITIALIZED")
    print("=" * 60)
    print(f"\nRun directory: {run_dir}")
    print(f"Query: {query}")
    print("\nTo execute with Claude Agent SDK:")
    print("  1. Set ANTHROPIC_API_KEY in .env")
    print(f"  2. Run: claude --project {run_dir} \"{query}\"")
    print("\nTo verify after completion:")
    print(f"  python -m src verify --run-id {run_id}")

    # Finalize
    audit.finish_run("initialized")
    print(f"\nAudit saved: {run_dir / 'audit.json'}")


def cmd_gate(args: argparse.Namespace) -> None:
    """Assess a specific gate for a target."""
    target = args.target
    gate_id = GateID(args.gate)
    gate_def = GATE_DEFINITIONS.get(gate_id)

    if not gate_def:
        print(f"Error: Unknown gate {args.gate}")
        sys.exit(1)

    print(f"SyFlow Gate Assessment: {gate_id.value} — {gate_def['name']}")
    print(f"Target: {target}")
    print(f"Required evidence: {gate_def['required_evidence']}")
    print(f"Hold triggers: {gate_def['hold_triggers']}")
    print(f"No-Go triggers: {gate_def['nogo_triggers']}")
    print(f"Primary agent: {gate_def['agent']}")
    print()

    # Load dossier
    dossier = load_target_dossier(target, args.dossier)

    # Create a gate-focused run
    run_id = generate_run_id(f"{target}_{args.gate}")
    run_dir = create_run_directory(run_id)
    audit = SessionAudit(run_dir, run_id)

    # Build gate-specific plan
    plan = {
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
                "task": f"Review evidence for gate {gate_id.value} and recommend verdict",
                "depends_on": ["s1_specialist"],
            },
        ],
    }

    with open(run_dir / "inputs" / "plan.json", "w") as f:
        json.dump(plan, f, indent=2)
    with open(run_dir / "inputs" / "dossier.yaml", "w") as f:
        yaml.dump(dossier, f, default_flow_style=False)

    audit.finish_run("initialized")
    print(f"Gate assessment run initialized: {run_id}")
    print(f"Run directory: {run_dir}")


def cmd_verify(args: argparse.Namespace) -> None:
    """Verify a completed run."""
    run_dir = RUNS_DIR / args.run_id
    if not run_dir.exists():
        print(f"Error: Run directory not found: {run_dir}")
        sys.exit(1)

    print(f"Verifying run: {args.run_id}")
    print()

    # Verify manifest
    manifest = RunManifest.load(run_dir)
    issues = manifest.verify_all()

    if issues:
        print(f"MANIFEST ISSUES ({len(issues)}):")
        for issue in issues:
            print(f"  - {issue['path']}: {issue['issue']}")
    else:
        print(f"Manifest: {len(manifest.artifacts)} artifacts, all verified ✓")

    # Reconstruct provenance
    prov = Provenance(run_dir)
    prov.reconstruct()
    print(f"\nAgents: {len(prov.agents)}")
    for name, activity in prov.agents.items():
        print(f"  - {name}: {activity.status}, {len(activity.tool_calls)} tool calls, "
              f"{len(activity.claims_produced)} claims")

    unattributed = prov.get_unattributed_artifacts()
    if unattributed:
        print(f"\nUnattributed artifacts: {len(unattributed)}")
        for path in unattributed:
            print(f"  - {path}")

    # Check plan reconciliation
    plan = PlanRunner.load(run_dir)
    if plan.steps:
        reconciliation = plan.reconcile()
        print(f"\nPlan: {reconciliation['completed']}/{reconciliation['total_steps']} completed, "
              f"{len(reconciliation['deviations'])} deviations")

    print("\nVerification complete.")


def cmd_replay(args: argparse.Namespace) -> None:
    """Replay a run for stochastic comparison."""
    run_dir = RUNS_DIR / args.run_id
    if not run_dir.exists():
        print(f"Error: Run directory not found: {run_dir}")
        sys.exit(1)

    print(f"Replay not yet implemented for: {args.run_id}")
    print("This would re-execute the same queries and diff the results.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="SyFlow NDC Go/No-Go Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s validate --target egfrviii --query "Evaluate EGFRvIII as NDC target for GBM"
  %(prog)s gate --target egfrviii --gate G1
  %(prog)s verify --run-id 20260928_egfrviii_001
        """,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # validate
    p_val = subparsers.add_parser("validate", help="Run full target validation")
    p_val.add_argument("--target", required=True, choices=["pnpla3", "rhoa", "tak1", "egfrviii"],
                       help="Target to validate")
    p_val.add_argument("--query", help="Analysis query (default: auto-generated)")
    p_val.add_argument("--dossier", help="Path to dossier YAML (default: targets/<target>/dossier.yaml)")
    p_val.set_defaults(func=cmd_validate)

    # gate
    p_gate = subparsers.add_parser("gate", help="Assess a specific gate")
    p_gate.add_argument("--target", required=True, choices=["pnpla3", "rhoa", "tak1", "egfrviii"])
    p_gate.add_argument("--gate", required=True, choices=["G0", "G1", "G2", "G3", "G4", "G5"])
    p_gate.add_argument("--dossier", help="Path to dossier YAML")
    p_gate.set_defaults(func=cmd_gate)

    # verify
    p_verify = subparsers.add_parser("verify", help="Verify a completed run")
    p_verify.add_argument("--run-id", required=True, help="Run ID to verify")
    p_verify.set_defaults(func=cmd_verify)

    # replay
    p_replay = subparsers.add_parser("replay", help="Replay a run for comparison")
    p_replay.add_argument("--run-id", required=True, help="Run ID to replay")
    p_replay.set_defaults(func=cmd_replay)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
