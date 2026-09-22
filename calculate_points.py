"""Calculate player point totals from this wallet's Solana Memo transactions."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

from solana.rpc.api import Client
from solana.rpc.commitment import Confirmed
from solders.keypair import Keypair
from solders.pubkey import Pubkey


DEVNET_RPC = "https://api.devnet.solana.com"
RPC_MEMO_PREFIX = re.compile(r"^\[\d+\]\s*")


def parse_points_memo(memo: str | None) -> list[tuple[str, int]] | None:
    if not memo:
        return None
    raw_memo = RPC_MEMO_PREFIX.sub("", memo, count=1)
    try:
        raw_players = json.loads(raw_memo)
    except json.JSONDecodeError:
        return None
    if not isinstance(raw_players, list) or not raw_players:
        return None

    players: list[tuple[str, int]] = []
    seen: set[str] = set()
    for item in raw_players:
        if not isinstance(item, list) or len(item) != 2:
            return None
        nickname, points = item
        if not isinstance(nickname, str) or not nickname.strip():
            return None
        if isinstance(points, bool) or not isinstance(points, int) or points <= 0:
            return None
        nickname = nickname.strip()
        nickname_key = nickname.casefold()
        if nickname_key in seen:
            return None
        players.append((nickname, points))
        seen.add(nickname_key)
    return players


def address_from_keypair(path: Path) -> Pubkey:
    with path.open("r", encoding="utf-8") as source:
        secret = json.load(source)
    if not isinstance(secret, list) or not all(isinstance(value, int) for value in secret):
        raise ValueError("keypair file must contain a JSON array of bytes")
    return Keypair.from_bytes(bytes(secret)).pubkey()


def calculate_balances(client: Client, address: Pubkey) -> tuple[dict[str, int], int]:
    balances: defaultdict[str, int] = defaultdict(int)
    display_names: dict[str, str] = {}
    transaction_count = 0
    before = None

    while True:
        response = client.get_signatures_for_address(
            address,
            before=before,
            limit=1_000,
            commitment=Confirmed,
        )
        signatures = response.value
        if not signatures:
            break

        for signature_info in signatures:
            if signature_info.err is not None:
                continue
            players = parse_points_memo(signature_info.memo)
            if players is None:
                continue
            transaction_count += 1
            for nickname, points in players:
                key = nickname.casefold()
                display_names.setdefault(key, nickname)
                balances[key] += points

        if len(signatures) < 1_000:
            break
        before = signatures[-1].signature

    result = {display_names[key]: points for key, points in balances.items()}
    return result, transaction_count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sum player points from list transactions in Solana Devnet."
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--keypair", type=Path, help="Solana keypair JSON file")
    source.add_argument("--address", help="public Solana wallet address")
    parser.add_argument("--rpc", default=DEVNET_RPC, help="Solana RPC URL")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        address = (
            address_from_keypair(args.keypair)
            if args.keypair is not None
            else Pubkey.from_string(args.address)
        )
        client = Client(args.rpc, commitment=Confirmed)
        balances, transaction_count = calculate_balances(client, address)
        print(f"Wallet: {address}")
        print(f"List transactions: {transaction_count}")
        if not balances:
            print("No player lists found")
            return 0

        nickname_width = max(len("Nickname"), *(len(name) for name in balances))
        print(f"{'Nickname':<{nickname_width}}  Points")
        print(f"{'-' * nickname_width}  ------")
        for nickname in sorted(balances, key=str.casefold):
            print(f"{nickname:<{nickname_width}}  {balances[nickname]}")
        return 0
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
