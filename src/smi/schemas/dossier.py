"""Small-molecule inhibitor candidate dossier.

One dossier is one decision unit:
indication × protein target × compound × assay batch.
A recorded structure without a batch is not a compound candidate.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class SMIModality(str, Enum):
    INHIBITOR = "small_molecule_inhibitor"


class SMIStage(str, Enum):
    TARGET_ID = "target_identification"
    HIT_CONFIRMATION = "hit_confirmation"
    LEAD_OPTIMIZATION = "lead_optimization"
    IN_VITRO = "in_vitro_characterization"
    IN_VIVO = "in_vivo_evaluation"
    IND_ENABLING = "ind_enabling"


class SMITargetProfile(BaseModel):
    """Protein target and the patient subset an inhibitor would be for."""

    gene_symbol: str
    protein_name: str
    indication: str
    uniprot_id: Optional[str] = None
    patient_subset: Optional[str] = None
    localization: Optional[str] = None
    protein_expression_disease: Optional[str] = Field(
        None, description="Protein-level disease expression. RNA is supporting only."
    )
    normal_tissue_expression: Optional[str] = None
    known_variants: list[str] = Field(default_factory=list)


class CompoundProfile(BaseModel):
    """One compound batch. Identity fields do not imply potency."""

    compound_id: str
    source: str = Field(..., description="Where this chemical matter was recorded")
    smiles: Optional[str] = None
    chembl_id: Optional[str] = None
    batch_id: Optional[str] = None
    lims_id: Optional[str] = None
    eln_reference: Optional[str] = None
    identity_method: Optional[str] = None
    purity_percent: Optional[float] = None


class SMIDossier(BaseModel):
    """Complete small-molecule inhibitor dossier."""

    model_config = ConfigDict(extra="allow")

    dossier_id: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    modality: SMIModality = SMIModality.INHIBITOR
    stage: SMIStage = SMIStage.TARGET_ID
    version: str = "1.0"

    target_profile: SMITargetProfile
    compound: Optional[CompoundProfile] = None

    current_gate: str = "M0"
    gate_history: list[dict] = Field(default_factory=list)
    recommendation: Optional[str] = Field(None, pattern=r"^(go|hold|no_go)$")
    next_experiment: Optional[str] = None
    decision_rationale: Optional[str] = None
    human_approver: Optional[str] = None
    approval_date: Optional[str] = None
    run_ids: list[str] = Field(default_factory=list)
    claim_ids: list[str] = Field(default_factory=list)

    def advance_gate(self, gate_id: str, verdict: str, rationale: str,
                     approver: Optional[str] = None) -> None:
        """Record a gate decision and advance on an explicit Go."""
        self.gate_history.append({
            "gate": gate_id,
            "verdict": verdict,
            "rationale": rationale,
            "approver": approver,
            "timestamp": datetime.now().isoformat(),
        })
        if verdict == "go":
            gate_order = ["M0", "M1", "M2", "M3", "M4", "M5"]
            idx = gate_order.index(gate_id)
            if idx + 1 < len(gate_order):
                self.current_gate = gate_order[idx + 1]
        self.updated_at = datetime.now()
