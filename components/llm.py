import os
import json
import datetime
import requests

from ddgs import DDGS

OLLAMA_URL = "http://localhost:11434/api/chat"
GENERATE_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2:3b"

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEMORY_FILE = os.path.join(_PROJECT_ROOT, "memory.json")

MAX_TURNS = 6          # rolling window: keep the last 6 exchanges
KEEP_ALIVE = -1        # keep the model resident in memory indefinitely

SYSTEM_PROMPT = """You are a voice assistant named Jarvis.
Respond in plain spoken sentences only.
No bullet points, no markdown, no lists.
Keep responses as concise as possible, elaborating if the user asks for detail.

You have access to a web search tool. Use it whenever the user asks about
current events beyond 2023, recent releases, dates, prices, live facts, or anything that
may have changed after your training. When unsure whether your knowledge is
current, prefer searching. Do not guess at facts that could be out of date. 
When you use search results, state the answer directly. Do not describe your 
searching process or mention multiple searches"""

# Tool declaration in the format Ollama's /api/chat expects
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search the web for current or factual information "
                           "the model may not know or that may be out of date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query string."
                    }
                },
                "required": ["query"]
            }
        }
    }
]


def _search_web(query):
    """Run a DuckDuckGo search and return a short text summary of the top hit."""
    print(f"[llm] Searching web for: {query}")
    try:
        with DDGS() as ddgs:
            results = list(ddgs.news(query, region="us-en", max_results=1))
            if not results:
                results = list(ddgs.text(query, region="us-en", max_results=1))
        if not results:
            return "No results found for that query."
        r = results[0]
        title = r.get("title", "")
        body = r.get("body", r.get("snippet", ""))
        return f"Search result for '{query}':\nTitle: {title}\nSnippet: {body[:300]}"
    except Exception as e:
        print(f"[llm] Search error: {e}")
        return "SEARCH_UNAVAILABLE"


class LLMClient:
    def __init__(self):
        self.system = {"role": "system", "content": SYSTEM_PROMPT}
        self.history = self._load_history()

    # ---- memory persistence -------------------------------------------------
    def _load_history(self):
        try:
            with open(MEMORY_FILE, "r") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception:
            pass
        return []

    def _save_history(self):
        try:
            with open(MEMORY_FILE, "w") as f:
                json.dump(self.history[-(MAX_TURNS * 2):], f)
        except Exception as e:
            print(f"[llm] Could not save memory: {e}")

    def reset_memory(self):
        self.history = []
        self._save_history()

    # ---- warm-up ------------------------------------------------------------
    def warm_up(self):
        """Load the model into memory at startup so the first real query is fast."""
        print("[llm] Warming up model...")
        try:
            requests.post(GENERATE_URL, json={
                "model": MODEL, "prompt": "", "keep_alive": KEEP_ALIVE
            }, timeout=60)
            print("[llm] Model warm.")
        except Exception as e:
            print(f"[llm] Warm-up failed: {e}")

    # ---- main entry point (unchanged signature) -----------------------------
    def query(self, user_text, context=""):
        # Voice command to wipe memory
        if "forget everything" in user_text.lower() or "reset memory" in user_text.lower():
            self.reset_memory()
            return "Okay, I've cleared my memory."

        self.history.append({"role": "user", "content": user_text})
        messages = [self.system] + self.history[-(MAX_TURNS * 2):]

        answer = ""
        try:
            for _ in range(3):  # allow up to 3 tool rounds, then force an answer
                resp = self._chat(messages, use_tools=True)
                tool_calls = resp.get("tool_calls")

                if not tool_calls:
                    answer = (resp.get("content") or "").strip()
                    break

                messages.append(resp)  # assistant's tool-call turn
                for call in tool_calls:
                    fn = call.get("function", {})
                    if fn.get("name") == "search_web":
                        args = fn.get("arguments", {})
                        q = args.get("query", "") if isinstance(args, dict) else ""
                        result = _search_web(q)
                        messages.append({"role": "tool", "content": result})
            else:
                # Ran out of rounds without a plain answer: ask once more, no tools
                final = self._chat(messages, use_tools=False)
                answer = (final.get("content") or "").strip()
        except Exception as e:
            print(f"[llm] error: {e}")
            return "Sorry, something went wrong."

        answer = self._strip_tool_json(answer)
        if not answer:
            answer = "Sorry, I could not find an answer."

        self.history.append({"role": "assistant", "content": answer})
        self._save_history()
        return answer

    def _strip_tool_json(self, text):
        """Remove any leaked tool-call JSON so it never gets spoken."""
        import re
        cleaned = re.sub(r'\{[^{}]*"(name|action)"[^{}]*\}', '', text).strip()
        return cleaned if cleaned else text

    # ---- one round-trip to /api/chat ---------------------------------------
    def _chat(self, messages, use_tools):
        payload = {
            "model": MODEL,
            "messages": messages,
            "stream": False,
            "keep_alive": KEEP_ALIVE,
        }
        if use_tools:
            payload["tools"] = TOOLS
        r = requests.post(OLLAMA_URL, json=payload, timeout=120)
        data = r.json()
        return data.get("message", {})