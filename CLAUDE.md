# SyFlow NDC Go/No-Go Platform

## Overview
This is the SyFlow target validation and NDC (Nanobody-Drug Conjugate) Go/No-Go decision platform.
It adapts Stanford's Virtual Biotech review-and-audit pattern for nanobody drug conjugate development.

The unit of work is one **NDC candidate dossier**:
*indication × surface antigen × VHH sequence × conjugation site × linker-payload × manufacturing batch*

## Architecture
- **6 specialist agents** + 1 CSO orchestrator + 1 scientific reviewer
- **6 gates** (G0-G5) with Go/Hold/No-Go decisions
- **Provenance-first**: every claim must cite verifiable evidence
- **Evidence types**: prediction, literature_evidence, retrospective_analysis, syflow_wetlab, independent_replication

## Active Targets
| Target | Indication | Modality | Status |
|--------|-----------|----------|--------|
| PNPLA3 | NASH/MAFLD | Small molecule (existing SyFlow data) | Reference |
| RhoA | Solid tumors | VHH binder (LigandMPNN designs exist) | Reference |
| TAK1/MAP3K7 | Inflammation/Cancer | NDC candidate | Active |
| EGFRvIII | GBM/Solid tumors | NDC (mutant-selective VHH) | Pilot |

## Key conventions
- Gate thresholds are set BEFORE each experiment, not after
- RNA expression is supporting evidence only; protein-level data required for target gates
- A model score cannot replace a missing assay
- Every claim must be labelled with its evidence type
- ELN/LIMS batch IDs required for any wet-lab measurement claim
- Run directories: `runs/<YYYYMMDD>_<target>_<run_id>/`
- Artifacts: `runs/.../work/<agent_name>/results/`

## Commands
```bash
# Run a target validation
python -m src validate --target egfrviii --query "Evaluate EGFRvIII as NDC target for GBM"

# Run a gate assessment
python -m src gate --target egfrviii --gate G1 --dossier targets/egfrviii/dossier.yaml

# Verify a completed run
python -m src verify --run-id <RUN_ID>

# Replay a run (stochastic comparison)
python -m src replay --run-id <RUN_ID>
```

After `pip install -e .`, the same commands are available as `syflow validate|gate|verify|replay`.
Helper scripts live in `scripts/` (`setup_mcp.py`, `evaluate_egfr_vhh.py`, slide builders).
Slide decks live in `docs/slides/`.

## Related AIDD SYStem resources
- PNPLA3 binding: `../Nesso-1/nesso_pnpla3/` (Nesso/Boltz-2 docking)
- RhoA design: `../ligandMNPP/rhoa_pipeline/` (LigandMPNN binder design)
- ADC chemistry: `../MediChem-FX/V3_ADC_Project_Arrow.md`
- Docking: `../GNINA/` (GNINA docking pipeline)
