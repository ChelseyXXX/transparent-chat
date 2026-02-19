from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
import traceback
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, constr, Field
from typing import Optional, Dict
import json
from database import save_message, get_conversation, save_user, update_message_trust_analysis, get_user_by_username
from openai import OpenAI
from dotenv import load_dotenv
import os
from passlib.context import CryptContext
from topic_flow_service import TopicFlowService, get_messages_with_ids_from_db
from linguistic_calibration import analyze_response  # ← Judge analysis imported for /analyze endpoint
from persona_service import generate_system_prompt  # ← Persona 3-Role System

# Load API key from .env file
load_dotenv()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# Initialize DeepSeek client
client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)

app = FastAPI()

pwd_context = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")

# Initialize Topic Flow Service
topic_flow_service = TopicFlowService(client)

# CORS configuration - read allowed origins from environment variables, default to local development
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Message(BaseModel):
    role: str
    content: str
    persona: Optional[Dict[str, str]] = None
    messages: Optional[list] = None  # Conversation history for multi-round chat
    user_id: Optional[int] = None

class UserCreate(BaseModel):
    username: constr(min_length=3, max_length=150)
    password: constr(min_length=6, max_length=128)


class LoginRequest(BaseModel):
    username: constr(min_length=3, max_length=150)
    password: constr(min_length=1)


class AnalysisRequest(BaseModel):
    """
    Request payload for Judge analysis endpoint.
    """
    user_question: str = Field(description="The original user question")
    assistant_answer: str = Field(description="The assistant's response to analyze")
    assistant_reasoning: Optional[str] = Field(default=None, description="Optional reasoning trace from the assistant")


class UpdateTrustAnalysisRequest(BaseModel):
    """Request to update trust analysis for a saved message."""
    message_content: str = Field(description="The message content to identify which message to update")
    trust_analysis: Dict = Field(description="The complete trust analysis object to save")
    user_id: Optional[int] = Field(default=None, description="User ID to scope the update")
    message_id: Optional[int] = Field(default=None, description="Message ID to update")


@app.post("/register", status_code=201)
def register(user: UserCreate):
    # Check if user already exists
    existing = get_user_by_username(user.username)
    if existing:
        raise HTTPException(status_code=409, detail="user exists")

    # Hash password and save
    hashed = pwd_context.hash(user.password)
    user_id = save_user(user.username, hashed)
    if not user_id:
        raise HTTPException(status_code=500, detail="could not create user")

    return {"id": user_id, "username": user.username}


@app.post("/chat")
async def chat(msg: Message):
    """
    Streaming chat endpoint with DeepSeek Thinking Mode.
    Returns Server-Sent Events for real-time updates.
    """
    try:
        # Build system prompt from persona using 3-Role System
        persona = msg.persona or {}
        role_id = persona.get('role', 'rational_analyst')  # Default to rational_analyst
        tone = persona.get('tone')
        custom_context = persona.get('personality')

        system_prompt = generate_system_prompt(role_id, tone, custom_context)

        # Log the active persona for verification
        log_msg = f"\n[PERSONA] Role: {role_id}, Tone: {tone}, Custom Context: {bool(custom_context)}\n[SYSTEM_PROMPT_FULL]:\n{system_prompt}\n"
        print(log_msg)
        # Also write to file for debugging
        with open('persona_debug.log', 'a', encoding='utf-8') as f:
            f.write(log_msg)

        async def generate_stream():
            """Generate SSE stream from DeepSeek API"""
            accumulated_reasoning = ""
            accumulated_content = ""

            try:
                # Build messages array for multi-round conversation
                if msg.messages:
                    # Use provided conversation history
                    print(f"[DEBUG /chat] Received conversation history with {len(msg.messages)} messages")
                    for idx, m in enumerate(msg.messages):
                        print(f"  [{idx}] {m.get('role')}: {m.get('content')[:50]}...")
                    api_messages = [{"role": "system", "content": system_prompt}] + msg.messages
                else:
                    # Fallback to single message (backward compatibility)
                    print(f"[DEBUG /chat] No conversation history provided, using single message")
                    api_messages = [
                        {"role": "system", "content": system_prompt},
                        {"role": msg.role, "content": msg.content}
                    ]

                # Use OpenAI SDK streaming
                stream = client.chat.completions.create(
                    model="deepseek-reasoner",
                    messages=api_messages,
                    temperature=0.3,
                    top_p=0.95,
                    max_tokens=8000,  # Increased from 1500 to handle longer reasoning
                    stream=True,
                    extra_body={
                        "thinking": {"type": "enabled"}
                    }
                )

                # Process stream chunks
                chunk_count = 0
                for chunk in stream:
                    chunk_count += 1
                    if chunk.choices and len(chunk.choices) > 0:
                        delta = chunk.choices[0].delta

                        # Extract reasoning delta
                        reasoning_delta = getattr(delta, 'reasoning_content', None) or ''
                        if reasoning_delta:
                            accumulated_reasoning += reasoning_delta
                            data = {
                                "type": "reasoning",
                                "content": reasoning_delta,
                                "accumulated": accumulated_reasoning
                            }
                            yield f"data: {json.dumps(data)}\n\n"

                        # Extract content delta
                        content_delta = getattr(delta, 'content', None) or ''
                        if content_delta:
                            accumulated_content += content_delta
                            data = {
                                "type": "content",
                                "content": content_delta,
                                "accumulated": accumulated_content
                            }
                            yield f"data: {json.dumps(data)}\n\n"

                # Log completion
                print(f"[DEBUG] Stream completed: {chunk_count} chunks, reasoning={len(accumulated_reasoning)} chars, content={len(accumulated_content)} chars")

                # Save messages to database
                user_message_id = save_message(msg.role, msg.content, None, None, user_id=msg.user_id)  # User message has no reasoning

                # Compute confidence
                confidence = compute_confidence_simple(accumulated_content)

                assistant_emotion = {
                    'label': confidence.get('label'),
                    'score': confidence.get('score'),
                    'topic': extract_simple_topic(accumulated_content),
                    'reasoning': accumulated_reasoning[:500] if accumulated_reasoning else ''
                }
                assistant_message_id = save_message('assistant', accumulated_content, assistant_emotion, accumulated_reasoning, user_id=msg.user_id)  # Save full reasoning

                # Send completion signal after persistence
                # Judge analysis will be done asynchronously by frontend
                completion_data = {
                    "type": "done",
                    "reasoning": accumulated_reasoning,
                    "content": accumulated_content,
                    "active_role": role_id,  # ← Show which role was used
                    "active_tone": tone,      # ← Show which tone was used
                    "assistant_message_id": assistant_message_id,
                    "user_message_id": user_message_id,
                }
                print(f"[DEBUG] Sending completion_data: {json.dumps(completion_data)[:200]}...")
                yield f"data: {json.dumps(completion_data)}\n\n"

            except Exception as e:
                error_data = {
                    "type": "error",
                    "message": str(e)
                }
                yield f"data: {json.dumps(error_data)}\n\n"

        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    except Exception as e:
        tb = traceback.format_exc()
        return JSONResponse(
            status_code=500,
            content={"detail": "server error", "debug": str(e), "trace": tb}
        )


def compute_confidence_simple(text: str):
    """Simple confidence heuristic"""
    t = (text or '').lower()
    hedges = ['maybe', 'might', 'could', 'i think', 'possibly', 'perhaps', 'not sure']
    strong = ['definitely', 'certainly', 'absolutely', 'clearly']

    score = 0.6
    word_count = len((text or '').split())
    if word_count < 6:
        score -= 0.2

    for h in hedges:
        if h in t:
            score -= 0.1
    for s in strong:
        if s in t:
            score += 0.1

    score = max(0.0, min(1.0, score))
    label = 'high' if score >= 0.7 else 'medium' if score >= 0.4 else 'low'
    return {'label': label, 'score': round(score, 3)}


def extract_simple_topic(text: str):
    """Extract simple topic from text"""
    import re
    if not text:
        return None
    text = re.sub(r"[\W_]+", ' ', text.lower())
    stopwords = set(["the", "is", "and", "a", "an", "of", "to", "in"])
    words = [w for w in text.split() if len(w) > 3 and w not in stopwords]
    return words[0] if words else None


# Legacy non-streaming endpoint (backup)
@app.post("/chat-legacy")
async def chat_legacy(msg: Message):
    try:
        # Call DeepSeek (OpenAI-compatible client first, then HTTP fallback). Compute a confidence
        # score from the assistant reply (simple heuristic). We no longer compute emotion.
        response_text = None
        exception_msg = None

        # Build system prompt from persona using 3-Role System
        persona = msg.persona or {}
        role_id = persona.get('role', 'rational_analyst')  # Default to rational_analyst
        tone = persona.get('tone')
        custom_context = persona.get('personality')

        system_prompt = generate_system_prompt(role_id, tone, custom_context)
        # Enable thinking mode instructions in the system prompt
        system_prompt = system_prompt + "\n\nBefore answering, think step by step to assess your factual confidence and reasoning certainty."

        # Log the active persona for verification
        log_msg = f"\n[PERSONA] Role: {role_id}, Tone: {tone}, Custom Context: {bool(custom_context)}\n[SYSTEM_PROMPT_FULL]:\n{system_prompt}\n"
        print(log_msg)
        # Also write to file for debugging
        with open('persona_debug.log', 'a', encoding='utf-8') as f:
            f.write(log_msg)

        # helper: extract simple topic keywords from text
        def extract_topics(text, topk=5):
            import re
            if not text:
                return []
            text = re.sub(r"[\W_]+", ' ', text.lower())
            stopwords = set(["the","is","and","a","an","of","to","in","it","that","this","i","you","for","on","with","as","are","be","was","were","by","or","from","at","but"])
            words = [w for w in text.split() if len(w) > 2 and w not in stopwords]
            if not words:
                return []
            freq = {}
            for w in words:
                freq[w] = freq.get(w,0) + 1
            items = sorted(freq.items(), key=lambda x: x[1], reverse=True)
            return [w for w,c in items[:topk]]

        # 1) try OpenAI-compatible client with Thinking Mode enabled
        reasoning_text = None
        try:
            if client is not None:
                resp = client.chat.completions.create(
                    model="deepseek-reasoner",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": msg.role, "content": msg.content}
                    ],
                    temperature=0.3,
                    top_p=0.95,
                    max_tokens=8000,
                    extra_body={
                        "thinking": {"type": "enabled"}
                    }
                )
                # Extract both reasoning_content and content
                response_text = getattr(resp.choices[0].message, 'content', None) or resp.choices[0].message.content
                reasoning_text = getattr(resp.choices[0].message, 'reasoning_content', None)

                if isinstance(response_text, bytes):
                    response_text = response_text.decode('utf-8')
                if isinstance(reasoning_text, bytes):
                    reasoning_text = reasoning_text.decode('utf-8')

                response_text = response_text.strip() if response_text else None
                reasoning_text = reasoning_text.strip() if reasoning_text else None
        except Exception as e:
            exception_msg = f"client error: {e}"

        # 2) HTTP fallback with Thinking Mode enabled
        if not response_text:
            try:
                import requests
                ds_url = "https://api.deepseek.com/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {os.getenv('DEEPSEEK_API_KEY')}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": "deepseek-reasoner",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": msg.role, "content": msg.content}
                    ],
                    "temperature": 0.3,
                    "top_p": 0.95,
                    "max_tokens": 8000,
                    "thinking": {"type": "enabled"}
                }
                r = requests.post(ds_url, json=payload, headers=headers, timeout=30)
                r.raise_for_status()
                jr = r.json()
                if isinstance(jr, dict):
                    choices = jr.get('choices') or []
                    if choices:
                        message = choices[0].get('message') or {}
                        response_text = message.get('content')
                        reasoning_text = message.get('reasoning_content')
                if response_text:
                    response_text = response_text.strip()
                if reasoning_text:
                    reasoning_text = reasoning_text.strip()
            except Exception as e:
                exception_msg = (exception_msg or '') + f"; requests error: {e}"

        # final fallback
        if not response_text:
            response_text = f"Echo: {msg.content}"

        # Compute a simple confidence heuristic based on the assistant reply text
        def compute_confidence(text: str):
            t = (text or '').lower()
            # simple heuristics: penalize fillers and hedges, reward assertive phrases, adjust by length
            hedges = ['maybe', 'might', 'could', 'i think', 'i believe', 'possibly', 'perhaps', 'sort of', 'kind of', 'not sure', 'i guess', 'seems', 'appear']
            fillers = ['um', 'uh', 'hmm', 'hmmm', 'ah', 'er']
            strong = ['definitely', 'certainly', 'of course', 'without a doubt', 'absolutely', 'clearly', 'surely']

            score = 0.6
            word_count = len((text or '').split())
            if word_count < 6:
                score -= 0.2
            elif word_count > 150:
                score -= 0.05

            for h in hedges:
                if h in t:
                    score -= 0.12
            for f in fillers:
                if f in t:
                    score -= 0.18
            for s in strong:
                if s in t:
                    score += 0.12

            score = max(0.0, min(1.0, score))
            if score >= 0.85:
                label = 'high'
            elif score >= 0.5:
                label = 'medium'
            else:
                label = 'low'
            return {'label': label, 'score': round(score, 3)}

        # We'll compute confidence on the cleaned text (after removing metadata/code blocks)
        # but initialize with the raw for now; update after cleaning below
        confidence = compute_confidence(response_text)

        # attempt to parse meta JSON from model reply (if present)
        parsed_meta = {}
        clean_response = response_text
        try:
            import re
            # first try to extract JSON blocks (both bare {} and within markdown code blocks)
            # look for: ```json ... ``` or bare JSON {...}
            json_patterns = [
                r"```json\s*([\s\S]*?)```",  # markdown code block (json)
                r"```\s*([\s\S]*?)```",       # generic code block
                r"\{[\s\S]*?\}",              # bare JSON object
            ]
            
            for pattern in json_patterns:
                candidates = re.findall(pattern, response_text)
                if not candidates:
                    continue
                candidates = sorted(candidates, key=lambda s: -len(s)) if isinstance(candidates[0], str) else candidates
                for cand in candidates:
                    # if it's a tuple/group, take first element
                    if isinstance(cand, tuple):
                        cand = cand[0]
                    cand = cand.strip() if cand else ""
                    if not cand or not cand.startswith('{'):
                        continue
                    try:
                        parsed_meta = json.loads(cand)
                        # remove the full matched block from response (including markdown markers)
                        full_match = re.search(pattern, response_text)
                        if full_match:
                            clean_response = response_text[:full_match.start()] + response_text[full_match.end():]
                        else:
                            clean_response = response_text.replace(cand, '')
                        clean_response = clean_response.strip()
                        break
                    except Exception:
                        # try sanitization
                        s = cand.replace("'", '"')
                        s = re.sub(r",\s*\}(?!,)", "}", s)
                        s = re.sub(r",\s*\]", "]", s)
                        try:
                            parsed_meta = json.loads(s)
                            full_match = re.search(pattern, response_text)
                            if full_match:
                                clean_response = response_text[:full_match.start()] + response_text[full_match.end():]
                            else:
                                clean_response = response_text.replace(cand, '')
                            clean_response = clean_response.strip()
                            break
                        except Exception:
                            continue
                if parsed_meta:
                    break
        except Exception:
            parsed_meta = {}

        # final sanitation: strip any remaining fenced code blocks and stray JSON objects
        try:
            import re
            # remove any ```...``` blocks entirely
            clean_response = re.sub(r"```[\s\S]*?```", "", clean_response).strip()
        except Exception:
            pass

        # recompute confidence on the cleaned text
        confidence = compute_confidence(clean_response)

        # topics: prefer model-provided topic else extract heuristically
        topic = parsed_meta.get('topic') or (extract_topics(clean_response)[:1] or [None])[0]

        # reasoning: prefer DeepSeek thinking mode reasoning_content, fallback to parsed meta
        reasoning = reasoning_text or parsed_meta.get('reasoning') or parsed_meta.get('reason') or ''

        # DEBUG: log topic extraction
        print(f"[DEBUG] parsed_meta={parsed_meta}, extracted_topic={topic}, clean_response_len={len(clean_response)}, reasoning_text_len={len(reasoning_text) if reasoning_text else 0}")

        # save user message (no confidence) and assistant message with confidence
        # save messages; for assistant include confidence and topic/reasoning in the emotion dict so DB can persist topic
        save_message(msg.role, msg.content, None, None, user_id=msg.user_id)  # User message has no reasoning
        assistant_emotion = {'label': confidence.get('label'), 'score': confidence.get('score'), 'topic': topic, 'reasoning': reasoning}
        # save the cleaned assistant response (without metadata/code blocks)
        save_message('assistant', clean_response, assistant_emotion, reasoning, user_id=msg.user_id)  # Save full reasoning

        return {
            'response': clean_response,
            'raw_response': response_text,
            'reasoning': reasoning,  # Use combined reasoning (thinking mode first, then parsed_meta)
            'confidence': confidence,
            'topic': topic,
            'meta': parsed_meta,
            'debug': exception_msg
        }
    except Exception as e:
        tb = traceback.format_exc()
        # Return stack trace in debug for local dev
        return JSONResponse(status_code=500, content={"detail": "server error", "debug": str(e), "trace": tb})


@app.get("/conversation")
async def conversation(user_id: Optional[int] = None):
    msgs = get_conversation(user_id=user_id)
    # include recent topics as well
    try:
        from database import get_recent_topics
        topics = get_recent_topics(7, user_id=user_id)
        print(f"[DEBUG /conversation] Found {len(topics)} topics from DB")
    except Exception as e:
        print(f"[DEBUG /conversation] Error getting topics: {e}")
        topics = []
    
    result = {"messages": msgs, "topics": topics}
    print(f"[DEBUG /conversation] Returning: {len(msgs)} messages, {len(topics)} topics")
    return result


@app.get("/topic-flow")
async def get_topic_flow(user_id: Optional[int] = None):
    """
    Get current Topic Flow visualization data.
    
    Returns hierarchical topic graph in D3-compatible format.
    Does NOT reprocess messages - returns current state.
    """
    try:
        result = topic_flow_service.get_current_topic_flow(user_id)
        return result
    except Exception as e:
        print(f"[ERROR /topic-flow] {e}")
        import traceback
        traceback.print_exc()
        return {"nodes": [], "links": [], "stats": {}}


@app.post("/topic-flow/update")
async def update_topic_flow(force_recompute: bool = False, user_id: Optional[int] = None):
    """
    Update Topic Flow with latest conversation messages.
    
    Query params:
        force_recompute: If true, reprocess ALL messages. Default: false (incremental)
    
    Returns:
        Updated D3 graph data with stats
    """
    try:
        # Fetch all messages with IDs from database
        messages = get_messages_with_ids_from_db(user_id)
        
        # Update topic flow (incremental by default)
        result = topic_flow_service.update_topic_flow(
            messages=messages,
            user_id=user_id,
            force_full_recomputation=force_recompute
        )
        
        print(f"[/topic-flow/update] Processed {result['processed_count']} messages, "
              f"incremental={result['is_incremental']}, "
              f"nodes={len(result['nodes'])}, links={len(result['links'])}")
        
        return result
        
    except Exception as e:
        print(f"[ERROR /topic-flow/update] {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/topic-flow/reset')
async def reset_topic_flow(user_id: Optional[int] = None):
    """
    Clear all topic flow data.

    Use for testing or when conversation is reset.
    """
    try:
        topic_flow_service.reset_topic_flow(user_id)
        return {"status": "success", "message": "Topic flow reset"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# NEW: Judge Analysis Endpoint
# ============================================================

@app.post('/analyze')
async def judge_analyze(request: AnalysisRequest):
    """
    JUDGE ANALYSIS ENDPOINT

    Call the Judge LLM to analyze an assistant response using
    epistemic marker methodology.

    This endpoint processes the response asynchronously and returns
    structured analysis with:
    - overall_uncertainty: float (0.0-1.0)
    - confidence_level: "green" | "yellow" | "red"
    - summary: one-sentence explanation
    - markers: list of detected uncertainty markers

    Args:
        request.user_question: Original user question
        request.assistant_answer: The assistant's response to analyze
        request.assistant_reasoning: Optional thinking trace

    Returns:
        TrustAnalysis JSON with structured marker data
    """
    try:
        print(f"\n[/analyze] Received analysis request")
        print(f"  User question length: {len(request.user_question)} chars")
        print(f"  Assistant answer length: {len(request.assistant_answer)} chars")
        if request.assistant_reasoning:
            print(f"  Reasoning trace length: {len(request.assistant_reasoning)} chars")

        # Call Judge LLM (method-driven epistemic marker analysis)
        print("[/analyze] Calling Judge LLM...")
        analysis = analyze_response(
            user_question=request.user_question,
            assistant_answer=request.assistant_answer,
            assistant_reasoning=request.assistant_reasoning or ""
        )

        print(f"[/analyze] Analysis complete: {analysis['confidence_level']} ({analysis['overall_uncertainty']:.2f})")
        print(f"           Markers detected: {len(analysis.get('markers', []))}")

        # DEBUG: Log marker details
        if analysis.get('markers'):
            for idx, marker in enumerate(analysis['markers'], 1):
                print(f"           Marker {idx}: {marker.get('dimension')} ({marker.get('severity')})")
                print(f"                       Evidence count: {len(marker.get('evidence', []))}")
                print(f"                       Interpretation length: {len(marker.get('interpretation', ''))}")
                print(f"                       Guidance length: {len(marker.get('user_guidance', ''))}")
        else:
            print("           ⚠️ WARNING: No markers in analysis response!")

        return analysis

    except TimeoutError as e:
        print(f"[ERROR /analyze] TIMEOUT: Judge API took too long")
        import traceback
        traceback.print_exc()

        # Return graceful error response with timeout indication
        return {
            "overall_uncertainty": 0.6,
            "confidence_level": "yellow",
            "summary": "Analysis timed out - response appears incomplete or complex",
            "markers": [],
            "error": "timeout"
        }

    except Exception as e:
        print(f"[ERROR /analyze] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

        # Return graceful error response
        return {
            "overall_uncertainty": 0.5,
            "confidence_level": "yellow",
            "summary": "Analysis unavailable due to system error",
            "markers": [],
            "error": str(e)
        }


@app.post('/update-trust-analysis')
async def update_trust_analysis(request: UpdateTrustAnalysisRequest):
    """
    Update the trust analysis for a saved message in the database.
    
    This endpoint is called by the frontend after it receives the Judge analysis
    to persist the analysis results so they survive page refreshes.
    
    Args:
        request.message_content: The content of the message to update
        request.trust_analysis: The complete trust analysis object
        
    Returns:
        Success/failure status
    """
    try:
        print(f"\n[/update-trust-analysis] Updating analysis for message (length: {len(request.message_content)} chars)")
        print(f"  Trust analysis status: {request.trust_analysis.get('status', 'unknown')}")
        print(f"  Trust analysis markers: {len(request.trust_analysis.get('markers', []))}")
        
        success = update_message_trust_analysis(
            request.message_content,
            request.trust_analysis,
            user_id=request.user_id,
            message_id=request.message_id
        )
        
        if success:
            print(f"[/update-trust-analysis] Successfully updated trust analysis")
            return {"success": True, "message": "Trust analysis saved"}
        else:
            print(f"[/update-trust-analysis] Failed to find matching message")
            return {"success": False, "message": "Message not found"}
            
    except Exception as e:
        print(f"[ERROR /update-trust-analysis] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/login')
def login(req: LoginRequest):
    # Find user by username
    existing = get_user_by_username(req.username)
    if not existing:
        raise HTTPException(status_code=401, detail='invalid credentials')

    # Verify password (supports multiple hash schemes)
    if not pwd_context.verify(req.password, existing['password_hash']):
        raise HTTPException(status_code=401, detail='invalid credentials')

    return { 'id': existing['id'], 'username': existing['username'] }


# ============================================================
# PERSONA VERIFICATION ENDPOINT
# ============================================================

@app.post('/verify-persona')
def verify_persona(persona: Dict = None):
    """
    Verify the current persona and get the generated system prompt.

    Use this endpoint to test what system prompt will be sent to the LLM
    based on your selected role, tone, and custom context.

    Args:
        persona: Dict with keys {role, tone, personality}
                Example: {"role": "rational_analyst", "tone": "Friendly", "personality": ""}

    Returns:
        Dict with:
        - role_name: Display name of the role
        - system_prompt: The complete system prompt that will be used
        - role_definition: The base role prompt
        - tone_instruction: The tone instruction (if provided)
    """
    try:
        persona = persona or {}
        role_id = persona.get('role', 'rational_analyst')
        tone = persona.get('tone')
        custom_context = persona.get('personality')

        # Generate the system prompt
        system_prompt = generate_system_prompt(role_id, tone, custom_context)

        # Get role definition and tone instruction for reference
        from persona_service import ROLE_DEFINITIONS, TONE_INSTRUCTIONS, get_role_name

        role_name = get_role_name(role_id)
        role_definition = ROLE_DEFINITIONS.get(role_id, {}).get('prompt', 'Unknown role')
        tone_instruction = TONE_INSTRUCTIONS.get(tone, '') if tone else None

        return {
            'role_id': role_id,
            'role_name': role_name,
            'tone': tone,
            'has_custom_context': bool(custom_context),
            'system_prompt': system_prompt,
            'role_definition': role_definition,
            'tone_instruction': tone_instruction,
        }
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Persona verification failed: {str(e)}"
        )

