"""Bitcoin script helpers matching ordinals.js bufferToChunk / inscription envelope."""

from __future__ import annotations

from embit import hashes

OP_DROP = 0x75
OP_TRUE = 0x51
OP_CHECKSIGVERIFY = 0xAD
OP_HASH160 = 0xA9
OP_EQUAL = 0x87

MAX_CHUNK_LEN = 240
MAX_PAYLOAD_LEN = 1500
MAX_SCRIPT_ELEMENT_SIZE = 520


def push_data(data: bytes) -> bytes:
    if len(data) == 0:
        return bytes([0])
    if len(data) <= 75:
        return bytes([len(data)]) + data
    if len(data) <= 255:
        return bytes([76, len(data)]) + data
    return bytes([77]) + len(data).to_bytes(2, "little") + data


def push_number(n: int) -> bytes:
    if n == 0:
        return bytes([0])
    if 1 <= n <= 16:
        return bytes([0x50 + n])
    if n < 128:
        return bytes([1, n])
    return bytes([2, n % 256, n // 256])


def push_text(s: str) -> bytes:
    return push_data(s.encode("utf-8") if isinstance(s, str) else s)


def hash160(data: bytes) -> bytes:
    return hashes.hash160(data)


def address_to_script_pubkey(address: str) -> bytes:
    from embit.script import Script

    return Script.from_address(address).data


def build_inscription_script(content_type: str, data: bytes) -> bytes:
    if len(content_type) > MAX_SCRIPT_ELEMENT_SIZE:
        raise ValueError("content type too long")
    parts: list[bytes] = []
    while data:
        part = data[: min(MAX_CHUNK_LEN, len(data))]
        data = data[len(part) :]
        parts.append(part)

    script = push_text("ord")
    script += push_number(len(parts))
    script += push_text(content_type)
    for n, part in enumerate(parts):
        script += push_number(len(parts) - n - 1)
        script += push_data(part)
    return script


def build_lock_script_with_drops(pubkey_sec: bytes, num_drops: int) -> bytes:
    lock = push_data(pubkey_sec) + bytes([OP_CHECKSIGVERIFY])
    lock += bytes([OP_DROP]) * num_drops
    lock += bytes([OP_TRUE])
    return lock


def p2sh_script_from_redeem(redeem: bytes) -> bytes:
    h = hash160(redeem)
    return bytes([OP_HASH160, 20]) + h + bytes([OP_EQUAL])


def build_unlock_script(partial: bytes, signature: bytes, redeem: bytes) -> bytes:
    sig_bytes = push_data(signature)
    redeem_bytes = push_data(redeem)
    return partial + sig_bytes + redeem_bytes
