#!/usr/bin/env python3
"""Doctor do ambiente — verifica em 5s se a maquina esta pronta para monetizar.

Roda sem credencial nenhuma (itens com (voce) dependem de criar conta/.env):
  python ops/env_doctor.py
Exit code 0 = tudo verde. Itens amarelos nao bloqueiam o dia.
"""
from __future__ import annotations

import importlib
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

OK, WARN, FAIL = "✅", "🟡", "❌"
fails = warns = 0

def rep(status: str, item: str, hint: str = "") -> None:
    global fails, warns
    if status == FAIL:
        fails += 1
    elif status == WARN:
        warns += 1
    pad = f"  → {hint}" if hint else ""
    print(f"{status} {item}{pad}")

def check_env_file() -> None:
    env = ROOT / ".env"
    if not env.exists():
        rep(WARN, ".env na raiz", "copie .env.example -> .env e preencha WALLET_ADDRESS")
        return
    kv = dict(l.split("=", 1) for l in env.read_text().splitlines()
              if "=" in l and not l.startswith("#"))
    for k in ("WALLET_ADDRESS",):
        v = kv.get(k, "").strip()
        valido = v.startswith("0x") and len(v) == 42
        if valido:
            rep(OK, f".env: {k} preenchido ({v[:6]}...{v[-4:]})")
        elif v:
            rep(WARN, f".env: {k} ainda e placeholder/invalido",
                "cole seu endereco publico real (0x + 40 hex, mesmo da MetaMask/Rabby)")
        else:
            rep(WARN, f".env: {k} vazio", "sem ele o wallet_watch nao sabe onde olhar")
    for k in ("DISCORD_BOT_TOKEN", "TELEGRAM_BOT_TOKEN"):
        rep(OK if kv.get(k, "").strip() else WARN,
            f".env: {k}", "so precisa quando FECHAR o 1o trial" if not kv.get(k, "").strip() else "")

def main() -> None:
    print(f"== DOCTOR {platform.system()} · python {platform.python_version()} ==\n")

    rep(OK if sys.version_info >= (3, 10) else FAIL, "Python >= 3.10",
        "winget install Python.Python.3.12 (Windows) ou python.org/downloads")
    rep(OK if shutil.which("git") else WARN, "git no PATH",
        "winget install Git.Git — ajuda a clonar repos do stack")

    for pasta in ("mod247", "x402-leads-api", "site-forge", "bounty-hunter", "agent-lab"):
        rep(OK if (ROOT / pasta).is_dir() else WARN, f"pasta {pasta}/")

    # bateria rapida do moderador (prova de fogo do produto MOD 24/7)
    sys.path.insert(0, str(ROOT / "mod247"))
    try:
        mod = importlib.import_module("mod247")
        log = mod.run_scenario()
        bans = sum(1 for r in log if r["action"] == "ban+delete")
        rep(OK if bans == 5 else FAIL, f"mod247 bateria viva ({bans} bans na simulacao)")
    except Exception as e:
        rep(FAIL, "mod247 importavel", str(e))

    check_env_file()

    tracker = ROOT / "ops" / "tracker.csv"
    if tracker.exists():
        n = max(0, len(tracker.read_text().splitlines()) - 1)
        rep(OK if n else WARN, f"tracker.csv ({n} prospectos)",
            "Hora 2 do PRIMEIRAS-HORAS.md: 15 disparos -> 15 linhas" if not n else "")
    else:
        rep(WARN, "ops/tracker.csv", "criado com cabecalho — verifique a pasta ops/")

    hist = ROOT / "ops" / "recebidos.log"
    if hist.exists() and hist.read_text().strip():
        rep(OK, "💰 JA ENTROU CRIPTO (ver ops/recebidos.log)")
    else:
        rep(WARN, "primeira cripto ainda nao caiu",
            "ligue o vigia: python ops/wallet_watch.py --loop --address 0xSUA...")

    print(f"\n== resultado: {fails} erro(s), {warns} aviso(s) ==")
    sys.exit(1 if fails else 0)

if __name__ == "__main__":
    main()
