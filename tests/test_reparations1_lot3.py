"""REPARATIONS-1 lot 3 — le statut « non disponible — partenariat requis » : hors vitrine
client (invisible), admis au catalogue (liste fermée G1), discipliné par V2b (partenaire
nommé en note), conservé en base ; et la couverture réelle est un champ servi."""
from __future__ import annotations

from labuse.circuit_garanties import STATUTS_ADMIS
from labuse.circuit_verrous import analyse_catalogue
from labuse.sources_catalog import est_affichee


def test_partenariat_requis_invisible_client():
    assert not est_affichee("LOVAC (logements vacants)", "NON DISPONIBLE — PARTENARIAT REQUIS…",
                            "partenariat_requis", False)


def test_partenariat_requis_dans_la_liste_fermee():
    assert "partenariat_requis" in STATUTS_ADMIS


def test_v2b_exige_le_partenaire_nomme():
    sans_note = [{"id": 1, "name": "X", "status": "partenariat_requis", "technical_notes": "",
                  "affichage_desactive": False, "alias_de": None,
                  "retiree_le": None, "retiree_raison": None}]
    pbs = analyse_catalogue(sans_note)
    assert any("partenariat_requis sans partenaire nommé" in p for p in pbs)
    avec_note = [dict(sans_note[0], technical_notes="NON DISPONIBLE — PARTENARIAT REQUIS : Cerema.")]
    assert analyse_catalogue(avec_note) == []


def test_couverture_note_servie(client=None):
    from labuse import models
    assert hasattr(models.DataSource, "couverture_note")
