"""Offline regression coverage; no model calls or biological validation."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.agents.registry import AGENT_REGISTRY
from src.cli import TARGETS, build_validation_plan, load_target_dossier
from src.schemas.evidence import Claim, EvidenceItem, EvidenceType, VerificationStatus
from src.schemas.gate import GATE_DEFINITIONS
from src.utils.claims import validate_claims
from src.utils.paths import runs_directory, workspace_root
from src.utils.provenance import Provenance
from src.utils.run_manifest import RunManifest
from src.utils.session_audit import SessionAudit
from src.utils.trace_logger import TraceLogger


class RegressionTests(unittest.TestCase):
    def test_gate_policy_matches_pre_restructure(self):
        baseline = json.loads((Path(__file__).parent / 'fixtures/gates_pre_restructure.json').read_text())
        self.assertEqual({k.value: v for k, v in GATE_DEFINITIONS.items()}, baseline)
        self.assertEqual(len(AGENT_REGISTRY), 7)
        for gate in GATE_DEFINITIONS.values():
            self.assertIn(gate['agent'], AGENT_REGISTRY)
        self.assertEqual(len({g['agent'] for g in GATE_DEFINITIONS.values()}), 5)

    def test_packaged_prompts_are_present(self):
        for config in AGENT_REGISTRY.values():
            self.assertGreater(len(config['prompt']), 200)

    def test_target_registry_and_plan_branches(self):
        self.assertEqual(set(TARGETS), {'pnpla3', 'rhoa', 'tak1', 'egfrviii'})
        for surface in (True, False):
            for conjugate in (True, False):
                dossier = {'target_profile': {'is_surface_protein': surface}}
                if conjugate:
                    dossier['conjugate'] = {}
                plan = build_validation_plan('test', dossier)
                agents = {s['agent'] for s in plan['steps']}
                self.assertEqual('delivery' in agents, surface)
                self.assertEqual('conjugation_payload' in agents, conjugate)
                self.assertEqual(plan['valid_order'][-1], 's6_review')

    def test_missing_and_invalid_dossiers_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {'SYFLOW_PROJECT_ROOT': tmp}):
                with self.assertRaises(ValueError):
                    load_target_dossier('egfrviii')
            path = Path(tmp) / 'bad.yaml'
            path.write_text('[]')
            with self.assertRaises(ValueError):
                load_target_dossier('egfrviii', str(path))

    def test_shared_workspace_overrides(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {'SYFLOW_PROJECT_ROOT': tmp, 'SYFLOW_RUNS_DIR': tmp + '/custom'}):
                self.assertEqual(workspace_root(), Path(tmp).resolve())
                self.assertEqual(runs_directory(), Path(tmp, 'custom').resolve())

    def test_evidence_categories_and_provenance(self):
        self.assertEqual({e.value for e in EvidenceType}, {
            'prediction', 'literature_evidence', 'retrospective_analysis',
            'syflow_wetlab', 'independent_replication'})
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'result.txt').write_text('measured result')
            manifest = RunManifest.create(root)
            manifest.register('result.txt', produced_by='delivery')
            claim = Claim(id='C1', text='test only', agent='delivery', confidence='weak', evidence=[
                EvidenceItem(kind='artifact', evidence_type='prediction', path='result.txt'),
                EvidenceItem(kind='citation', evidence_type='literature_evidence', doi='10.0000/test'),
                EvidenceItem(kind='assay_result', evidence_type='syflow_wetlab', path='missing.csv')])
            report = validate_claims([claim], manifest, TraceLogger(root))
            self.assertEqual([e.verification_status for e in claim.evidence], [
                VerificationStatus.VERIFIED, VerificationStatus.EXTERNAL, VerificationStatus.UNRESOLVED])
            self.assertEqual(report['claims_missing_batch_provenance'], 1)
            claim.evidence[-1].eln_id = 'ELN-test'
            self.assertTrue(claim.has_batch_provenance())
            self.assertEqual(manifest.verify_all(), [])
            (root / 'result.txt').write_text('tampered')
            self.assertEqual(manifest.verify_all()[0]['issue'], 'hash_mismatch')
            (root / 'result.txt').unlink()
            self.assertEqual(manifest.verify_all()[0]['issue'], 'missing')

    def test_trace_attribution_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audit = SessionAudit(root, 'test')
            audit.on_agent_start('delivery', 'offline fixture')
            output = root / 'result.txt'
            output.write_text('fixture')
            audit.on_file_write('delivery', str(output))
            audit.on_agent_stop('delivery')
            audit.finish_run()
            prov = Provenance(root)
            activity = prov.reconstruct()['delivery']
            self.assertEqual(activity.status, 'completed')
            self.assertEqual(activity.files_written, ['result.txt'])
            self.assertEqual(activity.artifacts_registered, ['result.txt'])

    def test_cli_initializes_only_from_unrelated_cwd(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dossier = root / 'dossier.yaml'
            dossier.write_text('target_profile:\n  is_surface_protein: true\n')
            env = {**os.environ, 'SYFLOW_RUNS_DIR': str(root / 'runs')}
            for command in ('validate', 'gate'):
                args = [sys.executable, '-m', 'src', command, '--target', 'egfrviii', '--dossier', str(dossier)]
                if command == 'gate':
                    args += ['--gate', 'G4']
                result = subprocess.run(args, cwd=root, env=env, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            for run in (root / 'runs').iterdir():
                audit = json.loads((run / 'audit.json').read_text())
                self.assertEqual(audit['status'], 'initialized')
                plan = audit['final_report']['plan_reconciliation']
                self.assertGreater(plan['total_steps'], 0)
                self.assertEqual(plan['completed'], 0)
                self.assertEqual(plan['pending'], plan['total_steps'])
                manifest = RunManifest.load(run)
                self.assertEqual(manifest.verify_all(), [])
                self.assertTrue(all(a.produced_by == 'cli_initializer' for a in manifest.artifacts.values()))
                trace = TraceLogger.load(run)
                self.assertFalse(any(e.event_type in ('agent_start', 'agent_stop', 'tool_start', 'gate_decision') for e in trace._events))


if __name__ == '__main__':
    unittest.main()
