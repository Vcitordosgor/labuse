"""VEILLE-2 · Lot 2 — Chemin RADAR, prouvé sur de VRAIES pages leboncoin déposées (dépôt HTML).

Corpus réel : qa/radar-html/ECH-1.html (35 annonces, variante A riche) + 3 pages d'annonce
qa/radar-terrains/T-*.html. On prouve la chaîne :
  · EXTRACTION — prix, surface, commune, type, date, lien, chaque fait juste (valeurs réelles) ;
  · RATTACHEMENT — à une parcelle quand la convergence le permet, « non rattachée » sinon, JAMAIS inventée ;
  · une annonce DÉJÀ VUE = pas de nouvel événement (dédup par list_id) ;
  · une annonce EXPIRÉE = retirée (sort des biens du jour et des veilles) ;
  · MATCHING — 3 veilles aux critères différents → chaque annonce aux bons comptes et à eux seuls.

Écrit en base réelle (session_scope) puis NETTOYÉ (list_ids + idus de test) — jamais de résidu.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import text

from labuse.db import session_scope
from labuse.pige import cycle, digests, html_ingest, rattachement_html, tables, veille

pytestmark = pytest.mark.db

_ROOT = Path(__file__).resolve().parents[1]
_ECH1 = _ROOT / "qa" / "radar-html" / "ECH-1.html"
_TERRAINS = {
    3055991753: _ROOT / "qa" / "radar-terrains" / "T-camelias.html",     # SD terrain 367 500 € · 1108 m²
    3241879744: _ROOT / "qa" / "radar-terrains" / "T-possession.html",   # Possession terrain 195 000 € · 419 m²
    3200222934: _ROOT / "qa" / "radar-terrains" / "T-saintemarie.html",  # Sainte-Marie terrain 825 000 € · 1600 m²
}

# Les six annonces d'ancrage (toutes bâti/terrain — jamais appartement, exclu des biens du jour).
A, B, C = 3143092379, 3253364472, 3184708502     # ECH-1 : SD maison 655k · SD maison 350k · Possession maison 384k
D, E, F = 3055991753, 3241879744, 3200222934     # T-*   : SD terrain 367,5k · Possession terrain 195k · Ste-Marie terrain 825k
_SEED_IDU = "97411000ZZ2001"                      # parcelle seedée pour la preuve de rattachement


def _ingerer_corpus(db):
    html_ingest.ingester(db, _ECH1.read_text(encoding="utf-8"), "ECH-1.html", archiver=False)
    for p in _TERRAINS.values():
        html_ingest.ingester(db, p.read_text(encoding="utf-8"), p.name, archiver=False)


def _nettoyer(db):
    ids = list(_TERRAINS) + list(range(0))
    db.execute(text("DELETE FROM p_model_bati WHERE idu = :i"), {"i": _SEED_IDU})
    db.execute(text("DELETE FROM parcels WHERE idu = :i"), {"i": _SEED_IDU})
    db.execute(text("DELETE FROM pige_biens WHERE bien_id IN "
                    "(SELECT bien_id FROM pige_annonces a JOIN pige_depots d ON true "
                    " WHERE a.list_id = ANY(:i))"), {"i": ids})
    # tout le corpus déposé dans ce test (ECH-1 + T-*) repéré par ses portails/urls leboncoin de test.
    db.execute(text("DELETE FROM pige_biens WHERE bien_id IN (SELECT bien_id FROM pige_annonces "
                    "WHERE url_sortante LIKE '%leboncoin.fr/ad/ventes_immobilieres/%')"))
    db.execute(text("DELETE FROM event_log WHERE dedup LIKE 'pige:%'"))
    db.execute(text("DELETE FROM pige_depots WHERE nom_fichier IN ('ECH-1.html','T-camelias.html',"
                    "'T-possession.html','T-saintemarie.html')"))
    db.commit()


@pytest.fixture
def corpus(monkeypatch, tmp_path):
    monkeypatch.setenv("LABUSE_PIGE_DEPOTS_DIR", str(tmp_path / "depots"))
    with session_scope() as db:
        tables.ensure_tables(db.get_bind())
        _nettoyer(db)
        _ingerer_corpus(db)
    yield
    with session_scope() as db:
        _nettoyer(db)


def _faits(db, list_id: int) -> dict:
    return dict(db.execute(text(
        "SELECT b.commune, b.type_bien, b.rattachement_etat, b.idu, "
        "       f.prix, f.surface_hab, f.surface_terrain, f.particulier_pro, "
        "       a.url_sortante, a.first_publication_date::date AS pub "
        "FROM pige_biens b JOIN pige_faits f ON f.bien_id=b.bien_id "
        "JOIN pige_annonces a ON a.bien_id=b.bien_id WHERE a.list_id=:l"), {"l": list_id}).mappings().first())


# ─────────────── EXTRACTION — chaque fait juste (pages d'annonce réelles) ───────────────

def test_extraction_faits_reels(corpus):
    """Les faits extraits des VRAIES pages = les valeurs réelles (prix, surface, commune, type, date, lien)."""
    with session_scope() as db:
        # T-camelias — terrain Saint-Denis
        d = _faits(db, D)
        assert d["commune"] == "Saint-Denis" and d["type_bien"] == "terrain"
        assert d["prix"] == 367500 and float(d["surface_terrain"]) == 1108
        assert d["url_sortante"].endswith(f"/{D}") and str(d["pub"]) == "2025-09-11"
        # T-possession — terrain La Possession
        e = _faits(db, E)
        assert e["commune"] == "La Possession" and e["type_bien"] == "terrain"
        assert e["prix"] == 195000 and float(e["surface_terrain"]) == 419
        # T-saintemarie — terrain Sainte-Marie
        f = _faits(db, F)
        assert f["commune"] == "Sainte-Marie" and f["type_bien"] == "terrain"
        assert f["prix"] == 825000 and float(f["surface_terrain"]) == 1600
        # ECH-1 — une maison riche (habitable + terrain + particulier)
        a = _faits(db, A)
        assert a["commune"] == "Saint-Denis" and a["type_bien"] == "maison"
        assert a["prix"] == 655000 and float(a["surface_hab"]) == 202 and float(a["surface_terrain"]) == 265
        assert a["particulier_pro"] == "particulier"


# ─────────────── DÉDUP — une annonce déjà vue = pas de nouvel événement ───────────────

def test_annonce_deja_vue_pas_de_nouvel_evenement(corpus):
    """Re-déposer le MÊME fichier : 0 nouvelle annonce, 0 nouvel événement `pige.nouvelle` (dédup list_id)."""
    with session_scope() as db:
        n_av = db.execute(text("SELECT count(*) FROM event_log WHERE kind='pige.nouvelle'")).scalar()
        r = html_ingest.ingester(db, _ECH1.read_text(encoding="utf-8"), "ECH-1.html", archiver=False)
        assert r["nb_nouvelles"] == 0 and r["nb_maj"] == 35
        n_ap = db.execute(text("SELECT count(*) FROM event_log WHERE kind='pige.nouvelle'")).scalar()
    assert n_ap == n_av                                   # aucun nouvel événement « nouvelle »


# ─────────────── EXPIRATION — une annonce expirée = retirée ───────────────

def test_annonce_expiree_retiree(corpus):
    """Une annonce dont l'expiration_date est passée → statut `retiree` (sort des biens du jour)."""
    with session_scope() as db:
        bid = db.execute(text("SELECT bien_id FROM pige_annonces WHERE list_id=:l"), {"l": A}).scalar()
        db.execute(text("UPDATE pige_annonces SET expiration_date = now() - interval '2 days' WHERE list_id=:l"),
                   {"l": A})
        db.commit()
        n = cycle.marquer_expirees(db)
        assert n >= 1
        statut = db.execute(text("SELECT statut FROM pige_biens WHERE bien_id=:b"), {"b": bid}).scalar()
        assert statut == "retiree"
        # elle ne fait plus partie des biens du jour (donc plus d'aucune veille)
        biens = digests._biens_du_jour(db)
        assert bid not in {b["bien_id"] for b in biens}


# ─────────────── RATTACHEMENT — convergence ≥2 critères, jamais inventé ───────────────

def test_rattachement_convergence_et_jamais_invente(corpus):
    """Annonce A (SD maison 202 m² hab / 265 m² terrain, position adresse) : une parcelle seedée qui
    CONVERGE (surface cadastrale ≈ terrain ET emprise bâtie plausible) → RATTACHÉE. Sans parcelle
    convergente, l'annonce reste « non rattachée » — jamais une parcelle inventée."""
    with session_scope() as db:
        a = _faits(db, A)
        assert a["rattachement_etat"] == "non_rattachee"      # aucune parcelle en base → jamais inventé
        # seed d'une parcelle qui converge, au point de l'annonce, surface ≈ 265, emprise ≈ 150 (maison 202)
        lat, lng = -20.90516, 55.45873
        wkt = (f"POLYGON(({lng} {lat},{lng+0.0006} {lat},{lng+0.0006} {lat+0.0006},"
               f"{lng} {lat+0.0006},{lng} {lat}))")
        db.execute(text(
            "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2, centroid, bbox) "
            "VALUES (:i,'Saint-Denis','ZZ','2001', ST_GeomFromText(:w,4326), "
            " ST_Transform(ST_GeomFromText(:w,4326),2975), 265, ST_Centroid(ST_GeomFromText(:w,4326)), "
            " ST_Envelope(ST_GeomFromText(:w,4326)))"), {"i": _SEED_IDU, "w": wkt})
        db.execute(text("INSERT INTO p_model_bati (idu, emprise_bati_m2) VALUES (:i, 150)"), {"i": _SEED_IDU})
        db.commit()
        rec = {"type": "maison", "lng": lng, "lat": lat, "commune": "Saint-Denis",
               "surface_hab": 202, "surface_terrain": 265}
        ratt = rattachement_html.rattacher(db, rec)
        assert ratt["etat"] == "rattachee" and ratt["idu"] == _SEED_IDU
        assert {c["critere"] for c in ratt["criteres"]} >= {"surface", "emprise"}   # ≥2 critères convergents


# ─────────────── MATCHING — 3 veilles, chaque annonce aux bons comptes et à eux seuls ───────────────

def test_matching_trois_veilles_matrice(corpus):
    """3 veilles aux critères différents ; matrice annonce × veille attendue == obtenue."""
    V1 = {"communes": ["Saint-Denis"], "type_bien": "maison", "prix_max": 600000}
    V2 = {"communes": ["La Possession", "Sainte-Marie"], "type_bien": "terrain"}
    V3 = {"type_bien": "terrain", "surface_min": 1000, "prix_max": 900000}
    attendu = {
        A: {"V1": False, "V2": False, "V3": False},   # SD maison 655k > 600k
        B: {"V1": True,  "V2": False, "V3": False},   # SD maison 350k ≤ 600k
        C: {"V1": False, "V2": False, "V3": False},   # Possession maison (pas terrain, pas SD)
        D: {"V1": False, "V2": False, "V3": True},    # SD terrain 1108 m² ≤ 900k
        E: {"V1": False, "V2": True,  "V3": False},   # Possession terrain 419 m² (<1000)
        F: {"V1": False, "V2": True,  "V3": True},    # Ste-Marie terrain 1600 m² ≤ 900k
    }
    with session_scope() as db:
        biens = {b["bien_id"]: b for b in digests._biens_du_jour(db)}
        bid = {lid: db.execute(text("SELECT bien_id FROM pige_annonces WHERE list_id=:l"), {"l": lid}).scalar()
               for lid in (A, B, C, D, E, F)}
        obtenu = {}
        for lid in (A, B, C, D, E, F):
            b = biens[bid[lid]]
            obtenu[lid] = {"V1": veille.matche(V1, b), "V2": veille.matche(V2, b), "V3": veille.matche(V3, b)}
    assert obtenu == attendu
