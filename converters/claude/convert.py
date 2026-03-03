#!/usr/bin/env python3
"""
Claude → UDIF 2.0 Converter

Converts a Claude (Anthropic) data export into valid UDIF 2.0 files.

Usage:
    python convert.py /path/to/claude-export/ /path/to/output/

Claude's export is a zip file containing JSON files for each conversation.
Each conversation file contains a structured list of messages with roles,
content, and timestamps.

Export your Claude data:
    Settings → Account → Export Data
    You'll receive an email with a download link for a zip file.
    Extract the zip — conversation files are in JSON format.

License: Apache 2.0
"""

import json
import hashlib
import uuid
import sys
import os
import glob
from datetime import datetime, timezone


def _format_utc(dt):
    """Format a datetime as ISO 8601 with Z suffix."""
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalize_timestamp(ts):
    """Parse a string timestamp and normalize to ISO 8601 with Z suffix."""
    for fmt in [
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
    ]:
        try:
            dt = datetime.strptime(ts, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return _format_utc(dt)
        except ValueError:
            continue
    # If nothing parses, return as-is (best effort)
    return ts


def sha256_hash(obj):
    """Generate SHA-256 hash of a JSON-serializable object."""
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, default=str).encode()
    ).hexdigest()


def extract_messages(chat_messages):
    """
    Extract and normalize messages from Claude's export format.

    Claude exports messages as an array of objects with:
    - sender: "human" or "assistant"
    - text or content: the message body
    - created_at or timestamp: ISO 8601 datetime

    This handles variations in the export format across different
    export versions.
    """
    messages = []

    for msg in chat_messages:
        # Handle different field names across export versions
        role_raw = msg.get("sender") or msg.get("role") or msg.get("author", "")
        if role_raw in ("human", "user"):
            role = "user"
        elif role_raw in ("assistant", "ai"):
            role = "assistant"
        else:
            # Skip unrecognized roles (system, tool, etc.)
            continue

        # Content can be in different fields
        content = (
            msg.get("text")
            or msg.get("content")
            or msg.get("body")
            or ""
        )

        # Handle content that's a list of blocks (newer export format)
        if isinstance(content, list):
            text_parts = []
            for block in content:
                if isinstance(block, str):
                    text_parts.append(block)
                elif isinstance(block, dict):
                    text_parts.append(block.get("text", ""))
            content = "\n".join(p for p in text_parts if p)

        if not content or not content.strip():
            continue

        # Timestamp handling — normalize all timestamps to ISO 8601 with Z suffix
        ts = msg.get("created_at") or msg.get("timestamp") or msg.get("updated_at")
        if ts:
            if isinstance(ts, (int, float)):
                timestamp = _format_utc(datetime.fromtimestamp(ts, tz=timezone.utc))
            elif isinstance(ts, str):
                # Try to parse and normalize string timestamps
                timestamp = _normalize_timestamp(ts)
            else:
                timestamp = _format_utc(datetime.now(timezone.utc))
        else:
            timestamp = _format_utc(datetime.now(timezone.utc))

        messages.append({
            "role": role,
            "content": content.strip(),
            "timestamp": timestamp
        })

    return messages


def convert_conversation(conversation_data, source_filename=""):
    """
    Convert a single Claude conversation to a UDIF 2.0 document.

    Handles multiple known structures of Claude exports:
    1. Top-level object with "chat_messages" array
    2. Top-level object with "messages" array
    3. Direct array of messages
    """
    # Determine conversation structure
    if isinstance(conversation_data, list):
        chat_messages = conversation_data
        title = source_filename or "Untitled"
        conv_id = str(uuid.uuid4())
        created_at = None
        updated_at = None
    elif isinstance(conversation_data, dict):
        chat_messages = (
            conversation_data.get("chat_messages")
            or conversation_data.get("messages")
            or []
        )
        title = (
            conversation_data.get("name")
            or conversation_data.get("title")
            or source_filename
            or "Untitled"
        )
        conv_id = (
            conversation_data.get("uuid")
            or conversation_data.get("id")
            or str(uuid.uuid4())
        )
        created_at = conversation_data.get("created_at")
        updated_at = conversation_data.get("updated_at")
    else:
        return None

    messages = extract_messages(chat_messages)
    if not messages:
        return None

    # Use first message timestamp as fallback
    if not created_at:
        created_at = messages[0]["timestamp"]
    if not updated_at:
        updated_at = messages[-1]["timestamp"]

    # Try to detect the model from message metadata
    generator = "claude"
    if isinstance(conversation_data, dict):
        model = conversation_data.get("model") or conversation_data.get("default_model")
        if model:
            generator = model

    now = _format_utc(datetime.now(timezone.utc))

    data_event = {
        "type": "chat_interaction",
        "service": "Claude",
        "tags": [],
        "content_title": title,
        "is_shareable": False,
        "messages": messages
    }

    event_hash = sha256_hash(data_event)

    udif_doc = {
        "udif": "2.0",
        "meta": {
            "source": "Claude",
            "generator": generator,
            "session_id": conv_id,
            "timestamp": created_at,
            "consent_granted": True,
            "consent_type": "explicit",
            "data_type": "chat_history"
        },
        "platform": {
            "name": "Anthropic",
            "data_format": "json",
            "source_type": "chat_log",
            "export_date": now,
            "session_reference_id": conv_id
        },
        "data_event": data_event,
        "provenance": {
            "created_at": created_at,
            "updated_at": updated_at,
            "source": "Claude",
            "hash": event_hash,
            "chain": [
                {
                    "platform": "Claude",
                    "exported_at": now,
                    "hash": event_hash
                }
            ]
        }
    }

    return udif_doc


def sanitize_filename(title):
    """Create a safe filename from a conversation title."""
    safe = "".join(c if c.isalnum() or c in (" ", "-", "_") else "_" for c in title)
    return safe.strip()[:80] or "untitled"


def convert_export(input_path, output_dir):
    """
    Convert a Claude data export to UDIF files.

    Args:
        input_path: Path to extracted Claude export directory, or a single JSON file
        output_dir: Directory to write UDIF files to
    """
    os.makedirs(output_dir, exist_ok=True)

    # Collect all JSON files to process
    json_files = []

    if os.path.isfile(input_path):
        json_files = [input_path]
    elif os.path.isdir(input_path):
        # Look for conversation JSON files in the export directory
        # Use recursive glob which also matches root-level files
        json_files = glob.glob(os.path.join(input_path, "**", "*.json"), recursive=True)
    else:
        print(f"Error: {input_path} is not a valid file or directory.")
        sys.exit(1)

    converted = 0
    skipped = 0

    for json_file in json_files:
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError):
            skipped += 1
            continue

        source_name = os.path.splitext(os.path.basename(json_file))[0]

        # Handle file containing a single conversation
        if isinstance(data, dict) and ("chat_messages" in data or "messages" in data):
            conversations = [data]
        # Handle file containing an array of conversations
        elif isinstance(data, list) and len(data) > 0:
            # Check if it's an array of conversations or an array of messages
            if isinstance(data[0], dict) and ("chat_messages" in data[0] or "messages" in data[0] or "title" in data[0]):
                conversations = data
            else:
                # Treat as a single conversation's messages
                conversations = [data]
        else:
            skipped += 1
            continue

        for i, conversation in enumerate(conversations):
            udif_doc = convert_conversation(conversation, source_name)
            if udif_doc is None:
                skipped += 1
                continue

            title = udif_doc["data_event"].get("content_title", "Untitled")
            filename = f"{sanitize_filename(title)}.udif.json"
            output_path = os.path.join(output_dir, filename)

            counter = 1
            while os.path.exists(output_path):
                filename = f"{sanitize_filename(title)}_{counter}.udif.json"
                output_path = os.path.join(output_dir, filename)
                counter += 1

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(udif_doc, f, indent=2, ensure_ascii=False)

            converted += 1

    print(f"Converted {converted} conversations to UDIF 2.0")
    if skipped:
        print(f"Skipped {skipped} items (no extractable messages or parse errors)")
    print(f"Output: {output_dir}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python convert.py <claude-export-path> <output_directory>")
        print()
        print("Convert Claude (Anthropic) data exports to UDIF 2.0 format.")
        print()
        print("Input can be:")
        print("  - A directory containing exported JSON files")
        print("  - A single conversation JSON file")
        print()
        print("To export your Claude data:")
        print("  Settings → Account → Export Data")
        print("  Download and extract the zip file")
        sys.exit(1)

    convert_export(sys.argv[1], sys.argv[2])
