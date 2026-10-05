"""PARCOURS-FIX-1 (point 2) — ÉTANCHÉITÉ du dry-run mail.

Incident PARCOURS-CLIENT-1 G1 : `config.py` → `load_dotenv(.env)` réinjecte `BREVO_API_KEY` dans le
process ; en « testant en local » la 1ʳᵉ invitation est partie POUR DE VRAI (Brevo). Ces tests GRAVENT
la garde : en local, SANS `LABUSE_MAIL_REEL`, ni Brevo ni SMTP ne touchent le réseau — quoi que
contienne le `.env` — et le mail est écrit en `.eml`. En prod, l'envoi réel reste autorisé.
"""
from __future__ import annotations

import pytest

from labuse import brevo, mail
from labuse.config import envoi_reel_autorise, get_settings


@pytest.fixture
def _local_sans_drapeau(monkeypatch, tmp_path):
    """env=local, une CLÉ Brevo bien présente dans l'environnement, AUCUN drapeau d'envoi réel."""
    monkeypatch.setenv("LABUSE_ENV", "local")
    monkeypatch.setenv("BREVO_API_KEY", "xkeysib-UNE-VRAIE-CLE-QUI-NE-DOIT-PAS-SERVIR")
    monkeypatch.delenv("LABUSE_MAIL_REEL", raising=False)
    monkeypatch.setenv("LABUSE_MAIL_DRYRUN_DIR", str(tmp_path))
    # SMTP volontairement configuré : prouve que la garde prime sur smtp_host.
    monkeypatch.setenv("LABUSE_SMTP_HOST", "smtp.gmail.com")
    get_settings.cache_clear()
    yield tmp_path
    get_settings.cache_clear()


def test_garde_ferme_en_local_sans_drapeau(_local_sans_drapeau):
    assert envoi_reel_autorise() is False


def test_garde_ouvre_avec_drapeau(monkeypatch):
    monkeypatch.setenv("LABUSE_ENV", "local")
    monkeypatch.setenv("LABUSE_MAIL_REEL", "1")
    get_settings.cache_clear()
    try:
        assert envoi_reel_autorise() is True
    finally:
        get_settings.cache_clear()


@pytest.mark.parametrize("env", ["production", "pilot"])
def test_garde_toujours_ouverte_en_prod(monkeypatch, env):
    # En prod/pilote l'envoi réel reste autorisé même sans drapeau (jamais de mail client avalé).
    monkeypatch.setenv("LABUSE_ENV", env)
    monkeypatch.delenv("LABUSE_MAIL_REEL", raising=False)
    get_settings.cache_clear()
    try:
        assert envoi_reel_autorise() is True
    finally:
        get_settings.cache_clear()


def test_brevo_zero_appel_reseau_en_dry_run(_local_sans_drapeau, monkeypatch):
    """Le cœur du mandat : clé Brevo présente + pas de drapeau → 0 appel réseau à Brevo, .eml écrit."""
    import httpx

    def _interdit(*a, **k):  # noqa: ANN001 — tout appel réseau est un échec du test
        raise AssertionError("APPEL RÉSEAU BREVO en dry-run — la garde a fui !")

    monkeypatch.setattr(httpx, "post", _interdit)
    monkeypatch.setattr(httpx, "get", _interdit)

    res = brevo.envoyer_template("prospect@exemple-inexistant.re", "essai",
                                 {"PRENOM": "Rémi", "LIEN_INVITATION": "https://x", "FIN_ESSAI": "le 12/10"})
    assert res["envoye"] is False
    assert "dry-run" in res["raison"].lower()
    # un .eml de trace a bien été écrit (preuve inspectable du dry-run)
    emls = list(_local_sans_drapeau.glob("*.eml"))
    assert len(emls) == 1
    contenu = emls[0].read_text()
    assert "DRY-RUN" in contenu and "essai" in contenu and "prospect@exemple-inexistant.re" in contenu


def test_smtp_zero_socket_en_dry_run(_local_sans_drapeau, monkeypatch):
    """send_email (SMTP) : smtp_host configuré mais dry-run → aucune socket SMTP, .eml écrit."""
    import smtplib

    def _interdit(*a, **k):  # noqa: ANN001
        raise AssertionError("OUVERTURE SMTP en dry-run — la garde a fui !")

    monkeypatch.setattr(smtplib, "SMTP", _interdit)

    res = mail.send_email("client@exemple-inexistant.re", "Sujet test", "Corps du mail.")
    assert res.ok is False
    assert res.detail == "dry-run"
    emls = list(_local_sans_drapeau.glob("*.eml"))
    assert len(emls) == 1
    brut = emls[0].read_text()
    assert "Sujet test" in brut and "client@exemple-inexistant.re" in brut
