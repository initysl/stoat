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

        find_phrase = self._extract_find_phrase(text)
        if find_phrase is not None:
            target, filters, source = self._parse_find_query(find_phrase)
            return Intent(
                action=IntentAction.FIND,
                target_type=TargetType.FILE,
                target=target,
                source=source,
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

    def _trim_noise(self, value: str) -> str:
        cleaned = re.sub(r"\b(from|in|at|on)\s*$", "", value, flags=re.IGNORECASE)
        return re.sub(r"\s+", " ", cleaned).strip(" ,")

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

    def _extract_find_phrase(self, text: str) -> str | None:
        direct_match = re.match(r"^(?:find|search|locate)\s+(.+)$", text, flags=re.IGNORECASE)
        if direct_match:
            return direct_match.group(1)

        conversational_patterns = (
            r"^(?:i(?:'m| am)?\s+)?(?:looking|searching|trying)\s+for\s+(.+)$",
            r"^(?:i(?:'m| am)?\s+)?finding\s+(.+)$",
            r"^(?:can you\s+)?find\s+me\s+(.+)$",
            r"^(?:can you\s+)?show me\s+(.+)$",
            r"^where(?:'s| is)\s+(.+)$",
            r"^i\s+saved\s+(?:a\s+)?file\s+as\s+(.+?),\s*find\s+it$",
            r"^i\s+saved\s+(?:a\s+)?file\s+as\s+(.+?)\s+find\s+it$",
            r"^i\s+saved\s+(?:a\s+)?file\s+named\s+(.+?),?\s*find\s+it$",
            r"^i\s+saved\s+(?:a\s+)?file\s+called\s+(.+?),?\s*find\s+it$",
        )
        for pattern in conversational_patterns:
            match = re.match(pattern, text, flags=re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def _parse_find_query(self, value: str) -> tuple[str, FileFilters | None, str | None]:
        query = self._clean_target_phrase(value)
        lowered = query.lower()
        filters = FileFilters()
        source = self._extract_source_alias(lowered)

        temporal_markers = (
            ("last week", 7),
            ("this week", 7),
            ("recently", 7),
            ("yesterday", 2),
            ("today", 1),
            ("recent", 7),
        )
        for phrase, days in temporal_markers:
            if phrase in lowered:
                lowered = re.sub(rf"\b{re.escape(phrase)}\b", "", lowered).strip()
                query = self._clean_target_phrase(lowered)
                filters.sort_by = "modified"
                filters.descending = True
                filters.modified_within_days = days

        for phrase in ("i last modified", "last modified", "recently modified"):
            if phrase in lowered:
                lowered = lowered.replace(phrase, "").strip()
                query = self._clean_target_phrase(lowered)
                filters.sort_by = "modified"
                filters.descending = True

        if any(marker in lowered for marker in ("latest", "newest", "most recent")):
            lowered = re.sub(r"\b(latest|newest|most recent)\b", "", lowered).strip()
            query = self._clean_target_phrase(lowered)
            filters.sort_by = "modified"
            filters.descending = True
            filters.limit = 1

        query, source = self._strip_source_terms(query, source)
        lowered = query.lower()

        document_aliases = {
            "doc": [".doc", ".docx", ".pdf", ".txt", ".md", ".rtf"],
            "docs": [".doc", ".docx", ".pdf", ".txt", ".md", ".rtf"],
            "document": [".doc", ".docx", ".pdf", ".txt", ".md", ".rtf"],
            "documents": [".doc", ".docx", ".pdf", ".txt", ".md", ".rtf"],
            "file": None,
            "files": None,
            "download": None,
            "downloads": None,
        }

        if lowered in document_aliases and document_aliases[lowered]:
            filters.extensions = document_aliases[lowered]
            return "*", filters, source

        containing_match = re.match(r"^(?:files?\s+)?containing\s+(.+)$", lowered)
        if containing_match:
            filters.name_contains = self._trim_noise(
                self._clean_target_phrase(containing_match.group(1))
            )
            return filters.name_contains or "*", filters, source

        extension_match = re.search(r"\b([a-z0-9]+)\s+files?$", lowered)
        if extension_match and extension_match.group(1) not in {"my", "all"}:
            filters.extension = f".{extension_match.group(1)}"
            prefix = lowered[: extension_match.start()].strip()
            if prefix in {"", "all"}:
                return "*", filters, source
            if prefix.startswith("containing "):
                filters.name_contains = self._clean_target_phrase(
                    prefix.removeprefix("containing ")
                )
                filters.name_contains = self._trim_noise(filters.name_contains or "")
                return filters.name_contains or "*", filters, source
            query = self._clean_target_phrase(prefix)

        if re.fullmatch(r"\.[a-z0-9]+", lowered):
            filters.extension = lowered
            return "*", filters, source

        normalized = self._normalize_file_query(query)
        if filters.extension is None and normalized.startswith("*.") and len(normalized) > 2:
            filters.extension = normalized[1:]
            return "*", filters, source
        if normalized != "*" and re.fullmatch(r"[A-Za-z0-9._-]+", normalized):
            filters.name_contains = normalized
        if filters.name_contains or filters.extension or filters.extensions or filters.sort_by:
            return normalized, filters, source
        return normalized, None, source

    def _extract_source_alias(self, lowered: str) -> str | None:
        aliases = {
            "download": "~/Downloads",
            "downloads": "~/Downloads",
            "documents": "~/Documents",
            "docs": "~/Documents",
            "desktop": "~/Desktop",
        }
        for word, path in aliases.items():
            if re.search(rf"\b{word}\b", lowered):
                return path
        return None

    def _strip_source_terms(self, query: str, source: str | None) -> tuple[str, str | None]:
        cleaned = query
        if source == "~/Downloads":
            cleaned = re.sub(r"\bmy\s+latest\s+download\b", "", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"\bdownloads?\b", "", cleaned, flags=re.IGNORECASE)
        if source == "~/Documents":
            cleaned = re.sub(r"\bmy\s+docs\b", "", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"\bdocs?\b", "", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"\bdocuments?\b", "", cleaned, flags=re.IGNORECASE)
        if source == "~/Desktop":
            cleaned = re.sub(r"\bdesktop\b", "", cleaned, flags=re.IGNORECASE)

        cleaned = re.sub(r"\b(that|the)\b", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(
            r"\b(i edited|i saved|saved as|named|called)\b", "", cleaned, flags=re.IGNORECASE
        )
        cleaned = re.sub(r"\bmy\b", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"^(?:a|an|the)\b", "", cleaned, flags=re.IGNORECASE)
        cleaned = self._trim_noise(cleaned)
        if source == "~/Documents" and cleaned in {"", "*"}:
            return "docs", source
        return cleaned or "*", source
