"""CONNEXIONS-2 Lot 5 (KO-7) — parité filtre carte ↔ veille de recherche.

Avant : la veille n'évaluait que 5 dimensions (tier, commune, événement, surface, SDP) alors que le
filtre en sérialise ~35 → sur-alerte silencieuse. Désormais un POINT UNIQUE (`filtre_from_hash` +
`parcelles_matchant_hash`) évalue la veille avec le MÊME moteur que la carte (`_q_v2_list`).

On prouve : (1) le hash rend un FiltreCriteres couvrant des dimensions HORS des 5 anciennes ;
(2) rien n'est surveillé en silence (dimensions non évaluables listées) ; (3) comportement : une
veille à 3 critères (dont un hors des 5) ne matche QUE les parcelles vérifiant les 3.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.api.app import (dimensions_hash_non_evaluees, filtre_from_hash,
                            parcelles_matchant_hash)


def test_hash_couvre_les_dimensions_hors_des_5():
    """Le hash → FiltreCriteres pour des dimensions IGNORÉES avant (zonage, état-sol, signaux,
    propriétaire) : la parité est réelle, la clause WHERE les porte (même moteur que la carte)."""
    c = filtre_from_hash("#f=1&cs=Saint-Pierre&smin=500&zf=U&es=libre&sv=friche&pt=personne_morale")
    assert c.communes == "Saint-Pierre" and c.surface_min == 500
    assert c.zonage == "U" and c.etat_sol == "libre" and c.signaux == "friche"
    assert c.proprietaire_type == "personne_morale"
    where, params = c.where()
    # les dimensions HORS des 5 anciennes apparaissent bien dans le WHERE partagé
    assert "zone_fam" in where            # zonage
    assert params.get("f_communes") == ["Saint-Pierre"]
    assert "signaux" in where.lower() or "friche" in where.lower()


def test_rien_surveille_en_silence():
    """Une clé inconnue du mappage est LISTÉE comme non évaluable (jamais retenue en silence) ;
    un filtre entièrement connu ne laisse rien de côté."""
    assert dimensions_hash_non_evaluees("#f=1&cs=Saint-Pierre&zf=U") == []
    assert dimensions_hash_non_evaluees("#f=1&cs=X&inconnue=42") == ["inconnue"]
    # `al` (toggle scoring), `z` (zone géo), `f` (marqueur) ne sont pas des dimensions de matching
    assert dimensions_hash_non_evaluees("#f=1&al=1&z=1_2") == []


_WKT = "POLYGON((55.48 -21.30,55.481 -21.30,55.481 -21.301,55.48 -21.301,55.48 -21.30))"
_RUN = "q_veille_test"


def _seed(s, idu, commune, surface, zone_fam, status="retenue"):
    pid = s.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2, centroid, bbox) VALUES "
        "(:i,:c,'ZZ','1', ST_GeomFromText(:w,4326), ST_Transform(ST_GeomFromText(:w,4326),2975), :s, "
        " ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326))) RETURNING id"),
        {"i": idu, "c": commune, "w": _WKT, "s": surface}).scalar()
    s.execute(text(
        "INSERT INTO dryrun_parcel_evaluations (run_label, parcel_id, completeness_score, opportunity_score, status) "
        "VALUES (:r, :p, 50, 50, :st)"), {"r": _RUN, "p": pid, "st": status})
    s.execute(text("INSERT INTO parcel_zone_plu (idu, zone_lib, zone_fam) VALUES (:i,:z,:f)"),
              {"i": idu, "z": zone_fam, "f": zone_fam})
    return pid


@pytest.mark.db
def test_veille_3_criteres_ne_matche_que_les_3(db_session):
    """Une veille « commune=Saint-Pierre ET surface≥500 ET zonage=U » (le zonage est HORS des 5
    dimensions d'avant) ne déclenche QUE sur la parcelle qui vérifie les trois. Sur l'ancien code
    (zonage ignoré), la parcelle en zone A aurait sur-alerté."""
    s = db_session
    a = "97410000VA0001"   # OK : Saint-Pierre, 800 m², zone U → matche les 3
    b = "97410000VA0002"   # zone A → échoue le zonage
    c = "97410000VA0003"   # 300 m² → échoue la surface
    d = "97410000VA0004"   # autre commune → échoue la commune
    _seed(s, a, "Saint-Pierre", 800, "U")
    _seed(s, b, "Saint-Pierre", 800, "A")
    _seed(s, c, "Saint-Pierre", 300, "U")
    _seed(s, d, "Le Tampon", 800, "U")
    hash_v = "#f=1&cs=Saint-Pierre&smin=500&zf=U"
    matched = parcelles_matchant_hash(s, hash_v, _RUN, [a, b, c, d], sans_tiers=True)
    assert matched == {a}
