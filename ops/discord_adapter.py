#!/usr/bin/env python3
"""Adapter Discord — fecha o circuito:  detecta -> aprova (Telegram) -> executa (aqui).

Modos:
  --simulate   100% offline (use ate o 1o trial fechar). Le ops/decisoes.jsonl e
               "executa" num log falso: ops/execucao_simulada.log. Nada sai do PC.
  --live       modo real (so com trial FECHADO):
                 pip install discord.py  +  DISCORD_BOT_TOKEN no .env
               mensagens novas -> mod247.Engine -> destrutivo vai p/ fila do Telegram;
               aprovados viram delete/ban de verdade no servidor do cliente.

Regras de seguranca (nao remova):
  * executa SOMENTE o que constar "aprovado" em decisoes.jsonl;
  * so serve servidores da DISCORD_GUILD_ALLOWLIST (.env) — fora dela, ignora;
  * nunca peca Administrator; a lista enxuta de permissoes esta no AUTOMACAO-TOTAL.md.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

OPS = Path(__file__).resolve().parent
ROOT = OPS.parent
FILA = OPS / "fila_aprovacao.jsonl"
DECISOES = OPS / "decisoes.jsonl"
SIMLOG = OPS / "execucao_simulada.log"

def load_jsonl(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []

def save_jsonl(p: Path, rows: list[dict]) -> None:
    p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")

def env(key: str) -> str:
    p = ROOT / ".env"
    for l in p.read_text().splitlines() if p.exists() else []:
        if l.startswith(key + "="):
            return l.split("=", 1)[1].strip()
    return ""

# --------------------------------------------------------------- simulate ---

def simulate() -> None:
    fila = load_jsonl(FILA)
    if not fila:
        sys.exit("fila vazia — alimente: python ops/approval_bot.py --enqueue user fake_airdrop motivo")
    decididas = {d["id"]: d["decisao"] for d in load_jsonl(DECISOES)}
    executadas = descartadas = aguardando = 0
    with SIMLOG.open("a", encoding="utf-8") as log:
        for r in fila:
            if r["status"] in ("executado(sim)", "descartado"):
                continue
            voto = decididas.get(r["id"])
            if voto == "aprovado":
                ts = time.strftime("%Y-%m-%d %H:%M:%S")
                log.write(f"[{ts}] BAN+DELETE (SIMULADO) user={r['user']} "
                          f"familia={r['category']} motivo={r['reason']}\n")
                r["status"] = "executado(sim)"
                executadas += 1
            elif voto == "negado":
                log.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] NEGADO por voce -> "
                          f"sem acao sobre {r['user']}\n")
                r["status"] = "descartado"
                descartadas += 1
            else:
                aguardando += 1
    save_jsonl(FILA, fila)
    print(f"== SIMULATE ==  executadas(sim): {executadas} · negadas: {descartadas} "
          f"· aguardando seu toque no Telegram: {aguardando}")
    print(f"log: {SIMLOG}")

# ------------------------------------------------------------------- live ---

def live() -> None:
    try:
        import discord  # noqa: F401
    except ImportError:
        sys.exit("modo live pede: pip install discord.py  (e DISCORD_BOT_TOKEN no .env)")
    token = env("DISCORD_BOT_TOKEN")
    allow = {g.strip() for g in env("DISCORD_GUILD_ALLOWLIST").split(",") if g.strip()}
    if not token or not allow:
        sys.exit("preencha DISCORD_BOT_TOKEN e DISCORD_GUILD_ALLOWLIST no .env")
    sys.path.insert(0, str(ROOT / "mod247"))
    from mod247 import Engine, Message          # noqa: E402
    import discord                               # noqa: E402

    eng = Engine()
    client = discord.Client(intents=discord.Intents(messages=True, message_content=True))

    @client.event
    async def on_message(m):
        if m.author.bot or str(getattr(m.guild, "id", "")) not in allow:
            return
        d = eng.classify(Message(user=str(m.author), text=m.content or "",
                                 ts=m.created_at.timestamp(),
                                 channel=str(m.channel)))
        if d.action == "answer_faq" and d.answer:
            await m.reply(d.answer)
        elif d.action in ("ban+delete", "delete+warn", "mute 10m"):
            # NUNCA executa direto: vai para a sua aprovacao no Telegram
            import subprocess
            subprocess.run([sys.executable, str(OPS / "approval_bot.py"), "--enqueue",
                            f"{m.author}#{m.channel}", d.category, (m.content or "")[:60]])
    print("MOD 24/7 LIVE — detectando, FAQ no auto, destrutivo so com seu ✅ no Telegram.")
    client.run(token)

if __name__ == "__main__":
    if "--live" in sys.argv:
        live()
    else:
        simulate()
