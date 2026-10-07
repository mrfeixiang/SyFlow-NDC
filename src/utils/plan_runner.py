"""DAG-based analysis plan validation and execution tracking.

Plans define the order of specialist agent dispatch with explicit
dependencies. Uses Kahn's topological sort for cycle detection.
Plan deviations are recorded but not treated as failures.
"""
from __future__ import annotations

import json
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


class PlanStep:
    """A single step in the analysis plan DAG."""

    def __init__(
        self,
        step_id: str,
        agent: str,
        task: str,
        depends_on: list[str] | None = None,
        expected_outputs: list[str] | None = None,
    ):
        self.id = step_id
        self.agent = agent
        self.task = task
        self.depends_on = depends_on or []
        self.expected_outputs = expected_outputs or []
        self.status: str = "pending"  # pending, running, completed, skipped, failed
        self.started_at: Optional[str] = None
        self.completed_at: Optional[str] = None
        self.actual_outputs: list[str] = []
        self.deviation_notes: list[str] = []

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "agent": self.agent,
            "task": self.task,
            "depends_on": self.depends_on,
            "expected_outputs": self.expected_outputs,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "actual_outputs": self.actual_outputs,
            "deviation_notes": self.deviation_notes,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PlanStep":
        step = cls(
            step_id=d["id"],
            agent=d["agent"],
            task=d["task"],
            depends_on=d.get("depends_on", []),
            expected_outputs=d.get("expected_outputs", []),
        )
        step.status = d.get("status", "pending")
        step.started_at = d.get("started_at")
        step.completed_at = d.get("completed_at")
        step.actual_outputs = d.get("actual_outputs", [])
        step.deviation_notes = d.get("deviation_notes", [])
        return step


def topological_sort(steps: list[PlanStep]) -> tuple[list[str], bool]:
    """Kahn's algorithm. Returns (sorted_ids, has_cycle)."""
    graph: dict[str, list[str]] = defaultdict(list)
    in_degree: dict[str, int] = {s.id: 0 for s in steps}
    step_map = {s.id: s for s in steps}

    for step in steps:
        for dep in step.depends_on:
            if dep in step_map:
                graph[dep].append(step.id)
                in_degree[step.id] += 1

    queue = deque([sid for sid, deg in in_degree.items() if deg == 0])
    sorted_ids: list[str] = []

    while queue:
        node = queue.popleft()
        sorted_ids.append(node)
        for neighbor in graph[node]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    has_cycle = len(sorted_ids) != len(steps)
    return sorted_ids, has_cycle


def compute_parallel_groups(steps: list[PlanStep]) -> list[list[str]]:
    """Group steps that can execute concurrently (same topological level)."""
    step_map = {s.id: s for s in steps}
    levels: dict[str, int] = {}

    def get_level(sid: str) -> int:
        if sid in levels:
            return levels[sid]
        step = step_map[sid]
        if not step.depends_on:
            levels[sid] = 0
        else:
            levels[sid] = 1 + max(
                get_level(dep) for dep in step.depends_on if dep in step_map
            )
        return levels[sid]

    for s in steps:
        get_level(s.id)

    groups: dict[int, list[str]] = defaultdict(list)
    for sid, level in sorted(levels.items(), key=lambda x: x[1]):
        groups[level].append(sid)

    return [groups[level] for level in sorted(groups.keys())]


def validate_plan(plan_data: dict) -> dict[str, Any]:
    """Validate a plan DAG. Returns validation result with sorted order and groups."""
    steps = [PlanStep.from_dict(s) for s in plan_data.get("steps", [])]

    if not steps:
        return {"valid": False, "error": "Plan has no steps"}

    # Check for unknown dependencies
    step_ids = {s.id for s in steps}
    for step in steps:
        unknown = [d for d in step.depends_on if d not in step_ids]
        if unknown:
            return {"valid": False, "error": f"Step {step.id} depends on unknown steps: {unknown}"}

    sorted_ids, has_cycle = topological_sort(steps)
    if has_cycle:
        return {"valid": False, "error": "Plan contains a dependency cycle"}

    parallel_groups = compute_parallel_groups(steps)

    return {
        "valid": True,
        "valid_order": sorted_ids,
        "parallel_groups": parallel_groups,
        "step_count": len(steps),
    }


class PlanRunner:
    """Track plan execution and reconcile against actual behavior."""

    def __init__(self, run_dir: str | Path):
        self.run_dir = Path(run_dir)
        self.plan_path = self.run_dir / "inputs" / "plan.json"
        self.steps: list[PlanStep] = []
        self.goal: str = ""
        self.created_at: str = ""
        self.deviations: list[dict] = []

    def write_plan(self, goal: str, steps: list[dict]) -> dict:
        """Write and validate a new plan."""
        plan_data = {
            "goal": goal,
            "created": datetime.now(timezone.utc).isoformat(),
            "steps": steps,
        }
        validation = validate_plan(plan_data)
        if not validation["valid"]:
            return validation

        plan_data["valid_order"] = validation["valid_order"]
        plan_data["parallel_groups"] = validation["parallel_groups"]

        (self.run_dir / "inputs").mkdir(parents=True, exist_ok=True)
        with open(self.plan_path, "w") as f:
            json.dump(plan_data, f, indent=2)

        self.goal = goal
        self.created_at = plan_data["created"]
        self.steps = [PlanStep.from_dict(s) for s in steps]

        return validation

    def mark_step(self, step_id: str, status: str, outputs: list[str] | None = None,
                  notes: str | None = None) -> None:
        for step in self.steps:
            if step.id == step_id:
                step.status = status
                now = datetime.now(timezone.utc).isoformat()
                if status == "running":
                    step.started_at = now
                elif status in ("completed", "failed", "skipped"):
                    step.completed_at = now
                if outputs:
                    step.actual_outputs = outputs
                if notes:
                    step.deviation_notes.append(notes)
                break

    def record_deviation(self, step_id: str, description: str) -> None:
        self.deviations.append({
            "step_id": step_id,
            "description": description,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def reconcile(self) -> dict[str, Any]:
        """Compare planned vs actual execution."""
        report = {
            "goal": self.goal,
            "total_steps": len(self.steps),
            "completed": sum(1 for s in self.steps if s.status == "completed"),
            "failed": sum(1 for s in self.steps if s.status == "failed"),
            "skipped": sum(1 for s in self.steps if s.status == "skipped"),
            "pending": sum(1 for s in self.steps if s.status == "pending"),
            "deviations": self.deviations,
            "steps": [s.to_dict() for s in self.steps],
        }

        # Check output alignment
        output_issues = []
        for step in self.steps:
            if step.status == "completed" and step.expected_outputs:
                missing = set(step.expected_outputs) - set(step.actual_outputs)
                extra = set(step.actual_outputs) - set(step.expected_outputs)
                if missing or extra:
                    output_issues.append({
                        "step_id": step.id,
                        "missing_outputs": list(missing),
                        "unexpected_outputs": list(extra),
                    })
        report["output_issues"] = output_issues

        return report

    @classmethod
    def load(cls, run_dir: str | Path) -> "PlanRunner":
        runner = cls(run_dir)
        if runner.plan_path.exists():
            with open(runner.plan_path) as f:
                data = json.load(f)
            runner.goal = data.get("goal", "")
            runner.created_at = data.get("created", "")
            runner.steps = [PlanStep.from_dict(s) for s in data.get("steps", [])]
        return runner
