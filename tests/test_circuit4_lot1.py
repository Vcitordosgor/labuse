"""CIRCUIT-4 lot 1 — la GARDE de l'inventaire des calculs (règle 1.3 du mandat) :
· toute donnée du registre avec calcul == "moteur" a UNE fiche de règle (ni zéro ni deux) ;
· toute fonction publique de `registre/moteurs/` est couverte par ≥ 1 fiche ;
· toute fiche pointe des données EXISTANTES du registre ;
· un verdict « conforme »/« partiel » sans extrait daté est refusé à la construction (verrou testé) ;
· chaque classe/verdict est dans son énumération."""
from __future__ import annotations

import pytest

from labuse import regles
from labuse.registre import CHIFFRES


@pytest.fixture(scope="module")
def fiches():
    return regles.charger()


def test_toute_donnee_moteur_a_sa_fiche(fiches):
    moteur_ids = {cid for cid, d in CHIFFRES.items() if d.calcul == "moteur"}
    sans_fiche = moteur_ids - set(fiches)
    assert not sans_fiche, f"données calculées SANS fiche de règle : {sorted(sans_fiche)}"


def test_aucune_fiche_sur_donnee_inconnue(fiches):
    inconnues = set(fiches) - set(CHIFFRES)
    assert not inconnues, f"fiches sur des données hors registre : {sorted(inconnues)}"


def test_toute_fonction_moteurs_pkg_couverte(fiches):
    couverture = regles.couverture_moteurs_pkg()
    sans = sorted(f for f, l in couverture.items() if not l)
    assert not sans, f"fonctions de registre/moteurs/ sans fiche de règle : {sans}"


def test_enumerations_et_champs(fiches):
    for f in regles.TOUTES:
        assert f.classe in regles.CLASSES and f.verdict in regles.VERDICTS
        assert f.donnees and f.formule_codee.strip() and f.entrees
        assert f.fonction.strip(), f.donnees
        # une fiche choix_labuse porte toujours sa définition (verrou du dataclass, revérifié)
        if f.classe == "choix_labuse":
            assert (f.choix or "").strip()


def test_verrou_conforme_sans_extrait():
    """Règle 2 du mandat : « conforme » sans passage cité daté est REFUSÉ à la construction."""
    with pytest.raises(ValueError, match="sans extrait"):
        regles.FicheRegle(
            donnees=("x",), formule_codee="f", entrees=("t",), classe="regle_externe",
            fonction="f.py:f", verdict="conforme", reference=None)
    with pytest.raises(ValueError, match="sans extrait"):
        regles.FicheRegle(
            donnees=("x",), formule_codee="f", entrees=("t",), classe="regle_externe",
            fonction="f.py:f", verdict="conforme",
            reference=regles.Reference(titre="t", article="a", url="u", version="", extrait=""))


def test_verrou_ecart_sans_description():
    with pytest.raises(ValueError, match="sans écart"):
        regles.FicheRegle(
            donnees=("x",), formule_codee="f", entrees=("t",), classe="regle_externe",
            fonction="f.py:f", verdict="ecart", ecart=None)


def test_un_calcul_une_fiche(fiches):
    """Une donnée n'est jamais couverte par deux fiches (déjà refusé par declarer ; on prouve
    l'invariant sur l'état chargé : chaque id apparaît dans exactement une fiche)."""
    vues: dict[str, int] = {}
    for f in regles.TOUTES:
        for d in f.donnees:
            vues[d] = vues.get(d, 0) + 1
    doubles = {d: n for d, n in vues.items() if n > 1}
    assert not doubles, f"données couvertes deux fois : {doubles}"
