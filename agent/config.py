import os
import itertools
from crewai import LLM
from dotenv import load_dotenv

load_dotenv()

class OpenRouterLLMManager: # Đổi tên class cho đúng bản chất
    def __init__(self):
        # Đọc danh sách API Key của Groq từ file .env
        keys = os.getenv("OPENROUTER_API_KEY") 

        if not keys:
            raise ValueError("OPENROUTER_API_KEY not found!")

        self.api_keys = [
            k.strip() for k in keys.split(",")
            if k.strip()
        ]

        self.index = 0

    def get_llm(self):
        key = self.api_keys[self.index]
        self.index = (self.index + 1) % len(self.api_keys)
        MODEL_NAME = "google/gemini-2.0-flash-lite-001"

        return ChatOpenAI(
            model=MODEL_NAME,
            openai_api_key=key,
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=0.1
        )


# Singleton
llm_manager = OpenRouterLLMManager()


def get_llm():
    return llm_manager.get_llm()
