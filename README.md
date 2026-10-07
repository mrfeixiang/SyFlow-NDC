# SyFlow NDC Go/No-Go Platform

A provenance-first decision framework for nanobody-drug conjugate (NDC) development, adapting Stanford's [Virtual Biotech](https://github.com/harrisongzhang/TheVirtualBiotech) review-and-audit pattern to produce traceable Go/Hold/No-Go decisions across six gates.

## Overview

The unit of work is one **NDC candidate dossier**: indication × surface antigen × VHH sequence × conjugation site × linker-payload × manufacturing batch.

Eight agents staff six gates:

| Agent | Gate | Role |
|---|---|---|
| CSO | All | Orchestrates specialists, synthesizes decisions (no data tools) |
| Target & Patient | G0 | Membrane accessibility, tumor expression, normal-tissue window |
| Nanobody & Epitope | G1 | Live-cell binding, selectivity, developability |
| Delivery | G2 | Internalization, trafficking, antigen-density dependence |
| Conjugation & Payload | G3/G4 | Product identity, stability, antigen-dependent killing |
| Translation & Safety | G5 | PK/PD, therapeutic window, kidney exposure |
| Scientific Reviewer | All | Read-only claim-by-claim audit |

## Active Targets

| Target | Classification | NDC Viable | Expected G0 |
|---|---|---|---|
| **EGFRvIII** | Surface neoantigen | Direct — ideal NDC target | Go |
| **TAK1** (MAP3K7) | Intracellular kinase | Indirect — surface receptor + TAK1i payload | Hold |
| **RhoA** | Intracellular GTPase | Indirect — via EphA2/CXCR4 | Hold |
| **PNPLA3** | Lipid droplet protein | Not viable for NDC | No-Go |

## Gate Framework

Six gates (G0–G5) with Go/Hold/No-Go decisions:

- **G0 — Target**: Protein-level expression required (RNA is supporting only)
- **G1 — VHH**: Live-cell binding on matched positive/negative cells
- **G2 — Delivery**: Internalization measured before toxin attachment
- **G3 — Product**: Site-specific conjugation, DAR, stability, lot-to-lot identity
- **G4 — Function**: Four matched controls (unconjugated VHH, nonbinding NDC, free payload, target-negative)
- **G5 — Translation**: Therapeutic window with kidney exposure as primary NDC concern

Thresholds are set **before** each experiment. A model score cannot replace a missing assay.

## Computational Binder Design

49 EGFR/EGFRvIII VHH candidates designed on a single RTX 5080 GPU:

| Pipeline | Target | Candidates | Top Score |
|---|---|---|---|
| PPI-Flow (RFdiffusion + AbMPNN + Boltz-2) | EGFR WT | 20 | composite 0.82, iPTM 0.75 |
| OpenDDE / rfantibody | EGFRvIII | 20 | iPAE 18.80, pLDDT 0.90 |
| ForceFlowAb / IgLM | EGFRvIII | 10 | CDR-H3 diversity |

Top 20 selected with 90% sequence identity diversity filter → submitted to ProteinBase.

## Quick Start

```bash
# Set up environment
conda env create -f environment.yml
conda activate syflow-ndc
cp .env.example .env  # Add your ANTHROPIC_API_KEY

# Run target validation
python run_syflow.py validate --target egfrviii --query "Evaluate EGFRvIII as NDC target for GBM"

# Assess a specific gate
python run_syflow.py gate --target egfrviii --gate G0

# Verify a completed run
python run_syflow.py verify --run-id <RUN_ID>
```

## Project Structure

```
├── run_syflow.py                  # CLI: validate, gate, verify, replay
├── src/
│   ├── agents/                    # 7 agent system prompts + registry
│   ├── schemas/                   # Pydantic: claims, evidence, dossier, gates
│   ├── utils/                     # Trace, manifest, provenance, plan DAG, audit
│   ├── config/                    # Gate definitions, target registry (YAML)
│   └── mcp_servers/               # Provenance MCP server
├── targets/                       # Per-target dossier YAMLs
│   ├── egfrviii/dossier.yaml      # Pilot target
│   ├── tak1/dossier.yaml
│   ├── rhoa/dossier.yaml
│   └── pnpla3/dossier.yaml
├── proteinbase_submission/        # Top 20 VHH submission files
├── figures/                       # Architecture & workflow diagrams
├── SyFlow_NDC_Workflow.pptx       # English presentation
├── SyFlow_NDC_Workflow_KR.pptx    # Korean presentation
└── .claude/skills/                # Evidence-citation, run-organization
```

## Evidence Rules

Every claim must be labelled:
- `prediction` — computational estimate
- `literature_evidence` — published finding (PMID/DOI required)
- `retrospective_analysis` — re-analysis of existing data
- `syflow_wetlab` — laboratory measurement (ELN/LIMS batch ID required)
- `independent_replication` — external validation

## Key Design Principles

1. **Correct No-Gos are successes.** PNPLA3 should fail at G0. ABT-414 teaches that WT EGFR cross-reactivity kills programs.
2. **Evidence hierarchy beats agent count.** A model score cannot replace a missing assay.
3. **Provenance from execution, not self-report.** SHA-256 manifest, trace-based attribution.
4. **GPU + API = closed loop.** GPU generates candidates, API agents validate, the loop closes on the bench.
5. **The dossier is the unit of accountability.** One decision per dossier, fully auditable.

## Acknowledgments

Architecture adapted from Stanford's [Virtual Biotech](https://github.com/harrisongzhang/TheVirtualBiotech) review-and-audit pattern. The B7-H3 case study and provenance design informed our approach; the NDC-specific gates, evidence hierarchy, and wet-lab provenance requirements are original to SyFlow.

## License

MIT
