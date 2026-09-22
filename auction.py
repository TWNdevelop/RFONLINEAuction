"""Minimal auction storage backed by SQLite."""

from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path


DEFAULT_DB = Path("auction.sqlite3")


def connect(database: str | Path) -> sqlite3.Connection:
    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS auctions (
            id TEXT PRIMARY KEY,
            text TEXT NOT NULL,
            ends_at TEXT
        );

        CREATE TABLE IF NOT EXISTS bids (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            auction_id TEXT NOT NULL REFERENCES auctions(id),
            nickname TEXT NOT NULL,
            points INTEGER NOT NULL CHECK (points > 0),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    columns = {
        row[1] for row in connection.execute("PRAGMA table_info(auctions)").fetchall()
    }
    if "ends_at" not in columns:
        connection.execute("ALTER TABLE auctions ADD COLUMN ends_at TEXT")
        connection.commit()
    return connection


def create_auction(
    connection: sqlite3.Connection,
    auction_id: str,
    text: str,
    lifetime_minutes: int,
) -> None:
    auction_id = auction_id.strip()
    text = text.strip()
    if not auction_id:
        raise ValueError("auction id cannot be empty")
    if not text:
        raise ValueError("auction text cannot be empty")
    if lifetime_minutes <= 0:
        raise ValueError("auction lifetime must be positive")
    ends_at = datetime.now(UTC) + timedelta(minutes=lifetime_minutes)
    try:
        connection.execute(
            "INSERT INTO auctions (id, text, ends_at) VALUES (?, ?, ?)",
            (auction_id, text, ends_at.isoformat()),
        )
        connection.commit()
    except sqlite3.IntegrityError as error:
        raise ValueError(f"auction already exists: {auction_id}") from error


def place_bid(
    connection: sqlite3.Connection,
    auction_id: str,
    nickname: str,
    points: int,
) -> int:
    nickname = nickname.strip()
    if not nickname:
        raise ValueError("nickname cannot be empty")
    if points <= 0:
        raise ValueError("points must be positive")
    auction = connection.execute(
        "SELECT id, ends_at FROM auctions WHERE id = ?", (auction_id,)
    ).fetchone()
    if auction is None:
        raise ValueError(f"auction not found: {auction_id}")
    if auction["ends_at"] and datetime.now(UTC) >= datetime.fromisoformat(
        auction["ends_at"]
    ):
        raise ValueError("auction has ended")

    cursor = connection.execute(
        "INSERT INTO bids (auction_id, nickname, points) VALUES (?, ?, ?)",
        (auction_id, nickname, points),
    )
    connection.commit()
    return int(cursor.lastrowid)


def get_auction(connection: sqlite3.Connection, auction_id: str):
    auction = connection.execute(
        "SELECT id, text, ends_at FROM auctions WHERE id = ?", (auction_id,)
    ).fetchone()
    if auction is None:
        raise ValueError(f"auction not found: {auction_id}")
    bids = connection.execute(
        """
        SELECT id, nickname, points, created_at
        FROM bids
        WHERE auction_id = ?
        ORDER BY id
        """,
        (auction_id,),
    ).fetchall()
    return auction, bids


def get_winner(connection: sqlite3.Connection, auction_id: str):
    return connection.execute(
        """
        SELECT id, nickname, points, created_at
        FROM bids
        WHERE auction_id = ?
        ORDER BY points DESC, id ASC
        LIMIT 1
        """,
        (auction_id,),
    ).fetchone()


def auction_has_ended(auction, now: datetime | None = None) -> bool:
    if not auction["ends_at"]:
        return False
    return (now or datetime.now(UTC)) >= datetime.fromisoformat(auction["ends_at"])


def list_auctions(connection: sqlite3.Connection):
    return connection.execute(
        """
        SELECT auctions.id, auctions.text, auctions.ends_at,
               COUNT(bids.id) AS bid_count
        FROM auctions
        LEFT JOIN bids ON bids.auction_id = auctions.id
        GROUP BY auctions.id, auctions.text, auctions.ends_at
        ORDER BY auctions.id
        """
    ).fetchall()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="RF Online auction skeleton")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="SQLite file")
    commands = parser.add_subparsers(dest="command", required=True)

    create = commands.add_parser("create", help="create an auction")
    create.add_argument("auction_id")
    create.add_argument("text")
    create.add_argument("lifetime_minutes", type=int)

    bid = commands.add_parser("bid", help="place a bid")
    bid.add_argument("auction_id")
    bid.add_argument("nickname")
    bid.add_argument("points", type=int)

    show = commands.add_parser("show", help="show an auction and its bids")
    show.add_argument("auction_id")

    commands.add_parser("list", help="list auctions")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        with connect(args.db) as connection:
            if args.command == "create":
                create_auction(
                    connection,
                    args.auction_id,
                    args.text,
                    args.lifetime_minutes,
                )
                print(f"Auction created: {args.auction_id}")
            elif args.command == "bid":
                bid_id = place_bid(
                    connection, args.auction_id, args.nickname, args.points
                )
                print(f"Bid saved: {bid_id}")
            elif args.command == "show":
                auction, bids = get_auction(connection, args.auction_id)
                print(f"Auction {auction['id']}: {auction['text']}")
                if not bids:
                    print("No bids")
                for bid in bids:
                    print(
                        f"#{bid['id']} {bid['nickname']}: {bid['points']} "
                        f"({bid['created_at']} UTC)"
                    )
            elif args.command == "list":
                auctions = list_auctions(connection)
                if not auctions:
                    print("No auctions")
                for auction in auctions:
                    print(
                        f"{auction['id']}: {auction['text']} "
                        f"(bids: {auction['bid_count']})"
                    )
        return 0
    except (OSError, ValueError, sqlite3.Error) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
