"""COPILOTE-2 lot 1 — LE CHEMIN FICHE. Le résumé d'une parcelle se construit DÉTERMINISTIQUEMENT
(sans modèle) des mêmes ids que la fiche + le Dossier ; une question de champ précis répond avec la
ligne déclarée et son id (plus de champ jeté). Ces tests tournent sans clé Anthropic (aucun appel modèle).
"""
from __future__ import annotations

import pytest

from labuse.db import session_factory

IDU = "97410000AN0347"   # Saint-Benoît, propriété communale, zone N, PPR rouge — parcelle témoin de l'audit


@pytest.fixture(scope="module")
def db():
    s = session_factory()()
    try:
        yield s
    finally:
        s.close()


def _present(db, idu):
    from labuse.copilote_v2 import resume_fiche as RF
    return RF.resume_parcelle(db, idu) is not None


def test_resume_parcelle_deterministe(db):
    """Le résumé porte le bandeau (chiffres servis) et des verdicts de section, sans aucun modèle."""
    from labuse.copilote_v2 import resume_fiche as RF
    r = RF.resume_parcelle(db, IDU)
    if r is None:
        pytest.skip("parcelle témoin absente du run servi sur cette base")
    assert r["commune"]
    # les chiffres du bandeau viennent de la fiche (jamais recalculés) — au moins la surface
    libs = {t["libelle"] for t in r["tuiles"]}
    assert "Surface" in libs
    # des verdicts de section (les mêmes moteurs que le Dossier)
    ids = {s["id"] for s in r["sections"]}
    assert ids & {"urbanisme", "risques", "identite", "marche"}
    # la phrase déterministe est stable (deux appels → même texte)
    assert RF.phrase(r) == RF.phrase(RF.resume_parcelle(db, IDU))


def test_champ_precis_porte_id(db):
    """Une question de champ répond avec la valeur ET l'id du registre (ligne déclarée)."""
    from labuse.copilote_v2 import resume_fiche as RF
    if not _present(db, IDU):
        pytest.skip("parcelle témoin absente")
    prop = RF.champ_precis(db, IDU, "qui est le proprietaire ?")
    assert prop and prop["champ_id"] == "type_proprietaire"
    assert "type_proprietaire" in prop["texte"]
    taxe = RF.champ_precis(db, IDU, "quel est le taux de taxe d'amenagement ?")
    assert taxe and taxe["champ_id"] == "taxe_amenagement_estimee_eur"
    assert "taxe_amenagement_estimee_eur" in taxe["texte"]


def test_champ_inconnu_rend_none(db):
    """Une demande qui ne vise aucun champ connu → None (le chemin FICHE ne s'impose pas)."""
    from labuse.copilote_v2 import resume_fiche as RF
    assert RF.champ_precis(db, IDU, "bonjour ça va ?") is None


def test_dispatch_fiche_sans_modele(db):
    """Le dispatch sert le résumé AVANT le routeur : aucun appel modèle pour « dis-moi tout sur X »
    (le court-circuit déterministe de `answer`). On vérifie que la réponse est le chemin FICHE."""
    from labuse.copilote_v2.answering import answer
    if not _present(db, IDU):
        pytest.skip("parcelle témoin absente")
    rep = answer(db, f"dis-moi tout sur la parcelle {IDU}")
    assert rep.get("tool") == "fiche_parcelle"
    assert rep.get("voie", {}).get("cible") == "fiche"
    assert IDU in rep["text"] and "Surface" in rep["text"]
    # pas de dégradation : le chemin ne touche pas le modèle
    assert not rep.get("degraded")


def test_dispatch_champ_precis_sans_modele(db):
    """Une question de champ précis (propriétaire) court-circuite le routeur et cite l'id."""
    from labuse.copilote_v2.answering import answer
    if not _present(db, IDU):
        pytest.skip("parcelle témoin absente")
    rep = answer(db, f"qui est le proprietaire de la parcelle {IDU} ?")
    assert rep.get("champ_id") == "type_proprietaire"
    assert not rep.get("degraded")


def test_idu_extrait_du_message(db):
    from labuse.copilote_v2.answering import _idu_dans
    assert _idu_dans(f"dis-moi tout sur {IDU} stp") == IDU
    assert _idu_dans("aucun idu ici") is None
