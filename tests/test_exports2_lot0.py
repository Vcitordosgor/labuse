"""EXPORTS-2 lot 0 — le registre avant les documents.

Verrous du lot 0.4/0.5/0.6 :
  · les 15 chiffres du Financier existent, en_attente (servis quand le builder les câble),
    portent un moteur et un producteur nommé — aucun n'est encore servi par un robinet ;
  · le bilan travaille HT (décision Vic 07/09 : bilan_ca_eur dit « HT ») ;
  · la garde de couverture (0.5, règle 0-bis) tient : un compteur sans couverture est refusé,
    aucun des nouveaux ids n'est un compteur mal formé ;
  · le registre reste intègre : verifier() est vide (0.6).
"""
from __future__ import annotations

from labuse import registre
from labuse.registre.donnees import DONNEES
from labuse.registre.robinets import ROBINETS
from labuse.registre.valeur import Valeur, probleme_couverture

#: les 15 ids créés au lot 0.4 (les postes du bilan à rebours + bornes + sensibilité + sorties
#: dérivées + le fait foncier D-a).
IDS_FINANCIER = (
    "bilan_frais_acquisition_eur", "bilan_honoraires_techniques_eur", "bilan_stationnement_eur",
    "bilan_aleas_eur", "bilan_depollution_eur", "bilan_portage_eur", "redevance_archeologie_eur",
    "charge_fonciere_basse_eur", "charge_fonciere_haute_eur", "sensibilite_prix_sortie",
    "seuil_rentabilite_eur", "prix_revient_eur_m2", "prix_achat_historique_eur",
    "mixite_seuil_m2", "mixite_quota_pct",
)


def test_les_quinze_ids_existent_et_sont_declares():
    for cid in IDS_FINANCIER:
        d = DONNEES.get(cid)
        assert d is not None, f"id {cid} absent du registre"
        assert d.moteur, f"{cid} : moteur manquant"
        assert d.fonction, f"{cid} : producteur (fonction) manquant"
        assert d.type in ("nombre",), (cid, d.type)   # €, €/m², %, m² → type « nombre »


def test_en_attente_jusqu_au_builder():
    """Lot 0.4 : créés en_attente ; l'attente est LEVÉE au fil des documents qui les servent —
    lot 2 : `prix_achat_historique_eur` (D-a, Dossier) ; lot 5 : les postes du bilan à rebours
    (Financier). Restent en_attente : la mixité seuil/quota (chantier ultérieur)."""
    sers = {cid for r in ROBINETS.values() for cid in r.chiffres}
    encore_en_attente = {"mixite_seuil_m2", "mixite_quota_pct"}
    for cid in IDS_FINANCIER:
        if cid in encore_en_attente:
            assert DONNEES[cid].en_attente and cid not in sers, f"{cid} : doit rester en_attente"
        else:
            assert not DONNEES[cid].en_attente, f"{cid} : servi → en_attente doit être levée"
            assert cid in sers, f"{cid} : servi mais absent des robinets"


def test_le_bilan_travaille_ht():
    """Décision Vic 07/09 : le bilan est HT — le chiffre d'affaires le dit dans sa définition."""
    assert "HT" in DONNEES["bilan_ca_eur"].definition


def test_charge_fonciere_trois_bornes():
    """Lot 5.3 : jamais un point seul — la charge foncière a une borne basse et une borne haute
    en plus de la centrale (charge_fonciere_eur)."""
    assert "charge_fonciere_eur" in DONNEES
    assert DONNEES["charge_fonciere_basse_eur"].libelle != DONNEES["charge_fonciere_haute_eur"].libelle


def test_deux_axes_de_sensibilite():
    """Lot 5.3 : sensibilité DOUBLE — coût de construction ET prix de sortie, deux ids distincts."""
    assert {"sensibilite_cout_construction", "sensibilite_prix_sortie"} <= set(DONNEES)


def test_garde_couverture_regle_du_registre():
    """Lot 0.5 (règle 0-bis) : un COMPTEUR (unité « nombre ») sans couverture est refusé ; les
    nouveaux ids ne sont pas des compteurs (unités €, €/m², %, m²) donc non concernés."""
    faux = Valeur(valeur=1, chiffre_id="n_batiments", version_def="x", run=None)
    assert probleme_couverture(faux)  # compteur sans couverture → refusé
    for cid in IDS_FINANCIER:
        assert DONNEES[cid].unite != "nombre", (cid, DONNEES[cid].unite)
        v = Valeur(valeur=1, chiffre_id=cid, version_def="x", run=None)
        assert probleme_couverture(v) is None, f"{cid} : pas un compteur, ne doit pas être refusé"


def test_registre_integre():
    """Lot 0.6 : verifier() vide — aucun id orphelin, la règle en_attente tient."""
    assert registre.verifier() == []
