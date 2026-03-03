# ChatGPT → UDIF Converter

Converts a ChatGPT data export (`conversations.json`) into valid UDIF 2.0 files.

## How to Export Your ChatGPT Data

1. Go to [chat.openai.com](https://chat.openai.com)
2. Click your profile → **Settings**
3. Navigate to **Data Controls**
4. Click **Export Data** → **Confirm Export**
5. Check your email for the download link
6. Download and unzip — you need `conversations.json`

## Usage

```bash
python convert.py /path/to/conversations.json /path/to/output/
```

This creates one `.udif.json` file per conversation in the output directory.

## What Gets Converted

- Full message history (user and assistant messages)
- Timestamps for each message
- Conversation titles
- Model information (GPT-4, GPT-4o, etc.)
- Session IDs
- SHA-256 provenance hashes for integrity verification

## Dependencies

Python 3.7+ with no external dependencies (stdlib only).

## Validating Output

```bash
python ../../validator/validate.py /path/to/output/
```
