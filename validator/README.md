# UDIF Validator

Validates UDIF 2.0 files against the official JSON Schema and performs integrity checks.

## Usage

```bash
# Validate a single file
python validate.py conversation.udif.json

# Validate all UDIF files in a directory
python validate.py /path/to/output/
```

## What It Checks

- **Schema compliance** — validates against `spec/schema/udif.schema.json`
- **Required fields** — verifies `udif`, `meta`, `platform`, `data_event` are present
- **Message structure** — checks each message has `role`, `content`, `timestamp`
- **Provenance integrity** — recomputes SHA-256 hash and compares to stored hash
- **Chain validation** — verifies provenance chain entries have required fields
- **Value ranges** — checks scores are within 1-10 bounds

## Dependencies

- Python 3.7+ (required)
- `jsonschema` (optional, recommended) — `pip install jsonschema`

Without `jsonschema`, the validator still checks required fields and provenance
but cannot perform full JSON Schema validation.

## Exit Codes

- `0` — all files valid
- `1` — one or more files invalid
