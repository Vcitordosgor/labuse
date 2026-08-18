"""M120 — le flux Projet : IDENTITÉ (infos) + CADRAGE (jeu de filtres) + SHORTLIST FIGÉE.

Tests DB DÉTERMINISTES : `_search_items` est monkeypatché → aucune dépendance aux données de
scoring (on contrôle exactement ce que le run « trouve »). Ils prouvent la doctrine M120 :
un critère = un seul endroit · budget/type/date INFORMATIFS (jamais dans le cadrage) · shortlist
FIGÉE et datée au cadrage · un rejeu EXPLICITE qui conserve les tris et DIT le diff · migration
non destructive de l'ancien format.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse import models
from labuse.api import projets

_WKT = "POLYGON((55.45 -20.9,55.451 -20.9,55.451 -20.901,55.45 -20.901,55.45 -20.9))"


def _parcelle(s, idu):
    return s.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2, centroid, bbox) VALUES "
        "(:i,'X','ZZ','1', ST_GeomFromText(:w,4326), ST_Transform(ST_GeomFromText(:w,4326),2975), 800, "
        " ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326))) RETURNING id"),
        {"i": idu, "w": _WKT}).scalar()


def _fake_search(idus):
    return lambda db, cadrage, limit, overrides=None: [{"idu": i} for i in idus]


# ───────────────────────── un critère = un seul endroit ─────────────────────────
@pytest.mark.db
def test_cadrage_est_le_point_unique_identite_informative(db_session, monkeypatch):
    s = db_session
    _parcelle(s, "97120000AA0001")
    monkeypatch.setattr(projets, "_search_items", _fake_search(["97120000AA0001"]))
    r = projets.projet_create(projets.ProjetIn(
        cadrage={"communes": ["X"], "surfaceMin": 500, "flagsExclus": ["risques"]},
        identite={"budget_eur": 300000, "type_logement": "social", "date_livraison": "2027-01"},
        nom="P"), None, s)
    p = s.get(models.Projet, r["projet"]["id"])
    # le CADRAGE ne contient QUE des facettes — budget/type/date n'y sont JAMAIS (informatifs)
    assert not ({"budget_eur", "type_logement", "date_livraison"} & set(p.filtres))
    assert p.filtres["communes"] == ["X"] and p.filtres["surfaceMin"] == 500
    # l'identité porte les infos, telles quelles
    assert p.identite == {"budget_eur": 300000, "type_logement": "social", "date_livraison": "2027-01"}


# ───────────────────────── la shortlist est figée et datée ─────────────────────────
@pytest.mark.db
def test_create_fige_et_date_la_shortlist(db_session, monkeypatch):
    s = db_session
    for i in range(3):
        _parcelle(s, f"97120000CC00{i:02d}")
    monkeypatch.setattr(projets, "_search_items", _fake_search([f"97120000CC00{i:02d}" for i in range(3)]))
    r = projets.projet_create(projets.ProjetIn(cadrage={"communes": ["X"]}, nom="Figé"), None, s)
    pid = r["projet"]["id"]
    p = s.get(models.Projet, pid)
    n = s.execute(text("SELECT count(*) FROM projet_parcelles WHERE projet_id=:p AND statut='proposee'"),
                  {"p": pid}).scalar()
    assert n == 3
    assert p.derniere_execution_at is not None      # datée (« cadrage du … »)
    assert p.shortlist_perimee is False             # à jour
    assert r["shortlist"]["n_shortlist"] == 3


# ───────────────────────── modifier le cadrage périme (jamais un run muet) ─────────────────────────
@pytest.mark.db
def test_patch_cadrage_perime_patch_identite_non(db_session, monkeypatch):
    s = db_session
    monkeypatch.setattr(projets, "_search_items", _fake_search([]))
    pid = projets.projet_create(projets.ProjetIn(cadrage={"communes": ["X"]}, nom="Patch"), None, s)["projet"]["id"]
    # patch IDENTITÉ (infos) → la shortlist n'est PAS périmée
    projets.projet_patch(pid, projets.ProjetPatchIn(identite={"budget_eur": 1}), None, s)
    assert s.get(models.Projet, pid).shortlist_perimee is False
    # patch CADRAGE changé → périmée (le front proposera un rejeu ; jamais un run automatique)
    projets.projet_patch(pid, projets.ProjetPatchIn(cadrage={"communes": ["Y"]}), None, s)
    assert s.get(models.Projet, pid).shortlist_perimee is True


# ───────────────────────── rejeu explicite : tris conservés + diff dit ─────────────────────────
@pytest.mark.db
def test_rejeu_conserve_les_tris_et_dit_le_diff(db_session, monkeypatch):
    s = db_session
    _parcelle(s, "97120000BB0001")   # retenue qui RESTE dans le cadrage
    _parcelle(s, "97120000BB0002")   # retenue qui SORT du cadrage → reste, dite hors_criteres
    _parcelle(s, "97120000BB0003")   # NOUVELLE entrée au rejeu
    monkeypatch.setattr(projets, "_search_items", _fake_search(["97120000BB0001"]))
    pid = projets.projet_create(projets.ProjetIn(cadrage={"communes": ["X"]}, nom="Rejeu"), None, s)["projet"]["id"]
    projets.projet_parcelle_statut(pid, "97120000BB0001", projets.StatutIn(statut="retenue"), None, s)
    projets.projet_parcelle_statut(pid, "97120000BB0002", projets.StatutIn(statut="retenue"), None, s)
    # rejeu : le cadrage matche désormais pin + pnew (pout sort)
    monkeypatch.setattr(projets, "_search_items", _fake_search(["97120000BB0001", "97120000BB0003"]))
    rr = projets.projet_rejouer(pid, None, s)
    rows = {r.idu: (r.statut, r.hors_criteres) for r in s.execute(text(
        "SELECT par.idu, pp.statut, pp.hors_criteres FROM projet_parcelles pp "
        "JOIN parcels par ON par.id=pp.parcel_id WHERE pp.projet_id=:p"), {"p": pid})}
    # les décisions SURVIVENT au rejeu (aucune retenue évincée)
    assert rows["97120000BB0001"][0] == "retenue" and rows["97120000BB0002"][0] == "retenue"
    # pout sortie du cadrage → DITE (hors_criteres) ; pin rematche → non
    assert rows["97120000BB0002"][1] is True and rows["97120000BB0001"][1] is False
    # pnew entre en proposée
    assert rows["97120000BB0003"][0] == "proposee"
    # le diff DIT ce qui change
    assert rr["shortlist"]["ajoutees"] >= 1 and rr["shortlist"]["tris_conserves"] == 2


# ───────── Phase 4 — le « pourquoi » court : signaux sourcés, jamais un score interne nu ─────────
def test_pourquoi_court_signaux_sources_et_borne():
    # aucun signal → aucune ligne (la carte renverra à la fiche, jamais une ligne inventée)
    assert projets._pourquoi_court("chaude", carencee=False, evenement=False, surface=600) == []
    # événement rouge + carence SRU → deux lignes sourcées, dans l'ordre
    r = projets._pourquoi_court("brulante", carencee=True, evenement=True, surface=3000)
    assert len(r) == 2 and "événement" in r[0].lower() and "carenc" in r[1].lower()
    # grande emprise seule → une ligne, jamais plus de 2
    g = projets._pourquoi_court(None, carencee=False, evenement=False, surface=5000)
    assert g == ["Grande emprise (5 000 m²)."]
    # le tier n'est JAMAIS répété dans le pourquoi (c'est le badge) ; aucune mention « qualité »
    assert not any("qualit" in l.lower() for l in projets._pourquoi_court("chaude", True, True, 9000))


# ───────────────────────── nettoyage du cadrage : jamais un critère inventé ─────────────────────────
def test_clean_cadrage_drop_inconnu_et_vide():
    c = projets.clean_cadrage({"communes": ["X"], "surfaceMin": 500, "evenement": False,
                               "veille": True, "flags": [], "zzz_inconnu": 1, "scoreMin": None})
    # False (toggle éteint), [] (liste vide), None, clé inconnue : tous écartés
    assert c == {"communes": ["X"], "surfaceMin": 500, "veille": True}


# ───────────────────────── migration non destructive de l'ancien format ─────────────────────────
@pytest.mark.db
def test_migration_fiche_vers_cadrage(db_session):
    s = db_session
    p = models.Projet(nom="Legacy",
                      fiche={"type_programme": "etudiant", "budget_foncier_eur": 250000},
                      filtres={"communes": ["Saint-Leu"], "sdpMin": 700}, identite={})
    s.add(p); s.flush()
    projets._migrer_fiche_vers_cadrage(s)
    s.refresh(p)
    assert p.identite.get("budget_eur") == 250000        # infos remontées de la fiche legacy
    assert p.identite.get("type_logement") == "etudiant"
    assert p.filtres == {"communes": ["Saint-Leu"], "sdpMin": 700}   # le cadrage ne bouge pas
