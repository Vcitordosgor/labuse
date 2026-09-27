"""KELFONCIER-FIX-1 (Lot C) — permis ANNULÉS servis + PA/DP libellés, par UNE fonction partagée.

`ingestion.permits.etat_libelle` / `est_annule` = la source unique de l'état administratif Sitadel3
(le `_ETAT_LABELS` que la frise invoquait sans qu'il existe). Tous les lecteurs s'y adossent :
fiche §4 (_statut), frise, outil Permis, séries commune/zone.
"""
from __future__ import annotations

from datetime import datetime


def test_etat_libelle_decode_les_codes_reels():
    from labuse.ingestion.permits import etat_libelle
    assert etat_libelle({"etat": "2"}) == "autorisé"
    assert etat_libelle({"etat": "4"}) == "annulé"              # 4 324 en base, jamais montré avant
    assert etat_libelle({"etat": "5"}) == "travaux commencés"
    assert etat_libelle({"etat": "6"}) == "travaux achevés"
    # la DAACT prime (achèvement réel), même sans etat=6
    assert etat_libelle({"etat": "2", "daact": "2024-03-01"}) == "travaux achevés"
    # code inconnu / absent → défaut « autorisé » (ces flux ne portent que des autorisations)
    assert etat_libelle({"etat": "9"}) == "autorisé"
    assert etat_libelle({}) == "autorisé"
    assert etat_libelle(None) == "autorisé"


def test_est_annule():
    from labuse.ingestion.permits import est_annule
    assert est_annule({"etat": "4"}) is True
    assert est_annule({"etat": "2"}) is False
    assert est_annule(None) is False


def test_statut_dit_annule():
    from labuse.ingestion import permits
    d = datetime(2023, 6, 15)
    assert permits._statut({"etat": "4"}, d).startswith("annulé")
    assert permits._statut({"etat": "2"}, d) == "autorisé le 2023-06-15"
    assert "travaux achevés" in permits._statut({"etat": "6"}, d)
    assert "travaux commencés" in permits._statut({"etat": "5"}, d)


def test_type_label_couvre_pa_dp_pd():
    from labuse.ingestion.permits import _TYPE_LABEL
    assert _TYPE_LABEL["PA"] == "Permis d'aménager"
    assert _TYPE_LABEL["DP"] == "Déclaration préalable"
    assert _TYPE_LABEL["PD"] == "Permis de démolir"
    assert _TYPE_LABEL["PC"] == "Permis de construire"
