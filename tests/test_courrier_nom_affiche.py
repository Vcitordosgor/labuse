"""OUTILS-LOT-4 (pt 5) — le destinataire d'un pli nomme la personne morale AVEC sa forme juridique
(« SARL MOUTOUSSAMY EMILE »), sans la coller aux entités publiques déjà nommées en entier, ni la
doubler quand la dénomination la porte déjà. Tests PURS de `_nom_affiche` (pas de DB)."""
from __future__ import annotations

from labuse.courrier_adressage import _nom_affiche


def test_forme_commerciale_prefixee():
    # une SARL/SCI… se nomme « FORME DÉNOMINATION » (sinon « MOUTOUSSAMY EMILE » se lit comme une personne).
    assert _nom_affiche("SARL", "MOUTOUSSAMY EMILE") == "SARL MOUTOUSSAMY EMILE"
    assert _nom_affiche("SAS", "COUVEE D'OR") == "SAS COUVEE D'OR"


def test_forme_deja_dans_la_denomination_pas_de_doublon():
    assert _nom_affiche("SCI", "SCI DESTINO") == "SCI DESTINO"
    assert _nom_affiche("sci", "SCI DESTINO") == "SCI DESTINO"


def test_entites_publiques_ou_institutionnelles_non_prefixees():
    # COMMUNE / DÉPARTEMENT / SEM… se nomment déjà en entier : on ne colle pas leur code.
    assert _nom_affiche("COM", "COMMUNE DE SAINT PAUL") == "COMMUNE DE SAINT PAUL"
    assert _nom_affiche("DEPT", "DEPARTEMENT DE LA REUNION") == "DEPARTEMENT DE LA REUNION"
    assert _nom_affiche("SEM", "SOCIETE IMMOBILIERE DEPARTEMENT REUNION") == "SOCIETE IMMOBILIERE DEPARTEMENT REUNION"
    assert _nom_affiche("AUPM", "UNION DES COPROPRIETAIRES") == "UNION DES COPROPRIETAIRES"


def test_forme_absente_renvoie_la_denomination():
    assert _nom_affiche(None, "MOUTOUSSAMY EMILE") == "MOUTOUSSAMY EMILE"
    assert _nom_affiche("", "MOUTOUSSAMY EMILE") == "MOUTOUSSAMY EMILE"
