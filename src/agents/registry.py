"""Agent registry for SyFlow NDC Go/No-Go platform.

Each agent is defined with its tools, model, effort level, and system prompt.
Specialists are sandboxed: each writes only to work/<its-name>/ and gets
only the MCP tools relevant to its domain.

Modeled after Virtual Biotech src/agents/registry.py pattern.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

AGENTS_DIR = Path(__file__).parent


def _load_prompt(agent_name: str) -> str:
    """Load system prompt from the agent's directory."""
    prompt_path = AGENTS_DIR / agent_name / "system_prompt.md"
    if prompt_path.exists():
        return prompt_path.read_text()
    return f"You are the {agent_name} specialist agent."


# Tool allowlists per agent domain
_TARGET_TOOLS = [
    "Read", "Write", "Glob", "Grep", "Bash",
    "mcp__open_targets__*",
    "mcp__pubmed__*",
    "mcp__clinical_trials__*",
    "mcp__chembl__*",
    "mcp__biorxiv__*",
    "mcp__provenance__register_artifact",
]

_NANOBODY_TOOLS = [
    "Read", "Write", "Glob", "Grep", "Bash",
    "mcp__pubmed__*",
    "mcp__chembl__*",
    "mcp__biorxiv__*",
    "mcp__scholar__*",
    "mcp__provenance__register_artifact",
]

_DELIVERY_TOOLS = [
    "Read", "Write", "Glob", "Grep", "Bash",
    "mcp__pubmed__*",
    "mcp__biorxiv__*",
    "mcp__provenance__register_artifact",
]

_CONJUGATION_TOOLS = [
    "Read", "Write", "Glob", "Grep", "Bash",
    "mcp__chembl__*",
    "mcp__pubmed__*",
    "mcp__provenance__register_artifact",
]

_TRANSLATION_TOOLS = [
    "Read", "Write", "Glob", "Grep", "Bash",
    "mcp__pubmed__*",
    "mcp__clinical_trials__*",
    "mcp__chembl__*",
    "mcp__open_targets__*",
    "mcp__provenance__register_artifact",
]

_REVIEWER_TOOLS = [
    "Read", "Glob", "Grep",  # Read-only access
]

_CSO_TOOLS = [
    "Agent", "Task", "Read", "Write", "Glob",
    "mcp__provenance__write_plan",
    "mcp__provenance__record_claims",
    "mcp__provenance__list_artifacts",
    "mcp__provenance__register_artifact",
]


AGENT_REGISTRY: dict[str, dict[str, Any]] = {
    "cso": {
        "description": "Chief Scientific Officer — orchestrates specialists, synthesizes Go/No-Go decisions",
        "prompt": _load_prompt("cso"),
        "tools": _CSO_TOOLS,
        "model": os.getenv("SYFLOW_CSO_MODEL", "claude-sonnet-4-6"),
        "effort": "high",
        "memory": "project",
        "is_orchestrator": True,
    },
    "target_patient": {
        "description": "Target and patient-selection specialist — G0 gate evidence",
        "prompt": _load_prompt("target_patient"),
        "tools": _TARGET_TOOLS,
        "model": os.getenv("SYFLOW_SPECIALIST_MODEL", "claude-sonnet-4-6"),
        "effort": "high",
        "memory": "project",
        "workspace": "work/target_patient",
    },
    "nanobody_epitope": {
        "description": "Nanobody and epitope specialist — G1 gate evidence",
        "prompt": _load_prompt("nanobody_epitope"),
        "tools": _NANOBODY_TOOLS,
        "model": os.getenv("SYFLOW_SPECIALIST_MODEL", "claude-sonnet-4-6"),
        "effort": "high",
        "memory": "project",
        "workspace": "work/nanobody_epitope",
    },
    "delivery": {
        "description": "Delivery specialist — G2 gate evidence (internalization and trafficking)",
        "prompt": _load_prompt("delivery"),
        "tools": _DELIVERY_TOOLS,
        "model": os.getenv("SYFLOW_SPECIALIST_MODEL", "claude-sonnet-4-6"),
        "effort": "high",
        "memory": "project",
        "workspace": "work/delivery",
    },
    "conjugation_payload": {
        "description": "Conjugation and payload specialist — G3/G4 gate evidence",
        "prompt": _load_prompt("conjugation_payload"),
        "tools": _CONJUGATION_TOOLS,
        "model": os.getenv("SYFLOW_SPECIALIST_MODEL", "claude-sonnet-4-6"),
        "effort": "high",
        "memory": "project",
        "workspace": "work/conjugation_payload",
    },
    "translation_safety": {
        "description": "Translation and safety specialist — G5 gate evidence",
        "prompt": _load_prompt("translation_safety"),
        "tools": _TRANSLATION_TOOLS,
        "model": os.getenv("SYFLOW_SPECIALIST_MODEL", "claude-sonnet-4-6"),
        "effort": "high",
        "memory": "project",
        "workspace": "work/translation_safety",
    },
    "scientific_reviewer": {
        "description": "Scientific reviewer and gatekeeper — evaluates all specialist outputs",
        "prompt": _load_prompt("scientific_reviewer"),
        "tools": _REVIEWER_TOOLS,
        "model": os.getenv("SYFLOW_REVIEWER_MODEL", "claude-haiku-4-5-20251001"),
        "effort": "high",
        "memory": "project",
        "workspace": "work/scientific_reviewer",
    },
}


def get_agent_config(agent_name: str) -> dict[str, Any]:
    """Get configuration for a named agent."""
    if agent_name not in AGENT_REGISTRY:
        raise ValueError(f"Unknown agent: {agent_name}. Available: {list(AGENT_REGISTRY.keys())}")
    return AGENT_REGISTRY[agent_name]


def build_specialist_agents(run_dir: Path) -> list[dict[str, Any]]:
    """Build agent definitions for all specialists, scoped to a run directory.

    Returns a list of agent config dicts with workspace paths resolved
    relative to the run directory.
    """
    agents = []
    for name, config in AGENT_REGISTRY.items():
        if config.get("is_orchestrator"):
            continue
        agent_def = {
            "name": name,
            "description": config["description"],
            "prompt": _build_agent_prompt(name, config, run_dir),
            "tools": config["tools"],
            "model": config["model"],
            "effort": config["effort"],
        }
        # Create workspace directory
        if "workspace" in config:
            workspace = run_dir / config["workspace"] / "results"
            workspace.mkdir(parents=True, exist_ok=True)
            agent_def["workspace"] = str(workspace)
        agents.append(agent_def)
    return agents


def _build_agent_prompt(name: str, config: dict, run_dir: Path) -> str:
    """Build the full prompt for an agent, including workspace instructions."""
    base_prompt = config["prompt"]
    workspace = config.get("workspace", f"work/{name}")
    workspace_path = run_dir / workspace / "results"

    instructions = f"""
## Workspace

You are operating within SyFlow run directory: {run_dir}
Your workspace: {workspace_path}

Save all output artifacts (tables, figures, reports) to your workspace directory.
Register each artifact with `mcp__provenance__register_artifact`.

## Evidence citation rules

Every finding must include:
- Evidence type label: prediction | literature_evidence | retrospective_analysis | syflow_wetlab | independent_replication
- For wet-lab evidence: ELN/LIMS batch ID, assay version, operator, date
- For citations: PMID or DOI
- Confidence level: strong | moderate | weak

Format claims as: [[claim:XX]] followed by the claim text.
"""
    return base_prompt + "\n\n" + instructions
