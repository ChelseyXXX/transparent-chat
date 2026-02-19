import axios from "axios";

// Use env-configurable API base URL; default to local dev.
const baseURL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
const api = axios.create({
  baseURL,
});

/**
 * Send message with streaming support
 * @param {string} content - User message
 * @param {object} persona - Persona settings
 * @param {function} onChunk - Callback for each chunk: (type, content, accumulated) => void
 * @param {array} messages - Conversation history (optional)
 * @returns {Promise<object>} Final response data
 */
export async function sendMessageStreaming(content, persona, onChunk, messages = null, userId = null) {
  const payload = {
    role: "user",
    content: content,
  };
  if (persona) payload.persona = persona;
  if (messages) payload.messages = messages;  // Add conversation history
  if (userId) payload.user_id = userId;

  console.log('[backend.js] Sending payload with messages:', messages ? messages.length : 0);

  const response = await fetch(`${baseURL}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  let accumulated_reasoning = "";
  let accumulated_content = "";
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      // Decode chunk
      buffer += decoder.decode(value, { stream: true });

      // Process complete SSE messages
      const lines = buffer.split("\n\n");
      buffer = lines.pop() || ""; // Keep incomplete message in buffer

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const dataStr = line.substring(6);
          try {
            const data = JSON.parse(dataStr);

            if (data.type === "reasoning") {
              accumulated_reasoning = data.accumulated;
              onChunk("reasoning", data.content, accumulated_reasoning);
            } else if (data.type === "content") {
              accumulated_content = data.accumulated;
              onChunk("content", data.content, accumulated_content);
            } else if (data.type === "done") {
              accumulated_reasoning = data.reasoning;
              accumulated_content = data.content;

              // DEBUG: Log received data
              console.log('[backend.js] Received "done" event');
              console.log('[backend.js] - reasoning length:', data.reasoning?.length || 0);
              console.log('[backend.js] - content length:', data.content?.length || 0);
              console.log('[backend.js] - content preview:', data.content?.substring(0, 100));

              onChunk("done", null, {
                reasoning: accumulated_reasoning,
                content: accumulated_content,
                assistantMessageId: data.assistant_message_id,
                userMessageId: data.user_message_id
              });
            } else if (data.type === "error") {
              throw new Error(data.message);
            }
          } catch (e) {
            console.error("Failed to parse SSE data:", e);
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }

  return {
    response: accumulated_content,
    reasoning: accumulated_reasoning,
  };
}

// Legacy non-streaming version (kept for compatibility)
export async function sendMessage(content, persona) {
  const payload = {
    role: "user",
    content: content,
  };
  if (persona) payload.persona = persona;
  const response = await api.post("/chat", payload);
  return response.data;
}

export async function getConversation(userId = null) {
  const response = await api.get("/conversation", {
    params: userId ? { user_id: userId } : undefined,
  });
  // backend returns { messages, topics }
  // return the full object so caller can access both messages and topics
  return response.data;
}

export async function registerUser(payload) {
  const response = await api.post("/register", payload);
  return response.data;
}

export async function loginUser(payload) {
  // If backend adds /login, use it. For now try /login and fall back to /register check
  const response = await api.post("/login", payload).catch((err) => {
    // Re-throw so caller can handle
    throw err;
  });
  return response.data;
}

/**
 * Judge Analysis API - Epistemic Marker Detection
 *
 * Calls the Judge LLM to analyze an assistant response for uncertainty markers.
 * This is an INDEPENDENT analysis that runs asynchronously after the response is displayed.
 *
 * Uses 6 epistemic dimensions:
 * 1. Hedging Language
 * 2. Self-Correction / Backtracking
 * 3. Knowledge Boundary Admission
 * 4. Lack of Specificity
 * 5. Unsupported Factual Claim
 * 6. Stepwise Reasoning & Internal Consistency
 *
 * @param {string} userQuestion - The original user's question
 * @param {string} assistantAnswer - The assistant's response to analyze
 * @param {string} [assistantReasoning] - Optional thinking trace from the assistant
 * @returns {Promise<Object>} TrustAnalysis with structured markers
 *
 * Response format:
 * {
 *   "overall_uncertainty": 0.0-1.0,
 *   "confidence_level": "green" | "yellow" | "red",
 *   "summary": "one-sentence explanation",
 *   "markers": [
 *     {
 *       "dimension": "Hedging Language",
 *       "type": "uncertainty" | "stability",
 *       "severity": "low" | "medium" | "high",
 *       "evidence": ["exact quotes from response"],
 *       "interpretation": "why this indicates uncertainty",
 *       "user_guidance": "actionable verification steps"
 *     }
 *   ]
 * }
 */
export async function analyzeResponse(userQuestion, assistantAnswer, assistantReasoning) {
  const payload = {
    user_question: userQuestion,
    assistant_answer: assistantAnswer,
    assistant_reasoning: assistantReasoning || null
  };

  // Add 60-second timeout (backend has 50s, add 10s buffer)
  const timeoutPromise = new Promise((_, reject) =>
    setTimeout(() => reject(new Error('Judge analysis timeout after 60 seconds')), 60000)
  );

  const apiPromise = api.post("/analyze", payload);

  try {
    const result = await Promise.race([apiPromise, timeoutPromise]);
    console.log('[backend.js analyzeResponse] Success:', result.data);
    return result.data;
  } catch (error) {
    console.error('[backend.js analyzeResponse] Error:', error.message);
    console.error('[backend.js analyzeResponse] Full error:', error);
    throw error;
  }
}

/**
 * Save trust analysis to database for a message
 * @param {string} messageContent - The content of the message to update
 * @param {object} trustAnalysis - The trust analysis object
 * @returns {Promise<object>} Result of the save operation
 */
export async function saveTrustAnalysis(messageId, trustAnalysis, userId = null, messageContent = null) {
  try {
    const response = await api.post("/update-trust-analysis", {
      message_id: messageId,
      message_content: messageContent,
      trust_analysis: trustAnalysis,
      user_id: userId
    });
    console.log('[backend.js saveTrustAnalysis] Success:', response.data);
    return response.data;
  } catch (error) {
    console.error('[backend.js saveTrustAnalysis] Error:', error);
    throw error;
  }
}

// Topic Flow API
export async function getTopicFlow(userId = null) {
  const response = await api.get("/topic-flow", {
    params: userId ? { user_id: userId } : undefined,
  });
  return response.data;
}

export async function updateTopicFlow(forceRecompute = false, userId = null) {
  const params = {};
  if (forceRecompute) params.force_recompute = true;
  if (userId) params.user_id = userId;

  const response = await api.post("/topic-flow/update", null, {
    params: Object.keys(params).length > 0 ? params : undefined,
  });
  return response.data;
}

