import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
SYNC_DATABASE_URL = os.getenv("SYNC_DATABASE_URL")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY")
LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "Trade-Agentic")
LANGCHAIN_ENDPOINT = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")

PDF_FOLDER = os.getenv("PDF_FOLDER", "./pdfs")
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")


def get_llm():
    return ChatGroq(
        model=GROQ_MODEL,
        api_key=GROQ_API_KEY,
        temperature=0.3,
    )

model = get_llm()
