import os
from pathlib import Path
from crewai import LLM
from dotenv import load_dotenv

AGENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = AGENT_DIR.parent

load_dotenv(REPO_ROOT / ".env")
load_dotenv(AGENT_DIR / ".env")


def _strip_crewai_cache_breakpoints(llm):
    original_formatter = llm._format_messages_for_provider

    def formatter(messages):
        formatted = original_formatter(messages)
        return [
            {
                key: value
                for key, value in message.items()
                if key != "cache_breakpoint"
            }
            for message in formatted
        ]

    llm._format_messages_for_provider = formatter
    return llm


def _read_keys(*env_names):
    raw_keys = []
    for env_name in env_names:
        value = os.getenv(env_name)
        if value:
            raw_keys.extend(value.split(","))

    keys = []
    seen = set()
    for key in raw_keys:
        key = key.strip()
        if key and key not in seen:
            keys.append(key)
            seen.add(key)

    return keys


class LLMManager:
    def __init__(self):
        requested_provider = os.getenv("LLM_PROVIDER", "").strip().lower()
        groq_keys = _read_keys("GROQ_API_KEY")
        gemini_keys = _read_keys("GEMINI_API_KEY", "GOOGLE_API_KEY", "API_KEY")

        if requested_provider == "gemini":
            self.provider = "gemini"
            self.api_keys = gemini_keys
        elif requested_provider == "groq":
            self.provider = "groq"
            self.api_keys = groq_keys
        elif groq_keys:
            self.provider = "groq"
            self.api_keys = groq_keys
        else:
            self.provider = "gemini"
            self.api_keys = gemini_keys

        if not self.api_keys:
            raise ValueError(
                "No LLM API key found. Set GROQ_API_KEY for Groq, or GEMINI_API_KEY/GOOGLE_API_KEY/API_KEY for Gemini."
            )

        if self.provider == "groq":
            self.model = os.getenv("GROQ_MODEL", "groq/llama-3.3-70b-versatile")
        else:
            self.model = os.getenv("GEMINI_MODEL", "gemini/gemini-2.5-flash")

        self.index = 0

    def get_llm(self):
        key = self.api_keys[self.index]

        self.index = (self.index + 1) % len(self.api_keys)

        llm = LLM(
            model=self.model,
            api_key=key,
            temperature=0.1
        )

        if self.provider == "groq":
            return _strip_crewai_cache_breakpoints(llm)

        return llm


# Singleton
llm_manager = LLMManager()


def get_llm():
    return llm_manager.get_llm()
