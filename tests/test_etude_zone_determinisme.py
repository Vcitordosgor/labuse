"""RECETTE-OUTILS-3 (S1) — DÉTERMINISME de l'Étude de zone.

Constat du mandat 2 : la même parcelle au même rayon rendait des chiffres différents d'un lancement
à l'autre. Cause trouvée : (a) les fenêtres glissantes « N mois » étaient ancrées sur `now()` (le
résultat dépendait du JOUR d'appel) ; (b) la requête des concurrents SIRENE avait un `LIMIT` SANS
`ORDER BY` (PostgreSQL pouvait renvoyer un autre sous-ensemble d'un process à l'autre).

Correctif : fenêtres ancrées sur la DERNIÈRE DATE DES DONNÉES (`max(date)`), tri stable avant tout
`LIMIT`. Deux garanties testées ici :
  · un GARDE DE CODE (sans base, joué par le hook) : plus de `now()` dans les fenêtres de données,
    les ancres sont bien utilisées, et la requête concurrents trie avant de limiter ;
  · un test SUR LA BASE RÉELLE (`local`) : deux appels successifs rendent des valeurs identiques.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parents[1]
_ZONE_SRC = (RACINE / "src/labuse/zone.py").read_text(encoding="utf-8")


def test_zone_fenetres_ancrees_sur_la_donnee():
    """Garde de code (hook) : aucune fenêtre de données « 36 mois » sur `now()`, ancres présentes,
    et la requête concurrents SIRENE trie avant de limiter."""
    # plus aucune fenêtre glissante de DONNÉES sur now() (le cache d'isochrone 30 j et le flag de
    # fraîcheur `maj_ancienne` restent légitimement relatifs à l'instant, mais pas les agrégats).
    assert "now() - interval '36 months'" not in _ZONE_SRC
    # les ancres sur la dernière date des données sont définies ET utilisées
    assert "_ANCRE_DVF" in _ZONE_SRC and "_ANCRE_SITADEL" in _ZONE_SRC
    assert _ZONE_SRC.count("{_ANCRE_SITADEL} - interval '36 months'") >= 3
    assert "{_ANCRE_DVF} - interval '36 months'" in _ZONE_SRC
    # la requête concurrents SIRENE a un ORDER BY stable AVANT son (unique) `LIMIT :maxi`.
    assert _ZONE_SRC.count("LIMIT :maxi") == 1
    lim = _ZONE_SRC.index("LIMIT :maxi")
    ordre = _ZONE_SRC.index("ORDER BY date_creation DESC NULLS LAST, siret")
    assert ordre < lim and (lim - ordre) < 120, "ORDER BY stable attendu juste avant LIMIT :maxi"


@pytest.mark.local
def test_etude_de_zone_deux_appels_identiques():
    """Sur la base réelle : deux appels au même couple (parcelle, rayon) → valeurs IDENTIQUES.
    On exerce les sous-moteurs qui portaient des fenêtres glissantes (population/emplois/marché/
    dynamique) sur le cercle de 1 km autour de la parcelle de référence 97411000BZ1281."""
    from labuse import zone as Z
    from labuse.db import session_scope
    from sqlalchemy import text

    idu = "97411000BZ1281"
    with session_scope() as db:
        pt = db.execute(text(
            "SELECT ST_X(ST_Centroid(centroid)) lon, ST_Y(ST_Centroid(centroid)) lat "
            "FROM parcels WHERE idu = :i"), {"i": idu}).mappings().first()
        if not pt or pt["lon"] is None:
            pytest.skip("parcelle de référence absente de la base locale")
        gj = db.execute(text(
            "SELECT ST_AsGeoJSON(ST_Buffer(ST_SetSRID(ST_MakePoint(:lon,:lat),4326)::geography, 1000)::geometry) g"),
            {"lon": pt["lon"], "lat": pt["lat"]}).scalar()
        geom = json.loads(gj)

        def _un_passage():
            return {
                "population": Z.population_zone(db, geom),
                "emplois": Z.emplois_zone(db, geom),
                "marche": Z.marche_zone(db, geom),
                "dynamique": Z.dynamique_zone(db, geom),
            }

        a = _un_passage()
        b = _un_passage()
    # comparaison sérialisée (ordre des clés indifférent) — strictement identique.
    assert json.dumps(a, sort_keys=True, default=str) == json.dumps(b, sort_keys=True, default=str)
