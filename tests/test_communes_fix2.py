"""OUTIL-COMMUNES-FIX-2 — recontrôle externe (03-COMMUNES-ASTRA-2) : liste fermée de six points.

Chaque cas chiffré du relecteur devient un test. Marqueur `db` (base réelle, lecture seule) : les
valeurs exactes exigent le jeu de données servi ; sur une base de test vide, les tests se skippent
(comme `test_dvf_doublons_couple`). Les invariants STRUCTURELS (num ⊆ dénom, arrêtés ≤ périls) tiennent
sur toute base.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

pytestmark = pytest.mark.db


def _has(conn) -> bool:
    try:
        return bool(conn.execute(text("SELECT 1 FROM dvf_mutations_parcelle LIMIT 1")).scalar())
    except Exception:
        return False


def _db():
    from labuse.db import engine
    return engine()


# ── #1 Terrain nu : qualifier sur l'acte entier AVANT toute jointure cadastrale ──────────────────
def test_terrain_mutation_batie_hors_cadastre_est_exclue():
    """2021-1677591 (Saint-Denis) porte une maison de 50 m² sur AV0527, ABSENTE de `parcels` (disparue
    du cadastre). Qualifiée via `code_commune` (toutes les lignes DVF), son bâti total n'est pas nul →
    l'acte est écarté du terrain nu. La zone U de Saint-Denis tombe à 285 €/m² sur 604 actes."""
    with _db().connect() as c:
        if not _has(c):
            pytest.skip("base sans dvf_mutations_parcelle")
        bati = c.execute(text(
            "SELECT sum(b) FROM (SELECT max(COALESCE(surface_reelle_bati,0)) b "
            "FROM dvf_mutations_parcelle WHERE id_mutation='2021-1677591' AND code_commune='97411' "
            "GROUP BY id_parcelle) q")).scalar()
        if bati is None:
            pytest.skip("mutation 2021-1677591 absente de la base locale")
        assert bati and bati > 0, "l'acte porte une maison (50 m²) : son bâti total n'est pas nul"

        from labuse.faisabilite.marche_commune import ligne2_terrain_zone
        sess = Session(bind=c)
        u = ligne2_terrain_zone(sess, "Saint-Denis")["valeurs"]["par_zone"]["U"]
        assert u["median_eur_m2"] == 285, f"Saint-Denis U attendu 285, obtenu {u['median_eur_m2']}"
        assert u["n"] == 604, f"effectif ENTRANT dans la médiane attendu 604, obtenu {u['n']}"


def test_terrain_effectif_est_celui_de_la_mediane():
    """L'effectif affiché est celui qui ENTRE dans la médiane (ratio non nul), pas le comptage brut."""
    with _db().connect() as c:
        if not _has(c):
            pytest.skip("base sans dvf_mutations_parcelle")
        from labuse.faisabilite.marche_commune import ligne2_terrain_zone
        pz = ligne2_terrain_zone(Session(bind=c), "Saint-Paul")["valeurs"]["par_zone"]["U"]
        if not pz.get("calculable"):
            pytest.skip("Saint-Paul U non calculable sur cette base")
        assert pz["n"] == 879 and pz["median_eur_m2"] == 271


# ── #3 Risques : numérateur ⊆ dénominateur (jamais > 100 %) ; arrêtés ≠ périls ───────────────────
def test_exposition_jamais_au_dessus_de_100pct():
    from labuse.api.fiche_commune import risques
    with _db().connect() as c:
        if not _has(c):
            pytest.skip("base sans données")
        sess = Session(bind=c)
        communes = [(r[0], r[1]) for r in sess.execute(text(
            "SELECT DISTINCT commune, left(idu,5) FROM parcels")).all()]
        if not communes:
            pytest.skip("pas de parcelles")
        for commune, insee in communes:
            r = risques(sess, commune, insee)
            for k in ("ppr_pct", "mouvement_terrain_pct"):
                v = r.get(k)
                assert v is None or v <= 100.0, f"{commune}.{k} = {v} > 100 % (num ⊄ dénom)"
        sd = risques(sess, "Saint-Denis", "97411")
        assert sd["ppr_pct"] == 72.5, f"Saint-Denis PPR attendu 72,5 %, obtenu {sd['ppr_pct']}"


def test_catnat_arretes_distincts_des_perils():
    """Un arrêté CatNat (identifié par sa date) couvre plusieurs périls : Saint-Denis 14 arrêtés / 21
    entrées par péril. `catnat_arretes` ≤ `catnat_perils`."""
    from labuse.api.fiche_commune import risques
    with _db().connect() as c:
        if not _has(c):
            pytest.skip("base sans données")
        sess = Session(bind=c)
        r = risques(sess, "Saint-Denis", "97411")
        if not r.get("catnat_perils"):
            pytest.skip("pas d'arrêtés CatNat pour Saint-Denis sur cette base")
        assert r["catnat_arretes"] <= r["catnat_perils"]
        assert r["catnat_arretes"] == 14 and r["catnat_perils"] == 21


# ── #4 VEFA : des lots distincts de même surface ne sont pas des doublons ─────────────────────────
def test_vefa_lots_meme_surface_non_fusionnes():
    """Acte 2021-1678474 : lots de 44, 65 et 65 m² sur AS0305 → 174 m² (pas 109). Médiane Saint-Denis
    4 878 €/m² (et non 4 886)."""
    from labuse.ingestion.dvf_marche import neuf_vefa_commune
    with _db().connect() as c:
        if not _has(c):
            pytest.skip("base sans données")
        sess = Session(bind=c)
        r = neuf_vefa_commune(sess, "97411")
        if not r.get("mediane_prix_m2_bati"):
            pytest.skip("VEFA Saint-Denis non calculable sur cette base")
        assert r["mediane_prix_m2_bati"] == 4878, f"attendu 4 878, obtenu {r['mediane_prix_m2_bati']}"


# ── #1 Étude de zone : la source lue contient bien du terrain nu ─────────────────────────────────
def test_etude_zone_terrain_sur_source_avec_terrain():
    """`dvf_mutations` ne porte AUCUN terrain nu (toutes mutations bâties) : `prix_par_type_zone` lit
    désormais `dvf_mutations_parcelle` et rend un terrain nu non vide sur une zone qui en contient."""
    from labuse.zone import prix_par_type_zone
    with _db().connect() as c:
        if not _has(c):
            pytest.skip("base sans données")
        sess = Session(bind=c)
        g = sess.execute(text(
            "SELECT ST_AsGeoJSON(ST_ConvexHull(ST_Collect(geom)))::json FROM parcels WHERE commune='Saint-Denis'"
        )).scalar()
        if not g:
            pytest.skip("pas de géométrie Saint-Denis")
        terr = next((t for t in prix_par_type_zone(sess, g)["types"] if t["type"] == "terrain"), None)
        assert terr and terr["n"] and terr["n"] > 0, "l'Étude de zone doit trouver du terrain nu"
