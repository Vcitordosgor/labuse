"""FIX-FILTRES — verrous de sémantique du constructeur de WHERE (`_q_v2_where`).

F4 : `zonage` (famille) et `zone_plu` (zone exacte) sont deux clauses INDÉPENDANTES cumulées
     en ET. L'UI les rend exclusifs, mais un deep-link peut poser les deux — l'intersection est
     le comportement voulu et ne doit pas régresser vers « l'un écrase l'autre ».
F5 : la normalisation majuscule des DEUX filtres de zonage se fait en PG (`upper()`), pas en
     Python (`str.upper()`) — une seule convention (le paramètre voyage BRUT).
"""
from __future__ import annotations

import dataclasses

import pytest

from labuse.api.app import FiltreCriteres, _q_v2_where


def _where(**kw) -> tuple[str, dict]:
    # arguments positionnels minimaux de _q_v2_where (score_min retiré — FIX-SCOREMIN) : le reste en mots-clés
    return _q_v2_where("q_v10_m129", None, None, None, False, None, **kw)


def test_zonage_zone_plu_cumulent_en_et():
    """F4 — les deux clauses coexistent (cumul ET), aucune n'écrase l'autre."""
    where, params = _where(zonage="U", zone_plu="UA")
    # les deux colonnes distinctes apparaissent → deux EXISTS cumulés
    assert "zone_fam" in where, "la clause famille (zonage) doit être présente"
    assert "zone_filtre" in where, "la clause zone exacte (zone_plu) doit être présente"
    # cumul = conjonction (le WHERE est une suite de « AND ») : les deux paramètres sont liés
    assert params.get("f_zonage") == ["U"]
    assert params.get("f_zplu") == ["UA"]
    # chacune seule ne fait apparaître QUE sa clause (pas d'écrasement mutuel)
    w_fam, _ = _where(zonage="A")
    assert "zone_fam" in w_fam and "zone_filtre" not in w_fam
    w_exact, _ = _where(zone_plu="Nh")
    assert "zone_filtre" in w_exact and "zone_fam" not in w_exact


def test_normalisation_zonage_en_pg_pas_python():
    """F5 — le paramètre famille voyage BRUT (pas de str.upper() Python) ; le pliage majuscule
    est fait par PG (`upper()` dans la sous-requête), même convention que zone_plu."""
    where, params = _where(zonage="u", zone_plu="ua")
    # le paramètre n'est PAS remonté en majuscules côté Python…
    assert params["f_zonage"] == ["u"], "le pliage ne doit plus se faire en Python"
    assert params["f_zplu"] == ["ua"]
    # …c'est PG qui plie, via upper() dans la clause (une seule convention des deux côtés)
    assert "SELECT upper(v) FROM unnest" in where
    # les deux filtres de zonage utilisent le MÊME pliage PG (deux occurrences upper(v))
    assert where.count("upper(v)") >= 2


def test_score_min_retire_du_contrat():
    """FIX-SCOREMIN — le paramètre mort `score_min` est PURGÉ du contrat : ni champ FiltreCriteres,
    ni argument de `_q_v2_where`. Un vieux `?score_min=` est ignoré par FastAPI (param inconnu) —
    jamais lu dans un champ pour être ensuite silencieusement non filtré."""
    champs = {f.name for f in dataclasses.fields(FiltreCriteres)}
    assert "score_min" not in champs, "score_min ne doit plus être un critère de /filtre"
    # la fonction de WHERE ne connaît plus le paramètre (kwarg inattendu → TypeError)
    with pytest.raises(TypeError):
        _q_v2_where("q_v10_m129", None, None, None, False, None, score_min=90)
