"""Rule-based NLP parser for MVP command understanding."""

from __future__ import annotations

import re

from stoat.core.intent_schema import Intent, IntentAction


class NLPEngine:
    """Parses natural language text into structured intents."""

    _LAUNCH_RE = re.compile(r"^(?:open|launch|start|run)\s+(.+)$", re.IGNORECASE)
    _CLOSE_RE = re.compile(r"^(?:close|quit|stop)\s+(.+)$", re.IGNORECASE)

    _APP_ALIASES: dict[str, str] = {
        "chrome": "google-chrome",
        "google chrome": "google-chrome",
        "browser": "firefox",
        "vscode": "code",
        "visual studio code": "code",
        "terminal": "gnome-terminal",
        "calendar": "gnome-calendar",
        "calculator": "gnome-calculator",
        "files": "nautilus",
        "file manager": "nautilus",
        "settings": "gnome-control-center",
        "text editor": "gedit",
    }
    _COMMON_TYPOS: dict[str, str] = {
        "calender": "calendar",
        "firefix": "firefox",
        "chorme": "chrome",
    }

    def parse(self, text: str) -> Intent:
        """Parse free text into a known intent."""
        cleaned = " ".join(text.strip().split())
        if not cleaned:
            return Intent(action=IntentAction.UNKNOWN, raw_text=text, confidence=0.0)

        launch_match = self._LAUNCH_RE.match(cleaned)
        if launch_match:
            target = self._normalize_target(launch_match.group(1))
            if target:
                return Intent(
                    action=IntentAction.LAUNCH_APP,
                    raw_text=text,
                    target=target,
                    confidence=0.96,
                )

        close_match = self._CLOSE_RE.match(cleaned)
        if close_match:
            target = self._normalize_target(close_match.group(1))
            if target:
                return Intent(
                    action=IntentAction.CLOSE_APP,
                    raw_text=text,
                    target=target,
                    confidence=0.94,
                    requires_confirmation=True,
                )

        return Intent(action=IntentAction.UNKNOWN, raw_text=text, confidence=0.1)

    def _normalize_target(self, raw_target: str) -> str:
        target = " ".join(raw_target.strip().split())
        if not target:
            return ""

        ignored_tokens = {"app", "application", "window", "windows"}
        filtered_tokens = [token for token in target.split() if token.lower() not in ignored_tokens]
        target = " ".join(filtered_tokens)
        if not target:
            return ""

        alias_key = target.lower().strip()
        alias_key = self._COMMON_TYPOS.get(alias_key, alias_key)
        return self._APP_ALIASES.get(alias_key, target)
