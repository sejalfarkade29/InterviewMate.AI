"""Thin Gemini REST client (text + JSON). The API key never leaves the server."""
import json
import logging
import re
import time
from typing import Any

import httpx

from app.core.config import settings

log = logging.getLogger("interviewmate.gemini")


class GeminiError(RuntimeError):
    """Raised when Gemini is not configured or the call fails. Callers use fallbacks."""


_bad_models: set[str] = set()  # model ids that returned 404 for this key; skipped afterwards


def is_configured() -> bool:
    return bool(settings.GEMINI_API_KEY)


def _endpoint(model: str) -> str:
    return f"{settings.GEMINI_API_BASE.rstrip('/')}/v1beta/models/{model}:generateContent"


def _extract_text(data: dict) -> str:
    try:
        parts = data["candidates"][0]["content"]["parts"]
    except (KeyError, IndexError, TypeError):
        reason = (data.get("promptFeedback") or {}).get("blockReason") or data.get("candidates", [{}])[0].get("finishReason", "no output")
        raise GeminiError(f"Gemini returned no text ({reason})")
    return "".join(p.get("text", "") for p in parts if not p.get("thought"))


def generate_text(prompt: str, *, system: str | None = None, json_mode: bool = False,
                  temperature: float = 0.8, max_tokens: int = 8192, history: list[dict] | None = None) -> str:
    if not is_configured():
        raise GeminiError("GEMINI_API_KEY is not set")
    contents = list(history or [])
    contents.append({"role": "user", "parts": [{"text": prompt}]})
    body: dict[str, Any] = {"contents": contents, "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens}}
    if json_mode:
        body["generationConfig"]["responseMimeType"] = "application/json"
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}

    last: Exception | None = None
    for model in settings.gemini_models:
        if model in _bad_models:
            continue
        for attempt in range(2):
            try:
                r = httpx.post(_endpoint(model), json=body, timeout=settings.GEMINI_TIMEOUT_SECONDS,
                               headers={"x-goog-api-key": settings.GEMINI_API_KEY, "Content-Type": "application/json"})
            except httpx.HTTPError as exc:
                last = GeminiError(f"Could not reach Gemini: {exc.__class__.__name__}")
                break
            if r.status_code == 404:
                _bad_models.add(model)
                last = GeminiError(f"Model {model} is not available for this API key")
                break
            if r.status_code in (429, 500, 502, 503, 504) and attempt == 0:
                time.sleep(1.2)
                continue
            if r.status_code >= 400:
                msg = ""
                try:
                    msg = r.json().get("error", {}).get("message", "")
                except ValueError:
                    pass
                last = GeminiError(f"Gemini error {r.status_code}: {msg[:200]}")
                break
            try:
                return _extract_text(r.json())
            except GeminiError as exc:
                last = exc
                break
    raise last or GeminiError("Gemini request failed")


_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.I)


def parse_json(text: str) -> Any:
    cleaned = _FENCE.sub("", text.strip())
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = min([i for i in (cleaned.find("{"), cleaned.find("[")) if i >= 0], default=-1)
        end = max(cleaned.rfind("}"), cleaned.rfind("]"))
        if start >= 0 and end > start:
            return json.loads(cleaned[start:end + 1])
        raise


def generate_json(prompt: str, *, system: str | None = None, temperature: float = 0.7, max_tokens: int = 8192) -> Any:
    last: Exception | None = None
    for _ in range(2):
        text = generate_text(prompt, system=system, json_mode=True, temperature=temperature, max_tokens=max_tokens)
        try:
            return parse_json(text)
        except (json.JSONDecodeError, ValueError) as exc:
            last = exc
            prompt += "\n\nReturn ONLY valid JSON. No prose, no markdown fences."
    raise GeminiError(f"Gemini returned invalid JSON: {last}")


def clamp_int(value: Any, lo: int = 0, hi: int = 100, default: int = 0) -> int:
    try:
        return max(lo, min(hi, int(round(float(value)))))
    except (TypeError, ValueError):
        return default


def str_list(value: Any, limit: int = 12) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(v).strip() for v in value if str(v).strip()][:limit]
