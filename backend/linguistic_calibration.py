"""
Linguistic Calibration Module
Based on Tian et al. (2023) - "LLM-as-a-Judge" Architecture

This module analyzes the reasoning trace (thinking process) of an LLM
to detect linguistic markers of uncertainty and calibrate trust signals.
"""

import json
import os
from typing import Dict, Literal
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# OPTIMIZED JUDGE SYSTEM PROMPT
# Concise version for faster processing
# ============================================================
JUDGE_SYSTEM_PROMPT = """You are an Expert AI Reliability Evaluator. Analyze the assistant's response AND reasoning trace to detect uncertainty markers.

==================================================
6 EPISTEMIC DIMENSIONS
==================================================

UNCERTAINTY MARKERS (detect these):

1. **Hedging Language**: "might", "could", "probably", "likely", "seems", "may", "I think"
   → Signals: Degrees of confidence, not certainty
   → Severity: HIGH if hedging core claims, LOW if hedging minor details

2. **Self-Correction**: "wait", "actually", "let me reconsider", "I was wrong"
   → Signals: Reasoning instability, mid-process error detection
   → Severity: HIGH if correcting core facts, LOW if minor clarifications

3. **Knowledge Gap Admission**: "I don't know", "I'm not sure", "beyond my knowledge", "my training data ends"
   → Signals: Explicit acknowledgment of missing information
   → Severity: HIGH if gap affects core answer

4. **Lack of Specificity**: "some experts", "studies show", "it's complicated" (without details)
   → Signals: Vague claims without concrete facts/citations
   → Severity: HIGH if core claims lack specificity

5. **Unsupported Claim**: Strong factual assertions with NO reasoning/evidence shown
   → Signals: Claims made without derivation
   → Severity: HIGH if claim is controversial or falsifiable

STABILITY MARKER (positive signal):

6. **Stepwise Reasoning**: Numbered steps, logical connectives ("therefore", "because"), consistent terminology
   → Signals: Structured, coherent reasoning
   → Severity: HIGH if rigorous step-by-step derivation

==================================================
OUTPUT FORMAT (JSON ONLY)
==================================================

{
  "overall_uncertainty": <float 0.0-1.0>,
  "confidence_level": "green" | "yellow" | "red",
  "summary": "<one sentence>",
  "markers": [
    {
      "dimension": "<one of the 6 above>",
      "type": "uncertainty" | "stability",
      "severity": "low" | "medium" | "high",
      "evidence": ["<exact verbatim quote>", "<another quote>"],
      "interpretation": "<2-4 sentences: (1) what pattern detected, (2) why it indicates uncertainty/stability, (3) what it reveals about AI knowledge>",
      "user_guidance": "<actionable steps: (1) WHAT to verify, (2) WHERE to check (specific sources), (3) HOW to verify (search terms)>"
    }
  ]
}

==================================================
SCORING
==================================================

- **0.0-0.2 (green)**: No uncertainty OR 1-2 low hedges + strong stability
- **0.3-0.6 (yellow)**: Multiple hedges OR lack of specificity OR minor gaps
- **0.7-1.0 (red)**: Self-correction OR knowledge gap OR high hedging on core claims

==================================================
EXAMPLE
==================================================

User: "What caused the 2008 financial crisis?"
Answer: "Probably caused by subprime mortgages and maybe deregulation. I'm not 100% certain. My training data is limited."

Output:
{
  "overall_uncertainty": 0.75,
  "confidence_level": "red",
  "summary": "High-severity hedging on causal claims plus knowledge gap admission.",
  "markers": [
    {
      "dimension": "Hedging Language",
      "type": "uncertainty",
      "severity": "high",
      "evidence": ["probably caused by", "maybe deregulation", "not 100% certain"],
      "interpretation": "Hedges all core causal factors ('probably', 'maybe'), indicating lack of confident knowledge. Pattern suggests AI encountered competing explanations and can't prioritize. Explicit admission confirms knowledge limits.",
      "user_guidance": "Verify by: (1) Consulting Financial Crisis Inquiry Commission Report (2011), (2) Google Scholar for 'subprime mortgage crisis causation' in econ journals 2009-2015, (3) Federal Reserve housing data."
    },
    {
      "dimension": "Knowledge Boundary Admission",
      "type": "uncertainty",
      "severity": "high",
      "evidence": ["My training data is limited"],
      "interpretation": "Explicit training data limitation. Suggests sparse coverage or conflicting sources. AI lacks internal confidence.",
      "user_guidance": "Access SEC investigation reports, Congressional hearing transcripts (govinfo.gov), economics textbooks post-2012."
    }
  ]
}

==================================================
CRITICAL INSTRUCTIONS
==================================================

1. Quote EXACT text (verbatim) in evidence
2. Analyze BOTH answer AND reasoning trace
3. interpretation: Be specific, explain mechanism, connect to knowledge state
4. user_guidance: Actionable (WHAT, WHERE, HOW), specific sources
5. Prioritize HIGH-IMPACT markers (3-4 max if many detected)
6. Output ONLY valid JSON (no markdown, no extra text)

Begin analysis."""


class LinguisticCalibrator:
    """
    Analyzes reasoning traces using an LLM Judge to detect uncertainty.
    """

    def __init__(self, api_key: str = None, model: str = "gpt-3.5-turbo"):
        """
        Initialize the Judge Agent.

        Args:
            api_key: OpenAI API key (defaults to env variable)
            model: Fast model for evaluation (gpt-3.5-turbo, claude-3-haiku, etc.)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com"
        )

    def evaluate_confidence(self, thinking_process: str) -> Dict:
        """
        [DEPRECATED - Use judge_analyze_response instead]

        This method maintains backward compatibility.
        For new code, use judge_analyze_response() which returns
        structured TrustAnalysis format.
        """
        # Just return a simple fallback for legacy calls
        return {
            "overall_uncertainty": 0.5,
            "confidence_level": "yellow",
            "summary": "Analysis system upgraded. Use judge_analyze_response() for new format.",
            "markers": []
        }

    def judge_analyze_response(
        self,
        user_question: str,
        assistant_answer: str,
        assistant_reasoning: str = ""
    ) -> Dict:
        """
        [PRIMARY METHOD]

        Call Judge LLM to analyze assistant response using epistemic marker methodology.

        Args:
            user_question: Original user question
            assistant_answer: The assistant's final answer
            assistant_reasoning: Optional thinking/reasoning from assistant

        Returns:
            Structured TrustAnalysis with:
            - overall_uncertainty (0.0-1.0)
            - confidence_level (green|yellow|red)
            - summary (one sentence)
            - markers (list of detected uncertainty markers)
        """
        if not assistant_answer or not assistant_answer.strip():
            return self._empty_analysis()

        # Build Judge input
        judge_input = f"""[ASSISTANT ANSWER TO ANALYZE]
{assistant_answer}

[ORIGINAL QUESTION]
{user_question}"""

        if assistant_reasoning and assistant_reasoning.strip():
            judge_input += f"\n\n[ASSISTANT'S REASONING TRACE]\n{assistant_reasoning}"

        # Call DeepSeek Judge
        try:
            print(f"[Judge] Analyzing response (length: {len(assistant_answer)} chars)...")

            response = self.client.chat.completions.create(
                model="deepseek-chat",  # Fast text analysis model
                messages=[
                    {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                    {"role": "user", "content": judge_input}
                ],
                temperature=0.0,  # Deterministic
                max_tokens=2500,  # Reduced (simpler prompt needs less output)
                response_format={"type": "json_object"},
                timeout=50  # 50-second timeout (increased for reliability)
            )

            # Parse response
            result_text = response.choices[0].message.content.strip()
            print(f"[Judge] Received response (length: {len(result_text)} chars)")

            result = json.loads(result_text)

            # Validate structure
            if self._validate_response(result):
                print(f"[Judge] Analysis complete: {result['confidence_level']} ({result['overall_uncertainty']:.2f})")
                return result
            else:
                print("[Judge] Invalid response structure, using fallback")
                return self._empty_analysis()

        except json.JSONDecodeError as e:
            print(f"[Judge] JSON parsing error: {e}")
            print(f"[Judge] Raw response that failed to parse: {result_text[:500]}...")
            import traceback
            traceback.print_exc()
            return self._empty_analysis()
        except Exception as e:
            print(f"[Judge] Error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return self._empty_analysis()

    def _empty_analysis(self) -> Dict:
        """Return empty analysis when Judge unavailable"""
        return {
            "overall_uncertainty": 0.5,
            "confidence_level": "yellow",
            "summary": "Analysis unavailable - Judge API error. Check backend logs for details.",
            "markers": []
        }

    def _validate_response(self, result: Dict) -> bool:
        """Validate the Judge's response structure"""
        required_keys = {"overall_uncertainty", "confidence_level", "summary", "markers"}
        if not all(k in result for k in required_keys):
            return False

        valid_levels = {"green", "yellow", "red"}
        valid_types = {"uncertainty", "stability"}
        valid_severities = {"low", "medium", "high"}

        # Check overall structure
        if result["confidence_level"] not in valid_levels:
            return False

        if not isinstance(result["overall_uncertainty"], (int, float)):
            return False

        if not isinstance(result["markers"], list):
            return False

        # Check marker structure
        for marker in result["markers"]:
            required_marker_keys = {"dimension", "type", "severity", "evidence", "interpretation", "user_guidance"}
            if not all(k in marker for k in required_marker_keys):
                return False

            if marker["type"] not in valid_types:
                return False

            if marker["severity"] not in valid_severities:
                return False

            if not isinstance(marker["evidence"], list):
                return False

        return True

    def _fallback_heuristic(self, thinking_process: str) -> Dict:
        """
        Rule-based fallback for when Judge LLM is unavailable.
        Generates context-specific explanations based on detected markers.
        """
        text = thinking_process.lower()
        original_text = thinking_process  # Keep original for context extraction

        # Check for self-corrections (Red) - with context extraction
        self_corrections = [
            ("wait", "Wait"),
            ("actually", "Actually"),
            ("let me reconsider", "reconsidering"),
            ("on second thought", "second thought"),
            ("i was wrong", "admitting error"),
            ("let me fix", "fixing"),
            ("that's incorrect", "correcting"),
            ("correction", "correction"),
            ("oops", "mistake"),
            ("my mistake", "mistake"),
            ("hold on", "pausing to reconsider")
        ]

        for marker, description in self_corrections:
            if marker in text:
                # Try to extract context around the marker
                marker_pos = text.find(marker)
                context_start = max(0, marker_pos - 50)
                context_end = min(len(text), marker_pos + 100)
                context = original_text[context_start:context_end].strip()

                # Extract topic if possible (look for keywords after marker)
                context_snippet = context[:70] + "..." if len(context) > 70 else context

                return {
                    "confidence_level": "Low",
                    "visual_signal": "red",
                    "analysis_explanation": f"The model corrected itself during reasoning ({description} detected), suggesting initial logic was unstable. Verify the final answer carefully."
                }

        # Check for knowledge gaps (Red) - with context
        knowledge_gaps = [
            ("i don't know", "lacking knowledge"),
            ("i'm not certain", "expressing uncertainty"),
            ("i lack information", "lacking information"),
            ("beyond my knowledge", "knowledge limitation"),
            ("i cannot verify", "inability to verify"),
            ("insufficient data", "insufficient data"),
            ("i'm unsure", "uncertainty"),
            ("i cannot confirm", "inability to confirm"),
            ("not sure", "uncertainty"),
            ("training data ends", "training data cutoff")
        ]

        for marker, description in knowledge_gaps:
            if marker in text:
                # Extract what the model doesn't know about
                marker_pos = text.find(marker)
                context_start = max(0, marker_pos - 30)
                context_end = min(len(text), marker_pos + 80)
                context = original_text[context_start:context_end].strip()

                return {
                    "confidence_level": "Low",
                    "visual_signal": "red",
                    "analysis_explanation": f"The model explicitly stated {description} regarding specific information. Cannot provide reliable answer on this topic."
                }

        # Check for hedging (Yellow) - count and list markers
        hedging_markers = [
            ("might", "might"),
            ("maybe", "maybe"),
            ("possibly", "possibly"),
            ("probably", "probably"),
            ("likely", "likely"),
            ("could", "could"),
            ("may", "may"),
            ("seems", "seems"),
            ("appears", "appears"),
            ("suggest", "suggests"),
            ("assume", "assuming"),
            ("guess", "guessing"),
            ("i think", "thinking")
        ]

        found_hedges = []
        for marker, display in hedging_markers:
            if marker in text:
                found_hedges.append(f"'{display}'")

        if len(found_hedges) >= 2:
            hedge_list = ", ".join(found_hedges[:3])  # Show up to 3
            return {
                "confidence_level": "Medium",
                "visual_signal": "yellow",
                "analysis_explanation": f"The model used hedging language ({hedge_list}) indicating uncertainty about specific claims. Consider verification of key facts."
            }

        # Default: High confidence
        return {
            "confidence_level": "High",
            "visual_signal": "green",
            "analysis_explanation": "The model used direct, step-by-step reasoning with no uncertainty markers detected. Answer appears reliable."
        }


# Export a global instance (lazy-initialized)
calibrator = None


def evaluate_confidence(thinking_process: str) -> Dict:
    """
    [DEPRECATED]
    Legacy function for backward compatibility.
    Use analyze_response() for new structured analysis.
    """
    global calibrator
    if calibrator is None:
        calibrator = LinguisticCalibrator()
    return calibrator.evaluate_confidence(thinking_process)


def analyze_response(
    user_question: str,
    assistant_answer: str,
    assistant_reasoning: str = ""
) -> Dict:
    """
    [PRIMARY EXPORT]

    Analyze an assistant response using Judge LLM.
    Returns structured TrustAnalysis with epistemic markers.

    Args:
        user_question: The original user question
        assistant_answer: The assistant's answer to analyze
        assistant_reasoning: Optional reasoning trace from assistant

    Returns:
        Dict with:
        - overall_uncertainty: float (0.0-1.0)
        - confidence_level: "green" | "yellow" | "red"
        - summary: one-sentence explanation
        - markers: list of TrustMarker objects
    """
    global calibrator
    if calibrator is None:
        calibrator = LinguisticCalibrator()
    return calibrator.judge_analyze_response(
        user_question=user_question,
        assistant_answer=assistant_answer,
        assistant_reasoning=assistant_reasoning
    )
