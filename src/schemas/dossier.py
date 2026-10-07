"""NDC candidate dossier schema.

One dossier = one decision unit:
indication × surface antigen × VHH sequence × conjugation site × linker-payload × batch
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ModalityType(str, Enum):
    NDC = "nanobody_drug_conjugate"
    SMALL_MOLECULE = "small_molecule"
    VHH_NAKED = "vhh_naked"
    BISPECIFIC_VHH = "bispecific_vhh"


class DevelopmentStage(str, Enum):
    TARGET_ID = "target_identification"
    BINDER_DISCOVERY = "binder_discovery"
    CONJUGATION = "conjugation_optimization"
    IN_VITRO = "in_vitro_characterization"
    IN_VIVO = "in_vivo_evaluation"
    IND_ENABLING = "ind_enabling"


class TargetProfile(BaseModel):
    """Surface antigen and patient-selection profile."""
    gene_symbol: str
    uniprot_id: Optional[str] = None
    protein_name: str
    indication: str
    patient_subset: Optional[str] = None
    tumor_expression: Optional[str] = Field(None, description="Protein-level tumor expression summary")
    normal_tissue_expression: Optional[str] = Field(None, description="Normal tissue expression and safety window")
    membrane_topology: Optional[str] = Field(None, description="Extracellular domain accessibility")
    known_mutations: list[str] = Field(default_factory=list)
    internalization_competent: Optional[bool] = None
    antigen_density_range: Optional[str] = Field(None, description="Estimated copies/cell in target tissue")


class VHHProfile(BaseModel):
    """Nanobody binder profile."""
    vhh_id: str
    sequence: Optional[str] = None
    source: str = Field(..., description="e.g., immunization, phage display, computational design")
    target_epitope: Optional[str] = None
    epitope_domain: Optional[str] = Field(None, description="e.g., domain IV, deletion junction")
    kd_recombinant: Optional[str] = Field(None, description="KD on recombinant protein")
    kd_live_cell: Optional[str] = Field(None, description="KD on live cells — required for G1")
    selectivity_ratio: Optional[str] = Field(None, description="Mutant vs WT binding ratio if applicable")
    species_crossreactivity: list[str] = Field(default_factory=list)
    thermal_stability_tm: Optional[float] = None
    aggregation_percent: Optional[float] = None
    expression_yield: Optional[str] = None
    pdb_id: Optional[str] = None
    structure_method: Optional[str] = None


class LinkerPayload(BaseModel):
    """Linker-payload chemistry profile."""
    linker_type: str = Field(..., description="e.g., MC-vc-PAB, glucuronide, non-cleavable")
    payload_name: str
    payload_class: str = Field(..., description="e.g., MMAE, SN-38, DXd, PBD")
    payload_moa: str = Field(..., description="Mechanism: microtubule, topoisomerase, DNA-alkylating")
    conjugation_chemistry: str = Field(..., description="e.g., Sortase-LPETG, SPAAC, maleimide")
    conjugation_site: str = Field(..., description="e.g., C-terminal, engineered Cys, Lys")
    target_dar: Optional[float] = Field(None, description="Target drug-to-antibody ratio")
    bystander_effect: Optional[bool] = None
    membrane_permeable_payload: Optional[bool] = None


class ConjugateProduct(BaseModel):
    """Manufactured NDC batch characterization."""
    batch_id: str
    lims_id: Optional[str] = None
    vhh_id: str
    linker_payload_id: str
    measured_dar: Optional[float] = None
    intact_mass: Optional[str] = None
    free_payload_percent: Optional[float] = None
    aggregation_percent: Optional[float] = None
    endotoxin: Optional[str] = None
    serum_stability_days: Optional[float] = None
    serum_stability_intact_percent: Optional[float] = None
    conjugation_date: Optional[str] = None
    operator: Optional[str] = None
    eln_reference: Optional[str] = None


class NDCDossier(BaseModel):
    """Complete NDC candidate dossier — the unit of Go/No-Go decision."""
    dossier_id: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    modality: ModalityType = ModalityType.NDC
    stage: DevelopmentStage = DevelopmentStage.TARGET_ID
    version: str = "1.0"

    # Core components
    target: TargetProfile
    vhh: Optional[VHHProfile] = None
    linker_payload: Optional[LinkerPayload] = None
    conjugate: Optional[ConjugateProduct] = None

    # Gate status
    current_gate: str = "G0"
    gate_history: list[dict] = Field(default_factory=list)

    # Decision
    recommendation: Optional[str] = Field(None, pattern=r"^(go|hold|no_go)$")
    next_experiment: Optional[str] = None
    decision_rationale: Optional[str] = None
    human_approver: Optional[str] = None
    approval_date: Optional[str] = None

    # Provenance
    run_ids: list[str] = Field(default_factory=list)
    claim_ids: list[str] = Field(default_factory=list)

    def advance_gate(self, gate_id: str, verdict: str, rationale: str,
                     approver: Optional[str] = None) -> None:
        """Record a gate decision and advance if Go."""
        self.gate_history.append({
            "gate": gate_id,
            "verdict": verdict,
            "rationale": rationale,
            "approver": approver,
            "timestamp": datetime.now().isoformat(),
        })
        if verdict == "go":
            gate_order = ["G0", "G1", "G2", "G3", "G4", "G5"]
            idx = gate_order.index(gate_id)
            if idx + 1 < len(gate_order):
                self.current_gate = gate_order[idx + 1]
        self.updated_at = datetime.now()
