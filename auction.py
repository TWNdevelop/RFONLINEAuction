"""Minimal auction storage backed by SQLite."""

from __future__ import annotations

import argparse
import sqlite3
import sys
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
            text TEXT NOT NULL
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
    return connection


def create_auction(connection: sqlite3.Connection, auction_id: str, text: str) -> None:
    auction_id = auction_id.strip()
    text = text.strip()
    if not auction_id:
        raise ValueError("auction id cannot be empty")
    if not text:
        raise ValueError("auction text cannot be empty")
    try:
        connection.execute(
            "INSERT INTO auctions (id, text) VALUES (?, ?)",
            (auction_id, text),
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
        "SELECT id FROM auctions WHERE id = ?", (auction_id,)
    ).fetchone()
    if auction is None:
        raise ValueError(f"auction not found: {auction_id}")

    cursor = connection.execute(
        "INSERT INTO bids (auction_id, nickname, points) VALUES (?, ?, ?)",
        (auction_id, nickname, points),
    )
    connection.commit()
    return int(cursor.lastrowid)


def get_auction(connection: sqlite3.Connection, auction_id: str):
    auction = connection.execute(
        "SELECT id, text FROM auctions WHERE id = ?", (auction_id,)
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


def list_auctions(connection: sqlite3.Connection):
    return connection.execute(
        """
        SELECT auctions.id, auctions.text, COUNT(bids.id) AS bid_count
        FROM auctions
        LEFT JOIN bids ON bids.auction_id = auctions.id
        GROUP BY auctions.id, auctions.text
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
                create_auction(connection, args.auction_id, args.text)
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
