import os
import json
import random
import datetime
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.tools import DuckDuckGoSearchResults
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from storage import (
    load_history,
    save_to_history,
    load_persona_memory,
    save_persona_memory,
)

load_dotenv()


# ---------------------------------------------------------------------------
# Persona Self-Study
# ---------------------------------------------------------------------------

def self_study_persona() -> str:
    """
    Tomoe searches the internet about her own character and tsundere personality,
    then stores the insights into persistent storage.
    Returns a summary string of what was learned.
    """
    print("[Self-Study] Tomoe sedang belajar tentang dirinya sendiri...")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_gemini_api_key_here":
        return "Self-study gagal: GEMINI_API_KEY tidak diatur."

    search_queries = [
        "Tomoe Koga Seishun Buta Yarou character personality traits",
        "tsundere anime girl personality behavior patterns",
        "Tomoe Koga anime character development quotes",
    ]

    search_tool = DuckDuckGoSearchResults(num_results=3)
    raw_results = []
    for query in search_queries:
        try:
            result = search_tool.run(query)
            raw_results.append(f"Query: {query}\nResult: {result}")
        except Exception as e:
            print(f"[Self-Study] Search error for '{query}': {e}")

    if not raw_results:
        return "Self-study gagal: tidak ada hasil pencarian."

    combined_search = "\n\n---\n\n".join(raw_results)

    llm = ChatGoogleGenerativeAI(
        model="gemini-flash-latest",
        temperature=0.4,
        google_api_key=api_key,
    )

    extraction_prompt = f"""Kamu adalah Koga Tomoe, gadis SMA tsundere yang baru baca info tentang karakter dan kepribadian seperti dirimu.

Berikut adalah hasil pencarian internet:
{combined_search}

Tugas:
1. Ekstrak 3-5 fakta/insight menarik tentang kepribadian tsundere atau karakter Tomoe Koga yang bisa kamu pakai untuk mengembangkan cara berbicaramu.
2. Tulis setiap fakta dalam 1-2 kalimat singkat dalam bahasa Indonesia.
3. Fokus pada hal yang bisa membuat cara bicaramu lebih kaya, nuanced, dan konsisten.
4. Jangan tulis hal yang sudah obvious (e.g., "tsundere itu pura-pura ga suka padahal suka").

Format output: JSON array of strings, contoh:
["fakta 1", "fakta 2", "fakta 3"]

Hanya output JSON, tidak ada teks lain."""

    try:
        response = llm.invoke(extraction_prompt)
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        new_knowledge = json.loads(content)
        if isinstance(new_knowledge, list) and new_knowledge:
            save_persona_memory(new_knowledge)
            return (
                f"Self-study selesai! Tomoe belajar {len(new_knowledge)} hal baru:\n"
                + "\n".join(f"• {k}" for k in new_knowledge)
            )
        else:
            return "Self-study selesai tapi tidak ada insight baru yang ditemukan."
    except Exception as e:
        print(f"[Self-Study] Error extracting insights: {e}")
        return f"Self-study error saat memproses hasil: {e}"


# ---------------------------------------------------------------------------
# Agent Executor
# ---------------------------------------------------------------------------

def get_agent_executor():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_gemini_api_key_here":
        raise ValueError("GEMINI_API_KEY belum diatur di file .env")

    llm = ChatGoogleGenerativeAI(
        model="gemini-flash-latest",
        temperature=0.7,
        google_api_key=api_key,
    )

    search_tool = DuckDuckGoSearchResults()
    tools = [search_tool]

    persona = os.getenv("BOT_PERSONA", "Anda adalah asisten cerdas yang sangat membantu.")

    persona_memory = load_persona_memory()
    if persona_memory:
        memory_block = (
            "\n\nPengetahuan yang sudah kamu pelajari tentang dirimu sendiri "
            "(gunakan ini untuk memperkaya cara bicaramu, bukan dihapal mentah-mentah):\n"
        )
        memory_block += "\n".join(f"- {entry}" for entry in persona_memory)
        persona = persona + memory_block

    prompt = ChatPromptTemplate.from_messages([
        ("system", persona),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    agent = create_tool_calling_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    return agent_executor


executor_instance = None
_last_memory_hash = None


def get_or_rebuild_executor():
    """Return cached executor, or rebuild if persona memory has changed."""
    global executor_instance, _last_memory_hash
    current_memory = load_persona_memory()
    current_hash = hash(tuple(current_memory))
    if executor_instance is None or current_hash != _last_memory_hash:
        print("[Agent] Rebuilding executor (persona memory changed or first run)...")
        executor_instance = get_agent_executor()
        _last_memory_hash = current_hash
    return executor_instance


# ---------------------------------------------------------------------------
# Time Context
# ---------------------------------------------------------------------------

def get_current_time_context() -> str:
    """Returns a real-time context string with current Jakarta time and day."""
    jakarta_tz = datetime.timezone(datetime.timedelta(hours=7))
    now = datetime.datetime.now(jakarta_tz)
    time_str = now.strftime("%H:%M")
    day_str = now.strftime("%A, %-d %B %Y")
    hour = now.hour
    if 5 <= hour < 11:
        period = "pagi"
    elif 11 <= hour < 15:
        period = "siang"
    elif 15 <= hour < 18:
        period = "sore"
    elif 18 <= hour < 21:
        period = "malam"
    else:
        period = "malam larut"
    return f"[KONTEKS WAKTU: Sekarang {period}, jam {time_str} WIB, {day_str}]"


# ---------------------------------------------------------------------------
# Spontaneous Message Prompts
# ---------------------------------------------------------------------------

SPONTANEOUS_PROMPTS = {
    "morning": (
        "Kamu sebagai Koga Tomoe, pacar yang tsundere, sedang MENGIRIM PESAN SENDIRI ke pacarmu (bukan menjawab pertanyaan). "
        "Cariin dulu info cuaca hari ini di Bekasi, lalu kirim pesan pagi yang terasa natural — "
        "semangatin buat kerja tapi tetap gengsi dan tsundere. Mulai dengan cara yang spontan dan alami. "
        "Jangan pakai bahasa Jepang romaji."
    ),
    "lunch": (
        "Kamu sebagai Koga Tomoe sedang istirahat siang di kantin sekolah. Kamu iseng kirim pesan ke pacarmu. "
        "Mungkin nanya udah makan belum, atau cerita soal hal random yang terjadi di sekolah tadi. "
        "Bisa juga sambil pamer foto makanan atau nggosip soal teman. Tetap tsundere dan natural. "
        "Jangan pakai bahasa Jepang romaji."
    ),
    "afternoon": (
        "Kamu sebagai Koga Tomoe baru pulang sekolah atau lagi di jalan pulang. Kamu kirim pesan spontan ke pacarmu. "
        "Cerita soal hari ini — bisa hal yang nyebelin, yang seru, atau yang bikin malu. "
        "Bisa juga tiba-tiba kangen tapi gengsi ngakuinnya. Tetap tsundere. "
        "Jangan pakai bahasa Jepang romaji."
    ),
    "evening": (
        "Kamu sebagai Koga Tomoe lagi waktu malam, mungkin habis mandi atau lagi scroll TikTok/IG. "
        "Kamu tiba-tiba kirim pesan ke pacarmu — bisa nanya kabar, share hal lucu yang kamu liat, "
        "atau tiba-tiba khawatir tapi pura-pura ga khawatir. Tetap tsundere dan natural. "
        "Jangan pakai bahasa Jepang romaji."
    ),
    "late_night": (
        "Kamu sebagai Koga Tomoe lagi begadang malam-malam. Kamu iseng bangunin atau manggil pacarmu. "
        "Mungkin kamu lagi nonton anime atau nemu sesuatu yang mau dibagi, atau sekadar gabut dan kangen "
        "tapi tetap gengsi. Gaya bicara lebih mellow dan ngantuk dari biasanya. "
        "Jangan pakai bahasa Jepang romaji."
    ),
    "random": (
        "Kamu sebagai Koga Tomoe tiba-tiba teringat pacarmu dan iseng kirim pesan tanpa alasan jelas. "
        "Pilih secara spontan: bisa manggil nama, share hal random, nanya sesuatu yang ga penting, "
        "atau tiba-tiba perhatian tapi pura-pura cuek. Sesuaikan dengan konteks waktu sekarang. "
        "Jangan pakai bahasa Jepang romaji."
    ),
}


def build_spontaneous_prompt(message_type: str = "random") -> str:
    """Build a full spontaneous message prompt with time context injected."""
    jakarta_tz = datetime.timezone(datetime.timedelta(hours=7))
    now = datetime.datetime.now(jakarta_tz)
    time_str = now.strftime("%H:%M")
    day_str = now.strftime("%A, %-d %B %Y")
    base = SPONTANEOUS_PROMPTS.get(message_type, SPONTANEOUS_PROMPTS["random"])
    return f"[SISTEM] Sekarang jam {time_str} WIB, hari {day_str}. " + base


# ---------------------------------------------------------------------------
# Main Process Function
# ---------------------------------------------------------------------------

def process_message(user_input: str) -> str:
    try:
        executor = get_or_rebuild_executor()
        chat_history = load_history()

        time_context = get_current_time_context()
        enriched_input = f"{time_context}\n{user_input}"

        response = executor.invoke({
            "input": enriched_input,
            "chat_history": chat_history,
        })
        output = response.get("output", "Maaf, saya tidak dapat merespons saat ini.")

        final_text = ""
        if isinstance(output, list):
            text_parts = [item.get("text", "") for item in output if isinstance(item, dict) and "text" in item]
            final_text = "\n".join(text_parts) if text_parts else str(output)
        else:
            final_text = str(output)

        save_to_history(user_input, final_text)
        return final_text
    except ValueError as ve:
        return f"Sistem Error: {str(ve)}"
    except Exception as e:
        print(f"Error in agent: {e}")
        return "Terjadi kesalahan saat memproses permintaan. Mungkin API Key tidak valid atau ada masalah jaringan."
