"""Provenance reconstruction from execution traces.

Attribution comes from observed execution (hooks, trace events), not
self-reported by agents. An agent cannot misattribute its own work.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Optional

from .trace_logger import TraceLogger
from .run_manifest import RunManifest


class AgentActivity:
    """Reconstructed activity record for one agent in a run."""

    def __init__(self, agent: str):
        self.agent = agent
        self.start_time: Optional[str] = None
        self.end_time: Optional[str] = None
        self.status: str = "unknown"
        self.tool_calls: list[dict] = []
        self.files_written: list[str] = []
        self.claims_produced: list[str] = []
        self.artifacts_registered: list[str] = []

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent": self.agent,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "status": self.status,
            "tool_call_count": len(self.tool_calls),
            "files_written": self.files_written,
            "claims_produced": self.claims_produced,
            "artifacts_registered": self.artifacts_registered,
        }


class Provenance:
    """Reconstruct who did what from trace.jsonl and MANIFEST.json.

    This is intentionally derived from observed execution, not self-reported.
    """

    def __init__(self, run_dir: str | Path):
        self.run_dir = Path(run_dir)
        self.trace = TraceLogger.load(run_dir)
        self.manifest = RunManifest.load(run_dir)
        self.agents: dict[str, AgentActivity] = {}

    def reconstruct(self) -> dict[str, AgentActivity]:
        """Build activity records from trace events."""
        # Pass 1: agent lifecycle
        for event in self.trace._events:
            d = event.to_dict()
            agent = d.get("agent")
            if not agent:
                continue

            if agent not in self.agents:
                self.agents[agent] = AgentActivity(agent)

            activity = self.agents[agent]

            if d["event_type"] == "agent_start":
                activity.start_time = d["timestamp"]
                activity.status = "running"
            elif d["event_type"] == "agent_stop":
                activity.end_time = d["timestamp"]
                activity.status = d.get("data", {}).get("status", "completed")
            elif d["event_type"] in ("tool_start", "tool_end"):
                activity.tool_calls.append({
                    "tool_name": d.get("tool_name"),
                    "tool_use_id": d.get("tool_use_id"),
                    "event_type": d["event_type"],
                    "timestamp": d["timestamp"],
                })
            elif d["event_type"] == "file_write":
                path = d.get("data", {}).get("path", "")
                if path:
                    activity.files_written.append(path)
            elif d["event_type"] == "claim_recorded":
                claim_id = d.get("data", {}).get("claim_id", "")
                if claim_id:
                    activity.claims_produced.append(claim_id)

        # Pass 2: attribute manifest artifacts to agents
        for path, artifact in self.manifest.artifacts.items():
            if artifact.produced_by and artifact.produced_by in self.agents:
                self.agents[artifact.produced_by].artifacts_registered.append(path)

        return self.agents

    def get_agent_summary(self) -> list[dict]:
        """Return a summary of all agent activities."""
        if not self.agents:
            self.reconstruct()
        return [a.to_dict() for a in self.agents.values()]

    def get_unattributed_artifacts(self) -> list[str]:
        """Find artifacts with no agent attribution."""
        return [
            path for path, a in self.manifest.artifacts.items()
            if not a.produced_by
        ]

    def get_claim_provenance(self, claim_id: str) -> Optional[dict]:
        """Trace a claim back to its producing agent and evidence chain."""
        if not self.agents:
            self.reconstruct()
        for agent_name, activity in self.agents.items():
            if claim_id in activity.claims_produced:
                return {
                    "claim_id": claim_id,
                    "produced_by": agent_name,
                    "agent_start": activity.start_time,
                    "agent_end": activity.end_time,
                    "supporting_artifacts": [
                        path for path, a in self.manifest.artifacts.items()
                        if claim_id in a.cited_by
                    ],
                }
        return None

    def generate_report(self) -> str:
        """Generate a human-readable provenance report."""
        if not self.agents:
            self.reconstruct()

        lines = ["# Provenance Report", f"Run: {self.run_dir.name}", ""]

        for name, activity in sorted(self.agents.items()):
            lines.append(f"## {name}")
            lines.append(f"- Status: {activity.status}")
            lines.append(f"- Tool calls: {len(activity.tool_calls)}")
            lines.append(f"- Files written: {len(activity.files_written)}")
            lines.append(f"- Claims: {', '.join(activity.claims_produced) or 'none'}")
            lines.append(f"- Artifacts: {len(activity.artifacts_registered)}")
            lines.append("")

        unattributed = self.get_unattributed_artifacts()
        if unattributed:
            lines.append("## Unattributed Artifacts")
            for path in unattributed:
                lines.append(f"- {path}")
            lines.append("")

        return "\n".join(lines)
