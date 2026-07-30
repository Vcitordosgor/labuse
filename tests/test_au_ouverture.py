"""Traitement AFFINÉ de l'ouverture AU (GPU-PILOTE, Vic 30/07) — les 3 statuts + le sous-plancher.

Verrouille la règle : fermée → déclassement ferme ; conditionnelle_operation → servie (sous-plancher
si trop petite, JAMAIS déclassée) ; conditionnelle_etat_tiers → statut inconnu. Sans DB (config YAML).
"""
from __future__ import annotations

from labuse.faisabilite.au_ouverture import classify, seuil_surface_m2, zone_regime
from labuse.faisabilite.constructibilite import (
    DECLASSE_AU_FERMEE, AU_SOUS_PLANCHER, DECLASSE_AU_STATUT_INCONNU, DECLASSE_LABELS,
)


def test_fermee_declasse_ferme():
    assert classify("97423", "AUs", 5000)[0] == DECLASSE_AU_FERMEE
    assert classify("97408", "AUST", 9000)[0] == DECLASSE_AU_FERMEE
    # declasse_au_fermee EST un tier de déclassement ; au_sous_plancher NON.
    assert DECLASSE_AU_FERMEE in DECLASSE_LABELS
    assert AU_SOUS_PLANCHER not in DECLASSE_LABELS


def test_phasage_reste_inconnu():
    # 2AU (phasage 2AU→1AU) = vrai inconnu, jamais servie avec mention « ouverte »
    assert classify("97423", "2AUb", 5000)[0] == DECLASSE_AU_STATUT_INCONNU


def test_seuil_surface():
    # Les Trois-Bassins 1AUc : 5 log ÷ 20 log/ha = 2 500 m²
    assert round(seuil_surface_m2(zone_regime("97423", "1AUc"))) == 2500
    # Saint-Leu AUc : 10 ÷ 15 = 6 667 m²
    assert round(seuil_surface_m2(zone_regime("97413", "AUc"))) == 6667


def test_sous_plancher_servie_jamais_declassee():
    # trop petite → au_sous_plancher (SERVIE, pas dans DECLASSE_LABELS)
    statut, mention = classify("97423", "1AUc", 1000, voisins_assemblables=2)
    assert statut == AU_SOUS_PLANCHER
    assert AU_SOUS_PLANCHER not in DECLASSE_LABELS          # servie
    assert "assemblage" in mention and "1500 m²" in mention  # 2500-1000 manquants
    assert "2 parcelle(s) voisine(s)" in mention             # la SOLUTION est servie
    # assez grande → servie conditionnelle (pas sous-plancher)
    assert classify("97423", "1AUc", 3000)[0] == "conditionnelle_operation"


def test_densite_seule_pas_de_seuil():
    # La Possession AUAv : densité 50 SANS min-logements → pas de seuil → jamais sous-plancher
    assert seuil_surface_m2(zone_regime("97408", "AUAv") or {}) is None
    assert classify("97408", "AUAv", 300)[0] == "conditionnelle_operation"


def test_prefixe_le_plus_specifique():
    # « 1AUc » doit matcher le préfixe « 1AUc » (min_log 5), pas « AUc » d'une autre commune
    assert zone_regime("97423", "1AUc")["densite_log_ha"] == 20


def test_zone_non_calibree_aucun_marquage():
    # commune hors config → None (comportement d'avant, rétro-compatible)
    assert classify("97404", "AUa", 3000) is None
    assert classify("99999", "AUa", 3000) is None
