#!/usr/bin/env python3
"""
Gemini → UDIF 2.0 Converter

Converts a Google Gemini (formerly Bard) data export into valid UDIF 2.0 files.

Usage:
    python convert.py /path/to/gemini-export/ /path/to/output/

Google exports Gemini data via Google Takeout. The export contains JSON files
with conversation data. Gemini's export format includes conversations with
nested turns containing parts (text, code, etc).

Export your Gemini data:
    Go to takeout.google.com
    Select "Gemini Apps" (or "Bard" for older exports)
    Create export and download the zip
    Extract — conversations are in Gemini Apps/

License: Apache 2.0
"""

import json
import hashlib
import uuid
import sys
import os
import glob
from datetime import datetime, timezone


def sha256_hash(obj):
    """Generate SHA-256 hash of a JSON-serializable object."""
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, default=str).encode()
    ).hexdigest()


def _format_utc(dt):
    """Format a datetime as ISO 8601 with Z suffix."""
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_gemini_timestamp(ts):
    """
    Parse various timestamp formats found in Gemini exports.
    Google Takeout uses multiple formats depending on export version.

    Returns the parsed timestamp string, or None if no timestamp was provided.
    """
    if not ts:
        return None

    if isinstance(ts, (int, float)):
        # Microseconds since epoch
        if ts > 1e15:
            return _format_utc(datetime.fromtimestamp(ts / 1e6, tz=timezone.utc))
        # Milliseconds since epoch
        elif ts > 1e12:
            return _format_utc(datetime.fromtimestamp(ts / 1e3, tz=timezone.utc))
        # Seconds since epoch
        else:
            return _format_utc(datetime.fromtimestamp(ts, tz=timezone.utc))

    if isinstance(ts, str):
        # Try ISO format first
        for fmt in [
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%d %H:%M:%S",
        ]:
            try:
                dt = datetime.strptime(ts, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return _format_utc(dt)
            except ValueError:
                continue
        # If nothing parses, return as-is (may not be valid ISO 8601)
        return None

    return None


def extract_text_from_parts(parts):
    """
    Extract text content from Gemini's parts structure.

    Gemini messages contain 'parts' which can include text, code,
    images, and other content types. We extract text content.
    """
    if not parts:
        return ""

    text_pieces = []
    for part in parts:
        if isinstance(part, str):
            text_pieces.append(part)
        elif isinstance(part, dict):
            # Standard text part
            if "text" in part:
                text_pieces.append(part["text"])
            # Code part
            elif "code" in part:
                text_pieces.append(f"```\n{part['code']}\n```")
            # Executable code
            elif "executableCode" in part:
                code = part["executableCode"]
                lang = code.get("language", "")
                text_pieces.append(f"```{lang}\n{code.get('code', '')}\n```")
            # Code execution result
            elif "codeExecutionResult" in part:
                result = part["codeExecutionResult"]
                text_pieces.append(f"[Output]: {result.get('output', '')}")

    return "\n".join(p for p in text_pieces if p.strip())


def extract_messages_from_conversation(conversation):
    """
    Extract messages from a Gemini conversation export.

    Gemini exports use varying structures:
    1. "turns" array with role and parts
    2. "messages" array
    3. "conversationTurns" array
    """
    messages = []

    # Try different known structures
    turns = (
        conversation.get("turns")
        or conversation.get("conversationTurns")
        or conversation.get("messages")
        or []
    )

    for turn in turns:
        # Determine role (convert to string first to handle integer values)
        role_raw = str(
            turn.get("role")
            or turn.get("author")
            or turn.get("sender")
            or ""
        ).lower()

        if role_raw in ("user", "human", "0"):
            role = "user"
        elif role_raw in ("model", "assistant", "bot", "1"):
            role = "assistant"
        else:
            # Try to infer from structure
            if "userInput" in turn:
                role = "user"
            elif "modelResponse" in turn or "response" in turn:
                role = "assistant"
            else:
                continue

        # Extract content based on structure variant
        if "parts" in turn:
            content = extract_text_from_parts(turn["parts"])
        elif "content" in turn:
            if isinstance(turn["content"], str):
                content = turn["content"]
            elif isinstance(turn["content"], list):
                content = extract_text_from_parts(turn["content"])
            elif isinstance(turn["content"], dict):
                content = extract_text_from_parts(turn["content"].get("parts", []))
            else:
                content = str(turn["content"])
        elif "userInput" in turn:
            inp = turn["userInput"]
            content = inp.get("text", "") if isinstance(inp, dict) else str(inp)
        elif "modelResponse" in turn:
            resp = turn["modelResponse"]
            if isinstance(resp, dict):
                content = extract_text_from_parts(resp.get("parts", []))
            else:
                content = str(resp)
        elif "text" in turn:
            content = turn["text"]
        else:
            continue

        if not content or not content.strip():
            continue

        # Timestamp
        ts = (
            turn.get("createTime")
            or turn.get("timestamp")
            or turn.get("created_at")
        )
        timestamp = parse_gemini_timestamp(ts) or _format_utc(datetime.now(timezone.utc))

        messages.append({
            "role": role,
            "content": content.strip(),
            "timestamp": timestamp
        })

    # Some exports nest user/assistant in paired structures
    if not messages and "conversationTurns" not in conversation:
        # Try paired turn structure
        for turn in turns:
            user_input = turn.get("userInput") or turn.get("request")
            model_response = turn.get("modelResponse") or turn.get("response")

            ts = turn.get("createTime") or turn.get("timestamp")
            timestamp = parse_gemini_timestamp(ts) or _format_utc(datetime.now(timezone.utc))

            if user_input:
                text = user_input if isinstance(user_input, str) else user_input.get("text", "")
                if text.strip():
                    messages.append({
                        "role": "user",
                        "content": text.strip(),
                        "timestamp": timestamp
                    })

            if model_response:
                if isinstance(model_response, str):
                    text = model_response
                elif isinstance(model_response, dict):
                    text = extract_text_from_parts(model_response.get("parts", []))
                elif isinstance(model_response, list):
                    text = extract_text_from_parts(model_response)
                else:
                    text = str(model_response)

                if text.strip():
                    messages.append({
                        "role": "assistant",
                        "content": text.strip(),
                        "timestamp": timestamp
                    })

    return messages


def convert_conversation(conversation, source_filename=""):
    """Convert a single Gemini conversation to a UDIF 2.0 document."""
    title = (
        conversation.get("title")
        or conversation.get("name")
        or conversation.get("conversationTitle")
        or source_filename
        or "Untitled"
    )

    conv_id = (
        conversation.get("id")
        or conversation.get("conversationId")
        or str(uuid.uuid4())
    )

    created_at = parse_gemini_timestamp(
        conversation.get("createTime")
        or conversation.get("created_at")
        or conversation.get("timestamp")
    )
    updated_at = parse_gemini_timestamp(
        conversation.get("updateTime")
        or conversation.get("updated_at")
    )

    messages = extract_messages_from_conversation(conversation)
    if not messages:
        return None

    # Use message timestamps as fallback when no conversation-level timestamp
    if created_at is None:
        created_at = messages[0]["timestamp"]
    if updated_at is None:
        updated_at = messages[-1]["timestamp"]

    # Detect model
    generator = "gemini"
    model = conversation.get("model") or conversation.get("modelVersion")
    if model:
        generator = model

    now = _format_utc(datetime.now(timezone.utc))

    data_event = {
        "type": "chat_interaction",
        "service": "Gemini",
        "tags": [],
        "content_title": title,
        "is_shareable": False,
        "messages": messages
    }

    event_hash = sha256_hash(data_event)

    udif_doc = {
        "udif": "2.0",
        "meta": {
            "source": "Gemini",
            "generator": generator,
            "session_id": conv_id,
            "timestamp": created_at,
            "consent_granted": True,
            "consent_type": "explicit",
            "data_type": "chat_history"
        },
        "platform": {
            "name": "Google",
            "data_format": "json",
            "source_type": "chat_log",
            "export_date": now,
            "session_reference_id": conv_id
        },
        "data_event": data_event,
        "provenance": {
            "created_at": created_at,
            "updated_at": updated_at,
            "source": "Gemini",
            "hash": event_hash,
            "chain": [
                {
                    "platform": "Gemini",
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
    Convert a Gemini/Google Takeout export to UDIF files.

    Args:
        input_path: Path to extracted Takeout directory or single JSON file
        output_dir: Directory to write UDIF files to
    """
    os.makedirs(output_dir, exist_ok=True)

    json_files = []

    if os.path.isfile(input_path):
        json_files = [input_path]
    elif os.path.isdir(input_path):
        # Google Takeout nests under "Gemini Apps/" or "Bard/"
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

        # Determine structure
        if isinstance(data, dict) and any(
            k in data for k in ("turns", "conversationTurns", "messages")
        ):
            conversations = [data]
        elif isinstance(data, list):
            # Check if it's a list of conversations
            if data and isinstance(data[0], dict) and any(
                k in data[0] for k in ("turns", "conversationTurns", "title", "messages")
            ):
                conversations = data
            else:
                conversations = [{"turns": data}]
        else:
            skipped += 1
            continue

        for conversation in conversations:
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
        print("Usage: python convert.py <gemini-export-path> <output_directory>")
        print()
        print("Convert Google Gemini data exports to UDIF 2.0 format.")
        print()
        print("Input can be:")
        print("  - A Google Takeout directory (look for 'Gemini Apps' folder)")
        print("  - A single conversation JSON file")
        print()
        print("To export your Gemini data:")
        print("  Go to takeout.google.com")
        print("  Select 'Gemini Apps' → Create Export → Download")
        print("  Extract the zip file")
        sys.exit(1)

    convert_export(sys.argv[1], sys.argv[2])
