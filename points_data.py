"""Validation and deterministic hashing of a player points list."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


MAX_PLAYERS = 50
MAX_NICKNAME_BYTES = 64


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


def canonical_json_bytes(players: tuple[PlayerPoints, ...]) -> bytes:
    """Return stable JSON bytes so input order and formatting do not affect the hash."""
    canonical_players = [
        {"nickname": player.nickname, "points": player.points}
        for player in sorted(players, key=lambda player: player.nickname.casefold())
    ]
    return json.dumps(
        canonical_players,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def calculate_hash(players: tuple[PlayerPoints, ...]) -> str:
    return hashlib.sha256(canonical_json_bytes(players)).hexdigest()


def memo_bytes(players: tuple[PlayerPoints, ...]) -> bytes:
    return f"RFOA1:{calculate_hash(players)}".encode("ascii")
