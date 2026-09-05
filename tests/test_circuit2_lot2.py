"""CIRCUIT-2 lot 2 — le document « la fiche, donnée par donnée » : généré DU registre,
chaque donnée de chaque tiroir présente, aucun trou « ? », les documents commités à jour
(pas d'édition à la main qui divergerait du registre)."""
from __future__ import annotations

from pathlib import Path

import pytest

from labuse import registre
from labuse.registre import fiche_doc

pytestmark = pytest.mark.db

RACINE = Path(__file__).resolve().parents[1]


def test_doc_parcelle_couvre_chaque_donnee_de_chaque_tiroir():
    doc = fiche_doc.doc_fiche_parcelle(db=None)
    for rid, r in registre.ROBINETS.items():
        if not rid.startswith("fiche_parcelle"):
            continue
        assert r.nom in doc, rid
        for cid in r.chiffres:
            assert f"`{cid}`" in doc, f"{rid} : {cid} absent du document"
    assert "| ? |" not in doc and "| — | — |" not in doc


def test_doc_autres_couvre_commune_annonce_proprietaire_soleil():
    doc = fiche_doc.doc_autres_fiches(db=None)
    for rid in [r for r in registre.ROBINETS if r.startswith("fiche_commune")] + \
               ["fiche_annonce", "fiche_proprietaire", "fiche_soleil"]:
        for cid in registre.ROBINETS[rid].chiffres:
            assert f"`{cid}`" in doc, f"{rid} : {cid} absent"


def test_documents_commites_a_jour_du_registre():
    """Le fichier commité contient chaque id du registre de la fiche — si le registre bouge,
    régénérer (`labuse registre fiche parcelle|autres`), jamais éditer à la main."""
    doc = (RACINE / "docs/CIRCUIT/FICHE-PARCELLE-DONNEES.md").read_text()
    for rid, r in registre.ROBINETS.items():
        if rid.startswith("fiche_parcelle"):
            for cid in r.chiffres:
                assert f"`{cid}`" in doc, f"régénérer le doc : {cid} manquant"
    autres = (RACINE / "docs/CIRCUIT/FICHES-DONNEES.md").read_text()
    for rid in [r for r in registre.ROBINETS if r.startswith("fiche_commune")]:
        for cid in registre.ROBINETS[rid].chiffres:
            assert f"`{cid}`" in autres, f"régénérer FICHES-DONNEES : {cid} manquant"
