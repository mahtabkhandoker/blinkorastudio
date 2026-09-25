"""Generation orchestration stub.

This NEVER calls a real paid video-generation provider — see
`Settings.video_generation_provider`, which stays "mock" unless a real
integration is deliberately wired in later. Its job right now is to give
the idempotency contract (spec section 20) a real, testable
implementation: submitting the same `idempotency_key` twice returns the
same record instead of creating a second one.

Not currently called by the frontend (which still runs its own local
mock-generation timer for the progress UI) — see the integration report
for why.
"""

from __future__ import annotations

import uuid

from app.models.generation import GenerationRecord, GenerationRequest, GenerationResponse


class InMemoryGenerationService:
    def __init__(self) -> None:
        self._by_idempotency_key: dict[str, GenerationRecord] = {}

    def submit(self, request: GenerationRequest) -> GenerationResponse:
        existing = self._by_idempotency_key.get(request.idempotency_key)
        if existing:
            return GenerationResponse(
                id=existing.id,
                status=existing.status,
                progress=existing.progress,
                video_url=existing.video_url,
                error=existing.error,
                deduplicated=True,
            )

        record = GenerationRecord(
            id=f"gen_{uuid.uuid4().hex[:12]}",
            conversation_id=request.conversation_id,
            idempotency_key=request.idempotency_key,
            status="QUEUED",
            progress=0,
        )
        self._by_idempotency_key[request.idempotency_key] = record
        return GenerationResponse(
            id=record.id, status=record.status, progress=record.progress, deduplicated=False
        )

    def get(self, generation_id: str) -> GenerationResponse | None:
        for record in self._by_idempotency_key.values():
            if record.id == generation_id:
                return GenerationResponse(
                    id=record.id,
                    status=record.status,
                    progress=record.progress,
                    video_url=record.video_url,
                    error=record.error,
                )
        return None


_service = InMemoryGenerationService()


def get_generation_service() -> InMemoryGenerationService:
    return _service
