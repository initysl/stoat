"""Parser orchestration for Stoat."""

from __future__ import annotations

from stoat.core.intent_schema import Intent, IntentAction, LowConfidenceError
from stoat.core.parser_backends import HybridParser, LLMParserBackend, RuleParserBackend


class NLPEngine:
    """Compatibility facade around pluggable parser backends."""

    def __init__(
        self,
        model: str = "llama3.2:3b-instruct-q4_K_M",
        confidence_threshold: float = 0.7,
        temperature: float = 0.1,
        enable_llm_fallback: bool = True,
        parser_mode: str | None = None,
        rule_backend: RuleParserBackend | None = None,
        llm_backend: LLMParserBackend | None = None,
    ) -> None:
        self.model = model
        self.confidence_threshold = confidence_threshold
        self.temperature = temperature
        self.enable_llm_fallback = enable_llm_fallback
        self.parser_mode = parser_mode or ("hybrid" if enable_llm_fallback else "rule")
        self.rule_backend = rule_backend or RuleParserBackend()
        self.llm_backend = llm_backend or LLMParserBackend(
            model=self.model,
            temperature=self.temperature,
        )
        self.hybrid_parser = HybridParser(
            rule_backend=self.rule_backend,
            llm_backend=self.llm_backend,
            confidence_threshold=self.confidence_threshold,
        )

    def parse(self, user_command: str) -> Intent:
        """Parse a natural-language command into a canonical intent."""
        if self.parser_mode == "rule":
            return self._parse_with_rules(user_command)

        if self.parser_mode == "llm":
            return self._parse_llm_only(user_command)

        if self.parser_mode != "hybrid":
            raise ValueError(f"Unsupported parser mode: {self.parser_mode}")

        return self._parse_hybrid(user_command)

    def _parse_hybrid(self, user_command: str) -> Intent:
        rule_intent, llm_intent = self.hybrid_parser.parse(user_command)
        if llm_intent is None:
            return rule_intent
        if llm_intent.confidence < self.confidence_threshold:
            raise LowConfidenceError(llm_intent.confidence, self.confidence_threshold)
        return llm_intent

    def _parse_llm_only(self, user_command: str) -> Intent:
        llm_intent = self._parse_with_llm(user_command)
        if llm_intent is None:
            return Intent(
                action=IntentAction.UNKNOWN,
                target="",
                raw_text=user_command,
            )
        if llm_intent.confidence < self.confidence_threshold:
            raise LowConfidenceError(llm_intent.confidence, self.confidence_threshold)
        return llm_intent

    def parse_intent(self, user_command: str) -> Intent:
        """Backwards-compatible alias for existing callers."""
        return self.parse(user_command)

    def _parse_with_rules(self, user_command: str) -> Intent:
        return self.rule_backend.parse(user_command) or Intent(
            action=IntentAction.UNKNOWN,
            target="",
            raw_text=user_command,
        )

    def _parse_with_llm(self, user_command: str) -> Intent | None:
        return self.llm_backend.parse(user_command)

    def test_connection(self) -> bool:
        """Test whether parsing works for a simple command."""
        intent = self.parse("open firefox")
        return intent.action == IntentAction.LAUNCH
