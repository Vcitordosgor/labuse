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


# ─────────────────────────── M13 — colonnes Comparer + sélecteur Évolution ───────────────────────────

def test_m13_compare_row_colonnes_ajoutees():
    """Comparer sert les colonnes O9 manquantes, TOUTES lues de la fiche servie (aucun second moteur) :
    propriétaire, bâti existant %, gabarit max, logements, accès & réseaux (UN verdict), assainissement,
    prix bâti secteur — sans jamais un « 0 » inventé (absent = None)."""
    from labuse.api.app import _compare_row
    qv2 = {
        "idu": "97415000BS0086", "commune": "Saint-Paul", "surface_m2": 1000,
        "score_v2": {"tier": "chaude", "rang": 12, "label": "À suivre", "fraction": "1/5", "pourquoi": []},
        "etage0": False,
        "proprietaire_moral": {"denomination": "PACIFIC", "siren": "484061601"},
        "viabilisation": {"libelle": "Viabilisation probable"},
        "anc": {"libelle": "Tout-à-l'égout (collectif)", "statut": "source"},
        "dvf_parcelle": {"secteur": [
            {"type_bien": "maison", "mediane_prix_m2": 2800, "n_ventes": 43},
            {"type_bien": "terrain", "mediane_prix_m2": 480, "n_ventes": 12}]},
        "lines": [{"result": "SOFT_FLAG", "detail": "Aléa inondation — niveau faible."}],
    }
    faisab = {"zone": "U", "constructible": True,
              "fourchette": {"surface_plancher_m2": 800, "logements_au_sol": [2, 6], "logements_sous_sol": [1, 4]},
              "residuel": {"disponible": True, "emprise_batie_m2": 150, "taux_emprise_pct": 20,
                           "sdp_residuelle_m2": 600, "sous_densite": True, "niveaux_max": 3},
              "bilan": {"charge_fonciere": {"par_m2_terrain": 250}}}
    row = _compare_row(qv2, faisab)
    assert row["proprietaire"] == "morale"                 # PM connue
    assert row["bati_existant_pct"] == 15                  # 150 / 1000
    assert row["gabarit_niveaux_max"] == 3
    assert row["logements_possibles"] == 6                 # borne haute (au sol)
    assert row["acces_reseaux"] == "Viabilisation probable"  # UN verdict
    assert row["assainissement"] == "Tout-à-l'égout (collectif)"
    assert row["prix_secteur_bati_m2"] == 2800            # bâti (maison), JAMAIS le terrain nu


def test_m13_compare_row_particulier_et_absences_sans_zero_invente():
    """Sans PM → particulier ; sans faisabilité/secteur → None (jamais un « 0 »)."""
    from labuse.api.app import _compare_row
    qv2 = {"idu": "97411000AT0710", "commune": "Saint-Denis", "surface_m2": None,
           "score_v2": {}, "etage0": True, "proprietaire_moral": None, "lines": []}
    row = _compare_row(qv2, None)
    assert row["proprietaire"] == "particulier"
    assert row["bati_existant_pct"] is None                # surface absente → None, pas 0
    assert row["prix_secteur_bati_m2"] is None
    assert row["logements_possibles"] is None


def test_m13_evolution_barometre_accepte_commune():
    """Évolution du marché : `_barometre_data` accepte un `insee` (sélecteur de commune) et le neuf
    de la commune vient du moteur UNIQUE M1 (neuf_vefa_commune) — jamais un second calcul."""
    import inspect
    from labuse.api import moteurs
    sig = inspect.signature(moteurs._barometre_data)
    assert "insee" in sig.parameters, "le baromètre doit accepter un insee (sélecteur commune)"
    src = inspect.getsource(moteurs._barometre_data)
    assert "neuf_vefa_commune" in src, "le neuf commune doit venir du moteur unique M1"
    assert "code_commune = :insee" in src, "la série terrain doit filtrer par commune"
