"""CIRCUIT-4 lot 4 — la GARDE des exemples témoins : toute fiche « conforme » ou « choix_assume »
pointe un test d'implémentation INDÉPENDANTE qui existe réellement (fichier + fonction) ; les
trois exceptions assumées sont listées (documentées au compte-rendu). Le xfail de l'écart E1 est
présent et motivé (4.2)."""
from __future__ import annotations

import re
from pathlib import Path

from labuse import regles

#: gaps ASSUMÉS (documentés au CR lot 4) : témoin non constructible sans le builder gelé / la
#: source réseau — la fiche reste honnête (choix écrit), le témoin viendra avec son chantier.
SANS_TEMOIN_ASSUME = {"divisible_classe", "ecart_candidat_pct", "evenements_proprietaire_liste"}


def test_tout_conforme_ou_choix_a_son_temoin():
    regles.charger()
    manquants = []
    for f in regles.TOUTES:
        if f.verdict not in ("conforme", "choix_assume"):
            continue
        if f.donnees[0] in SANS_TEMOIN_ASSUME:
            assert not f.exemple_temoin
            continue
        if not f.exemple_temoin:
            manquants.append(f.donnees[0])
            continue
        chemin, _, fonction = f.exemple_temoin.partition("::")
        p = Path(chemin)
        if not p.exists():
            manquants.append(f"{f.donnees[0]} → fichier absent {chemin}")
            continue
        src = p.read_text()
        nom = fonction.split("[")[0]
        if nom and not re.search(rf"def {re.escape(nom)}\b", src):
            manquants.append(f"{f.donnees[0]} → test absent {f.exemple_temoin}")
    assert not manquants, f"fiches sans exemple témoin réel : {manquants}"


def test_xfail_ecart_e1_present():
    src = Path("tests/regles/test_distance_knn.py").read_text()
    assert "xfail" in src and "E1" in src and "800" in src


def test_les_temoins_sont_dans_la_suite_normale():
    # tests/regles est collecté par pytest (testpaths=tests) — un fichier au moins par classe
    assert Path("tests/regles/test_taxe_amenagement.py").exists()      # regle_externe
    assert Path("tests/regles/test_sector_price.py").exists()          # methode_standard
    assert Path("tests/regles/test_compteurs_simples.py").exists()     # choix_labuse
