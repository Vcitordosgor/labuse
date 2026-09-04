"""RETOURS-11F — session F3 (branche `fix/retours-11f3`). Gardes des soldes finaux.

Chaque test grave une divergence corrigée pour qu'elle ne revienne pas. Les gardes de
structure (chaîne SQL, config) sont LECTURE SEULE (aucune base) ; celles qui exigent la
base sont marquées `db` (skippées sans PostGIS).
"""
from __future__ import annotations


# ─────────────────────────── M9 — Densifier : capacité NETTE + surélévation ───────────────────────────

def test_m9_capacite_nette_deduit_les_contraintes():
    """La SDP résiduelle est corrigée par un facteur de constructibilité (PPR rouge %, pente > 30 %,
    ravine, mvt) AVANT de piloter le score : une parcelle contrainte descend. Vic : « 900 m² en
    falaise ne densifie rien »."""
    from labuse import renouvellement as R
    sql = R._BUILD_SQL
    # les trois sources de contrainte, SERVIES par le run (jamais inventées)
    assert "ppr_x" in sql and "PPR zone rouge" in sql, "PPR rouge : fraction réelle non déduite"
    assert "ravine_x" in sql and "mvt_x" in sql, "ravine / mouvement de terrain non pris en compte"
    assert "pente_non_batie_deg" in sql, "pente (parcel_terrain) non prise en compte"
    assert "frac_net" in sql and "sdp_nette" in sql, "SDP nette absente de la formule"
    # le potentiel classe sur la SDP NETTE, plus sur la brute
    assert "percent_rank() OVER (ORDER BY n.sdp_nette)" in sql, "comp_potentiel doit ranker la SDP nette"
    # le facteur reste borné [0,1] (greatest 0 + facteurs ≤ 1)
    assert "greatest(0.0" in sql


def test_m9_surelevation_lue_de_parcel_residuel_bati():
    """La surélévation possible (hauteur PLU − hauteur bâti BD TOPO) est lue de la table déjà
    calculée `parcel_residuel_bati` — jamais recalculée, jamais inventée."""
    from labuse import renouvellement as R
    sql = R._BUILD_SQL
    assert "parcel_residuel_bati" in sql
    assert "surelevation_possible" in sql and "niveaux_sur" in sql
    # DDL : les colonnes existent bien dans la table servie
    assert "sdp_nette_m2" in R.DDL and "surelevation_possible" in R.DDL and "niveaux_surelevation" in R.DDL


def test_m9_config_capacite_nette_chargee():
    """Les facteurs de capacité nette viennent de la config versionnée (jamais codés en dur)."""
    from labuse import renouvellement as R
    cfg = R.load_config()
    cn = cfg["capacite_nette"]
    assert 0 < cn["facteur_pente_forte"] <= 1
    assert 0 < cn["facteur_ravine"] <= 1 and 0 < cn["facteur_mvt"] <= 1
    assert cn["pente_seuil_pct"] == 30
    # le score CONTINU (M9 F2) reste intact : pas de clamp, somme des rangs bruts
    assert "LEAST(100" not in R._BUILD_SQL
    assert "round((c.pr_pot + c.pr_ass + c.pr_mar)" in R._BUILD_SQL
