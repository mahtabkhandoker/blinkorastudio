"""Generation endpoints — idempotent stub, never calls a real paid
provider (see services/generations/service.py). Not yet called by the
frontend, which still runs its own local mock-generation timer.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.models.generation import GenerationRequest, GenerationResponse
from app.services.generations.service import InMemoryGenerationService, get_generation_service

router = APIRouter(prefix="/api/generations", tags=["generations"])


@router.post("", response_model=GenerationResponse)
async def post_generation(
    request: GenerationRequest,
    service: InMemoryGenerationService = Depends(get_generation_service),
) -> GenerationResponse:
    return service.submit(request)


@router.get("/{generation_id}", response_model=GenerationResponse)
async def get_generation(
    generation_id: str,
    service: InMemoryGenerationService = Depends(get_generation_service),
) -> GenerationResponse:
    result = service.get(generation_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Generation not found")
    return result
