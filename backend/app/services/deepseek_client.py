import json

import httpx

from app.config import get_settings


class DeepSeekClientError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def request_chat_json(messages: list[dict], max_tokens: int = 900) -> dict:
    settings = get_settings()
    if not settings.deepseek_api_key:
        raise DeepSeekClientError("llm_api_key_missing", "DeepSeek API key is not configured.")

    base_url = settings.deepseek_base_url.rstrip("/")
    payload = {
        "model": settings.deepseek_model,
        "messages": messages,
        "temperature": 0,
        "max_tokens": max_tokens,
        "stream": False,
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {settings.deepseek_api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = httpx.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=settings.deepseek_timeout_seconds,
        )
    except httpx.TimeoutException as error:
        raise DeepSeekClientError("llm_api_timeout", "DeepSeek API request timed out.") from error
    except httpx.HTTPError as error:
        raise DeepSeekClientError("llm_api_failed", "DeepSeek API request failed.") from error

    if response.status_code >= 400:
        raise DeepSeekClientError(
            "llm_api_failed",
            f"DeepSeek API returned HTTP {response.status_code}.",
        )

    try:
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        return json.loads(content)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as error:
        raise DeepSeekClientError("llm_response_invalid", "DeepSeek API returned an invalid JSON response.") from error
