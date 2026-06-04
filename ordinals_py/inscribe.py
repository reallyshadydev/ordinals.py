"""Ordinals inscription (commit/reveal chain) — Python port of ordinals.js inscribe()."""

from __future__ import annotations

from collections import deque
from io import BytesIO

from embit import ec
from embit.script import Script, script_sig_p2pkh
from embit.transaction import SIGHASH, Transaction, TransactionInput, TransactionOutput

from .networks import INSCRIPTION_OUTPUT_SATS, MAX_PAYLOAD_LEN, MAX_SCRIPT_ELEMENT_SIZE
from .script_builder import (
    build_lock_script_with_drops,
    build_unlock_script,
    p2sh_script_from_redeem,
    push_data,
    push_number,
    push_text,
)
from .wallet import update_wallet_from_tx, wallet_script_pubkey


def _display_txid(tx: Transaction) -> str:
    return tx.txid().hex()


def _txid_bytes(display_txid: str) -> bytes:
    """Display-order txid bytes (embit reverses on serialize for wire format)."""
    return bytes.fromhex(display_txid)


def _inscription_chunks(content_type: str, data: bytes) -> deque[bytes]:
    parts: list[bytes] = []
    while data:
        part = data[: min(240, len(data))]
        data = data[len(part) :]
        parts.append(part)

    chunks: list[bytes] = [push_text("ord"), push_number(len(parts)), push_text(content_type)]
    for n, part in enumerate(parts):
        chunks.append(push_number(len(parts) - n - 1))
        chunks.append(push_data(part))
    return deque(chunks)


def _tx_fee(tx: Transaction, fee_per_kb: int) -> int:
    return max(1, len(tx.serialize()) * fee_per_kb // 1000)


def _is_change_output(output: TransactionOutput, wallet_script_bytes: bytes) -> bool:
    """Wallet outputs above inscription dust are change, not the inscription carrier."""
    return (
        output.script_pubkey.data == wallet_script_bytes
        and output.value > INSCRIPTION_OUTPUT_SATS
    )


def _strip_change_outputs(tx: Transaction, wallet_script_bytes: bytes) -> None:
    tx.vout = [o for o in tx.vout if not _is_change_output(o, wallet_script_bytes)]


def _sign_wallet_inputs(tx: Transaction, privkey: ec.PrivateKey, pubkey: ec.PublicKey, wallet: dict) -> None:
    wallet_script = Script(wallet_script_pubkey(wallet))
    for i, inp in enumerate(tx.vin):
        for u in wallet["utxos"]:
            if bytes.fromhex(u["txid"]) != inp.txid or u["vout"] != inp.vout:
                continue
            msg = tx.sighash_legacy(i, wallet_script, SIGHASH.ALL)
            sig = privkey.sign(msg)
            inp.script_sig = script_sig_p2pkh(sig, pubkey, SIGHASH.ALL)
            break


def _payment_output_sum(tx: Transaction, wallet_script_bytes: bytes) -> int:
    """Sum outputs excluding change; keep inscription dust (100k sats) even on same address."""
    return sum(
        o.value for o in tx.vout if not _is_change_output(o, wallet_script_bytes)
    )


def _input_sum(tx: Transaction, wallet: dict) -> int:
    """Total input value: wallet UTXOs plus inscription P2SH carries (100k sats each)."""
    total = 0
    for inp in tx.vin:
        found = False
        for u in wallet["utxos"]:
            if bytes.fromhex(u["txid"]) == inp.txid and u["vout"] == inp.vout:
                total += u["satoshis"]
                found = True
                break
        if not found:
            total += INSCRIPTION_OUTPUT_SATS
    return total


def fund_transaction(
    wallet: dict,
    tx: Transaction,
    privkey: ec.PrivateKey,
    fee_per_kb: int,
) -> None:
    """Fund and sign wallet P2PKH inputs (ordinals.js fund())."""
    wallet_script_bytes = wallet_script_pubkey(wallet)
    wallet_script = Script(wallet_script_bytes)
    pubkey = privkey.get_public_key()

    while True:
        input_amount = _input_sum(tx, wallet)
        payment_out = _payment_output_sum(tx, wallet_script_bytes)
        fee = _tx_fee(tx, fee_per_kb)

        if tx.vin and tx.vout and input_amount >= payment_out + fee:
            break

        added = False
        for u in wallet["utxos"]:
            if any(bytes.fromhex(u["txid"]) == inp.txid and u["vout"] == inp.vout for inp in tx.vin):
                continue
            tx.vin.append(TransactionInput(_txid_bytes(u["txid"]), u["vout"]))
            added = True
            break

        if not added:
            raise RuntimeError("not enough funds")

        _strip_change_outputs(tx, wallet_script_bytes)
        input_amount = _input_sum(tx, wallet)
        payment_out = _payment_output_sum(tx, wallet_script_bytes)
        fee = _tx_fee(tx, fee_per_kb)
        change = input_amount - payment_out - fee
        if change > 0:
            tx.vout.append(TransactionOutput(change, wallet_script))

        _sign_wallet_inputs(tx, privkey, pubkey, wallet)

    if input_amount < payment_out + fee:
        raise RuntimeError("not enough funds")


def _sign_p2sh_input(
    tx: Transaction,
    privkey: ec.PrivateKey,
    partial: bytes,
    lock_script: bytes,
) -> None:
    redeem = Script(lock_script)
    msg = tx.sighash_legacy(0, redeem, SIGHASH.ALL)
    buf = BytesIO()
    privkey.sign(msg).write_to(buf)
    sig = buf.getvalue() + bytes([SIGHASH.ALL])
    tx.vin[0].script_sig = Script(build_unlock_script(partial, sig, lock_script))


def inscribe(
    wallet: dict,
    receiver_script: bytes,
    content_type: str,
    data: bytes,
    *,
    privkey: ec.PrivateKey,
    fee_per_kb: int,
    tx_version: int,
) -> list[Transaction]:
    if not data:
        raise ValueError("no data to mint")
    if len(content_type) > MAX_SCRIPT_ELEMENT_SIZE:
        raise ValueError("content type too long")

    pubkey = privkey.get_public_key()
    pubkey_sec = pubkey.sec()
    inscription = _inscription_chunks(content_type, data)

    txs: list[Transaction] = []
    p2sh_prev: TransactionInput | None = None
    last_lock: bytes | None = None
    last_partial: bytes | None = None

    while inscription:
        partial_chunks: list[bytes] = []

        if not txs:
            partial_chunks.append(inscription.popleft())

        partial = b"".join(partial_chunks)
        while len(partial) <= MAX_PAYLOAD_LEN and inscription:
            partial_chunks.append(inscription.popleft())
            if inscription:
                partial_chunks.append(inscription.popleft())
            partial = b"".join(partial_chunks)

        if len(partial) > MAX_PAYLOAD_LEN:
            inscription.appendleft(partial_chunks.pop())
            inscription.appendleft(partial_chunks.pop())
            partial = b"".join(partial_chunks)

        lock_script = build_lock_script_with_drops(pubkey_sec, len(partial_chunks))
        p2sh_spk = p2sh_script_from_redeem(lock_script)

        tx = Transaction(version=tx_version, vin=[], vout=[])
        if p2sh_prev:
            tx.vin.append(p2sh_prev)

        tx.vout.append(TransactionOutput(INSCRIPTION_OUTPUT_SATS, Script(p2sh_spk)))
        fund_transaction(wallet, tx, privkey, fee_per_kb)

        if p2sh_prev and last_lock and last_partial:
            _sign_p2sh_input(tx, privkey, last_partial, last_lock)

        update_wallet_from_tx(wallet, tx, _display_txid(tx))
        txs.append(tx)

        p2sh_prev = TransactionInput(_txid_bytes(_display_txid(tx)), 0)
        last_lock = lock_script
        last_partial = partial

    tx = Transaction(version=tx_version, vin=[], vout=[])
    assert p2sh_prev is not None
    tx.vin.append(p2sh_prev)
    tx.vout.append(TransactionOutput(INSCRIPTION_OUTPUT_SATS, Script(receiver_script)))
    fund_transaction(wallet, tx, privkey, fee_per_kb)

    if last_lock and last_partial:
        _sign_p2sh_input(tx, privkey, last_partial, last_lock)

    update_wallet_from_tx(wallet, tx, _display_txid(tx))
    txs.append(tx)

    return txs
