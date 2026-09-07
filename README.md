# 🛡️ MOD 24/7 — AI-assisted security toolkit for web3 & gaming communities

> Porteiro digital 24/7: detecta golpes, modera e responde FAQ — em Python puro,
> **sem API paga** e custo marginal **US$ 0,00**. Roda num laptop comum.

**✅ Prova ao vivo (05/09/2026):**
`12/12` testes unitários OK · demo de combate: **6 golpes bloqueados**
(5 ban+delete, 1 delete+warn) · 1 spammer mutado · 5 FAQs respondidas ·
**7 mensagens legítimas intactas** · latência média **0,038 ms** ·
custo de API **US$ 0,00** — relatório completo: [`demo-report.md`](./demo-report.md)

## 🧩 O que tem dentro

| peça | papel |
|---|---|
| `mod247/mod247.py` | motor anti-golpe e de moderação (regras + heurísticas) |
| `mod247/test_mod247.py` | bateria com 12 testes |
| `ops/discord_adapter.py` | adaptador ao vivo p/ Discord (token via `.env` local) |
| `ops/approval_bot.py` | bot de aprovações no Telegram |
| `ops/wallet_watch.py` | vigia de carteira na rede **Base** (avisa quando cai USDC/ETH) |
| `ops/env_doctor.py` | "médico" do ambiente: audita a instalação em 1 comando |
| `instalar.py` | instalador guiado (Windows/Linux/Mac) + agendador de rotinas |
| `index.html` | página pública do projeto (servida via GitHub Pages) |

## ⚡ Quickstart (5 min)

```bash
python instalar.py            # instala e agenda cockpit diário + vigia de login
cd mod247
python -m unittest test_mod247   # esperado: Ran 12 tests ... OK
python mod247.py demo            # bateria de combate, relatório em out/
python ../ops/wallet_watch.py --once --address 0xSUA_CARTEIRA
```

## 🔐 Segurança

Tokens e senhas vivem **só no `.env` local** (veja `.env.example`) — o
`.gitignore` deste repositório bloqueia `.env*`, bancos e caches. Se um token
aparecer num print: revogue na hora (BotFather → `/revoke`; Portal de
Developers do Discord → Reset Token).

## 💼 Serviços / freelance

Moderação e segurança para comunidades web3, jogos e criadores — setup + retainer.

- 💬 Discord: `fabiano.mod247`
- 🤖 Telegram: [@fabiano_mod247_bot](https://t.me/fabiano_mod247_bot)
- ✉️ bellagroup23@gmail.com
- 💵 Pagamento: **USDC na rede Base** — endereço público no rodapé da página do projeto

---
Feito no Rio de Janeiro 🇧🇷 com um laptop e café. [MIT License](./LICENSE).
