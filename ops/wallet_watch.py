#!/usr/bin/env python3
"""Vigia de carteira on-chain — dispara quando a PRIMEIRA CRIPTO chegar.

Zero credencial: so usa o endereco PUBLICO + RPC publico da Base (grpc web).
Nenhuma seed, nenhuma chave privada, nenhuma API key. Read-only = risco zero.

Uso:
  python wallet_watch.py --once --address 0xSUA...     # confere uma vez
  python wallet_watch.py --loop  --address 0xSUA...    # vigia a cada 5 min
  python wallet_watch.py --demo                        # simulacao (offline)

Monitora: ETH nativo + USDC (0x833589...913) na Base. Quer USDT/polygon?
Basta trocar RPC e contrato — o endereco EVM e o mesmo em todas as redes.
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parent
STATE = OUT / "wallet_state.json"
LOG = OUT / "recebidos.log"

RPC = "https://mainnet.base.org"                 # RPC publico oficial da Base
USDC_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"  # USDC nativo na Base
USDT_BASE = "0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2"  # USDT na Base

def rpc_call(method: str, params: list, timeout: int = 12) -> str:
    body = json.dumps({"jsonrpc": "2.0", "method": method, "params": params, "id": 1}).encode()
    req = urllib.request.Request(RPC, data=body,
                                 headers={"Content-Type": "application/json",
                                          "User-Agent": "Mozilla/5.0 (mod247-wallet-watch)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        out = json.loads(r.read().decode())
    if "error" in out:
        raise RuntimeError(out["error"])
    return out["result"]

def balance_of(token: str, address: str, decimals: int) -> float:
    data = "0x70a08231" + address.lower().removeprefix("0x").rjust(64, "0")
    raw = rpc_call("eth_call", [{"to": token, "data": data}, "latest"])
    return int(raw, 16) / 10**decimals

def balances_live(address: str) -> dict:
    eth = int(rpc_call("eth_getBalance", [address, "latest"]), 16) / 10**18
    return {
        "ETH": round(eth, 6),
        "USDC": round(balance_of(USDC_BASE, address, 6), 2),
        "USDT": round(balance_of(USDT_BASE, address, 6), 2),
    }

def balances_demo() -> dict:
    # simula a primeira chegada: voce ve exatamente o que o alerta vai mostrar
    p = STATE.with_name(".demo_step")
    step = int(p.read_text()) if p.exists() else 0
    p.write_text(str(step + 1))
    return {"ETH": 0.0, "USDC": 0.0, "USDT": 0.0} if step < 2 else {"ETH": 0.0, "USDC": 50.0, "USDT": 0.0}

def load_state() -> dict:
    return json.loads(STATE.read_text()) if STATE.exists() else {}

def save_state(s: dict) -> None:
    STATE.write_text(json.dumps(s, indent=2))

def check_once(address: str, demo: bool) -> dict:
    got = balances_demo() if demo else balances_live(address)
    prev = load_state().get(address, {})
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    chegadas = {k: v for k, v in got.items()
                if v > 0 and float(prev.get(k, 0) or 0) < v}
    if chegadas:
        linhas = [f"[{ts}] 🎉 ENTROU: +{got[k] - float(prev.get(k, 0) or 0):.6g} {k} "
                  f"(saldo: {v} {k})" for k, v in chegadas.items()]
        msg = "\n".join(linhas)
        print("=" * 56)
        print("💰💰💰  CRIPTO NA CARTEIRA!  💰💰💰")
        print(msg)
        print("=" * 56)
        with LOG.open("a", encoding="utf-8") as f:
            f.write(msg + "\n")
    else:
        print(f"[{ts}] saldos: ETH {got['ETH']} · USDC {got['USDC']} · USDT {got['USDT']}"
              " (nada novo ainda — o vigia segue olhando)")
    state = load_state()
    state[address] = got
    save_state(state)
    return got

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--address", help="seu endereco publico 0x...")
    ap.add_argument("--once", action="store_true", help="confere uma vez e sai")
    ap.add_argument("--loop", action="store_true", help="loop infinito (padrao 300s)")
    ap.add_argument("--interval", type=int, default=300)
    ap.add_argument("--demo", action="store_true", help="modo simulacao offline")
    a = ap.parse_args()
    address = (a.address or "0xDEMO").lower()
    if not a.demo and not a.address:
        ap.error("passe --address 0x... (ou --demo para simular)")
    if a.loop:
        print(f"vigia ligado em {address} a cada {a.interval}s — Ctrl+C para parar")
        while True:
            try:
                check_once(address, a.demo)
            except Exception as e:      # rede oscilou? espera e tenta de novo
                print(f"  (falha de rede: {e}; re-tentando em {a.interval}s)")
            time.sleep(a.interval)
    else:
        check_once(address, a.demo)

if __name__ == "__main__":
    main()
