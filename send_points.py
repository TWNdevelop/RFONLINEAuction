"""Send player point accrual records to the Solana Memo program on Devnet."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from points_data import load_batch, memo_bytes


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


def send_batch(batch, keypair_path: Path, rpc_url: str) -> list[str]:
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

    memo_program = Pubkey.from_string(MEMO_PROGRAM_ID)
    signatures: list[str] = []
    for number, player in enumerate(batch.players, start=1):
        instruction = Instruction(
            memo_program,
            memo_bytes(batch.operation_id, player),
            [AccountMeta(payer.pubkey(), True, False)],
        )
        blockhash = client.get_latest_blockhash(Confirmed).value.blockhash
        message = Message.new_with_blockhash(
            [instruction], payer.pubkey(), blockhash
        )
        transaction = Transaction.new_unsigned(message)
        transaction.sign([payer], blockhash)
        response = client.send_transaction(
            transaction,
            opts=TxOpts(skip_preflight=False, preflight_commitment=Confirmed),
        )
        transaction_signature = response.value
        signature = str(transaction_signature)
        confirmation = client.confirm_transaction(
            transaction_signature, commitment=Confirmed
        )
        if confirmation.value[0].err is not None:
            raise RuntimeError(f"transaction failed: {signature}")
        signatures.append(signature)
        print(f"[{number}/{len(batch.players)}] {player.nickname}: {signature}")

    return signatures


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a points JSON file and write its records to Solana Devnet."
    )
    parser.add_argument("json_file", type=Path, help="path to the points JSON file")
    parser.add_argument(
        "--keypair",
        type=Path,
        help="Solana keypair JSON file; required unless --dry-run is used",
    )
    parser.add_argument("--rpc", default=DEVNET_RPC, help="Solana RPC URL")
    parser.add_argument(
        "--dry-run", action="store_true", help="validate and print records without sending"
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        batch = load_batch(args.json_file)
        print(f"Operation: {batch.operation_id}; players: {len(batch.players)}")
        if args.dry_run:
            for player in batch.players:
                print(memo_bytes(batch.operation_id, player).decode("utf-8"))
            return 0
        if args.keypair is None:
            raise ValueError("--keypair is required when sending transactions")
        signatures = send_batch(batch, args.keypair, args.rpc)
        print(f"Sent {len(signatures)} records to Solana Devnet")
        return 0
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
