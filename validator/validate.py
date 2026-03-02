#!/usr/bin/env python3
"""
UDIF 2.0 Validator

Validates UDIF files against the official JSON Schema and performs
additional integrity checks on provenance hashes.

Usage:
    python validate.py <file.udif.json>
    python validate.py <directory>        # validate all .udif.json files

Requirements:
    pip install jsonschema

License: Apache 2.0
"""

import json
import hashlib
import re
import sys
import os
import glob

try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False


SCHEMA_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "spec", "schema", "udif.schema.json"
)


def load_schema():
    """Load the UDIF JSON Schema."""
    schema_path = SCHEMA_PATH
    if not os.path.exists(schema_path):
        # Try relative to current directory
        alt = os.path.join("spec", "schema", "udif.schema.json")
        if os.path.exists(alt):
            schema_path = alt
        else:
            return None

    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)


_ISO8601_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
    r"(\.\d+)?"
    r"(Z|[+-]\d{2}:\d{2})$"
)


def _is_valid_datetime(value):
    """Check if a string is a valid ISO 8601 date-time."""
    return isinstance(value, str) and bool(_ISO8601_RE.match(value))


def sha256_hash(obj):
    """Generate SHA-256 hash of a JSON-serializable object."""
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, default=str).encode()
    ).hexdigest()


def validate_file(filepath, schema=None):
    """
    Validate a single UDIF file.

    Returns a dict with:
        - valid: bool
        - errors: list of error strings
        - warnings: list of warning strings
        - filepath: the file path
    """
    result = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "filepath": filepath
    }

    # Load the file
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            doc = json.load(f)
    except json.JSONDecodeError as e:
        result["valid"] = False
        result["errors"].append(f"Invalid JSON: {e}")
        return result
    except Exception as e:
        result["valid"] = False
        result["errors"].append(f"Could not read file: {e}")
        return result

    # Schema validation
    if schema and HAS_JSONSCHEMA:
        try:
            jsonschema.validate(instance=doc, schema=schema)
        except jsonschema.ValidationError as e:
            result["valid"] = False
            path = " → ".join(str(p) for p in e.absolute_path) if e.absolute_path else "(root)"
            result["errors"].append(f"Schema violation at {path}: {e.message}")
        except jsonschema.SchemaError as e:
            result["warnings"].append(f"Schema itself has issues: {e.message}")
    elif not HAS_JSONSCHEMA:
        result["warnings"].append(
            "jsonschema not installed — skipping schema validation. "
            "Install with: pip install jsonschema"
        )

    # Manual required field checks (works without jsonschema)
    for field in ["udif", "meta", "platform", "data_event"]:
        if field not in doc:
            result["valid"] = False
            result["errors"].append(f"Missing required field: {field}")

    # Version check — schema defines "const": "2.0"
    if doc.get("udif") != "2.0":
        result["valid"] = False
        result["errors"].append(
            f"Unexpected UDIF version: {doc.get('udif')} (expected '2.0')"
        )

    # Meta validation
    meta = doc.get("meta", {})
    for field in ["source", "session_id", "timestamp", "consent_granted"]:
        if field not in meta:
            result["valid"] = False
            result["errors"].append(f"Missing required meta field: {field}")

    if meta.get("consent_granted") is not True:
        result["warnings"].append("consent_granted is not True")

    # Timestamp format checks (schema specifies format: date-time)
    if "timestamp" in meta and not _is_valid_datetime(meta["timestamp"]):
        result["warnings"].append(
            f"meta.timestamp is not valid ISO 8601: {meta['timestamp']}"
        )

    # Platform validation
    platform = doc.get("platform", {})
    for field in ["name", "data_format", "source_type", "export_date"]:
        if field not in platform:
            result["valid"] = False
            result["errors"].append(f"Missing required platform field: {field}")

    if "export_date" in platform and not _is_valid_datetime(platform["export_date"]):
        result["warnings"].append(
            f"platform.export_date is not valid ISO 8601: {platform['export_date']}"
        )

    # Data event validation
    data_event = doc.get("data_event", {})
    for field in ["type", "service"]:
        if field not in data_event:
            result["valid"] = False
            result["errors"].append(f"Missing required data_event field: {field}")

    # Message validation
    messages = data_event.get("messages", [])
    for i, msg in enumerate(messages):
        for field in ["role", "content", "timestamp"]:
            if field not in msg:
                result["errors"].append(
                    f"Message {i}: missing required field '{field}'"
                )
                result["valid"] = False
        if msg.get("role") not in ("user", "assistant"):
            result["warnings"].append(
                f"Message {i}: unexpected role '{msg.get('role')}' "
                f"(expected 'user' or 'assistant')"
            )
        if "timestamp" in msg and not _is_valid_datetime(msg["timestamp"]):
            result["warnings"].append(
                f"Message {i}: timestamp is not valid ISO 8601: {msg['timestamp']}"
            )

    # Provenance required fields — schema requires created_at and source
    provenance = doc.get("provenance", {})
    if provenance:
        for field in ["created_at", "source"]:
            if field not in provenance:
                result["valid"] = False
                result["errors"].append(f"Missing required provenance field: {field}")

    # Provenance hash verification
    if provenance.get("hash") and "data_event" in doc:
        expected_hash = sha256_hash(data_event)
        actual_hash = provenance["hash"]

        # Skip placeholder hashes
        if "placeholder" not in actual_hash.lower():
            if actual_hash != expected_hash:
                result["warnings"].append(
                    "Provenance hash does not match data_event content. "
                    "Data may have been modified after initial capture."
                )

    # Chain validation
    chain = provenance.get("chain", [])
    if chain:
        for i, link in enumerate(chain):
            if "platform" not in link:
                result["warnings"].append(f"Chain entry {i}: missing 'platform'")
            if "exported_at" not in link:
                result["warnings"].append(f"Chain entry {i}: missing 'exported_at'")

    # Frequency module check (optional but flag if malformed)
    frequency = doc.get("frequency", {})
    if frequency:
        if "authenticity_score" in frequency:
            score = frequency["authenticity_score"]
            if not isinstance(score, int) or score < 1 or score > 10:
                result["warnings"].append(
                    f"frequency.authenticity_score should be 1-10, got {score}"
                )

    # Context energy_score check (independent of frequency)
    if "energy_score" in doc.get("context", {}):
        score = doc["context"]["energy_score"]
        if not isinstance(score, int) or score < 1 or score > 10:
            result["warnings"].append(
                f"context.energy_score should be 1-10, got {score}"
            )

    return result


def print_result(result):
    """Pretty-print a validation result."""
    filename = os.path.basename(result["filepath"])
    status = "VALID" if result["valid"] else "INVALID"

    print(f"\n{status}  {filename}")

    for error in result["errors"]:
        print(f"  ERROR: {error}")

    for warning in result["warnings"]:
        print(f"  WARN:  {warning}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python validate.py <file.udif.json | directory>")
        print()
        print("Validate UDIF 2.0 files against the official schema.")
        print()
        print("Examples:")
        print("  python validate.py conversation.udif.json")
        print("  python validate.py ./output/")
        sys.exit(1)

    target = sys.argv[1]
    schema = load_schema()

    if schema is None:
        print("Warning: Could not find udif.schema.json — running without schema validation")

    # Collect files
    files = []
    if os.path.isfile(target):
        files = [target]
    elif os.path.isdir(target):
        files = glob.glob(os.path.join(target, "*.udif.json"))
        if not files:
            files = glob.glob(os.path.join(target, "*.json"))
    else:
        print(f"Error: {target} not found")
        sys.exit(1)

    if not files:
        print(f"No UDIF files found in {target}")
        sys.exit(1)

    # Validate
    total = len(files)
    valid_count = 0
    invalid_count = 0

    for filepath in sorted(files):
        result = validate_file(filepath, schema)
        print_result(result)
        if result["valid"]:
            valid_count += 1
        else:
            invalid_count += 1

    # Summary
    print(f"\n{'='*50}")
    print(f"Total: {total}  |  Valid: {valid_count}  |  Invalid: {invalid_count}")

    sys.exit(0 if invalid_count == 0 else 1)


if __name__ == "__main__":
    main()
