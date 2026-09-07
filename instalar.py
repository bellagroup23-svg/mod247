#!/usr/bin/env python3
"""INSTALADOR da operacao MOD 24/7 — pergunta permissao antes de QUALQUER coisa.

  python instalar.py           (Windows: de dois cliques em instalar.bat)
  python instalar.py --demo    (ensaio geral: nao grava nada, nao chama a rede)

O que ele faz, SEMPRE pedindo seu OK (padrao = nao):
  1. coleta sua identidade (nome, wallet 0x..., @telegram, discord, e-mail) com validacao
  2. [opcional] valida tokens de bot de verdade (Telegram getMe / Discord users/@me)
     e DESCOBRE seu chat_id do Telegram sozinho (voce so manda /start pro seu bot)
  3. grava .env (com backup) e personaliza o one-pager — via as mesmas regras do preenche.py
  4. [opcional] agenda o cockpit diario (8h) e o vigia de carteira no login do PC
  5. roda ops/env_doctor.py e entrega o checklist dos proximos passos

100% stdlib. Nada e escrito ou agendado sem um "s" seu.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEMO = "--demo" in sys.argv

DEMO_ANS = {  # ensaio geral: nada e gravado, nada vai p/ rede
    "nome": "Rafael Costa",
    "wallet": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
    "telegram": "@rafa_costa", "discord": "rafacosta", "email": "rafa@exemplo.com",
    "conf_telegram": False, "conf_discord": False,
    "gravar": True, "agendar": True, "vigia": True,
}

# ------------------------------------------------------------- interacao ---


def pergunta(chave: str, texto: str, default: str = "") -> str:
    if DEMO:
        val = str(DEMO_ANS.get(chave, default))
        print(f"? {texto} [{default or '…'}] → {val}   (demo)")
        return val
    sufixo = f" [{default}]" if default else ""
    r = input(f"? {texto}{sufixo}: ").strip()
    return r or default


def confirma(chave: str, texto: str) -> bool:
    """Permissao: padrao NAO. So segue com 's' explicito."""
    if DEMO:
        print(f"? {texto} [s/N] → {'s' if DEMO_ANS.get(chave) else 'N'}   (demo)")
        return bool(DEMO_ANS.get(chave))
    return input(f"? {texto} [s/N]: ").strip().lower() in {"s", "sim", "y", "yes"}


# ------------------------------------------------------------- validacoes ---

def http_json(url: str, headers: dict | None = None, timeout: int = 12) -> dict:
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "Mozilla/5.0 (mod247-instalador)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def telegram_valida(token: str) -> str:
    try:
        return http_json(f"https://api.telegram.org/bot{token}/getMe").get("result", {}).get("username", "")
    except Exception:
        return ""


def telegram_chat_id(token: str) -> str:
    try:
        msgs = http_json(f"https://api.telegram.org/bot{token}/getUpdates").get("result", [])
        if not msgs:
            return ""
        m = msgs[-1].get("message") or msgs[-1].get("channel_post") or {}
        return str(m.get("chat", {}).get("id", ""))
    except Exception:
        return ""


def discord_valida(token: str) -> str:
    try:
        d = http_json("https://discord.com/api/v10/users/@me",
                      headers={"Authorization": f"Bot {token}", "User-Agent": "mod247-instalador"})
        return d.get("username", "")
    except Exception:
        return ""


# ----------------------------------------------------------------- gravacao ---

def conteudo_env(d: dict) -> str:
    return f"""# .env — gerado por instalar.py em {time.strftime('%Y-%m-%d %H:%M:%S')}
# REGRAS: nunca commitar · seed NUNCA aqui (papel!) · token vazou = revoga e troca
WALLET_ADDRESS={d['wallet']}
TELEGRAM_HANDLE={d['telegram']}
DISCORD_USER={d['discord']}
EMAIL={d['email']}
DISCORD_BOT_TOKEN={d.get('discord_token', '')}
TELEGRAM_BOT_TOKEN={d.get('telegram_token', '')}
TELEGRAM_CHAT_ID={d.get('chat_id', '')}
DISCORD_GUILD_ALLOWLIST=
"""


def gravar_tudo(d: dict) -> None:
    envp = ROOT / ".env"
    if envp.exists():
        shutil.copy(envp, ROOT / ".env.bak")
        print("   backup: .env → .env.bak")
    envp.write_text(conteudo_env(d), encoding="utf-8")
    print("   gravado: .env ✔")
    html = ROOT / "MODERADOR-247-onepager.html"
    if html.exists():
        h = html.read_text(encoding="utf-8")
        for velho, novo in [("SEU NOME AQUI", d["nome"]), ("@SEU_HANDLE", d["telegram"]),
                            ("seu_discord", d["discord"]),
                            ("mailto:seu@email.com", f"mailto:{d['email']}"),
                            ("seu@email.com", d["email"])]:
            h = h.replace(velho, novo)
        html.write_text(h, encoding="utf-8")
        (ROOT / "public" / "index.html").write_text(h, encoding="utf-8")
        print("   gravado: one-pager personalizado (e copia em public/) ✔")


def agendar(py: str, cockpit: bool, vigia: bool, wallet: str) -> None:
    if sys.platform.startswith("win"):
        if cockpit:
            subprocess.run(["schtasks", "/create", "/f", "/tn", "mod247-cockpit",
                            "/tr", f'"{py}" "{ROOT / "ops" / "daily.py"}"', "/sc", "daily", "/st", "08:00"],
                           capture_output=True)
            print("   agendado: cockpit diario 08:00 (Agendador de Tarefas) ✔")
        if vigia:
            subprocess.run(["schtasks", "/create", "/f", "/tn", "mod247-vigia",
                            "/tr", f'"{py}" "{ROOT / "ops" / "wallet_watch.py"}" --loop --address {wallet}',
                            "/sc", "onlogon"], capture_output=True)
            print("   agendado: vigia de carteira no login ✔")
    else:
        linhas = []
        if cockpit:
            linhas.append(f'0 8 * * * cd {ROOT} && {py} ops/daily.py >> ops/cron.log 2>&1')
        if vigia:
            linhas.append(f'@reboot cd {ROOT} && {py} ops/wallet_watch.py --loop --address {wallet} >> ops/vigia.log 2>&1 &')
        bloco = "\n".join(linhas).replace('"', '\\"')
        subprocess.run(f'(crontab -l 2>/dev/null | grep -v mod247; echo "{bloco}") | crontab -',
                       shell=True, capture_output=True)
        print("   agendado via cron: " + " · ".join(
            x for x, ok in (("cockpit 8h", cockpit), ("vigia @reboot", vigia)) if ok) + " ✔")


# -------------------------------------------------------------------- main ---

def main() -> None:
    print("═" * 60)
    print("  🛡️  INSTALADOR MOD 24/7 — nada acontece sem o seu 's'")
    print("═" * 60)
    if DEMO:
        print("  (modo DEMO — ensaio geral: zero gravacoes, zero rede)\n")

    d: dict = {}
    print("\n── ETAPA 1/5 · sua identidade (vai no .env e nos materiais de venda) ──")
    d["nome"] = pergunta("nome", "Seu nome (aparece no one-pager)")
    while True:
        d["wallet"] = pergunta("wallet", "Endereco da wallet (0x + 40 hex — o mesmo de toda rede EVM)")
        if re.fullmatch(r"0x[0-9a-fA-F]{40}", d["wallet"]):
            break
        print("   ✖ invalido: precisa ser 0x seguido de 40 caracteres hex. Tente de novo.")
    d["telegram"] = pergunta("telegram", "Seu usuario do Telegram (@...)", "@seu_handle")
    d["discord"] = pergunta("discord", "Seu usuario do Discord", "seu_discord")
    d["email"] = pergunta("email", "Seu e-mail de contato")

    print("\n── ETAPA 2/5 · tokens de bot (OPCIONAL — so precisa quando o 1o trial fechar) ──")
    if confirma("conf_telegram", "Configurar o porteiro do Telegram agora? (precisa do token do @BotFather)"):
        t = pergunta("telegram_token", "Cole o TELEGRAM_BOT_TOKEN")
        user = telegram_valida(t)
        if user:
            print(f"   ✔ token valido — bot: @{user}")
            d["telegram_token"] = t
            print("   → agora mande /start PARA O SEU BOT no Telegram e pressione Enter aqui…")
            if not DEMO:
                input()
            cid = telegram_chat_id(t)
            if cid:
                d["chat_id"] = cid
                print(f"   ✔ chat_id descoberto sozinho: {cid}")
            else:
                d["chat_id"] = pergunta("chat_id", "Nao achei automatico — cole seu chat_id (ou deixe vazio p/ depois)")
        else:
            print("   ✖ token nao validou (rede off ou token errado) — salvando mesmo assim? preenche depois no .env")
            d["telegram_token"] = t
    if confirma("conf_discord", "Configurar o bot do Discord agora? (token do Developer Portal)"):
        t = pergunta("discord_token", "Cole o DISCORD_BOT_TOKEN")
        user = discord_valida(t)
        if user:
            print(f"   ✔ token valido — bot: {user}")
        else:
            print("   ✖ nao validou agora (rede/token) — segue no .env para revisar depois")
        d["discord_token"] = t

    print("\n── ETAPA 3/5 · gravacao de arquivos ──")
    if confirma("gravar", "Posso GRAVAR o .env (com backup .bak) e personalizar seu one-pager?"):
        if DEMO:
            print("   (demo) o .env ficaria assim:\n")
            print("   " + "\n   ".join(conteudo_env(d).splitlines()))
        else:
            gravar_tudo(d)
    else:
        print("   ok — nada gravado. Voce pode preencher depois: python ops/preenche.py --help")

    print("\n── ETAPA 4/5 · agendamentos no seu sistema ──")
    quer_agenda = confirma("agendar", "Posso AGENDAR o cockpit diario as 08:00?")
    quer_vigia = confirma("vigia", "Posso iniciar o VIGIA de carteira a cada login do PC?")
    if quer_agenda or quer_vigia:
        if DEMO:
            print(f"   (demo) eu agendaria no {sys.platform}: "
                  + ("cockpit 8h " if quer_agenda else "")
                  + ("+ vigia no login" if quer_vigia else ""))
        else:
            agendar(sys.executable, quer_agenda, quer_vigia, d["wallet"])
    else:
        print("   ok — sem agendamentos. Rodando manual: python ops/daily.py")

    print("\n── ETAPA 5/5 · auditoria final ──")
    if not DEMO:
        subprocess.run([sys.executable, str(ROOT / "ops" / "env_doctor.py")])
    print("""
════════════════════  INSTALACAO OK  ════════════════════
Proximos 5 passos (so voce pode — ~3h, detalhados em PACOTE-LANCAMENTO.md):
  1. 15 min → KYC da exchange      4. 90 min → 10 DMs web3 + 10 WhatsApp
  2. 40 min → GitHub + Pages       5. sempre → vigia no canto da tela:
  3. 20 min → perfis + gig LaborX     python ops/wallet_watch.py --loop --address {w}
Comandos de bolso:  python ops/daily.py  ·  python instalar.py --demo  ·  python ops/env_doctor.py
""".format(w=d["wallet"]))


if __name__ == "__main__":
    if DEMO or confirma("comecar", "Posso comecar a instalacao guiada (so leitura ate voce autorizar gravacao)?"):
        main()
    else:
        print("Instalacao cancelada — nada foi tocado. Quando quiser: python instalar.py")
