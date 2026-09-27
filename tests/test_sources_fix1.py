"""SOURCES-FIX-1 — verrous des 3 écarts + 5 mortes.

DVF : une seule médiane, même table (`dvf_mutations`), à périmètre égal (E1).
Mortes : les 5 sont `retiree` avec motif, Office de l'eau n'est plus dite « servie » (E3).
Contraintes : les 3 blocs de la fiche parcelle (APER, mesures compensatoires, SCOT) sont câblés
au registre (registre.verifier == []) et servis par un robinet (A1/A2/A3).
"""
from __future__ import annotations

import json

import pytest
from sqlalchemy import text

from labuse.db import session_scope


def _has_table(s, t: str) -> bool:
    return s.execute(text("SELECT to_regclass(:t)"), {"t": t}).scalar() is not None


def test_dvf_une_seule_mediane_meme_table_sur_3_communes():
    """E1 — l'Étude de zone (`marche_zone`) et le point de calcul unique (`dvf_mediane.mediane_bati`)
    donnent la MÊME médiane €/m² bâti au MÊME périmètre, sur 3 communes témoins ; et le périmètre
    commune (attribut) == le périmètre polygone. Toutes lisent `dvf_mutations` (plus jamais l'éclatée)."""
    from labuse import zone as Z
    from labuse.dvf_mediane import mediane_bati
    with session_scope() as s:
        if not _has_table(s, "dvf_mutations") or not _has_table(s, "parcels"):
            pytest.skip("base sans dvf_mutations/parcels")
        communes = []
        for (c,) in s.execute(text(
                "SELECT commune, count(*) n FROM dvf_mutations WHERE commune IS NOT NULL "
                "AND nature_mutation ILIKE 'vente%' AND coalesce(surface_reelle_bati,0)>=20 "
                "AND valeur_fonciere>0 AND date_mutation>=now()-interval '36 months' "
                "GROUP BY commune HAVING count(*)>=20 ORDER BY count(*) DESC LIMIT 3")):
            communes.append(c)
        if len(communes) < 3:
            pytest.skip("moins de 3 communes avec assez de ventes")
        for c in communes:
            gj = s.execute(text("SELECT ST_AsGeoJSON(ST_Union(geom)) FROM parcels WHERE commune=:c"),
                           {"c": c}).scalar()
            geom = json.loads(gj)
            mz = Z.marche_zone(s, geom)["prix_m2_median_bati"]
            helper_geom = mediane_bati(s, geom_geojson=geom)["median"]
            helper_com = mediane_bati(s, commune=c)["median"]
            assert mz == helper_geom, f"{c}: marche_zone {mz} != helper(geom) {helper_geom}"
            assert helper_geom == helper_com, f"{c}: geom {helper_geom} != commune {helper_com}"


def test_zone_ne_lit_plus_la_table_eclatee():
    """E1 — plus aucune requête de zone/marché ne LIT la table éclatée (FROM dvf_mutations_parcelle)."""
    import pathlib
    src = pathlib.Path(__file__).resolve().parent.parent / "src" / "labuse" / "zone.py"
    assert "FROM dvf_mutations_parcelle" not in src.read_text(encoding="utf-8")


def test_cinq_mortes_retiree_avec_motif():
    """Les 5 sources mortes portent un motif de retrait durable EN CODE (RETRAITS)."""
    from labuse.ingestion.seed_sources import RETRAITS
    for nom in ["EDF SEI Réunion — open data", "Registre national des installations (ODRÉ)",
                "Office de l'eau Réunion — Chroniques de l'eau",
                "MOBPRO (mobilités domicile-travail, INSEE)", "BDNB"]:
        assert RETRAITS.get(nom), f"{nom} : pas de motif de retrait en code"


def test_office_eau_nest_plus_dite_servie():
    """E3 — ni le commentaire du catalogue ni la note seed de la source ne disent plus « servie à la fiche »."""
    import pathlib
    root = pathlib.Path(__file__).resolve().parent.parent
    sc = (root / "src" / "labuse" / "sources_catalog.py").read_text(encoding="utf-8")
    seed = (root / "src" / "labuse" / "ingestion" / "seed_sources.py").read_text(encoding="utf-8")
    assert "est SERVIE à la fiche depuis M95" not in sc
    assert "SERVIE à la fiche depuis M95" not in seed


def test_trois_contraintes_cablees_au_registre():
    """A1/A2/A3 — les 3 données sont au registre, servies par un robinet, câblées au robinet fiche."""
    from labuse.registre import donnees as D
    from labuse.registre import robinets as ROB
    from labuse.exports import miroir as M
    ids = {"enr_exclue_parcelle", "mesures_compensatoires_parcelle", "scot_parcelle"}
    assert ids <= set(D.DONNEES)
    servis = {c for r in ROB.ROBINETS.values() for c in (r.chiffres or ())}
    assert ids <= servis, f"non servis par un robinet : {ids - servis}"
    assert not (ids & set(M.non_cables())), "un id contrainte n'a pas d'extracteur PDF"
