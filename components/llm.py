import requests
import json

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2:3b"

SYSTEM_PROMPT = """You are a concise voice assistant.
Respond in plain spoken sentences only.
No bullet points, no markdown, no lists.
Keep responses under 3 sentences unless the user asks for detail."""

class LLMClient:
    def query(self, user_text, context=""):
        prompt = user_text
        if context:
            prompt = f"Use this information to answer: {context}\n\nQuestion: {user_text}"

        payload = {
            "model": MODEL,
            "prompt": prompt,
            "system": SYSTEM_PROMPT,
            "stream": False
        }

        try:
            response = requests.post(OLLAMA_URL, json=payload, timeout=60)
            data = response.json()
            return data.get("response", "Sorry, I could not get a response.")
        except Exception as e:
            print(f"LLM error: {e}")
            return "Sorry, something went wrong."
