#!/usr/bin/env python3
"""
ChatGPT → UDIF 2.0 Converter

Converts a ChatGPT data export (conversations.json) into valid UDIF 2.0 files.

Usage:
    python convert.py /path/to/conversations.json /path/to/output/

ChatGPT's export format uses a tree structure where each message links to
its parent and children by UUID. This converter walks the tree from root
to leaf to reconstruct the conversation as the user experienced it.

Export your ChatGPT data:
    Settings → Data Controls → Export Data → Confirm Export
    You'll receive a zip file containing conversations.json

License: Apache 2.0
"""

import json
import hashlib
import uuid
import sys
import os
from datetime import datetime, timezone


def _format_utc(dt):
    """Format a datetime as ISO 8601 with Z suffix."""
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_hash(obj):
    """Generate SHA-256 hash of a JSON-serializable object."""
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, default=str).encode()
    ).hexdigest()


def extract_messages_from_tree(conversation):
    """
    Walk the ChatGPT message tree from current_node back to root,
    then reverse to get chronological order.

    ChatGPT stores conversations as a tree (mapping) where each node
    has a parent pointer. We follow current_node → parent → parent
    until we hit the root, collecting messages along the way.
    """
    messages = []
    current_node = conversation.get("current_node")
    mapping = conversation.get("mapping", {})

    while current_node:
        node = mapping.get(current_node, {})
        message = node.get("message") if node else None

        if message:
            author_role = message.get("author", {}).get("role", "")
            content = message.get("content", {})
            parts = content.get("parts", [])

            # Filter to user and assistant messages with actual content
            if author_role in ("user", "assistant") and parts:
                text_parts = [
                    p for p in parts
                    if isinstance(p, str) and p.strip()
                ]
                if text_parts:
                    create_time = message.get("create_time")
                    timestamp = (
                        _format_utc(datetime.fromtimestamp(create_time, tz=timezone.utc))
                        if create_time
                        else _format_utc(datetime.now(timezone.utc))
                    )
                    messages.append({
                        "role": author_role,
                        "content": "\n".join(text_parts),
                        "timestamp": timestamp
                    })

        current_node = node.get("parent") if node else None

    # Tree walk goes leaf→root, so reverse for chronological order
    return messages[::-1]


def convert_conversation(conversation):
    """Convert a single ChatGPT conversation to a UDIF 2.0 document."""
    title = conversation.get("title", "Untitled")
    create_time = conversation.get("create_time")
    update_time = conversation.get("update_time")

    created_at = (
        _format_utc(datetime.fromtimestamp(create_time, tz=timezone.utc))
        if create_time
        else _format_utc(datetime.now(timezone.utc))
    )
    updated_at = (
        _format_utc(datetime.fromtimestamp(update_time, tz=timezone.utc))
        if update_time
        else created_at
    )

    # Determine the model used
    model_slug = conversation.get("default_model_slug", "")
    mapping = conversation.get("mapping", {})
    for node in mapping.values():
        msg = node.get("message")
        if msg and msg.get("author", {}).get("role") == "assistant":
            meta = msg.get("metadata", {})
            if meta.get("model_slug"):
                model_slug = meta["model_slug"]
                break

    messages = extract_messages_from_tree(conversation)

    if not messages:
        return None

    now = _format_utc(datetime.now(timezone.utc))

    # Build the data_event
    data_event = {
        "type": "chat_interaction",
        "service": "ChatGPT",
        "tags": [],
        "content_title": title,
        "is_shareable": False,
        "messages": messages
    }

    event_hash = sha256_hash(data_event)

    # Build the full UDIF document
    udif_doc = {
        "udif": "2.0",
        "meta": {
            "source": "ChatGPT",
            "generator": model_slug or "unknown",
            "session_id": conversation.get("id", str(uuid.uuid4())),
            "timestamp": created_at,
            "consent_granted": True,
            "consent_type": "explicit",
            "data_type": "chat_history"
        },
        "platform": {
            "name": "OpenAI",
            "data_format": "json",
            "source_type": "chat_log",
            "export_date": now,
            "session_reference_id": conversation.get("id", "")
        },
        "data_event": data_event,
        "provenance": {
            "created_at": created_at,
            "updated_at": updated_at,
            "source": "ChatGPT",
            "hash": event_hash,
            "chain": [
                {
                    "platform": "ChatGPT",
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


def convert_file(input_path, output_dir):
    """
    Convert a ChatGPT conversations.json export to UDIF files.

    Args:
        input_path: Path to conversations.json
        output_dir: Directory to write UDIF files to
    """
    os.makedirs(output_dir, exist_ok=True)

    with open(input_path, "r", encoding="utf-8") as f:
        conversations = json.load(f)

    if not isinstance(conversations, list):
        print("Error: Expected a JSON array of conversations.")
        sys.exit(1)

    converted = 0
    skipped = 0

    for conversation in conversations:
        udif_doc = convert_conversation(conversation)
        if udif_doc is None:
            skipped += 1
            continue

        title = conversation.get("title", "Untitled")
        filename = f"{sanitize_filename(title)}.udif.json"
        output_path = os.path.join(output_dir, filename)

        # Handle duplicate filenames
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
        print(f"Skipped {skipped} conversations (no extractable messages)")
    print(f"Output: {output_dir}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python convert.py <conversations.json> <output_directory>")
        print()
        print("Convert ChatGPT data exports to UDIF 2.0 format.")
        print()
        print("To export your ChatGPT data:")
        print("  Settings → Data Controls → Export Data → Confirm Export")
        print("  Unzip the file and find conversations.json")
        sys.exit(1)

    convert_file(sys.argv[1], sys.argv[2])
