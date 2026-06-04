# ordinals-py

Pure Python ordinals inscriber for **Pepecoin**, Dogecoin, Wojakcoin, and other chains — no Node.js required.

Compatible with `.env` and `.wallet.json` from [multi-ordinals-script](https://github.com/booktoshi/doginals) / `ordinals.js`.

## Install

**Requires embit 0.8+** (system `pip install embit` often gives 0.7 and breaks with `No module named 'embit.misc'`).

```bash
cd ordinals-py
python3 -m venv .venv
source .venv/bin/activate   # optional
.venv/bin/pip install -U pip
.venv/bin/pip install embit==0.8.0
```

Then run via the venv (any of these):

```bash
./run.sh wallet new
./ordinals.py wallet new          # auto-switches to .venv
.venv/bin/python -m ordinals_py wallet new
```

## Configuration

Copy `.env.example` to `.env` (or reuse one from `multi-ordinals-script`):

```env
COIN=pepecoin
TESTNET=false
NODE_RPC_URL=http://127.0.0.1:33873
NODE_RPC_USER=your_rpc_user
NODE_RPC_PASS=your_rpc_password
FEE_PER_KB=20000000
WALLET=.wallet.json
```

Pepecoin relay minimum is about **1,000,000 ribbits/kB** (1 PEPE/kB). Inscription chains need more headroom; use **20,000,000+** (`~20,000 ribbits/byte`) if txs sit in mempool with `currentpriority: 0`. The test mint at `2,000,000` paid only ~0.0018 PEPE fee per tx and stayed unconfirmed for many blocks.

## Commands

```bash
# After install
ordinals-py info

# Or without installing
python3 -m ordinals_py info
python3 ordinals.py mint PAddress... ./image.png

# Wallet
python3 -m ordinals_py wallet new
python3 -m ordinals_py wallet sync
python3 -m ordinals_py wallet balance

# Inscribe
python3 -m ordinals_py mint PYourAddress... ./image.png

# Send inscription (0.001 coin on recipient output; change returns to wallet)
python3 -m ordinals_py send WRecipient... [txid:vout]

# PRC-20 / DRC-20
python3 -m ordinals_py token mint PAddress... tick amount 1
```

Run from this directory so `pending-txs.json` and `.wallet.json` resolve correctly.

### Avoiding stuck mempool packages

`mint` syncs UTXOs from the node by default. If you have an old unconfirmed inscription change output, sync will add it and coin-selection may spend it first, chaining new txs behind a low-fee package.

Use a **confirmed** funding UTXO only, then:

```bash
ORDINALS_SKIP_SYNC=1 FEE_PER_KB=50000000 WALLET=.wallet.json \
  python3 -m ordinals_py mint PReceiver... ./file.png
```

Successful Pepecoin test: inscription `d4a29c663a9fae93e201ce47a7e06cac1c2f0e3e69a606dac97b195deacc4b33i0` at `FEE_PER_KB=50000000`.

## vs `ordinals.js`

| Feature | `ordinals.js` | `ordinals_py` |
|---------|---------------|---------------|
| Mint / inscribe | yes | yes |
| Wallet new/sync/balance | yes | yes |
| Token deploy/mint/transfer | yes | yes |
| HTTP server | yes | no |
| Taproot / segwit | yes | legacy P2PKH only |

Pending broadcasts are saved to `pending-txs.json`; re-run the same command to retry.

## Batch minting from multi-ordinals-script

Point `auto9.py` at this repo (default: sibling folder `../ordinals-py`):

```bash
export ORDINALS_PY_DIR=/root/ordinals-py
cd /root/multi-ordinals-script
python3 auto9.py
```
