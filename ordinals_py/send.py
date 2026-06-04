"""Send a wallet UTXO (e.g. inscription output) to another address."""

from __future__ import annotations

from embit import ec
from embit.script import Script, script_sig_p2pkh
from embit.transaction import SIGHASH, Transaction, TransactionInput, TransactionOutput

from .inscribe import _tx_fee, _txid_bytes
from .networks import INSCRIPTION_OUTPUT_SATS
from .script_builder import address_to_script_pubkey
from .wallet import wallet_script_pubkey


def send_utxo(
    wallet: dict,
    dest_address: str,
    *,
    privkey: ec.PrivateKey,
    fee_per_kb: int,
    tx_version: int,
    txid: str | None = None,
    vout: int | None = None,
) -> Transaction:
    """Send inscription on a 0.001 (100k sat) output; return the rest as change."""
    utxos = wallet["utxos"]
    if not utxos:
        raise RuntimeError("no UTXOs in wallet")

    if txid is not None:
        utxo = next((u for u in utxos if u["txid"] == txid and u["vout"] == vout), None)
        if utxo is None:
            raise RuntimeError(f"UTXO {txid}:{vout} not in wallet")
    else:
        if len(utxos) != 1:
            raise RuntimeError("multiple UTXOs — specify txid:vout")
        utxo = utxos[0]

    dest_script = Script(address_to_script_pubkey(dest_address))
    wallet_script = Script(wallet_script_pubkey(wallet))
    pubkey = privkey.get_public_key()
    input_sats = utxo["satoshis"]
    vin = [TransactionInput(_txid_bytes(utxo["txid"]), utxo["vout"])]

    change = max(0, input_sats - INSCRIPTION_OUTPUT_SATS)
    for _ in range(8):
        tx = Transaction(
            version=tx_version,
            vin=vin[:],
            vout=[
                TransactionOutput(INSCRIPTION_OUTPUT_SATS, dest_script),
                TransactionOutput(change, wallet_script),
            ],
        )
        fee = _tx_fee(tx, fee_per_kb)
        next_change = input_sats - INSCRIPTION_OUTPUT_SATS - fee
        if next_change == change:
            break
        change = next_change

    if change <= 0:
        raise RuntimeError("not enough funds for inscription output and fee")

    tx = Transaction(
        version=tx_version,
        vin=vin,
        vout=[
            TransactionOutput(INSCRIPTION_OUTPUT_SATS, dest_script),
            TransactionOutput(change, wallet_script),
        ],
    )
    fee = _tx_fee(tx, fee_per_kb)
    if input_sats < INSCRIPTION_OUTPUT_SATS + fee + change:
        raise RuntimeError("not enough funds after fee")

    msg = tx.sighash_legacy(0, wallet_script, SIGHASH.ALL)
    sig = privkey.sign(msg)
    tx.vin[0].script_sig = script_sig_p2pkh(sig, pubkey, SIGHASH.ALL)

    return tx
