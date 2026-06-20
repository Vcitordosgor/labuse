"""Type de propriétaire (Lot C3) — classification + courrier SPF, cœur PUR.

Vérifie le classement fin (SCI / commune / EPF / bailleur / État / indivision / inconnu),
le besoin de demande SPF, et que le courrier ne contient AUCUNE donnée nominative.
"""
from __future__ import annotations

from datetime import date

from labuse.proprietaire_type import classify_owner_type, needs_spf, spf_letter


def _ff(categorie=None, morale=False, nb=None, indivision=False):
    return {"categorie": categorie, "personne_morale": morale,
            "nb_droits_propriete": nb, "indivision": indivision}


def test_sci_identifiable_acquerable():
    o = classify_owner_type(_ff("SCI du Verger", morale=True))
    assert o["owner_type"] == "sci" and o["famille"] == "prive" and o["identifiable"] is True
    assert needs_spf(o) is False


def test_commune_public():
    o = classify_owner_type(_ff("Commune de Saint-Paul", morale=True))
    assert o["owner_type"] == "commune" and o["public"] is True and o["famille"] == "public"


def test_epf_et_bailleur():
    assert classify_owner_type(_ff("EPF Réunion", morale=True))["owner_type"] == "epf"
    assert classify_owner_type(_ff("SHLMR", morale=True))["owner_type"] == "bailleur_social"
    assert classify_owner_type(_ff("SIDR — logement social", morale=True))["owner_type"] == "bailleur_social"


def test_etat_et_collectivite():
    assert classify_owner_type(_ff("État — domaine public", morale=True))["owner_type"] == "etat"
    assert classify_owner_type(_ff("Région Réunion", morale=True))["owner_type"] == "collectivite"
    assert classify_owner_type(_ff("TCO (EPCI)", morale=True))["owner_type"] == "collectivite"


def test_indivision_prime_sur_physique():
    o = classify_owner_type(_ff(None, morale=False, nb=7, indivision=True))
    assert o["owner_type"] == "indivision" and o["indivision"] is True
    assert needs_spf(o) is True   # pas d'interlocuteur unique identifié


def test_inconnu_quand_pas_de_donnee():
    o = classify_owner_type(None)
    assert o["owner_type"] == "inconnu" and o["famille"] == "inconnu" and needs_spf(o) is True


def test_societe_generique_si_morale_sans_categorie():
    o = classify_owner_type(_ff(None, morale=True))
    assert o["owner_type"] == "societe" and o["famille"] == "prive"


def test_spf_letter_reference_cadastrale_sans_nominatif():
    letter = spf_letter({"idu": "97415000BV0912", "commune": "Saint-Paul", "section": "BV",
                         "numero": "912", "surface_m2": 3948}, today=date(2026, 6, 12))
    assert "97415000BV0912" in letter and "Saint-Paul" in letter and "section BV" in letter
    assert "Publicité Foncière" in letter and "12/06/2026" in letter
    # Garde-fou : aucune donnée nominative fabriquée ; mention de la voie légale.
    assert "aucune donnée nominative" in letter.lower()
