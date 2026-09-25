"""POST /api/creative-plan — builds a brief from a given state on demand.

The chat endpoint already returns `creative_brief` inline once ready;
this endpoint exists for cases that need to (re)build a brief without
sending a chat message (e.g. a "review my plan" UI affordance, or tests).
"""

from __future__ import annotations

from fastapi import APIRouter

from app.models.assets import AssetInfo
from app.models.creative import CreativeBrief, CreativeInput
from app.services.chatbot.brief_builder import build_creative_brief

router = APIRouter(prefix="/api/creative-plan", tags=["creative-plan"])


class CreativePlanRequest(CreativeInput):
    assets: list[AssetInfo] = []


@router.post("", response_model=CreativeBrief)
async def post_creative_plan(request: CreativePlanRequest) -> CreativeBrief:
    creative_input = CreativeInput(**request.model_dump(exclude={"assets"}))
    return build_creative_brief(creative_input, request.assets)
