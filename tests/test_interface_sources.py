"""Source inventory coverage is not native, rights or provenance approval."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from tools.interface_sources_check import (
    INVENTORY_RE, collect_inventory, validate_registry,
)

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs/legal/interface-sources.json"


def synthetic_registry(root):
    entries = [
        {"inventory_key": key, "fact": key, "code_locations": locations,
         "source_class": "needs_observation", "reference": "",
         "observation": "Maintainer must observe this on an owned device."}
        for key, locations in collect_inventory(root).items()
    ]
    return {"schema": "interface-sources/1", "facts": entries}


def fixture_root(tmp_path):
    src = tmp_path / "src/aikey"
    src.mkdir(parents=True)
    (src / "protocol.py").write_text('MODEL = "UP-AI-KEY"\n')
    return tmp_path


def test_current_registry_covers_all_inventory_locations():
    data = json.loads(REGISTRY.read_text())
    assert validate_registry(ROOT, data) == []
    # Check the original requested regex independently of AST enrichment.
    recorded = {
        (entry["inventory_key"].removeprefix("inventory:"), location)
        for entry in data["facts"] if entry["inventory_key"].startswith("inventory:")
        for location in entry["code_locations"]
    }
    requested = {
        (match.group(), f"{path.relative_to(ROOT).as_posix()}:{line}")
        for path in (ROOT / "src").rglob("*.py")
        for line, text in enumerate(path.read_text().splitlines(), 1)
        for match in INVENTORY_RE.finditer(text)
    }
    assert recorded == requested
    assert data["rights_approval"] is False


def test_a_new_uncatalogued_protocol_constant_fails(tmp_path):
    root = fixture_root(tmp_path)
    registry = synthetic_registry(root)
    assert validate_registry(root, registry) == []
    with (root / "src/aikey/protocol.py").open("a") as stream:
        stream.write('NEW_ROUTE = "/api/info"\n')
    errors = validate_registry(root, registry)
    assert "missing_inventory_fact:inventory:/api/info" in errors


def test_new_header_and_message_field_are_not_hidden_by_original_regex(tmp_path):
    root = fixture_root(tmp_path)
    registry = synthetic_registry(root)
    with (root / "src/aikey/protocol.py").open("a") as stream:
        stream.write('def response():\n    return {"x-future-header": "v", "newWireField": 1}\n')
    errors = validate_registry(root, registry)
    assert "missing_inventory_fact:wire_atom:x-future-header" in errors
    assert "missing_inventory_fact:wire_field:newWireField" in errors


def test_new_occurrence_of_existing_constant_also_requires_mapping(tmp_path):
    root = fixture_root(tmp_path)
    registry = synthetic_registry(root)
    (root / "src/aikey/other.py").write_text('MODEL = "UP-AI-KEY"\n')
    assert "location_mismatch:inventory:UP-AI-KEY" in validate_registry(root, registry)


def test_recorded_fact_cannot_disappear_silently(tmp_path):
    root = fixture_root(tmp_path)
    registry = synthetic_registry(root)
    (root / "src/aikey/protocol.py").write_text("")
    assert "stale_inventory_fact:inventory:UP-AI-KEY" in validate_registry(root, registry)


@pytest.mark.parametrize("source_class", [
    "protect_own_installation", "own_device_observation", "live_trial", "public_documentation",
])
def test_mapped_sources_need_a_nonempty_reference(tmp_path, source_class):
    root = fixture_root(tmp_path)
    registry = synthetic_registry(root)
    registry["facts"][0]["source_class"] = source_class
    assert any(e.startswith("missing_reference:") for e in validate_registry(root, registry))


def test_pending_source_may_have_empty_reference_but_needs_action(tmp_path):
    root = fixture_root(tmp_path)
    registry = synthetic_registry(root)
    assert validate_registry(root, registry) == []
    registry["facts"][0]["observation"] = ""
    assert any(e.startswith("missing_observation_instruction:") for e in validate_registry(root, registry))


def test_reference_digest_prevents_silent_evidence_drift(tmp_path):
    root = fixture_root(tmp_path)
    evidence = root / "docs/evidence/synthetic-trial.md"
    evidence.parent.mkdir(parents=True)
    evidence.write_text("Synthetic reference for checker tests, not a real observation.\n")
    registry = synthetic_registry(root)
    entry = registry["facts"][0]
    entry.update(source_class="live_trial", reference="docs/evidence/synthetic-trial.md#L1",
                 reference_sha256=hashlib.sha256(evidence.read_bytes()).hexdigest())
    assert validate_registry(root, registry) == []
    evidence.write_text("Changed synthetic reference.\n")
    assert any(e.startswith("reference_digest_mismatch:") for e in validate_registry(root, registry))


@pytest.mark.parametrize("reference", [
    "../outside.md", "/private/outside.md", "docs/evidence/../../../../outside.md",
    "https://example.org/not-a-repository-record",
])
def test_registry_cannot_point_outside_the_reviewed_repository(tmp_path, reference):
    root = fixture_root(tmp_path)
    registry = synthetic_registry(root)
    registry["facts"][0].update(source_class="live_trial", reference=reference)
    assert any(e.startswith("invalid_repository_reference:") for e in validate_registry(root, registry))


def test_duplicate_fact_and_unknown_source_class_fail(tmp_path):
    root = fixture_root(tmp_path)
    registry = synthetic_registry(root)
    registry["facts"].append(deepcopy(registry["facts"][0]))
    assert "invalid_or_duplicate_inventory_key" in validate_registry(root, registry)
    registry["facts"].pop()
    registry["facts"][0]["source_class"] = "automatically_approved"
    assert any(e.startswith("invalid_source_class:") for e in validate_registry(root, registry))


def test_discovery_inventory_covers_tlv_type_but_not_arbitrary_integer_tuple(tmp_path):
    root = fixture_root(tmp_path)
    path = root / "src/aikey/discovery.py"
    path.write_text('CHOICES = (0, 4)\ndef response():\n    fields = [(0x10, b"value")]\n')
    inventory = collect_inventory(root)
    assert "discovery_tlv:0x10" in inventory
    assert "discovery_tlv:0x00" not in inventory


def test_source_symlink_cannot_open_private_artifact(tmp_path):
    root = fixture_root(tmp_path / "repo")
    private = tmp_path / "outside.py"
    private.write_text('raise RuntimeError("must not be read as source")\n')
    (root / "src/aikey/outside.py").symlink_to(private)
    with pytest.raises(ValueError, match="source_path_outside_repository"):
        collect_inventory(root)
