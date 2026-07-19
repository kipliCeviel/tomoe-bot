import os
import json
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.tools import DuckDuckGoSearchResults
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, HumanMessage

load_dotenv()

HISTORY_FILE = "chat_history.json"

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                messages = []
                for msg in data:
                    if msg["type"] == "human":
                        messages.append(HumanMessage(content=msg["content"]))
                    elif msg["type"] == "ai":
                        messages.append(AIMessage(content=msg["content"]))
                return messages
        except Exception as e:
            print(f"Error loading history: {e}")
            return []
    return []

def save_to_history(user_input: str, ai_output: str):
    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = []
            
    history.append({"type": "human", "content": user_input})
    history.append({"type": "ai", "content": ai_output})
    
    # Keep only last 20 messages (10 rounds of conversation) to manage token limit
    history = history[-20:]
    
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving history: {e}")

def get_agent_executor():
    # Load API Key directly in function to ensure it is picked up if env changes
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_gemini_api_key_here":
        raise ValueError("GEMINI_API_KEY belum diatur di file .env")

    # Initialize LLM
    llm = ChatGoogleGenerativeAI(
        model="gemini-flash-latest",
        temperature=0.7,
        google_api_key=api_key
    )

    # Initialize Tools
    search_tool = DuckDuckGoSearchResults()
    tools = [search_tool]

    # Setup Prompt with Persona
    persona = os.getenv("BOT_PERSONA", "Anda adalah asisten cerdas yang sangat membantu.")
    prompt = ChatPromptTemplate.from_messages([
        ("system", persona),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    # Create Agent
    agent = create_tool_calling_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    return agent_executor

# We will cache the executor to avoid re-initializing if possible, 
# but keep it simple for now.
executor_instance = None

def process_message(user_input: str) -> str:
    global executor_instance
    try:
        if executor_instance is None:
            executor_instance = get_agent_executor()
            
        # Load conversation history
        chat_history = load_history()
            
        response = executor_instance.invoke({
            "input": user_input,
            "chat_history": chat_history
        })
        output = response.get("output", "Maaf, saya tidak dapat merespons saat ini.")
        
        # In newer LangChain versions, output might be a list of dicts
        final_text = ""
        if isinstance(output, list):
            # Extract text from the first dictionary
            text_parts = [item.get("text", "") for item in output if isinstance(item, dict) and "text" in item]
            final_text = "\n".join(text_parts) if text_parts else str(output)
        else:
            final_text = str(output)
            
        # Save this round to history
        save_to_history(user_input, final_text)
        return final_text
    except ValueError as ve:
        return f"Sistem Error: {str(ve)}"
    except Exception as e:
        print(f"Error in agent: {e}")
        return "Terjadi kesalahan saat memproses permintaan. Mungkin API Key tidak valid atau ada masalah jaringan."
