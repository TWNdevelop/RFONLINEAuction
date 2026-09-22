"""Watch ended auctions and write their winning results to Solana Devnet."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable

from auction import DEFAULT_DB, connect, get_winner
from solana_memo import DEVNET_RPC, send_memo


def result_memo(nickname: str, points: int, item: str) -> bytes:
    return json.dumps(
        [nickname, -points, item],
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")


def finalize_ready_auctions(
    connection: sqlite3.Connection,
    sender: Callable[[bytes], str],
    now: datetime | None = None,
) -> list[tuple[str, str | None]]:
    current_time = (now or datetime.now(UTC)).isoformat()
    auctions = connection.execute(
        """
        SELECT id, text
        FROM auctions
        WHERE finalized = 0 AND ends_at IS NOT NULL AND ends_at <= ?
        ORDER BY ends_at
        """,
        (current_time,),
    ).fetchall()

    results: list[tuple[str, str | None]] = []
    for auction in auctions:
        winner = get_winner(connection, auction["id"])
        if winner is None:
            connection.execute(
                "UPDATE auctions SET finalized = 1 WHERE id = ?", (auction["id"],)
            )
            connection.commit()
            results.append((auction["id"], None))
            continue

        memo = result_memo(winner["nickname"], winner["points"], auction["text"])
        signature = sender(memo)
        connection.execute(
            """
            UPDATE auctions
            SET finalized = 1, result_signature = ?
            WHERE id = ?
            """,
            (signature, auction["id"]),
        )
        connection.commit()
        results.append((auction["id"], signature))
    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write ended auction results to Solana Devnet."
    )
    parser.add_argument("--keypair", type=Path, required=True)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--rpc", default=DEVNET_RPC)
    parser.add_argument("--interval", type=float, default=5.0)
    parser.add_argument("--once", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        while True:
            with closing(connect(args.db)) as connection:
                results = finalize_ready_auctions(
                    connection,
                    lambda memo: send_memo(memo, args.keypair, args.rpc),
                )
            for auction_id, signature in results:
                if signature:
                    print(f"Auction {auction_id}: {signature}", flush=True)
                else:
                    print(f"Auction {auction_id}: no bids", flush=True)
            if args.once:
                return 0
            time.sleep(args.interval)
    except KeyboardInterrupt:
        return 0
    except (OSError, ValueError, RuntimeError, sqlite3.Error) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
