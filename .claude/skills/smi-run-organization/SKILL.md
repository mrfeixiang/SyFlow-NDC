# Small-molecule inhibitor runs

Use this skill when the CSO is organizing a small-molecule inhibitor validation run. NDC runs stay on the nanobody skill. The two gate tables are not interchangeable.

## Decision unit

indication × protein target × compound × assay batch

## Gates

| Gate | Agent | Question |
|---|---|---|
| M0 | `target_biology` | Protein-level target credibility in a defined population |
| M1 | `ligand_chemistry` | Batch identity, purity, and stability |
| M2 | `pharmacology` | Orthogonal biochemical potency and a pre-registered selectivity panel |
| M3 | `pharmacology` | Cellular engagement separated from cytotoxicity |
| M4 | `adme_exposure` | Measured ADME and exposure versus a pre-registered free concentration |
| M5 | `safety_translation` | Safety panel and therapeutic window |

Runtime rules are `src/smi/schemas/gate.py`. `src/smi/config/gates.yaml` is a reference copy and is not loaded by the CLI.

## Commands

```bash
python -m src.smi validate --target pnpla3
syflow smi validate --target pnpla3
syflow smi gate --target pnpla3 --gate M0 --dossier targets/pnpla3/smi_dossier.yaml
python -m src verify --run-id <RUN_ID>
```

`validate` and `gate` write a pending plan under `SYFLOW_RUNS_DIR`. They do not call a model and they do not assign a verdict. The same `verify` command used for NDC runs checks the manifest and trace.

## Plan rules

- If the dossier has a `compound` mapping, chemistry starts in parallel with target biology.
- If it does not, chemistry is a landscape review and waits for M0. The PNPLA3 reference dossier is in this second state: its SMILES strings live under `recorded_structures`.
- Cellular engagement depends on the biochemical step.
- ADME depends on chemistry and can run beside pharmacology.
- The reviewer is last.

## Evidence

Use the same five evidence types as the NDC module. A model score is `prediction`. Wet-lab claims need an ELN or LIMS batch ID. Do not write synthetic routes.
