"""M-U Volet A — bloc « Marché » par commune (point de calcul unique).

Tourne sur la base DE DONNÉES (LABUSE_DATABASE_URL) car le bloc lit DVF/Sitadel/DPE/run réels ;
lecture seule. Valide : structure 9 lignes, date amont PAR ligne, « non calculable » explicite
sous les seuils (jamais un chiffre inventé), run servi pour le gisement, dénominateur DPE honnête.
"""
from __future__ import annotations

import pytest

from labuse.db import session_scope
from labuse.faisabilite.marche_commune import (SEUIL_TENDANCE_N, SEUIL_TERRAIN_CELLULE_N,
                                               build_marche_commune)
from labuse.scoring.score_v_constants import Q_A_RUN_LABEL


def _bloc(commune):
    with session_scope() as s:
        b = build_marche_commune(s, commune)
    return {l["cle"]: l for l in b["lignes"]}, b


def _has_data(commune):
    from sqlalchemy import text
    with session_scope() as s:
        return bool(s.execute(text("SELECT 1 FROM dvf_mutations WHERE commune=:c LIMIT 1"),
                              {"c": commune}).scalar())


@pytest.mark.skipif(not _has_data("Saint-Paul"), reason="base sans données DVF Saint-Paul")
def test_commune_riche_8_lignes_sourcees_datees():
    lignes, b = _bloc("Saint-Paul")
    # EXPORTS-1 (1.2, arbitrage Q2) : ligne1 « prix ancien commune » (médiane autour du centroïde,
    # « n 11 », libellé faux) SUPPRIMÉE — le prix de l'ancien est parcellaire (marche_service).
    assert len(b["lignes"]) == 8
    assert "prix_ancien_median" not in lignes
    # chaque ligne porte source + (si calculable) sa PROPRE date amont — jamais un millésime unique
    for l in b["lignes"]:
        assert l["source"] and l["etiquette"]
        assert set(l) >= {"cle", "groupe", "calculable", "valeurs", "source", "date_amont", "fiabilite"}
    # Saint-Paul : terrain + tendance calculables
    assert lignes["tendance_12m"]["calculable"]
    # EXPORTS-1 (1.6) : la date amont DVF dit la borne réelle, plus un millésime d'année
    assert (lignes["tendance_12m"]["date_amont"] or "").startswith("ventes jusqu'au ")
    # ligne 2 : les DEUX cellules U/AU présentes (calculable ou motif), jamais omises
    pz = lignes["prix_terrain_nu_par_zone"]["valeurs"]["par_zone"]
    assert set(pz) == {"U", "AU"}
    for cell in pz.values():
        assert cell["calculable"] or "motif" in cell


@pytest.mark.skipif(not _has_data("Salazie"), reason="base sans données Salazie")
def test_commune_pauvre_tendance_non_calculable():
    lignes, _ = _bloc("Salazie")
    t = lignes["tendance_12m"]
    # une flèche sur peu de ventes est un mensonge : sous le seuil → non calculable explicite
    if (t["valeurs"].get("n12") or 0) < SEUIL_TENDANCE_N or (t["valeurs"].get("nprev") or 0) < SEUIL_TENDANCE_N:
        assert t["calculable"] is False and str(SEUIL_TENDANCE_N) in t["motif"]


@pytest.mark.skipif(not _has_data("Saint-Paul"), reason="base sans données")
def test_gisement_run_servi_et_dpe_denominateur_connu():
    lignes, _ = _bloc("Saint-Paul")
    g = lignes["gisement_constructible"]
    if g["calculable"]:
        assert Q_A_RUN_LABEL in (g["date_amont"] or "") and Q_A_RUN_LABEL in g["etiquette"]
    dpe = lignes["pression_dpe"]
    # dénominateur = parc DIAGNOSTIQUÉ, dit explicitement (« sur N DPE connus »)
    assert "DPE conn" in dpe["etiquette"]


@pytest.mark.skipif(not _has_data("Saint-Paul"), reason="base sans données")
def test_market_signal_jamais_un_label_nu_source_dvf_sitadel():
    from labuse.faisabilite.marche_commune import market_signal
    with session_scope() as s:
        sig = market_signal(s, "Saint-Paul")
    if sig["disponible"]:
        # jamais un mot nu : le label est TOUJOURS accompagné de ses composantes visibles
        assert sig["label"] in ("favorable", "neutre", "prudence")
        assert sig["composantes"] and len(sig["composantes"]) >= 1
        assert sig["source"] == "DVF (actes) + Sitadel (autorisations)"
        # aucune lecture Obsimmo dans la source servie
        assert "obsimmo" not in sig["source"].lower()


@pytest.mark.skipif(not _has_data("Saint-Paul"), reason="base sans données")
def test_ligne2_cellule_sous_seuil_non_calculable_jamais_mediane_sur_3_ventes():
    lignes, _ = _bloc("Salazie") if _has_data("Salazie") else _bloc("Saint-Paul")
    pz = lignes["prix_terrain_nu_par_zone"]["valeurs"]["par_zone"]
    for cell in pz.values():
        if not cell["calculable"]:
            assert cell.get("n", 0) < SEUIL_TERRAIN_CELLULE_N   # jamais une médiane sous le seuil
