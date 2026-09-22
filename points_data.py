"""Validation and encoding for player point accrual records."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


MAX_NICKNAME_BYTES = 64
MAX_OPERATION_ID_BYTES = 64


@dataclass(frozen=True)
class PlayerAccrual:
    player_id: int
    nickname: str
    points: int


@dataclass(frozen=True)
class AccrualBatch:
    operation_id: str
    players: tuple[PlayerAccrual, ...]


def _required_text(value: Any, field: str, max_bytes: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    value = value.strip()
    if len(value.encode("utf-8")) > max_bytes:
        raise ValueError(f"{field} is longer than {max_bytes} UTF-8 bytes")
    return value


def load_batch(path: str | Path) -> AccrualBatch:
    with Path(path).open("r", encoding="utf-8") as source:
        raw = json.load(source)

    if not isinstance(raw, dict):
        raise ValueError("JSON root must be an object")

    operation_id = _required_text(
        raw.get("operation_id"), "operation_id", MAX_OPERATION_ID_BYTES
    )
    raw_players = raw.get("players")
    if not isinstance(raw_players, list) or not raw_players:
        raise ValueError("players must be a non-empty list")

    players: list[PlayerAccrual] = []
    seen_ids: set[int] = set()
    for index, item in enumerate(raw_players):
        prefix = f"players[{index}]"
        if not isinstance(item, dict):
            raise ValueError(f"{prefix} must be an object")

        player_id = item.get("player_id")
        points = item.get("points")
        if isinstance(player_id, bool) or not isinstance(player_id, int) or player_id <= 0:
            raise ValueError(f"{prefix}.player_id must be a positive integer")
        if player_id in seen_ids:
            raise ValueError(f"duplicate player_id in batch: {player_id}")
        if isinstance(points, bool) or not isinstance(points, int) or points <= 0:
            raise ValueError(f"{prefix}.points must be a positive integer")

        nickname = _required_text(
            item.get("nickname"), f"{prefix}.nickname", MAX_NICKNAME_BYTES
        )
        players.append(PlayerAccrual(player_id, nickname, points))
        seen_ids.add(player_id)

    return AccrualBatch(operation_id, tuple(players))


def memo_bytes(operation_id: str, player: PlayerAccrual) -> bytes:
    record = {
        "v": 1,
        "type": "points_accrual",
        "operation_id": operation_id,
        "player_id": player.player_id,
        "nickname": player.nickname,
        "points": player.points,
    }
    return json.dumps(
        record, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
