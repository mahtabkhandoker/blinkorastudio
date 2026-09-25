"""Conversation persistence, behind a small repository interface.

An in-memory implementation is used for now (per spec section 21:
"choose one: in-memory for dev, or SQLite/Postgres if a backend DB
already exists" — this repo has no existing database, so in-memory is
the correct default). The orchestrator/routes only depend on the
`ConversationRepository` protocol, so swapping in a real database later
means writing one new class, not touching call sites.
"""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, Field


class StoredMessage(BaseModel):
    request_id: str | None
    message: str
    reply: str


class ConversationRecord(BaseModel):
    conversation_id: str
    messages: list[StoredMessage] = Field(default_factory=list)
    seen_request_ids: set[str] = Field(default_factory=set)


class ConversationRepository(Protocol):
    async def get(self, conversation_id: str) -> ConversationRecord | None: ...
    async def append_message(
        self, conversation_id: str, request_id: str | None, message: str, reply: str
    ) -> None: ...
    async def has_seen(self, conversation_id: str, request_id: str) -> bool: ...


class InMemoryConversationRepository:
    """Process-local store. Resets on restart — fine for dev/demo; a real
    deployment should swap this for a database-backed implementation.
    """

    def __init__(self) -> None:
        self._records: dict[str, ConversationRecord] = {}

    async def get(self, conversation_id: str) -> ConversationRecord | None:
        return self._records.get(conversation_id)

    async def append_message(
        self, conversation_id: str, request_id: str | None, message: str, reply: str
    ) -> None:
        record = self._records.setdefault(
            conversation_id, ConversationRecord(conversation_id=conversation_id)
        )
        record.messages.append(StoredMessage(request_id=request_id, message=message, reply=reply))
        if request_id:
            record.seen_request_ids.add(request_id)

    async def has_seen(self, conversation_id: str, request_id: str) -> bool:
        record = self._records.get(conversation_id)
        return bool(record and request_id in record.seen_request_ids)


_repository = InMemoryConversationRepository()


def get_conversation_repository() -> ConversationRepository:
    return _repository
