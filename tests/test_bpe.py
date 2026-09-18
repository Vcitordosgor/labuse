"""SOURCES-4 lot 2 — BPE INSEE : attrs MAXIMUM (année + adresse + SIRET + qualité + sectoriels).

BPE25 publie 95 colonnes ; on n'en gardait que 4 (dom/sdom/typequ + nom). `_bpe_attrs` capture
désormais l'année (AN), l'adresse, le SIRET, la qualité de géoloc et les caractéristiques
sectorielles non vides — en écartant la modalité « _Z » (sans objet pour ce type d'équipement).
"""
from __future__ import annotations

from labuse.ingestion.bpe import _bpe_attrs


def test_bpe_attrs_annee_adresse_sectoriels():
    row = {"DOM": "C", "SDOM": "C1", "TYPEQU": "C101", "AN": "2025",
           "NUMVOIE": "12", "TYPVOIE": "RUE", "LIBVOIE": "DE L ECOLE", "CODPOS": "97400",
           "SIRET": "12345678900011", "QUALITE_XY": "B",
           # sectoriels : un renseigné, un « _Z » (sans objet), un vide
           "SECTEUR": "PU", "CAPACITE_D_ACCUEIL": "_Z", "NBSALLES": ""}
    a = _bpe_attrs(row)
    assert a["dom"] == "C" and a["dom_label"] == "Enseignement"
    assert a["sdom"] == "C1" and a["typequ"] == "C101"
    assert a["an"] == "2025"                                  # année captée (jamais avant)
    assert a["adresse"] == "12 RUE DE L ECOLE" and a["code_postal"] == "97400"
    assert a["siret"] == "12345678900011" and a["qualite_xy"] == "B"
    # seul le sectoriel renseigné est gardé ; « _Z » et vide écartés
    assert a["caracteristiques"] == {"secteur": "PU"}


def test_bpe_attrs_sans_sectoriels_ni_adresse():
    row = {"DOM": "B", "SDOM": "B2", "TYPEQU": "B201", "AN": "2025",
           "SECTEUR": "_Z", "CAPACITE": ""}
    a = _bpe_attrs(row)
    assert a["caracteristiques"] is None        # aucun sectoriel renseigné → None (jamais {})
    assert a["adresse"] is None and a["siret"] is None
    assert a["an"] == "2025"


def test_parc_national_popup_riche_sources4():
    """SOURCES-4 lot 2 — Parc national : superficie (ha) + décret/arrêté publiés par l'ODS
    pnrun_2021 servis au clic. COUCHES-RETRAIT-1 lot 3 — l'ancien endpoint V1 (_RICH_POPUP_KINDS)
    est retiré : la couche est servie (attrs au clic) par le tuyau."""
    from labuse.registre.declarations import couches_carte
    assert "parc_national" in {c["kind"] for c in couches_carte()}
