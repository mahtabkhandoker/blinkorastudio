"""LLM provider abstraction.

`ChatLLMClient` is a `Protocol`: the orchestrator depends only on this
shape, never on a concrete provider. `MockChatLLMClient` gives fully
deterministic extraction (no network, no API key) so local development
and CI never need a paid LLM call. `RealChatLLMClient` is a working
OpenAI-compatible implementation, gated behind `CHATBOT_PROVIDER=openai`
and an API key — swapping providers is a one-line env change
(`get_llm_client()` at the bottom is the single place that decides).

Only `extracted` is trusted by the orchestrator (see orchestrator.py's
module docstring for why `reply` is not used verbatim); both providers
still return a `reply` for interface parity and so a future orchestrator
change can make use of it directly.
"""

from __future__ import annotations

import json
import re
from typing import Protocol

from pydantic import BaseModel

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.models.creative import CreativeInput
from app.services.chatbot.system_prompt import SYSTEM_PROMPT

logger = get_logger(__name__)


class LLMResult(BaseModel):
    reply: str
    extracted: dict


class ChatLLMClient(Protocol):
    async def extract_and_reply(
        self, message: str, current_input: CreativeInput
    ) -> LLMResult: ...


# --- Mock provider -----------------------------------------------------------

_STYLE_KEYWORDS: dict[str, list[str]] = {
    "premium": ["premium", "প্রিমিয়াম", "luxury", "lakjhari"],
    "elegant": ["elegant", "এলিগেন্ট", "graceful", "classy"],
    # Deliberately excludes "eid"/"ঈদ"/"ramadan"/"রমজান": those words are
    # campaign-type signals (see _CAMPAIGN_KEYWORDS) and mentioning a
    # campaign must not, by itself, also imply a "festive" visual style —
    # the two are independent fields the user can set separately.
    "festive": ["festive", "উৎসবমুখর", "puja", "পূজা", "celebration"],
    "minimal": ["minimal", "মিনিমাল", "simple", "সাধারণ", "clean"],
    "energetic": ["energetic", "এনার্জেটিক", "energy", "lively", "dynamic", "fast"],
}

_CAMPAIGN_KEYWORDS: dict[str, list[str]] = {
    "Eid": ["eid", "ঈদ"],
    "Ramadan": ["ramadan", "রমজান"],
    "Offer / Discount": ["offer", "অফার", "discount", "sale", "ছাড়"],
    "Product Launch": ["launch", "new product", "নতুন প্রোডাক্ট"],
    "Restaurant Offer": ["restaurant", "রেস্টুরেন্ট", "menu", "food offer"],
    "Product Promo": ["promo", "promotion", "প্রোমো", "advertisement", "biggapon", "বিজ্ঞাপন"],
}

_PLATFORM_KEYWORDS: dict[str, list[str]] = {
    "facebook_instagram": ["facebook", "fb", "instagram", "insta"],
    "tiktok_reels": ["tiktok", "reels", "reel"],
    "youtube": ["youtube", "yt"],
}

_DURATION_PATTERN = re.compile(r"(\d{1,2})\s*(?:sec|second|seconds|sec\.|s\b|সেকেন্ড)", re.IGNORECASE)

_BUSINESS_NAME_PATTERNS = [
    re.compile(r"\bamar\s+([a-zA-Z0-9ঀ-৿]+)\s+([a-zA-Zঀ-৿]+)\s+business\b", re.IGNORECASE),
    re.compile(r"আমার\s+([a-zA-Z0-9ঀ-৿]+)\s+([a-zA-Zঀ-৿]+)\s+ব্যবসা"),
    re.compile(r"\bmy\s+([a-zA-Z0-9]+)\s+([a-zA-Z]+)\s+(?:business|shop|store)\b", re.IGNORECASE),
]

_NO_VOICEOVER_PATTERN = re.compile(
    r"\bno\s+voice.?over\b|ভয়েসওভার\s+লাগবে না|voice.?over\s+chai\s*na", re.IGNORECASE
)
_NO_CAPTION_PATTERN = re.compile(r"\bno\s+caption\b|caption\s+bad\s+dao|ক্যাপশন\s+বাদ", re.IGNORECASE)
_CTA_PATTERN = re.compile(r"[\"']([^\"']{3,40})[\"']")

_BANGLA_RANGE = re.compile(r"[ঀ-৿]")

# "15 sec na, 20 sec kori" style corrections: an earlier number followed by a
# negation/correction marker, then a new number — the LAST duration found
# wins, which the generic duration pattern already gives us since we always
# take the final match.


def _extract_style(text: str, lower: str) -> list[str]:
    return [
        style
        for style, keywords in _STYLE_KEYWORDS.items()
        if any(kw.lower() in lower or kw in text for kw in keywords)
    ]


def _extract_campaign(text: str, lower: str) -> str | None:
    for campaign, keywords in _CAMPAIGN_KEYWORDS.items():
        if any(kw.lower() in lower or kw in text for kw in keywords):
            return campaign
    return None


def _extract_platform(lower: str) -> str | None:
    for platform, keywords in _PLATFORM_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return platform
    return None


def _extract_duration(text: str) -> int | None:
    matches = _DURATION_PATTERN.findall(text)
    if not matches:
        return None
    try:
        return int(matches[-1])  # last mention wins (handles corrections)
    except ValueError:
        return None


def _extract_business_and_product(text: str) -> tuple[str | None, str | None]:
    for pattern in _BUSINESS_NAME_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(1), match.group(2).lower()
    return None, None


def rule_based_extract(message: str) -> dict:
    """Deterministic, dependency-free extraction used by the mock provider.

    Mirrors the frontend's `lib/chat/parse-input.ts` heuristics so mock-mode
    behavior on the backend matches what local-only mode already did,
    across Bangla, Banglish, English, and mixed-language input.
    """
    text = message.strip()
    lower = text.lower()

    business_name, product_category = _extract_business_and_product(text)

    extracted: dict = {
        "business_name": business_name,
        "business_type": None,
        "product_name": business_name,  # best-effort: the named business IS the product context
        "product_category": product_category,
        "campaign_type": _extract_campaign(text, lower),
        "target_audience": None,
        "duration_seconds": _extract_duration(text),
        "aspect_ratio": None,
        "platform": _extract_platform(lower),
        "style": _extract_style(text, lower),
        "language": "bn" if _BANGLA_RANGE.search(text) else None,
        "captions": False if _NO_CAPTION_PATTERN.search(text) else None,
        "voiceover": False if _NO_VOICEOVER_PATTERN.search(text) else None,
        "music_mood": None,
        "cta": None,
        "notes": None,
    }

    cta_match = _CTA_PATTERN.search(text)
    if cta_match:
        extracted["cta"] = cta_match.group(1)

    # Drop Nones/empties so merge logic only overwrites what was actually found.
    return {k: v for k, v in extracted.items() if v not in (None, [], "")}


class MockChatLLMClient:
    """No network, no API key — fully deterministic. Used when
    `CHATBOT_PROVIDER=mock` (the default), so local dev and CI never need a
    real LLM call.
    """

    async def extract_and_reply(self, message: str, current_input: CreativeInput) -> LLMResult:
        extracted = rule_based_extract(message)
        # `reply` is provided for interface parity only — the orchestrator
        # builds the user-facing reply deterministically from templates.
        return LLMResult(reply="", extracted=extracted)


# --- Real provider (OpenAI-compatible) --------------------------------------


class RealChatLLMClient:
    """A working OpenAI-compatible client, used when
    `CHATBOT_PROVIDER=openai` and `OPENAI_API_KEY` is set.

    Never called unless explicitly configured — the mock provider is the
    default so no accidental paid API usage happens in development.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def extract_and_reply(self, message: str, current_input: CreativeInput) -> LLMResult:
        if not self._settings.openai_api_key:
            logger.warning("RealChatLLMClient invoked without an API key; returning empty extraction.")
            return LLMResult(reply="", extracted={})

        import httpx  # imported lazily so `httpx` isn't a hard dependency for mock-only setups

        payload = {
            "model": self._settings.openai_model,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "message": message,
                            "known_fields": current_input.model_dump(exclude_none=True),
                        }
                    ),
                },
            ],
        }
        base_url = self._settings.openai_base_url or "https://api.openai.com/v1"
        headers = {"Authorization": f"Bearer {self._settings.openai_api_key}"}

        try:
            async with httpx.AsyncClient(timeout=self._settings.openai_timeout_seconds) as client:
                response = await client.post(f"{base_url}/chat/completions", json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                return LLMResult(reply=parsed.get("reply", ""), extracted=parsed.get("extracted", {}))
        except Exception:  # noqa: BLE001 - any provider/network/parse failure degrades to empty extraction
            logger.exception("RealChatLLMClient call failed")
            raise


def get_llm_client(settings: Settings | None = None) -> ChatLLMClient:
    settings = settings or get_settings()
    if settings.chatbot_provider == "openai":
        return RealChatLLMClient(settings)
    return MockChatLLMClient()
