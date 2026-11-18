"""Optional, safe migration of old JSON-file dev orders into Postgres.

Pre-P0.5, `ORDER_STORE=file` wrote one JSON file per order under
`storage/orders/`. Those files have no `owner_user_id` (that field didn't
exist yet), so they can't be loaded as a modern `Order` directly. This
script assigns every order found there to one account you name, then
inserts it into the `orders` table.

Safety:
* Never writes, moves or deletes the source JSON files.
* Never overwrites a row that already exists in Postgres for that order
  id — it skips it and reports that it did, so re-running is harmless.
* Dry-run by default; pass --apply to actually write.

Usage:
    python -m scripts.migrate_json_orders --owner-user-id <uuid> \\
        --storage-dir ./storage/orders [--apply]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.db.models import OrderRecord, User
from app.db.session import session_scope
from app.models.orders import Order


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--storage-dir", default="./storage/orders", help="Directory of *.json order files")
    parser.add_argument("--owner-user-id", required=True, help="Existing user id every migrated order is assigned to")
    parser.add_argument("--apply", action="store_true", help="Actually write; without this, only reports what would happen")
    args = parser.parse_args()

    root = Path(args.storage_dir)
    if not root.is_dir():
        print(f"No such directory: {root}", file=sys.stderr)
        return 1

    with session_scope() as session:
        if session.get(User, args.owner_user_id) is None:
            print(f"No user with id {args.owner_user_id!r} — create the account first.", file=sys.stderr)
            return 1

        migrated, skipped_existing, skipped_invalid = 0, 0, 0
        for path in sorted(root.glob("*.json")):
            raw = path.read_text(encoding="utf-8")
            try:
                import json

                data = json.loads(raw)
            except ValueError:
                print(f"  skip (not JSON): {path.name}")
                skipped_invalid += 1
                continue

            data.setdefault("owner_user_id", args.owner_user_id)
            try:
                order = Order.model_validate(data)
            except Exception as exc:  # noqa: BLE001 - report and keep going
                print(f"  skip (invalid order): {path.name}: {exc}")
                skipped_invalid += 1
                continue

            if session.get(OrderRecord, order.id) is not None:
                print(f"  skip (already in Postgres): {order.number} ({order.id})")
                skipped_existing += 1
                continue

            print(f"  {'migrate' if args.apply else 'would migrate'}: {order.number} ({order.id})")
            if args.apply:
                session.add(
                    OrderRecord(
                        id=order.id,
                        number=order.number,
                        owner_user_id=order.owner_user_id,
                        channel=order.channel,
                        status=order.status,
                        data=order.model_dump(mode="json"),
                    )
                )
            migrated += 1

        if args.apply:
            session.commit()

    mode = "Migrated" if args.apply else "Would migrate"
    print(f"\n{mode}: {migrated}. Already in Postgres: {skipped_existing}. Invalid/skipped: {skipped_invalid}.")
    if not args.apply:
        print("Dry run — nothing was written. Re-run with --apply to commit.")
    print(f"Source JSON files in {root} were not modified or deleted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
