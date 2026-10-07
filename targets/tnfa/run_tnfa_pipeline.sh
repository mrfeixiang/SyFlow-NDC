#!/bin/bash
# ============================================================================
# TNF-α VHH Binder Design Pipeline — Anthropic × Adaptyv 2026
# ============================================================================
# Target: TNF-α (human P01375, PDB 1TNF; mouse P06804, PDB 2TNF)
# Objective: 20 VHH designs with binding + cross-species + pH selectivity
# Deadline: 2026-10-11 23:59 AoE
# ============================================================================

set -euo pipefail

# ---- Configuration ----
AIDD_ROOT="/home/syslab/Desktop/AIDD SYStem"
WORK_DIR="${AIDD_ROOT}/Virtual Biotech workflow/targets/tnfa"
FASTA_INPUT="${WORK_DIR}/vhh_candidates_20.fasta"
RESULTS_DIR="${WORK_DIR}/results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RUN_DIR="${RESULTS_DIR}/${TIMESTAMP}"

# Tool paths
BOLTZ2="${AIDD_ROOT}/boltz2"
RFANTIBODY="${AIDD_ROOT}/rfantibody"
NANOFLOW="${AIDD_ROOT}/nanobody-pipeline"
LIGANDMPNN="${AIDD_ROOT}/ligandMNPP"
ABMPNN="${AIDD_ROOT}/AbMPNN"
BOLTZGEN="${AIDD_ROOT}/BoltzGen"

# Target PDB
PDB_HUMAN="1TNF"
PDB_MOUSE="2TNF"

echo "============================================================"
echo "  TNF-α VHH Design Pipeline — ${TIMESTAMP}"
echo "============================================================"
echo "  Candidates: ${FASTA_INPUT}"
echo "  Output: ${RUN_DIR}"
echo "============================================================"

mkdir -p "${RUN_DIR}"/{step1_structures,step2_scoring,step3_crossspecies,step4_pH_analysis,step5_final}

# ============================================================================
# STEP 0: Download target PDB structures
# ============================================================================
echo "[Step 0] Downloading TNF-α structures..."

cd "${RUN_DIR}/step1_structures"

if [ ! -f "${PDB_HUMAN}.pdb" ]; then
    wget -q "https://files.rcsb.org/download/${PDB_HUMAN}.pdb" -O "${PDB_HUMAN}.pdb" 2>/dev/null || \
    echo "WARNING: Could not download ${PDB_HUMAN}.pdb — provide manually"
fi

if [ ! -f "${PDB_MOUSE}.pdb" ]; then
    wget -q "https://files.rcsb.org/download/${PDB_MOUSE}.pdb" -O "${PDB_MOUSE}.pdb" 2>/dev/null || \
    echo "WARNING: Could not download ${PDB_MOUSE}.pdb — provide manually"
fi

echo "  Structures ready."

# ============================================================================
# STEP 1: Boltz-2 Structure Prediction (VHH + TNF-α complex)
# ============================================================================
echo "[Step 1] Running Boltz-2 complex prediction..."

cd "${BOLTZ2}"

# Parse FASTA and run predictions for each candidate
python3 -c "
import os, sys
fasta = '${FASTA_INPUT}'
outdir = '${RUN_DIR}/step2_scoring'

seqs = {}
current_id = None
current_seq = ''

with open(fasta) as f:
    for line in f:
        line = line.strip()
        if line.startswith('>'):
            if current_id:
                seqs[current_id] = current_seq.replace(' ', '')
            current_id = line[1:].split('|')[0]
            current_seq = ''
        else:
            current_seq += line
    if current_id:
        seqs[current_id] = current_seq.replace(' ', '')

# Write individual FASTA files for each candidate
for seq_id, seq in seqs.items():
    out_fasta = os.path.join(outdir, f'{seq_id}.fasta')
    with open(out_fasta, 'w') as out:
        out.write(f'>{seq_id}\n{seq}\n')
    print(f'  Prepared: {seq_id} ({len(seq)} aa)')

print(f'\nTotal candidates: {len(seqs)}')
" || echo "WARNING: FASTA parsing encountered issues"

echo "  Individual FASTA files prepared in ${RUN_DIR}/step2_scoring/"

# Run Boltz-2 batch prediction (if available)
if [ -f "${BOLTZ2}/scripts/batch_affinity.py" ]; then
    echo "  Running Boltz-2 batch affinity prediction..."
    cd "${BOLTZ2}"
    python3 scripts/batch_affinity.py \
        --input_dir "${RUN_DIR}/step2_scoring" \
        --target_pdb "${RUN_DIR}/step1_structures/${PDB_HUMAN}.pdb" \
        --output_dir "${RUN_DIR}/step2_scoring/boltz2_results" \
        2>&1 | tee "${RUN_DIR}/step2_scoring/boltz2.log" || \
    echo "  NOTE: Boltz-2 batch run needs manual configuration — see log"
else
    echo "  WARNING: batch_affinity.py not found — run Boltz-2 predictions manually"
fi

# ============================================================================
# STEP 2: NanoFlow Pipeline Scoring
# ============================================================================
echo "[Step 2] Running NanoFlow pipeline scoring..."

cd "${NANOFLOW}"

if [ -f "pipeline.py" ]; then
    python3 pipeline.py \
        --input "${FASTA_INPUT}" \
        --target "${RUN_DIR}/step1_structures/${PDB_HUMAN}.pdb" \
        --output "${RUN_DIR}/step2_scoring/nanoflow_results" \
        --mode score \
        2>&1 | tee "${RUN_DIR}/step2_scoring/nanoflow.log" || \
    echo "  NOTE: NanoFlow needs manual configuration — see config.yaml"
else
    echo "  WARNING: NanoFlow pipeline.py not found at expected path"
fi

# ============================================================================
# STEP 3: Cross-Species Validation (Mouse TNF-α)
# ============================================================================
echo "[Step 3] Cross-species validation against mouse TNF-α..."

# Run same prediction pipeline against mouse TNF-α structure
if [ -f "${RUN_DIR}/step1_structures/${PDB_MOUSE}.pdb" ]; then
    echo "  Scoring against mouse TNF-α (PDB ${PDB_MOUSE})..."
    cd "${BOLTZ2}"

    if [ -f "scripts/batch_affinity.py" ]; then
        python3 scripts/batch_affinity.py \
            --input_dir "${RUN_DIR}/step2_scoring" \
            --target_pdb "${RUN_DIR}/step1_structures/${PDB_MOUSE}.pdb" \
            --output_dir "${RUN_DIR}/step3_crossspecies" \
            2>&1 | tee "${RUN_DIR}/step3_crossspecies/mouse_scoring.log" || \
        echo "  NOTE: Mouse scoring needs manual configuration"
    fi
else
    echo "  WARNING: Mouse TNF-α PDB not available"
fi

# ============================================================================
# STEP 4: pH Selectivity Analysis
# ============================================================================
echo "[Step 4] pH selectivity analysis..."

# Analyze His content and predicted pH switch strength
python3 -c "
import re

fasta = '${FASTA_INPUT}'
seqs = {}
current_id = None
current_seq = ''

with open(fasta) as f:
    for line in f:
        line = line.strip()
        if line.startswith('>'):
            if current_id:
                seqs[current_id] = current_seq.replace(' ', '')
            parts = line[1:].split('|')
            current_id = parts[0]
            current_seq = ''
        else:
            current_seq += line
    if current_id:
        seqs[current_id] = current_seq.replace(' ', '')

print('=' * 70)
print('pH SELECTIVITY ANALYSIS — His Count in CDR Regions')
print('=' * 70)
print(f'{\"Design\":<20} {\"Length\":<8} {\"Total His\":<10} {\"Group\":<12} {\"pH Score\":<10}')
print('-' * 70)

for sid, seq in sorted(seqs.items()):
    his_count = seq.count('H')
    # Estimate pH-switch strength
    if his_count >= 4:
        ph_score = 'STRONG'
    elif his_count >= 3:
        ph_score = 'MODERATE'
    elif his_count >= 2:
        ph_score = 'MILD'
    else:
        ph_score = 'NONE'

    # Determine group from name
    group = 'A' if 'Group=A' in sid or int(sid.split('-')[-1]) <= 5 else \
            'B' if int(sid.split('-')[-1]) <= 10 else \
            'C' if int(sid.split('-')[-1]) <= 15 else 'D'

    # Count His in framework vs CDR (approximate)
    fr_his = 0  # Framework has no His by design
    cdr_his = his_count - fr_his

    print(f'{sid:<20} {len(seq):<8} {his_count:<10} {group:<12} {ph_score:<10}')

print()
print('NOTE: SIpHAB analysis recommended for CDR-specific pH prediction')
print('URL: https://mm.nrc-cnrc.gc.ca/software/siphab/runner/')
" > "${RUN_DIR}/step4_pH_analysis/ph_analysis.txt" 2>&1

cat "${RUN_DIR}/step4_pH_analysis/ph_analysis.txt"

# ============================================================================
# STEP 5: Final Ranking and Submission Preparation
# ============================================================================
echo "[Step 5] Preparing final submission..."

# Copy candidates and create submission-ready file
cp "${FASTA_INPUT}" "${RUN_DIR}/step5_final/submission_candidates.fasta"

echo ""
echo "============================================================"
echo "  PIPELINE COMPLETE"
echo "============================================================"
echo "  Results: ${RUN_DIR}"
echo ""
echo "  Manual steps remaining:"
echo "  1. Review Boltz-2 scores in step2_scoring/"
echo "  2. Compare human vs mouse scores in step3_crossspecies/"
echo "  3. Run SIpHAB on Group C/D designs for pH validation"
echo "  4. Select final 20 candidates"
echo "  5. Submit to proteinbase.com by 2026-10-11"
echo "============================================================"
