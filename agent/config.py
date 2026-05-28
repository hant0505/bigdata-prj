import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

class OpenRouterLLMManager:
    def __init__(self):
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
            api_key=key,
            base_url="https://openrouter.ai/api/v1",
            temperature=0.1
        )


llm_manager = OpenRouterLLMManager()

def get_llm():
    return llm_manager.get_llm()
