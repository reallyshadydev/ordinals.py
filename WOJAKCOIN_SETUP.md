# Wojakcoin setup (ordinals-py)

Python inscriber for **wojakinals** and **WJK-20** on Wojakcoin — no Node.js. Based on [reallyshadydev/ordinals.py](https://github.com/reallyshadydev/ordinals.py).

## Prerequisites

- Synced `wojakcoind` with `txindex=1`, `server=1`, RPC enabled
- Default ports: P2P **20759**, RPC **20760** ([wojakcore](https://github.com/WojakCoinProj/wojakcore))

## Install

```bash
cd /root/ordinals-py
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install embit==0.8.0
# or: pip install -r requirements.txt  (needs pip 22+ for embit 0.8)
```

## Configuration

`.env` is already configured for this server (RPC `127.0.0.1:20760`). Edit if your RPC user/password differ.

| Variable | Wojakcoin value |
|----------|-----------------|
| `COIN` | `wojakcoin` |
| `NODE_RPC_URL` | `http://127.0.0.1:20760` |
| `TOKEN_PROTOCOL` | `wjk-20` (indexed by **ordwoj**) |
| `FEE_PER_KB` | Raise if txs sit unconfirmed in mempool |

Addresses use prefix **W** (`pubKeyHash` `0x49`, WIF `0xC9`), same as ordwoj / rust-wojakcoin.

## Quick start

```bash
cd /root/ordinals-py

# Verify RPC + network params
python3 -m ordinals_py info

# New wallet (imports key into wojakcoind with rescan=false)
python3 -m ordinals_py wallet new

# Fund the printed W... address from another wallet, then:
python3 -m ordinals_py wallet sync
python3 -m ordinals_py wallet balance

# Inscribe an image (wojakinal)
python3 -m ordinals_py mint WYourAddress... ./image.png

# WJK-20 deploy
python3 -m ordinals_py wjk-20 deploy WYourAddress... TICK 21000000 1000

# WJK-20 mint (optional repeat count as 4th arg)
python3 -m ordinals_py wjk-20 mint WYourAddress... TICK 1000

# WJK-20 transfer
python3 -m ordinals_py wjk-20 transfer WRecipient... TICK 500
```

## Stuck mempool packages

If an old low-fee inscription change is blocking new mints:

```bash
ORDINALS_SKIP_SYNC=1 FEE_PER_KB=5000000 python3 -m ordinals_py mint WAddress... ./file.png
```

## Explorer / balances

After inscribing, index and view on **ordwoj**:

- `ordwoj server` → `http://127.0.0.1:3080`
- WJK-20 APIs: `/api/tokens`, `/api/balances/<Waddress>`

## Related

- `/root/ord-wojakcoin` — ordwoj indexer + explorer
- `/root/.wojakcoin/wojakcoin.conf` — node RPC
