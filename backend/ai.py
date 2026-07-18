"""LLM chat helper using emergentintegrations.

Default: Emergent universal key. Admin can override with their own provider key
via site settings (ai_use_own_key + ai_own_key + ai_provider + ai_model).
"""
import os
import logging
from emergentintegrations.llm.chat import LlmChat, UserMessage, TextDelta, StreamDone

logger = logging.getLogger(__name__)

EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")
DEFAULT_PROVIDER = "openai"
DEFAULT_MODEL = "gpt-5.4"


def resolve_ai_config(settings: dict) -> dict:
    settings = settings or {}
    use_own = bool(settings.get("ai_use_own_key"))
    own_key = (settings.get("ai_own_key") or "").strip()
    provider = settings.get("ai_provider") or DEFAULT_PROVIDER
    model = settings.get("ai_model") or DEFAULT_MODEL
    if use_own and own_key:
        return {"api_key": own_key, "provider": provider, "model": model, "source": "own"}
    return {"api_key": EMERGENT_KEY, "provider": provider, "model": model, "source": "emergent"}


def build_chat(session_id: str, system_message: str, settings: dict) -> LlmChat:
    cfg = resolve_ai_config(settings)
    chat = LlmChat(api_key=cfg["api_key"], session_id=session_id, system_message=system_message)
    chat.with_model(cfg["provider"], cfg["model"])
    return chat


async def stream_reply(session_id: str, system_message: str, history: list, user_text: str, settings: dict):
    """Async generator yielding text chunks. history: list of {role, content}."""
    chat = build_chat(session_id, system_message, settings)
    # Fold prior conversation into the prompt for context (library manages single turn)
    context = ""
    for m in history[-10:]:
        role = "User" if m["role"] == "user" else "Assistant"
        context += f"{role}: {m['content']}\n"
    prompt = (context + f"User: {user_text}\nAssistant:") if context else user_text
    try:
        async for event in chat.stream_message(UserMessage(text=prompt)):
            if isinstance(event, TextDelta):
                yield event.content
            elif isinstance(event, StreamDone):
                break
    except Exception as e:
        logger.error(f"AI stream error: {e}")
        yield f"\n[AI error: {str(e)[:200]}]"
