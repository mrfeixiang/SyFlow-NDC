"""Execution event tracing for SyFlow runs.

Every tool call, agent dispatch, file write, and gate decision is recorded
as a structured event in trace.jsonl. Provenance is reconstructed from
observed execution, not self-reported by agents.
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


class TraceEvent:
    """A single traced execution event."""

    def __init__(
        self,
        event_type: str,
        agent: Optional[str] = None,
        tool_name: Optional[str] = None,
        tool_use_id: Optional[str] = None,
        data: Optional[dict[str, Any]] = None,
    ):
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.monotonic_ns = time.monotonic_ns()
        self.event_type = event_type
        self.agent = agent
        self.tool_name = tool_name
        self.tool_use_id = tool_use_id
        self.data = data or {}

    def to_dict(self) -> dict[str, Any]:
        d = {
            "timestamp": self.timestamp,
            "monotonic_ns": self.monotonic_ns,
            "event_type": self.event_type,
        }
        if self.agent:
            d["agent"] = self.agent
        if self.tool_name:
            d["tool_name"] = self.tool_name
        if self.tool_use_id:
            d["tool_use_id"] = self.tool_use_id
        if self.data:
            d["data"] = self.data
        return d


class TraceLogger:
    """Append-only trace logger writing to trace.jsonl in the run directory."""

    def __init__(self, run_dir: str | Path):
        self.run_dir = Path(run_dir)
        self.trace_path = self.run_dir / "trace.jsonl"
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self._events: list[TraceEvent] = []

    def log(
        self,
        event_type: str,
        agent: Optional[str] = None,
        tool_name: Optional[str] = None,
        tool_use_id: Optional[str] = None,
        **data: Any,
    ) -> TraceEvent:
        event = TraceEvent(
            event_type=event_type,
            agent=agent,
            tool_name=tool_name,
            tool_use_id=tool_use_id,
            data=data if data else None,
        )
        self._events.append(event)
        with open(self.trace_path, "a") as f:
            f.write(json.dumps(event.to_dict()) + "\n")
        return event

    def log_agent_start(self, agent: str, task: str) -> TraceEvent:
        return self.log("agent_start", agent=agent, task=task)

    def log_agent_stop(self, agent: str, status: str = "completed") -> TraceEvent:
        return self.log("agent_stop", agent=agent, status=status)

    def log_tool_start(self, agent: str, tool_name: str, tool_use_id: str) -> TraceEvent:
        return self.log("tool_start", agent=agent, tool_name=tool_name, tool_use_id=tool_use_id)

    def log_tool_end(self, agent: str, tool_name: str, tool_use_id: str, success: bool = True) -> TraceEvent:
        return self.log("tool_end", agent=agent, tool_name=tool_name, tool_use_id=tool_use_id, success=success)

    def log_file_write(self, agent: str, path: str, sha256: Optional[str] = None) -> TraceEvent:
        return self.log("file_write", agent=agent, path=path, sha256=sha256)

    def log_gate_decision(self, gate_id: str, verdict: str, agent: str = "scientific_reviewer") -> TraceEvent:
        return self.log("gate_decision", agent=agent, gate_id=gate_id, verdict=verdict)

    def log_claim_recorded(self, claim_id: str, agent: str) -> TraceEvent:
        return self.log("claim_recorded", agent=agent, claim_id=claim_id)

    def get_events(self, event_type: Optional[str] = None, agent: Optional[str] = None) -> list[dict]:
        """Filter events by type and/or agent."""
        results = []
        for e in self._events:
            if event_type and e.event_type != event_type:
                continue
            if agent and e.agent != agent:
                continue
            results.append(e.to_dict())
        return results

    def get_tool_calls_by_agent(self, agent: str) -> list[dict]:
        return self.get_events(event_type="tool_start", agent=agent)

    @classmethod
    def load(cls, run_dir: str | Path) -> "TraceLogger":
        """Load an existing trace from disk."""
        logger = cls(run_dir)
        if logger.trace_path.exists():
            with open(logger.trace_path) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        d = json.loads(line)
                        event = TraceEvent(
                            event_type=d["event_type"],
                            agent=d.get("agent"),
                            tool_name=d.get("tool_name"),
                            tool_use_id=d.get("tool_use_id"),
                            data=d.get("data"),
                        )
                        event.timestamp = d["timestamp"]
                        event.monotonic_ns = d.get("monotonic_ns", 0)
                        logger._events.append(event)
        return logger
