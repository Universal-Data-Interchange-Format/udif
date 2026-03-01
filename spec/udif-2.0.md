# UDIF 2.0 Specification

**Status:** Draft  
**Version:** 2.0.0  
**Invented by:** Angela Benton  
**Original standard:** Streamlytics, Inc. (2018)  
**License:** Apache 2.0

---

## Overview

UDIF (Universal Data Interchange Format) is an open standard for 
portable, sovereign data. Version 2.0 extends the original standard 
into the AI interaction layer.

A UDIF file is a structured JSON document that represents a person's 
data in a format that is:

- Platform-agnostic — readable by any system
- Self-contained — no platform dependency to access
- Verifiable — includes provenance metadata proving origin and integrity
- Extensible — supports any data type through the module system

---

## Core Structure

Every UDIF file contains four top-level objects:
```json
{
  "udif": "2.0",
  "identity": {},
  "context": {},
  "provenance": {}
}
```

### udif
Version string. Always present. Identifies the file as UDIF and 
specifies the version.

### identity
Information about the data subject. Contains verified or 
self-attested identity attributes.

### context
The data itself, organized by module. Each module represents 
a category of data (ai_interactions, preferences, creative_output, etc.)

### provenance
Cryptographic metadata establishing the origin, authenticity, 
and integrity of the file.

---

## Modules

UDIF 2.0 ships with the following core modules:

| Module | Description |
|--------|-------------|
| `ai_interactions` | Conversation history with AI systems |
| `preferences` | User preferences and values |
| `creative_output` | Written work, ideas, and creative artifacts |
| `behavioral_context` | Patterns and tendencies across systems |
| `identity_attributes` | Verified and self-attested identity data |

---

## Provenance Layer

The provenance object contains:

- `created_at` — ISO 8601 timestamp of file creation
- `source` — platform or system the data originated from
- `hash` — SHA-256 hash of the context object
- `signature` — optional cryptographic signature

---

## Versioning

UDIF follows semantic versioning. Breaking changes increment 
the major version. The `udif` field in every file identifies 
the version of the spec it conforms to.

---

## Status

The full technical specification is under active development. 
The JSON Schema definition is in `/spec/schema/udif.schema.json`.

To contribute to the spec, open an issue or pull request.
