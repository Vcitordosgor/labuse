"""VEFA-1 — le €/m² du logement neuf (VEFA) se calcule sur les SURFACES DES LOTS D'HABITATION,
sur une fenêtre ANCRÉE sur la dernière vente (jamais un now() glissant).

Tests sur 3 mutations RÉELLES extraites de dvf_mutations_parcelle au 974 (geo-DVF 2021-2025) :

  · SIMPLE     2021-1673153 — 1 appartement 41 m², 176 200 €                → 4 298 €/m²
  · MULTI-LOTS 2021-1672907 — 3 appartements (45+45+59=149 m²) + 3 parkings → 4 538 €/m²
                              (valeur / SOMME des surfaces habitables ; jamais / un seul lot = 15 024 ;
                               les dépendances/parkings n'entrent pas au dénominateur ; jamais éliminée)
  · MIXTE      2022-1639750 — 1 appartement 104 m² + 2 locaux commerciaux (177+137 m²), 630 360 €
                              → 6 061 €/m² habitable (et NON 1 508 €/m² si on sommait le commercial)

Graver ces trois cas interdit la régression du dénominateur (dilution par le commercial/les parkings)
et de la fenêtre (érosion du vieux bord par un now() glissant sur un millésime pourtant figé).
"""
from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy import text

from labuse.ingestion.dvf_marche import neuf_vefa_commune

VEFA = "Vente en l'état futur d'achèvement"
INSEE = "97499"   # commune de test, hors des 24 réelles

# (id_parcelle, type_local, surface_reelle_bati) — lignes réelles des 3 mutations.
_SIMPLE = [("97411000AY0401", "Appartement", 41.0)]
_MULTI = [
    ("97411000DK0038", "Appartement", 45.0),
    ("97411000DK0038", "Appartement", 45.0),
    ("97411000DK0038", "Appartement", 59.0),
    ("97411000DK0038", "Dépendance", None),      # parking — pas de surface habitable
    ("97411000DK0038", "Dépendance", None),
    ("97411000DK0038", "Dépendance", None),
]
_MIXTE = [
    ("97423000AB1840", "Appartement", 104.0),
    ("97423000AB1840", "Local industriel. commercial ou assimilé", 177.0),
    ("97423000AB1840", "Local industriel. commercial ou assimilé", 137.0),
]
_MUTATIONS = [
    ("2021-1673153", dt.date(2021, 2, 4), 176200.0, _SIMPLE),
    ("2021-1672907", dt.date(2021, 2, 16), 676096.0, _MULTI),
    ("2022-1639750", dt.date(2022, 11, 18), 630360.0, _MIXTE),
]


def _seed(db, mutations, *, insee=INSEE, base=990000):
    rid = base
    for id_mut, date_mut, valeur, lignes in mutations:
        for parcelle, type_local, surf in lignes:
            db.execute(text(
                "INSERT INTO dvf_mutations_parcelle (id, id_mutation, date_mutation, nature_mutation, "
                "valeur_fonciere, code_commune, id_parcelle, type_local, surface_reelle_bati, millesime) "
                "VALUES (:id, :m, :d, :n, :v, :c, :p, :tl, :s, :mi)"),
                {"id": rid, "m": id_mut, "d": date_mut, "n": VEFA, "v": valeur, "c": insee,
                 "p": parcelle, "tl": type_local, "s": surf, "mi": date_mut.year})
            rid += 1
    db.flush()


@pytest.mark.db
def test_denominateur_lots_habitation_sur_3_mutations_reelles(db_session):
    db = db_session
    _seed(db, _MUTATIONS)
    v = neuf_vefa_commune(db, INSEE)

    # Les 3 mutations portent une surface d'habitation → les 3 sont SERVIES (aucune éliminée).
    assert v["n_total"] == 3
    assert v["n"] == 3

    # Médiane des €/m² habitables : median(4298, 4538, 6061) = 4538.
    # Si le dénominateur sommait le commercial, la MIXTE vaudrait 1 508 € et la médiane tomberait à 4 298.
    assert v["mediane_prix_m2_bati"] == 4538


@pytest.mark.db
def test_eur_m2_par_mutation(db_session):
    """Chaque mutation, isolée dans sa commune, donne le €/m² habitable attendu."""
    db = db_session
    attendus = {
        "2021-1673153": 4298,   # 176200 / 41
        "2021-1672907": 4538,   # 676096 / (45+45+59) — pas / 45 (=15024), parkings exclus
        "2022-1639750": 6061,   # 630360 / 104 — locaux commerciaux (314 m²) exclus, PAS 1508
    }
    for i, (id_mut, *_rest) in enumerate(_MUTATIONS):
        insee = f"9749{i}"
        _seed(db, [m for m in _MUTATIONS if m[0] == id_mut], insee=insee, base=990000 + i * 100)
        v = neuf_vefa_commune(db, insee)
        assert v["n"] == 1
        assert v["mediane_prix_m2_bati"] == attendus[id_mut], id_mut


@pytest.mark.db
def test_mixte_commercial_non_dilue(db_session):
    """Régression ciblée : la mutation mixte vaut 6 061 €/m² (habitable), jamais 1 508 (tout sommé)."""
    db = db_session
    _seed(db, [m for m in _MUTATIONS if m[0] == "2022-1639750"])
    v = neuf_vefa_commune(db, INSEE)
    assert v["mediane_prix_m2_bati"] == 6061
    assert v["mediane_prix_m2_bati"] != 1508


@pytest.mark.db
def test_fenetre_ancree_sur_derniere_vente_pas_sur_horloge(db_session):
    """La fenêtre est ancrée sur max(date_mutation), pas sur now() : une vente ~4,8 ans AVANT la
    dernière vente observée reste servie, même si elle a plus de 5 ans par rapport à l'horloge
    système (millésime DVF figé → un now() glissant la jetterait à tort)."""
    db = db_session
    recent = dt.date(2025, 12, 1)          # dernière vente observée (ancre)
    vieille = dt.date(2021, 3, 1)          # > 5 ans avant aujourd'hui (2026), < 5 ans avant l'ancre
    muts = [
        ("A-ancre", recent, 60 * 4800.0, [("97499000AA0001", "Appartement", 60.0)]),
        ("A-vieille", vieille, 60 * 4200.0, [("97499000AA0002", "Appartement", 60.0)]),
    ]
    _seed(db, muts)
    v = neuf_vefa_commune(db, INSEE)
    # Les DEUX sont dans la fenêtre ancrée (2020-12 → 2025-12) ; un now()-5 ans n'en garderait qu'une.
    assert v["n_total"] == 2
    assert v["n"] == 2
