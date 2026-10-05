"""DASHBOARD-FIX-1 — points 4 (verrous datés / à rejouer) et 6 (un seul moteur « jamais vérifiée »)."""
from labuse import circuit_etats as CE
from labuse import etats_sources as ES
from labuse.api import dashboard as D


# ── point 4 — comparaison de dates (socle de « à rejouer ») ──────────────────────────────────
def test_apres_compare_les_timestamps():
    assert D._apres("2026-10-05T12:00:00+00:00", "2026-09-26T08:00:00+00:00") is True   # bascule après
    assert D._apres("2026-09-20T12:00:00+00:00", "2026-09-26T08:00:00+00:00") is False  # bascule avant
    # fuseaux différents mais même instant comparés correctement (parse ISO)
    assert D._apres("2026-10-05T15:35:00+04:00", "2026-10-05T11:00:00+00:00") is True


# ── point 6 — un seul prédicat « surveillée », partagé par les deux moteurs ───────────────────
def test_est_surveillee_predicat_unique():
    assert ES.est_surveillee("api", None) is True
    assert ES.est_surveillee("temoin", True) is True
    assert ES.est_surveillee("api", False) is False     # sonde désactivée
    assert ES.est_surveillee("rappel", None) is False   # rappel manuel ≠ sonde amont
    assert ES.est_surveillee(None, None) is False        # pas de méthode


def test_jamais_verifiee_meme_verdict_dans_les_deux_moteurs():
    """Sur les mêmes cas, circuit_etats et etats_sources classent « jamais vérifiée » IDENTIQUEMENT :
    SURVEILLÉE + jamais passée → jamais ; NON surveillée → PAS jamais (à jour / non surveillée)."""
    # 1) surveillée (sonde api active), aucun statut → JAMAIS vérifiée des deux côtés
    res_reservoir = {"veille": {"methode": "api", "statut": None, "passage": None}}
    row_source = {"veille_methode": "api", "veille_statut": None, "veille_actif": True}
    assert CE.etat_reservoir(res_reservoir) == ("gris", "jamais vérifiée")
    assert ES.etat_source(row_source)["etat"] == "jamais_verifiee"

    # 2) NON surveillée (aucune sonde amont) → ni l'un ni l'autre ne dit « jamais vérifiée »
    res_non = {"veille": {"statut": None, "passage": None}}          # pas de méthode
    row_non = {"veille_methode": None, "veille_statut": None, "veille_actif": None}
    assert CE.etat_reservoir(res_non)[1] != "jamais vérifiée"
    assert ES.etat_source(row_non)["etat"] != "jamais_verifiee"

    # 3) surveillée mais DÉSACTIVÉE → non plus « jamais vérifiée »
    res_off = {"veille": {"methode": "api", "actif": False, "statut": None}}
    row_off = {"veille_methode": "api", "veille_actif": False, "veille_statut": None}
    assert CE.etat_reservoir(res_off)[1] != "jamais vérifiée"
    assert ES.etat_source(row_off)["etat"] != "jamais_verifiee"
