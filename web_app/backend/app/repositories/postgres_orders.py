"""PostgreSQL-backed `OrderRepository`.

The order aggregate (answers, plan, assets metadata, generation,
feedback, events — all typed by `app/models/orders.py`) is stored as one
JSONB document per row; `owner_user_id`, `number`, `channel` and `status`
are promoted to real columns because authorization checks and the "my
orders" listing filter on them. See `app/db/models.py` for the full
rationale.

`locked()` is the one place this repository differs from the
memory/file ones in a way that matters for correctness: it holds a
`SELECT ... FOR UPDATE` row lock for the entire confirm-plan critical
section, across worker processes, so two concurrent confirmations of the
same order revision can never both submit generation jobs.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import OrderRecord, OrderSequence
from app.db.session import get_session_factory
from app.models.orders import Order
from app.repositories.orders import _format_number


def _to_order(row: OrderRecord) -> Order:
    return Order.model_validate(row.data)


def _apply(row: OrderRecord, order: Order) -> None:
    row.number = order.number
    row.owner_user_id = order.owner_user_id
    row.channel = order.channel
    row.status = order.status
    row.data = order.model_dump(mode="json")


class PostgresOrderRepository:
    def __init__(self) -> None:
        self._sessions = get_session_factory()

    def get(self, order_id: str) -> Order | None:
        with self._sessions() as session:
            row = session.get(OrderRecord, order_id)
            return _to_order(row) if row else None

    def save(self, order: Order) -> None:
        with self._sessions() as session:
            row = session.get(OrderRecord, order.id)
            if row is None:
                row = OrderRecord(id=order.id, number=order.number, owner_user_id=order.owner_user_id, data={})
                session.add(row)
            _apply(row, order)
            session.commit()

    def next_number(self) -> str:
        with self._sessions() as session:
            row = session.scalar(select(OrderSequence).where(OrderSequence.id == 1).with_for_update())
            if row is None:
                row = OrderSequence(id=1, value=0)
                session.add(row)
                session.flush()
            row.value += 1
            session.commit()
            return _format_number(row.value)

    def list_by_owner(self, owner_user_id: str) -> list[Order]:
        with self._sessions() as session:
            rows = session.scalars(
                select(OrderRecord)
                .where(OrderRecord.owner_user_id == owner_user_id)
                .order_by(OrderRecord.updated_at.desc())
            ).all()
            return [_to_order(row) for row in rows]

    @contextmanager
    def locked(self, order_id: str) -> Iterator[tuple[Order | None, Callable[[Order], None]]]:
        session: Session = self._sessions()
        try:
            with session.begin():
                row = session.scalar(select(OrderRecord).where(OrderRecord.id == order_id).with_for_update())
                order = _to_order(row) if row else None

                def _save(updated: Order) -> None:
                    nonlocal row
                    if row is None:
                        row = OrderRecord(id=updated.id, number=updated.number, owner_user_id=updated.owner_user_id, data={})
                        session.add(row)
                    _apply(row, updated)

                yield order, _save
            # `session.begin()` committed here, releasing the row lock.
        finally:
            session.close()
