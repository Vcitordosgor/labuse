"""URGENCE-1 (NU-F-018) — GARDE : les liens des mails pointent sur une URL PUBLIQUE absolue
(https://app.labuse.immo), jamais sur localhost ni vide.

`LABUSE_PUBLIC_BASE_URL` est OBLIGATOIRE pour envoyer : ce test ÉCHOUE si le garde laisse passer
une URL absente/locale (c.-à-d. si la variable manque), et prouve que l'envoi est FAIL-CLOSED.
"""
from __future__ import annotations

import pytest

from labuse import config


def test_exiger_base_url_refuse_absente_ou_vide():
    """Variable absente / vide → RuntimeError (la variable est obligatoire)."""
    with pytest.raises(RuntimeError):
        config.exiger_base_url_publique("")
    with pytest.raises(RuntimeError):
        config.exiger_base_url_publique("   ")


def test_exiger_base_url_refuse_localhost():
    """Toute adresse locale est refusée (un client ne pourrait pas cliquer)."""
    for u in ("http://localhost:8000", "http://127.0.0.1:8000", "https://0.0.0.0/socle"):
        with pytest.raises(RuntimeError):
            config.exiger_base_url_publique(u)


def test_exiger_base_url_accepte_publique_et_normalise():
    """Une URL publique absolue passe ; le slash final est retiré."""
    assert config.exiger_base_url_publique("https://app.labuse.immo/") == "https://app.labuse.immo"
    assert config.exiger_base_url_publique("https://app.labuse.immo") == "https://app.labuse.immo"


def test_variable_env_obligatoire_echoue_si_manque(monkeypatch):
    """Si LABUSE_PUBLIC_BASE_URL manque (réglage retombé sur vide), le garde DOIT refuser —
    c'est le filet « test qui échoue si elle manque »."""
    class _Settings:
        public_base_url = ""   # variable d'environnement absente
    monkeypatch.setattr(config, "get_settings", lambda: _Settings())
    with pytest.raises(RuntimeError):
        config.exiger_base_url_publique()


def test_digest_client_fail_closed_sur_localhost():
    """Le digest client (`envoyer_digests`) ne part PAS avec un lien mort : le garde lève AVANT toute
    requête base (d=None suffit — la garde ne touche pas la base)."""
    from labuse.api import events
    with pytest.raises(RuntimeError):
        events.envoyer_digests(None, base_url="http://localhost:8000", dry_run=False)


def test_digest_radar_fail_closed_sur_localhost():
    """Idem pour l'alerte de veille Radar (`pige.digests.envoyer`)."""
    from labuse.pige import digests
    with pytest.raises(RuntimeError):
        digests.envoyer(None, base_url="", dry_run=False)
