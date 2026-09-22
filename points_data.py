"""Validation and deterministic hashing of a player points list."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


MAX_PLAYERS = 50
MAX_NICKNAME_BYTES = 64
MAX_MEMO_BYTES = 1_000


@dataclass(frozen=True)
class PlayerPoints:
    nickname: str
    points: int


def _nickname(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    value = value.strip()
    if len(value.encode("utf-8")) > MAX_NICKNAME_BYTES:
        raise ValueError(f"{field} is longer than {MAX_NICKNAME_BYTES} UTF-8 bytes")
    return value


def load_players(path: str | Path) -> tuple[PlayerPoints, ...]:
    with Path(path).open("r", encoding="utf-8") as source:
        raw = json.load(source)

    if not isinstance(raw, list) or not raw:
        raise ValueError("JSON root must be a non-empty list")
    if len(raw) > MAX_PLAYERS:
        raise ValueError(f"the list cannot contain more than {MAX_PLAYERS} players")

    players: list[PlayerPoints] = []
    seen_nicknames: set[str] = set()
    for index, item in enumerate(raw):
        prefix = f"players[{index}]"
        if not isinstance(item, dict):
            raise ValueError(f"{prefix} must be an object")
        if set(item) != {"nickname", "points"}:
            raise ValueError(f"{prefix} must contain only nickname and points")

        nickname = _nickname(item["nickname"], f"{prefix}.nickname")
        nickname_key = nickname.casefold()
        if nickname_key in seen_nicknames:
            raise ValueError(f"duplicate nickname in list: {nickname}")

        points = item["points"]
        if isinstance(points, bool) or not isinstance(points, int) or points <= 0:
            raise ValueError(f"{prefix}.points must be a positive integer")

        players.append(PlayerPoints(nickname, points))
        seen_nicknames.add(nickname_key)

    return tuple(players)


def memo_bytes(players: tuple[PlayerPoints, ...]) -> bytes:
    """Encode the complete list as compact JSON for one Solana Memo transaction."""
    compact_players = [
        [player.nickname, player.points]
        for player in sorted(players, key=lambda player: player.nickname.casefold())
    ]
    encoded = json.dumps(
        compact_players,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    if len(encoded) > MAX_MEMO_BYTES:
        raise ValueError(
            f"the complete list is {len(encoded)} bytes; maximum is {MAX_MEMO_BYTES}"
        )
    return encoded
