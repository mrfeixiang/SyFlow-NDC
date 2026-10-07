"""Evidence and claim schemas for SyFlow NDC Go/No-Go platform.

Adapted from Virtual Biotech claim validation (src/utils/claims.py) with
additions for NDC-specific evidence types: ELN/LIMS batch IDs, assay versions,
raw-data links, and human approval signatures.
"""
from __future__ import annotations

import re
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class EvidenceType(str, Enum):
    """How the evidence was produced. A model score cannot replace a missing assay."""
    PREDICTION = "prediction"
    LITERATURE = "literature_evidence"
    RETROSPECTIVE = "retrospective_analysis"
    WETLAB = "syflow_wetlab"
    REPLICATION = "independent_replication"


class EvidenceKind(str, Enum):
    """What form the evidence takes."""
    ARTIFACT = "artifact"
    FIGURE = "figure"
    TABLE = "table"
    CODE = "code"
    TOOL_CALL = "tool_call"
    CITATION = "citation"
    ASSAY_RESULT = "assay_result"
    BATCH_RECORD = "batch_record"


class VerificationStatus(str, Enum):
    """Three-state verification following Virtual Biotech semantics."""
    VERIFIED = "verified"       # Resolved against this run's manifest or trace
    EXTERNAL = "external"       # Citation (PMID/DOI/URL), not checkable locally
    UNRESOLVED = "unresolved"   # Cites local artifact NOT on record — a defect


class EvidenceItem(BaseModel):
    """A single piece of evidence supporting a claim."""
    kind: EvidenceKind
    evidence_type: EvidenceType
    path: Optional[str] = None
    note: Optional[str] = None
    verified: bool = False
    verification_status: VerificationStatus = VerificationStatus.UNRESOLVED
    sha256: Optional[str] = None
    produced_by: Optional[str] = None

    # For tool_call evidence
    tool_use_id: Optional[str] = None
    tool_name: Optional[str] = None
    agent: Optional[str] = None

    # For citation evidence
    pmid: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None

    # NDC-specific: wet-lab provenance
    eln_id: Optional[str] = Field(None, description="Electronic lab notebook entry ID")
    lims_batch_id: Optional[str] = Field(None, description="LIMS batch identifier")
    assay_id: Optional[str] = Field(None, description="Assay protocol version")
    assay_date: Optional[str] = Field(None, description="Date assay was performed")
    raw_data_path: Optional[str] = Field(None, description="Path to raw instrument data")
    operator: Optional[str] = Field(None, description="Person who performed the assay")


class Claim(BaseModel):
    """A verifiable claim in an NDC candidate dossier.

    Claim IDs follow the pattern [A-Za-z0-9_.-]{1,32}.
    Every claim must have at least one evidence item.
    """
    id: str = Field(..., pattern=r"^[A-Za-z0-9_.\-]{1,32}$")
    text: str
    agent: str
    confidence: str = Field(..., pattern=r"^(strong|moderate|weak)$")
    gate: Optional[str] = Field(None, description="Which gate (G0-G5) this claim supports")
    turn: Optional[int] = None
    evidence: list[EvidenceItem] = Field(..., min_length=1)
    n_verified: int = 0
    n_external: int = 0
    n_unresolved: int = 0
    created_at: Optional[datetime] = None

    @field_validator("id")
    @classmethod
    def validate_claim_id(cls, v: str) -> str:
        if not re.match(r"^[A-Za-z0-9_.\-]{1,32}$", v):
            raise ValueError(f"Claim ID must match [A-Za-z0-9_.\\-]{{1,32}}, got: {v}")
        return v

    def recount_verification(self) -> None:
        """Recompute verification counts from evidence items."""
        self.n_verified = sum(
            1 for e in self.evidence
            if e.verification_status == VerificationStatus.VERIFIED
        )
        self.n_external = sum(
            1 for e in self.evidence
            if e.verification_status == VerificationStatus.EXTERNAL
        )
        self.n_unresolved = sum(
            1 for e in self.evidence
            if e.verification_status == VerificationStatus.UNRESOLVED
        )

    def has_wetlab_evidence(self) -> bool:
        """Check if this claim has any wet-lab measurement evidence."""
        return any(
            e.evidence_type in (EvidenceType.WETLAB, EvidenceType.REPLICATION)
            for e in self.evidence
        )

    def has_batch_provenance(self) -> bool:
        """Check if wet-lab evidence has required batch/ELN provenance."""
        for e in self.evidence:
            if e.evidence_type == EvidenceType.WETLAB:
                if not (e.eln_id or e.lims_batch_id):
                    return False
        return True
