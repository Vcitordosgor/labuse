"""DONNEES-FIX-1 lot A — le badge « Sources discordantes » compare la BONNE grandeur.

Règle UNIQUE (`discordance_hauteur`) lue par la fiche §Bâti ET la marge en hauteur (Potentiel).
Avant : on comparait le FAÎTAGE LiDAR (p99) à BD TOPO (≈ égout) → 52 759 bâtis badgés à tort.
Après : on compare l'ÉGOUT LiDAR à BD TOPO (même grandeur) + un plafond sur le faîtage aberrant.
"""
from labuse.faisabilite.hauteur_lidar import (
    discordance_hauteur,
    SEUIL_ECART_EGOUT_BDTOPO_M,
    PLAFOND_FAITAGE_ABERRANT_M,
)


def test_bz1065_plus_badgee():
    """BZ1065 (R+2/R+3, LiDAR juste) : faîtage 10,3 > BD TOPO 4,2 était badgé à tort. L'égout 3,6
    ≈ BD TOPO 4,2 → même grandeur cohérente → plus de badge."""
    d = discordance_hauteur({"faitage_m": 10.3, "egout_m": 3.6, "hauteur_bdtopo_m": 4.2,
                             "ecart_faitage_bdtopo_m": 6.1})
    assert d["discordante"] is False
    assert d["motif"] is None
    assert d["ecart_egout_bdtopo_m"] == -0.6


def test_aberration_faitage_toujours_badgee():
    """Les 2 aberrations de l'audit (faîtage 53 401 m = bug de coordonnée) : l'égout est normal
    (−1,8 m), donc invisible à la comparaison égout↔BD TOPO — c'est le PLAFOND faîtage qui les capte."""
    d = discordance_hauteur({"faitage_m": 53401.6, "egout_m": 4.3, "hauteur_bdtopo_m": 6.1,
                             "ecart_faitage_bdtopo_m": 53395.5})
    assert d["discordante"] is True
    assert d["motif"] == "faîtage aberrant"


def test_faitage_negatif_est_aberrant():
    """MNS < MNT → faîtage ≤ 0 : mesure cassée, à écarter (56 lignes en base)."""
    d = discordance_hauteur({"faitage_m": -11.6, "egout_m": -15.7, "hauteur_bdtopo_m": 4.5})
    assert d["discordante"] is True
    assert d["motif"] == "faîtage aberrant"


def test_discordance_egout_meme_grandeur():
    """BD TOPO dit 28,9 m mais LiDAR mesure ~6 m au faîtage ET à l'égout → une source est fausse
    sur la MÊME grandeur (écart 23,3 m > 15 m)."""
    d = discordance_hauteur({"faitage_m": 6.4, "egout_m": 5.6, "hauteur_bdtopo_m": 28.9,
                             "ecart_faitage_bdtopo_m": -22.5})
    assert d["discordante"] is True
    assert d["motif"] == "égout ↔ BD TOPO"
    assert d["ecart_egout_bdtopo_m"] == -23.3


def test_ecart_egout_sous_seuil_pas_de_badge():
    """Un écart égout↔BD TOPO dans le bruit normal (≤ ~8 m) n'est PAS discordant."""
    d = discordance_hauteur({"faitage_m": 12.0, "egout_m": 8.0, "hauteur_bdtopo_m": 3.5,
                             "ecart_faitage_bdtopo_m": 8.5})
    assert abs(d["ecart_egout_bdtopo_m"]) < SEUIL_ECART_EGOUT_BDTOPO_M
    assert d["discordante"] is False


def test_sans_mesure_lidar_jamais_discordant():
    """Repli BD TOPO (pas de LiDAR) ou None : jamais de badge (rien à comparer)."""
    assert discordance_hauteur(None)["discordante"] is False
    assert discordance_hauteur({"faitage_m": None, "egout_m": None,
                                "hauteur_bdtopo_m": None})["discordante"] is False


def test_seuils_documentes():
    """Les deux constantes valent ce que le rapport justifie (garde contre une dérive muette)."""
    assert SEUIL_ECART_EGOUT_BDTOPO_M == 15.0
    assert PLAFOND_FAITAGE_ABERRANT_M == 60.0
