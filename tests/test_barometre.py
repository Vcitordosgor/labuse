"""Baromètre → onglet « Évolution » de Communes. Véracité (trimestre partiel), séries enrichies,
source unique du prix par commune (PDF ↔ tableau Communes), et le PDF « ne lève pas » (il n'avait
AUCUN test — canal marketing sans filet)."""
from __future__ import annotations

import pytest
from sqlalchemy import text


# ── §1a — un trimestre partiel est marqué (pas de barre courte muette), pur, sans DB ──

def test_marque_partiel():
    from labuse.api.moteurs import _marque_partiel
    partiel = [{"trimestre": "2025T4", "mutations": 100}, {"trimestre": "2025T3", "mutations": 1000},
               {"trimestre": "2025T2", "mutations": 1100}, {"trimestre": "2025T1", "mutations": 900},
               {"trimestre": "2024T4", "mutations": 1050}]
    _marque_partiel(partiel, "mutations")   # 100 < 60 % de la médiane (~1000) → partiel
    assert partiel[0]["partiel"] is True and all(not x["partiel"] for x in partiel[1:])
    complet = [dict(r) for r in partiel]
    complet[0]["mutations"] = 1000          # ≈ médiane → complet
    _marque_partiel(complet, "mutations")
    assert complet[0]["partiel"] is False


def test_tendance_pct_glissement_annuel():
    from labuse.api.moteurs import _tendance_pct
    s = [{"m": 3300, "partiel": False}, {"m": 3200, "partiel": False}, {"m": 3100, "partiel": False},
         {"m": 3050, "partiel": False}, {"m": 3000, "partiel": False}]
    assert _tendance_pct(s, "m") == 10                       # 3300 vs 3000 (4 trim = 1 an) → +10 %
    assert _tendance_pct([{"m": 9, "partiel": True}, *s], "m") == 10   # ignore le partiel en tête
    assert _tendance_pct(s[:3], "m") is None                # < 5 points → pas de tendance


# ── §3 — _barometre_data « ne lève pas ». M141 (commit 1ecba711, décision Vic) a RETIRÉ l'export PDF
#         du baromètre (route GET /barometre.pdf + générateur `barometre_pdf` supprimés en entier, bouton
#         front retiré) : il n'a plus vocation à sortir en PDF. Le test historique importait
#         `barometre_pdf` → ImportError depuis ce retrait. On teste ce qui RESTE (données de l'onglet
#         Évolution) ET on verrouille l'absence VOULUE du PDF (pas de ré-ajout silencieux). ──

@pytest.mark.db
def test_barometre_data_ne_leve_pas(db_session):
    from labuse.api import moteurs
    d = moteurs._barometre_data(db_session)   # ne lève pas
    for k in ("dvf_trimestres", "terrain_trimestres", "permis_trimestres", "tendance_ancien_pct",
              "tendance_terrain_pct", "tendance_permis_pct", "neuf_reference", "top_communes_prix",
              "top_communes_cap", "top_communes_total"):
        assert k in d
    # M141 — plus d'export PDF (ni fonction, ni route) : garde anti-ré-ajout silencieux.
    assert not hasattr(moteurs, "barometre_pdf")
    assert not any(getattr(r, "path", "").endswith("barometre.pdf") for r in moteurs.router.routes)


# ── §1b — UN SEUL prix par commune : le PDF (baromètre) et le tableau (comparateur) lisent la
#         MÊME fonction `prix_ancien_communes`, plus une formule recopiée qui pourrait dériver. ──

@pytest.mark.db
def test_prix_ancien_source_unique_pdf_vs_comparateur(db_session):
    from labuse.api import comparateur
    from labuse.api.moteurs import prix_ancien_communes
    _wkt = "POLYGON((55.4 -21.0,55.4003 -21.0,55.4003 -20.9997,55.4 -20.9997,55.4 -21.0))"
    db_session.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2, centroid, bbox) VALUES "
        "('97499000TV0001','Testville','S','1', ST_GeomFromText(:w,4326),"
        " ST_Transform(ST_GeomFromText(:w,4326),2975), 500,"
        " ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326))) ON CONFLICT (idu) DO NOTHING"),
        {"w": _wkt})
    # 100 ventes strictes à 3 000 €/m² bâti (300 000 € / 100 m²) → médiane 3 000, seuil ≥ 100 atteint
    db_session.execute(text(
        "INSERT INTO dvf_mutations (date_mutation, nature_mutation, valeur_fonciere, surface_reelle_bati, commune, geom) "
        "SELECT '2025-03-15', 'Vente', 300000, 100, 'Testville', ST_SetSRID(ST_Point(55.4,-21.0),4326) "
        "FROM generate_series(1, 100)"))
    pa = prix_ancien_communes(db_session)
    assert pa.get("Testville", {}).get("median") == 3000
    # le tableau Communes (comparateur._compute) lit la MÊME fonction → le MÊME chiffre
    out = comparateur._compute(db_session, {"stock": 0.3, "velocite": 0.15, "permis": 0.15,
                                            "deficit_sru": 0.15, "pression_zan": 0.10, "prix_neuf": 0.15})
    tv = next((r for r in out["communes"] if r["commune"] == "Testville"), None)
    assert tv is not None and tv["prix_ancien"] == 3000
