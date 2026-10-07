# challenge_bootstrap

A small configuration bridge around existing SyFlow components, not a new design pipeline.
The checked-in Challenge 3 config intentionally cannot run until the official problem is released.
No target, ortholog, assembly, pH direction, molecule class or experimental requirement is inferred.
No GPU job or Proteinbase upload is performed by `check` or `prepare`.

## Source audit and reuse map

Audited `mrfeixiang/SyFlow-NDC` main at `09d682d9dc06c8ee31576d470412816e474794c5`.
The default branch was the only branch returned; no open PR was returned during the audit.
`mrfeixiang/nanobody-workflow` contains presentation assets rather than a computation framework.
This audit does not cover unpublished scripts on the laboratory workstation.

| Requirement | Existing implementation | Minimal bridge / actual gap |
|---|---|---|
| Target / ortholog | `src/config/targets.yaml`, `targets/*/dossier.yaml` | Per-campaign construct, species, source and explicit chains in YAML; no NDC indication assumptions |
| Chain / multimer | `targets/tnfa/results/initial_analysis/boltz_inputs/*.yaml` | Preserve every configured protomer, allocate binder IDs without collision, check predicted PDB chain sequences |
| Class / length | `evaluate_egfr_vhh.py:print_evaluation_report` reports 10–250 aa and assumes nanobody | Fail before preparation on invalid class, per-chain length, alphabet, duplicate IDs or sequences; rules must be confirmed for each challenge |
| Zero-shot / novelty | EGFR report estimates novelty from diversity; no evidence gate found | Separate sequence-hash-bound evidence reviews; unknown/fail blocks export; experimental feedback cannot pass zero-shot |
| Ortholog / pH / off-target | TNF script has mouse branch and His-count heuristic | Explicit enable/disable; ortholog QC contexts; pH/off-target require local evidence adapters; His count is never a pH score |
| Batch Boltz | `targets/tnfa/results/initial_analysis/run_batch_boltz.sh` | Generalizes its `boltz predict` and confidence-JSON pattern to context × seed jobs; retains exit status/logs, requires all seeds; uses existing Boltz CLI, not another predictor |
| Ranking / diversity | `evaluate_egfr_vhh.py:select_diverse_top20` | Direct import; supply measured QC summary instead of mixed/estimated legacy composite scores |
| CSV export | `evaluate_egfr_vhh.py:write_submission_csv` | Direct import; one backwards-compatible change allows per-candidate molecule class |
| Metadata / provenance | `src/utils/run_manifest.py:RunManifest` | Direct import for SHA-256 registry and verification; snapshot config, evidence, jobs, source hashes, commit, version, output and metadata |
| General orchestration | `run_syflow.py`, `src/utils/plan_runner.py` | Existing orchestrator is an NDC agent/gate assessment, not a Boltz job runner; leave it unchanged |

The TNF legacy batch uses one diffusion sample, has no explicit seed and reads only `model_0`.
The inspected TNF YAML contains one target chain plus one VHH, not the full trimer.
The main TNF shell script has workstation-specific paths and several warning-and-continue branches.
These scripts and historical results are preserved. The bootstrap does not call their target-specific wrappers.
EGFR loaders mix targets/metrics and contain estimated scores, so only the pure diversity selector and exporter are reused.

## Before Challenge 3 opens

```bash
python -m challenge_bootstrap check --config challenge_bootstrap/challenge3.yaml
# Expected: exit 2, BLOCKED: rules.source_url is UNSET
python -m unittest discover -s tests -v
```

Dependencies: existing SyFlow environment (`environment.yml`). Boltz must be installed separately
in the same Python environment as this entry point. Run from repository root.

## After release

1. Copy `challenge3.yaml` to a campaign config. Fill the official URL and review date;
   allowed classes, per-chain limits, submission count and zero-shot/novelty requirements.
   Confirm these against the actual upload form. Earlier rounds' limits are not silently inherited.
2. Fill target ID, species, exact soluble/domain construct, assembly reference and all chains.
   Each protomer is a separate `{id, sequence, source}` record, including identical copies.
   `assembly_source` records where the biological assembly came from; it is not a structure restraint.
   Resolve chain renumbering/construct boundaries before starting.
3. Explicitly enable or disable each condition. Add complete ortholog/off-target context records
   if enabled. pH/off-target need evidence-producing adapters as described below.
4. Supply candidates exported by the existing design engine. Supply evidence review JSON.
   Paths in the YAML and evidence JSON resolve relative to the YAML's directory.
5. Pin installed Boltz version (`python -c 'import importlib.metadata; print(importlib.metadata.version("boltz"))'`).
   Set score/seed-variability thresholds *before* evaluating candidates. Seeds `[11,22,33]`,
   recycling steps `3` and diversity cutoff `0.90` are editable engineering defaults, not official rules.
6. Run the following stages. Use a new run directory for every configuration/sequence change:

```bash
python -m challenge_bootstrap check --config path/to/campaign.yaml
python -m challenge_bootstrap prepare --config path/to/campaign.yaml --run-dir runs/YYYYMMDD_challenge3_RUNID
# Review inputs/jobs.json, chain maps and job count before launching GPU work.
python -m challenge_bootstrap run --run-dir runs/YYYYMMDD_challenge3_RUNID
python -m challenge_bootstrap collect --run-dir runs/YYYYMMDD_challenge3_RUNID
python -m challenge_bootstrap export --run-dir runs/YYYYMMDD_challenge3_RUNID
```

`run` executes jobs sequentially to fit a single GPU; it records nonzero exits instead of hiding them.
It refuses to repeat an attempted execution in the same directory. Failed/incomplete runs require a
fresh directory; automatic resume/caching and scheduler integration are deliberately outside this minimum.
`collect` can show ranking and failure reasons even when some jobs fail. `export` includes only eligible
candidates and refuses an empty or previously exported bundle. It does not submit anything remotely.
All stages after preparation verify the existing manifest before reading prior artifacts.

### Candidate CSV

Columns: `name,sequence,molecule_class,source`.
Names use letters/digits/underscore/hyphen. Sequences use uppercase canonical amino acids.
For supported paired formats use `VH:VL`; lengths are checked per component, not on the combined string.
The class must also be allowed by the campaign's reviewed rules. Semantic VHH/VH/VL annotation is
not inferred from length; add an annotation hook if required by the new challenge.

### Evidence JSON

```json
{
  "YOUR_CANDIDATE_ID": {
    "sequence_sha256": "SHA256_OF_EXACT_CSV_SEQUENCE_INCLUDING_COLON_IF_PRESENT",
    "target_specific_experimental_feedback_used": false,
    "zero_shot": {"status": "unknown", "evidence_path": null},
    "novelty": {"status": "unknown", "evidence_path": null}
  }
}
```

A `pass` requires a local evidence document, copied and hashed into the run. The review should identify
the challenge, target, generator/version, scaffold/CDR origins, design date, data used, template/binder
origins and any experimental feedback. Novelty evidence should record the search/reference snapshot,
method and separate sequence/structure conclusions. The code validates evidence presence and sequence
linkage; it cannot independently prove a truthful zero-shot declaration or assign Proteinbase novelty levels.
Diversity is the legacy positional match heuristic, not an alignment or novelty measurement.
Keep statuses `unknown` until the underlying review is complete. Do not migrate old estimated scores as evidence.

### Optional adapters

The local command is configured as an argument list, never a shell command string:

```yaml
hooks:
  ph:
    argv: [python, /absolute/path/to/existing_ph_adapter.py, --config, '{config}', --candidates, '{candidates}', --output, '{output}']
```

Commands get the snapshotted config and candidates JSON. The adapter should reuse the corresponding
existing local tool, and write a JSON object keyed by candidate name:

```json
{"YOUR_CANDIDATE_ID": {"sequence_sha256": "EXACT_SEQUENCE_HASH", "status": "unknown", "evidence": "method/version/result reference", "metrics": {}}}
```

Every configured hook is an export gate. It must return exit code 0 and per-candidate `pass`, a matching
hash, and evidence. Missing results/unknown/fail all block that candidate. Use optional `assembly`,
`annotation` or `novelty_search` hooks for additional checks. Native Boltz is not treated as a pH predictor;
simply labelling identical inputs with two pH values cannot establish conditional binding.

## Outputs and interpretation

- `inputs/`: immutable config, candidate/evidence snapshots, generated multichain YAML and job argument lists.
- `work/boltz/`: separate output directory and log per candidate/context/seed.
- `work/hooks/`: condition adapter result JSON/logs.
- `execution.json`: actual version and command return codes.
- `ranking.csv` / `ranking.json`: all candidates, QC eligibility, exclusions and per-context seed mean/SD.
- `export/submission.csv`: the existing `name,sequence,molecule_class` format.
- `export/metadata.json`: local sidecar containing rules, target/conditions, evidence references, scores and provenance.
- `MANIFEST.json`: SyFlow artifact hashes. Preserve the whole run folder with the export.

Ranking is the minimum, across the target and enabled positive orthologs, of the mean over seeds
of bidirectional binder-target pair iPTM values. All binder-target chain pairs are included. Antigen-antigen
pairs are excluded. Off-target scores are reported but an explicit adapter decides selectivity; high
confidence is not automatically high binding affinity. Scores, thresholds and seed SD are triage aids,
not experimental binding/functional validation. For an asymmetric multimer, the pair aggregation may
need an epitope-aware adapter once the actual target is known.

PDB checks preserve chain identity and sequence coverage. They do **not** prove correct trimer geometry,
inter-protomer contacts, accessibility, receptor competition, disulfides or binding affinity. Use an assembly/
interface adapter and inspect top complexes where these matter. The bootstrap uses sequence-based
Boltz refolding, not fixed-coordinate target docking. A full assembly YAML alone cannot guarantee geometry.

Metadata is a local review sidecar, not an assertion that Proteinbase accepts a JSON metadata upload.
A researcher must inspect designs and complete the actual submission form after export.

## Validation scope

Offline tests cover unresolved placeholders, multimer chain loss, pair-specific scoring, missing seed,
class/per-chain length, unknown/stale zero-shot/novelty evidence, experimental-feedback exclusion,
pH adapter requirement, duplicate seeds, artifact drift and export overwrite prevention.
Synthetic fixtures are created in temporary directories and removed. No model weights, GPU prediction,
paid API jobs, novelty database search, or competition submission were run during implementation.
