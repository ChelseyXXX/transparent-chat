# Multi-Round Conversation Implementation

## Overview

This document describes the implementation of multi-round conversation functionality for the Transparent Chat project. The system now maintains conversation history and passes it to the DeepSeek API with each request, enabling contextual multi-turn conversations.

## Architecture

The implementation follows the pattern described in the DeepSeek API documentation:

```
User Input (Round 1)
    ↓
[Frontend] Build messages array: [{"role": "user", "content": "..."}]
    ↓
[Backend] Add system prompt + messages → DeepSeek API
    ↓
[DeepSeek] Returns response
    ↓
[Frontend] Store response in conversation history
    ↓
User Input (Round 2)
    ↓
[Frontend] Build messages array: [
    {"role": "user", "content": "Round 1 question"},
    {"role": "assistant", "content": "Round 1 answer"},
    {"role": "user", "content": "Round 2 question"}
]
    ↓
[Backend] Add system prompt + messages → DeepSeek API
    ↓
... (continues for each round)
```

## Implementation Details

### 1. Backend Changes (main.py)

#### Updated Message Model

```python
class Message(BaseModel):
    role: str
    content: str
    persona: Optional[Dict[str, str]] = None
    messages: Optional[list] = None  # NEW: Conversation history for multi-round chat
```

The `messages` field is optional for backward compatibility. When provided, it contains the full conversation history in the format:

```python
[
    {"role": "user", "content": "First question"},
    {"role": "assistant", "content": "First answer"},
    {"role": "user", "content": "Second question"},
    ...
]
```

#### Updated /chat Endpoint

Modified the `/chat` endpoint to use conversation history when available:

```python
# Build messages array for multi-round conversation
if msg.messages:
    # Use provided conversation history
    api_messages = [{"role": "system", "content": system_prompt}] + msg.messages
else:
    # Fallback to single message (backward compatibility)
    api_messages = [
        {"role": "system", "content": system_prompt},
        {"role": msg.role, "content": msg.content}
    ]

# Pass to DeepSeek API
stream = client.chat.completions.create(
    model="deepseek-reasoner",
    messages=api_messages,  # Now includes full history
    ...
)
```

**Benefits:**
- ✅ Backward compatible: Works with or without conversation history
- ✅ Clean separation: System prompt is always prepended
- ✅ Efficient: Only sends necessary context to API

### 2. Frontend Changes

#### Updated backend.js

Modified `sendMessageStreaming` function to accept conversation history:

```javascript
export async function sendMessageStreaming(content, persona, onChunk, messages = null) {
  const payload = {
    role: "user",
    content: content,
  };
  if (persona) payload.persona = persona;
  if (messages) payload.messages = messages;  // NEW: Add conversation history

  // ... rest of the implementation
}
```

#### Updated ChatLayout.jsx

Modified `handleSend` function to build and send conversation history:

```javascript
// Build conversation history for multi-round conversation
const conversationHistory = messages.map(msg => ({
  role: msg.role,
  content: msg.content
}));

// Add current user message to history
conversationHistory.push({
  role: 'user',
  content: userQueryText
});

// Send with full conversation context
await sendMessageStreaming(userQueryText, persona, (type, delta, accumulated) => {
  // ... streaming callback logic
}, conversationHistory);
```

**Key Implementation Details:**
1. **History Building**: Extracts only `role` and `content` from stored messages (excludes UI metadata like `trustAnalysis`, `reasoning`, etc.)
2. **Current Message**: Appends the current user input to the history before sending
3. **Streaming Support**: Full conversation context is maintained even with streaming responses

## Usage Example

### First Round

**User:** "What's the highest mountain in the world?"

**Request to Backend:**
```json
{
  "role": "user",
  "content": "What's the highest mountain in the world?",
  "messages": [
    {"role": "user", "content": "What's the highest mountain in the world?"}
  ]
}
```

**DeepSeek receives:**
```json
{
  "messages": [
    {"role": "system", "content": "You are an intelligent assistant..."},
    {"role": "user", "content": "What's the highest mountain in the world?"}
  ]
}
```

### Second Round (with context)

**User:** "What is the second?"

**Request to Backend:**
```json
{
  "role": "user",
  "content": "What is the second?",
  "messages": [
    {"role": "user", "content": "What's the highest mountain in the world?"},
    {"role": "assistant", "content": "The highest mountain in the world is Mount Everest..."},
    {"role": "user", "content": "What is the second?"}
  ]
}
```

**DeepSeek receives:**
```json
{
  "messages": [
    {"role": "system", "content": "You are an intelligent assistant..."},
    {"role": "user", "content": "What's the highest mountain in the world?"},
    {"role": "assistant", "content": "The highest mountain in the world is Mount Everest..."},
    {"role": "user", "content": "What is the second?"}
  ]
}
```

Now DeepSeek can understand "the second" refers to the second highest mountain!

## Testing

### Manual Testing Steps

1. **Start the backend:**
   ```bash
   cd backend
   python main.py
   ```

2. **Start the frontend:**
   ```bash
   cd frontend/vite-project
   npm run dev
   ```

3. **Test multi-round conversation:**

   **Round 1:**
   - User: "What's the highest mountain in the world?"
   - Expected: Assistant responds with "Mount Everest"

   **Round 2:**
   - User: "What is the second?"
   - Expected: Assistant understands context and responds with "K2" or "Mount K2"

   **Round 3:**
   - User: "How tall is it?"
   - Expected: Assistant understands "it" refers to K2 and provides height

### Verification Points

- ✅ **Context Retention**: Assistant remembers previous conversation
- ✅ **Streaming Works**: Real-time streaming still functions correctly
- ✅ **Trust Analysis**: Per-message trust analysis still works
- ✅ **History Loading**: Conversation history loads correctly on page refresh
- ✅ **Backward Compatibility**: Old API calls without `messages` field still work

## Benefits

1. **Natural Conversations**: Users can ask follow-up questions without repeating context
2. **Contextual Understanding**: AI maintains awareness of previous exchanges
3. **Improved UX**: More human-like conversation flow
4. **Trust Analysis Integration**: Each message still gets individual trust/uncertainty analysis
5. **Backward Compatible**: Existing functionality remains unaffected

## Technical Notes

### Memory Considerations

- **Frontend**: Stores full conversation in React state (`messages` array)
- **Backend**: Stateless - receives history with each request
- **API Costs**: DeepSeek API charges based on token count, including conversation history
- **Optimization**: Only essential fields (`role`, `content`) are sent to reduce payload size

### Limitations

- **No History Truncation**: Currently sends entire conversation history
- **Future Enhancement**: Implement automatic truncation for very long conversations to stay within token limits
- **Session Persistence**: Uses database for history, but multi-round context is session-based

### Future Enhancements

1. **Smart Truncation**: Automatically summarize or truncate old messages to fit token limits
2. **Conversation Branching**: Allow users to fork conversations from specific points
3. **Export Conversations**: Export full conversation history with context
4. **Search Within Context**: Search through conversation history

## Files Modified

### Backend
- `backend/main.py`:
  - Updated `Message` model (line 46-50)
  - Updated `/chat` endpoint (line 177-186)

### Frontend
- `frontend/vite-project/src/api/backend.js`:
  - Updated `sendMessageStreaming` function (line 8-22)

- `frontend/vite-project/src/components/ChatLayout.jsx`:
  - Updated `handleSend` function (line 170-179, 328)

## Compatibility

- ✅ DeepSeek API v1
- ✅ OpenAI-compatible chat completion format
- ✅ Existing trust calibration and analysis features
- ✅ Topic flow tracking
- ✅ Database conversation storage

## Conclusion

The multi-round conversation feature is now fully integrated into the Transparent Chat system. Users can engage in natural, contextual conversations while still benefiting from the trust calibration and epistemic marker analysis features that make Transparent Chat unique.
