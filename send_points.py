"""Write a complete player points list to one Solana Devnet transaction."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from points_data import load_players, memo_bytes


DEVNET_RPC = "https://api.devnet.solana.com"
MEMO_PROGRAM_ID = "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr"


def load_keypair(path: Path):
    try:
        from solders.keypair import Keypair
    except ImportError as error:
        raise RuntimeError(
            "Dependencies are missing. Run: python -m pip install -r requirements.txt"
        ) from error

    with path.open("r", encoding="utf-8") as source:
        secret = json.load(source)
    if not isinstance(secret, list) or not all(isinstance(value, int) for value in secret):
        raise ValueError("keypair file must contain a JSON array of bytes")
    return Keypair.from_bytes(bytes(secret))


def send_hash(players, keypair_path: Path, rpc_url: str) -> str:
    from solana.rpc.api import Client
    from solana.rpc.commitment import Confirmed
    from solana.rpc.types import TxOpts
    from solders.instruction import AccountMeta, Instruction
    from solders.message import Message
    from solders.pubkey import Pubkey
    from solders.transaction import Transaction

    payer = load_keypair(keypair_path)
    client = Client(rpc_url, commitment=Confirmed)
    if not client.is_connected():
        raise RuntimeError(f"cannot connect to Solana RPC: {rpc_url}")

    instruction = Instruction(
        Pubkey.from_string(MEMO_PROGRAM_ID),
        memo_bytes(players),
        [AccountMeta(payer.pubkey(), True, False)],
    )
    blockhash = client.get_latest_blockhash(Confirmed).value.blockhash
    message = Message.new_with_blockhash([instruction], payer.pubkey(), blockhash)
    transaction = Transaction.new_unsigned(message)
    transaction.sign([payer], blockhash)
    response = client.send_transaction(
        transaction,
        opts=TxOpts(skip_preflight=False, preflight_commitment=Confirmed),
    )
    transaction_signature = response.value
    confirmation = client.confirm_transaction(
        transaction_signature, commitment=Confirmed
    )
    if confirmation.value[0].err is not None:
        raise RuntimeError(f"transaction failed: {transaction_signature}")
    return str(transaction_signature)


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

        signature = send_hash(players, args.keypair, args.rpc)
        print("Sent 1 transaction to Solana Devnet")
        print(f"Signature: {signature}")
        print(f"Explorer: https://explorer.solana.com/tx/{signature}?cluster=devnet")
        return 0
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
