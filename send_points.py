"""Write a complete player points list to one Solana Devnet transaction."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from points_data import load_players, memo_bytes
from solana_memo import DEVNET_RPC, send_memo


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write a player points JSON list to one Solana Devnet transaction."
    )
    parser.add_argument("json_file", type=Path, help="path to the player points JSON file")
    parser.add_argument(
        "--keypair",
        type=Path,
        help="Solana keypair JSON file; required unless --dry-run is used",
    )
    parser.add_argument("--rpc", default=DEVNET_RPC, help="Solana RPC URL")
    parser.add_argument(
        "--dry-run", action="store_true", help="validate and encode without sending"
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        players = load_players(args.json_file)
        memo = memo_bytes(players)
        print(f"Players: {len(players)}")
        print(f"Memo bytes: {len(memo)}")
        print(f"Memo: {memo.decode('utf-8')}")
        if args.dry_run:
            return 0
        if args.keypair is None:
            raise ValueError("--keypair is required when sending a transaction")

        signature = send_memo(memo, args.keypair, args.rpc)
        print("Sent 1 transaction to Solana Devnet")
        print(f"Signature: {signature}")
        print(f"Explorer: https://explorer.solana.com/tx/{signature}?cluster=devnet")
        return 0
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
