# Evidence Citation Skill — SyFlow NDC Platform

## When to use
Use this skill whenever a specialist agent produces a finding that will support a gate decision.

## Evidence citation rules

Every finding MUST include:

### 1. Evidence type label (REQUIRED)
- `prediction` — computational estimate, model score, docking result
- `literature_evidence` — published finding (must include PMID or DOI)
- `retrospective_analysis` — re-analysis of existing datasets
- `syflow_wetlab` — SyFlow laboratory measurement
- `independent_replication` — external validation of SyFlow finding

### 2. Provenance (type-dependent)

**For predictions:**
- Model name and version
- Input parameters
- Confidence metric

**For literature evidence:**
- PMID or DOI (required)
- Journal, year
- Key figure/table reference

**For wet-lab measurements (syflow_wetlab):**
- ELN entry ID (required)
- LIMS batch ID (required)
- Assay protocol version
- Operator name
- Date performed
- Raw data file path
- Instrument and method

**For retrospective analysis:**
- Dataset name and version
- Analysis script path
- Date of analysis

### 3. Confidence level (REQUIRED)
- `strong` — multiple independent lines of evidence, reproduced
- `moderate` — single reliable data source, awaiting replication
- `weak` — preliminary, indirect, or computational only

### 4. Claim format

```
[[claim:XX]] Claim text here.
- Evidence type: [type]
- Confidence: [level]
- Source: [provenance details]
```

### 5. Anti-patterns to avoid

- DO NOT present a model prediction as equivalent to experimental data
- DO NOT use RNA expression as sole evidence for a target gate (protein required)
- DO NOT cite a binding affinity on recombinant protein as proof of cell-surface selectivity
- DO NOT omit batch IDs for wet-lab measurements
- DO NOT claim selectivity without testing against relevant high-expression controls
