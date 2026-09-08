"""Témoin CIRCUIT-4 — prix d'achat historique de la parcelle (fait foncier D-a, choix_assume).

Le calcul est un PASSE-PLAT : la dernière mutation DVF rattachée à l'IDU, rendue TELLE QUELLE si
elle porte un montant, sinon « non disponible » (jamais un 0 € inventé, jamais une médiane). On
recompose la règle INDÉPENDAMMENT (autre expression que le collecteur) et on prouve trois choses :
la valeur servie est l'objet mutation lui-même (montant/date non recalculés), l'absence rend None,
et une mutation sans montant est refusée (garde anti-faux-zéro)."""
from __future__ import annotations

from labuse.exports.collecte import _c_prix_achat


def _attendu(fiche: dict):
    """Réimplémentation indépendante de la règle D-a : dernière mutation DVF de la parcelle,
    passée telle quelle si (et seulement si) elle porte un montant non nul."""
    dvf = fiche.get("dvf_parcelle")
    if not isinstance(dvf, dict):
        return None
    mut = dvf.get("derniere_mutation")
    if not isinstance(mut, dict):
        return None
    return mut if mut.get("valeur") else None


def test_passe_plat_dvf_de_la_parcelle():
    mut = {"valeur": 342000, "date": "2019-06-14"}
    fiche = {"dvf_parcelle": {"derniere_mutation": mut, "secteur": {"mediane_prix_m2": 2265}}}
    out = _c_prix_achat(None, "974110000A1234", fiche)
    # servi TEL QUEL : l'objet mutation lui-même, montant et date jamais recalculés ni le secteur
    assert out is mut
    assert out == {"valeur": 342000, "date": "2019-06-14"}
    assert out == _attendu(fiche)


def test_non_disponible_si_aucune_mutation():
    # parcelle jamais mutée seule : dvf_parcelle absent, vide, ou derniere_mutation None → None
    for fiche in ({}, {"dvf_parcelle": {}}, {"dvf_parcelle": {"derniere_mutation": None}},
                  {"dvf_parcelle": None}):
        assert _c_prix_achat(None, "974110000A0001", fiche) is None
        assert _attendu(fiche) is None


def test_pas_de_faux_zero_si_mutation_sans_montant():
    # une mutation rattachée mais sans montant (valeur 0 ou manquante) n'invente pas un « 0 € »
    for mut in ({"valeur": 0, "date": "2020-01-01"}, {"date": "2020-01-01"}):
        fiche = {"dvf_parcelle": {"derniere_mutation": mut}}
        assert _c_prix_achat(None, "974110000A0002", fiche) is None
        assert _attendu(fiche) is None
