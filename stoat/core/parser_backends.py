"""Parser backend implementations for Stoat."""

from __future__ import annotations

from abc import ABC, abstractmethod
import importlib
import json
import re

from stoat.core.intent_schema import (
    FileFilters,
    Intent,
    IntentAction,
    IntentParseError,
    TargetType,
)
from stoat.prompts.system_prompt import build_chat_messages

RECENCY_MARKERS: tuple[tuple[str, int], ...] = (
    ("last month", 31),
    ("this month", 31),
    ("last week", 7),
    ("this week", 7),
    ("recently", 7),
    ("yesterday", 2),
    ("today", 1),
    ("recent", 7),
)

MODIFIED_PHRASES: tuple[str, ...] = ("i last modified", "last modified", "recently modified")

DIRECT_FIND_PATTERN = r"^(?:find|search|locate)\s+(.+)$"

CONVERSATIONAL_FIND_PATTERNS: tuple[str, ...] = (
    r"^(?:i(?:'m| am)?\s+)?(?:looking|searching|trying)\s+for\s+(.+)$",
    r"^(?:i(?:'m| am)?\s+)?finding\s+(.+)$",
    r"^help me find\s+(.+)$",
    r"^look for\s+(.+)$",
    r"^(?:can you\s+)?find\s+me\s+(.+)$",
    r"^where can i find\s+(.+)$",
    r"^where did i save\s+(.+)$",
    r"^(?:can you\s+)?show me\s+(.+)$",
    r"^where(?:'s| is)\s+(.+)$",
    r"^i\s+saved\s+(?:a\s+)?file\s+as\s+(.+?),\s*find\s+it$",
    r"^i\s+saved\s+(?:a\s+)?file\s+as\s+(.+?)\s+find\s+it$",
    r"^i\s+saved\s+(?:a\s+)?file\s+named\s+(.+?),?\s*find\s+it$",
    r"^i\s+saved\s+(?:a\s+)?file\s+called\s+(.+?),?\s*find\s+it$",
)

SOURCE_ALIASES: tuple[tuple[str, str], ...] = (
    ("download", "~/Downloads"),
    ("downloads", "~/Downloads"),
    ("documents", "~/Documents"),
    ("docs", "~/Documents"),
    ("pictures", "~/Pictures"),
    ("photos", "~/Pictures"),
    ("images", "~/Pictures"),
    ("videos", "~/Videos"),
    ("music", "~/Music"),
    ("desktop", "~/Desktop"),
)

SOURCE_CLEANUPS: dict[str, tuple[str, ...]] = {
    "~/Downloads": (r"\bmy\s+latest\s+download\b", r"\bdownloads?\b"),
    "~/Documents": (r"\bmy\s+docs\b", r"\bdocs?\b", r"\bdocuments?\b"),
    "~/Desktop": (r"\bdesktop\b",),
    "~/Pictures": (r"\b(pictures?|photos?|images?)\b",),
    "~/Videos": (r"\bvideos?\b",),
    "~/Music": (r"\bmusic\b",),
}

GENERIC_CLEANUPS: tuple[str, ...] = (
    r"\b(that|the)\b",
    r"\b(i edited|i saved|saved as|named|called|edited|modified|downloaded)\b",
    r"\bmy\b",
    r"^(?:a|an|the)\b",
)

SEMANTIC_ALIASES: dict[str, object | None] = {
    "doc": [".doc", ".docx", ".pdf", ".txt", ".md", ".rtf"],
    "docs": [".doc", ".docx", ".pdf", ".txt", ".md", ".rtf"],
    "document": [".doc", ".docx", ".pdf", ".txt", ".md", ".rtf"],
    "documents": [".doc", ".docx", ".pdf", ".txt", ".md", ".rtf"],
    "pdf": ".pdf",
    "pdfs": ".pdf",
    "image": [".png", ".jpg", ".jpeg", ".webp", ".gif"],
    "images": [".png", ".jpg", ".jpeg", ".webp", ".gif"],
    "photo": [".png", ".jpg", ".jpeg", ".webp", ".gif"],
    "photos": [".png", ".jpg", ".jpeg", ".webp", ".gif"],
    "picture": [".png", ".jpg", ".jpeg", ".webp", ".gif"],
    "pictures": [".png", ".jpg", ".jpeg", ".webp", ".gif"],
    "screenshot": {
        "extensions": [".png", ".jpg", ".jpeg", ".webp", ".gif"],
        "name_contains": "screenshot",
    },
    "screenshots": {
        "extensions": [".png", ".jpg", ".jpeg", ".webp", ".gif"],
        "name_contains": "screenshot",
    },
    "spreadsheet": [".xls", ".xlsx", ".csv", ".ods"],
    "spreadsheets": [".xls", ".xlsx", ".csv", ".ods"],
    "sheet": [".xls", ".xlsx", ".csv", ".ods"],
    "sheets": [".xls", ".xlsx", ".csv", ".ods"],
    "presentation": [".ppt", ".pptx", ".key", ".odp"],
    "presentations": [".ppt", ".pptx", ".key", ".odp"],
    "slide": [".ppt", ".pptx", ".key", ".odp"],
    "slides": [".ppt", ".pptx", ".key", ".odp"],
    "archive": [".zip", ".tar", ".gz", ".rar", ".7z"],
    "archives": [".zip", ".tar", ".gz", ".rar", ".7z"],
    "zip": ".zip",
    "zips": ".zip",
    "video": [".mp4", ".mov", ".mkv", ".avi", ".webm"],
    "videos": [".mp4", ".mov", ".mkv", ".avi", ".webm"],
    "music": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"],
    "audio": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"],
    "file": None,
    "files": None,
    "download": None,
    "downloads": None,
}

SYSTEM_INFO_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"^(?:show|check)\s+disk(?:\s+usage|\s+space)?$", "disk_usage"),
    (r"^disk(?:\s+usage|\s+space)$", "disk_usage"),
    (r"^(?:show\s+)?(?:memory|ram)\s+usage$", "memory_usage"),
    (r"^what(?:'s| is)\s+using(?:\s+all)?\s+my\s+ram$", "memory_usage"),
    (r"^what(?:'s| is)\s+using(?:\s+all)?\s+my\s+memory$", "memory_usage"),
    (r"^(?:show\s+)?battery\s+status$", "battery_status"),
    (r"^what(?:'s| is)\s+my\s+battery(?:\s+status)?$", "battery_status"),
    (r"^how\s+much\s+battery\s+do\s+i\s+have$", "battery_status"),
)


class ParserBackend(ABC):
    """Base parser backend contract."""

    @abstractmethod
    def parse(self, user_command: str) -> Intent | None:
        """Return a parsed intent or None when unavailable."""


def create_llm_backend(provider: str, *, model: str, temperature: float) -> ParserBackend:
    """Create a semantic parser backend for the configured provider."""
    normalized = provider.lower()
    if normalized == "ollama":
        return LLMParserBackend(model=model, temperature=temperature)
    raise ValueError(f"Unsupported LLM provider: {provider}")


class HybridParser:
    """Policy object that prefers deterministic parsing and falls back semantically."""

    def __init__(
        self,
        rule_backend: ParserBackend,
        llm_backend: ParserBackend,
        confidence_threshold: float,
    ) -> None:
        self._rule_backend = rule_backend
        self._llm_backend = llm_backend
        self._confidence_threshold = confidence_threshold

    def parse(self, user_command: str) -> tuple[Intent, Intent | None]:
        """Return the rule intent plus an optional accepted fallback intent."""
        rule_intent = self._rule_backend.parse(user_command) or Intent(
            action=IntentAction.UNKNOWN,
            target="",
            raw_text=user_command,
        )
        if not rule_intent.is_unknown and rule_intent.confidence >= self._confidence_threshold:
            return rule_intent, None

        llm_intent = self._llm_backend.parse(user_command)
        return rule_intent, llm_intent


class RuleParserBackend(ParserBackend):
    """Deterministic parser backend for supported command patterns."""

    def parse(self, user_command: str) -> Intent:
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
            return Intent(
                action=IntentAction.LAUNCH,
                target_type=TargetType.APPLICATION,
                target=self._clean_target_phrase(launch_match.group(1)),
                confidence=0.98,
                raw_text=text,
            )

        close_match = re.match(r"^(?:close|quit|stop)\s+(.+)$", text, flags=re.IGNORECASE)
        if close_match:
            return Intent(
                action=IntentAction.CLOSE,
                target_type=TargetType.APPLICATION,
                target=self._clean_target_phrase(close_match.group(1)),
                requires_confirmation=True,
                confidence=0.97,
                raw_text=text,
            )

        system_info_target = self._parse_system_info_target(text)
        if system_info_target is not None:
            return Intent(
                action=IntentAction.SYSTEM_INFO,
                target_type=TargetType.SYSTEM,
                target=system_info_target,
                confidence=0.96,
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

        for action, verbs in ((IntentAction.MOVE, "move"), (IntentAction.COPY, "copy")):
            pattern = rf"^{verbs}\s+(.+?)(?:\s+from\s+(.+?))?\s+to\s+(.+)$"
            match = re.match(pattern, text, flags=re.IGNORECASE)
            if match:
                return Intent(
                    action=action,
                    target_type=TargetType.FILE,
                    target=self._normalize_file_query(match.group(1)),
                    source=self._clean_target_phrase(match.group(2)) if match.group(2) else None,
                    destination=self._clean_target_phrase(match.group(3)),
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
            return Intent(
                action=IntentAction.DELETE,
                target_type=TargetType.FILE,
                target=self._normalize_file_query(delete_match.group(1)),
                source=(
                    self._clean_target_phrase(delete_match.group(2))
                    if delete_match.group(2)
                    else None
                ),
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

    def _parse_system_info_target(self, text: str) -> str | None:
        for pattern, target in SYSTEM_INFO_PATTERNS:
            if re.match(pattern, text, flags=re.IGNORECASE):
                return target
        return None

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
        direct_match = re.match(DIRECT_FIND_PATTERN, text, flags=re.IGNORECASE)
        if direct_match:
            return direct_match.group(1)

        for pattern in CONVERSATIONAL_FIND_PATTERNS:
            match = re.match(pattern, text, flags=re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def _parse_find_query(self, value: str) -> tuple[str, FileFilters | None, str | None]:
        query = self._clean_target_phrase(value)
        filters = FileFilters()
        source = self._extract_source_alias(query.lower())
        query = self._apply_recency_terms(query, filters)
        query = self._apply_modified_terms(query, filters)
        query, source = self._strip_source_terms(query, source)
        lowered = query.lower()

        if self._apply_semantic_alias(lowered, filters):
            return "*", filters, source

        containing_target = self._extract_containing_target(lowered, filters)
        if containing_target is not None:
            return containing_target, filters, source

        query, extension_target = self._extract_extension_target(query, filters)
        if extension_target is not None:
            return extension_target, filters, source

        normalized = self._normalize_file_query(query)
        return self._finalize_find_result(normalized, filters, source)

    def _extract_source_alias(self, lowered: str) -> str | None:
        for word, path in SOURCE_ALIASES:
            if re.search(rf"\b{word}\b", lowered):
                return path
        return None

    def _strip_source_terms(self, query: str, source: str | None) -> tuple[str, str | None]:
        cleaned = query
        for pattern in SOURCE_CLEANUPS.get(source or "", ()):
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
        for pattern in GENERIC_CLEANUPS:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
        cleaned = self._trim_noise(cleaned)
        if source == "~/Documents" and cleaned in {"", "*"}:
            return "docs", source
        return cleaned or "*", source

    def _apply_recency_terms(self, query: str, filters: FileFilters) -> str:
        lowered = query.lower()
        if any(marker in lowered for marker in ("latest", "newest", "most recent")):
            query = re.sub(r"\b(latest|newest|most recent)\b", "", query, flags=re.IGNORECASE)
            filters.sort_by = "modified"
            filters.descending = True
            filters.limit = 1

        for phrase, days in RECENCY_MARKERS:
            if re.search(rf"\b{re.escape(phrase)}\b", query, flags=re.IGNORECASE):
                query = re.sub(rf"\b{re.escape(phrase)}\b", "", query, flags=re.IGNORECASE)
                filters.sort_by = "modified"
                filters.descending = True
                filters.modified_within_days = days

        return self._clean_target_phrase(query.lower())

    def _apply_modified_terms(self, query: str, filters: FileFilters) -> str:
        for phrase in MODIFIED_PHRASES:
            if phrase in query.lower():
                query = re.sub(rf"\b{re.escape(phrase)}\b", "", query, flags=re.IGNORECASE)
                filters.sort_by = "modified"
                filters.descending = True
        return self._clean_target_phrase(query.lower())

    def _apply_semantic_alias(self, lowered: str, filters: FileFilters) -> bool:
        alias = SEMANTIC_ALIASES.get(lowered)
        if isinstance(alias, list):
            filters.extensions = alias
            return True
        if isinstance(alias, str):
            filters.extension = alias
            return True
        if isinstance(alias, dict):
            alias_extensions = alias.get("extensions")
            alias_name_contains = alias.get("name_contains")
            if isinstance(alias_extensions, list):
                filters.extensions = [str(value) for value in alias_extensions]
            if isinstance(alias_name_contains, str):
                filters.name_contains = alias_name_contains
            return True
        return False

    def _extract_containing_target(self, lowered: str, filters: FileFilters) -> str | None:
        containing_match = re.match(r"^(?:files?\s+)?containing\s+(.+)$", lowered)
        if not containing_match:
            return None
        filters.name_contains = self._trim_noise(
            self._clean_target_phrase(containing_match.group(1))
        )
        return filters.name_contains or "*"

    def _extract_extension_target(
        self,
        query: str,
        filters: FileFilters,
    ) -> tuple[str, str | None]:
        lowered = query.lower()
        extension_match = re.search(r"\b([a-z0-9]+)\s+files?$", lowered)
        if extension_match and extension_match.group(1) not in {"my", "all"}:
            filters.extension = f".{extension_match.group(1)}"
            prefix = lowered[: extension_match.start()].strip()
            if prefix in {"", "all"}:
                return query, "*"
            if prefix.startswith("containing "):
                filters.name_contains = self._trim_noise(
                    self._clean_target_phrase(prefix.removeprefix("containing "))
                )
                return query, filters.name_contains or "*"
            return self._clean_target_phrase(prefix), None

        if re.fullmatch(r"\.[a-z0-9]+", lowered):
            filters.extension = lowered
            return query, "*"

        return query, None

    def _finalize_find_result(
        self,
        normalized: str,
        filters: FileFilters,
        source: str | None,
    ) -> tuple[str, FileFilters | None, str | None]:
        if filters.extension is None and normalized.startswith("*.") and len(normalized) > 2:
            filters.extension = normalized[1:]
            return "*", filters, source
        if normalized != "*" and re.fullmatch(r"[A-Za-z0-9._-]+", normalized):
            filters.name_contains = normalized
        if filters.name_contains or filters.extension or filters.extensions or filters.sort_by:
            return normalized, filters, source
        return normalized, None, source


class LLMParserBackend(ParserBackend):
    """Optional semantic parser backend using an Ollama-compatible runtime."""

    def __init__(self, model: str, temperature: float = 0.1) -> None:
        self.model = model
        self.temperature = temperature

    def parse(self, user_command: str) -> Intent | None:
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
            payload = json.loads(response.message.content.strip())
        except Exception:
            return None

        payload["raw_text"] = user_command
        payload.setdefault(
            "requires_confirmation",
            payload.get("action") in {"delete", "undo"},
        )

        try:
            return Intent(**payload)
        except Exception as exc:
            raise IntentParseError(f"Failed to normalize LLM intent: {exc}") from exc
