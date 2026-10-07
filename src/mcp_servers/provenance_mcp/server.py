#!/usr/bin/env python3
"""Provenance MCP server for SyFlow NDC platform.

Provides tools for:
- write_plan: Declare an analysis plan DAG
- register_artifact: Register a file in the run manifest
- record_claims: Record and validate claims against manifest/trace
- list_artifacts: List all registered artifacts
- get_gate_status: Get current gate evidence status

This is a simplified MCP server skeleton. In production, this would implement
the full MCP protocol over stdio.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.plan_runner import PlanRunner, validate_plan
from src.utils.run_manifest import RunManifest
from src.utils.trace_logger import TraceLogger
from src.utils.claims import validate_claims
from src.schemas.evidence import Claim, EvidenceItem, EvidenceType, EvidenceKind
from src.schemas.gate import GATE_DEFINITIONS, GateID


RUNS_DIR = Path(os.getenv("SYFLOW_RUNS_DIR", PROJECT_ROOT / "runs"))


class ProvenanceServer:
    """Provenance MCP server implementation."""

    def __init__(self, run_dir: str | Path):
        self.run_dir = Path(run_dir)
        self.manifest = RunManifest.load(run_dir)
        self.trace = TraceLogger.load(run_dir)
        self.plan = PlanRunner.load(run_dir)

    def write_plan(self, goal: str, steps: list[dict]) -> dict:
        """Declare an analysis plan DAG. Validated with topological sort."""
        result = self.plan.write_plan(goal, steps)
        if result.get("valid"):
            self.trace.log("plan_written", data={"goal": goal, "steps": len(steps)})
        return result

    def register_artifact(
        self,
        path: str,
        kind: str = "other",
        produced_by: str | None = None,
        description: str = "",
    ) -> dict:
        """Register a file artifact in the run manifest."""
        entry = self.manifest.register(
            path=path,
            kind=kind,
            produced_by=produced_by,
            description=description,
        )
        self.trace.log(
            "artifact_registered",
            agent=produced_by,
            path=path,
            kind=kind,
        )
        return entry.to_dict()

    def record_claims(self, claims_data: list[dict]) -> dict:
        """Record and validate claims against manifest and trace."""
        claims = []
        for cd in claims_data:
            evidence_items = []
            for ed in cd.get("evidence", []):
                evidence_items.append(EvidenceItem(
                    kind=EvidenceKind(ed.get("kind", "artifact")),
                    evidence_type=EvidenceType(ed.get("evidence_type", "prediction")),
                    path=ed.get("path"),
                    note=ed.get("note"),
                    tool_use_id=ed.get("tool_use_id"),
                    tool_name=ed.get("tool_name"),
                    agent=ed.get("agent"),
                    pmid=ed.get("pmid"),
                    doi=ed.get("doi"),
                    url=ed.get("url"),
                    eln_id=ed.get("eln_id"),
                    lims_batch_id=ed.get("lims_batch_id"),
                    assay_id=ed.get("assay_id"),
                    assay_date=ed.get("assay_date"),
                    raw_data_path=ed.get("raw_data_path"),
                    operator=ed.get("operator"),
                ))
            claims.append(Claim(
                id=cd["id"],
                text=cd["text"],
                agent=cd["agent"],
                confidence=cd.get("confidence", "moderate"),
                gate=cd.get("gate"),
                evidence=evidence_items,
            ))

        validation = validate_claims(claims, self.manifest, self.trace)

        # Log each claim
        for claim in claims:
            self.trace.log_claim_recorded(claim.id, claim.agent)

        # Save claims to run directory
        claims_path = self.run_dir / "claims.json"
        existing = []
        if claims_path.exists():
            with open(claims_path) as f:
                existing = json.load(f)
        existing.extend([c.model_dump(mode="json") for c in claims])
        with open(claims_path, "w") as f:
            json.dump(existing, f, indent=2, default=str)

        return validation

    def list_artifacts(self) -> list[dict]:
        """List all registered artifacts."""
        return [entry.to_dict() for entry in self.manifest.artifacts.values()]

    def get_gate_status(self, gate_id: str) -> dict:
        """Get evidence status for a specific gate."""
        gate = GateID(gate_id)
        gate_def = GATE_DEFINITIONS.get(gate)
        if not gate_def:
            return {"error": f"Unknown gate: {gate_id}"}

        # Load claims for this gate
        claims_path = self.run_dir / "claims.json"
        gate_claims = []
        if claims_path.exists():
            with open(claims_path) as f:
                all_claims = json.load(f)
            gate_claims = [c for c in all_claims if c.get("gate") == gate_id]

        # Check evidence coverage
        required = gate_def["required_evidence"]
        covered = set()
        for claim in gate_claims:
            for ev in claim.get("evidence", []):
                if ev.get("verification_status") == "verified":
                    covered.add(claim.get("text", "")[:50])

        return {
            "gate_id": gate_id,
            "gate_name": gate_def["name"],
            "required_evidence": required,
            "claims_count": len(gate_claims),
            "hold_triggers": gate_def["hold_triggers"],
            "nogo_triggers": gate_def["nogo_triggers"],
        }


def main():
    """MCP server entry point (stdio protocol skeleton)."""
    print(json.dumps({
        "name": "syflow-provenance",
        "version": "1.0.0",
        "tools": [
            {"name": "write_plan", "description": "Declare an analysis plan DAG"},
            {"name": "register_artifact", "description": "Register a file in the manifest"},
            {"name": "record_claims", "description": "Record and validate claims"},
            {"name": "list_artifacts", "description": "List all registered artifacts"},
            {"name": "get_gate_status", "description": "Get evidence status for a gate"},
        ],
    }))


if __name__ == "__main__":
    main()
