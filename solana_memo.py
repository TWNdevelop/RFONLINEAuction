"""Shared helper for sending one signed Memo transaction to Solana."""

from __future__ import annotations

import json
from pathlib import Path


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


def send_memo(memo: bytes, keypair_path: Path, rpc_url: str = DEVNET_RPC) -> str:
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
        memo,
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
