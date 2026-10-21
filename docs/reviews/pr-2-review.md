# PR #2 targeted review, 2026-10-21

Reviewed base `09d682d9dc06c8ee31576d470412816e474794c5` and original PR head
`2199605e06bb9bb5a4c45b68972b222a7cf76253`. No merge or license approval.

## Findings and minimal fixes

1. **Packaging, high:** CLI and MCP defaulted to the parent of the installed `src`
   package for mutable runs and external dossiers. A wheel therefore used site-packages.
   Both now share workspace resolution; wheel tests run outside the checkout and
   assert the imported package is inside the wheel installation. Explicit dossiers
   and `SYFLOW_PROJECT_ROOT` support external inputs without copying scientific data
   into the distribution. Missing inputs fail before run creation.
2. **Gate source, high:** Python is the existing runtime policy in both CLI and MCP.
   YAML is not equivalent: e.g. G1 criterion identifiers differ, G3 uses
   `lot_to_lot` instead of `lot_to_lot_identity`, G4 omits `no_advantage_over_free_payload`, and YAML adds
   evidence-type annotations not enforced by Python. Marked YAML reference-only;
   no criteria, triggers, thresholds or evidence requirements were changed.
   Fixture extracted directly from the base commit locks every G0-G5 definition.
3. **Registry, medium:** seven agents = five domain specialists + CSO + reviewer.
   Corrected CLAUDE.md. G3/G4 still share conjugation_payload; no new specialist.
4. **Targets, medium:** four supported choices now come from packaged targets.yaml,
   replacing duplicated hardcoded lists. TNF-alpha and NK2R are not enabled:
   their existing binder/agonist dossiers do not specify `is_surface_protein`,
   and the current plan builder defaults missing values to true. Their workflows
   need modality review rather than silently treating them as cytotoxic NDCs.
5. **Execution/provenance, high:** initialization previously logged agent start/stop
   and attributed CLI-written task.md files to agents that never ran. Removed fake
   agent lifecycle events; attributed task files to cli_initializer. Audit now loads
   the saved plan, so pending steps are reported rather than an empty plan.
   This is an intentional reporting correction, not a change to scientific policy.

## Scientific boundaries and remaining issues

- G0-G5 are declarative criteria and triggers, not an executable decision engine.
  A GateDecision can hold a caller-supplied verdict; automatic evidence sufficiency,
  frozen-threshold timing and human approval are not enforced. A computational
  prediction must not be interpreted as expression, binding, affinity or function.
- EvidenceType remains exactly prediction, literature_evidence,
  retrospective_analysis, syflow_wetlab and independent_replication. These are
  evidence origins, not an automatic confidence ranking. Confidence remains
  strong/moderate/weak. Existing scientific schema definitions are unchanged.
- Existing claim validation labels an artifact verified on manifest membership;
  it does not re-hash that file at claim-validation time. RunManifest.verify_all
  detects missing/modified files separately. A verified claim is not therefore
  proof that its scientific evidence is valid or currently intact.
- Existing tool-call validation checks whether the ID appears, not whether the
  call completed successfully. Existing has_batch_provenance checks ELN/LIMS for
  syflow_wetlab only, not all required metadata or independent_replication.
- `verify` can report an empty manifest as clean and does not return failure for
  manifest issues. Treat it as a report, not an automated scientific release gate.
- Inputs are not all registered in the manifest; tool allowlists and workspace
  instructions are not enforced sandbox boundaries without an executor.
- Those pre-existing validation limitations are not introduced by the restructure;
  this patch preserves the validation engine and calls them out for a dedicated
  hardening change before using this as an operational Go/No-Go system.
- PNPLA3/RhoA/TAK1 classifications and dossier gate expectations are project
  annotations, not measured outcomes or a completed modality validation.

## Verification

Original remote CI run 39449422348: success, Python 3.11, Ruff + smoke + help only.
Local repair validation: Python 3.12.14, Ruff, smoke, eight regression tests,
and wheel build/install with the same eight tests from an unrelated working
folder. Wheel checks include all seven prompts, packaged target configuration,
external dossier input, pending audit plans, no fictitious agent/tool/gate events,
G0-G5 baseline equality, evidence states, wet-lab batch checks, provenance
round-trip and manifest tamper/missing-file detection.

The wheel test reuses locally installed dependency packages; it is not a clean
full dependency-resolution test. No AI API calls, wet-lab experiments, biological
replication, automatic Go/No-Go decisions or replay were executed. Updated CI adds
regressions and wheel validation on Python 3.11; its result must be checked for
the new commit, not inferred from the original green run.

## Owner decisions before merge

- MIT license and copyright holder (left untouched).
- Unifying Python/YAML policy and enforcing evidence eligibility.
- Adding a specialist, renaming the src package or supporting non-NDC modalities.

Recommendation: keep draft until owner decisions and updated CI are reviewed.
