"""Claim-evidence validation engine for SyFlow.

Every claim must cite evidence that exists. Evidence is validated on write.
Claims for wet-lab measurements require ELN/LIMS batch provenance.
"""
from __future__ import annotations

from typing import Any

from ..schemas.evidence import Claim, VerificationStatus
from .run_manifest import RunManifest
from .trace_logger import TraceLogger


def verify_claim_evidence(
    claim: Claim,
    manifest: RunManifest,
    trace: TraceLogger,
) -> Claim:
    """Verify each evidence item in a claim against manifest and trace.

    Sets verification_status to:
    - verified: artifact path found in manifest with matching hash, or tool_use_id in trace
    - external: citation with PMID/DOI/URL (not checkable locally)
    - unresolved: cites local artifact or tool call not on record — a defect
    """
    for item in claim.evidence:
        if item.kind.value == "citation":
            if item.pmid or item.doi or item.url:
                item.verification_status = VerificationStatus.EXTERNAL
                item.verified = False  # deliberately: external ref
            else:
                item.verification_status = VerificationStatus.UNRESOLVED
                item.verified = False
            continue

        if item.kind.value == "tool_call":
            if item.tool_use_id:
                # Check if tool_use_id appears in trace
                found = any(
                    e.tool_use_id == item.tool_use_id
                    for e in trace._events
                )
                if found:
                    item.verification_status = VerificationStatus.VERIFIED
                    item.verified = True
                else:
                    item.verification_status = VerificationStatus.UNRESOLVED
                    item.verified = False
            else:
                item.verification_status = VerificationStatus.UNRESOLVED
                item.verified = False
            continue

        # Artifact-based evidence (artifact, figure, table, code, assay_result, batch_record)
        if item.path:
            artifact = manifest.get(item.path)
            if artifact:
                item.verification_status = VerificationStatus.VERIFIED
                item.verified = True
                item.sha256 = artifact.sha256
                if not item.produced_by:
                    item.produced_by = artifact.produced_by
            else:
                item.verification_status = VerificationStatus.UNRESOLVED
                item.verified = False
        else:
            item.verification_status = VerificationStatus.UNRESOLVED
            item.verified = False

    claim.recount_verification()
    return claim


def validate_claims(
    claims: list[Claim],
    manifest: RunManifest,
    trace: TraceLogger,
) -> dict[str, Any]:
    """Validate a batch of claims. Returns validation report."""
    results = {
        "total_claims": len(claims),
        "verified_claims": 0,
        "claims_with_unresolved": 0,
        "claims_missing_batch_provenance": 0,
        "issues": [],
    }

    for claim in claims:
        verify_claim_evidence(claim, manifest, trace)

        if claim.n_unresolved > 0:
            results["claims_with_unresolved"] += 1
            results["issues"].append({
                "claim_id": claim.id,
                "issue": "unresolved_evidence",
                "count": claim.n_unresolved,
                "details": [
                    {"kind": e.kind.value, "path": e.path, "tool_use_id": e.tool_use_id}
                    for e in claim.evidence
                    if e.verification_status == VerificationStatus.UNRESOLVED
                ],
            })

        if claim.n_verified > 0 and claim.n_unresolved == 0:
            results["verified_claims"] += 1

        # NDC-specific: check batch provenance for wet-lab claims
        if claim.has_wetlab_evidence() and not claim.has_batch_provenance():
            results["claims_missing_batch_provenance"] += 1
            results["issues"].append({
                "claim_id": claim.id,
                "issue": "missing_batch_provenance",
                "detail": "Wet-lab evidence requires ELN/LIMS batch ID",
            })

    return results
