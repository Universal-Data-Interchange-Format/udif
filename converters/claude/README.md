# Claude → UDIF Converter

Converts a Claude (Anthropic) data export into valid UDIF 2.0 files.

## How to Export Your Claude Data

1. Go to [claude.ai](https://claude.ai)
2. Click your profile icon → **Settings**
3. Navigate to **Account**
4. Click **Export Data**
5. Check your email for the download link from Anthropic
6. Download and extract the zip file

## Usage

```bash
# Convert an entire export directory
python convert.py /path/to/claude-export/ /path/to/output/

# Convert a single conversation file
python convert.py conversation.json /path/to/output/
```

This will create one `.udif.json` file per conversation in the output directory.

## What Gets Converted

- Full message history (user and assistant messages)
- Timestamps for each message
- Conversation titles
- Model information
- Session IDs (UUIDs)
- SHA-256 provenance hashes for integrity verification

## Dependencies

Python 3.7+ with no external dependencies (stdlib only).

## Validating Output

After conversion, validate your files:

```bash
python ../../validator/validate.py /path/to/output/
```
