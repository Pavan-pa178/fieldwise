from __future__ import annotations
import os
import json
import random
import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class LLMResponse:
    text: str
    confidence: float          # 0.0 - 1.0, used by agents for escalation logic
    raw: Optional[dict] = None # raw provider payload, kept for audit/logging


class LLMClient:



    def __init__(self, mode: Optional[str] = None):
        self.mode = mode or os.environ.get("FIELDWISE_LLM_MODE", "mock")
        if self.mode not in ("mock", "gemini"):
            raise ValueError(f"Unknown LLM mode: {self.mode}")

        if self.mode == "gemini":
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                raise RuntimeError(
                    "FIELDWISE_LLM_MODE=gemini but GEMINI_API_KEY is not set. "
                    "Export it as an environment variable before running — "
                    "never hardcode it in source."
                )
            self._init_gemini(api_key)

    def _init_gemini(self, api_key: str):

        try:
            import google.generativeai as genai
        except ImportError as e:
            raise ImportError(
                "google-generativeai package not installed. "
                "Run: pip install google-generativeai"
            ) from e
        genai.configure(api_key=api_key)
        self._genai = genai
        self._text_model = genai.GenerativeModel("gemini-2.0-flash")
        self._vision_model = genai.GenerativeModel("gemini-2.0-flash")

    # ------------------------------------------------------------------
    # Text generation
    # ------------------------------------------------------------------
    def generate(self, prompt: str, system: Optional[str] = None) -> LLMResponse:
        if self.mode == "mock":
            return self._mock_generate(prompt, system)
        return self._gemini_generate(prompt, system)

    def _gemini_generate(self, prompt: str, system: Optional[str]) -> LLMResponse:
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        response = self._text_model.generate_content(full_prompt)
        return LLMResponse(text=response.text, confidence=0.85, raw=None)

    @staticmethod
    def _keyword_classify(lowered_prompt: str) -> str:

        start_marker = "--- farmer description start ---"
        end_marker = "--- farmer description end ---"
        if start_marker in lowered_prompt and end_marker in lowered_prompt:
            start = lowered_prompt.index(start_marker) + len(start_marker)
            end = lowered_prompt.index(end_marker)
            text_to_score = lowered_prompt[start:end]
        else:
            text_to_score = lowered_prompt

        pest_keywords = ["insect", "aphid", "bug", "larvae", "caterpillar", "sticky", "curl", "chew", "holes"]
        disease_keywords = ["spot", "blight", "mold", "fungus", "fungal", "lesion", "wilt", "rot", "rust", "mildew"]
        nutrient_keywords = ["yellow", "pale", "vein", "stunt", "discolor"]

        scores = {
            "pest": sum(k in text_to_score for k in pest_keywords),
            "disease": sum(k in text_to_score for k in disease_keywords),
            "nutrient_deficiency": sum(k in text_to_score for k in nutrient_keywords),
        }
        best = max(scores, key=scores.get)
        return best if scores[best] > 0 else random.choice(list(scores.keys()))

    @staticmethod
    def _diagnosis_for_category(lowered_prompt: str) -> dict:

        if "category: pest" in lowered_prompt or "diagnose this pest" in lowered_prompt:
            return {
                "diagnosis": "Aphid infestation",
                "explanation": (
                    "Mock diagnosis: clusters of small insects on leaf undersides, "
                    "curling leaves, and sticky honeydew residue are classic signs of aphids."
                ),
            }
        if "category: nutrient_deficiency" in lowered_prompt or "diagnose this nutrient_deficiency" in lowered_prompt:
            return {
                "diagnosis": "Magnesium / Nitrogen deficiency",
                "explanation": (
                    "Mock diagnosis: yellowing between leaf veins, starting with older "
                    "leaves, typically points to a magnesium or nitrogen deficiency."
                ),
            }
        return {
            "diagnosis": "Early blight (Alternaria solani)",
            "explanation": (
                "Mock diagnosis: concentric dark lesions with yellow halos on "
                "lower leaves are characteristic of early blight in tomato/potato."
            ),
        }


    def _mock_generate(self, prompt: str, system: Optional[str]) -> LLMResponse:

        time.sleep(0.05)  # simulate latency so UI spinners feel real
        lowered = prompt.lower()

        if "triage" in lowered or "classify" in lowered:
            category = self._keyword_classify(lowered)
            return LLMResponse(
                text=json.dumps({
                    "category": category,
                    "reasoning": f"Mock triage selected '{category}' based on described symptoms."
                }),
                confidence=round(random.uniform(0.6, 0.92), 2),
            )

        if "diagnos" in lowered:
            diag = self._diagnosis_for_category(lowered)
            return LLMResponse(
                text=json.dumps(diag),
                confidence=round(random.uniform(0.65, 0.92), 2),
            )

        if "follow" in lowered or "schedule" in lowered:
            return LLMResponse(
                text=json.dumps({
                    "next_check_days": 5,
                    "message": "Mock follow-up: re-check affected leaves in 5 days for spread."
                }),
                confidence=0.95,
            )

        return LLMResponse(
            text="Mock response: no specific handler matched this prompt.",
            confidence=0.5,
        )

    # ------------------------------------------------------------------
    # Vision (crop photo) analysis
    # ------------------------------------------------------------------
    def analyze_image(self, image_path: str, prompt: str) -> LLMResponse:

        if self.mode == "mock":
            time.sleep(0.1)
            mock_findings = random.choice([
                {
                    "visible_symptoms": "Dark concentric leaf spots with yellow margins",
                    "likely_category": "disease",
                    "likely_cause": "Early blight (Alternaria solani)",
                },
                {
                    "visible_symptoms": "Curled leaves with sticky residue and tiny insects on undersides",
                    "likely_category": "pest",
                    "likely_cause": "Aphid infestation",
                },
                {
                    "visible_symptoms": "Yellowing between leaf veins, older leaves affected first",
                    "likely_category": "nutrient_deficiency",
                    "likely_cause": "Magnesium or nitrogen deficiency",
                },
            ])
            mock_findings["_mock_notice"] = (
                "MOCK VISION RESULT — image was not actually analyzed. "
                "Set FIELDWISE_LLM_MODE=gemini with a valid GEMINI_API_KEY "
                "to enable real photo analysis."
            )
            return LLMResponse(
                text=json.dumps(mock_findings),
                confidence=round(random.uniform(0.5, 0.88), 2),
            )

        return self._gemini_analyze_image(image_path, prompt)

    def _gemini_analyze_image(self, image_path: str, prompt: str) -> LLMResponse:
        import PIL.Image
        img = PIL.Image.open(image_path)
        response = self._vision_model.generate_content([prompt, img])
        return LLMResponse(text=response.text, confidence=0.8, raw=None)
