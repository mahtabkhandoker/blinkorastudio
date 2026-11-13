"""Video generation provider interface.

Order code depends only on `VideoGenerationProvider`. The only
implementation is `MockVideoProvider`, which calls nothing external and
produces no video. Adding a real provider means adding a class here and a
branch in `get_video_provider`; nothing else needs to know its name.

No paid provider is wired in. `get_video_provider` refuses any other
configured value rather than guessing, so a typo in an env file can never
start paid generation.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Protocol

from app.core.config import Settings


@dataclass(frozen=True)
class ShotGenerationRequest:
    client_reference: str  # unique per shot attempt; lets a provider dedupe
    prompt: str
    negative_prompt: str
    image_storage_key: str | None
    aspect_ratio: str
    duration_seconds: int
    resolution: str


@dataclass(frozen=True)
class ProviderJobStatus:
    status: str  # QUEUED | RUNNING | SUCCEEDED | FAILED
    error: str | None = None
    output_url: str | None = None


class VideoGenerationProvider(Protocol):
    name: str
    is_simulated: bool

    def submit(self, request: ShotGenerationRequest) -> str:
        """Starts one clip and returns the provider's job id."""
        ...

    def get_status(self, provider_job_id: str) -> ProviderJobStatus: ...


class MockVideoProvider:
    """Pretends to run a job for a few seconds. Never produces a video.

    The submit time is encoded in the job id, so status survives a server
    restart without the provider keeping any state of its own.
    """

    name = "mock"
    is_simulated = True

    def __init__(self, run_seconds: float = 8.0) -> None:
        self._run_seconds = max(run_seconds, 0.0)
        self.submitted: list[ShotGenerationRequest] = []

    def submit(self, request: ShotGenerationRequest) -> str:
        self.submitted.append(request)
        return f"mock-{int(time.time() * 1000)}-{uuid.uuid4().hex[:8]}"

    def get_status(self, provider_job_id: str) -> ProviderJobStatus:
        try:
            started_ms = int(provider_job_id.split("-")[1])
        except (IndexError, ValueError):
            return ProviderJobStatus(status="FAILED", error="unknown mock job")
        elapsed = time.time() - started_ms / 1000
        if elapsed >= self._run_seconds:
            return ProviderJobStatus(status="SUCCEEDED")  # no output_url: nothing was made
        if elapsed >= self._run_seconds * 0.2:
            return ProviderJobStatus(status="RUNNING")
        return ProviderJobStatus(status="QUEUED")


def get_video_provider(settings: Settings) -> VideoGenerationProvider:
    if settings.video_generation_provider == "mock":
        return MockVideoProvider(run_seconds=settings.mock_generation_seconds)
    raise RuntimeError(
        f"VIDEO_GENERATION_PROVIDER='{settings.video_generation_provider}' is not supported. "
        "Only 'mock' exists; paid providers are not wired in."
    )
