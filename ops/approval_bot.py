#!/usr/bin/env python3
"""Porteiro de aprovacao — decisoes destrutivas chegam no seu Telegram com ✅/❌.

Fluxo (padrao humano-no-loop):
  mod247/adapter detecta  ->  --enqueue grava em fila_aprovacao.jsonl
  --serve (loop 24/7)     ->  manda mensagem com botoes no SEU Telegram
  voce toca ✅/❌          ->  callback grava em decisoes.jsonl (adapter executa)

Uso:
  python approval_bot.py --demo                                   # sem token: mostra o fluxo
  python approval_bot.py --enqueue "AirdropLord" fake_airdrop "link de claim falso"
  python approval_bot.py --serve                                  # loop real de long polling

Credenciais (.env): TELEGRAM_BOT_TOKEN (do @BotFather) + TELEGRAM_CHAT_ID (seu id;
descubra mandando /start pro seu bot e vendo getUpdates). 100% stdlib: zero pip.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

OPS = Path(__file__).resolve().parent
ROOT = OPS.parent
FILA = OPS / "fila_aprovacao.jsonl"
DECISOES = OPS / "decisoes.jsonl"

def env(key: str) -> str:
    p = ROOT / ".env"
    if not p.exists():
        return ""
    for l in p.read_text().splitlines():
        if l.startswith(key + "="):
            return l.split("=", 1)[1].strip()
    return ""

TOKEN, CHAT_ID = env("TELEGRAM_BOT_TOKEN"), env("TELEGRAM_CHAT_ID")

def tg(method: str, params: dict) -> dict:
    url = f"https://api.telegram.org/bot{TOKEN}/{method}"
    data = urllib.parse.urlencode({"json": json.dumps(params)}).encode()
    # Bot API aceita JSON direto:
    req = urllib.request.Request(url, data=json.dumps(params).encode(),
            headers={"Content-Type": "application/json",
                     "User-Agent": "Mozilla/5.0 (mod247-approval)"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read().decode())

def load_fila() -> list[dict]:
    return [json.loads(l) for l in FILA.read_text().splitlines()] if FILA.exists() else []

def save_fila(rows: list[dict]) -> None:
    FILA.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")

def enqueue(user: str, category: str, reason: str) -> None:
    rows = load_fila()
    rows.append({"id": int(time.time() * 1000), "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
                 "user": user, "category": category, "reason": reason,
                 "status": "pendente"})
    save_fila(rows)
    print(f"enfileirado #{rows[-1]['id']}: {user} ({category})")

def texto_msg(r: dict) -> str:
    return (f"🛡️ MOD 24/7 — ação destrutiva pendente\n\n"
            f"👤 usuário: {r['user']}\n🏷️ família: {r['category']}\n"
            f"📝 motivo: {r['reason']}\n🕐 {r['ts']}\n\nAprovar ban+delete?")

def serve() -> None:
    if not TOKEN or not CHAT_ID:
        sys.exit("preencha TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID no .env (ver cabeçalho)")
    print(f"porteiro no ar — aprovando via chat {CHAT_ID}. Ctrl+C para parar.")
    offset = 0
    while True:
        try:
            for r in load_fila():
                if r["status"] == "pendente":
                    tg("sendMessage", {
                        "chat_id": CHAT_ID, "text": texto_msg(r),
                        "reply_markup": {"inline_keyboard": [[
                            {"text": "✅ Aprovar", "callback_data": f"ok:{r['id']}"},
                            {"text": "❌ Negar",   "callback_data": f"no:{r['id']}"}]]}})
                    r["status"] = "enviado"
                    save_fila(load_fila() and rows_update(r))
            upd = tg("getUpdates", {"offset": offset, "timeout": 25})
            for u in upd.get("result", []):
                offset = u["update_id"] + 1
                cb = u.get("callback_query")
                if not cb:
                    continue
                verdict, rid = cb["data"].split(":", 1)
                decide(int(rid), verdict == "ok")
                tg("answerCallbackQuery", {"callback_query_id": cb["id"],
                    "text": "✅ aprovado" if verdict == "ok" else "❌ negado"})
                tg("editMessageText", {"chat_id": CHAT_ID,
                    "message_id": cb["message"]["message_id"],
                    "text": cb["message"]["text"] + f"\n\n👉 VOCÊ: {'✅ APROVADO' if verdict=='ok' else '❌ NEGADO'}"})
        except Exception as e:
            print(f"(rede oscilou: {e}; seguindo)")
        time.sleep(2)

def rows_update(row: dict) -> list[dict]:
    rows = load_fila()
    for i, r in enumerate(rows):
        if r["id"] == row["id"]:
            rows[i] = row
    return rows

def decide(rid: int, ok: bool) -> None:
    rows = load_fila()
    for r in rows:
        if r["id"] == rid:
            r["status"] = "aprovado" if ok else "negado"
    save_fila(rows)
    with DECISOES.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"id": rid, "decisao": "aprovado" if ok else "negado",
                            "ts": time.strftime("%Y-%m-%d %H:%M:%S")}, ensure_ascii=False) + "\n")
    print(f"#{rid} -> {'APROVADO' if ok else 'NEGADO'} (decisoes.jsonl atualizado)")

def demo() -> None:
    amostra = {"id": 999, "user": "AirdropLord", "category": "fake_airdrop",
               "reason": "link de claim falso (https://claim-base.xyz/claim)",
               "ts": time.strftime("%Y-%m-%d %H:%M:%S")}
    print("== DEMO do porteiro (sem token, sem rede) ==\n")
    print("O que chegaria no seu Telegram agora:\n")
    print("┌" + "─" * 52 + "┐")
    for linha in texto_msg(amostra).splitlines():
        linha = linha if len(linha) <= 48 else linha[:45] + "..."
        print(f"│ {linha:<50} │")
    print(f"│ {'[ ✅ Aprovar ]   [ ❌ Negar ]':<50} │")
    print("└" + "─" * 52 + "┘")
    print("\nSeu toque grava em ops/decisoes.jsonl -> o adapter Discord executa.")
    print("Custo: US$ 0 (Bot API grátis) · pip: nenhum (stdlib)")

if __name__ == "__main__":
    if "--demo" in sys.argv:
        demo()
    elif "--enqueue" in sys.argv:
        i = sys.argv.index("--enqueue")
        enqueue(*sys.argv[i + 1: i + 4])
    else:
        serve()
