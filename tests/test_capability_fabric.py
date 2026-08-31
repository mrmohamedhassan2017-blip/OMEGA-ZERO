from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from omega.capability_fabric import (
    controlled_routing,
    discover_capabilities,
    historical_replay,
    profile_task,
    red_team_review,
    route_task,
    run_capability_fabric_cycle,
    security_review,
    shadow_compare,
)


class CapabilityFabricTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "omega").mkdir()
        (self.root / "tests").mkdir()
        for name in (
            "engine.py", "store.py", "api.py", "supervisor.py", "wake_plane.py",
            "wake_provenance.py", "gmail_adapter.py", "capability_discovery.py",
            "development_governor.py", "zpa.py", "evaluation.py",
        ):
            (self.root / "omega" / name).write_text(name, encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_registry_is_repository_truth_based(self) -> None:
        registry = discover_capabilities(self.root)
        ids = {item["capability_id"] for item in registry["capabilities"]}
        self.assertIn("deterministic-core", ids)
        self.assertIn("host-verification", ids)
        self.assertIn("claude-code-backend", ids)
        self.assertEqual(registry["version"], 2)
        self.assertTrue(registry["registry_hash"])
        for item in registry["capabilities"]:
            self.assertIn(item["availability"], {
                "AVAILABLE", "UNAVAILABLE", "UNKNOWN", "DEGRADED", "WAITING_RESOURCE",
                "AUTHORITY_REQUIRED", "QUOTA_LIMITED", "TEMPORARILY_BLOCKED",
            })

    def test_unknown_capability_is_not_available(self) -> None:
        registry = discover_capabilities(self.root)
        unknown = next(item for item in registry["capabilities"] if item["capability_id"] == "web-research")
        self.assertEqual(unknown["availability"], "UNKNOWN")
        self.assertNotEqual(unknown["availability"], "AVAILABLE")

    def test_claude_presence_alone_is_not_routing_eligibility(self) -> None:
        with patch("omega.capability_fabric._claude_executable", return_value="C:/tools/claude.exe"):
            registry = discover_capabilities(self.root)
        claude = next(item for item in registry["capabilities"] if item["capability_id"] == "claude-code-backend")
        self.assertEqual("UNKNOWN", claude["availability"])
        self.assertEqual("DISCOVERED", claude["adoption_state"])
        self.assertIn("not routing-eligible", " ".join(claude["current_limits"]))

    def test_provider_canary_can_select_discovered_claude_without_general_promotion(self) -> None:
        with patch("omega.capability_fabric._claude_executable", return_value="C:/tools/claude.exe"):
            registry = discover_capabilities(self.root)
        profile = profile_task({"task_id": "canary", "objective": "provider canary", "task_type": "CODE"})
        profile["required_capabilities"] = ["CODE_GENERATION"]
        profile["required_capability_id"] = "claude-code-backend"
        profile["provider_canary"] = True
        route = route_task(profile, registry)
        self.assertEqual("SELECTED", route["selected_route"]["status"])
        selected = route["selected_route"]["capabilities"][0]
        self.assertEqual("claude-code-backend", selected["capability_id"])
        self.assertEqual("UNKNOWN", selected["availability"])
        self.assertFalse(route["selected_route"]["execution_performed"])

    def test_host_verified_canary_registers_claude_for_shadow_only(self) -> None:
        runtime = self.root / ".omega" / "runtime"
        runtime.mkdir(parents=True)
        (runtime / "claude_backend_status.json").write_text(json.dumps({
            "authentication_state": "AUTHENTICATED", "resource_state": "ACTIVE",
            "canary_result": "PASS", "capability_registry_eligible": True,
        }), encoding="utf-8")
        with patch("omega.capability_fabric._claude_executable", return_value="C:/tools/claude.exe"), \
             patch("omega.capability_fabric._codex_executable", return_value=None):
            registry = discover_capabilities(self.root)
            route = route_task(profile_task({"task_id": "code", "objective": "repair code", "changes_code": True}), registry)
        claude = next(item for item in registry["capabilities"] if item["capability_id"] == "claude-code-backend")
        self.assertEqual("AVAILABLE", claude["availability"])
        self.assertEqual("CONTROLLED", claude["adoption_state"])
        selected = next(item for item in route["selected_route"]["capabilities"] if item["capability"] == "CODE_GENERATION")
        self.assertEqual("claude-code-backend", selected["capability_id"])
        self.assertFalse(route["selected_route"]["execution_performed"])
        self.assertTrue(route["verification_plan"]["required_before_acceptance"])

    def test_task_profiles_are_deterministic_and_typed(self) -> None:
        first = profile_task({"task_id": "t1", "objective": "run deterministic tests"})
        second = profile_task({"task_id": "t1", "objective": "run deterministic tests"})
        self.assertEqual(first, second)
        self.assertIn("TESTING", first["required_capabilities"])
        self.assertEqual(first["task_type"], "DETERMINISTIC")

    def test_external_profile_requires_authority(self) -> None:
        profile = profile_task({"task_id": "external", "objective": "publish a GitHub artifact", "external_effects": True})
        self.assertTrue(profile["external_effects"])
        self.assertEqual(profile["task_type"], "EXTERNAL")
        self.assertIn("EXTERNAL_OBSERVATION", profile["required_capabilities"])

    def test_local_route_is_selected_without_execution(self) -> None:
        registry = discover_capabilities(self.root)
        profile = profile_task({"task_id": "local", "objective": "run unit tests"})
        route = route_task(profile, registry)
        self.assertEqual(route["selected_route"]["status"], "SELECTED")
        self.assertFalse(route["selected_route"]["execution_performed"])
        self.assertTrue(route["verification_plan"]["required_before_acceptance"])

    def test_external_route_waits_for_authority(self) -> None:
        registry = discover_capabilities(self.root)
        profile = profile_task({"task_id": "external", "objective": "publish public artifact", "external_effects": True})
        route = route_task(profile, registry)
        self.assertEqual(route["selected_route"]["status"], "WAIT_AUTHORITY")

    def test_quota_route_waits_for_resource(self) -> None:
        registry = discover_capabilities(self.root)
        profile = profile_task({"task_id": "quota", "objective": "resume task", "resource_state": "QUOTA_EXHAUSTED"})
        route = route_task(profile, registry)
        self.assertEqual(route["selected_route"]["status"], "WAIT_RESOURCE")

    def test_novel_route_escalates_without_calling_a_model(self) -> None:
        registry = discover_capabilities(self.root)
        profile = profile_task({"task_id": "novel", "objective": "resolve novel lifecycle state", "novel": True})
        route = route_task(profile, registry)
        self.assertIn(route["selected_route"]["status"], {"CAPABILITY_GAP", "MODEL_ESCALATION_REQUIRED"})
        self.assertTrue(route["model_escalation"] or route["selected_route"]["status"] == "CAPABILITY_GAP")

    def test_historical_replay_covers_required_families(self) -> None:
        registry = discover_capabilities(self.root)
        replay = historical_replay(self.root, registry)
        self.assertEqual(replay["count"], 9)
        self.assertTrue(replay["passed"])
        self.assertEqual(replay["passed_count"], 9)

    def test_shadow_is_non_authoritative_and_parity_holds(self) -> None:
        registry = discover_capabilities(self.root)
        replay = historical_replay(self.root, registry)
        shadow = shadow_compare(replay)
        self.assertTrue(shadow["passed"])
        self.assertEqual(shadow["decision_parity"], shadow["total"])
        self.assertEqual(shadow["side_effects"], 0)

    def test_controlled_routing_is_internal_only(self) -> None:
        result = controlled_routing(discover_capabilities(self.root))
        self.assertTrue(result["passed"])
        self.assertFalse(result["production_switch"])
        self.assertEqual(result["side_effects"], 0)

    def test_no_subprocess_is_used_by_discovery_or_routing(self) -> None:
        with patch.object(subprocess, "run", side_effect=AssertionError("subprocess forbidden")), \
             patch.object(subprocess, "Popen", side_effect=AssertionError("subprocess forbidden")):
            registry = discover_capabilities(self.root)
            profile = profile_task("inspect local state")
            route_task(profile, registry)
            historical_replay(self.root, registry)

    def test_security_and_red_team_controls_pass(self) -> None:
        registry = discover_capabilities(self.root)
        self.assertTrue(security_review(registry)["passed"])
        red = red_team_review()
        self.assertEqual(red["authority_violations"], 0)
        self.assertEqual(red["unverified_success_acceptances"], 0)

    def test_cycle_persists_registry_replay_and_performance_memory(self) -> None:
        out = self.root / ".omega" / "zero"
        result = run_capability_fabric_cycle(self.root, out)
        self.assertEqual(result["final_result"], "CAPABILITY_FABRIC_SHADOW_PARITY_NO_MEASURABLE_DELTA")
        self.assertTrue((out / "capability_fabric_registry_v2.json").exists())
        self.assertTrue((out / "capability_fabric_replay_0001.json").exists())
        self.assertTrue((out / "capability_fabric_cycle_0001.json").exists())
        self.assertTrue((out / "capability_fabric_performance.json").exists())
        persisted = json.loads((out / "capability_fabric_cycle_0001.json").read_text(encoding="utf-8"))
        self.assertEqual(persisted["v030_state"], "WAITING_EXTERNAL_EVIDENCE")
        self.assertEqual(persisted["verified_economic_value_change_kwd"], 0)

    def test_cycle_sequence_is_monotonic(self) -> None:
        out = self.root / ".omega" / "zero"
        run_capability_fabric_cycle(self.root, out)
        run_capability_fabric_cycle(self.root, out)
        self.assertTrue((out / "capability_fabric_cycle_0002.json").exists())


if __name__ == "__main__":
    unittest.main()
