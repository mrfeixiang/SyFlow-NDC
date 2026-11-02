"""Agent registry for the small-molecule inhibitor module.

Seven agents staff six gates. Pharmacology covers M2 and M3, matching the
NDC pattern where one specialist covers two adjacent gates. Specialists
write only under work/<name>/.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

AGENTS_DIR = Path(__file__).parent


def _load_prompt(agent_name: str) -> str:
    prompt_path = AGENTS_DIR / "agents" / agent_name / "system_prompt.md"
    if prompt_path.exists():
        return prompt_path.read_text()
    return f"You are the {agent_name} specialist agent."


_TARGET_TOOLS = [
    "Read", "Write", "Glob", "Grep", "Bash",
    "mcp__open_targets__*",
    "mcp__pubmed__*",
    "mcp__clinical_trials__*",
    "mcp__chembl__*",
    "mcp__biorxiv__*",
    "mcp__provenance__register_artifact",
]

_CHEMISTRY_TOOLS = [
    "Read", "Write", "Glob", "Grep", "Bash",
    "mcp__chembl__*",
    "mcp__pubmed__*",
    "mcp__provenance__register_artifact",
]

_PHARMACOLOGY_TOOLS = [
    "Read", "Write", "Glob", "Grep", "Bash",
    "mcp__chembl__*",
    "mcp__pubmed__*",
    "mcp__biorxiv__*",
    "mcp__provenance__register_artifact",
]

_ADME_TOOLS = [
    "Read", "Write", "Glob", "Grep", "Bash",
    "mcp__chembl__*",
    "mcp__pubmed__*",
    "mcp__provenance__register_artifact",
]

_SAFETY_TOOLS = [
    "Read", "Write", "Glob", "Grep", "Bash",
    "mcp__pubmed__*",
    "mcp__clinical_trials__*",
    "mcp__chembl__*",
    "mcp__open_targets__*",
    "mcp__provenance__register_artifact",
]

_REVIEWER_TOOLS = [
    "Read", "Glob", "Grep",
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
        "description": "Chief Scientific Officer — orchestrates small-molecule Go/No-Go decisions",
        "prompt": _load_prompt("cso"),
        "tools": _CSO_TOOLS,
        "model": os.getenv("SYFLOW_CSO_MODEL", "claude-sonnet-4-6"),
        "effort": "high",
        "memory": "project",
        "is_orchestrator": True,
    },
    "target_biology": {
        "description": "Target biology specialist — M0 gate evidence",
        "prompt": _load_prompt("target_biology"),
        "tools": _TARGET_TOOLS,
        "model": os.getenv("SYFLOW_SPECIALIST_MODEL", "claude-sonnet-4-6"),
        "effort": "high",
        "memory": "project",
        "workspace": "work/target_biology",
    },
    "ligand_chemistry": {
        "description": "Ligand chemistry specialist — M1 gate evidence",
        "prompt": _load_prompt("ligand_chemistry"),
        "tools": _CHEMISTRY_TOOLS,
        "model": os.getenv("SYFLOW_SPECIALIST_MODEL", "claude-sonnet-4-6"),
        "effort": "high",
        "memory": "project",
        "workspace": "work/ligand_chemistry",
    },
    "pharmacology": {
        "description": "Pharmacology specialist — M2 biochemical potency and M3 cellular engagement",
        "prompt": _load_prompt("pharmacology"),
        "tools": _PHARMACOLOGY_TOOLS,
        "model": os.getenv("SYFLOW_SPECIALIST_MODEL", "claude-sonnet-4-6"),
        "effort": "high",
        "memory": "project",
        "workspace": "work/pharmacology",
    },
    "adme_exposure": {
        "description": "ADME and exposure specialist — M4 gate evidence",
        "prompt": _load_prompt("adme_exposure"),
        "tools": _ADME_TOOLS,
        "model": os.getenv("SYFLOW_SPECIALIST_MODEL", "claude-sonnet-4-6"),
        "effort": "high",
        "memory": "project",
        "workspace": "work/adme_exposure",
    },
    "safety_translation": {
        "description": "Safety and therapeutic-window specialist — M5 gate evidence",
        "prompt": _load_prompt("safety_translation"),
        "tools": _SAFETY_TOOLS,
        "model": os.getenv("SYFLOW_SPECIALIST_MODEL", "claude-sonnet-4-6"),
        "effort": "high",
        "memory": "project",
        "workspace": "work/safety_translation",
    },
    "scientific_reviewer": {
        "description": "Scientific reviewer — evaluates specialist outputs before a verdict",
        "prompt": _load_prompt("scientific_reviewer"),
        "tools": _REVIEWER_TOOLS,
        "model": os.getenv("SYFLOW_REVIEWER_MODEL", "claude-haiku-4-5-20251001"),
        "effort": "high",
        "memory": "project",
        "workspace": "work/scientific_reviewer",
    },
}


def get_agent_config(agent_name: str) -> dict[str, Any]:
    """Return the configuration for one small-molecule agent."""
    if agent_name not in AGENT_REGISTRY:
        raise ValueError(f"Unknown agent: {agent_name}. Available: {list(AGENT_REGISTRY.keys())}")
    return AGENT_REGISTRY[agent_name]


def build_specialist_agents(run_dir: Path) -> list[dict[str, Any]]:
    """Build specialist configs and create each workspace under the run directory."""
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
        if "workspace" in config:
            workspace = run_dir / config["workspace"] / "results"
            workspace.mkdir(parents=True, exist_ok=True)
            agent_def["workspace"] = str(workspace)
        agents.append(agent_def)
    return agents


def _build_agent_prompt(name: str, config: dict, run_dir: Path) -> str:
    base_prompt = config["prompt"]
    workspace = config.get("workspace", f"work/{name}")
    workspace_path = run_dir / workspace / "results"
    instructions = f"""
## Workspace

You are operating within a SyFlow small-molecule run directory: {run_dir}
Your workspace: {workspace_path}

Save output artifacts to your workspace directory.
Register each artifact with `mcp__provenance__register_artifact`.

## Evidence citation rules

Every finding must include:
- Evidence type label: prediction | literature_evidence | retrospective_analysis | syflow_wetlab | independent_replication
- For wet-lab evidence: ELN/LIMS batch ID, assay version, operator, date
- For citations: PMID or DOI
- Confidence level: strong | moderate | weak

A docking score, generative-model rank, or predicted ADME value is `prediction`.
It cannot satisfy a gate that asks for a measured assay.

Format claims as: [[claim:XX]] followed by the claim text.
Do not write synthetic routes, reagents, or reaction conditions.
"""
    return base_prompt + "\n\n" + instructions
