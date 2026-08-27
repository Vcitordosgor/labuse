"""E5 (parcours d'entrée) — cohérence Stripe ⇄ app : l'app ne facture JAMAIS un montant
différent de celui qu'elle affiche. Stripe est mocké (aucun appel réseau)."""
from __future__ import annotations

import pytest

from labuse import facturation as F
from labuse.config import get_settings


def _fake_stripe(unit_amount_integral=None, unit_amount_flash=None, interval="month"):
    prices = {}
    if unit_amount_integral is not None:
        prices["price_integral"] = type("P", (), {"unit_amount": unit_amount_integral, "currency": "eur",
                                                   "recurring": {"interval": interval}})()
    if unit_amount_flash is not None:
        prices["price_flash"] = type("P", (), {"unit_amount": unit_amount_flash, "currency": "eur",
                                               "recurring": None})()

    class _Price:
        @staticmethod
        def retrieve(pid):
            if pid not in prices:
                raise RuntimeError("No such price")
            return prices[pid]

    return type("S", (), {"Price": _Price})()


def test_garde_refuse_prix_divergent(monkeypatch):
    """Prix Stripe 499 € alors que l'app affiche 349 € → ConfigError claire, pas de facturation."""
    s = _fake_stripe(unit_amount_integral=49900)
    with pytest.raises(F.ConfigError, match="INCOH"):
        F._garde_coherence_prix(s, "price_integral", 349 * 100, "Intégral")


def test_garde_passe_prix_concordant(monkeypatch):
    s = _fake_stripe(unit_amount_integral=34900)
    F._garde_coherence_prix(s, "price_integral", 349 * 100, "Intégral")  # ne lève pas


def test_garde_tolere_lecture_impossible():
    """Une lecture Stripe qui échoue (réseau) ne bloque pas un paiement (seule une divergence lève)."""
    s = _fake_stripe()  # aucun prix connu → retrieve lève → toléré
    F._garde_coherence_prix(s, "price_inconnu", 349 * 100, "Intégral")  # ne lève pas


def test_verifier_prix_stripe_ok(monkeypatch):
    monkeypatch.setattr(get_settings(), "stripe_secret_key", "sk_test_fake")
    monkeypatch.setattr(get_settings(), "stripe_price_integral", "price_integral")
    monkeypatch.setattr(get_settings(), "stripe_price_flash", "price_flash")
    monkeypatch.setattr(F, "_stripe", lambda: _fake_stripe(34900, 7900))
    lignes = F.verifier_prix_stripe()
    assert all(r["ok"] for r in lignes), lignes


def test_verifier_prix_stripe_ecart(monkeypatch):
    monkeypatch.setattr(get_settings(), "stripe_secret_key", "sk_test_fake")
    monkeypatch.setattr(get_settings(), "stripe_price_integral", "price_integral")
    monkeypatch.setattr(get_settings(), "stripe_price_flash", "price_flash")
    monkeypatch.setattr(F, "_stripe", lambda: _fake_stripe(49900, 7900))   # Intégral faux
    lignes = F.verifier_prix_stripe()
    integral = next(r for r in lignes if r["offre"] == "integral")
    assert not integral["ok"] and "499" in integral["detail"]
