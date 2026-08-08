"""M-N — hypothèses par commune (P1-13), fiabilité du bilan au prix neuf (P2-47), radar (P2-51).

Tests PURS (aucun accès base) : ils verrouillent la doctrine, pas les données.
"""
from __future__ import annotations

from datetime import datetime, timezone

from labuse.faisabilite.engine import HE_DEFAUT_GENERIQUE_M, Hypotheses
from labuse.faisabilite.plu_rules import _hypotheses_faisabilite, _zone_generique
from labuse.faisabilite.bilan import compute_bilan, _fiabilite_prix_neuf
from labuse.radar import _parse_date_amont


# ── P1-13 — Hypotheses.charger(commune) ──────────────────────────────────────────────────────
def test_yaml_communal_effectivement_lu():
    """Validation #2 : le YAML PLU d'une commune est RÉELLEMENT lu (plus le Saint-Paul en dur).
    Preuve : Saint-Paul DÉCLARE sa source de mixité (mixite_source_ref) ; Saint-Denis, qui ne la
    déclare pas, ne l'hérite PAS — c'est donc bien SA section qui est lue, pas celle de Saint-Paul."""
    assert Hypotheses.charger(None).mixite_source_ref == "Art. 2 règlement PLU"
    assert Hypotheses.charger("Saint-Paul").mixite_source_ref == "Art. 2 règlement PLU"
    assert Hypotheses.charger("Saint-Denis").mixite_source_ref is None
    # la section existe bien et est non vide pour une commune outillée
    assert _hypotheses_faisabilite("Le Tampon"), "section hypotheses_faisabilite du Tampon vide ?"


def test_repli_defauts_dataclass_pas_saint_paul():
    """Validation #3 : commune SANS YAML → défauts du DATACLASS, jamais Saint-Paul."""
    assert _hypotheses_faisabilite("Communefictive") == {}
    h, d = Hypotheses.charger("Communefictive"), Hypotheses()
    assert h.mixite_source_ref is None                      # jamais l'Art. 2 emprunté
    assert h.pct_lls == d.pct_lls == 0.0                    # pas le 30 % de Saint-Paul
    assert h.mixite_sdp_seuil_m2 == d.mixite_sdp_seuil_m2   # seuils = défauts dataclass
    assert h.cout_construction_m2_bas == d.cout_construction_m2_bas


def test_zone_generique_he_du_dataclass():
    """Conséquence #1 : hé générique d'une zone estimée = constante dataclass, pas le YAML SP."""
    zg = _zone_generique("U2")
    assert zg.calibree is False
    assert zg.he_m == HE_DEFAUT_GENERIQUE_M == 9.0


# ── P1-13 — source affichée des seuils de mixité ─────────────────────────────────────────────
def _prix_fiable() -> dict:
    return {"fiabilite": "fiable", "fiable": True, "type_prix": "appartement", "n": 12,
            "n_exclus": 0, "n_doublons": 0, "radius_m": 1000.0, "commune_fallback": False,
            "periode": [2019, 2024], "q1": 4000, "median": 4400, "q3": 4800,
            "min": 3500, "max": 5200, "pct_appartement": 100}


def _eco_mixite_sous_seuils() -> dict:
    # programme SOUS les seuils → step « clause non déclenchée » qui PORTE la source affichée
    return {"mixite": True, "sdp_max_m2": 200, "logements_estimes": 3, "terrain_m2": 500}


def test_mixite_source_art2_seulement_si_declaree():
    """Validation #1 : une commune qui ne déclare pas sa source n'affiche JAMAIS « Art. 2 » ;
    seule Saint-Paul (qui la déclare) le fait."""
    def _src_mixite(commune):
        b = compute_bilan(1000.0, 2000.0, _prix_fiable(), Hypotheses.charger(commune),
                          contexte_eco=_eco_mixite_sous_seuils())
        steps = [s for s in b.steps if "mixit" in s.label.lower()]
        assert steps, "step mixité absent"
        return steps[0].source

    assert _src_mixite(None) == "Art. 2 règlement PLU"
    assert _src_mixite("Saint-Paul") == "Art. 2 règlement PLU"
    for commune in ("Saint-Denis", "Le Tampon", "Communefictive"):
        assert "Art. 2" not in _src_mixite(commune)
        assert "défaut" in _src_mixite(commune)


# ── P2-47 — fiabilité et disponibilité du bilan viennent du prix NEUF ─────────────────────────
def _prix_insuffisant() -> dict:
    # ce que renvoie sector_price quand l'ancien est mince : NI médiane NI quartiles.
    return {"fiabilite": "insuffisant", "fiable": False, "type_prix": "mixte (appart+maison)",
            "n": 0, "n_exclus": 0, "radius_m": 1500.0, "commune_fallback": True,
            "fiabilite_raisons": ["échantillon insuffisant"]}


def test_bilan_servi_au_prix_neuf_malgre_ancien_insuffisant():
    """Validation #5 : prix neuf résolu MAIS DVF ancien insuffisant → le bilan est SERVI
    (avant : refusé sur la seule minceur de l'ancien) et ne plante pas sur l'absence de médiane."""
    ps = {"prix": 4500, "niveau": "commune", "n": 14, "label": "Estimé — médiane locale, 14 ventes"}
    b = compute_bilan(1000.0, 2000.0, _prix_insuffisant(), Hypotheses(),
                      bilan_params={"prix_m2_neuf": 4500}, prix_neuf=ps)
    assert b.fiable is True and b.fiabilite == "fiable"
    assert b.charge_fonciere is not None
    assert b.ca["central"] > 0


def test_fiabilite_derive_du_niveau_neuf_pas_de_lancien():
    """La fiabilité affichée suit le NIVEAU du prix neuf, pas la dispersion de l'ancien :
    local (secteur/commune/bassin) → fiable ; repli île → fragile."""
    assert _fiabilite_prix_neuf("commune")[0] == "fiable"
    assert _fiabilite_prix_neuf("secteur")[0] == "fiable"
    assert _fiabilite_prix_neuf("override_bassin")[0] == "fiable"
    assert _fiabilite_prix_neuf("ile_validee")[0] == "fragile"
    assert _fiabilite_prix_neuf("ile_sans_operation")[0] == "fragile"

    # ancien « fragile » n'impose plus « fragile » quand le neuf local est fiable
    anc = {**_prix_fiable(), "fiabilite": "fragile"}
    ps = {"prix": 4500, "niveau": "commune", "n": 20, "label": "Estimé — médiane locale"}
    b = compute_bilan(1000.0, 2000.0, anc, Hypotheses(),
                      bilan_params={"prix_m2_neuf": 4500}, prix_neuf=ps)
    assert b.fiabilite == "fiable"
    # neuf en repli île → fragile même si l'ancien était « fiable »
    ps_ile = {"prix": 4500, "niveau": "ile_validee", "n": None, "label": "Estimé — île"}
    b2 = compute_bilan(1000.0, 2000.0, _prix_fiable(), Hypotheses(),
                       bilan_params={"prix_m2_neuf": 4500}, prix_neuf=ps_ile)
    assert b2.fiabilite == "fragile"


def test_repli_sans_prix_neuf_comportement_historique():
    """Sans prix neuf résolu (prix_neuf None), l'ancien pilote encore : ancien insuffisant → refus
    (on ne crée pas de bilan silencieux)."""
    b = compute_bilan(1000.0, 2000.0, _prix_insuffisant(), Hypotheses())
    assert b.fiable is False and b.fiabilite == "insuffisant"


# ── P2-51 — radar : fraîcheur = date amont, jamais date de constat ────────────────────────────
def test_radar_parse_date_amont():
    """Validation #6 : Last-Modified / champ JSON ISO / epoch → date amont ; ETag opaque → None."""
    assert _parse_date_amont("Wed, 03 Jul 2024 10:00:00 GMT") == datetime(2024, 7, 3, 10, tzinfo=timezone.utc)
    assert _parse_date_amont("2024-07-03T10:00:00Z") == datetime(2024, 7, 3, 10, tzinfo=timezone.utc)
    assert _parse_date_amont("2024-07-03").date() == datetime(2024, 7, 3).date()
    assert _parse_date_amont("1719999600").tzinfo is not None            # epoch secondes
    assert _parse_date_amont('W/"opaque-etag"') is None                  # ETag → non datable
    assert _parse_date_amont('"abc123"') is None
    assert _parse_date_amont(None) is None
