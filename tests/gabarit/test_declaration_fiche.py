"""GABARIT-5 lot B — le gabarit déclaré dans la fiche (registre + déclarations).

Vérifie que les données du gabarit sont au registre, servies par un robinet, et déclarées à la
section « Potentiel » avec extracteur et source (pas de câble muet). Aucune DB.
"""
from __future__ import annotations

from labuse import registre
from labuse.registre import declarations as DEC

GAB_IDS = ("gabarit_implantation_m2", "gabarit_emprise_plafond_m2", "gabarit_hauteur_m",
           "gabarit_couverture_verdict", "gabarit_motif_blocage", "gabarit_plan_2d")


def test_registre_integre():
    assert registre.verifier() == []


def test_donnees_gabarit_au_registre_et_servies():
    from labuse.registre.chiffres import CHIFFRES
    from labuse.registre.robinets import ROBINETS
    servis = {c for r in ROBINETS.values() for c in r.chiffres}
    for cid in GAB_IDS:
        assert cid in CHIFFRES, f"{cid} absent du registre"
        assert cid in servis, f"{cid} servi par aucun robinet"


def test_lignes_gabarit_declarees_en_potentiel_avec_extracteur():
    from labuse.exports.robinet_fiche import EXTRACTEURS
    surfaces, _gen = DEC.charger()
    gab = [s for s in surfaces if s.surface == "fiche_parcelle_gabarit"]
    assert gab, "surface fiche_parcelle_gabarit non chargée"
    assert gab[0].fiche_section == "potentiel"
    declares = {ln.quoi for ln in gab[0].donnees}
    for cid in GAB_IDS:
        assert cid in declares, f"{cid} non déclaré en fiche"
        assert cid in EXTRACTEURS, f"{cid} sans extracteur robinet_fiche"
    # toutes masquées quand absentes : parcelle bloquée → seul le motif s'imprime
    for ln in gab[0].donnees:
        assert ln.masquer_si_absent is True


def test_figure_est_un_format_valide():
    assert "figure" in DEC.FORMATS


def test_declarations_sans_orphelin_gabarit():
    _viol, orph = DEC.verifier()
    assert not any("gabarit_" in o for o in orph)
