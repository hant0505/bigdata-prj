import os
from crewai import LLM
from dotenv import load_dotenv

load_dotenv()

class GroqLLMManager:
    def __init__(self):
        # Đọc danh sách API Key của Groq từ file .env (Mã bắt đầu bằng gsk_...)
        keys = os.getenv("GROQ_API_KEY") 

        if not keys:
            raise ValueError("GROQ_API_KEY not found!")

        self.api_keys = [
            k.strip() for k in keys.split(",")
            if k.strip()
        ]

        self.index = 0

    def get_llm(self):
        key = self.api_keys[self.index]
        self.index = (self.index + 1) % len(self.api_keys)

        # CẤU HÌNH TIÊU CHUẨN CHẠY MODEL MẠNH NHẤT CỦA GROQ
        return LLM(
            model="groq/llama-3.3-70b-versatile", 
            api_key=key,
            temperature=0.1
        )


# Khởi tạo đối tượng Singleton
llm_manager = GroqLLMManager()


def get_llm():
    return llm_manager.get_llm()
