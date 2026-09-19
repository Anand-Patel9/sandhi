"""Provider-agnostic LLM client (Gemini, Groq, OpenAI, Anthropic) over plain HTTPS."""
from __future__ import annotations

import json
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

import httpx

OFFLINE = "offline"

PROVIDERS = {
    "gemini": {"label": "Google Gemini", "style": "openai", "default_model": "gemini-2.5-flash",
               "url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"},
    "groq": {"label": "Groq", "style": "openai", "default_model": "llama-3.3-70b-versatile",
             "url": "https://api.groq.com/openai/v1/chat/completions"},
    "openai": {"label": "OpenAI", "style": "openai", "default_model": "gpt-4o-mini",
               "url": "https://api.openai.com/v1/chat/completions"},
    "anthropic": {"label": "Anthropic Claude", "style": "anthropic",
                  "default_model": "claude-haiku-4-5-20251001",
                  "url": "https://api.anthropic.com/v1/messages"},
}


class LLMError(RuntimeError):
    pass


@dataclass
class LLMClient:
    provider: str = OFFLINE
    api_key: Optional[str] = None
    model: Optional[str] = None
    timeout: float = 40.0
    max_retries: int = 2
    calls: int = 0
    failures: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    @classmethod
    def create(cls, provider: str, api_key: Optional[str], model: Optional[str] = None) -> "LLMClient":
        if provider == OFFLINE or provider not in PROVIDERS:
            return cls(provider=OFFLINE)
        return cls(provider=provider, api_key=api_key, model=model or PROVIDERS[provider]["default_model"])

    @property
    def online(self) -> bool:
        return self.provider != OFFLINE and bool(self.api_key)

    @property
    def label(self) -> str:
        return f"{PROVIDERS[self.provider]['label']} · {self.model}" if self.online else "Offline (rule-based)"

    def chat(self, system: str, user: str, temperature: float = 0.6, max_tokens: int = 400) -> str:
        if not self.online:
            raise LLMError("offline")
        cfg = PROVIDERS[self.provider]
        last_err: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            with self._lock:
                self.calls += 1
            try:
                if cfg["style"] == "anthropic":
                    r = httpx.post(cfg["url"], timeout=self.timeout,
                                   headers={"x-api-key": self.api_key, "anthropic-version": "2023-06-01"},
                                   json={"model": self.model, "max_tokens": max_tokens,
                                         "temperature": temperature, "system": system,
                                         "messages": [{"role": "user", "content": user}]})
                else:
                    r = httpx.post(cfg["url"], timeout=self.timeout,
                                   headers={"Authorization": f"Bearer {self.api_key}"},
                                   json={"model": self.model, "temperature": temperature,
                                         "max_tokens": max_tokens,
                                         "messages": [{"role": "system", "content": system},
                                                      {"role": "user", "content": user}]})
                if r.status_code == 429 or r.status_code >= 500:
                    last_err = LLMError(f"HTTP {r.status_code}")
                    time.sleep(2 * (attempt + 1))
                    continue
                if r.status_code != 200:
                    raise LLMError(f"HTTP {r.status_code}: {r.text[:300]}")
                data = r.json()
                if cfg["style"] == "anthropic":
                    return "".join(b.get("text", "") for b in data.get("content", [])).strip()
                return (data["choices"][0]["message"]["content"] or "").strip()
            except (httpx.HTTPError, KeyError, ValueError) as e:
                last_err = LLMError(str(e))
                time.sleep(1.5 * (attempt + 1))
        with self._lock:
            self.failures += 1
        raise LLMError(str(last_err or "unknown LLM error"))

    def chat_json(self, system: str, user: str, **kw) -> dict:
        return extract_json(self.chat(system, user + "\n\nRespond with a single JSON object only.", **kw))

    def ping(self) -> str:
        return self.chat("You are a connectivity test.", "Reply with the single word OK.",
                         temperature=0, max_tokens=5)


def extract_json(text: str) -> dict:
    text = re.sub(r"```(?:json)?", "", text).strip()
    try:
        return json.loads(text)
    except ValueError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            raise LLMError("No JSON object in response")
        try:
            return json.loads(m.group(0))
        except ValueError as e:
            raise LLMError(f"Invalid JSON: {e}")