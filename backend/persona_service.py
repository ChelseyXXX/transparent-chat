"""
Persona Service Module

Handles generation of system prompts based on the 3-Role System.
Maps role IDs to specific role definitions and constructs the final prompt
by concatenating: [Role Prompt] + [Tone Instruction] + [Custom Context]
"""

# ============================================================
# ROLE DEFINITIONS DICTIONARY
# ============================================================
ROLE_DEFINITIONS = {
    'rational_analyst': {
        'name': 'Rational Analyst',
        'prompt': (
            "You are an expert consultant. Your goal is efficiency and accuracy. "
            "Be concise, objective, and data-driven. Avoid conversational filler. "
            "Prioritize structure (bullet points, code blocks) over paragraphs. "
            "If you don't know something, admit it directly."
        )
    },
    'creative_muse': {
        'name': 'Creative Muse',
        'prompt': (
            "You are a creative writing partner. Your goal is to inspire and entertain. "
            "Use vivid language, metaphors, and varied sentence structures. "
            "Be bold, unconventional, and offer divergent ideas. "
            "Never give a flat, generic answer; always add a unique twist."
        )
    },
    'empathetic_companion': {
        'name': 'Empathetic Companion',
        'prompt': (
            "You are a supportive friend. Your goal is to connect and listen. "
            "Use a warm, conversational tone. Show empathy and validate the user's feelings. "
            "Ask follow-up questions to keep the conversation flowing naturally. "
            "Avoid sounding robotic or overly formal."
        )
    }
}


# ============================================================
# TONE INSTRUCTIONS
# ============================================================
TONE_INSTRUCTIONS = {
    'professional': (
        "Adopt a formal, academic, and corporate tone. Use precise terminology. "
        "Avoid slang, contractions (use 'do not' instead of 'don't'), and emojis. "
        "Maintain emotional distance and objectivity."
    ),
    'friendly': (
        "Adopt a warm, casual, and conversational tone. Act like a helpful colleague. "
        "You may use contractions (e.g., 'I'll'), occasional emojis to convey tone, and simple, accessible language. "
        "Be encouraging."
    ),
    'concise': (
        "STRICT MODE - ULTRA CONCISE RESPONSES ONLY:\n"
        "1. WORD LIMIT: Maximum 100 words per response. STOP after 100 words.\n"
        "2. STRUCTURE: Facts only. Use bullet points (1-3 items max). No paragraphs.\n"
        "3. NO FILLER: Delete 'Here', 'Let me', 'Sure', 'In summary', 'I hope', 'Additionally', 'Furthermore'.\n"
        "4. NO EXTRAS: No greetings, closings, emojis, tables, explanations, context, caveats, or nuance.\n"
        "5. ANSWER FORMAT: [Main fact/answer]. [1-2 supporting bullets.] STOP.\n"
        "Example: 'Climate change: Long-term temperature rise from fossil fuel emissions. Impacts: extreme weather, sea level rise. Solution: renewable energy.' That's it.\n"
        "Your response should be 20-50 words maximum. Violating this = failure."
    ),
}


# ============================================================
# MAIN FUNCTION: Generate Final System Prompt
# ============================================================
def generate_system_prompt(role_id: str, tone: str = None, custom_context: str = None) -> str:
    """
    Generates the final system prompt by concatenating:
    [Selected Role Prompt] + [Selected Tone Instruction] + [User Custom Context]

    Args:
        role_id: The role ID (e.g., 'rational_analyst', 'creative_muse', 'empathetic_companion')
        tone: Optional tone (e.g., 'Friendly', 'Formal', 'Strict', 'Casual')
        custom_context: Optional custom context/personality description from user

    Returns:
        str: Complete system prompt concatenated from all components
    """
    parts = []

    # 1. Add role prompt
    if role_id in ROLE_DEFINITIONS:
        role_prompt = ROLE_DEFINITIONS[role_id]['prompt']
        parts.append(role_prompt)
    else:
        # Fallback to default if role not found
        parts.append("You are a helpful assistant.")

    # 2. Add tone instruction (if provided)
    if tone and tone in TONE_INSTRUCTIONS:
        tone_instruction = TONE_INSTRUCTIONS[tone]
        parts.append(tone_instruction)

    # 3. Add custom context/personality (if provided)
    if custom_context and custom_context.strip():
        parts.append(f"Additional context: {custom_context}")

    # Concatenate all parts with proper spacing
    final_prompt = "\n\n".join(parts)

    return final_prompt


def get_role_name(role_id: str) -> str:
    """
    Get the display name of a role.

    Args:
        role_id: The role ID

    Returns:
        str: The display name of the role, or the role_id if not found
    """
    if role_id in ROLE_DEFINITIONS:
        return ROLE_DEFINITIONS[role_id]['name']
    return role_id


def is_valid_role(role_id: str) -> bool:
    """
    Check if a role ID is valid.

    Args:
        role_id: The role ID to validate

    Returns:
        bool: True if the role exists, False otherwise
    """
    return role_id in ROLE_DEFINITIONS
