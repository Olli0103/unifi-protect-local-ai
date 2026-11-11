"""Check repository-only interface inventory coverage, never source rights.

This tool does not access firmware, devices, private research or reference URLs.
Synthetic coverage cannot establish that a cited observation actually occurred.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
from collections import defaultdict
import json
from pathlib import Path
import re

INVENTORY_PATTERN = (
    r"0xa5f0|0xa5f1|UP-AI-KEY|UVC AI Port|10001|233\.89\.188\.1|7442|7443|"
    r"/api/adopt|/api/1\.2/manage|/api/info|ucp4|x-ident|x-mode|x-key|x-adopted|"
    r"ubnt_avclient|UiStreamControl|GetStreamList|ResetAIPortStreams|EventAIPortStatus|"
    r"ChangeVideoSettings|UpdateUsernamePassword|/internal/aiprocessors|"
    r"secure_transfer|/camera/1\.0/ws|a photo of|ubntbox"
)
INVENTORY_RE = re.compile(INVENTORY_PATTERN)
COMMAND_RE = re.compile(
    r"(?:get|set|change|update|recognize|generate|speech|post|Get|Set|Change|"
    r"Update|Reset|Event|Request|Start|Stop|Onvif|Network)[A-Z][A-Za-z0-9_]*\Z"
)
SOURCE_CLASSES = {
    "protect_own_installation", "own_device_observation", "live_trial",
    "public_documentation", "needs_observation",
}
# Explicitly reviewed wire-boundary functions. This is not a proof that a regex
# or AST pass recognizes every possible future manufacturer-protocol fact.
WIRE_FUNCTIONS = {
    "protocol.py": None,
    "device.py": {"_headers", "get_info", "_validate_adoption"},
    "aiport_candidate.py": {
        "_send_diagnostic_hello", "_reply_control", "_send_control_event",
        "_send_stream_status",
    },
}
TOP_LEVEL_WIRE_NAMES = {
    "device.py": {"_OBJECT_CAPABILITIES", "_EMPTY_BODY_ACKS", "_NATIVE_TASK_TARGETS"},
    "aiport_candidate.py": {"_ALLOWED_TOP_LEVEL", "_ALLOWED_MGMT", "_OBSERVABLE_FUNCTIONS"},
}


def _dict_fields(node):
    for item in ast.walk(node):
        if isinstance(item, ast.Dict):
            for key in item.keys:
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    yield key
        if isinstance(item, ast.Subscript):
            if (isinstance(item.value, ast.Name)
                    and item.value.id in {"header", "body", "result", "event", "message",
                                          "payload", "flags", "response", "management"}
                    and isinstance(item.slice, ast.Constant)
                    and isinstance(item.slice.value, str)):
                yield item.slice


def collect_inventory(root: Path) -> dict[str, list[str]]:
    """Return stable fact keys and exact current source locations."""
    root = root.resolve()
    found = defaultdict(set)

    def add(key, path, line):
        found[key].add(f"{path.relative_to(root).as_posix()}:{line}")

    for path in sorted((root / "src").rglob("*.py")):
        if not path.resolve().is_relative_to(root):
            raise ValueError("source_path_outside_repository")
        text = path.read_text()
        for line, content in enumerate(text.splitlines(), 1):
            for match in INVENTORY_RE.finditer(content):
                add("inventory:" + match.group(), path, line)
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                continue
            value = node.value
            # Additional commands/headers and target URIs across the source tree.
            if ((COMMAND_RE.fullmatch(value) and value != "NetworkVerified")
                    or (path.name in WIRE_FUNCTIONS
                        and re.fullmatch(r"[xX]-[A-Za-z0-9-]+", value))
                    or re.fullmatch(r"Camera-[A-Za-z]+", value)
                    or value.startswith((":7968/", ":7445/", ":7788/",
                                         "/internal/aiprocessors/", "/api/1.2/",
                                         "/camera/1.0/"))
                    or value in {"NL_PARSE", "IMAGE_SEARCH", "Adopted", "diskInfo",
                                 "networkStatus", "sshService", "timeSync"}):
                add("wire_atom:" + value, path, node.lineno)

        if path.name in {"device.py", "aiport_candidate.py"}:
            for node in ast.walk(tree):
                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                        and node.func.attr == "get"
                        and isinstance(node.func.value, ast.Name)
                        and node.func.value.id in {"message", "payload", "body", "header"}
                        and node.args and isinstance(node.args[0], ast.Constant)
                        and isinstance(node.args[0].value, str)):
                    add("wire_field:" + node.args[0].value, path, node.args[0].lineno)
                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                        and node.func.attr == "_reply_control" and len(node.args) >= 4
                        and isinstance(node.args[3], ast.Constant)
                        and type(node.args[3].value) is int):
                    add("aiport_status:" + str(node.args[3].value), path, node.lineno)

        if path.name in WIRE_FUNCTIONS:
            names = WIRE_FUNCTIONS[path.name]
            selected = [
                node for node in ast.walk(tree)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and (names is None or node.name in names)
            ]
            for node in selected:
                for field in _dict_fields(node):
                    add("wire_field:" + field.value, path, field.lineno)
            if path.name == "protocol.py":
                for node in ast.walk(tree):
                    if (isinstance(node, ast.Call)
                            and isinstance(node.func, ast.Attribute)
                            and node.func.attr == "get"
                            and node.args
                            and isinstance(node.args[0], ast.Constant)
                            and isinstance(node.args[0].value, str)):
                        add("wire_field:" + node.args[0].value, path, node.args[0].lineno)
            for node in tree.body:
                if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                    continue
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                assigned = {target.id for target in targets if isinstance(target, ast.Name)}
                if assigned & TOP_LEVEL_WIRE_NAMES.get(path.name, set()):
                    for atom in ast.walk(node.value):
                        if isinstance(atom, ast.Constant) and isinstance(atom.value, str):
                            add("wire_atom:" + atom.value, path, atom.lineno)

        if path.name == "discovery.py":
            for assignment in ast.walk(tree):
                if not (isinstance(assignment, ast.Assign) and any(
                    isinstance(target, ast.Name) and target.id == "fields"
                    for target in assignment.targets
                )):
                    continue
                for node in ast.walk(assignment.value):
                    if (isinstance(node, ast.Tuple) and len(node.elts) == 2
                            and isinstance(node.elts[0], ast.Constant)
                            and type(node.elts[0].value) is int):
                        add(f"discovery_tlv:0x{node.elts[0].value:02x}", path, node.lineno)
            for node in tree.body:
                if isinstance(node, ast.Assign) and any(
                    isinstance(target, ast.Name) and target.id in {"_HEADER", "_TLV"}
                    for target in node.targets
                ):
                    for atom in ast.walk(node.value):
                        if isinstance(atom, ast.Constant) and isinstance(atom.value, str):
                            add("discovery_layout:" + atom.value, path, atom.lineno)

        if path.name == "protocol.py":
            for node in tree.body:
                if isinstance(node, ast.Assign) and any(
                    isinstance(target, ast.Name) and target.id == "_RECORD"
                    for target in node.targets
                ):
                    add("ucp_record:two_records_types_1_2_format_1_empty_body_2", path, node.lineno)

    return {key: sorted(locations) for key, locations in sorted(found.items())}


def validate_registry(root: Path, registry: dict) -> list[str]:
    """Check coverage and reference shape, not the truth of the evidence."""
    errors = []
    if not isinstance(registry, dict) or registry.get("schema") != "interface-sources/1":
        return ["unsupported_schema"]
    entries = registry.get("facts")
    if not isinstance(entries, list):
        return ["invalid_facts"]
    expected = collect_inventory(root)
    observed = {}
    for entry in entries:
        if not isinstance(entry, dict):
            errors.append("invalid_fact")
            continue
        key = entry.get("inventory_key")
        if not isinstance(key, str) or key in observed:
            errors.append("invalid_or_duplicate_inventory_key")
            continue
        observed[key] = entry
        if not isinstance(entry.get("fact"), str) or not entry["fact"].strip():
            errors.append(f"missing_fact:{key}")
        locations = entry.get("code_locations")
        if locations != expected.get(key):
            errors.append(f"location_mismatch:{key}")
        source_class = entry.get("source_class")
        if source_class not in SOURCE_CLASSES:
            errors.append(f"invalid_source_class:{key}")
        reference = entry.get("reference")
        if not isinstance(reference, str) or (
            source_class != "needs_observation" and not reference.strip()
        ):
            errors.append(f"missing_reference:{key}")
        if source_class != "needs_observation" and isinstance(reference, str):
            path_part = reference.split("#", 1)[0]
            candidate = (root / path_part).resolve()
            if (not path_part.startswith("docs/evidence/")
                    or not candidate.is_relative_to(root.resolve())
                    or not candidate.is_file()):
                errors.append(f"invalid_repository_reference:{key}")
            elif entry.get("reference_sha256") != hashlib.sha256(candidate.read_bytes()).hexdigest():
                errors.append(f"reference_digest_mismatch:{key}")
        if source_class == "needs_observation":
            if not isinstance(entry.get("observation"), str) or not entry["observation"].strip():
                errors.append(f"missing_observation_instruction:{key}")
    for key in sorted(expected.keys() - observed.keys()):
        errors.append(f"missing_inventory_fact:{key}")
    for key in sorted(observed.keys() - expected.keys()):
        errors.append(f"stale_inventory_fact:{key}")
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--inventory", action="store_true", help="Print source inventory only.")
    parser.add_argument("--require-observed", action="store_true",
                        help="Fail if any fact still needs an observation.")
    args = parser.parse_args(argv)
    if args.inventory:
        print(json.dumps(collect_inventory(args.root), indent=2))
        return 0
    registry = json.loads((args.root / "docs/legal/interface-sources.json").read_text())
    errors = validate_registry(args.root, registry)
    pending = sum(entry["source_class"] == "needs_observation" for entry in registry["facts"])
    if args.require_observed and pending:
        errors.append("observations_pending")
    print(json.dumps({"facts": len(registry["facts"]), "needs_observation": pending,
                      "errors": errors, "rights_approval": False}, indent=2))
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
