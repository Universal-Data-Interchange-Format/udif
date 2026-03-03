# Gemini → UDIF Converter

Converts a Google Gemini (formerly Bard) data export into valid UDIF 2.0 files.

## How to Export Your Gemini Data

1. Go to [takeout.google.com](https://takeout.google.com)
2. Click **Deselect All**, then select **Gemini Apps**
3. Click **Next Step** → **Create Export**
4. Download and extract the zip file
5. Conversations are in the `Gemini Apps/` folder

## Usage

```bash
# Convert the entire Takeout export
python convert.py /path/to/Takeout/Gemini\ Apps/ /path/to/output/

# Convert a single conversation file
python convert.py conversation.json /path/to/output/
```

This creates one `.udif.json` file per conversation in the output directory.

## What Gets Converted

- Full message history (user and model responses)
- Text content and code blocks
- Timestamps
- Conversation titles
- SHA-256 provenance hashes for integrity verification

## Dependencies

Python 3.7+ with no external dependencies (stdlib only).

## Validating Output

```bash
python ../../validator/validate.py /path/to/output/
```
