"""Offline tests for the small-molecule inhibitor module. No model calls."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from importlib.resources import files
from pathlib import Path
from unittest.mock import patch

import yaml
from src.agents.registry import AGENT_REGISTRY as NDC_AGENTS
from src.schemas.gate import GATE_DEFINITIONS as NDC_GATES
from src.smi.cli import TARGETS, build_smi_plan, load_smi_dossier
from src.smi.registry import AGENT_REGISTRY, build_specialist_agents
from src.smi.schemas.dossier import SMIDossier
from src.smi.schemas.gate import SMI_GATE_DEFINITIONS, SMIGateID
from src.utils.run_manifest import RunManifest
from src.utils.trace_logger import TraceLogger

REPO = Path(__file__).resolve().parents[1]


class SmallMoleculeModuleTests(unittest.TestCase):
    def test_policy_is_separate_from_ndc(self):
        self.assertEqual(len(AGENT_REGISTRY), 7)
        self.assertEqual(len(NDC_AGENTS), 7)
        self.assertEqual(set(AGENT_REGISTRY) & set(NDC_AGENTS), {"cso", "scientific_reviewer"})
        self.assertEqual({gate.value for gate in SMI_GATE_DEFINITIONS}, {gate.value for gate in SMIGateID})
        self.assertEqual(len(SMI_GATE_DEFINITIONS), 6)
        self.assertTrue({gate.value for gate in NDC_GATES}.isdisjoint({gate.value for gate in SMIGateID}))
        agents = {gate["agent"] for gate in SMI_GATE_DEFINITIONS.values()}
        self.assertEqual(agents, {
            "target_biology", "ligand_chemistry", "pharmacology", "adme_exposure", "safety_translation",
        })
        self.assertEqual(SMI_GATE_DEFINITIONS[SMIGateID.M2_POTENCY]["agent"], "pharmacology")
        self.assertEqual(SMI_GATE_DEFINITIONS[SMIGateID.M3_CELLULAR]["agent"], "pharmacology")
        for config in AGENT_REGISTRY.values():
            self.assertGreater(len(config["prompt"]), 200)
        self.assertIn("Do not write synthetic routes", AGENT_REGISTRY["cso"]["prompt"])
        self.assertIn("Do not provide reagents", AGENT_REGISTRY["ligand_chemistry"]["prompt"])

    def test_reference_yaml_matches_runtime_ids_and_is_not_loaded_by_cli(self):
        cli_source = (REPO / "src/smi/cli.py").read_text()
        self.assertNotIn("gates.yaml", cli_source)
        document = yaml.safe_load(files("src.smi").joinpath("config/gates.yaml").read_text())
        self.assertEqual(set(document["gates"]), {gate.value for gate in SMIGateID})
        for gate_id, spec in SMI_GATE_DEFINITIONS.items():
            recorded = document["gates"][gate_id.value]
            self.assertEqual(recorded["agent"], spec["agent"])
            self.assertEqual([item["id"] for item in recorded["required_evidence"]], spec["required_evidence"])

    def test_plan_branches_on_compound_batch(self):
        landscape = build_smi_plan("pnpla3", {"target_profile": {"gene_symbol": "PNPLA3"}})
        candidate = build_smi_plan("pnpla3", {
            "target_profile": {"gene_symbol": "PNPLA3"},
            "compound": {"compound_id": "CMPD-1", "source": "fixture"},
        })
        for plan in (landscape, candidate):
            agents = {step["agent"] for step in plan["steps"]}
            self.assertEqual(agents, set(AGENT_REGISTRY) - {"cso"})
            self.assertEqual(plan["valid_order"][-1], "s7_review")
            self.assertEqual(plan["module"], "small_molecule_inhibitor")
            by_id = {step["id"]: step for step in plan["steps"]}
            self.assertEqual(by_id["s4_cellular"]["depends_on"], ["s3_potency"])
            self.assertEqual(by_id["s5_adme"]["depends_on"], ["s2_chemistry"])
            self.assertEqual(by_id["s3_potency"]["agent"], "pharmacology")
            self.assertEqual(by_id["s4_cellular"]["agent"], "pharmacology")
        self.assertEqual(landscape["parallel_groups"][0], ["s1_target"])
        chemistry = next(step for step in landscape["steps"] if step["id"] == "s2_chemistry")
        self.assertEqual(chemistry["depends_on"], ["s1_target"])
        candidate_chemistry = next(step for step in candidate["steps"] if step["id"] == "s2_chemistry")
        self.assertEqual(candidate_chemistry["depends_on"], [])
        self.assertEqual(set(candidate["parallel_groups"][0]), {"s1_target", "s2_chemistry"})

    def test_pnpla3_reference_dossier_has_no_batch_claim(self):
        with patch.dict(os.environ, {"SYFLOW_PROJECT_ROOT": str(REPO)}):
            dossier = load_smi_dossier("pnpla3")
        self.assertNotIn("compound", dossier)
        self.assertEqual(dossier["target_profile"]["gene_symbol"], "PNPLA3")
        self.assertIsNone(dossier["target_profile"]["protein_expression_disease"])
        model = SMIDossier.model_validate(dossier)
        self.assertIsNone(model.compound)
        self.assertEqual(model.current_gate, "M0")
        model.advance_gate("M0", "hold", "protein data missing")
        self.assertEqual(model.current_gate, "M0")
        self.assertEqual(TARGETS["pnpla3"]["dossier"], "targets/pnpla3/smi_dossier.yaml")
        plan = build_smi_plan("pnpla3", dossier)
        self.assertEqual(plan["parallel_groups"][0], ["s1_target"])

    def test_missing_dossier_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"SYFLOW_PROJECT_ROOT": tmp}):
                with self.assertRaises(ValueError):
                    load_smi_dossier("pnpla3")
            path = Path(tmp) / "bad.yaml"
            path.write_text("target_profile: {}\n")
            with self.assertRaises(ValueError):
                load_smi_dossier("pnpla3", str(path))

    def test_cli_initializes_without_a_verdict(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dossier = root / "dossier.yaml"
            dossier.write_text("target_profile:\n  gene_symbol: PNPLA3\n")
            env = {**os.environ, "SYFLOW_RUNS_DIR": str(root / "runs")}
            commands = [
                [sys.executable, "-m", "src.smi", "validate", "--target", "pnpla3", "--dossier", str(dossier)],
                [sys.executable, "-m", "src", "smi", "gate", "--target", "pnpla3", "--gate", "M2", "--dossier", str(dossier)],
            ]
            for args in commands:
                result = subprocess.run(args, cwd=root, env=env, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            runs = list((root / "runs").iterdir())
            self.assertEqual(len(runs), 2)
            for run in runs:
                metadata = json.loads((run / "run_metadata.json").read_text())
                self.assertEqual(metadata["platform"], "syflow_smi")
                audit = json.loads((run / "audit.json").read_text())
                self.assertEqual(audit["status"], "initialized")
                plan = json.loads((run / "inputs" / "plan.json").read_text())
                self.assertEqual(plan["module"], "small_molecule_inhibitor")
                manifest = RunManifest.load(run)
                self.assertEqual(manifest.verify_all(), [])
                self.assertTrue(all(item.produced_by == "cli_initializer" for item in manifest.artifacts.values()))
                trace = TraceLogger.load(run)
                self.assertFalse(any(
                    event.event_type in ("agent_start", "agent_stop", "tool_start", "gate_decision")
                    for event in trace._events
                ))

    def test_specialist_workspaces_omit_the_cso(self):
        with tempfile.TemporaryDirectory() as tmp:
            agents = build_specialist_agents(Path(tmp))
        self.assertEqual({agent["name"] for agent in agents}, set(AGENT_REGISTRY) - {"cso"})


if __name__ == "__main__":
    unittest.main()
