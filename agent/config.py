import os
from crewai import LLM
from dotenv import load_dotenv

load_dotenv()

class GroqLLMManager:
    def __init__(self):
        keys = os.getenv("GROQ_API_KEY")
        if not keys:
            raise ValueError("GROQ_API_KEY not found!")

        self.api_keys = [k.strip() for k in keys.split(",") if k.strip()]
        self.index = 0

    def get_llm(self):
        key = self.api_keys[self.index]
        self.index = (self.index + 1) % len(self.api_keys)

        return LLM(
            model="groq/openai/gpt-oss-20b",
            api_key=key,
            temperature=0.1
        )

llm_manager = GroqLLMManager()

def get_llm():
    return llm_manager.get_llm()