"""ETUDE-STATIONNEMENT-FIX-2 (LOT 1) — BANC D'EXÉCUTION du stationnement.

La preuve n'est plus « la citation est présente » mais « le nombre de places calculé est JUSTE ». Chaque cas
porte le nombre attendu LU À LA MAIN sur l'image de la page officielle par le relecteur indépendant (contre-
audit en lecture seule), et le compare au calcul du moteur (`BaremeStationnement.exiger`). Détail exigé :
résidents, visiteurs, places publiques à part, arrondi, seuil, plafond.

Programmes types (mandat) : maison T4 120 m² (individuel) ; collectif privé 20 × T3 = 1 400 m² ; le même en
logement aidé ; collectif mixte 10 × 110 m² + 10 × 30 m². Les 15 zones recalculées par le relecteur figurent
ici ; 6 donnaient un nombre faux avant ce lot (Saint-Paul, Saint-Louis, Saint-Leu, Trois-Bassins, Saint-Joseph,
+ la maison seule à Salazie/Sainte-Marie/Sainte-Suzanne).
"""
from types import SimpleNamespace

import pytest

from labuse.implantation import regles as R


def _maison():
    return [SimpleNamespace(pieces=4, surface_m2=120.0)]


def _collectif(n=20, pieces=3, surf=70.0):
    return [SimpleNamespace(pieces=pieces, surface_m2=surf) for _ in range(n)]


# (insee, zone, maison attendue [individuel], collectif privé attendu [20×T3])  — valeurs LUES SUR L'IMAGE.
BANC = [
    ("97415", "U2c", 2, 44),   # Saint-Paul : 40 + 4 visiteurs (1/5) — visiteurs étaient omis
    ("97416", "Ud", 1, 18),    # Saint-Pierre : 1 place / 75 m², tranches complètes
    ("97411", "Uj", 1, 20),    # Saint-Denis
    ("97407", "Uc", 3, 20),    # Le Port
    ("97414", "UA", 2, 40),    # Saint-Louis : 40 privées À DESSINER (+ 10 publiques à part)
    ("97422", "Ud", 1, 30),    # Le Tampon : opération > 5 → 1,5/logt
    ("97410", "Ua", 1, 24),    # Saint-Benoît
    ("97403", "Ua", 3, 44),    # Entre-Deux
    ("97421", "UA", 2, 40),    # Salazie : maison seule = tranche > 50 m² (pas « non vérifié »)
    ("97413", "UD", 2, 30),    # Saint-Leu : collectif par pièces (3-5p = 1,5) — était flat 2
    ("97423", "UC", 1, 40),    # Trois-Bassins : maison = 1,5 arrondi INFÉRIEUR = 1 — était 2
    ("97401", "Ub", 2, 40),    # Les Avirons
    ("97418", "UB", 2, 20),    # Sainte-Marie : maison seule via tranche
    ("97420", "UB", 2, 40),    # Sainte-Suzanne : maison seule via tranche
    ("97412", "U2", 1, 20),    # Saint-Joseph : visiteurs « 1/10 » visent l'HÉBERGEMENT, pas l'ordinaire
]


@pytest.mark.parametrize("insee,zone,maison,collectif", BANC)
def test_banc_maison_et_collectif(insee, zone, maison, collectif):
    b = R.charger(insee, zone).stationnement
    assert b.validee, f"{insee}/{zone} : barème non servi"
    em = b.exiger(_maison(), destination="individuel")
    ec = b.exiger(_collectif(), destination="collectif")
    assert em.places == maison, f"{insee}/{zone} maison : {em.places} ≠ {maison} attendu ({em.formule})"
    assert ec.places == collectif, f"{insee}/{zone} collectif : {ec.places} ≠ {collectif} attendu ({ec.formule})"


def test_saint_louis_places_publiques_a_part():
    """Saint-Louis UA, 20 logements : 40 places PRIVÉES à dessiner + 10 places PUBLIQUES (hors parcelle),
    comptées séparément — elles ne gonflent pas le nombre à dessiner."""
    b = R.charger("97414", "UA").stationnement
    ec = b.exiger(_collectif(20), destination="collectif")
    assert ec.places == 40 and ec.places_publiques == 10


def test_saint_joseph_visiteurs_hebergement_pas_ordinaire():
    """Saint-Joseph : la ligne « 1 place / 10 logements » vise les établissements d'hébergement (CASF), pas
    le logement ordinaire → 20 logements ordinaires = 20 places (était 22)."""
    b = R.charger("97412", "U2").stationnement
    assert b.exiger(_collectif(20), destination="collectif").places == 20


def test_petite_ile_aide_pas_dispense():
    """Petite-Île : la dispense de place est réservée au LLTS, pas à tout l'aidé → 20 logements aidés
    (hors LLTS) = 20 places (était 0)."""
    b = R.charger("97405", "UB").stationnement
    assert b.exiger(_collectif(20), destination="social").places == 20


def test_trois_bassins_maison_arrondi_inferieur():
    """Trois-Bassins : 1,5 place/logt « arrondi à l'entier inférieur » (en-tête) → 1 maison = 1 (était 2)."""
    b = R.charger("97423", "UC").stationnement
    assert b.exiger(_maison(), destination="individuel").places == 1


def test_saint_leu_collectif_par_pieces():
    """Saint-Leu : habitat collectif par pièces (3-5 pièces = 1,5) → 20 T3 = 30 (était 40, barème individuel)."""
    b = R.charger("97413", "UD").stationnement
    assert b.exiger(_collectif(20), destination="collectif").places == 30
