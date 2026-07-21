"""O12 — DIVISION EN OR : détecteur conservateur, MASQUÉ jusqu'à validation visuelle Vic (20 cartes).

Faux positif = péché mortel : EXPOSE=False ; seuils conservateurs codés en dur dans _DETECT ;
la métrique d'accès du lot bâti (invalidée) n'est PAS filtrante — champ NULL, revue humaine.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.ingestion import division_or as d


def test_expose_false():
    assert d.EXPOSE is False    # masqué tant que Vic n'a pas validé le dossier de revue


def test_seuils_conservateurs_dans_detect():
    q = d._DETECT
    assert "BETWEEN 1000 AND 6000" in q            # parcelle assez grande pour DEUX lots
    assert "BETWEEN 0.08 AND 0.45" in q            # bâti présent mais ne remplit pas
    assert "free_m2 >= 500" in q and "surface_m2 - 400" in q   # les deux lots restent viables
    assert "rad >= 9" in q                          # pas de lanière (largeur ~18 m)
    assert "facade_free >= 12" in q                 # accès voirie indépendant


def test_metrique_bati_invalidee_pas_filtrante():
    # la métrique façade du lot bâti est NULL (invalidée — finding), jamais un filtre sur un chiffre faux
    assert "NULL::numeric AS bati_facade_m" in d._DETECT
    assert "(facade_parcelle - facade_free) >= 5" not in d._DETECT


@pytest.mark.db
def test_build_commune_vide_et_table_creee(db_session):
    s = db_session
    r = d.build_divisions(s, ["Commune-Inexistante"], commit=False, log=lambda *_: None)
    assert r["total"] == 0 and r["expose"] is False
    # la table masquée existe (DDL passé), vide
    assert s.execute(text("SELECT count(*) FROM division_or_candidates")).scalar() == 0
    assert d.top_candidates(s, limit=5) == []
