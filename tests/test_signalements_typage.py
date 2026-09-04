"""RETOURS-11F M11 — signalements typés de bout en bout + R-verif (Vic).

Deux entrées :
 · le « Signaler une erreur » du BAS DE FICHE écrit dans `signalements` (type='fiche') avec l'IDU et la
   section (`champ`) ; l'admin le voit dans Produit avec un lien cliquable, cloisonné au compte émetteur ;
 · le « Signaler » du BANDEAU écrit dans `retours` (bug/idée/question/donnée) ; un retour « donnée » venu
   de la fiche porte l'IDU + la section et un lien cliquable vers la fiche.

R-verif : compte A signale, l'admin (Produit) le voit avec le BON type + BON compte + lien ; le compte B
ne le voit PAS via sa file cliente (cloison). On écrit via `session_scope` (commit réel, comme l'app) car
l'admin ouvre une connexion séparée ; les lignes de test sont nettoyées en fin de test.
"""
from __future__ import annotations

import types

import pytest
from sqlalchemy import text

from labuse.api import app as appmod
from labuse.api import auth, dashboard
from labuse.db import session_scope

pytestmark = pytest.mark.db


def _req(compte_id=None):
    return types.SimpleNamespace(state=types.SimpleNamespace(compte_id=compte_id))


def _deux_comptes(engine):
    from labuse.comptes import ensure_tables as comptes_ens
    with session_scope() as s:
        comptes_ens(s)
    with engine.begin() as c:
        a = c.execute(text("INSERT INTO comptes (nom, plan, statut) VALUES ('Agence A','integral','actif') RETURNING id")).scalar()
        b = c.execute(text("INSERT INTO comptes (nom, plan, statut) VALUES ('Agence B','integral','actif') RETURNING id")).scalar()
    return a, b


def test_signalement_fiche_typé_cloisonné_et_lien(engine, monkeypatch):
    a, b = _deux_comptes(engine)
    idu = "97415000CR0811"
    body = appmod.SignalementIn(idu=idu, type_erreur="zonage", champ="Urbanisme",
                                commentaire="la zone affichée semble fausse")
    with session_scope() as s:
        out = appmod.creer_signalement(body, _req(a), s)   # commit à la sortie du scope
    sid = out["id"]
    try:
        assert out["ok"] and out["statut"] == "nouveau"
        # A voit son signalement, B ne le voit PAS (cloison cliente).
        with session_scope() as s:
            vus_a = appmod.liste_signalements(_req(a), limit=500, db=s)
            vus_b = appmod.liste_signalements(_req(b), limit=500, db=s)
        assert any(x["id"] == sid for x in vus_a)
        assert all(x["id"] != sid for x in vus_b)
        # L'admin (Produit) le voit : BON type, BON compte, section (`champ`), LIEN cliquable.
        monkeypatch.setattr(auth, "exiger_admin", lambda req: None)
        adm = dashboard.admin_signalements(_req(a))
        ligne = next(x for x in adm["signalements"] if x["id"] == sid)
        assert ligne["type"] == "fiche" and ligne["type_erreur"] == "zonage"
        assert ligne["champ"] == "Urbanisme" and ligne["parcelle_id"] == idu
        assert ligne["compte_nom"] == "Agence A"
        assert ligne["fiche_lien"] == f"#idu={idu}"
    finally:
        with engine.begin() as c:
            c.execute(text("DELETE FROM signalements WHERE id=:i"), {"i": sid})
            c.execute(text("DELETE FROM comptes WHERE id IN (:a,:b)"), {"a": a, "b": b})


def test_retour_donnee_depuis_fiche_porte_idu_section_et_lien(engine, monkeypatch):
    a, _ = _deux_comptes(engine)
    dashboard.ensure_tables(engine)  # retours + colonnes idu/section
    idu = "97415000CR0811"
    out = dashboard.creer_retour(
        dashboard.RetourIn(type="donnee", message="prix de sortie douteux sur cette parcelle",
                           idu=idu, section="Marché"), _req(a))
    rid = out["id"]
    try:
        assert out["ok"]
        monkeypatch.setattr(auth, "exiger_admin", lambda req: None)
        prod = dashboard.admin_produit(_req(a))
        ligne = next(r for r in prod["retours"] if r["id"] == rid)
        assert ligne["type"] == "donnee"
        assert ligne["idu"] == idu and ligne["section"] == "Marché"
        assert ligne["fiche_lien"] == f"#idu={idu}"
    finally:
        with engine.begin() as c:
            c.execute(text("DELETE FROM retours WHERE id=:i"), {"i": rid})
            c.execute(text("DELETE FROM comptes WHERE id = :a"), {"a": a})


def test_retour_type_invalide_refuse():
    import pydantic
    with pytest.raises(pydantic.ValidationError):
        dashboard.RetourIn(type="spam", message="xxxx")
    for t in ("bug", "idee", "question", "donnee"):   # les quatre types valides passent
        dashboard.RetourIn(type=t, message="xxxx")
