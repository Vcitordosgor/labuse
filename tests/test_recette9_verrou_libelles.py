"""RECETTE-9 T10 — le verrou LIBELLÉS n'est plus une liste noire figée : il est DÉRIVÉ des
vocabulaires contrôlés (rattachement à la source de vérité). Un nouveau code snake_case / EN
MAJUSCULES / variante sans-accent d'un libellé est couvert AUTOMATIQUEMENT — plus de maintenance.
"""
from __future__ import annotations

from labuse.exports import provenance as P


def test_derive_des_vocabulaires_pas_une_liste_figee():
    # la liste EST le produit de la dérivation (rattachée aux vocabulaires), pas une constante à la main
    derive = P._codes_techniques_derives()
    assert P._CODES_TECHNIQUES == (derive | P._SUPPLEMENT)


def test_couvre_automatiquement_les_codes_des_vocabulaires():
    from labuse.enums import CascadeVerdict, SourceResultStatus
    from labuse.scoring.tiers_client import CORRESPONDANCE_LEGACY
    codes = P._CODES_TECHNIQUES
    # tout code snake_case d'un vocabulaire y est (ex. declassements, en_cours) — sans l'avoir listé
    for c in CORRESPONDANCE_LEGACY:
        if "_" in c:
            assert c in codes, c
    assert "en_cours" in codes                       # SourceResultStatus.EN_COURS.value — auto
    assert CascadeVerdict.HARD_EXCLUDE.value in codes


def test_ne_prend_pas_les_mots_francais_de_prose():
    # les mots français légitimes (y compris des codes de scénario qui SONT des mots) ne sont pas pris
    for mot in ("reconstruction", "revente", "division", "chaude", "faible", "moyen", "fort", "repondu"):
        assert mot not in P._CODES_TECHNIQUES, mot


def test_mord_toujours_sur_les_identifiants_techniques():
    bad = "<p>Scénario surelevation ; palier sans_signal ; verdict HARD_EXCLUDE ; en_cours.</p>"
    trouves = {e["libelle"] for e in P.libelles_hors_registre("faux/doc", bad)}
    assert {"surelevation", "sans_signal", "HARD_EXCLUDE", "en_cours"} <= trouves, trouves
    good = "<p>Scénario Surélévation ; reconstruction ; palier Sans signal ; verdict Écartée.</p>"
    assert not P.libelles_hors_registre("faux/doc", good)
