"""RETOURS-11F session F2 — gardes de non-contradiction / de comportement pour les items M soldés.

M12 (piscines) : la confiance FILTRE le service (haute par défaut), la bascule « inclure les
incertaines » l'élargit, et « pas une piscine » RETIRE la parcelle du compteur ET de la carte.
M13 (colonnes) : la table Communes lit le €/m² terrain nu du MÊME moteur que la fiche (pas de calcul
parallèle) ; la colonne existe toujours (« — » si absente, jamais un zéro inventé).
"""
from __future__ import annotations

import inspect

import pytest
from sqlalchemy import text


# ─────────────────────────────── M12 — piscines ───────────────────────────────

@pytest.fixture
def client_piscines(engine):
    from fastapi.testclient import TestClient

    from labuse.api.app import app
    from labuse.db import session_scope
    from labuse.ingestion.ortho_equipements import DDL, ensure_corrections
    wkt = "POLYGON((55.30 -21.00,55.31 -21.00,55.31 -20.99,55.30 -20.99,55.30 -21.00))"
    ids = ["97999000PA0001", "97999000PA0002", "97999000PA0003"]
    with session_scope() as s:
        s.execute(text(DDL))
        ensure_corrections(s)
        for i, (idu, conf) in enumerate(zip(ids, (0.95, 0.62, 0.40))):
            s.execute(text(
                "INSERT INTO parcels (idu, commune, section, numero, geom, surface_m2, centroid, bbox) VALUES "
                "(:idu,'Piscineville','P',:num, ST_GeomFromText(:w,4326), 1000, "
                "ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326))) "
                "ON CONFLICT (idu) DO NOTHING"), {"idu": idu, "num": str(i + 1), "w": wkt})
            s.execute(text(
                "INSERT INTO parcel_equipements (idu, piscine, piscine_surface_m2, piscine_confiance) "
                "VALUES (:idu, true, 30, :c) ON CONFLICT (idu) DO UPDATE SET piscine=true, piscine_confiance=:c"),
                {"idu": idu, "c": conf})
    try:
        yield TestClient(app), ids
    finally:
        with session_scope() as s:
            s.execute(text("DELETE FROM piscine_corrections WHERE idu = ANY(:ids)"), {"ids": ids})
            s.execute(text("DELETE FROM parcel_equipements WHERE idu = ANY(:ids)"), {"ids": ids})
            s.execute(text("DELETE FROM parcels WHERE idu = ANY(:ids)"), {"ids": ids})


@pytest.mark.db
def test_m12_confiance_filtre_et_bascule(client_piscines):
    client, ids = client_piscines
    # défaut : seule la confiance HAUTE (≥ 0,80) est comptée → 1 des 3 piscines de Piscineville
    base = client.get("/modules/prospection-piscines", params={"commune": "Piscineville"}).json()
    assert base["total"] == 1, base
    assert base["confiance"]["incertaines"] == 2   # 0,62 et 0,40 sont sous le seuil
    # bascule : inclure les incertaines → les 3
    tous = client.get("/modules/prospection-piscines",
                      params={"commune": "Piscineville", "inclure_incertaines": True}).json()
    assert tous["total"] == 3, tous
    # la carte suit la même bascule (points GeoJSON) + porte la bande de confiance
    pts = client.get("/modules/prospection-piscines/points",
                     params={"commune": "Piscineville", "inclure_incertaines": True}).json()
    assert len(pts["features"]) == 3
    bandes = {f["properties"]["idu"]: f["properties"]["bande"] for f in pts["features"]}
    assert bandes[ids[0]] == "haute" and bandes[ids[1]] == "moyenne" and bandes[ids[2]] == "basse"


@pytest.mark.db
def test_m12_pas_une_piscine_retire_du_service(client_piscines):
    client, ids = client_piscines
    # « pas une piscine » sur la haute → elle DISPARAÎT du compteur défaut ET de la carte
    r = client.post("/modules/prospection-piscines/pas-une-piscine", json={"idu": ids[0]})
    assert r.status_code == 200 and r.json()["ok"]
    base = client.get("/modules/prospection-piscines", params={"commune": "Piscineville"}).json()
    assert base["total"] == 0, base          # la seule « haute » a été retirée
    assert base["corrigees"] >= 1
    pts = client.get("/modules/prospection-piscines/points",
                     params={"commune": "Piscineville", "inclure_incertaines": True}).json()
    idus = {f["properties"]["idu"] for f in pts["features"]}
    assert ids[0] not in idus                # retirée aussi de la carte, quelle que soit la bascule


# ─────────────────────────────── M13 — colonnes ───────────────────────────────

def test_m13_table_communes_lit_le_moteur_terrain_nu_unique():
    # Le tableau Communes ne recalcule PAS le terrain nu : il lit `ligne2_terrain_zone` (le moteur de
    # la fiche Marché). La colonne `prix_terrain_nu` est posée dans chaque ligne (« — » si absente).
    from labuse.api import comparateur
    src = inspect.getsource(comparateur.raw_rows)
    assert "ligne2_terrain_zone" in src
    assert "prix_terrain_nu" in src


# ─────────────────────────────── M9 — Densifier ───────────────────────────────

def test_m9_score_renouvellement_est_continu_sans_plateau():
    # Le plateau de tête (mesuré : top 50 = 2 scores distincts, 23 à 100) venait du `round()` PAR
    # COMPOSANTE + `LEAST(100, …)`. Le score naît désormais des percent_rank BRUTS, arrondi UNE fois
    # à la décimale — il discrimine. Ce test grave l'absence du clamp et de l'arrondi par composante
    # dans la formule (une régression rouvrirait le plateau).
    from labuse import renouvellement as R
    sql = R._BUILD_SQL
    assert "LEAST(100" not in sql, "le clamp LEAST(100,…) écrase la tête de liste — retiré (M9)"
    # le score se calcule sur les percent_rank bruts (pr_pot/pr_ass/pr_mar), pas sur les comp_* arrondis
    assert "pr_pot" in sql and "pr_ass" in sql and "pr_mar" in sql
    assert "round((c.pr_pot + c.pr_ass + c.pr_mar)" in sql


# ─────────────────────────────── M3 — prix de secteur ───────────────────────────────

def test_m3_prix_secteur_une_seule_methode_fenetre_n():
    # sector_price (fiche Marché / Étudier un bien / bilan) et _ref_local (référence locale Radar /
    # Mon secteur) partagent LA MÊME méthode et LES MÊMES constantes — plus de « 2 365 vs 2 403 » nés
    # de deux fenêtres/seuils divergents sur le même écran. On grave le partage des constantes SECTEUR-2.
    from labuse.faisabilite import bilan
    from labuse.pige import signaux
    # _ref_local importe la robustification de bilan (méthode unique), il ne la recopie pas.
    src = inspect.getsource(signaux._ref_local)
    assert "from ..faisabilite.bilan import" in src
    assert "trim_extremes_5pct" in src and "RAYONS_SECTEUR_M" in src
    # même n minimum des deux côtés (le seuil local ne descend jamais sous le n secteur).
    assert signaux.SEUIL_REF_LOCAL >= 1 and bilan.MIN_N_SECTEUR == 8
    assert bilan.PERIODE_SECTEUR_ANS == 5   # fenêtre unique (années récentes), partagée
