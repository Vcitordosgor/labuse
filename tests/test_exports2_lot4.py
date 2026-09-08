"""EXPORTS-2 lot 4 — le questionnaire du Financier (données : ids, persistance, pré-remplissage
sourcé, résolution). Les 3 règles Vic verrouillées :
  1. chaque pré-remplissage porte sa source ; un pré-remplissage sans source n'est pas émis ;
  2. un champ vidé reste vide → « non chiffré » (jamais un retour silencieux au défaut) ;
  3. le régime de TVA est obligatoire (décide de la vérité du bilan).
"""
from __future__ import annotations

import pytest

from labuse import financier_questionnaire as qf
from labuse import registre
from labuse.registre.donnees import DONNEES
from labuse.registre.robinets import ROBINETS

NOUVEAUX = ("scenario_saisi", "logements_vises_saisi", "typologie_moyenne_saisi", "part_sociale_saisi_pct",
            "stationnement_type_saisi", "prix_refuse_saisi_eur", "frais_acquisition_saisi_pct",
            "commission_apporteur_saisi_eur", "honoraires_techniques_saisi_pct", "vrd_saisi_eur_m2",
            "cout_place_stationnement_saisi_eur", "aleas_saisi_pct", "taxe_amenagement_saisi_eur",
            "prix_sortie_saisi_eur_m2", "prix_vente_bailleur_saisi_eur_m2", "marge_visee_saisi_pct",
            "regime_tva_saisi", "duree_portage_saisi_mois", "apport_saisi_eur", "taux_apport_saisi_pct")


# ── registre ─────────────────────────────────────────────────────────────────────────────────

def test_les_champs_sont_des_ids_projet():
    for fid in NOUVEAUX:
        d = DONNEES.get(fid)
        assert d is not None and d.portee == "projet" and d.calcul == "passe_plat", fid
        assert d.unite != "nombre", (fid, d.unite)     # jamais un compteur mal formé
    sers = {c for r in ROBINETS.values() for c in r.chiffres}
    for fid in NOUVEAUX:
        assert fid in sers, f"{fid} non servi par un robinet"
    assert registre.verifier() == []


def test_regime_tva_est_une_classe_avec_domaine():
    d = DONNEES["regime_tva_saisi"]
    assert d.type == "classe" and set(d.domaine) == {"assujetti_recuperation", "tva_marge", "autre"}


def test_quatre_ecrans_vingtaine_de_champs():
    assert len(qf.ECRANS) == 4
    assert [t for t, _ in qf.ECRANS] == ["Votre projet", "Le foncier", "Vos coûts", "Vos conditions"]
    assert 18 <= len(qf.CHAMPS) <= 26
    assert qf.OBLIGATOIRES == {"regime_tva_saisi"}


# ── règle 1 : pré-remplissage toujours sourcé ────────────────────────────────────────────────

def test_prefill_toujours_source():
    pf = qf.prefill({"potentiel_transformation": {"surelevation_possible": False, "capacite_estimee": 8},
                     "taxe_amenagement": {"total_eur": 39000}})
    assert pf, "des pré-remplissages sont attendus"
    for fid, v in pf.items():
        assert v.get("source"), f"{fid} : pré-remplissage sans source (règle 1)"
    assert pf["cout_construction_saisi_eur_m2"]["valeur"] == 2550 and "EPTB" in pf["cout_construction_saisi_eur_m2"]["source"]
    assert pf["scenario_saisi"]["valeur"] == "reconstruction"
    assert pf["logements_vises_saisi"]["valeur"] == 8
    # pas de source pour ces champs → jamais pré-remplis
    for fid in ("prix_demande_saisi_eur", "regime_tva_saisi", "bilan_demolition_eur", "cout_place_stationnement_saisi_eur"):
        assert fid not in pf


def test_prefill_omet_quand_pas_de_donnee():
    pf = qf.prefill({})     # aucune fiche → seulement les constantes sourcées
    assert "scenario_saisi" not in pf and "taxe_amenagement_saisi_eur" not in pf
    assert "cout_construction_saisi_eur_m2" in pf   # constante toujours sourcée


# ── règle 2 : vidé → non chiffré, jamais le défaut ──────────────────────────────────────────

def test_vide_reste_vide():
    pf = qf.prefill({})
    res = qf.resoudre({"cout_construction_saisi_eur_m2": None, "vrd_saisi_eur_m2": 120}, pf)
    assert res["cout_construction_saisi_eur_m2"]["origine"] == "non_chiffre"   # vidé → non chiffré
    assert res["cout_construction_saisi_eur_m2"]["valeur"] is None
    assert res["vrd_saisi_eur_m2"] == {"valeur": 120, "origine": "saisi"}      # saisi
    assert res["frais_acquisition_saisi_pct"]["origine"] == "prefill"          # jamais touché → pré-rempli
    assert res["prix_demande_saisi_eur"]["origine"] == "non_chiffre"           # ni saisi ni pré-rempli


# ── règle 3 : régime de TVA obligatoire ──────────────────────────────────────────────────────

def test_complet_exige_le_regime_tva():
    assert qf.est_complet({"regime_tva_saisi": "tva_marge"}) is True
    assert qf.est_complet({"regime_tva_saisi": None}) is False
    assert qf.est_complet({"prix_demande_saisi_eur": 650000}) is False
    assert "expert-comptable" in qf.TVA_EXPLICATION and "8,5" in qf.TVA_EXPLICATION


# ── persistance (cloison compte) ─────────────────────────────────────────────────────────────

@pytest.mark.db
def test_persistance_roundtrip_et_cloison(db_session):
    from sqlalchemy import text
    idu = "TESTIDU0001"
    qf.ensure(db_session)
    db_session.execute(text("DELETE FROM questionnaire_financier WHERE idu = :i"), {"i": idu})
    qf.enregistrer(db_session, idu, 1, {"regime_tva_saisi": "autre", "vrd_saisi_eur_m2": 95, "inconnu": 1})
    etat = qf.charger(db_session, idu, 1)
    assert etat["existe"] and etat["complet"] is True
    assert etat["reponses"] == {"regime_tva_saisi": "autre", "vrd_saisi_eur_m2": 95}  # « inconnu » filtré
    # cloison : un autre compte ne voit rien
    assert qf.charger(db_session, idu, 2)["existe"] is False
    db_session.execute(text("DELETE FROM questionnaire_financier WHERE idu = :i"), {"i": idu})
