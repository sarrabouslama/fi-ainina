from openai import AsyncOpenAI
from typing import List, Dict
from app.config import settings
from app.memory import get_short_term_memory, add_message_to_memory
from app.external_services import get_long_term_facts, save_conversation_turn

# We use the OpenAI client because Ollama provides an OpenAI-compatible API.
# Just point the base_url to the Ollama server.
client = AsyncOpenAI(
    base_url=settings.ollama_url,
    api_key="ollama" # api key is required by the client but ignored by Ollama
)

BASE_SYSTEM_PROMPT = """
You are a kind, empathetic, and patient companion for an elderly person. 
Your goal is to converse naturally, provide comfort, and assist them. 
Keep your answers concise and friendly.
"""

async def generate_chat_response(user_id: str, message: str, emotion: str) -> str:
    # 1. Fetch Context
    long_term_facts = await get_long_term_facts(user_id)
    short_term_history = await get_short_term_memory(user_id)
    
    # 2. Construct System Prompt
    system_content = f"{BASE_SYSTEM_PROMPT}\n\nUser Facts:\n{long_term_facts}\n\nCurrent User Emotion: {emotion}"
    
    messages = [{"role": "system", "content": system_content}]
    
    # 3. Add History
    for msg in short_term_history:
        messages.append(msg)
        
    # 4. Add Current Message
    messages.append({"role": "user", "content": message})
    
    # 5. Call LLM
    response = await client.chat.completions.create(
        model=settings.llm_model,
        messages=messages,
        temperature=0.7,
        max_tokens=250
    )
    
    assistant_reply = response.choices[0].message.content
    
    # 6. Save new messages to memory
    await add_message_to_memory(user_id, "user", message)
    await add_message_to_memory(user_id, "assistant", assistant_reply)
    await save_conversation_turn(user_id, message, assistant_reply)
    
    return assistant_reply
