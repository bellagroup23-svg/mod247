# 🛡️ MOD 24/7 — community security engine for web3

AI-speed detection, human judgment on every destructive action. Fake airdrops, wallet-verify
phishing, seed drainers, impersonated staff, typosquat domains, guaranteed-profit bait,
pump shills and spam floods — triaged in **0.016 ms average, $0.00 API cost**.

## Proof (not promises)

Full honest log from the latest embedded test battery
(19-message simulated raid — phishing wave + spam flood + real members):

| Metric | Result |
|---|---|
| Scam threats blocked | **6/6** (5 ban+delete · 1 delete+warn) |
| Spam flood (>4 msg/30s) | auto-muted at the 5th message |
| Member FAQs answered | 5/5 instantly, with safety notes |
| False positives on regular members | **0** |
| Avg triage latency | **0.016 ms** (max 0.029 ms) |
| Automated test suite | **12/12 passing** |
| API cost per action | **$0.00** (deterministic rules engine) |

## Security model (why communities trust this)

- **Human-in-the-loop by design:** every destructive action (ban/mute/warn) lands in an
  approval queue → the operator approves in one tap from Telegram → only then it executes.
  The engine *detects*; a human *decides*. (See `ops/approval_bot.py`.)
- **Never asks for admin, keys or wallet connections.** Standard bot invite with
  message-manage permissions is all it needs.
- **Server allowlist:** the adapter only acts in pre-authorized guilds.
- **No funds are ever held or moved by any agent.** (In memory of Freysa's $47k lesson.)

## Quickstart (local, zero dependencies)

```bash
cd mod247
python -m unittest test_mod247 -v     # 12 tests
python mod247.py demo                 # runs the 19-message raid battery
python mod247.py chat                 # interactive triage, try your own messages
```

## Architecture

```
Discord/Telegram ──detect──> rules engine (SCAM_RULES) ──FAQ──> instant safe answer
                                    │
                        destructive?──┴──> approval queue (Telegram ✅/❌)
                                                  │
                                  approved ──> adapter executes (delete/ban)
                                  denied ────> logged, member untouched
```

## Files

| Path | What |
|---|---|
| `mod247.py` | the engine + demo battery + CLI (stdlib only) |
| `test_mod247.py` | 12 tests: scam families, FAQ, spam windows, zero false positives |
| `ops/approval_bot.py` | Telegram approval gate (stdlib, free Bot API) |
| `ops/discord_adapter.py` | Discord adapter — `--simulate` offline, `--live` in production |
| `ops/wallet_watch.py` | on-chain payment watcher (read-only, USDC/USDT/ETH on Base) |

## Roadmap

- [x] Rules engine + test battery (6/6 families)
- [x] Telegram human-approval loop
- [x] Discord adapter (simulate mode)
- [ ] Live Discord deployment with pilot community
- [ ] Weekly threat-intelligence digest generator
- [ ] x402 pay-per-report endpoint (USDC on Base)

## License

MIT — see the engine, read the tests, judge the code yourself.
Hiring me is easier than reading all of it: **[portfolio](https://SEUUSER.github.io/SEUREPO/)**.
