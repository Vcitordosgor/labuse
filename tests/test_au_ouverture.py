"""Traitement AFFINÉ de l'ouverture AU (GPU-PILOTE, Vic 30/07) — les 3 statuts + le sous-plancher.

Verrouille la règle : fermée → déclassement ferme ; conditionnelle_operation → servie (sous-plancher
si trop petite, JAMAIS déclassée) ; conditionnelle_etat_tiers → statut inconnu. Sans DB (config YAML).
"""
from __future__ import annotations

from labuse.faisabilite.au_ouverture import (
    classify, facteur_ponderation, seuil_surface_m2, zone_regime,
)
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
    vois = {"libres": 2, "reserve": 0, "demolition": 0,
            "atteint_sans_demo": True, "atteint_avec_demo": True}
    statut, mention = classify("97423", "1AUc", 1000, voisins=vois)
    assert statut == AU_SOUS_PLANCHER
    assert AU_SOUS_PLANCHER not in DECLASSE_LABELS          # servie
    assert "assemblage" in mention and "1500 m²" in mention  # 2500-1000 manquants
    assert "2 voisine(s) libre(s)" in mention                # la SOLUTION est servie
    # assez grande → servie conditionnelle (pas sous-plancher)
    assert classify("97423", "1AUc", 3000)[0] == "conditionnelle_operation"


def test_mention_distingue_demolition():
    # voisines nécessitant démolition → mention le DIT (dette #4 : le bâti nuance, pas de silence)
    vois = {"libres": 0, "reserve": 0, "demolition": 3,
            "atteint_sans_demo": False, "atteint_avec_demo": True}
    _, mention = classify("97413", "AUc", 2000, voisins=vois)
    assert "à démolir" in mention                            # jamais silencé (dette #4)
    assert "libre" not in mention                            # ne dit JAMAIS « libre » d'une bâtie


def test_densite_seule_pas_de_seuil():
    # La Possession AUAv : densité 50 SANS min-logements → pas de seuil → jamais sous-plancher
    assert seuil_surface_m2(zone_regime("97408", "AUAv") or {}) is None
    assert classify("97408", "AUAv", 300)[0] == "conditionnelle_operation"


def test_prefixe_le_plus_specifique():
    # « 1AUc » doit matcher le préfixe « 1AUc » (min_log 5), pas « AUc » d'une autre commune
    assert zone_regime("97423", "1AUc")["densite_log_ha"] == 20


def test_zone_non_calibree_aucun_marquage():
    # commune hors config → None (comportement d'avant, rétro-compatible).
    # M-S : 97404 (L'Étang-Salé) a été CALIBRÉE depuis (M32 Phase C) → n'est plus un exemple valide
    # de commune non calibrée. On prend 97417 (Saint-Philippe, RNU, aucun zonage) : hors config par
    # nature, jamais calibrable. Le code est juste (97404 EST calibrée) — c'est l'exemple qui datait.
    assert classify("97417", "AUa", 3000) is None
    assert classify("99999", "AUa", 3000) is None


def test_facteur_ponderation_option_b():
    """Option B (Vic 04/08) : facteur = 1 − manque/seuil = surface/seuil, sur le MÊME seuil
    que la mention. Un manque de 94 % pèse 94 % ; un manque de 10 % pèse 10 %."""
    seuil = seuil_surface_m2(zone_regime("97413", "AUc"))          # Saint-Leu AUc : 6667 m²
    f = facteur_ponderation("97413", "AUc", seuil * 0.06)          # manque 94 %
    assert abs(f - 0.06) < 1e-9
    f = facteur_ponderation("97413", "AUc", seuil * 0.90)          # manque 10 %
    assert abs(f - 0.90) < 1e-9
    # au-dessus du seuil → pas de pondération (None = signal inchangé)
    assert facteur_ponderation("97413", "AUc", seuil + 1) is None
    # zone sans plancher (densité seule) / non calibrée / fermée → None
    assert facteur_ponderation("97408", "AUAv", 300) is None       # densité seule
    assert facteur_ponderation("99999", "AUa", 300) is None        # non calibrée
    assert facteur_ponderation("97423", "AUs", 300) is None        # fermée ≠ conditionnelle
    # surfaces dégénérées → None (jamais un facteur négatif ou > 1)
    assert facteur_ponderation("97413", "AUc", 0) is None
    assert facteur_ponderation("97413", "AUc", None) is None
