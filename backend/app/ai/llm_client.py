from functools import lru_cache
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
import os

load_dotenv()

@lru_cache(maxsize=1)
def get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model="deepseek-v4-pro",
        base_url="https://api.deepseek.com",
        api_key=os.getenv("DEEPSEEK_API_KEY"),
    )
