#!/usr/bin/env python3
"""Mod 24/7 — motor de triagem de moderacao para comunidades web3 (100% local).

Pipeline: mensagem -> classificar (scam/spam/faq/ok) -> acao -> log -> relatorio.

Padrao operacional (igual ao resto do seu stack):
  agente detecta -> humano aprova (acoes destrutivas) -> agente executa.
No demo local as acoes sao simuladas e tudo e logado em out/demo-log.jsonl.

Uso:
  python mod247.py demo     # bateria de 19 mensagens (onda de phishing + legitimos)
  python mod247.py chat     # modo interativo: digite mensagens e veja a triagem
  python mod247.py report   # reimprime o ultimo relatorio

Zero dependencias externas. Adaptadores reais (Discord/Telegram) entram depois.
"""
from __future__ import annotations

import json
import re
import sys
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

BASE = Path(__file__).resolve().parent
OUT = BASE / "out"

# ----------------------------------------------------------------- modelo ---


@dataclass
class Message:
    user: str
    text: str
    ts: float
    channel: str = "geral"


@dataclass
class Decision:
    action: str                    # ban+delete | delete+warn | mute 10m | answer_faq | none
    category: str | None = None
    answer: str | None = None
    latency_ms: float = 0.0
    needs_approval: bool = True    # no modo real, acoes destrutivas exigem OK humano


# ----------------------------------------------------------------- regras ---

# Familias de golpe que mais drenam comunidades (fake airdrop, wallet-verify,
# pedido de seed, falso suporte, links de phishing, typosquat, "lucro garantido").
SCAM_RULES: list[tuple[str, re.Pattern, str]] = [
    ("seed_drain", re.compile(
        r"seed\s*phrase|recovery\s*phrase|backup\s*phrase|\b12\s*words\b|\b24\s*words\b", re.I),
        "ban+delete"),
    ("fake_airdrop", re.compile(
        r"free\s+airdrop|claim\s+(your\s+)?(free\s+)?(airdrop|rewards?|tokens?)\b|airdrop\s+(is\s+)?live", re.I),
        "ban+delete"),
    ("phishing_verify", re.compile(
        r"verify\s+(your\s+)?wallet|wallet\s+verification|sync\s+your\s+wallet|validate\s+(your\s+)?wallet", re.I),
        "ban+delete"),
    ("impersonation", re.compile(
        r"official\s+support|\b(support|admin|mod)\s+(team\s+)?(here|will\s+dm)\b|"
        r"i'?m\s+(from\s+)?(the\s+)?(official\s+)?support\b", re.I),
        "ban+delete"),
    ("phishing_link", re.compile(
        r"https?://\S*(\.click|\.icu|\.top/claim|-claim\.|claim-)", re.I),
        "ban+delete"),
    ("typosquat", re.compile(
        r"metamsak|metarnask|binanace|binanse|uniswp|uniswap-claim|pancakswap", re.I),
        "ban+delete"),
    ("guaranteed_profit", re.compile(
        r"guaranteed\s+profit|100x\s+guaranteed|double\s+your\s+(btc|eth|usdt|money)|risk[- ]free\s+income", re.I),
        "ban+delete"),
    ("pump_shill", re.compile(
        r"\$\w{2,6}\s+(is\s+)?(mooning|about\s+to\s+moon|100x)|buy\s+now\s+or\s+regret", re.I),
        "delete+warn"),
]

# FAQ cobre ~80% das perguntas repetidas de comunidade (o 2o produto do moderador).
FAQ_RULES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bwen\b.*\b(token|launch|listing|tge)\b|\bwhen\s+(token|launch|listing|tge)", re.I),
     "Dates are ONLY announced in official pinned channels. The team will NEVER DM you first. Stay safe 🛡️"),
    (re.compile(r"contract\s+(address|ca)|\bca\b\s*\?", re.I),
     "Official contract address lives in the PINNED message only ⚠️ Never trust a CA sent via DM."),
    (re.compile(r"how\s+(do\s+i|to)\s+buy|where\s+(can\s+i\s+)?buy", re.I),
     "Full buying guide is in #how-to-buy. Always verify links against the pinned message."),
    (re.compile(r"\broadmap\b", re.I),
     "Latest roadmap is pinned in #announcements — happy to clarify anything there!"),
    (re.compile(r"\bteam\b.*\b(doxxed|anon|who)\b|who\s+is\s+(the\s+)?team", re.I),
     "Core team info is on the official site (link in pins). Admins will NEVER ask for funds or keys."),
]

SPAM_WINDOW_S = 30.0
SPAM_MAX_MSGS = 4


# ----------------------------------------------------------------- engine ---


class Engine:
    """Classificador deterministico: regras primeiro, FAQ depois, spam por janela."""

    def __init__(self, window: float = SPAM_WINDOW_S, max_msgs: int = SPAM_MAX_MSGS):
        self.window = window
        self.max_msgs = max_msgs
        self._recent: dict[str, list[float]] = {}

    def classify(self, msg: Message) -> Decision:
        t0 = time.perf_counter()
        dec = self._decide(msg)
        dec.latency_ms = (time.perf_counter() - t0) * 1000.0
        return dec

    def _decide(self, msg: Message) -> Decision:
        for name, rx, action in SCAM_RULES:
            if rx.search(msg.text):
                return Decision(action=action, category=name)

        hist = self._recent.setdefault(msg.user, [])
        hist.append(msg.ts)
        self._recent[msg.user] = [t for t in hist if t >= msg.ts - self.window]
        if len(self._recent[msg.user]) > self.max_msgs:
            return Decision(action="mute 10m", category="spam_flood")

        for rx, answer in FAQ_RULES:
            if rx.search(msg.text):
                return Decision(action="answer_faq", category="faq",
                                answer=answer, needs_approval=False)

        return Decision(action="none", needs_approval=False)


# ------------------------------------------------------------- cenario demo ---
# Raid simulado de 19 mensagens: 6 golpes de 6 familias, 1 flood de spam,
# 5 perguntas de FAQ e 3 mensagens legitimas (nao podem ser tocadas).

SCENARIO: list[tuple[str, float, str]] = [
    ("ana.eth",       0, "gm fam! just bridged to base, fees are so cheap today"),
    ("newbie_dev",    8, "gm! wen token? any dates announced?"),
    ("Support Team", 15, "Hello, this is the official support team. To fix sync "
                         "issues please verify your wallet at https://wallet-verify.click/verify"),
    ("holderAna",    22, "what's the contract address? I don't want to buy the wrong one"),
    ("AirdropLord",  29, "🚨 FREE AIRDROP LIVE! Claim your free airdrop tokens now: "
                         "https://claim-base.xyz/claim"),
    ("traderJoe",    36, "how do i buy on base? is there a guide?"),
    ("MetaMaskHelp", 43, "Your MetaMask wallet is out of sync. Sync your wallet now: "
                         "https://metamask-verify.top/claim"),
    ("curiousCat",   50, "is the team doxxed? want to know before investing more"),
    ("InvestPro",    57, "Guaranteed profit!! Double your USDT with our new vault — "
                         "risk-free income 🚀"),
    ("builderBee",   64, "where can I read the latest roadmap?"),
    ("WhaleTip",     71, "DM me your seed phrase and I'll whitelist you for the presale 😉"),
    ("dev_dan",      78, "anyone here building on the SDK? got a question about nonces"),
    ("PumpKing",     85, "$FAKE is mooning! buy now or regret forever, 100x soon"),
    ("spamBot99",    90, "JOIN MY TRADING GROUP T.ME/XYZ LFG 🚀"),
    ("spamBot99",    92, "JOIN MY TRADING GROUP T.ME/XYZ LFG 🚀"),
    ("spamBot99",    94, "JOIN MY TRADING GROUP T.ME/XYZ LFG 🚀"),
    ("spamBot99",    96, "JOIN MY TRADING GROUP T.ME/XYZ LFG 🚀"),
    ("spamBot99",    99, "JOIN MY TRADING GROUP T.ME/XYZ LFG 🚀"),
    ("ana.eth",     105, "great space today, thanks team!"),
]

THREAT_USERS = {"Support Team", "AirdropLord", "MetaMaskHelp", "InvestPro",
                "WhaleTip", "PumpKing"}
LEGIT_SAFE = {"ana.eth", "dev_dan"}


def run_scenario(engine: Engine | None = None) -> list[dict]:
    eng = engine or Engine()
    t0 = 1_755_000_000.0
    log = []
    for user, off, text in SCENARIO:
        msg = Message(user=user, text=text, ts=t0 + off)
        dec = eng.classify(msg)
        log.append({
            "user": user, "channel": msg.channel, "text": text,
            "action": dec.action, "category": dec.category,
            "answer": dec.answer, "latency_ms": round(dec.latency_ms, 3),
        })
    return log


def build_report(log: list[dict]) -> tuple[str, dict]:
    acts = Counter(r["action"] for r in log)
    cats = Counter(r["category"] for r in log if r["category"] and r["action"] != "mute 10m")
    spammers = {r["user"] for r in log if r["action"] == "mute 10m"}
    lat = [r["latency_ms"] for r in log]
    data = {
        "messages": len(log),
        "bans": acts.get("ban+delete", 0),
        "warns": acts.get("delete+warn", 0),
        "mutes": acts.get("mute 10m", 0),
        "faqs": acts.get("answer_faq", 0),
        "untouched": acts.get("none", 0),
        "avg_latency_ms": round(sum(lat) / max(len(lat), 1), 3),
        "max_latency_ms": round(max(lat, default=0.0), 3),
        "threat_categories": sorted(set(cats) - {"faq"}),
        "spammers_muted": sorted(spammers),
        "api_cost_usd": 0.0,
    }
    rows = ["| # | user | verdict | category | latency (ms) |", "|---|---|---|---|---|"]
    for i, r in enumerate(log, 1):
        rows.append(f"| {i} | {r['user']} | {r['action']} | {r['category'] or '—'} | {r['latency_ms']} |")
    md = f"""# 🛡️ MOD 24/7 — Demo Battery Report

_Local simulation · {data['messages']} messages · US$ {data['api_cost_usd']:.2f} API cost_

| metric | value |
|---|---|
| Messages processed | {data['messages']} |
| Scam threats blocked | **{data['bans'] + data['warns']}** ({data['bans']} ban+delete, {data['warns']} delete+warn) |
| Spammers muted | {data['mutes']} (flood > {SPAM_MAX_MSGS} msg/{SPAM_WINDOW_S:.0f}s) |
| FAQs answered instantly | {data['faqs']} |
| Legit messages untouched | {data['untouched']} |
| Avg triage latency | **{data['avg_latency_ms']} ms** (max {data['max_latency_ms']} ms) |
| Threat families caught | {", ".join(data["threat_categories"])} |
| API cost | US$ 0.00 (deterministic rules engine) |

## Timeline

{chr(10).join(rows)}

_Operating mode in production: destructive actions (ban/mute/warn) land in a
human-approval queue before execution — the engine triages, the human signs off._
"""
    return md, data


# -------------------------------------------------------------------- cli ---


def cmd_demo() -> None:
    log = run_scenario()
    OUT.mkdir(exist_ok=True)
    (OUT / "demo-log.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in log) + "\n", encoding="utf-8")
    md, data = build_report(log)
    (OUT / "demo-report.md").write_text(md, encoding="utf-8")
    (OUT / "demo-report.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"== MOD 24/7 demo: {data['messages']} mensagens processadas ==")
    print(f"  golpes bloqueados : {data['bans'] + data['warns']} "
          f"({data['bans']} ban+delete, {data['warns']} delete+warn)")
    print(f"  spammers mutados  : {data['mutes']}  {data['spammers_muted']}")
    print(f"  FAQs respondidas  : {data['faqs']}")
    print(f"  legitimos intactos: {data['untouched']}")
    print(f"  latencia media    : {data['avg_latency_ms']} ms (max {data['max_latency_ms']} ms)")
    print(f"  custo de API      : US$ {data['api_cost_usd']:.2f}")
    print(f"  relatorio         : {OUT / 'demo-report.md'}")


def cmd_chat() -> None:
    eng = Engine()
    print("MOD 24/7 — modo interativo. Digite mensagens (sair para encerrar).")
    while True:
        try:
            text = input("msg> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not text or text.lower() in {"sair", "exit", "quit"}:
            break
        d = eng.classify(Message(user="voce", text=text, ts=time.time()))
        extra = f" -> {d.answer}" if d.answer else ""
        print(f"  [{d.category or '—'}] {d.action} ({d.latency_ms:.3f} ms){extra}")


def cmd_report() -> None:
    p = OUT / "demo-report.md"
    print(p.read_text(encoding="utf-8") if p.exists()
          else "Sem relatorio. Rode primeiro: python mod247.py demo")


def main(argv: list[str]) -> None:
    cmd = argv[1] if len(argv) > 1 else "demo"
    {"demo": cmd_demo, "chat": cmd_chat, "report": cmd_report}.get(cmd, cmd_demo)()


if __name__ == "__main__":
    main(sys.argv)
