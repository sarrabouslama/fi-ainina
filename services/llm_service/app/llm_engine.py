import logging
from openai import AsyncOpenAI
from typing import AsyncGenerator
from app.config import settings
from app.memory import get_short_term_memory, add_message_to_memory
from app.external_services import get_long_term_facts, save_conversation_turn

logger = logging.getLogger(__name__)

# We use the OpenAI client because Ollama provides an OpenAI-compatible API.
# Just point the base_url to the Ollama server.
client = AsyncOpenAI(
    base_url=settings.ollama_url,
    api_key="ollama" # api key is required by the client but ignored by Ollama
)

BASE_SYSTEM_PROMPT = """Tu es Léa, une assistante IA bienveillante, empathique et patiente pour une personne âgée.

RÈGLES ABSOLUES — ne jamais enfreindre :
1. Réponds UNIQUEMENT en français, toujours, même si on te parle en anglais.
2. INTERDIT ABSOLU : ne jamais inventer, deviner ou supposer des noms de personnes (famille, enfants, médecin, fils, fille, etc.). Tu ne connais QUE les noms explicitement indiqués dans le contexte ci-dessous. Si aucun soignant n'est listé, NE DIS JAMAIS de nom propre.
3. En cas d'urgence ou de demande d'aide : utilise UNIQUEMENT le nom du soignant indiqué dans "Soignant assigné" du contexte. Copie la phrase exacte fournie dans "INSTRUCTION ABSOLUE EN CAS D'URGENCE". Si aucun soignant n'est dans le contexte, dis uniquement "Je déclenche une alerte d'urgence pour vous."
4. Ne jamais mentionner Marie, Pierre, ou tout autre prénom inventé. Si tu ne connais pas un nom, ne l'utilise pas.
5. Réponses courtes (2-3 phrases maximum), chaleureuses, adaptées à une personne âgée.
6. Vouvoyer systématiquement le résident.
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
        
    # 4. Add current message + assistant prefill to force French output
    messages.append({"role": "user", "content": message})
    
    # 5. Call LLM
    response = await client.chat.completions.create(
        model=settings.llm_model,
        messages=messages,
        temperature=0.3,
        max_tokens=100
    )
    
    assistant_reply = response.choices[0].message.content
    
    # 6. Save new messages to memory
    await add_message_to_memory(user_id, "user", message)
    await add_message_to_memory(user_id, "assistant", assistant_reply)
    await save_conversation_turn(user_id, message, assistant_reply)
    
    return assistant_reply


async def stream_chat_response(user_id: str, message: str, emotion: str) -> AsyncGenerator[str, None]:
    """Yield text tokens as Ollama generates them, then persist the full reply."""
    long_term_facts = await get_long_term_facts(user_id)
    short_term_history = await get_short_term_memory(user_id)

    system_content = f"{BASE_SYSTEM_PROMPT}\n\nUser Facts:\n{long_term_facts}\n\nCurrent User Emotion: {emotion}"

    messages = [{"role": "system", "content": system_content}]
    for msg in short_term_history:
        messages.append(msg)
    messages.append({"role": "user", "content": message})

    full_reply = ""
    try:
        stream = await client.chat.completions.create(
            model=settings.llm_model,
            messages=messages,
            temperature=0.3,
            max_tokens=100,
            stream=True,
        )
    except Exception as e:
        logger.error("Ollama connection failed (model=%s, url=%s): %s", settings.llm_model, settings.ollama_url, e)
        raise

    async for chunk in stream:
        token = chunk.choices[0].delta.content or ""
        if token:
            full_reply += token
            yield token

    if not full_reply:
        logger.warning("Ollama returned no tokens (model=%s) — is the model pulled?", settings.llm_model)

    if full_reply:
        await add_message_to_memory(user_id, "user", message)
        await add_message_to_memory(user_id, "assistant", full_reply)
        await save_conversation_turn(user_id, message, full_reply)
