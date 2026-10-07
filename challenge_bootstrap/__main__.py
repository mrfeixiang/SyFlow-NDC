"""Thin SyFlow bridge: check -> prepare -> run -> collect -> export.

No design engine and no remote submission. Existing design engines supply CSV.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import re
import statistics
import subprocess
import sys
from types import SimpleNamespace
import yaml

from evaluate_egfr_vhh import select_diverse_top20, write_submission_csv
from src.utils.run_manifest import RunManifest

AA = set('ACDEFGHIKLMNPQRSTVWY')
CLASSES = {'single_chain': 1, 'nanobody': 1, 'scfv': 2, 'fab_kappa': 2, 'fab_lambda': 2}
ROOT = Path(__file__).resolve().parents[1]


def digest(s):
    return hashlib.sha256(s.encode()).hexdigest()


def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')


def read(path):
    return json.loads(path.read_text())


def need(ok, message):
    if not ok:
        raise ValueError(message)


def register(run, path):
    RunManifest.load(run).register(str(path.relative_to(run)), produced_by='challenge_bootstrap')


def verified(run):
    need((run / 'MANIFEST.json').exists(), 'Missing MANIFEST.json')
    issues = RunManifest.load(run).verify_all()
    need(not issues, f'Artifact drift: {issues}')
    return read(run / 'inputs/config.json'), read(run / 'inputs/candidates.json')


def contexts(c):
    return [c['target']] + (c['orthologs'] if c['conditions']['ortholog']['enabled'] else []) + (c['off_targets'] if c['conditions']['off_target']['enabled'] else [])


def checked(config):
    c = yaml.safe_load(config.read_text())
    r = c['rules']
    for field in ('source_url', 'reviewed_at', 'allowed_molecule_classes', 'min_chain_length', 'max_chain_length', 'max_designs'):
        need(r.get(field) is not None, f'rules.{field} is UNSET')
    for field in ('zero_shot_required', 'novelty_review_required'):
        need(type(r.get(field)) is bool, f'rules.{field} is UNSET')
    need(bool(r['allowed_molecule_classes']) and set(r['allowed_molecule_classes']) <= CLASSES.keys(), 'Unsupported molecule class')
    need(0 < r['min_chain_length'] <= r['max_chain_length'] and r['max_designs'] > 0, 'Invalid length/count rules')
    for name in ('ortholog', 'ph', 'off_target'):
        need(type(c['conditions'][name]['enabled']) is bool, f'conditions.{name}.enabled is UNSET')
    for name, key in [('ortholog', 'orthologs'), ('off_target', 'off_targets')]:
        need(not c['conditions'][name]['enabled'] or bool(c[key]), f'{key} required')
    if c['conditions']['ph']['enabled']:
        need(all(c['conditions']['ph'].get(k) is not None for k in ('binding_condition', 'release_condition')), 'pH conditions are UNSET')
    for name in ('ph', 'off_target'):
        need(not c['conditions'][name]['enabled'] or name in c['hooks'], f'{name} requires an evidence adapter')
    ids = []
    for t in contexts(c):
        for key in ('id', 'species', 'construct', 'assembly_source', 'chains'):
            need(bool(t.get(key)), f'target context {key} is UNSET')
        need(re.fullmatch(r'[A-Za-z0-9_-]+', t['id']), 'Unsafe context ID')
        ids.append(t['id'])
        chain_ids = []
        for ch in t['chains']:
            need(re.fullmatch(r'[A-Za-z0-9]', ch['id']), 'Use unique single-character PDB chain IDs')
            need(ch.get('source') and ch.get('sequence') and set(ch['sequence']) <= AA, 'Invalid target sequence/source')
            chain_ids.append(ch['id'])
        need(len(chain_ids) == len(set(chain_ids)), 'Duplicate target chain ID')
    need(len(ids) == len(set(ids)), 'Duplicate context ID')
    b = c['boltz']
    need(b.get('expected_version'), 'boltz.expected_version is UNSET')
    need(len(b['seeds']) >= 2 and len(set(b['seeds'])) == len(b['seeds']) and all(type(s) is int and s >= 0 for s in b['seeds']), 'At least two unique integer seeds required')
    need(c['ranking']['metric'] == 'min_context_mean_binder_target_iptm', 'Unsupported ranking metric')
    for key in ('min_score', 'max_seed_std', 'diversity_identity'):
        v = c['ranking'].get(key)
        need(type(v) in (int, float) and math.isfinite(v) and 0 <= v <= 1, f'ranking.{key} is UNSET or invalid')
    for name, hook in c['hooks'].items():
        need(re.fullmatch(r'[a-z_]+', name), 'Unsafe hook name')
        need(isinstance(hook.get('argv'), list) and hook['argv'] and all(isinstance(x, str) for x in hook['argv']), 'Hook argv required')
    for key in ('candidates_csv', 'evidence_json'):
        need(c.get(key), f'{key} is UNSET')
        c[key] = str((config.parent / c[key]).resolve())
        need(Path(c[key]).is_file(), f'Missing {key}')
    with open(c['candidates_csv'], newline='') as f:
        rows = list(csv.DictReader(f))
    need(rows, 'No candidates')
    names, sequences = set(), set()
    for row in rows:
        need(set(('name', 'sequence', 'molecule_class', 'source')) <= row.keys(), 'Missing CSV columns')
        name, seq, cls = row['name'], row['sequence'], row['molecule_class']
        need(re.fullmatch(r'[A-Za-z0-9_-]+', name) and name not in names, 'Invalid/duplicate candidate ID')
        need(cls in r['allowed_molecule_classes'] and cls in CLASSES, f'{name}: molecule class rejected')
        chains = seq.split(':')
        need(len(chains) == CLASSES[cls], f'{name}: chain count does not match class')
        need(all(set(s) <= AA and r['min_chain_length'] <= len(s) <= r['max_chain_length'] for s in chains), f'{name}: invalid sequence/per-chain length')
        need(seq not in sequences and row['source'].strip(), f'{name}: duplicate sequence or missing source')
        names.add(name); sequences.add(seq)
        row['sequence_sha256'] = digest(seq)
    evidence = read(Path(c['evidence_json']))
    return c, rows, evidence


def prepare(config, run):
    c, rows, evidence = checked(config)
    need(not run.exists(), 'Run directory exists; use a fresh run directory')
    RunManifest.create(run)
    # Snapshot local evidence files; references cannot silently change after preparation.
    for name, ev in evidence.items():
        for gate in ('zero_shot', 'novelty'):
            record = ev.get(gate, {})
            if record.get('evidence_path'):
                src = (config.parent / record['evidence_path']).resolve()
                need(src.is_file(), f'Missing evidence: {src}')
                dest = run / 'inputs/evidence' / (digest(name + gate) + src.suffix)
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(src.read_bytes())
                record['evidence_path'] = str(dest.relative_to(run))
    dump(run / 'inputs/config.json', c)
    dump(run / 'inputs/candidates.json', rows)
    dump(run / 'inputs/evidence.json', evidence)
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    dirty = subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True)
    source_hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__), ROOT / 'evaluate_egfr_vhh.py', ROOT / 'src/utils/run_manifest.py']}
    dump(run / 'inputs/provenance.json', {'git_commit': commit, 'git_dirty': bool(dirty), 'source_sha256': source_hashes, 'python': sys.version, 'evidence_type': 'prediction'})
    jobs = []
    for row in rows:
        for t in contexts(c):
            used = {ch['id'] for ch in t['chains']}
            available = [x for x in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789' if x not in used]
            binder = row['sequence'].split(':')
            need(len(available) >= len(binder), 'No free chain IDs')
            bid = available[:len(binder)]
            proteins = [{'protein': {'id': ch['id'], 'sequence': ch['sequence']}} for ch in t['chains']]
            proteins += [{'protein': {'id': ch, 'sequence': seq}} for ch, seq in zip(bid, binder)]
            stem = row['name'] + '__' + t['id']
            inp = run / 'inputs/boltz' / (stem + '.yaml')
            inp.parent.mkdir(parents=True, exist_ok=True)
            inp.write_text(yaml.safe_dump({'version': 1, 'sequences': proteins}, sort_keys=False))
            for seed in c['boltz']['seeds']:
                out = run / 'work/boltz' / stem / str(seed)
                argv = [c['boltz']['executable'], 'predict', str(inp), '--out_dir', str(out), '--seed', str(seed), '--diffusion_samples', '1', '--recycling_steps', str(c['boltz']['recycling_steps']), '--output_format', 'pdb', '--write_full_pae']
                if c['boltz']['use_msa_server']:
                    argv.append('--use_msa_server')
                jobs.append({'name': row['name'], 'context': t['id'], 'seed': seed, 'argv': argv, 'out': str(out), 'stem': stem, 'target_chains': len(t['chains']), 'chains': {p['protein']['id']: p['protein']['sequence'] for p in proteins}})
    dump(run / 'inputs/jobs.json', jobs)
    for p in sorted((run / 'inputs').rglob('*')):
        if p.is_file(): register(run, p)
    print(f'Prepared {len(jobs)} jobs; no compute launched: {run}')


def run_jobs(run):
    c, rows = verified(run)
    need(not (run / 'execution.json').exists(), 'Execution already attempted; prepare a fresh run')
    actual = importlib.metadata.version('boltz')
    need(actual == c['boltz']['expected_version'], f'Boltz version {actual} != configured version')
    jobs = read(run / 'inputs/jobs.json')
    status = {'boltz_version': actual, 'jobs': [], 'hooks': {}}
    dump(run / 'execution.json', status)
    try:
        for job in jobs:
            out = Path(job['out']); out.mkdir(parents=True, exist_ok=True)
            with (out / 'execution.log').open('w') as log:
                p = subprocess.run(job['argv'], stdout=log, stderr=subprocess.STDOUT)
            status['jobs'].append({'name': job['name'], 'context': job['context'], 'seed': job['seed'], 'returncode': p.returncode})
            dump(run / 'execution.json', status)
        for name, hook in c['hooks'].items():
            out = run / 'work/hooks' / (name + '.json'); out.parent.mkdir(parents=True, exist_ok=True)
            argv = [x.format(config=str(run / 'inputs/config.json'), candidates=str(run / 'inputs/candidates.json'), output=str(out)) for x in hook['argv']]
            with out.with_suffix('.log').open('w') as log:
                p = subprocess.run(argv, stdout=log, stderr=subprocess.STDOUT)
            status['hooks'][name] = {'argv': argv, 'returncode': p.returncode}
    finally:
        dump(run / 'execution.json', status)
        for p in sorted((run / 'work').rglob('*')):
            if p.is_file(): register(run, p)
        register(run, run / 'execution.json')


def score_job(job):
    base = Path(job['out']) / ('boltz_results_' + job['stem']) / 'predictions' / job['stem']
    d = read(base / ('confidence_' + job['stem'] + '_model_0.json'))
    pdb = base / (job['stem'] + '_model_0.pdb')
    # Validate chain identities and lengths, not just number of chains.
    aa3 = dict(zip('ALA CYS ASP GLU PHE GLY HIS ILE LYS LEU MET ASN PRO GLN ARG SER THR VAL TRP TYR'.split(), 'ACDEFGHIKLMNPQRSTVWY'))
    observed = {}
    for line in pdb.read_text().splitlines():
        if line.startswith('ATOM') and line[12:16].strip() == 'CA' and line[16] in (' ', 'A'):
            observed.setdefault(line[21], {})[line[22:27]] = aa3.get(line[17:20], 'X')
    observed = {ch: ''.join(res.values()) for ch, res in observed.items()}
    need(observed == job['chains'], 'Predicted chain sequences/assembly differ from planned input')
    nt = job['target_chains']; nc = len(job['chains'])
    # Pair-specific score avoids antigen-antigen interfaces inflating global iPTM.
    pairs = [float(d['pair_chains_iptm'][str(i)][str(j)]) for i in range(nt) for j in range(nt, nc)]
    pairs += [float(d['pair_chains_iptm'][str(j)][str(i)]) for i in range(nt) for j in range(nt, nc)]
    need(pairs and all(math.isfinite(x) and 0 <= x <= 1 for x in pairs), 'Invalid pair iPTM')
    return statistics.mean(pairs)


def gate_evidence(row, evidence, gate):
    e = evidence.get(row['name'], {})
    g = e.get(gate, {})
    return e.get('sequence_sha256') == row['sequence_sha256'] and g.get('status') == 'pass' and bool(g.get('evidence_path'))


def collect(run):
    c, rows = verified(run)
    evidence = read(run / 'inputs/evidence.json')
    execution = read(run / 'execution.json')
    statuses = {(j['name'], j['context'], j['seed']): j['returncode'] for j in execution['jobs']}
    jobs = read(run / 'inputs/jobs.json')
    metrics, failures = {}, {}
    for job in jobs:
        key = (job['name'], job['context'])
        try:
            need(statuses.get((job['name'], job['context'], job['seed'])) == 0, 'Missing/failed execution')
            value = score_job(job)
            metrics.setdefault(key, []).append(value)
        except (ValueError, OSError, KeyError, TypeError) as e:
            failures.setdefault(job['name'], []).append(f"{job['context']}/seed{job['seed']}: {e}")
    results = []
    positive = [c['target']['id']] + ([t['id'] for t in c['orthologs']] if c['conditions']['ortholog']['enabled'] else [])
    for row in rows:
        reasons = failures.get(row['name'], []).copy()
        for gate, rule in [('zero_shot', 'zero_shot_required'), ('novelty', 'novelty_review_required')]:
            if c['rules'][rule] and not gate_evidence(row, evidence, gate): reasons.append(gate + ': unknown/fail')
        if c['rules']['zero_shot_required'] and evidence.get(row['name'], {}).get('target_specific_experimental_feedback_used') is not False:
            reasons.append('zero_shot: experimental feedback not explicitly excluded')
        summary = {}
        for t in contexts(c):
            vals = metrics.get((row['name'], t['id']), [])
            if len(vals) != len(c['boltz']['seeds']): reasons.append(t['id'] + ': incomplete seeds')
            summary[t['id']] = {'n': len(vals), 'mean': statistics.mean(vals) if vals else None, 'std': statistics.pstdev(vals) if vals else None}
        for name in c['hooks']:
            try:
                need(execution['hooks'].get(name, {}).get('returncode') == 0, 'hook failed')
                h = read(run / 'work/hooks' / (name + '.json'))[row['name']]
                need(h.get('sequence_sha256') == row['sequence_sha256'] and h.get('status') == 'pass' and h.get('evidence'), 'hook unknown/fail')
            except (OSError, KeyError, ValueError, TypeError): reasons.append(name + ': missing/failing evidence')
        scores = [summary[t]['mean'] for t in positive]
        score = min(scores) if all(s is not None for s in scores) else None
        if score is None or score < c['ranking']['min_score']: reasons.append('score below configured threshold or missing')
        if any(s['std'] is not None and s['std'] > c['ranking']['max_seed_std'] for s in summary.values()): reasons.append('seed variability above configured threshold')
        results.append({**row, 'score': score, 'eligible': not reasons, 'reasons': reasons, 'contexts': summary})
    results.sort(key=lambda x: (not x['eligible'], -(x['score'] if x['score'] is not None else -1), x['name']))
    dump(run / 'ranking.json', results)
    with (run / 'ranking.csv').open('w', newline='') as f:
        w = csv.writer(f); w.writerow(['rank', 'name', 'sequence_sha256', 'score', 'eligible', 'reasons', 'contexts'])
        for i, r in enumerate(results, 1): w.writerow([i, r['name'], r['sequence_sha256'], r['score'], r['eligible'], '; '.join(r['reasons']), json.dumps(r['contexts'])])
    register(run, run / 'ranking.json'); register(run, run / 'ranking.csv')
    print(f"Ranked {len(rows)} candidates; eligible: {sum(r['eligible'] for r in results)}")


def export(run):
    c, rows = verified(run)
    ranked = read(run / 'ranking.json')
    candidates = [SimpleNamespace(**r, composite_score=r['score']) for r in ranked if r['eligible']]
    selected = select_diverse_top20(candidates, c['rules']['max_designs'], c['ranking']['diversity_identity'])
    need(selected, 'No eligible candidates; submission CSV withheld')
    out = run / 'export'
    need(not out.exists(), 'Export exists; do not overwrite a reviewed bundle')
    out.mkdir()
    write_submission_csv(selected, out / 'submission.csv')
    dump(out / 'metadata.json', {'challenge_id': c['challenge_id'], 'rules': c['rules'], 'target': c['target'], 'orthologs': c['orthologs'], 'off_targets': c['off_targets'], 'conditions': c['conditions'], 'ranking_policy': c['ranking'], 'evidence_type': 'prediction', 'researcher_review': 'required_before_upload', 'candidate_evidence': read(run / 'inputs/evidence.json'), 'selected': [vars(x) for x in selected], 'provenance': read(run / 'inputs/provenance.json')})
    register(run, out / 'submission.csv'); register(run, out / 'metadata.json')
    print('Exported for researcher review; nothing uploaded to Proteinbase.')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage', choices=['check', 'prepare', 'run', 'collect', 'export'])
    p.add_argument('--config', type=Path, default=Path('challenge_bootstrap/challenge3.yaml'))
    p.add_argument('--run-dir', type=Path)
    a = p.parse_args()
    try:
        if a.stage == 'check':
            c, rows, _ = checked(a.config.resolve()); print(f"Config OK: {len(rows)} candidates")
        else:
            need(a.run_dir is not None, '--run-dir is required')
            run = a.run_dir.resolve()
            if a.stage == 'prepare': prepare(a.config.resolve(), run)
            else: {'run': run_jobs, 'collect': collect, 'export': export}[a.stage](run)
    except (ValueError, OSError, KeyError, TypeError, importlib.metadata.PackageNotFoundError) as e:
        p.exit(2, f'BLOCKED: {e}\n')


if __name__ == '__main__': main()
