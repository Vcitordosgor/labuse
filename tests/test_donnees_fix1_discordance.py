"""Le badge « Sources discordantes » compare des hauteurs de MÊME NATURE.

DONNEES-FIX-1 lot A : on ne compare plus le FAÎTAGE LiDAR au simple « BD TOPO ≈ égout ».
FAISA-REGLES-1 (A-004) : la hauteur BD TOPO est une hauteur de BÂTIMENT (haut du bâti, ≈ faîtage) ; elle
doit tomber dans l'ENVELOPPE mesurée [égout, faîtage] du LiDAR. Discordance UNIQUEMENT si BD TOPO sort de
l'enveloppe (au-dessus du faîtage ou sous l'égout), JAMAIS le simple « faîtage > égout » (définition d'un
toit, qui comparait deux grandeurs différentes et allumait ~16 % des bâtis). L'écart égout↔BD TOPO reste
fourni en annexe (nature différente), mais ne pilote plus le verdict.
"""
from labuse.faisabilite.hauteur_lidar import (
    PLAFOND_FAITAGE_ABERRANT_M,
    SEUIL_BDTOPO_SOUS_EGOUT_M,
    SEUIL_ECART_EGOUT_BDTOPO_M,
    SEUIL_FAITAGE_SOUS_BDTOPO_M,
    discordance_hauteur,
)


def test_bz1065_plus_badgee():
    """BZ1065 (R+2/R+3, LiDAR juste) : faîtage 10,3 > BD TOPO 4,2 était badgé à tort. BD TOPO 4,2 ∈
    [égout 3,6 ; faîtage 10,3] → cohérent → plus de badge."""
    d = discordance_hauteur({"faitage_m": 10.3, "egout_m": 3.6, "hauteur_bdtopo_m": 4.2,
                             "ecart_faitage_bdtopo_m": 6.1})
    assert d["discordante"] is False
    assert d["motif"] is None
    assert d["ecart_egout_bdtopo_m"] == -0.6


def test_aberration_faitage_toujours_badgee():
    """Les 2 aberrations de l'audit (faîtage 53 401 m = bug de coordonnée) captées par le PLAFOND faîtage."""
    d = discordance_hauteur({"faitage_m": 53401.6, "egout_m": 4.3, "hauteur_bdtopo_m": 6.1,
                             "ecart_faitage_bdtopo_m": 53395.5})
    assert d["discordante"] is True
    assert d["motif"] == "faîtage aberrant"


def test_faitage_negatif_est_aberrant():
    """MNS < MNT → faîtage ≤ 0 : mesure cassée, à écarter."""
    d = discordance_hauteur({"faitage_m": -11.6, "egout_m": -15.7, "hauteur_bdtopo_m": 4.5})
    assert d["discordante"] is True
    assert d["motif"] == "faîtage aberrant"


def test_bdtopo_au_dessus_du_faitage():
    """FAISA-REGLES-1 (A-004) — BD TOPO AU-DESSUS du faîtage mesuré (rien n'est plus haut que le point
    haut du toit) : comparaison de MÊME nature (faîtage ↔ BD TOPO), écart > seuil 3 m → badge."""
    d = discordance_hauteur({"faitage_m": 10.0, "egout_m": 4.0, "hauteur_bdtopo_m": 15.5,
                             "ecart_faitage_bdtopo_m": -5.5})
    assert d["discordante"] is True
    assert d["motif"] == "BD TOPO au-dessus du faîtage mesuré"


def test_bdtopo_sous_l_egout():
    """FAISA-REGLES-1 (A-004) — BD TOPO SOUS l'égout mesuré (la hauteur déclarée ne peut être sous le
    bord de toit) : écart égout − BD TOPO > seuil 3 m → badge."""
    d = discordance_hauteur({"faitage_m": 20.0, "egout_m": 12.0, "hauteur_bdtopo_m": 5.0,
                             "ecart_faitage_bdtopo_m": 15.0})
    assert d["discordante"] is True
    assert d["motif"] == "BD TOPO sous l'égout mesuré"


def test_bdtopo_dans_enveloppe_pas_de_badge():
    """FAISA-REGLES-1 (A-004) — BD TOPO cohérente DANS l'enveloppe [égout, faîtage] : jamais badgée, même
    si l'écart ÉGOUT↔BD TOPO est grand (toit en pente / R+n : faîtage ≫ égout est NORMAL, pas une erreur —
    fin des ~16 % de faux positifs). Cas type : égout 5,6, faîtage 28, BD TOPO 28,9 (≈ faîtage)."""
    d = discordance_hauteur({"faitage_m": 28.0, "egout_m": 5.6, "hauteur_bdtopo_m": 28.9,
                             "ecart_faitage_bdtopo_m": -0.9})
    assert d["discordante"] is False
    assert d["motif"] is None
    assert d["ecart_egout_bdtopo_m"] == -23.3   # grand écart égout↔BD TOPO, mais nature différente → ignoré


def test_sans_mesure_lidar_jamais_discordant():
    """Repli BD TOPO (pas de LiDAR) ou None : jamais de badge (rien à comparer)."""
    assert discordance_hauteur(None)["discordante"] is False
    assert discordance_hauteur({"faitage_m": None, "egout_m": None,
                                "hauteur_bdtopo_m": None})["discordante"] is False


def test_seuils_documentes():
    """Les constantes valent ce que le rapport justifie (garde contre une dérive muette)."""
    assert SEUIL_FAITAGE_SOUS_BDTOPO_M == 3.0
    assert SEUIL_BDTOPO_SOUS_EGOUT_M == 3.0
    assert PLAFOND_FAITAGE_ABERRANT_M == 60.0
    assert SEUIL_ECART_EGOUT_BDTOPO_M == 15.0   # conservée pour l'annexe (écart égout↔BD TOPO servi)
