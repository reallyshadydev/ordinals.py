"""Local .wallet.json wallet (compatible with ordinals.js format)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from embit import ec
from embit.script import Script

from .networks import COIN
from .script_builder import address_to_script_pubkey


def wallet_path() -> Path:
    return Path(os.environ.get("WALLET", ".wallet.json"))


def load_wallet() -> dict[str, Any]:
    path = wallet_path()
    if not path.is_file():
        raise FileNotFoundError(f"wallet not found at {path}. Run: python -m ordinals_py wallet new")
    return json.loads(path.read_text())


def save_wallet(wallet: dict[str, Any]) -> None:
    wallet_path().write_text(json.dumps(wallet, indent=2) + "\n")


def wallet_balance(wallet: dict[str, Any]) -> int:
    return sum(u["satoshis"] for u in wallet["utxos"])


def new_wallet(
    wif: str,
    address: str,
    script_hex: str,
    *,
    coin: str,
    testnet: bool,
    address_type: str,
) -> dict:
    return {
        "privkey": wif,
        "address": address,
        "script": script_hex,
        "addressType": address_type,
        "network": coin,
        "testnet": testnet,
        "utxos": [],
    }


def sync_wallet(wallet: dict[str, Any], rpc) -> dict[str, Any]:
    utxos = rpc.call("listunspent", [0, 9999999, [wallet["address"]]])
    wallet["utxos"] = [
        {
            "txid": u["txid"],
            "vout": u["vout"],
            "script": u["scriptPubKey"],
            "satoshis": int(round(float(u["amount"]) * COIN)),
        }
        for u in utxos
    ]
    save_wallet(wallet)
    return wallet


def wallet_script_pubkey(wallet: dict[str, Any]) -> bytes:
    """Standard P2PKH scriptPubKey for this wallet (not embit Script.serialize())."""
    return address_to_script_pubkey(wallet["address"])


def update_wallet_from_tx(wallet: dict[str, Any], tx, txid_hex: str) -> None:
    """Remove spent UTXOs and add change outputs (matches ordinals.js updateWallet)."""
    spent = {(inp.txid.hex(), inp.vout) for inp in tx.vin}
    wallet["utxos"] = [u for u in wallet["utxos"] if (u["txid"], u["vout"]) not in spent]

    wallet_script = wallet_script_pubkey(wallet).hex()
    for vout, out in enumerate(tx.vout):
        if out.script_pubkey.data == bytes.fromhex(wallet_script):
            wallet["utxos"].append(
                {
                    "txid": txid_hex,
                    "vout": vout,
                    "script": wallet_script,
                    "satoshis": out.value,
                }
            )

