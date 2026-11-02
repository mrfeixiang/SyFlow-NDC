"""Gate decision schema for small-molecule inhibitor programs.

Six gates (M0–M5). Thresholds are frozen before the experiment from assay
variability, the indication, and a named reference compound. This module
does not set universal numeric cutoffs, and a model score cannot replace
a missing assay.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class SMIGateID(str, Enum):
    M0_TARGET = "M0"
    M1_CHEMISTRY = "M1"
    M2_POTENCY = "M2"
    M3_CELLULAR = "M3"
    M4_EXPOSURE = "M4"
    M5_SAFETY = "M5"


class SMIGateVerdict(str, Enum):
    GO = "go"
    HOLD = "hold"
    NO_GO = "no_go"


class SMIGateThreshold(BaseModel):
    """A measurable threshold frozen before the experiment."""

    parameter: str
    operator: str = Field(..., description=">=, <=, >, <, ==, range")
    value: str
    unit: Optional[str] = None
    rationale: str
    reference_compound: Optional[str] = None
    assay_cv_percent: Optional[float] = None
    set_date: str = Field(..., description="Date the threshold was frozen, before the experiment")
    set_by: Optional[str] = None


class SMIGateEvidence(BaseModel):
    """Evidence submitted against one gate criterion."""

    criterion: str
    claim_ids: list[str]
    threshold: Optional[SMIGateThreshold] = None
    measured_value: Optional[str] = None
    meets_threshold: Optional[bool] = None
    evidence_type: str
    notes: Optional[str] = None


class SMIGateDecision(BaseModel):
    """A gate assessment for one small-molecule inhibitor dossier."""

    gate_id: SMIGateID
    dossier_id: str
    target: str
    assessed_at: datetime = Field(default_factory=datetime.now)
    required_evidence: list[str]
    submitted_evidence: list[SMIGateEvidence] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    verdict: SMIGateVerdict
    rationale: str
    hold_reason: Optional[str] = None
    nogo_reason: Optional[str] = None
    next_experiment: Optional[str] = None
    reviewer_agent: str = "scientific_reviewer"
    reviewer_notes: Optional[str] = None
    human_approver: Optional[str] = None
    approval_date: Optional[str] = None
    run_id: Optional[str] = None
    conflicting_findings: list[str] = Field(default_factory=list)
    comparator_adequacy: Optional[str] = None


SMI_GATE_DEFINITIONS = {
    SMIGateID.M0_TARGET: {
        "name": "Target and Patient Biology",
        "required_evidence": [
            "defined_patient_subset",
            "protein_level_disease_relevance",
            "functional_or_genetic_support",
            "on_target_safety_biology",
        ],
        "hold_triggers": [
            "disease_protein_data_missing",
            "normal_tissue_protein_data_missing",
        ],
        "nogo_triggers": [
            "therapeutic_window_implausible",
            "no_protein_in_disease_tissue",
        ],
        "agent": "target_biology",
    },
    SMIGateID.M1_CHEMISTRY: {
        "name": "Chemical Matter Identity",
        "required_evidence": [
            "confirmed_structure",
            "batch_identity",
            "purity_or_composition",
            "chemical_stability_flag",
        ],
        "hold_triggers": [
            "prediction_or_docking_only",
            "single_unconfirmed_batch",
        ],
        "nogo_triggers": [
            "identity_not_established",
            "unstable_or_uncontrolled_composition",
        ],
        "agent": "ligand_chemistry",
    },
    SMIGateID.M2_POTENCY: {
        "name": "Biochemical Potency and Selectivity",
        "required_evidence": [
            "orthogonal_biochemical_potency",
            "declared_selectivity_panel",
            "inhibition_mode",
        ],
        "hold_triggers": [
            "single_assay_format",
            "docking_pose_only",
        ],
        "nogo_triggers": [
            "no_reproducible_activity",
            "selectivity_lost_on_safety_homolog",
        ],
        "agent": "pharmacology",
    },
    SMIGateID.M3_CELLULAR: {
        "name": "Cellular Target Engagement",
        "required_evidence": [
            "cellular_target_engagement",
            "inactive_analog_or_orthogonal_compound",
            "cell_health_control",
        ],
        "hold_triggers": [
            "biochemical_activity_only",
        ],
        "nogo_triggers": [
            "signal_tracks_nonspecific_cytotoxicity",
            "no_engagement_below_preregistered_cytotoxicity",
        ],
        "agent": "pharmacology",
    },
    SMIGateID.M4_EXPOSURE: {
        "name": "ADME and Exposure",
        "required_evidence": [
            "measured_solubility",
            "measured_permeability",
            "measured_metabolic_stability",
            "exposure_versus_cellular_potency",
        ],
        "hold_triggers": [
            "in_vitro_adme_only",
            "predicted_adme_only",
        ],
        "nogo_triggers": [
            "exposure_cannot_reach_preregistered_free_concentration",
        ],
        "agent": "adme_exposure",
    },
    SMIGateID.M5_SAFETY: {
        "name": "Safety and Therapeutic Window",
        "required_evidence": [
            "preregistered_safety_panel",
            "on_target_liability",
            "dose_tolerability",
        ],
        "hold_triggers": [
            "therapeutic_window_not_measured",
        ],
        "nogo_triggers": [
            "no_therapeutic_window",
            "liability_inseparable_from_mechanism",
        ],
        "agent": "safety_translation",
    },
}
