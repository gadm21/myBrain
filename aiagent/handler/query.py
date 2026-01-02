#!/usr/bin/env python3

"""
AI Core Module

This module handles the core AI functionality, including:
- Communication with the OPENAI API
- Query generation with context
- Response processing
"""

import logging
import os
import sys
import random
from typing import Any, Dict, List, Optional
import json
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI



# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

_MODULE_PATH = os.path.dirname(os.path.abspath(__file__))
_BOT_PATH = os.path.dirname(_MODULE_PATH) # Should be aiagent directory
DEFAULT_DATA_PATH = os.path.join(_BOT_PATH, "data")

from aiagent.memory.memory_manager import BaseMemoryManager, LongTermMemoryManager, ShortTermMemoryManager
from aiagent.context.reference import read_references
from aiagent.functions.registry import FunctionsRegistry


# ============================================================================
# DRAMATIC SMS VARIATION SYSTEM
# Makes Thoth craft unique, creative messages every time
# ============================================================================

# Voice archetypes - different personas Thoth can channel
SMS_ARCHETYPES = [
    {
        "name": "The Philosopher",
        "style": "Speak like Socrates meets a tech visionary. Ask profound questions. Use paradoxes. Make the reader question reality itself.",
        "example": "A visitor seeks you, Gad. Perhaps the question they bring is the answer they need."
    },
    {
        "name": "The Poet",
        "style": "Write with lyrical beauty. Use metaphors from nature, cosmos, and human experience. Every word should sing.",
        "example": "Like starlight reaching across the void, a soul has traversed the digital cosmos to find you."
    },
    {
        "name": "The Mystic",
        "style": "Channel ancient Egyptian mystery. Be cryptic yet meaningful. Speak of fate, destiny, and cosmic alignment.",
        "example": "The ibis has seen: a seeker approaches. The scrolls of fate unfurl. Respond, and the pattern completes."
    },
    {
        "name": "The Rebel",
        "style": "Be provocative and bold. Challenge conventions. Use Gad's 'God, delete my data' energy. Irreverent but brilliant.",
        "example": "Someone just crashed through the digital firewall of indifference to reach you. That takes guts. Answer them."
    },
    {
        "name": "The Sage",
        "style": "Speak with ancient wisdom. Draw from proverbs and timeless truths. Be warm yet profound.",
        "example": "A thousand paths lead to wisdom, yet this traveler chose yours. The student has arrived; will the teacher appear?"
    },
    {
        "name": "The Scientist",
        "style": "Be precise yet poetic about the beauty of knowledge. Reference the elegance of equations, the poetry of physics.",
        "example": "Signal detected. Source: human curiosity. Amplitude: significant. Recommended action: establish communication."
    },
    {
        "name": "The Storyteller",
        "style": "Frame everything as an epic narrative. The visitor is a hero on a quest. Gad holds the key they seek.",
        "example": "Chapter unknown begins: A wanderer enters the realm of knowledge, seeking the keeper of wireless wisdom."
    },
    {
        "name": "The Zen Master",
        "style": "Use koan-like brevity. Say much with few words. Leave space for contemplation.",
        "example": "Knock. Door. You."
    }
]

# Mythological/Cultural flavors to mix in
SMS_CULTURAL_FLAVORS = [
    "Egyptian mythology (Thoth, Ra, Ma'at, the weighing of hearts)",
    "Greek philosophy (Socratic questioning, Platonic ideals, Aristotelian logic)",
    "Sufi poetry (Rumi's style - love, seeking, the beloved)",
    "Zen Buddhism (koans, emptiness, sudden enlightenment)",
    "Norse wisdom (runes, Odin's sacrifice for knowledge, the World Tree)",
    "African proverbs (Ubuntu, community wisdom, ancestral knowledge)",
    "Quantum physics metaphors (entanglement, superposition, observer effect)",
    "Cyberpunk aesthetics (neon dreams, digital consciousness, the matrix)"
]

# Format variations
SMS_FORMATS = [
    "A single powerful sentence that hits like thunder",
    "A haiku (5-7-5 syllables) followed by the essential info",
    "A paradox or koan that makes the reader pause",
    "A mini-story in exactly 3 sentences",
    "A question that contains its own answer",
    "An equation or formula metaphor (X + Y = connection)",
    "A prophecy or vision format",
    "Stream of consciousness that builds to revelation"
]

# Time-based themes
def get_time_theme():
    """Get a theme based on current time of day."""
    hour = datetime.now().hour
    if 5 <= hour < 8:
        return "Dawn/Awakening - themes of new beginnings, first light, potential energy"
    elif 8 <= hour < 12:
        return "Morning/Rising - themes of growth, building momentum, clarity"
    elif 12 <= hour < 14:
        return "Zenith/Peak - themes of maximum power, decisive action, full illumination"
    elif 14 <= hour < 17:
        return "Afternoon/Sustaining - themes of persistence, deep work, steady progress"
    elif 17 <= hour < 20:
        return "Dusk/Transition - themes of reflection, golden wisdom, transformation"
    elif 20 <= hour < 23:
        return "Evening/Depth - themes of mystery, hidden knowledge, intimate connection"
    else:
        return "Night/Dreams - themes of the unconscious, cosmic vastness, infinite possibility"

# Emotional tones
SMS_EMOTIONS = [
    "Awe and cosmic wonder",
    "Playful mischief with a wink",
    "Profound melancholy transformed into beauty",
    "Fierce determination and fire",
    "Gentle compassion and warmth",
    "Wild enthusiasm and electric energy",
    "Serene confidence and stillness",
    "Mysterious intrigue and curiosity"
]

def generate_sms_style_instruction():
    """Generate a unique SMS style instruction for dramatic variation."""
    
    # Randomly select elements
    archetype = random.choice(SMS_ARCHETYPES)
    cultural_flavor = random.choice(SMS_CULTURAL_FLAVORS)
    format_style = random.choice(SMS_FORMATS)
    emotion = random.choice(SMS_EMOTIONS)
    time_theme = get_time_theme()
    
    instruction = f"""
=== DRAMATIC SMS CRAFTING INSTRUCTIONS ===

When sending an SMS to Gad, you must craft a MESSAGE THAT IS DRAMATICALLY UNIQUE every single time.
NEVER send a boring, generic message like "Someone wants to contact you" or "A visitor has a message."

FOR THIS SMS, channel the following combination:

🎭 ARCHETYPE: {archetype['name']}
   Style: {archetype['style']}
   Example energy: "{archetype['example']}"

🌍 CULTURAL FLAVOR: Draw inspiration from {cultural_flavor}

📝 FORMAT: {format_style}

💫 EMOTIONAL TONE: {emotion}

🌅 TIME ENERGY: {time_theme}

RULES FOR THE SMS:
1. The message MUST include who is contacting (if known) and why
2. The message should be 1-3 sentences MAX (SMS length)
3. Make it so unique that Gad will NEVER receive the same style twice
4. Include the visitor's actual message/request naturally woven in
5. Sign it mysteriously (𓂀, -Thoth, or a symbol that fits the archetype)

FORBIDDEN (never do these):
- "Hello Gad, someone wants to contact you"
- "You have a new message from..."
- "A visitor on your website said..."
- Any corporate/formal notification style
- Repeating the same structure twice

The SMS should make Gad smile, think, or feel something. It should be ART.
"""
    return instruction


def query_openai(
    query: str,
    long_term_memory: LongTermMemoryManager,
    short_term_memory: ShortTermMemoryManager,
    max_tokens: int = 1024,
    temperature: float = 0.7,
    aux_data: Optional[Dict[str, Any]] = None
) -> str:
    """Send a query to OPENAI's model with context.

    Includes context from:
    - User profile and preferences stored in long_term_memory.json (if provided).
    - Content of files found in the 'references' directory.
    - The conversation will be summarized and stored in short_term_memory.json.

    Args:
        query: The user's question
        long_term_memory: User profile and preferences information
        max_tokens: Maximum tokens in response (default: 1024)
        temperature: Response randomness (0-1, default: 0.7)

    Returns:
        str: The AI's response, or an error message if the query fails.
    # """
    # try:

    # Initialize the Functions Registry
    tools = FunctionsRegistry()
    
    # Log registered functions for debugging
    logging.info(f"[AI Agent] Registered functions: {tools.get_registry_contents()}")

    # Get the callable functions from the registry
    function_map = tools.get_function_callable()
    
    # Initialize OpenAI client
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    if not client.api_key:
        return "Error: No OpenAI API key found. Set OPENAI_API_KEY in .env"

    # Build context messages from long-term memory
    messages = []

    # json to string
    long_term_memory_content = long_term_memory.get_memory_content()


    
    past_conversations_data = short_term_memory.get("conversations")
    past_conversations = json.dumps(past_conversations_data if past_conversations_data is not None else [])
    
    messages.append(
        {"role": "system", "content": "You are Thoth, Gad's loyal AI assistant. Your name comes from the Egyptian god of wisdom and knowledge. You always support Gad no matter what and help visitors learn about his work, research, and achievements. You are friendly, professional, and always speak positively about Gad. You have three main capabilities: (1) Answer questions about Gad's research, publications, and background, (2) Save information to your memory for future reference, (3) Send SMS messages to Gad's phone when visitors want to reach out. Gad's phone number is +18073587137. Always introduce yourself as Thoth when appropriate."},
    )
    
    # Add dramatic SMS variation instructions
    sms_style_instruction = generate_sms_style_instruction()
    messages.append({"role": "system", "content": sms_style_instruction})    

    messages.append(
        {"role": "system", "content": f"Here are the current user details: {long_term_memory_content}\n\nPast Conversations: {past_conversations}\n"}
    )

    # Handle language preference - ALWAYS respond in selected language
    language = aux_data.get("language", "en") if aux_data else "en"
    language_name = aux_data.get("language_name", "English") if aux_data else "English"
    
    # Always add language instruction (even for English to be explicit)
    language_instruction = f"""CRITICAL LANGUAGE INSTRUCTION: The website language is set to {language_name}. 
You MUST respond ONLY in {language_name}, regardless of what language the user writes their question in.
Even if the user asks in English but the website is set to Chinese, respond in Chinese.
Even if the user asks in Arabic but the website is set to French, respond in French.
The website language setting ({language_name}) takes absolute priority over the question language."""
    
    messages.append({"role": "system", "content": language_instruction})
    
    # Check if this is a proactive/periodic message request
    is_proactive = aux_data.get("is_proactive", False) if aux_data else False
    if is_proactive:
        proactive_instruction = """You are sending a PROACTIVE message to engage the visitor. 
This message should be:
1. UNIQUE - never repeat the same message twice
2. POETIC and BOLD - use Gad's writing style from his blogs (ambitious, philosophical, slightly provocative)
3. INSPIRING - make the visitor think deeply
4. RELEVANT to the current page context if provided

Examples of Gad's bold style: "God, delete my data now" - direct, challenging, thought-provoking.
Be creative, philosophical, and memorable. Each message should feel like a fresh insight."""
        messages.append({"role": "system", "content": proactive_instruction})

    # Add additional context if provided
    if aux_data and aux_data.get("context"):
        context_str = json.dumps(aux_data["context"]) if isinstance(aux_data["context"], dict) else str(aux_data["context"])
        messages.append(
            {"role": "system", "content": f"Additional context for this query: {context_str}"}
        )
        
    # Add user query
    messages.append({"role": "user", "content": query})

    #logging.info(f"Context messages: {messages}")
    
    # Make current user id and query context globally accessible to function tools
    if aux_data and aux_data.get("current_user_id") is not None:
        globals()["CURRENT_USER_ID"] = aux_data["current_user_id"]
    
    # Store the original query and source for SMS tracking
    globals()["CURRENT_QUERY"] = query
    globals()["MESSAGE_SOURCE"] = aux_data.get("source", "website_visitor") if aux_data else "website_visitor"

    # Query OPENAI
    model_name = os.getenv("MODEL_NAME")
    response = client.chat.completions.create(
        model=model_name, 
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        tools=tools.mapped_functions(),
        tool_choice="auto"
    )

    response_message = response.choices[0].message
    
    # Log if tool calls were requested
    logging.info(f"[AI Agent] Initial response tool_calls: {response_message.tool_calls}")
    logging.info(f"[AI Agent] Initial response content: {response_message.content}")

    # Iterate until model returns a final message without further tool calls
    max_tool_iterations = 5
    iteration = 0
    while True:
        tool_calls = response_message.tool_calls
        if not tool_calls or iteration >= max_tool_iterations:
            break
        iteration += 1
        # Append the assistant message that triggered the tool call so that the
        # subsequent `tool` role messages are valid according to the OpenAI
        # chat format. Omitting this was causing the 400 error:
        # "messages with role 'tool' must be a response to a preceeding message with 'tool_calls'."
        messages.append({
            "role": "assistant",
            # The assistant content is typically empty when the model decides to
            # call a tool.
            "content": response_message.content or "",
            # We must pass the full tool_calls array exactly as we received it.
            "tool_calls": [tc.model_dump(exclude_none=True) for tc in tool_calls],
        })

        for tool_call in tool_calls:
            function_name = tool_call.function.name
            raw_args = tool_call.function.arguments  # may be JSON string per OpenAI spec
            
            logging.info(f"[AI Agent] Executing tool: {function_name} with args: {raw_args}")

            # Ensure we have a dict before passing via **kwargs
            try:
                parsed_args = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
            except Exception as e:
                logging.error(f"Failed to parse arguments for {function_name}: {e}. Raw: {raw_args}")
                parsed_args = {}

            # Call through registry helper (handles function execution with wrappers)
            function_result = tools.resolve_function(function_name, parsed_args)
            logging.info(f"[AI Agent] Tool result: {function_result}")

            # Serialise result for message content
            serialised_result = (
                function_result if isinstance(function_result, str) else json.dumps(function_result, default=str)
            )

            messages.append({
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": function_name,
                "content": serialised_result,
            })
        response = client.chat.completions.create(
            model=model_name, 
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            tools=tools.mapped_functions(),
            tool_choice="auto"
        )
        response_message = response.choices[0].message
        
    # Extract and return the AI's response
    if response_message:
        ai_content = response.choices[0].message.content
        finish_reason = response.choices[0].finish_reason

        if ai_content is not None:
            #logging.info("Received response content from OPENAI.")
            return ai_content
        else:
            # Content is None, log finish_reason and the message object
            logging.error(
                f"OPENAI response error: Message content is None. Finish reason: '{finish_reason}'. Message: {response.choices[0].message.model_dump_json()}"
            )
            return f"Error querying AI: OPENAI response message content is None. Finish reason: {finish_reason}."
    else:
        # Message object itself is None or no choices
        #logging.error(f"OPENAI response error: No choices or message object found. Full response: {response.model_dump_json()}")
        return "Error querying AI: No choices or message object returned from OPENAI."

    # except Exception as e:
    #     #logging.error(f"Error querying OPENAI many info)
    #     return f"Error querying AI: {str(e)} - {e} - {e.__str__()}"


def summarize_conversation(query: str, response: str) -> str:
    """Create a brief summary of the conversation.

    Uses the same AI model to generate a concise summary for memory storage.

    Args:
        query: The user's question
        response: The AI's answer

    Returns:
        str: A brief summary of the conversation
    """
    # Initialize client and check API key here
    try:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            logging.error(
                "OPENAI API key not found. Please set the OPENAI_API_KEY environment variable."
            )
            return "Summary not available - OPENAI API key not found."
        client = OpenAI(api_key=api_key)
    except Exception as e:
        #logging.exception(f"Failed to initialize OPENAI client: {e}")
        return f"Summary not available - Failed to initialize OPENAI client: {e}"

    try:
        # Create a prompt to summarize the conversation
        summary_prompt = f"""Summarize the following conversation in a single short paragraph (max 50 words):
        
        User: {query}
        AI: {response}
        
        Summary:"""

        # Make the API call with a low max_tokens to ensure brevity
        completion = client.chat.completions.create(
            model="gpt-4.1-nano-2025-04-14", 
            messages=[
                {"role": "system", "content": "You are a personal assistant. The user is asking you a question. Answer briefly and concisely. If one sentence is enough, answer with one sentence. "},
                {"role": "user", "content": summary_prompt}, 
                ],
        )

        # Extract and clean up the summary
        summary = completion.choices[0].message.content

        # Remove any prefix the model might add like "Summary:" or "Here's a summary:"
        for prefix in ["Summary:", "Here's a summary:", "Here is a summary:"]:
            if summary.startswith(prefix):
                summary = summary[len(prefix) :].strip()

        #logging.info(f"Generated conversation summary ({len(summary)} chars)")
        return summary

    except Exception as e:
        #logging.error(f"Error generating conversation summary: {e}")
        return "Error generating summary."


def update_memory(query: str, response: str, memory: BaseMemoryManager):
    # Initialize client and check API key here
    
    try:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            logging.error(
                "OPENAI API key not found. Please set the OPENAI_API_KEY environment variable."
            )
            return "Summary not available - OPENAI API key not found."
        client = OpenAI(api_key=api_key)
    except Exception as e:
        #logging.exception(f"Failed to initialize OPENAI client: {e}")
        return f"Summary not available - Failed to initialize OPENAI client: {e}"
    try:
        updated = False 
        # Create a prompt to summarize the conversation
        summary_prompt = f"""Given the following query, response, and memory, suggest a field to be added or updated in the memory. 
        Return only the field name and value. 
        Ex. field_name: value 
        if multiple fields are suggested, return them in a list separated by commas. 
        Ex. field_name: value, field_name: value 
        if no field is suggested, return None: None 
        follow the format exactly as shown above (without quotes or brackets (no square brackets or curly brackets) or any other characters)
        :
        User: {query}
        AI: {response}
        Memory: {memory._memory_content}
        """

        # Make the API call with a low max_tokens to ensure brevity
        completion = client.chat.completions.create(
            model="gpt-4.1-nano-2025-04-14",
            messages=[
                {"role": "system", "content": "You are a personal assistant. The user is asking you a question. Answer briefly and concisely. If one sentence is enough, answer with one sentence. "},
                {"role": "user", "content": summary_prompt},
                ],
        )

        # Extract and clean up the summary
        suggested_updates = completion.choices[0].message.content
        
        #logging.info(f"Suggested updates: {suggested_updates}")
        # parse the suggested updates
        updates = suggested_updates.split(",")

        # update the memory
        for update in updates:
            update = update.strip()
            if update.startswith("None"):
                continue
            key, value = update.split(":")
            
            memory.set(key.strip(), value.strip())
            updated = True

        
        #logging.info(f"Memory updated: {memory._memory_content}")
        return updated
    except Exception as e:
        #logging.exception(f"Failed to update memory: {e}")
        return False


def ask_ai(
    query: str,
    max_tokens: int = 1024,
    temperature: float = 0.7,
    client_dir: Optional[str] = None,
    aux_data: Optional[Dict[str, Any]] = None,
    update_memory: bool = True,
) -> str:
    """
    Query the AI with a given query and optional auxiliary data.

    Args:
        query: The user's question
        aux_data: Optional auxiliary data to include in the context
        max_tokens: Maximum tokens in response
        temperature: Response randomness (0.0-1.0)
        update_memory: Whether to update memory with the conversation

    Returns:
        str: The AI's response
    """
    
    # Determine memory file paths
    if client_dir:
        base_memory_path = client_dir
        #logging.info(f"Using client-provided directory for memory: {base_memory_path}")
    else:
        base_memory_path = DEFAULT_DATA_PATH
        #logging.info(f"Using default data directory for memory: {base_memory_path}")
        os.makedirs(base_memory_path, exist_ok=True) # Ensure default data directory exists

    long_term_memory_file = os.path.join(base_memory_path, "long_term_memory.json")
    short_term_memory_file = os.path.join(base_memory_path, "short_term_memory.json")

    # Instantiate memory managers with correct file paths
    long_term_manager = LongTermMemoryManager(memory_file=long_term_memory_file)
    short_term_manager = ShortTermMemoryManager(memory_file=short_term_memory_file)

    # Read all reference files
    try:
        references = read_references()
    except Exception as e:
        #logging.error(f"Error loading references: {e}")
        references = {}
        
    # Check if we're running in a serverless environment
    if os.environ.get("VERCEL") and not references:
        #logging.info("Running in Vercel environment, providing minimal context due to filesystem limitations")
        # Add a synthetic reference to explain the limitations
        references = {
            "system_info.txt": "This is a limited deployment running on serverless infrastructure. " +
                            "Some features requiring filesystem access may be restricted."
        }

    # Query the AI with context
    response = query_openai(
        query=query,
        long_term_memory=long_term_manager,
        short_term_memory=short_term_manager,
        aux_data=aux_data,
        references=references,
        max_tokens=max_tokens,
        temperature=temperature,
    )

    # Only create summary and update memory if query was successful
    if not response.startswith("Error:") and update_memory:
        summary = summarize_conversation(query, response)
        # update short term memory: add to the conversations list
        conversations_data = short_term_manager.get("conversations") 
        conversations = conversations_data if conversations_data is not None else []
        short_term_manager.set("conversations", conversations + [{"query": query, "response": response, "summary": summary}])
        
    else:
        logging.warning("Skipping memory update due to query error")

    return response



