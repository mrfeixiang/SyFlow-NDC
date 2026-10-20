# Run Organization Skill — SyFlow NDC Platform

## When to use
Use this skill when the CSO agent is organizing a new validation run, dispatching specialists, or finalizing a gate decision.

## Run directory structure

```
runs/<YYYYMMDD>_<target>_<NNN>/
├── inputs/
│   ├── dossier.yaml          # Target dossier (frozen at run start)
│   ├── plan.json              # Analysis plan DAG
│   └── query.txt              # Original query
├── work/
│   ├── target_patient/
│   │   └── results/           # Target assessment artifacts
│   ├── nanobody_epitope/
│   │   └── results/           # VHH assessment artifacts
│   ├── delivery/
│   │   └── results/           # Internalization/trafficking artifacts
│   ├── conjugation_payload/
│   │   └── results/           # Product characterization artifacts
│   ├── translation_safety/
│   │   └── results/           # PK/safety artifacts
│   └── scientific_reviewer/
│       └── results/           # Review reports
├── MANIFEST.json              # Artifact registry with hashes
├── trace.jsonl                # Execution trace (append-only)
├── run_metadata.json          # Run ID, status, timestamps
├── provenance_report.md       # Who did what (reconstructed from trace)
├── audit.json                 # Final audit record
└── README.md                  # Human-readable run summary
```

## CSO workflow

### 1. Plan declaration
Before dispatching any specialist, declare the analysis plan:

```
write_plan(
    goal="Validate EGFRvIII as NDC target for GBM",
    steps=[
        {"id": "s1", "agent": "target_patient", "task": "...", "depends_on": []},
        {"id": "s2", "agent": "nanobody_epitope", "task": "...", "depends_on": []},
        ...
    ]
)
```

The plan is validated as a DAG (cycle detection via topological sort).
Parallel groups are computed automatically.

### 2. Specialist dispatch
- Dispatch specialists in parallel where dependencies allow
- Each specialist writes to `work/<agent_name>/results/`
- Each specialist registers artifacts via `register_artifact`
- Each specialist returns FINDING/EVIDENCE/CONFIDENCE blocks

### 3. Review
- ALWAYS send specialist outputs to `scientific_reviewer` before synthesis
- The reviewer returns: Approve, Minor Revision, or Major Revision
- If Major Revision: re-delegate to the specialist with specific instructions

### 4. Claim recording
- Embed `[[claim:XX]]` references in the synthesis report
- Call `record_claims` with all claims — validated against MANIFEST.json and trace.jsonl
- Claims with nonexistent evidence paths are REJECTED

### 5. Gate decision
- Collect all evidence for the relevant gate
- Check against gate definitions (src/config/gates.yaml)
- Record verdict: Go, Hold (with specified next experiment), or No-Go (with rationale)
- Require human approval signature for any Go decision

## Commands

From the repository root, after `pip install -e .`:

```bash
python -m src validate --target egfrviii --query "Evaluate EGFRvIII as NDC target for GBM"
python -m src gate --target egfrviii --gate G1 --dossier targets/egfrviii/dossier.yaml
python -m src verify --run-id <RUN_ID>
python -m src replay --run-id <RUN_ID>
python scripts/setup_mcp.py
```

`syflow` is the installed console script for the same subcommands.

## Key rules

- The CSO has NO data query tools — delegate all analysis
- Plan deviation is expected — record it, don't treat it as failure
- Thresholds are set BEFORE experiments, not after
- RNA is supporting evidence only — protein data required for G0
- Every claim needs at least one piece of verifiable evidence
