"""Rule-first NLP engine with optional Ollama fallback."""

from __future__ import annotations

import importlib
import json
import re

from stoat.core.intent_schema import (
    FileFilters,
    Intent,
    IntentAction,
    IntentParseError,
    LowConfidenceError,
    TargetType,
)
from stoat.prompts.system_prompt import build_chat_messages


class NLPEngine:
    """Natural language parser for Stoat commands."""

    def __init__(
        self,
        model: str = "llama3.2:3b-instruct-q4_K_M",
        confidence_threshold: float = 0.7,
        temperature: float = 0.1,
        enable_llm_fallback: bool = True,
    ) -> None:
        self.model = model
        self.confidence_threshold = confidence_threshold
        self.temperature = temperature
        self.enable_llm_fallback = enable_llm_fallback

    def parse(self, user_command: str) -> Intent:
        """Parse a natural-language command into a canonical intent."""
        rule_intent = self._parse_with_rules(user_command)
        if not rule_intent.is_unknown and rule_intent.confidence >= self.confidence_threshold:
            return rule_intent

        if not self.enable_llm_fallback:
            return rule_intent

        llm_intent = self._parse_with_llm(user_command)
        if llm_intent is None:
            return rule_intent
        if llm_intent.confidence < self.confidence_threshold:
            raise LowConfidenceError(llm_intent.confidence, self.confidence_threshold)
        return llm_intent

    def parse_intent(self, user_command: str) -> Intent:
        """Backwards-compatible alias for existing callers."""
        return self.parse(user_command)

    def _parse_with_rules(self, user_command: str) -> Intent:
        text = re.sub(r"\s+", " ", user_command.strip())
        lowered = text.lower()

        if lowered == "undo":
            return Intent(
                action=IntentAction.UNDO,
                target_type=TargetType.FILE,
                target="last_operation",
                requires_confirmation=True,
                confidence=1.0,
                raw_text=text,
            )

        launch_match = re.match(r"^(?:open|launch|start)\s+(.+)$", text, flags=re.IGNORECASE)
        if launch_match:
            target = self._clean_target_phrase(launch_match.group(1))
            return Intent(
                action=IntentAction.LAUNCH,
                target_type=TargetType.APPLICATION,
                target=target,
                confidence=0.98,
                raw_text=text,
            )

        close_match = re.match(r"^(?:close|quit|stop)\s+(.+)$", text, flags=re.IGNORECASE)
        if close_match:
            target = self._clean_target_phrase(close_match.group(1))
            return Intent(
                action=IntentAction.CLOSE,
                target_type=TargetType.APPLICATION,
                target=target,
                requires_confirmation=True,
                confidence=0.97,
                raw_text=text,
            )

        find_match = re.match(r"^(?:find|search|locate)\s+(.+)$", text, flags=re.IGNORECASE)
        if find_match:
            target, filters = self._parse_find_query(find_match.group(1))
            return Intent(
                action=IntentAction.FIND,
                target_type=TargetType.FILE,
                target=target,
                filters=filters,
                confidence=0.95,
                raw_text=text,
            )

        for action, verbs in (
            (IntentAction.MOVE, "move"),
            (IntentAction.COPY, "copy"),
        ):
            pattern = rf"^{verbs}\s+(.+?)(?:\s+from\s+(.+?))?\s+to\s+(.+)$"
            match = re.match(pattern, text, flags=re.IGNORECASE)
            if match:
                target = self._normalize_file_query(match.group(1))
                source = self._clean_target_phrase(match.group(2)) if match.group(2) else None
                destination = self._clean_target_phrase(match.group(3))
                return Intent(
                    action=action,
                    target_type=TargetType.FILE,
                    target=target,
                    source=source,
                    destination=destination,
                    requires_confirmation=action == IntentAction.MOVE,
                    confidence=0.94,
                    raw_text=text,
                )

        delete_match = re.match(
            r"^(?:delete|remove|trash)\s+(.+?)(?:\s+from\s+(.+))?$",
            text,
            flags=re.IGNORECASE,
        )
        if delete_match:
            target = self._normalize_file_query(delete_match.group(1))
            source = (
                self._clean_target_phrase(delete_match.group(2)) if delete_match.group(2) else None
            )
            return Intent(
                action=IntentAction.DELETE,
                target_type=TargetType.FILE,
                target=target,
                source=source,
                requires_confirmation=True,
                confidence=0.93,
                raw_text=text,
            )

        return Intent(
            action=IntentAction.UNKNOWN,
            target_type=TargetType.UNKNOWN,
            target="",
            confidence=0.0,
            raw_text=text,
        )

    def _parse_with_llm(self, user_command: str) -> Intent | None:
        try:
            ollama = importlib.import_module("ollama")
        except ImportError:
            return None

        try:
            messages = build_chat_messages(user_command)
            response = ollama.chat(  # type: ignore[attr-defined]
                model=self.model,
                messages=messages,
                options={"temperature": self.temperature, "num_predict": 256},
                format="json",
            )
            raw_output = response.message.content.strip()
            payload = json.loads(raw_output)
        except Exception:
            return None

        payload["raw_text"] = user_command
        payload.setdefault("requires_confirmation", payload.get("action") in {"delete", "undo"})

        try:
            return Intent(**payload)
        except Exception as exc:
            raise IntentParseError(f"Failed to normalize LLM intent: {exc}") from exc

    def test_connection(self) -> bool:
        """Test whether the optional LLM fallback can parse a simple command."""
        intent = self.parse("open firefox")
        return intent.action == IntentAction.LAUNCH

    def _clean_target_phrase(self, value: str | None) -> str:
        if value is None:
            return ""
        cleaned = value.strip().strip("\"'")
        return re.sub(r"\s+", " ", cleaned)

    def _normalize_file_query(self, value: str) -> str:
        query = self._clean_target_phrase(value)
        lowered = query.lower()

        replacements: dict[str, str] = {
            "all files": "*",
            "everything": "*",
            "all pdfs": "*.pdf",
            "pdfs": "*.pdf",
            "all txt files": "*.txt",
            "text files": "*.txt",
            "all log files": "*.log",
            "logs": "*.log",
        }
        for needle, replacement in replacements.items():
            if lowered == needle:
                return replacement

        if lowered.startswith("my "):
            return query[3:].strip()
        return query

    def _parse_find_query(self, value: str) -> tuple[str, FileFilters | None]:
        query = self._clean_target_phrase(value)
        lowered = query.lower()
        filters = FileFilters()

        containing_match = re.match(r"^(?:files?\s+)?containing\s+(.+)$", lowered)
        if containing_match:
            filters.name_contains = self._clean_target_phrase(containing_match.group(1))
            return filters.name_contains or "*", filters

        extension_match = re.search(r"\b([a-z0-9]+)\s+files?$", lowered)
        if extension_match and extension_match.group(1) not in {"my", "all"}:
            filters.extension = f".{extension_match.group(1)}"
            prefix = lowered[: extension_match.start()].strip()
            if prefix in {"", "all"}:
                return "*", filters
            if prefix.startswith("containing "):
                filters.name_contains = self._clean_target_phrase(
                    prefix.removeprefix("containing ")
                )
                return filters.name_contains or "*", filters
            query = self._clean_target_phrase(prefix)

        if re.fullmatch(r"\.[a-z0-9]+", lowered):
            filters.extension = lowered
            return "*", filters

        normalized = self._normalize_file_query(query)
        if filters.extension is None and normalized.startswith("*.") and len(normalized) > 2:
            filters.extension = normalized[1:]
            return "*", filters
        if filters.name_contains or filters.extension:
            return normalized, filters
        return normalized, None
