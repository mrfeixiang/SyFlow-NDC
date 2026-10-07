#!/bin/bash
set -euo pipefail
INPUT_DIR="boltz_inputs"
OUTPUT_DIR="boltz_outputs"
RESULTS_FILE="boltz_all_scores.tsv"

echo -e "Design\tConfScore\tpTM\tiPTM\tpLDDT\tiPLDDT\tChainA_pTM\tChainB_pTM" > "${RESULTS_FILE}"

for yaml_file in ${INPUT_DIR}/SyF-TNFa-*.yaml; do
    name=$(basename "${yaml_file}" .yaml)
    out_dir="${OUTPUT_DIR}/${name}"
    
    if [ -f "${out_dir}/boltz_results_${name}/predictions/${name}/confidence_${name}_model_0.json" ]; then
        echo "[SKIP] ${name} — already predicted"
    else
        echo "[RUN] ${name}..."
        boltz predict "${yaml_file}" \
            --out_dir "${out_dir}" \
            --diffusion_samples 1 \
            --recycling_steps 3 \
            --output_format pdb \
            --write_full_pae \
            --use_msa_server \
            2>&1 | grep -E "^(Predicting|Number|COMPLETE|Failed)" || true
    fi
    
    # Extract scores
    conf_file="${out_dir}/boltz_results_${name}/predictions/${name}/confidence_${name}_model_0.json"
    if [ -f "${conf_file}" ]; then
        python3 -c "
import json
with open('${conf_file}') as f:
    d = json.load(f)
print(f'${name}\t{d[\"confidence_score\"]:.4f}\t{d[\"ptm\"]:.4f}\t{d[\"iptm\"]:.4f}\t{d[\"complex_plddt\"]:.4f}\t{d.get(\"complex_iplddt\",0):.4f}\t{d[\"chains_ptm\"][\"0\"]:.4f}\t{d[\"chains_ptm\"][\"1\"]:.4f}')
" >> "${RESULTS_FILE}"
    fi
done

echo ""
echo "=== ALL RESULTS ==="
column -t -s $'\t' "${RESULTS_FILE}"
