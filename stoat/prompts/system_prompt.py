"""System prompts for the LLM"""

SYSTEM_PROMPT = """Parse command to JSON.
Format: {"action":"launch|close|find|move|copy|delete","target_type":"file|application","target":"name","source":null,"destination":null,"new_name":null,"filters":null,"confirmation_required":false,"confidence":0.9,"raw_query":"text"}

Command:"""


def build_prompt(user_command: str) -> str:
    """Build the complete prompt for the LLM"""
    return f"{SYSTEM_PROMPT} {user_command}\nJSON:"