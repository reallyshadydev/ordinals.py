"""Network parameters (ported from ordinals.js NETWORKS)."""

from embit.misc import const
from embit.networks import NETWORKS

NETWORKS_BY_COIN = {
    "dogecoin": {
        "mainnet": {
            "name": "dogecoin",
            "messagePrefix": "\x19Dogecoin Signed Message:\n",
            "bech32": None,
            "bip32": {"public": 0x02FACAFD, "private": 0x02FAC398},
            "pubKeyHash": 0x1E,
            "scriptHash": 0x16,
            "wif": 0x9E,
            "tx_version": 2,
            "default_fee_per_kb": 100_000_000,
            "token_protocol": "drc-20",
            "supported_address_types": ("legacy",),
        },
        "testnet": {
            "name": "dogecoin-testnet",
            "bech32": None,
            "bip32": {"public": 0x04358394, "private": 0x04358394},
            "pubKeyHash": 0x71,
            "scriptHash": 0xC4,
            "wif": 0xF1,
            "tx_version": 2,
            "default_fee_per_kb": 100_000_000,
            "token_protocol": "drc-20",
            "supported_address_types": ("legacy",),
        },
    },
    "litecoin": {
        "mainnet": {
            "name": "litecoin-mainnet",
            "bech32": "ltc",
            "bip32": {"public": 0x019DA462, "private": 0x019D9CFE},
            "pubKeyHash": 0x30,
            "scriptHash": 0x32,
            "wif": 0xB0,
            "tx_version": 2,
            "default_fee_per_kb": 100_000_000,
            "token_protocol": "ltc-20",
            "supported_address_types": ("legacy", "segwit", "taproot"),
        },
        "testnet": {
            "name": "litecoin-testnet",
            "bech32": "tltc",
            "bip32": {"public": 0x043587CF, "private": 0x04358394},
            "pubKeyHash": 0x6F,
            "scriptHash": 0x3A,
            "wif": 0xEF,
            "tx_version": 2,
            "default_fee_per_kb": 100_000_000,
            "token_protocol": "ltc-20",
            "supported_address_types": ("legacy", "segwit", "taproot"),
        },
    },
    "bitcoin": {
        "mainnet": {
            "name": "bitcoin",
            "bech32": "bc",
            "bip32": {"public": 0x0488B21E, "private": 0x0488ADE4},
            "pubKeyHash": 0x00,
            "scriptHash": 0x05,
            "wif": 0x80,
            "tx_version": 2,
            "default_fee_per_kb": 100_000_000,
            "token_protocol": "brc-20",
            "supported_address_types": ("legacy", "segwit", "taproot"),
        },
        "testnet": {
            "name": "bitcoin-testnet",
            "bech32": "tb",
            "bip32": {"public": 0x043587CF, "private": 0x04358394},
            "pubKeyHash": 0x6F,
            "scriptHash": 0xC4,
            "wif": 0xEF,
            "tx_version": 2,
            "default_fee_per_kb": 100_000_000,
            "token_protocol": "brc-20",
            "supported_address_types": ("legacy", "segwit", "taproot"),
        },
    },
    "wojakcoin": {
        "mainnet": {
            "name": "wojakcoin",
            "bech32": None,
            "bip32": {"public": 0x02FACAFD, "private": 0x02FAC398},
            "pubKeyHash": 0x49,
            "scriptHash": 0x1E,
            "wif": 0xC9,
            "tx_version": 1,
            "default_fee_per_kb": 1_000_000,
            "token_protocol": "wjk-20",
            "supported_address_types": ("legacy",),
        },
        "testnet": None,
    },
    "pepecoin": {
        "mainnet": {
            "name": "pepecoin",
            "bech32": "pep",
            "bip32": {"public": 0x02FACAFD, "private": 0x02FAC398},
            "pubKeyHash": 0x38,
            "scriptHash": 0x16,
            "wif": 0x9E,
            "tx_version": 2,
            "default_fee_per_kb": 20_000_000,
            "token_protocol": "prc-20",
            "supported_address_types": ("legacy",),
        },
        "testnet": {
            "name": "pepecoin-testnet",
            "bech32": None,
            "bip32": {"public": 0x043587CF, "private": 0x04358394},
            "pubKeyHash": 0x71,
            "scriptHash": 0xC4,
            "wif": 0xF1,
            "tx_version": 2,
            "default_fee_per_kb": 20_000_000,
            "token_protocol": "prc-20",
            "supported_address_types": ("legacy",),
        },
    },
}

COIN = 100_000_000
INSCRIPTION_OUTPUT_SATS = 100_000
MAX_SCRIPT_ELEMENT_SIZE = 520
MAX_CHUNK_LEN = 240
MAX_PAYLOAD_LEN = 1500


def _bip32_bytes(val: int) -> bytes:
    return val.to_bytes(4, "big")


def embit_network(net: dict) -> dict:
    """Map ordinals network dict to embit NETWORKS entry."""
    b32 = net["bip32"]
    return {
        "name": net["name"],
        "wif": bytes([net["wif"]]),
        "p2pkh": bytes([net["pubKeyHash"]]),
        "p2sh": bytes([net["scriptHash"]]),
        "bech32": net.get("bech32") or "bc",
        "xprv": _bip32_bytes(b32["private"]),
        "xpub": _bip32_bytes(b32["public"]),
        "yprv": _bip32_bytes(b32["private"]),
        "zprv": _bip32_bytes(b32["private"]),
        "Yprv": _bip32_bytes(b32["private"]),
        "Zprv": _bip32_bytes(b32["private"]),
        "ypub": _bip32_bytes(b32["public"]),
        "zpub": _bip32_bytes(b32["public"]),
        "Ypub": _bip32_bytes(b32["public"]),
        "Zpub": _bip32_bytes(b32["public"]),
        "bip32": const(0),
    }


def register_embit_network(net: dict) -> dict:
    entry = embit_network(net)
    NETWORKS[net["name"]] = entry
    return entry


def get_network(coin: str, testnet: bool) -> dict:
    coin = coin.lower()
    if coin not in NETWORKS_BY_COIN:
        raise ValueError(f"Unsupported coin: {coin}. Supported: {', '.join(NETWORKS_BY_COIN)}")
    nets = NETWORKS_BY_COIN[coin]
    net = nets["testnet" if testnet else "mainnet"]
    if not net:
        raise ValueError(f"No {'testnet' if testnet else 'mainnet'} for {coin}")
    register_embit_network(net)
    return net
