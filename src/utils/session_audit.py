"""Session audit lifecycle for SyFlow runs.

Installs hooks at agent start/stop and tool use to capture execution
events. Generates README.md and audit report at run completion.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .trace_logger import TraceLogger
from .run_manifest import RunManifest
from .provenance import Provenance
from .plan_runner import PlanRunner


class SessionAudit:
    """Manages the audit lifecycle for a single SyFlow run."""

    def __init__(self, run_dir: str | Path, run_id: str):
        self.run_dir = Path(run_dir)
        self.run_id = run_id
        self.trace = TraceLogger(run_dir)
        self.manifest = RunManifest.create(run_dir)
        self.plan = PlanRunner(run_dir)
        self.start_time = datetime.now(timezone.utc).isoformat()
        self.status = "running"
        self.turns: list[dict] = []
        self.current_turn = 0

        # Write initial run metadata
        self._write_metadata()

    def _write_metadata(self) -> None:
        meta = {
            "run_id": self.run_id,
            "start_time": self.start_time,
            "status": self.status,
            "platform": "syflow_ndc",
            "version": "1.0",
        }
        with open(self.run_dir / "run_metadata.json", "w") as f:
            json.dump(meta, f, indent=2)

    def on_agent_start(self, agent: str, task: str) -> None:
        """Hook: specialist agent dispatched."""
        self.trace.log_agent_start(agent, task)
        agent_dir = self.run_dir / "work" / agent / "results"
        agent_dir.mkdir(parents=True, exist_ok=True)

    def on_agent_stop(self, agent: str, status: str = "completed") -> None:
        """Hook: specialist agent completed."""
        self.trace.log_agent_stop(agent, status)

    def on_tool_start(self, agent: str, tool_name: str, tool_use_id: str) -> None:
        """Hook: tool invocation begins."""
        self.trace.log_tool_start(agent, tool_name, tool_use_id)

    def on_tool_end(self, agent: str, tool_name: str, tool_use_id: str,
                    success: bool = True) -> None:
        """Hook: tool invocation ends."""
        self.trace.log_tool_end(agent, tool_name, tool_use_id, success)

    def on_file_write(self, agent: str, path: str, kind: str = "other",
                      description: str = "") -> None:
        """Hook: agent writes a file."""
        rel_path = str(Path(path).relative_to(self.run_dir)) if Path(path).is_absolute() else path
        self.manifest.register(
            path=rel_path,
            kind=kind,
            produced_by=agent,
            description=description,
        )
        self.trace.log_file_write(agent, rel_path, self.manifest.get(rel_path).sha256)

    def on_gate_decision(self, gate_id: str, verdict: str, agent: str = "scientific_reviewer") -> None:
        """Hook: gate decision recorded."""
        self.trace.log_gate_decision(gate_id, verdict, agent)

    def start_turn(self) -> int:
        self.current_turn += 1
        self.turns.append({
            "turn": self.current_turn,
            "started_at": datetime.now(timezone.utc).isoformat(),
        })
        return self.current_turn

    def finish_turn(self) -> dict[str, Any]:
        """Complete a conversation turn: reconcile, verify, generate reports."""
        if self.turns:
            self.turns[-1]["completed_at"] = datetime.now(timezone.utc).isoformat()

        # Reconcile plan
        plan_report = self.plan.reconcile()

        # Reconstruct provenance
        prov = Provenance(self.run_dir)
        prov.reconstruct()
        prov_report = prov.generate_report()

        # Verify manifest
        manifest_issues = self.manifest.verify_all()

        turn_report = {
            "turn": self.current_turn,
            "plan_reconciliation": plan_report,
            "manifest_issues": manifest_issues,
            "agent_summary": prov.get_agent_summary(),
        }

        # Write provenance report
        (self.run_dir / "provenance_report.md").write_text(prov_report)

        return turn_report

    def finish_run(self, status: str = "completed") -> dict[str, Any]:
        """Finalize the run and generate all audit artifacts."""
        self.status = status
        self._write_metadata()

        # Final turn report
        turn_report = self.finish_turn()

        # Generate README
        readme = self._generate_readme(turn_report)
        (self.run_dir / "README.md").write_text(readme)

        # Save final audit
        audit = {
            "run_id": self.run_id,
            "status": status,
            "start_time": self.start_time,
            "end_time": datetime.now(timezone.utc).isoformat(),
            "turns": self.turns,
            "final_report": turn_report,
        }
        with open(self.run_dir / "audit.json", "w") as f:
            json.dump(audit, f, indent=2)

        return audit

    def _generate_readme(self, report: dict) -> str:
        """Generate a human-readable README for the run directory."""
        lines = [
            f"# SyFlow Run: {self.run_id}",
            "",
            f"- **Status:** {self.status}",
            f"- **Started:** {self.start_time}",
            f"- **Turns:** {self.current_turn}",
            "",
            "## Plan",
            f"- Goal: {self.plan.goal}",
            f"- Steps: {len(self.plan.steps)}",
            "",
        ]

        plan = report.get("plan_reconciliation", {})
        lines.append(f"- Completed: {plan.get('completed', 0)}")
        lines.append(f"- Failed: {plan.get('failed', 0)}")
        lines.append(f"- Deviations: {len(plan.get('deviations', []))}")
        lines.append("")

        # Agent summary
        lines.append("## Agents")
        for agent in report.get("agent_summary", []):
            lines.append(f"- **{agent['agent']}**: {agent['status']}, "
                        f"{agent['tool_call_count']} tool calls, "
                        f"{len(agent['claims_produced'])} claims")
        lines.append("")

        # Manifest issues
        issues = report.get("manifest_issues", [])
        if issues:
            lines.append("## Manifest Issues")
            for issue in issues:
                lines.append(f"- {issue['path']}: {issue['issue']}")
            lines.append("")

        lines.append("---")
        lines.append("*Generated by SyFlow NDC Go/No-Go Platform*")

        return "\n".join(lines)
