"""Order persistence behind a small Protocol.

`JsonFileOrderRepository` is development persistence: one JSON file per
order, so orders survive a server restart and can be inspected by hand.
It is single-process and is not a substitute for the planned PostgreSQL
store; swapping that in means implementing `OrderRepository`.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Protocol

from app.models.orders import Order

_SAFE_ID = re.compile(r"^[A-Za-z0-9\-]{8,64}$")


class OrderRepository(Protocol):
    def get(self, order_id: str) -> Order | None: ...

    def save(self, order: Order) -> None: ...

    def next_number(self) -> str: ...


def _format_number(sequence: int) -> str:
    return f"ORD-{sequence:06d}"


class InMemoryOrderRepository:
    def __init__(self) -> None:
        self._orders: dict[str, str] = {}
        self._sequence = 0

    def get(self, order_id: str) -> Order | None:
        raw = self._orders.get(order_id)
        return Order.model_validate_json(raw) if raw else None

    def save(self, order: Order) -> None:
        self._orders[order.id] = order.model_dump_json()

    def next_number(self) -> str:
        self._sequence += 1
        return _format_number(self._sequence)


class JsonFileOrderRepository:
    def __init__(self, root: Path) -> None:
        self._root = root
        self._root.mkdir(parents=True, exist_ok=True)
        self._sequence_file = self._root / "_sequence"

    def _path(self, order_id: str) -> Path | None:
        if not _SAFE_ID.match(order_id):
            return None
        return self._root / f"{order_id}.json"

    def get(self, order_id: str) -> Order | None:
        path = self._path(order_id)
        if path is None or not path.exists():
            return None
        return Order.model_validate_json(path.read_text(encoding="utf-8"))

    def save(self, order: Order) -> None:
        path = self._path(order.id)
        if path is None:
            raise ValueError("unsafe order id")
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(order.model_dump_json(indent=2), encoding="utf-8")
        os.replace(tmp, path)

    def next_number(self) -> str:
        current = 0
        if self._sequence_file.exists():
            try:
                current = int(self._sequence_file.read_text().strip() or 0)
            except ValueError:
                current = 0
        current += 1
        self._sequence_file.write_text(str(current))
        return _format_number(current)
