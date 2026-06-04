#!/usr/bin/env python3
"""CLI — Python replacement for `node ordinals.js` (mint, wallet, token, info)."""

from __future__ import annotations

import json
import mimetypes
import os
import re
import sys
from pathlib import Path

from embit import ec
from embit.networks import NETWORKS
from embit.script import Script, p2pkh

from .inscribe import inscribe
from .send import send_utxo
from .networks import get_network
from .rpc import NodeRpc, RpcError
from .script_builder import address_to_script_pubkey
from .wallet import (
    load_wallet,
    new_wallet,
    save_wallet,
    sync_wallet,
    update_wallet_from_tx,
    wallet_balance,
    wallet_path,
)


def load_dotenv(path: str = ".env") -> None:
  p = Path(path)
  if not p.is_file():
    return
  for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
      continue
    k, _, v = line.partition("=")
    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def config() -> tuple[dict, int, str, NodeRpc]:
  load_dotenv()
  coin = os.environ.get("COIN", "pepecoin").lower()
  testnet = os.environ.get("TESTNET", "false").lower() == "true"
  net = get_network(coin, testnet)
  fee_env = os.environ.get("FEE_PER_KB")
  fee_per_kb = int(fee_env) if fee_env and fee_env.isdigit() else net["default_fee_per_kb"]
  rpc = NodeRpc.from_env()
  return net, fee_per_kb, coin, rpc


def cmd_info() -> int:
  net, fee_per_kb, coin, rpc = config()
  print("=== Network Configuration (ordinals-py) ===")
  print(f"Coin: {coin}")
  print(f"Network: {net['name']}")
  print(f"Fee per KB: {fee_per_kb}")
  print(f"TX version: {net['tx_version']}")
  print(f"Token protocol: {net['token_protocol']}")
  print(f"RPC URL: {rpc.url}")
  try:
    blocks = rpc.call("getblockcount")
    print(f"Block height: {blocks}")
  except RpcError as e:
    print(f"RPC: {e}")
  return 0


def cmd_wallet_new() -> int:
  net, _, coin, rpc = config()
  if wallet_path().exists():
    print("wallet already exists", file=sys.stderr)
    return 1
  embit_net = NETWORKS[net["name"]]
  priv = ec.PrivateKey(os.urandom(32), network=embit_net)
  script = p2pkh(priv.get_public_key())
  address = script.address(embit_net)
  script_hex = address_to_script_pubkey(address).hex()
  wallet = new_wallet(
    priv.wif(embit_net),
    address,
    script_hex,
    coin=coin,
    testnet=os.environ.get("TESTNET", "false").lower() == "true",
    address_type=os.environ.get("ADDRESS_TYPE", "legacy"),
  )
  save_wallet(wallet)
  print("=== New Wallet Created ===")
  print(f"Network: {net['name']}")
  print(f"Address: {address}")
  skip = os.environ.get("WALLET_RPC_IMPORT", "").lower() in ("0", "false")
  if not skip:
    try:
      rpc.import_privkey_no_rescan(wallet["privkey"])
      print("importprivkey done (rescan=false). Run: python -m ordinals_py wallet sync")
    except RpcError as e:
      print(f"importprivkey skipped: {e}", file=sys.stderr)
  return 0


def cmd_wallet_sync() -> int:
  _, _, _, rpc = config()
  wallet = load_wallet()
  sync_wallet(wallet, rpc)
  bal = wallet_balance(wallet)
  print(f"Balance: {bal} satoshis ({len(wallet['utxos'])} UTXOs)")
  return 0


def cmd_wallet_balance() -> int:
  wallet = load_wallet()
  print(wallet["address"], wallet_balance(wallet))
  return 0


def cmd_mint(address: str, content_type_or_file: str, hex_data: str | None = None) -> int:
  net, fee_per_kb, _, rpc = config()
  path = Path(content_type_or_file)
  if path.is_file():
    content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    data = path.read_bytes()
  else:
    content_type = content_type_or_file
    if not hex_data or not re.fullmatch(r"[0-9a-fA-F]*", hex_data):
      print("data must be hex when not passing a file", file=sys.stderr)
      return 1
    data = bytes.fromhex(hex_data)

  wallet = load_wallet()
  if not os.environ.get("ORDINALS_SKIP_SYNC"):
    sync_wallet(wallet, rpc)
  if wallet_balance(wallet) == 0:
    print("no funds — run wallet sync after funding", file=sys.stderr)
    return 1

  priv = ec.PrivateKey.from_wif(wallet["privkey"])
  receiver_script = address_to_script_pubkey(address)

  source = "env" if os.environ.get("FEE_PER_KB", "").isdigit() else "default"
  print(
    f"[ordinals-py] fee source={source} per-kb={fee_per_kb} (~{fee_per_kb / 1000:.0f} ribbits/byte)",
    file=sys.stderr,
  )

  txs = inscribe(
    wallet,
    receiver_script,
    content_type,
    data,
    privkey=priv,
    fee_per_kb=fee_per_kb,
    tx_version=net["tx_version"],
  )

  if len(txs) > 1:
    inscription_txid = _display_txid(txs[1])
    print(f"inscription txid: {inscription_txid}")

  pending = Path("pending-txs.json")
  for i, tx in enumerate(txs):
    print(f"broadcasting tx {i + 1} of {len(txs)}")
    hex_tx = tx.serialize().hex()
    try:
      rpc.send_raw_transaction(hex_tx, retry=True)
    except RpcError as e:
      print(f"broadcast failed: {e}", file=sys.stderr)
      if "insufficient priority" in str(e).lower():
        print("Raise FEE_PER_KB in .env (Pepecoin: try 2000000+)", file=sys.stderr)
      sync_wallet(wallet, rpc)
      save_wallet(wallet)
      pending.write_text(json.dumps([t.serialize().hex() for t in txs[i:]]))
      print("saved pending-txs.json — re-run to retry broadcast", file=sys.stderr)
      return 1
    sync_wallet(wallet, rpc)
    save_wallet(wallet)

  if pending.exists():
    pending.unlink()
  return 0


def _display_txid(tx) -> str:
  return tx.txid().hex()


def cmd_token(sub: str, argv: list[str]) -> int:
  net, _, _, _ = config()
  proto = os.environ.get("TOKEN_PROTOCOL", net["token_protocol"])
  if sub == "deploy":
    if len(argv) < 4:
      print("usage: token deploy <address> <tick> <max> <lim>", file=sys.stderr)
      return 1
    address, tick, max_supply, lim = argv[0], argv[1], argv[2], argv[3]
    body = json.dumps(
      {"p": proto, "op": "deploy", "tick": tick.lower(), "max": max_supply, "lim": lim},
      separators=(",", ":"),
    )
  elif sub in ("mint", "transfer"):
    if len(argv) < 3:
      print(f"usage: token {sub} <address> <tick> <amt> [repeat]", file=sys.stderr)
      return 1
    address, tick, amt = argv[0], argv[1], argv[2]
    repeat = int(argv[3]) if len(argv) > 3 else 1
    op = sub
    for i in range(repeat):
      print(f"{op} {proto} {i + 1}/{repeat}")
      body = json.dumps(
        {"p": proto, "op": op, "tick": tick.lower(), "amt": amt},
        separators=(",", ":"),
      )
      rc = cmd_mint(address, "text/plain;charset=utf-8", body.encode().hex())
      if rc != 0:
        return rc
    return 0
  else:
    print(f"unknown token subcommand: {sub}", file=sys.stderr)
    return 1
  return cmd_mint(address, "text/plain;charset=utf-8", body.encode().hex())


def cmd_send(dest: str, utxo_ref: str | None = None) -> int:
    net, fee_per_kb, _, rpc = config()
    wallet = load_wallet()
    if not os.environ.get("ORDINALS_SKIP_SYNC"):
        sync_wallet(wallet, rpc)

    txid, vout = None, None
    if utxo_ref:
        if ":" not in utxo_ref:
            print("usage: send <address> [txid:vout]", file=sys.stderr)
            return 1
        txid, vout_s = utxo_ref.split(":", 1)
        vout = int(vout_s)

    priv = ec.PrivateKey.from_wif(wallet["privkey"])
    print(
        f"[ordinals-py] send fee per-kb={fee_per_kb} (~{fee_per_kb / 1000:.0f} ribbits/byte)",
        file=sys.stderr,
    )
    tx = send_utxo(
        wallet,
        dest,
        privkey=priv,
        fee_per_kb=fee_per_kb,
        tx_version=net["tx_version"],
        txid=txid,
        vout=vout,
    )
    txid_hex = _display_txid(tx)
    print(f"txid: {txid_hex}")
    hex_tx = tx.serialize().hex()
    try:
        rpc.send_raw_transaction(hex_tx, retry=True)
    except RpcError as e:
        print(f"broadcast failed: {e}", file=sys.stderr)
        Path("pending-txs.json").write_text(json.dumps([hex_tx]))
        return 1

    update_wallet_from_tx(wallet, tx, txid_hex)
    save_wallet(wallet)
    return 0


def cmd_rebroadcast_pending() -> int:
  pending = Path("pending-txs.json")
  if not pending.is_file():
    print("no pending-txs.json", file=sys.stderr)
    return 1
  _, _, _, rpc = config()
  hexes = json.loads(pending.read_text())
  for i, hx in enumerate(hexes):
    print(f"rebroadcast {i + 1}/{len(hexes)}")
    rpc.send_raw_transaction(hx, retry=False)
  pending.unlink()
  return 0


def main(argv: list[str] | None = None) -> int:
  argv = argv if argv is not None else sys.argv[1:]
  if not argv:
    print("usage: python -m ordinals_py <mint|send|wallet|token|info> ...", file=sys.stderr)
    return 1

  if Path("pending-txs.json").is_file() and argv[0] not in ("wallet", "info"):
    return cmd_rebroadcast_pending()

  cmd = argv[0]
  if cmd == "info":
    return cmd_info()
  if cmd == "mint":
    if len(argv) < 3:
      print("usage: mint <address> <file>|<content-type> [hex]", file=sys.stderr)
      return 1
    return cmd_mint(argv[1], argv[2], argv[3] if len(argv) > 3 else None)
  if cmd == "send":
    if len(argv) < 2:
      print("usage: send <address> [txid:vout]", file=sys.stderr)
      return 1
    return cmd_send(argv[1], argv[2] if len(argv) > 2 else None)
  if cmd == "wallet":
    sub = argv[1] if len(argv) > 1 else ""
    if sub == "new":
      return cmd_wallet_new()
    if sub == "sync":
      return cmd_wallet_sync()
    if sub == "balance":
      return cmd_wallet_balance()
    print(f"unknown wallet subcommand: {sub}", file=sys.stderr)
    return 1
  if cmd in ("drc-20", "token", "prc-20", "wjk-20", "wrc-20"):
    sub = argv[1] if len(argv) > 1 else ""
    return cmd_token(sub, argv[2:])
  print(f"unknown command: {cmd}", file=sys.stderr)
  return 1
