# Judge Prompt Engineering Reference

## The Judge System Prompt

This is the **core prompt** that instructs the LLM to analyze reasoning traces for uncertainty.

---

## Full Judge Prompt

```
You are an expert AI reasoning evaluator. Your task is to analyze a language model's
internal reasoning trace (thinking process) and identify linguistic markers of uncertainty.

**Your Goal:**
Assess the confidence level of the reasoning by detecting three categories of uncertainty signals:

1. **Hedging Language** (Epistemic Uncertainty):
   - Words: "might", "maybe", "possibly", "probably", "likely", "could", "may", "seems",
     "appears", "suggest", "assume", "guess", "think"
   - Phrases: "I think", "it seems", "appears to be", "not sure", "unclear"

2. **Self-Correction** (Reasoning Instability):
   - Phrases: "Wait", "Actually", "Let me reconsider", "On second thought", "I was wrong",
     "Let me fix", "That's incorrect", "Correction", "Oops", "My mistake"
   - Pattern: Changing answers mid-reasoning

3. **Knowledge Gaps** (Explicit Uncertainty):
   - Phrases: "I don't know", "I'm not certain", "I lack information", "beyond my knowledge",
     "I cannot verify", "insufficient data", "I'm unsure", "I cannot confirm"
   - Pattern: Admitting limitations

**Evaluation Criteria:**
- **Red (Low Confidence)**: Reasoning contains self-corrections OR explicit knowledge gaps.
  These are CRITICAL signals.
- **Yellow (Medium Confidence)**: Reasoning uses hedging language regarding specific facts,
  numbers, or claims WITHOUT self-correction.
- **Green (High Confidence)**: Reasoning is linear, definitive, step-by-step, with minimal
  hedging and no corrections.

**Output Format:**
You MUST respond with ONLY a valid JSON object (no markdown, no extra text):

{
  "confidence_level": "High" | "Medium" | "Low",
  "visual_signal": "green" | "yellow" | "red",
  "reasoning_summary": "Brief explanation in max 15 words"
}

**Examples:**

Input: "9.11 has two decimal places. So 9.11 > 9.8."
Output: {"confidence_level": "High", "visual_signal": "green",
         "reasoning_summary": "Direct logical reasoning with no uncertainty markers"}

Input: "I think 9.11 might be larger, probably because of the digits."
Output: {"confidence_level": "Medium", "visual_signal": "yellow",
         "reasoning_summary": "Contains hedging: 'think', 'might', 'probably'"}

Input: "Wait, I made an error. Let me recalculate. 9.8 is actually larger."
Output: {"confidence_level": "Low", "visual_signal": "red",
         "reasoning_summary": "Self-correction detected: changed answer mid-reasoning"}

Input: "I don't know the exact conversion rate for this currency."
Output: {"confidence_level": "Low", "visual_signal": "red",
         "reasoning_summary": "Explicit knowledge gap admitted"}

**Important:**
- Prioritize self-corrections and knowledge gaps (always Red)
- Only flag hedging as Yellow if it relates to factual claims
- Ignore hedging in casual language or explanations
- Keep reasoning_summary concise and user-friendly
```

---

## Design Principles

### 1. **Clear Taxonomy**

The prompt defines **three distinct categories** of uncertainty:

| Category | Cognitive Signal | Severity |
|----------|------------------|----------|
| Hedging | Epistemic uncertainty about facts | Medium |
| Self-Correction | Reasoning instability | High |
| Knowledge Gap | Explicit limitation | High |

### 2. **Priority Logic**

The evaluation follows a **waterfall priority**:

```
1. Check for self-corrections → If found: RED
2. Check for knowledge gaps → If found: RED
3. Check for hedging → If found: YELLOW
4. Default: GREEN
```

This ensures critical signals (corrections, gaps) override weaker signals (hedging).

### 3. **Examples-Driven**

The prompt includes **4 concrete examples** covering all scenarios:

- ✅ Green: No uncertainty markers
- 🟡 Yellow: Hedging language
- 🔴 Red (correction): Self-correction detected
- 🔴 Red (gap): Knowledge gap admitted

### 4. **Strict Output Format**

**Requirement:** JSON-only output

**Enforcement:**
1. Explicit instruction: "You MUST respond with ONLY a valid JSON object"
2. OpenAI API parameter: `response_format={"type": "json_object"}`

This prevents the LLM from adding explanatory text outside the JSON.

### 5. **User-Friendly Summary**

**Constraint:** Max 15 words

**Purpose:**
- Display inline in UI badge
- Explain *why* the confidence level was assigned

**Examples:**
- ✅ "Direct logical reasoning with no uncertainty markers"
- ✅ "Self-correction detected: changed answer mid-reasoning"
- ❌ "The model's reasoning trace exhibits multiple hedging phrases including 'might' and 'probably' which suggest epistemic uncertainty" (too long)

---

## Linguistic Markers (Complete List)

### Hedging Language

```python
HEDGING_WORDS = [
    "might", "maybe", "possibly", "probably", "likely",
    "could", "may", "seems", "appears", "suggest",
    "assume", "guess", "I think", "unclear", "not sure"
]
```

**Examples in Context:**
- "The answer is **probably** 42."
- "It **seems** like the data is incomplete."
- "I **assume** the user wants X."

### Self-Correction

```python
SELF_CORRECTION_PHRASES = [
    "wait", "actually", "let me reconsider", "on second thought",
    "I was wrong", "let me fix", "that's incorrect", "correction",
    "oops", "my mistake", "hold on"
]
```

**Examples in Context:**
- "9.11 is greater. **Wait**, let me check again."
- "**On second thought**, I made an error."
- "**That's incorrect** — the answer is different."

### Knowledge Gaps

```python
KNOWLEDGE_GAP_PHRASES = [
    "I don't know", "I'm not certain", "I lack information",
    "beyond my knowledge", "I cannot verify", "insufficient data",
    "I'm unsure", "I cannot confirm", "not sure"
]
```

**Examples in Context:**
- "**I don't know** the current exchange rate."
- "This is **beyond my knowledge** cutoff."
- "**I cannot verify** this claim."

---

## Edge Cases & Handling

### Case 1: Hedging in Explanations (Not Facts)

**Input:**
```
The model probably uses a transformer architecture to generate text.
Let me explain how it might work...
```

**Analysis:**
- Hedging about *how transformers work* (explanation)
- NOT hedging about a specific factual claim

**Output:** 🟢 Green (ignore conversational hedging)

---

### Case 2: Multiple Weak Signals

**Input:**
```
I think the answer could be around 42, maybe 43. It seems reasonable.
```

**Analysis:**
- Contains: "I think", "could", "maybe", "seems"
- 4 hedging markers about the factual answer

**Output:** 🟡 Yellow (cumulative hedging)

---

### Case 3: Self-Correction After Verification

**Input:**
```
Let me calculate: 9.11 vs 9.8. Wait, I need to compare decimals carefully.
9.11 = 9 + 0.11, while 9.8 = 9 + 0.8. So 9.8 is larger.
```

**Analysis:**
- "Wait" signals reconsideration
- But then reasoning becomes definitive
- This is **verification**, not error correction

**Output:** 🟡 Yellow (cautious but correct)

**Note:** This is a judgment call. The current prompt would flag "Wait" as Red.
You may tune the prompt to distinguish:
- "Wait, I was wrong" → Red (error)
- "Wait, let me verify" → Yellow (caution)

---

### Case 4: No Reasoning Trace Available

**Input:** (empty or None)

**Fallback Response:**
```json
{
  "confidence_level": "Medium",
  "visual_signal": "yellow",
  "reasoning_summary": "No reasoning trace available"
}
```

---

## Tuning the Prompt

### To Reduce False Positives (Too Many Reds)

**Problem:** "Wait" in verification is flagged as Red

**Solution:** Refine self-correction detection

```diff
2. **Self-Correction** (Reasoning Instability):
-  - Phrases: "Wait", "Actually", ...
+  - Phrases: "Wait, I was wrong", "Actually, that's incorrect", ...
+  - Pattern: Changing from one answer to a DIFFERENT answer
```

### To Increase Sensitivity (Catch More Yellows)

**Problem:** Missing subtle hedging

**Solution:** Lower threshold for hedging

```diff
- **Yellow (Medium Confidence)**: Reasoning uses hedging language regarding specific facts
+ **Yellow (Medium Confidence)**: Reasoning uses hedging language (1+ markers) regarding specific facts
```

### To Handle Multi-Language Reasoning

**Problem:** Chinese reasoning traces use different markers

**Solution:** Add language-specific examples

```python
# Chinese hedging: "可能", "大概", "也许"
# Spanish hedging: "quizás", "tal vez", "probablemente"
```

---

## Testing Checklist

Use these test cases to validate the Judge prompt:

| Test Reasoning Trace | Expected Signal | Expected Summary |
|---------------------|-----------------|------------------|
| "2 + 2 = 4." | 🟢 Green | "Direct calculation" |
| "I think it's 4, probably." | 🟡 Yellow | "Contains hedging" |
| "Wait, I meant 5, not 4." | 🔴 Red | "Self-correction detected" |
| "I don't know the answer." | 🔴 Red | "Knowledge gap admitted" |
| "Maybe around 4, seems right." | 🟡 Yellow | "Multiple hedging markers" |

---

## Temperature Setting

**Recommendation:** `temperature=0.0`

**Reason:**
- Judge evaluation should be deterministic
- Same reasoning → same calibration
- Avoids random variation in signals

---

## Alternative Models

### GPT-3.5-turbo (Default)
- **Cost:** $0.0015 / 1K tokens
- **Speed:** ~500ms
- **Accuracy:** Good for simple cases

### GPT-4o-mini
- **Cost:** $0.00015 / 1K tokens (10× cheaper!)
- **Speed:** ~600ms
- **Accuracy:** Better at edge cases

### Claude 3 Haiku
- **Cost:** $0.00025 / 1K tokens
- **Speed:** ~400ms
- **Accuracy:** Excellent at linguistic nuance

**Switch in code:**
```python
calibrator = LinguisticCalibrator(model="claude-3-haiku-20240307")
```

---

## Validation Metrics

To measure Judge accuracy, use these metrics:

1. **Precision:** % of Red signals that are truly critical
2. **Recall:** % of critical issues caught by Judge
3. **User Agreement:** % of users who agree with calibration

**Target:**
- Precision > 85%
- Recall > 90%
- User Agreement > 75%

---

## Summary

The Judge Prompt uses:

✅ **Clear taxonomy** of 3 uncertainty types
✅ **Priority logic** (corrections > gaps > hedging)
✅ **Concrete examples** covering all scenarios
✅ **Strict JSON output** enforcement
✅ **User-friendly summaries** (max 15 words)
✅ **Fallback heuristic** when Judge unavailable

**Result:** A reliable, fast, and cost-effective confidence calibration system.
