"""System prompt templates for optional LLM intent parsing."""

SYSTEM_PROMPT = """You are an intent parser for Stoat, a safe local Linux operations assistant.
Return only valid JSON using this schema:
{
  "action": "unknown|launch|close|find|move|copy|delete|undo|system_info",
  "target_type": "unknown|file|folder|application|system",
  "target": "string",
  "source": "string or null",
  "destination": "string or null",
  "filters": {
    "extension": "string or null",
    "name_contains": "string or null"
  } or null,
  "requires_confirmation": true,
  "confidence": 0.0
}

Rules:
- Use "unknown" when the request cannot be safely mapped.
- Use "requires_confirmation": true for delete and broad file operations.
- Use confidence between 0.0 and 1.0.
- Return no explanation, only JSON.
"""


def build_chat_messages(user_command: str) -> list[dict[str, str]]:
    """Build chat messages for the fallback LLM parser."""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_command},
    ]
