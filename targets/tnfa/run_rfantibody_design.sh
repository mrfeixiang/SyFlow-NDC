#!/bin/bash
# ============================================================================
# RFAntibody De Novo VHH Design for TNF-α
# Uses: RFdiffusion → ProteinMPNN → RF2 pipeline
# ============================================================================
set -euo pipefail

AIDD_ROOT="/home/syslab/Desktop/AIDD SYStem"
RFANTIBODY_DIR="${AIDD_ROOT}/rfantibody"
WORK_DIR="${AIDD_ROOT}/Virtual Biotech workflow/targets/tnfa"
OUTPUT_DIR="${WORK_DIR}/rfantibody_results/$(date +%Y%m%d_%H%M%S)"

# VHH framework (cAbBCII10-derived, PDB 3DWT)
FRAMEWORK_PDB="${RFANTIBODY_DIR}/scripts/examples/example_inputs/h-NbBCII10.pdb"

# TNF-α target epitope hotspots (from PDB 5M2I/5M2J VHH-TNF structures)
# Residues at protomer interface groove: 20-25, 65-67, 70-74, 88-92, 135-141
HOTSPOTS="T20,T23,T25,T65,T67,T70,T72,T74,T88,T89,T91,T92,T97,T107,T135,T138,T141"

# CDR length specifications for VHH
DESIGN_LOOPS="H1:7,H2:6,H3:5-13"

echo "============================================================"
echo "  RFAntibody TNF-α VHH Design Pipeline"
echo "============================================================"

mkdir -p "${OUTPUT_DIR}"

# ---- Step 0: Download target PDB ----
echo "[Step 0] Preparing target structure..."
cd "${OUTPUT_DIR}"
if [ ! -f "1TNF.pdb" ]; then
    wget -q "https://files.rcsb.org/download/1TNF.pdb" -O "1TNF.pdb" 2>/dev/null || \
    echo "  Download 1TNF.pdb manually from RCSB"
fi

# Convert to HLT format if script available
if [ -f "${RFANTIBODY_DIR}/scripts/util/chothia_to_HLT.py" ]; then
    cd "${RFANTIBODY_DIR}"
    source .venv/bin/activate 2>/dev/null || true
    python scripts/util/chothia_to_HLT.py \
        -inpdb "${OUTPUT_DIR}/1TNF.pdb" \
        -outpdb "${OUTPUT_DIR}/1TNF_HLT.pdb" 2>/dev/null || \
    echo "  HLT conversion needs manual setup"
fi

# ---- Step 1: RFdiffusion backbone design ----
echo "[Step 1] RFdiffusion backbone generation (500 designs)..."
cd "${RFANTIBODY_DIR}"
source .venv/bin/activate 2>/dev/null || true

uv run rfdiffusion \
    --target "${OUTPUT_DIR}/1TNF_HLT.pdb" \
    --framework "${FRAMEWORK_PDB}" \
    --output-quiver "${OUTPUT_DIR}/1_rfdiffusion.qv" \
    --num-designs 500 \
    --design-loops "${DESIGN_LOOPS}" \
    --hotspots "${HOTSPOTS}" \
    --deterministic \
    2>&1 | tee "${OUTPUT_DIR}/step1_rfdiffusion.log" || \
echo "  NOTE: RFdiffusion may need GPU and model weights — check log"

# ---- Step 2: ProteinMPNN sequence design ----
echo "[Step 2] ProteinMPNN sequence design (4 seqs per backbone)..."

uv run proteinmpnn \
    --input-quiver "${OUTPUT_DIR}/1_rfdiffusion.qv" \
    --output-quiver "${OUTPUT_DIR}/2_proteinmpnn.qv" \
    --seqs-per-struct 4 \
    --temperature 0.2 \
    --deterministic \
    2>&1 | tee "${OUTPUT_DIR}/step2_proteinmpnn.log" || \
echo "  NOTE: ProteinMPNN step needs input from Step 1"

# ---- Step 3: RF2 structure prediction & validation ----
echo "[Step 3] RF2 structure prediction & filtering..."

uv run rf2 \
    --input-quiver "${OUTPUT_DIR}/2_proteinmpnn.qv" \
    --output-quiver "${OUTPUT_DIR}/3_rf2.qv" \
    --num-recycles 10 \
    --hotspot-show-prop 0.1 \
    2>&1 | tee "${OUTPUT_DIR}/step3_rf2.log" || \
echo "  NOTE: RF2 step needs input from Step 2"

# ---- Step 4: Extract results ----
echo "[Step 4] Extracting top designs..."

if [ -f "${OUTPUT_DIR}/3_rf2.qv" ]; then
    uv run qvextract "${OUTPUT_DIR}/3_rf2.qv" -o "${OUTPUT_DIR}/final_pdbs/" || true
    uv run qvscorefile "${OUTPUT_DIR}/3_rf2.qv" > "${OUTPUT_DIR}/final_scores.tsv" || true
    uv run qvls "${OUTPUT_DIR}/3_rf2.qv" > "${OUTPUT_DIR}/design_list.txt" || true
fi

echo ""
echo "============================================================"
echo "  RFAntibody pipeline complete"
echo "  Results: ${OUTPUT_DIR}"
echo "  Next: Select top 20, apply pH-switch His mutations"
echo "============================================================"
