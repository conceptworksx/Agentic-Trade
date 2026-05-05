import os
from dotenv import load_dotenv
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from langchain_groq import ChatGroq

from pydantic_settings import BaseSettings
from functools import lru_cache


load_dotenv()


def get_llm():
 
    return ChatGroq(
        model="llama-3.3-70b-versatile",
        # model="meta-llama/llama-4-scout-17b-16e-instruct",
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.3,
        
    )

model = get_llm()

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://pdfuser:mypassword@localhost:5431/pdfdb"
    SYNC_DATABASE_URL: str = "postgresql://pdfuser:mypassword@localhost:5431/pdfdb"

    # Groq
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # LangSmith
    LANGCHAIN_TRACING_V2: bool = True
    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_PROJECT: str = "Trade-Agentic"
    LANGCHAIN_ENDPOINT: str = "https://api.smith.langchain.com"

    # App paths
    PDF_FOLDER: str = "./pdfs"
    
    API_BASE_URL: str = "http://127.0.0.1:8000" 

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

