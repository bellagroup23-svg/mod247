#!/usr/bin/env python3
"""Bateria de testes do Mod 24/7. Rode: python -m unittest test_mod247 -v"""
import unittest

from mod247 import Engine, Message, SCENARIO, LEGIT_SAFE, THREAT_USERS, run_scenario


def triage(text: str, user: str = "u1", ts: float = 0.0):
    return Engine().classify(Message(user=user, text=text, ts=ts))


class TestScamFamilies(unittest.TestCase):
    def test_seed_phrase_eh_ban(self):
        d = triage("send me your seed phrase for the whitelist")
        self.assertEqual(d.action, "ban+delete")
        self.assertEqual(d.category, "seed_drain")

    def test_fake_airdrop_eh_ban(self):
        d = triage("Claim your free airdrop tokens now!")
        self.assertEqual(d.action, "ban+delete")
        self.assertEqual(d.category, "fake_airdrop")

    def test_wallet_verify_phishing_eh_ban(self):
        d = triage("please verify your wallet at https://wallet-verify.click/verify")
        self.assertEqual(d.action, "ban+delete")
        self.assertIn(d.category, ("phishing_verify", "phishing_link"))

    def test_lucro_garantido_eh_ban(self):
        d = triage("Guaranteed profit! Double your USDT today")
        self.assertEqual(d.action, "ban+delete")
        self.assertEqual(d.category, "guaranteed_profit")

    def test_shill_eh_aviso_nao_ban(self):
        d = triage("$FAKE is mooning! buy now or regret")
        self.assertEqual(d.action, "delete+warn")

    def test_acoes_destrutivas_exigem_aprovacao(self):
        d = triage("Claim your free airdrop now!")
        self.assertTrue(d.needs_approval)


class TestFaqELegitimos(unittest.TestCase):
    def test_faq_wen_token(self):
        d = triage("gm! wen token?")
        self.assertEqual(d.action, "answer_faq")
        self.assertIn("NEVER DM", d.answer)

    def test_faq_contract_address(self):
        d = triage("what's the contract address?")
        self.assertEqual(d.action, "answer_faq")

    def test_mensagem_legitima_intacta(self):
        d = triage("anyone building on the SDK today?")
        self.assertEqual(d.action, "none")
        self.assertIsNone(d.category)


class TestSpam(unittest.TestCase):
    def test_flood_eh_mutado_no_5o_envio(self):
        eng = Engine()
        actions = [
            eng.classify(Message(user="bot99", text="JOIN MY GROUP", ts=float(i))).action
            for i in range(5)
        ]
        self.assertEqual(actions[:4], ["none"] * 4)
        self.assertEqual(actions[4], "mute 10m")

    def test_janela_expira_e_reseta(self):
        eng = Engine()
        for i in range(4):
            eng.classify(Message(user="u", text="oi", ts=float(i)))
        d = eng.classify(Message(user="u", text="oi de novo", ts=100.0))
        self.assertEqual(d.action, "none")  # fora da janela de 30s


class TestBateriaDemo(unittest.TestCase):
    def test_catch_rate_100_e_zero_falso_positivo(self):
        log = run_scenario()
        ameacas = [r for r in log if r["user"] in THREAT_USERS]
        legitimos = [r for r in log if r["user"] in LEGIT_SAFE]
        self.assertTrue(all(r["action"] in ("ban+delete", "delete+warn") for r in ameacas))
        self.assertTrue(all(r["action"] == "none" for r in legitimos))


if __name__ == "__main__":
    unittest.main(verbosity=2)
