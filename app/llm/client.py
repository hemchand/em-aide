from __future__ import annotations
from typing import Protocol, Type, Any
import os
import json
import httpx
from pydantic import BaseModel
from app.settings import settings

mode = os.getenv("LLM_MODE", "openai").lower()

class LLMClient(Protocol):
    def generate_structured(self, system: str, user: str, schema: Type[BaseModel]) -> BaseModel: ...
    def name(self) -> str: ...

def _parse_structured(content: str, schema: Type[BaseModel]) -> BaseModel:
    try:
        return schema.model_validate_json(content)
    except Exception:
        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        snippet = content[start:end + 1]
        try:
            return schema.model_validate_json(snippet)
        except Exception:
            data = json.loads(snippet)
            return schema.model_validate(data)

class OpenAICompatibleClient:
    def __init__(self):
        if not settings.llm_api_key:
            raise RuntimeError("LLM_API_KEY is required for remote mode.")
        self.base_url = settings.llm_base_url.rstrip("/")
        self.api_key = settings.llm_api_key
        self.model = settings.llm_model
        self.timeout = settings.llm_timeout_seconds

    def name(self) -> str:
        return f"remote:{self.model}"

    def generate_structured(self, system: str, user: str, schema: Type[BaseModel]) -> BaseModel:
        # Uses Chat Completions compatible endpoint: /chat/completions
        # Uses "response_format" JSON schema if supported; otherwise relies on strict prompt.
        url = f"{self.base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload: dict[str, Any] = {
            "model": self.model,
            "temperature": settings.llm_temperature,
            "max_tokens": settings.llm_max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            # Best-effort: many OpenAI-compatible providers accept this; if not, it is ignored.
            "response_format": {"type": "json_object"},
        }
        with httpx.Client(timeout=self.timeout) as client:
            r = client.post(url, headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()
        content = data["choices"][0]["message"]["content"]
        # Parse JSON into schema
        return _parse_structured(content, schema)

class OllamaClient:
    def __init__(self):
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.model = settings.ollama_model
        self.api_key = settings.llm_api_key

    def name(self) -> str:
        return f"local:{self.model}"

    def generate_structured(self, system: str, user: str, schema: Type[BaseModel]) -> BaseModel:
        url = f"{self.base_url}/api/chat"
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "format": "json",
            "options": {
                "temperature": settings.llm_temperature,
                "num_predict": settings.llm_max_tokens,
            },
            "stream": False,
        }
        with httpx.Client(timeout=settings.llm_timeout_seconds) as client:
            r = client.post(url, headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()
        content = data["message"]["content"]
        return _parse_structured(content, schema)

def get_llm_client() -> LLMClient:
    if settings.llm_mode.lower() in ["ollama", "local"]:
        return OllamaClient()
    return OpenAICompatibleClient()
