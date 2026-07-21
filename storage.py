"""
storage.py — Persistent storage layer for Tomoe Bot.

Uses Redis when REDIS_URL is set (Railway production).
Falls back to local JSON files when REDIS_URL is not set (local dev).
"""

import os
import json
import logging
import datetime
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

REDIS_URL = os.getenv("REDIS_URL", "")

# Redis keys
KEY_CHAT_ID       = "tomoe:chat_id"
KEY_CHAT_HISTORY  = "tomoe:chat_history"
KEY_PERSONA_MEM   = "tomoe:persona_memory"

# Fallback file paths (local dev)
FILE_CHAT_ID      = "chat_id.txt"
FILE_HISTORY      = "chat_history.json"
FILE_PERSONA_MEM  = "persona_memory.json"

MAX_HISTORY_MESSAGES = 20
MAX_PERSONA_ENTRIES  = 20

_redis_client = None


def get_redis():
    """Lazy-init Redis client. Returns None if REDIS_URL is not set."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    if not REDIS_URL:
        return None
    try:
        import redis
        _redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        _redis_client.ping()
        logging.info("[Storage] Connected to Redis.")
        return _redis_client
    except Exception as e:
        logging.error(f"[Storage] Redis connection failed, falling back to file storage: {e}")
        return None


def _using_redis() -> bool:
    return get_redis() is not None


# ---------------------------------------------------------------------------
# Chat ID
# ---------------------------------------------------------------------------

def save_chat_id(chat_id: int) -> None:
    r = get_redis()
    if r:
        r.set(KEY_CHAT_ID, str(chat_id))
    else:
        with open(FILE_CHAT_ID, "w") as f:
            f.write(str(chat_id))


def get_chat_id() -> int | None:
    r = get_redis()
    if r:
        val = r.get(KEY_CHAT_ID)
        if val:
            try:
                return int(val)
            except ValueError:
                return None
        return None
    else:
        if os.path.exists(FILE_CHAT_ID):
            with open(FILE_CHAT_ID, "r") as f:
                try:
                    return int(f.read().strip())
                except ValueError:
                    return None
        return None


# ---------------------------------------------------------------------------
# Chat History
# ---------------------------------------------------------------------------

def load_history() -> list:
    """Load chat history as a list of LangChain message objects."""
    from langchain_core.messages import AIMessage, HumanMessage

    r = get_redis()
    if r:
        raw = r.get(KEY_CHAT_HISTORY)
        if raw:
            try:
                data = json.loads(raw)
            except Exception:
                data = []
        else:
            data = []
    else:
        if os.path.exists(FILE_HISTORY):
            try:
                with open(FILE_HISTORY, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = []
        else:
            data = []

    messages = []
    for msg in data:
        if msg.get("type") == "human":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg.get("type") == "ai":
            messages.append(AIMessage(content=msg["content"]))
    return messages


def save_to_history(user_input: str, ai_output: str) -> None:
    """Append a conversation round to history, trimming to MAX_HISTORY_MESSAGES."""
    r = get_redis()

    # Load current raw history
    if r:
        raw = r.get(KEY_CHAT_HISTORY)
        try:
            history = json.loads(raw) if raw else []
        except Exception:
            history = []
    else:
        if os.path.exists(FILE_HISTORY):
            try:
                with open(FILE_HISTORY, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except Exception:
                history = []
        else:
            history = []

    history.append({"type": "human", "content": user_input})
    history.append({"type": "ai", "content": ai_output})
    history = history[-MAX_HISTORY_MESSAGES:]

    serialized = json.dumps(history, ensure_ascii=False)

    if r:
        r.set(KEY_CHAT_HISTORY, serialized)
    else:
        try:
            with open(FILE_HISTORY, "w", encoding="utf-8") as f:
                f.write(serialized)
        except Exception as e:
            logging.error(f"[Storage] Error saving history to file: {e}")


# ---------------------------------------------------------------------------
# Persona Memory
# ---------------------------------------------------------------------------

def load_persona_memory() -> list[str]:
    """Load Tomoe's self-study knowledge list."""
    r = get_redis()
    if r:
        raw = r.get(KEY_PERSONA_MEM)
        if raw:
            try:
                data = json.loads(raw)
                return data.get("knowledge", [])
            except Exception:
                return []
        return []
    else:
        if os.path.exists(FILE_PERSONA_MEM):
            try:
                with open(FILE_PERSONA_MEM, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("knowledge", [])
            except Exception:
                return []
        return []


def save_persona_memory(new_entries: list[str]) -> None:
    """Merge new entries into persona memory, deduplicate, trim to MAX_PERSONA_ENTRIES."""
    existing = load_persona_memory()
    combined = existing + new_entries

    seen = set()
    unique = []
    for entry in combined:
        if entry not in seen:
            seen.add(entry)
            unique.append(entry)
    trimmed = unique[-MAX_PERSONA_ENTRIES:]

    jakarta_tz = datetime.timezone(datetime.timedelta(hours=7))
    now = datetime.datetime.now(jakarta_tz)
    data = {
        "last_studied": now.strftime("%Y-%m-%d %H:%M WIB"),
        "knowledge": trimmed,
    }
    serialized = json.dumps(data, ensure_ascii=False)

    r = get_redis()
    if r:
        r.set(KEY_PERSONA_MEM, serialized)
        logging.info(f"[Storage] Persona memory saved to Redis ({len(trimmed)} entries).")
    else:
        try:
            with open(FILE_PERSONA_MEM, "w", encoding="utf-8") as f:
                f.write(serialized)
            logging.info(f"[Storage] Persona memory saved to file ({len(trimmed)} entries).")
        except Exception as e:
            logging.error(f"[Storage] Error saving persona memory: {e}")
