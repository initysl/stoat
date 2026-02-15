import json
import re
from pathlib import Path
from typing import Optional
from llama_cpp import Llama

from stoat.core.intent_schema import Intent, IntentParseError, LowConfidenceError
from stoat.prompts.system_prompt import build_prompt


class NLPEngine:
    """Natural Language Processing engine for intent parsing"""
    
    def __init__(
        self,
        model_path: Optional[Path] = None,
        confidence_threshold: float = 0.7,
        temperature: float = 0.1,
        max_tokens: int = 512,
    ):
        """
        Initialize the NLP engine
        Args:
            model_path: Path to the GGUF model file
            confidence_threshold: Minimum confidence score to accept
            temperature: LLM temperature (lower = more deterministic)
            max_tokens: Maximum tokens to generate
        """
        if model_path is None:
            # Default to models directory in project root
            project_root = Path(__file__).parent.parent.parent
            model_path = project_root / "models" / "Llama-3.2-3B-Instruct-Q4_K_M.gguf"
        
        if not model_path.exists():
            raise FileNotFoundError(
                f"Model file not found at {model_path}\n"
                f"Download it with:\n"
                f"wget https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf"
            )
        
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Initialize the model
        print(f"Loading model from {model_path}...")
        self.llm = Llama(
            model_path=str(model_path),
            n_ctx=1024,          # Increased from 512
            n_threads=2,
            n_batch=128,
            verbose=False,       # Turn off verbose now
        )
        print("Model loaded successfully!")
    
    def parse_intent(self, user_command: str) -> Intent:
        """
        Parse user command into structured intent
        Args:
            user_command: Natural language command from user
        Returns:
            Intent object with parsed information
        Raises:
            IntentParseError: If parsing fails
            LowConfidenceError: If confidence is below threshold
        """
        # Build the prompt
        prompt = build_prompt(user_command)
        
        # Get response from LLM
        response = self.llm(
            prompt,
            max_tokens=256,      # Reduced from 512
            temperature=0.1,
            stop=["User:", "\n\n", "}"],  # Add } to stop after JSON
            echo=False,
        )
        
        # Extract the generated text
        raw_output = response["choices"][0]["text"].strip() # type: ignore
        
        # Parse JSON from response
        try:
            intent_data = self._extract_json(raw_output)
            intent = Intent(**intent_data)
        except (json.JSONDecodeError, ValueError) as e:
            raise IntentParseError(f"Failed to parse intent: {e}\nRaw output: {raw_output}")
        
        # Check confidence threshold
        if intent.confidence < self.confidence_threshold:
            raise LowConfidenceError(intent.confidence, self.confidence_threshold)
        
        return intent
    
    def _extract_json(self, text: str) -> dict:
        """
        Extract JSON from LLM response, handling common issues
        Args:
            text: Raw text from LLM
        Returns:
            Parsed JSON dictionary
        """
        # Try direct JSON parse first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # Try to extract JSON from markdown code blocks
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))
        
        # Try to find JSON object in text
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
        
        raise ValueError(f"No valid JSON found in response: {text}")
    
    def test_connection(self) -> bool:
        """Test if the model is working"""
        try:
            test_intent = self.parse_intent("open firefox")
            return test_intent.action == "launch" and "firefox" in test_intent.target.lower()
        except Exception as e:
            print(f"Test failed: {e}")
            return False


# Singleton instance
_engine: Optional[NLPEngine] = None


def get_engine() -> NLPEngine:
    """Get or create the global NLP engine instance"""
    global _engine
    if _engine is None:
        _engine = NLPEngine()
    return _engine