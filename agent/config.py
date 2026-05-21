import os
import itertools
from crewai import LLM
from dotenv import load_dotenv

load_dotenv()

class GeminiLLMManager:
    def __init__(self):
        keys = os.getenv("API_KEY")

        if not keys:
            raise ValueError("API_KEY not found!")

        self.api_keys = [
            k.strip() for k in keys.split(",")
            if k.strip()
        ]

        self.index = 0

    def get_llm(self):
        key = self.api_keys[self.index]

        self.index = (self.index + 1) % len(self.api_keys)

        return LLM(
            model="gemini/gemini-2.5-flash",
            api_key=key,
            temperature=0.1
        )


# Singleton
llm_manager = GeminiLLMManager()


def get_llm():
    return llm_manager.get_llm()