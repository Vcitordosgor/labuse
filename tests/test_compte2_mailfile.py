"""COMPTE-2 · Lot 2 — la file d'attente `mail_queue` et le point d'envoi unique.

On vérifie ce qui rend l'envoi HONNÊTE : rien n'affiche « reçu » si rien n'est parti (RV-013), un
double-clic ne double pas l'envoi, un échec est rejouable, un programmé s'annule sans disparaître,
et chaque transition laisse une ligne de journal avec QUI l'a demandé.
"""
from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import text

from labuse import mailfile
from labuse.mailfile import _now

pytestmark = pytest.mark.db


@pytest.fixture()
def eng(engine):
    mailfile.ensure_tables(engine)
    with engine.begin() as c:
        c.execute(text("DELETE FROM mail_queue"))
        c.execute(text("DELETE FROM evenements_compte WHERE type LIKE 'mail_%'"))
    return engine


# params COMPLETS par clé (la garde fail-closed refuse un template incomplet — cf. test dédié).
_FULL = {
    "onboarding1":    {"PRENOM": "Vic", "EMAIL": "a@labuse.test", "MDP_PROVISOIRE": "x"},
    "onboarding2":    {"PRENOM": "Vic"},
    "onboarding3":    {"PRENOM": "Vic"},
    "suspension":     {"PRENOM": "Vic", "LIEN_PAIEMENT": "https://x"},
    "retablissement": {"PRENOM": "Vic"},
}


def _p(key):
    return dict(_FULL[key])


def _ok(*a, **k):
    return {"envoye": True, "message_id": "<brevo-123@labuse>"}


def _ko(raison="Brevo a refusé l'envoi (HTTP 400)."):
    def _f(*a, **k):
        return {"envoye": False, "raison": raison}
    return _f


def test_envoi_immediat_recu_avec_message_id(eng, monkeypatch):
    monkeypatch.setattr("labuse.brevo.envoyer_template", _ok)
    r = mailfile.envoyer_mail(eng, key="onboarding1", to="a@labuse.test",
                              params=_p("onboarding1"), compte_id=1, demandeur="vic")
    assert r["etat"] == "recu"
    assert r["message_id"] == "<brevo-123@labuse>"
    assert r["parti_at"] is not None            # daté SEULEMENT parce que c'est parti
    assert r["template_id"] == 6 and r["template_nom"] == "LABUSE-1-BIENVENUE"


def test_dry_run_clef_absente_non_date(eng, monkeypatch):
    # clé Brevo absente → le transport dit « aucun envoi », l'entrée n'est PAS datée (RV-013).
    monkeypatch.setattr("labuse.brevo.envoyer_template",
                        _ko("Brevo non configuré (BREVO_API_KEY absente) — aucun envoi."))
    r = mailfile.envoyer_mail(eng, key="onboarding1", to="a@labuse.test",
                              params=_p("onboarding1"), compte_id=1, demandeur="vic")
    assert r["etat"] == "en_attente"            # une tentative ratée ≠ échec définitif ≠ envoyé
    assert r["parti_at"] is None
    assert "absente" in (r["erreur"] or "")


def test_echec_brevo_trois_tentatives_puis_echec(eng, monkeypatch):
    monkeypatch.setattr("labuse.brevo.envoyer_template", _ko("Brevo a refusé l'envoi (HTTP 401)."))
    r = mailfile.envoyer_mail(eng, key="suspension", to="a@labuse.test",
                              params=_p("suspension"), compte_id=2, demandeur="vic")
    assert r["etat"] == "en_attente" and r["tentatives"] == 1
    r = mailfile.rejouer(eng, r["id"], demandeur="vic")   # rejouer remet à zéro puis retente
    # après le rejeu on est reparti d'une tentative ; refaisons monter jusqu'à l'échec définitif
    mid = r["id"]
    for _ in range(mailfile.TENTATIVES_MAX):
        r = mailfile._tenter_depart(eng, mid)
    assert r["etat"] == "echec"
    assert "401" in r["erreur"] and r["parti_at"] is None


def test_anti_doublon_double_clic(eng, monkeypatch):
    monkeypatch.setattr("labuse.brevo.envoyer_template", _ok)
    a = mailfile.envoyer_mail(eng, key="onboarding1", to="a@labuse.test",
                              params=_p("onboarding1"), compte_id=3, demandeur="vic")
    b = mailfile.envoyer_mail(eng, key="onboarding1", to="a@labuse.test",
                              params=_p("onboarding1"), compte_id=3, demandeur="vic")
    assert b.get("doublon") is True and b["id"] == a["id"]
    with eng.begin() as c:
        n = c.execute(text("SELECT count(*) FROM mail_queue WHERE compte_id = 3")).scalar()
    assert n == 1                               # un seul mail malgré le double-clic


def test_rejouer_un_echec(eng, monkeypatch):
    monkeypatch.setattr("labuse.brevo.envoyer_template", _ko("Brevo injoignable (ConnectError)."))
    r = mailfile.envoyer_mail(eng, key="onboarding2", to="a@labuse.test",
                              params=_p("onboarding2"), compte_id=4, demandeur="vic")
    for _ in range(mailfile.TENTATIVES_MAX):
        r = mailfile._tenter_depart(eng, r["id"])
    assert r["etat"] == "echec"
    monkeypatch.setattr("labuse.brevo.envoyer_template", _ok)   # Brevo revient
    r2 = mailfile.rejouer(eng, r["id"], demandeur="vic")
    assert r2["etat"] == "recu" and r2["message_id"]


def test_programme_en_attente_puis_annule(eng, monkeypatch):
    monkeypatch.setattr("labuse.brevo.envoyer_template", _ok)
    prevu = _now() + timedelta(days=3)
    r = mailfile.envoyer_mail(eng, key="onboarding2", to="a@labuse.test", compte_id=5,
                              params=_p("onboarding2"), demandeur="job:onboarding", prevu_at=prevu)
    assert r["etat"] == "en_attente" and r["parti_at"] is None   # programmé : pas encore parti
    a = mailfile.annuler(eng, r["id"], demandeur="vic")
    assert a["etat"] == "annule"
    # annulé ≠ supprimé : la ligne existe toujours (l'historique est la preuve)
    with eng.begin() as c:
        assert c.execute(text("SELECT etat FROM mail_queue WHERE id = :i"), {"i": r["id"]}).scalar() == "annule"


def test_depart_des_programmes_quand_heure_venue(eng, monkeypatch):
    monkeypatch.setattr("labuse.brevo.envoyer_template", _ok)
    passe = _now() - timedelta(minutes=1)
    mailfile.enfiler(eng, key="onboarding3", to="a@labuse.test", compte_id=6,
                     params=_p("onboarding3"), demandeur="job:onboarding", prevu_at=passe)
    n = mailfile.depart_des_programmes(eng)
    assert n == 1
    rows = mailfile.lister(eng, filtre="partis", compte_id=6)
    assert rows and rows[0]["etat"] == "recu"


def test_journal_nomme_le_demandeur(eng, monkeypatch):
    monkeypatch.setattr("labuse.brevo.envoyer_template", _ok)
    mailfile.envoyer_mail(eng, key="retablissement", to="a@labuse.test",
                          params=_p("retablissement"), compte_id=7, demandeur="vic")
    with eng.begin() as c:
        det = c.execute(text("SELECT detail FROM evenements_compte WHERE type = 'mail_recu'"
                             " AND compte_id = 7 ORDER BY id DESC LIMIT 1")).scalar()
    assert det and det.startswith("[vic]") and "file#" in det


def test_garde_params_manquants_ne_part_jamais(eng, monkeypatch):
    # onboarding1 attend PRENOM/EMAIL/MDP_PROVISOIRE ; on en fournit deux → la file REFUSE de partir
    # (jamais un « {{ params.MDP_PROVISOIRE }} » brut chez le client), sans même appeler le transport.
    appele = {"n": 0}

    def _spy(*a, **k):
        appele["n"] += 1
        return {"envoye": True, "message_id": "x"}
    monkeypatch.setattr("labuse.brevo.envoyer_template", _spy)
    r = mailfile.envoyer_mail(eng, key="onboarding1", to="a@labuse.test",
                              params={"PRENOM": "Vic", "EMAIL": "a@labuse.test"},
                              compte_id=9, demandeur="vic")
    assert appele["n"] == 0                       # transport jamais appelé
    assert r["etat"] == "en_attente" and r["parti_at"] is None
    assert "MDP_PROVISOIRE" in (r["erreur"] or "")


def test_filtres_et_compteurs(eng, monkeypatch):
    monkeypatch.setattr("labuse.brevo.envoyer_template", _ok)
    mailfile.envoyer_mail(eng, key="onboarding1", to="a@labuse.test",
                          params=_p("onboarding1"), compte_id=8, demandeur="vic")
    monkeypatch.setattr("labuse.brevo.envoyer_template", _ko())
    r = mailfile.envoyer_mail(eng, key="onboarding2", to="b@labuse.test",
                              params=_p("onboarding2"), compte_id=8, demandeur="vic")
    for _ in range(mailfile.TENTATIVES_MAX):
        r = mailfile._tenter_depart(eng, r["id"])
    cpt = mailfile.compteurs(eng)
    assert cpt["partis"] >= 1 and cpt["echecs"] >= 1
    assert len(mailfile.lister(eng, filtre="echecs")) >= 1
    assert len(mailfile.lister(eng, filtre="partis")) >= 1
