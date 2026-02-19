/**
 * Trust Analysis Type Definitions
 * Defines the data structures for the Judge LLM analysis system
 */

export interface TrustMarker {
  // Epistemic dimension being analyzed
  dimension:
    | "Hedging Language"
    | "Self-Correction / Backtracking"
    | "Knowledge Boundary Admission"
    | "Lack of Specificity"
    | "Unsupported Factual Claim"
    | "Stepwise Reasoning & Internal Consistency";

  // Whether this is an uncertainty or stability marker
  type: "uncertainty" | "stability";

  // Severity level of this marker
  severity: "low" | "medium" | "high";

  // Exact quotes from the assistant's answer that support this finding
  evidence: string[];

  // Explanation of why this indicates the uncertainty type
  interpretation: string;

  // Actionable guidance for the user on how to verify or proceed
  user_guidance: string;
}

export interface TrustAnalysis {
  // Overall uncertainty score (0.0 = high confidence, 1.0 = low confidence)
  overall_uncertainty: number;

  // Confidence traffic light: "green" (high) | "yellow" (medium) | "red" (low)
  confidence_level: "green" | "yellow" | "red";

  // One-sentence summary of the analysis
  summary: string;

  // Array of detected epistemic markers
  markers: TrustMarker[];

  // UI state for loading indicator
  isAnalyzing?: boolean;

  // Error message if analysis failed
  error?: string;
}

/**
 * Internal representation mapping for ChatLayout
 * Converts between backend response and component state
 */
export interface MappedTrustAnalysis {
  // Status mapped from confidence_level
  status: "green" | "yellow" | "red";

  // Score mapped from overall_uncertainty
  score: number;

  // Reasoning mapped from summary
  reasoning: string;

  // Direct pass-through of markers
  markers: TrustMarker[];

  // UI state
  isAnalyzing?: boolean;

  // Error handling
  error?: string;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  reasoning?: string;
  trustAnalysis?: MappedTrustAnalysis;
  isStreaming?: boolean;
}
