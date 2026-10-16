"""RECETTE-GENERALE-1 A-06 — les 3 anomalies du Copilote.

A-06-1 (parcelle introuvable propre) : un IDU BIEN FORMÉ mais INEXISTANT ne doit jamais remonter en
       « incident serveur » — les outils rendent un refus « parcelle introuvable ».
A-06-2 (règles PLU calibrées lues) : le Copilote RESTITUE hauteur/emprise/reculs d'une zone calibrée.
A-06-3 (oui/non PPR) : une question PPR reçoit une réponse OUI/NON sur le PPR, pas une esquive.

La partie DÉTERMINISTE (détecteurs, catalogue, mapping du refus) tourne sans clé IA ni base. Les outils
qui lisent la base sont marqués `db` (fixture base de test ; skip propre si la parcelle témoin manque).
"""
from __future__ import annotations

import pytest

from labuse.copilote_v2 import answering, outils


# ───────────────────────── déterministe (ni IA ni base) ─────────────────────────
def test_detecteur_question_ppr():
    assert answering._est_question_ppr("Cette parcelle est-elle en zone rouge PPR ?")
    assert answering._est_question_ppr("y a-t-il un risque PPR sur cette parcelle ?")
    assert answering._est_question_ppr("elle est en zone bleue ?")
    # une demande de NOTION (pas un statut) ne doit PAS être happée (voie explication/web)
    assert not answering._est_question_ppr("c'est quoi un PPR ?")
    assert not answering._est_question_ppr("explique-moi le plan de prévention des risques")
    # pas de mot PPR du tout
    assert not answering._est_question_ppr("quelle est la surface de cette parcelle ?")


def test_detecteur_question_regle_plu():
    assert answering._est_question_regle_plu("Quelle hauteur maximale en zone Ua à Saint-Denis ?")
    assert answering._est_question_regle_plu("emprise au sol autorisée en zone U2 ?")
    assert answering._est_question_regle_plu("quel recul par rapport à la voirie ?")
    assert answering._est_question_regle_plu("combien de mètres de hauteur max ?")
    # une question hors règles (compte) ne doit pas matcher
    assert not answering._est_question_regle_plu("combien de parcelles à Saint-Paul ?")


def test_catalogue_et_registre_portent_les_deux_outils():
    """Les 2 nouveaux outils sont dans le registre exécutable ET dans le catalogue montré au sélecteur."""
    assert "regles_plu_zone" in outils.OUTILS
    assert "statut_ppr" in outils.OUTILS
    noms = {t["nom"] for t in answering.CATALOGUE}
    assert "regles_plu_zone" in noms
    assert "statut_ppr" in noms
    # coercition des args câblée (sinon le sélecteur ne pourrait pas les appeler)
    assert "regles_plu_zone" in answering._ARG_SPEC
    assert "statut_ppr" in answering._ARG_SPEC


# ───────────────────────── base de test (lecture seule) ─────────────────────────
pytestmark_db = pytest.mark.db


@pytest.fixture(scope="module")
def db():
    from labuse.db import session_factory
    s = session_factory()()
    try:
        yield s
    finally:
        s.close()


def _un_idu(db, commune: str) -> str | None:
    from sqlalchemy import text
    return db.execute(text("SELECT idu FROM parcels WHERE commune = :c LIMIT 1"),
                      {"c": commune}).scalar()


@pytest.mark.db
def test_a06_1_idu_inexistant_refus_propre(db):
    """A-06-1 — un IDU bien formé mais inexistant → refus « introuvable », JAMAIS une exception."""
    idu = "00000000ZZ9999"
    r = outils.fiche_parcelle(db, idu=idu)
    assert r.ok is False and "introuvable" in (r.refus or "")
    p = outils.statut_ppr(db, idu=idu)
    assert p.ok is False and "introuvable" in (p.refus or "")
    g = outils.regles_plu_zone(db, idu=idu)
    assert g.ok is False and "introuvable" in (g.refus or "")
    # destination_zone utilisait `text` non importé → NameError remontait comme incident serveur
    d = outils.destination_zone(db, idu=idu, activite="restaurant")
    assert d.ok is False and "introuvable" in (d.refus or "")


@pytest.mark.db
def test_a06_2_regles_plu_calibrees_restituees(db):
    """A-06-2 — zone calibrée : hauteur/emprise/reculs servis avec leurs citations article/page."""
    r = outils.regles_plu_zone(db, commune="Saint-Denis", zone="Ua")
    if not r.ok or not r.data.get("calibree"):
        pytest.skip("zone Ua de Saint-Denis non calibrée sur cette base")
    reg = r.data["regles"]
    # au moins hauteur + emprise + un recul sont renseignés et chiffrés
    assert reg.get("hauteur_m") is not None
    assert reg.get("emprise_sol_pct") is not None
    assert reg.get("recul_voirie_m") is not None or reg.get("recul_limites_m") is not None
    # les citations existent (article/page) — la restitution est sourcée
    cit = r.data.get("citations") or {}
    assert cit.get("hauteur")
    assert "Saint-Denis" in r.source and "Ua" in r.source


@pytest.mark.db
def test_a06_2_regle_absente_dite_non_renseignee(db):
    """A-06-2 — honnêteté : une zone sans règle calibrée le DIT (« non renseignée »), jamais un faux."""
    idu = _un_idu(db, "Saint-Denis")
    if not idu:
        pytest.skip("aucune parcelle Saint-Denis sur cette base")
    r = outils.regles_plu_zone(db, idu=idu)
    assert r.ok  # on a toujours une réponse (règle ou « non renseignée »), jamais une exception
    reg = r.data["regles"]
    # chaque champ est soit chiffré, soit explicitement « non renseignée »
    assert reg["hauteur_texte"] and reg["emprise_texte"]


@pytest.mark.db
def test_a06_3_ppr_oui_non(db):
    """A-06-3 — PPR : oui (rouge/bleue) ou non (hors), lu de la couche de risque servie."""
    from sqlalchemy import text
    from labuse import runs
    from labuse.api.app import _q_v2_fiche
    # une parcelle en PPR rouge et une hors PPR, prises dans la base
    rouge = non = None
    for idu in db.execute(text("SELECT idu FROM parcels WHERE commune = 'Saint-Denis' LIMIT 60"))\
            .scalars().all():
        try:
            f = _q_v2_fiche(db, idu, run_label=runs.current())
        except Exception:
            continue
        liste = ((f.get("aleas") or {}).get("liste")) or []
        a_rouge = any("zone rouge" in (a.get("nature") or "").lower() for a in liste)
        a_ppr = any("PPR" in (a.get("nature") or "") for a in liste)
        if a_rouge and rouge is None:
            rouge = idu
        if not a_ppr and non is None:
            non = idu
        if rouge and non:
            break
    if not rouge or not non:
        pytest.skip("pas de couple PPR rouge / hors-PPR trouvé sur cette base")
    pr = outils.statut_ppr(db, idu=rouge)
    assert pr.ok and pr.valeur == "oui" and pr.data["statut_ppr"] == "rouge"
    pn = outils.statut_ppr(db, idu=non)
    assert pn.ok and pn.valeur == "non" and pn.data["statut_ppr"] == "hors"
    assert "PAS" in pn.data["libelle"] or "non" in pn.data["libelle"].lower()
