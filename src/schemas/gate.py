"""Gate decision schema for the NDC Go/No-Go framework.

Six gates (G0-G5), each with required evidence, hold triggers, and no-go triggers.
Thresholds are set BEFORE each experiment from assay variability, indication,
and reference conjugate — not universal cutoffs.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class GateID(str, Enum):
    G0_TARGET = "G0"
    G1_VHH = "G1"
    G2_DELIVERY = "G2"
    G3_PRODUCT = "G3"
    G4_FUNCTION = "G4"
    G5_TRANSLATION = "G5"


class GateVerdict(str, Enum):
    GO = "go"
    HOLD = "hold"
    NO_GO = "no_go"


class GateThreshold(BaseModel):
    """A measurable threshold for a gate criterion.

    Set BEFORE the experiment, derived from assay variability,
    indication context, and reference conjugate performance.
    """
    parameter: str
    operator: str = Field(..., description=">=, <=, >, <, ==, range")
    value: str
    unit: Optional[str] = None
    rationale: str = Field(..., description="Why this threshold was chosen")
    reference_conjugate: Optional[str] = Field(None, description="Comparator used to set threshold")
    assay_cv_percent: Optional[float] = Field(None, description="Assay coefficient of variation")
    set_date: str = Field(..., description="Date threshold was frozen — before experiment")
    set_by: Optional[str] = None


class GateEvidence(BaseModel):
    """Evidence submitted for a specific gate criterion."""
    criterion: str
    claim_ids: list[str]
    threshold: Optional[GateThreshold] = None
    measured_value: Optional[str] = None
    meets_threshold: Optional[bool] = None
    evidence_type: str = Field(..., description="prediction, literature_evidence, syflow_wetlab, etc.")
    notes: Optional[str] = None


class GateDecision(BaseModel):
    """A complete gate assessment for one NDC candidate."""
    gate_id: GateID
    dossier_id: str
    target: str
    assessed_at: datetime = Field(default_factory=datetime.now)

    # Evidence
    required_evidence: list[str] = Field(
        ..., description="List of evidence categories required for this gate"
    )
    submitted_evidence: list[GateEvidence] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)

    # Decision
    verdict: GateVerdict
    rationale: str
    hold_reason: Optional[str] = None
    nogo_reason: Optional[str] = None
    next_experiment: Optional[str] = Field(
        None, description="The cheapest decisive next experiment"
    )

    # Audit
    reviewer_agent: str = "scientific_reviewer"
    reviewer_notes: Optional[str] = None
    human_approver: Optional[str] = None
    approval_date: Optional[str] = None
    run_id: Optional[str] = None

    # Conflicts and gaps
    conflicting_findings: list[str] = Field(default_factory=list)
    comparator_adequacy: Optional[str] = None


# Gate definitions with required evidence and triggers
GATE_DEFINITIONS = {
    GateID.G0_TARGET: {
        "name": "Target and Patient Selection",
        "required_evidence": [
            "defined_patient_subset",
            "membrane_protein_confirmation",
            "tumor_protein_expression",
            "normal_tissue_assessment",
        ],
        "hold_triggers": [
            "tumor_protein_data_missing",
            "normal_tissue_protein_data_missing",
        ],
        "nogo_triggers": [
            "therapeutic_window_implausible",
            "no_membrane_accessibility",
        ],
        "agent": "target_patient",
    },
    GateID.G1_VHH: {
        "name": "VHH Binding and Selectivity",
        "required_evidence": [
            "live_cell_binding_positive_cells",
            "live_cell_binding_negative_cells",
            "counter_binding_specificity",
            "developability_assessment",
        ],
        "hold_triggers": [
            "recombinant_binding_only",
            "developability_incomplete",
        ],
        "nogo_triggers": [
            "selectivity_lost_on_wt_cells",
            "no_reproducible_binding",
        ],
        "agent": "nanobody_epitope",
    },
    GateID.G2_DELIVERY: {
        "name": "Internalization and Trafficking",
        "required_evidence": [
            "quantified_internalization",
            "trafficking_compartment",
            "antigen_density_dependence",
            "uptake_time_course",
        ],
        "hold_triggers": [
            "binding_established_but_uptake_unknown",
        ],
        "nogo_triggers": [
            "no_internalization",
            "wrong_trafficking_compartment",
        ],
        "agent": "delivery",
    },
    GateID.G3_PRODUCT: {
        "name": "Conjugate Identity and Stability",
        "required_evidence": [
            "site_specific_conjugation_confirmed",
            "measured_dar",
            "intact_mass",
            "free_payload_below_threshold",
            "aggregation_below_threshold",
            "serum_stability",
            "lot_to_lot_identity",
        ],
        "hold_triggers": [
            "single_batch_only",
            "stability_data_incomplete",
        ],
        "nogo_triggers": [
            "unstable_product",
            "poorly_defined_product",
            "high_free_payload",
        ],
        "agent": "conjugation_payload",
    },
    GateID.G4_FUNCTION: {
        "name": "Antigen-Dependent Killing",
        "required_evidence": [
            "target_positive_cytotoxicity",
            "unconjugated_vhh_control",
            "nonbinding_ndc_control",
            "free_payload_control",
            "target_negative_control",
            "reference_adc_comparison",
        ],
        "hold_triggers": [
            "reference_adc_unavailable",
            "single_cell_line_only",
        ],
        "nogo_triggers": [
            "killing_tracks_free_payload",
            "killing_in_target_negative_cells",
            "no_advantage_over_free_payload",
        ],
        "agent": "conjugation_payload",
    },
    GateID.G5_TRANSLATION: {
        "name": "Exposure and Therapeutic Window",
        "required_evidence": [
            "tumor_exposure",
            "organ_exposure_especially_kidney",
            "free_payload_exposure",
            "species_relevance",
            "pk_pd_relationship",
            "dose_tolerability",
        ],
        "hold_triggers": [
            "exposure_window_not_yet_demonstrated",
        ],
        "nogo_triggers": [
            "persistent_exposure_linked_liability",
            "no_therapeutic_window",
            "unacceptable_kidney_toxicity",
        ],
        "agent": "translation_safety",
    },
}
