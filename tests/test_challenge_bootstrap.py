"""Offline contract tests. Synthetic sequences/scores are never design evidence."""
import copy
import csv
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import yaml
from challenge_bootstrap.__main__ import checked, prepare, collect, export, digest, dump, register, score_job, run_jobs
from src.utils.run_manifest import RunManifest


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.config = self.root / 'config.yaml'
        self.run = self.root / 'run'
        self.seq = 'ACDEFGHIKL'
        (self.root / 'candidates.csv').write_text('name,sequence,molecule_class,source\nfixture,ACDEFGHIKL,nanobody,synthetic-test-only\n')
        (self.root / 'review.txt').write_text('Synthetic test fixture, not biological evidence.')
        self.ev = {'fixture': {'sequence_sha256': digest(self.seq), 'target_specific_experimental_feedback_used': False, 'zero_shot': {'status': 'pass', 'evidence_path': 'review.txt'}, 'novelty': {'status': 'pass', 'evidence_path': 'review.txt'}}}
        self.c = yaml.safe_load(Path('challenge_bootstrap/challenge3.yaml').read_text())
        self.c.update(challenge_id='synthetic_test', candidates_csv='candidates.csv', evidence_json='evidence.json')
        self.c['rules'] = dict(source_url='synthetic-test-only', reviewed_at='2026-10-07', allowed_molecule_classes=['nanobody', 'scfv'], min_chain_length=10, max_chain_length=250, max_designs=20, zero_shot_required=True, novelty_review_required=True)
        self.c['target'] = dict(id='synthetic', species='synthetic', construct='test trimer', assembly_source='test fixture', chains=[dict(id=x, sequence='ACDEFGHIKL', source='test') for x in 'ABC'])
        for cond in self.c['conditions'].values(): cond['enabled'] = False
        self.c['boltz']['expected_version'] = 'test'
        self.c['ranking'].update(min_score=0.4, max_seed_std=0.2)
        self.save()

    def save(self):
        self.config.write_text(yaml.safe_dump(self.c))
        dump(self.root / 'evidence.json', self.ev)

    def fake_results(self, omit=None, wrong_chains=False):
        prepare(self.config, self.run)
        jobs = json.loads((self.run / 'inputs/jobs.json').read_text())
        statuses = []
        aa3 = 'ALA CYS ASP GLU PHE GLY HIS ILE LYS LEU'.split()
        for job in jobs:
            if job['seed'] == omit: continue
            base = Path(job['out']) / ('boltz_results_' + job['stem']) / 'predictions' / job['stem']
            base.mkdir(parents=True)
            pairs = {str(i): {str(j): (0.99 if i < 3 and j < 3 else 0.6) for j in range(4)} for i in range(4)}
            dump(base / ('confidence_' + job['stem'] + '_model_0.json'), {'pair_chains_iptm': pairs})
            lines = []
            for chain in ('AB' if wrong_chains else 'ABCD'):
                for k, res in enumerate(aa3, 1):
                    lines.append(f'ATOM  {len(lines)+1:5d}  CA  {res} {chain}{k:4d}    {1.:8.3f}{2.:8.3f}{3.:8.3f}  1.00 90.00           C')
            (base / (job['stem'] + '_model_0.pdb')).write_text('\n'.join(lines) + '\n')
            statuses.append(dict(name=job['name'], context=job['context'], seed=job['seed'], returncode=0))
        dump(self.run / 'execution.json', dict(jobs=statuses, hooks={}, boltz_version='synthetic fixture'))
        for p in (self.run / 'work').rglob('*'):
            if p.is_file(): register(self.run, p)
        register(self.run, self.run / 'execution.json')
        collect(self.run)
        return json.loads((self.run / 'ranking.json').read_text())

    def test_runner_records_failed_command_and_explicit_seeds(self):
        prepare(self.config, self.run)
        with patch('challenge_bootstrap.__main__.importlib.metadata.version', return_value='test'), patch('challenge_bootstrap.__main__.subprocess.run') as execute:
            execute.return_value.returncode = 1
            run_jobs(self.run)
            self.assertEqual(execute.call_count, 3)
            for call, seed in zip(execute.call_args_list, [11, 22, 33]):
                argv = call.args[0]
                self.assertEqual(argv[argv.index('--seed') + 1], str(seed))
        collect(self.run)
        self.assertFalse(json.loads((self.run / 'ranking.json').read_text())[0]['eligible'])
        with self.assertRaisesRegex(ValueError, 'No eligible'): export(self.run)

    def test_missing_condition_hook_result_blocks(self):
        self.c['hooks'] = {'assembly': {'argv': ['python', 'existing_adapter.py']}}
        self.save()
        ranked = self.fake_results()
        self.assertFalse(ranked[0]['eligible'])
        self.assertIn('assembly: missing/failing evidence', ranked[0]['reasons'])

    def test_template_blocks(self):
        with self.assertRaisesRegex(ValueError, 'UNSET'): checked(Path('challenge_bootstrap/challenge3.yaml'))

    def test_multimer_pair_score_and_export(self):
        ranked = self.fake_results()
        self.assertTrue(ranked[0]['eligible'])
        self.assertAlmostEqual(ranked[0]['score'], 0.6)
        export(self.run)
        with (self.run / 'export/submission.csv').open() as f:
            row = next(csv.DictReader(f))
        self.assertEqual(row['molecule_class'], 'nanobody')
        self.assertEqual(RunManifest.load(self.run).verify_all(), [])
        with self.assertRaisesRegex(ValueError, 'Export exists'): export(self.run)

    def test_missing_seed_blocks_export(self):
        self.assertFalse(self.fake_results(omit=22)[0]['eligible'])
        with self.assertRaisesRegex(ValueError, 'No eligible'): export(self.run)
        self.assertFalse((self.run / 'export/submission.csv').exists())

    def test_multimer_loss_blocks(self):
        self.assertFalse(self.fake_results(wrong_chains=True)[0]['eligible'])

    def test_unknown_evidence_blocks(self):
        self.ev = {}; self.save()
        self.assertFalse(self.fake_results()[0]['eligible'])

    def test_sequence_evidence_mismatch_blocks(self):
        self.ev['fixture']['sequence_sha256'] = 'stale'; self.save()
        self.assertFalse(self.fake_results()[0]['eligible'])

    def test_experimental_feedback_blocks_zero_shot(self):
        self.ev['fixture']['target_specific_experimental_feedback_used'] = True; self.save()
        self.assertFalse(self.fake_results()[0]['eligible'])

    def test_tampering_blocks_export(self):
        self.fake_results()
        (self.run / 'inputs/evidence.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'Artifact drift'): export(self.run)

    def test_each_chain_length_and_class(self):
        f = self.root / 'candidates.csv'
        f.write_text('name,sequence,molecule_class,source\nfixture,ACDEFGHIKL:ACDEFGHIKL,scfv,test\n')
        checked(self.config)
        f.write_text('name,sequence,molecule_class,source\nfixture,ACDEFGHIKL:ACD,scfv,test\n')
        with self.assertRaisesRegex(ValueError, 'per-chain length'): checked(self.config)

    def test_ph_requires_adapter(self):
        self.c['conditions']['ph'] = dict(enabled=True, binding_condition=7.4, release_condition=6.0)
        self.save()
        with self.assertRaisesRegex(ValueError, 'requires an evidence adapter'): checked(self.config)

    def test_no_implicit_context_or_seed(self):
        self.c['boltz']['seeds'] = [11, 11]; self.save()
        with self.assertRaisesRegex(ValueError, 'unique integer seeds'): checked(self.config)


if __name__ == '__main__': unittest.main()
