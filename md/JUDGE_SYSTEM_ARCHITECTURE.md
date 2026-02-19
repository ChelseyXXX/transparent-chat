# Transparent Judge System - Complete Implementation Guide

## Architecture Overview

```
User Question + Assistant Answer
           ↓
   [Main Chat API - DeepSeek]
           ↓
Assistant Response + Reasoning
           ↓
   [INDEPENDENT Judge Call - DeepSeek]
   (analyzeAnswer function)
           ↓
Structured JSON Analysis
(overall_uncertainty, markers[])
           ↓
Store in message.trustAnalysis
           ↓
Frontend UI: Analysis Report Panel
```

---

## Step 1: Frontend Data Types (TypeScript)

### Create `types/TrustAnalysis.ts`:

```typescript
export interface TrustMarker {
  dimension:
    | "Hedging Language"
    | "Self-Correction / Backtracking"
    | "Knowledge Boundary Admission"
    | "Lack of Specificity"
    | "Unsupported Factual Claim"
    | "Stepwise Reasoning & Internal Consistency";

  type: "uncertainty" | "stability";

  severity: "low" | "medium" | "high";

  // Exact quotes from assistant answer
  evidence: string[];

  // Why this indicates uncertainty
  interpretation: string;

  // What user should do
  user_guidance: string;
}

export interface TrustAnalysis {
  // 0.0 (high confidence) to 1.0 (low confidence)
  overall_uncertainty: number;

  confidence_level: "green" | "yellow" | "red";

  // One-sentence summary
  summary: string;

  // Detailed marker analysis
  markers: TrustMarker[];

  // UI state
  isAnalyzing?: boolean;
  error?: string;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  reasoning?: string;
  trustAnalysis?: TrustAnalysis;
  isStreaming?: boolean;
}
```

---

## Step 2: Backend Judge API Call

### In `main.py`, add new endpoint:

```python
@app.post("/analyze")
async def analyze_response(request: AnalysisRequest):
    """
    Independent Judge API call.
    Analyzes uncertainty markers in assistant's response.

    Args:
        request: AnalysisRequest = {user_question, assistant_answer}

    Returns:
        Structured TrustAnalysis JSON with markers
    """
    try:
        # Call Judge LLM (independent of main chat)
        analysis = await judge_analyze(
            user_question=request.user_question,
            assistant_answer=request.assistant_answer,
            assistant_reasoning=request.assistant_reasoning
        )

        return analysis

    except Exception as e:
        print(f"[ERROR] Judge analysis failed: {e}")
        # Return graceful fallback
        return {
            "overall_uncertainty": 0.5,
            "confidence_level": "yellow",
            "summary": "Analysis unavailable",
            "markers": [],
            "error": str(e)
        }

class AnalysisRequest(BaseModel):
    user_question: str
    assistant_answer: str
    assistant_reasoning: Optional[str] = None
```

### Create `judge_analyze` function:

```python
async def judge_analyze(
    user_question: str,
    assistant_answer: str,
    assistant_reasoning: Optional[str] = None
) -> Dict:
    """
    Call DeepSeek Judge to analyze response.
    Judge uses method-driven epistemic marker detection.
    """

    # Construct prompt for Judge
    judge_input = f"""[ASSISTANT ANSWER TO ANALYZE]
{assistant_answer}

[ORIGINAL QUESTION]
{user_question}
"""

    if assistant_reasoning:
        judge_input += f"\n[ASSISTANT'S THINKING PROCESS]\n{assistant_reasoning}"

    try:
        # Call Judge LLM (independent)
        response = client.chat.completions.create(
            model="deepseek-reasoner",
            messages=[
                {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                {"role": "user", "content": judge_input}
            ],
            temperature=0.0,  # Deterministic evaluation
            max_tokens=1500,
            response_format={"type": "json_object"}
        )

        # Parse JSON response
        result_text = response.choices[0].message.content.strip()
        result = json.loads(result_text)

        # Validate structure
        if validate_judge_response(result):
            print(f"[Judge] Analysis complete: {result['confidence_level']} ({result['overall_uncertainty']:.2f})")
            return result
        else:
            print("[Judge] Invalid response structure")
            return fallback_analysis()

    except Exception as e:
        print(f"[Judge] Error: {e}")
        return fallback_analysis()

def validate_judge_response(result: Dict) -> bool:
    """Validate Judge response structure"""
    required = {"overall_uncertainty", "confidence_level", "summary", "markers"}
    return all(k in result for k in required) and isinstance(result["markers"], list)

def fallback_analysis() -> Dict:
    """Fallback when Judge fails"""
    return {
        "overall_uncertainty": 0.5,
        "confidence_level": "yellow",
        "summary": "Analysis methodology unavailable",
        "markers": []
    }
```

---

## Step 3: Frontend API Call

### Add to `backend.js`:

```typescript
export async function analyzeResponse(
  userQuestion: string,
  assistantAnswer: string,
  assistantReasoning?: string
): Promise<TrustAnalysis> {
  const payload = {
    user_question: userQuestion,
    assistant_answer: assistantAnswer,
    assistant_reasoning: assistantReasoning || null
  };

  const response = await fetch("http://127.0.0.1:8000/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw new Error(`Judge analysis failed: ${response.status}`);
  }

  return await response.json();
}
```

---

## Step 4: ChatLayout Integration

### Modify `handleSend()` to call Judge after response:

```javascript
// After streaming completes...
const response = await sendMessageStreaming(userQueryText, persona, (type, delta, accumulated) => {
  // ... existing streaming logic ...
  if (type === 'done') {
    const content = accumulated.content;
    const reasoning = accumulated.reasoning;

    // STEP: Call Judge independently
    console.log('[ChatLayout] Calling Judge to analyze response...');

    analyzeResponse(userQueryText, content, reasoning)
      .then(trustAnalysis => {
        console.log('[ChatLayout] Judge analysis received:', trustAnalysis);

        // Store analysis in message
        setMessages((prev) =>
          prev.map(m =>
            m.id === msgId
              ? {
                  ...m,
                  content: content,
                  reasoning: reasoning,
                  trustAnalysis: trustAnalysis,  // ← Store structured analysis
                  isStreaming: false
                }
              : m
          )
        );
      })
      .catch(err => {
        console.error('[ChatLayout] Judge analysis failed:', err);
        // Continue anyway, show analysis unavailable
        setMessages((prev) =>
          prev.map(m =>
            m.id === msgId
              ? {
                  ...m,
                  trustAnalysis: {
                    overall_uncertainty: 0.5,
                    confidence_level: "yellow",
                    summary: "Analysis unavailable",
                    markers: [],
                    error: err.message
                  },
                  isStreaming: false
                }
              : m
          )
        );
      });
  }
});
```

---

## Step 5: UI Component - Analysis Report Panel

### Create `components/panels/AnalysisReportPanel.jsx`:

```jsx
export default function AnalysisReportPanel({ trustAnalysis, messageContent }) {
  if (!messageContent) {
    return <div style={{ padding: '24px', color: '#999' }}>No message selected</div>;
  }

  if (!trustAnalysis) {
    return <div style={{ padding: '24px', color: '#999' }}>Analysis not available</div>;
  }

  if (trustAnalysis.isAnalyzing) {
    return (
      <div style={{ padding: '24px', textAlign: 'center' }}>
        <Spinner /> Analyzing Response...
      </div>
    );
  }

  const overallColor =
    trustAnalysis.confidence_level === "green" ? "#4caf50" :
    trustAnalysis.confidence_level === "yellow" ? "#ffc107" :
    "#f44336";

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>

      {/* HEADER: Traffic Light + Summary */}
      <div style={{
        padding: '16px',
        backgroundColor: overallColor + '15',
        borderLeft: `4px solid ${overallColor}`,
        borderRadius: '8px'
      }}>
        <div style={{
          fontSize: '18px',
          fontWeight: '700',
          color: overallColor,
          marginBottom: '8px'
        }}>
          {trustAnalysis.confidence_level.toUpperCase()} CONFIDENCE
        </div>
        <div style={{ fontSize: '13px', color: '#666' }}>
          Overall Uncertainty: {(trustAnalysis.overall_uncertainty * 100).toFixed(0)}%
        </div>
        <div style={{ fontSize: '13px', color: '#555', marginTop: '8px',fontWeight: '500' }}>
          {trustAnalysis.summary}
        </div>
      </div>

      {/* MARKERS SECTION */}
      {trustAnalysis.markers && trustAnalysis.markers.length > 0 && (
        <div>
          <div style={{
            fontSize: '12px',
            fontWeight: '700',
            color: '#6c63ff',
            textTransform: 'uppercase',
            marginBottom: '12px'
          }}>
            📊 Detection Report ({trustAnalysis.markers.length} signal{trustAnalysis.markers.length > 1 ? 's' : ''})
          </div>

          {trustAnalysis.markers.map((marker, idx) => {
            const severityColor =
              marker.severity === "high" ? "#f44336" :
              marker.severity === "medium" ? "#ffc107" :
              "#4caf50";

            const typeBadge = marker.type === "uncertainty" ? "🚨" : "✅";

            return (
              <div key={idx} style={{
                marginBottom: '12px',
                padding: '12px',
                backgroundColor: '#f8f9fc',
                borderLeft: `3px solid ${severityColor}`,
                borderRadius: '6px'
              }}>

                {/* Marker Title */}
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  fontSize: '13px',
                  fontWeight: '600',
                  marginBottom: '8px'
                }}>
                  <span>{typeBadge}</span>
                  <span style={{ color: '#2b2f42' }}>{marker.dimension}</span>
                  <span style={{
                    fontSize: '10px',
                    color: severityColor,
                    fontWeight: '700',
                    textTransform: 'uppercase'
                  }}>
                    {marker.severity}
                  </span>
                </div>

                {/* Evidence Section */}
                {marker.evidence && marker.evidence.length > 0 && (
                  <div style={{ marginBottom: '8px' }}>
                    <div style={{
                      fontSize: '11px',
                      fontWeight: '600',
                      color: '#6c63ff',
                      marginBottom: '4px'
                    }}>
                      Evidence:
                    </div>
                    {marker.evidence.map((quote, i) => (
                      <div key={i} style={{
                        fontSize: '12px',
                        color: '#555',
                        backgroundColor: '#fff',
                        padding: '6px 8px',
                        borderLeft: `2px solid #e0e0e0`,
                        borderRadius: '3px',
                        marginBottom: '4px',
                        fontStyle: 'italic',
                        fontFamily: 'monospace'
                      }}>
                        "{quote}"
                      </div>
                    ))}
                  </div>
                )}

                {/* Interpretation */}
                <div style={{ marginBottom: '8px' }}>
                  <div style={{
                    fontSize: '11px',
                    fontWeight: '600',
                    color: '#6c63ff',
                    marginBottom: '3px'
                  }}>
                    Why it matters:
                  </div>
                  <div style={{
                    fontSize: '12px',
                    color: '#555',
                    lineHeight: '1.5'
                  }}>
                    {marker.interpretation}
                  </div>
                </div>

                {/* User Guidance */}
                <div>
                  <div style={{
                    fontSize: '11px',
                    fontWeight: '600',
                    color: '#2e7d32',
                    marginBottom: '3px'
                  }}>
                    ✓ What you can do:
                  </div>
                  <div style={{
                    fontSize: '12px',
                    color: '#1b5e20',
                    lineHeight: '1.5',
                    backgroundColor: '#e8f5e9',
                    padding: '6px 8px',
                    borderRadius: '3px'
                  }}>
                    {marker.user_guidance}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* NO MARKERS SECTION */}
      {(!trustAnalysis.markers || trustAnalysis.markers.length === 0) && trustAnalysis.confidence_level === "green" && (
        <div style={{
          padding: '16px',
          backgroundColor: '#e8f5e9',
          borderRadius: '8px',
          color: '#2e7d32',
          fontSize: '13px',
          textAlign: 'center'
        }}>
          ✓ No uncertainty markers detected. Response appears reliable.
        </div>
      )}

      {/* FOOTER */}
      <div style={{
        padding: '10px',
        backgroundColor: '#f5f5f5',
        borderRadius: '6px',
        fontSize: '11px',
        color: '#999',
        textAlign: 'center'
      }}>
        This analysis detects uncertainty signals using epistemic marker methodology.
        No fact-checking or external search is performed.
      </div>
    </div>
  );
}
```

---

## Step 6: Update InsightsPanel

Replace the ConfidencePanel with the new AnalysisReportPanel:

```jsx
<AccordionSection title="AI Reliability Analysis" icon="🔍">
  <AnalysisReportPanel
    trustAnalysis={selectedMessage?.trustAnalysis}
    messageContent={selectedMessage?.content}
  />
</AccordionSection>
```

---

## Testing Checklist

- [ ] Judge API call fires after each response (check Network tab)
- [ ] JSON response has correct structure (check Console)
- [ ] Markers display with evidence quotes
- [ ] User guidance is specific and actionable
- [ ] No API calls on message click (instant loading)
- [ ] Severity colors match (green/yellow/red)
- [ ] Works with multi-marker responses

---

## Expected User Experience

**Before clicking a message:**
> Sidebar shows "No message selected"

**After clicking a response with Yellow/Red confidence:**
> Sidebar shows:
>
> ⚠️ YELLOW CONFIDENCE (60% uncertainty)
>
> Response shows multiple hedging statements and some knowledge boundary admission, suggesting moderate certainty on this topic.
>
> **Hedging Language** [MEDIUM]
> Evidence: "probably", "might be", "I think"
> Why it matters: Using uncertain language on key factual claims
> What you can do: Cross-reference with authoritative sources
>
> **Knowledge Boundary Admission** [HIGH]
> Evidence: "My training data doesn't cover 2024"
> Why it matters: Explicit admission of knowledge cutoff
> What you can do: Search for 2024 developments in current news sources

This is **Transparent Chat** at its core: users see HOW and WHY responses are uncertain!

