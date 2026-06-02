"""JSON-RPC client (same env vars as ordinals.js)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


class RpcError(RuntimeError):
    pass


class NodeRpc:
    def __init__(self, url: str, user: str, password: str, timeout: int = 120):
        self.url = url.rstrip("/") + "/"
        self.user = user
        self.password = password
        self.timeout = timeout

    @classmethod
    def from_env(cls) -> "NodeRpc":
        url = os.environ.get("NODE_RPC_URL", "http://127.0.0.1:22555")
        user = os.environ.get("NODE_RPC_USER", "")
        password = os.environ.get("NODE_RPC_PASS", "")
        if not user or not password:
            raise RpcError("NODE_RPC_USER and NODE_RPC_PASS must be set in .env")
        return cls(url, user, password)

    def call(self, method: str, params: list | None = None) -> Any:
        params = params if params is not None else []
        body = json.dumps({"jsonrpc": "1.0", "id": "ordinals-py", "method": method, "params": params}).encode()
        import base64

        auth = base64.b64encode(f"{self.user}:{self.password}".encode()).decode()
        req = urllib.request.Request(
            self.url,
            data=body,
            headers={"Content-Type": "text/plain;", "Authorization": f"Basic {auth}"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            raise RpcError(f"HTTP {e.code}: {e.read().decode(errors='replace')[:400]}") from e
        except urllib.error.URLError as e:
            raise RpcError(f"RPC connection failed: {e}") from e
        if data.get("error"):
            err = data["error"]
            raise RpcError(err.get("message", str(err)))
        return data.get("result")

    def send_raw_transaction(self, hex_tx: str, retry: bool = False) -> None:
        import time

        while True:
            try:
                self.call("sendrawtransaction", [hex_tx])
                return
            except RpcError as e:
                if retry and "too-long-mempool-chain" in str(e).lower():
                    time.sleep(1)
                    continue
                raise

    def import_privkey_no_rescan(self, wif: str) -> None:
        self.call("importprivkey", [wif, "", False])
