"""FIX post-validation A — robustesse du cadrage projet (entretien copilote).

Bug reproduit (tour de validation Vic, 20/07) : « cadrage non conforme (Additional properties
are not allowed ('niveaux' was unexpected)) ». Cause : le modèle place `niveaux` (gabarit R+n,
donnée LÉGITIME) à la RACINE de la fiche au lieu de `ampleur.niveaux` → additionalProperties:false
rejette et TOUT l'entretien tombe. Fix : récupérer la donnée (relocate) + robustesse générale
(prune_to_schema retire un champ inattendu au lieu d'échouer). Fonctions PURES → pas de DB.
"""
from __future__ import annotations

from jsonschema import ValidationError, validate

from labuse.api.ia import ENTRETIEN_SCHEMA
from labuse.api.projet_schema import clean_fiche, prune_to_schema, relocate_niveaux

FICHE_SCHEMA = ENTRETIEN_SCHEMA["properties"]["fiche"]


def _entretien(fiche: dict, **extra) -> dict:
    return {"reformulation": "ok", "fiche": fiche, "questions": [], "pret": True, **extra}


def test_reproduction_bug_niveaux_racine():
    """Sans le fix : `niveaux` à la racine de la fiche fait échouer la validation (le bug PJ1)."""
    data = _entretien({"type_programme": "logements", "ampleur": {"logements": 40}, "niveaux": 3})
    try:
        validate(data, ENTRETIEN_SCHEMA)
        raised = False
    except ValidationError as exc:
        raised = "niveaux" in exc.message and "Additional properties" in exc.message
    assert raised, "le bug doit se reproduire sans le fix"


def test_relocate_niveaux_recupere_la_donnee():
    """La donnée légitime R+n est REMISE dans ampleur, jamais perdue."""
    fiche = relocate_niveaux({"ampleur": {"logements": 40}, "niveaux": 3})
    assert fiche["ampleur"] == {"logements": 40, "niveaux": 3}
    assert "niveaux" not in fiche  # plus à la racine
    # ampleur absente → créée
    assert relocate_niveaux({"niveaux": 2})["ampleur"] == {"niveaux": 2}


def test_relocate_nikeaux_n_ecrase_pas_une_valeur_bien_placee():
    fiche = relocate_niveaux({"ampleur": {"niveaux": 2}, "niveaux": 9})
    assert fiche["ampleur"]["niveaux"] == 2  # la valeur déjà bien placée prime


def test_relocate_idempotent_et_non_destructif():
    bien = {"ampleur": {"logements": 20, "niveaux": 2}}
    assert relocate_niveaux(bien) == bien
    assert relocate_niveaux(relocate_niveaux(bien)) == bien


def test_cadrage_aboutit_apres_relocate():
    """Le cas EXACT qui échouait aboutit maintenant (preuve du fix)."""
    fiche = clean_fiche(relocate_niveaux(
        {"type_programme": "logements", "ampleur": {"logements": 40}, "niveaux": 3,
         "perimetre": {"mode": "secteur", "secteur": "Ouest"}}))
    data, dropped = prune_to_schema(_entretien(fiche, nom="Résidence Ouest"), ENTRETIEN_SCHEMA)
    validate(data, ENTRETIEN_SCHEMA)  # ne lève plus
    assert data["fiche"]["ampleur"]["niveaux"] == 3
    assert dropped == []  # rien à retirer : la donnée était légitime


def test_prune_retire_champ_inattendu_sans_echouer():
    """Robustesse générale : un champ hors vocabulaire est retiré + signalé, pas fatal."""
    data = _entretien(
        {"type_programme": "bureaux", "budget_max": 999, "perimetre": {"mode": "ile", "zzz": 1}},
        inventé_au_top="x",
        questions=[{"id": "type", "texte": "?", "chips": [
            {"label": "A", "value": "a", "bogus": 1}, {"label": "B", "value": "b"}]}])
    cleaned, dropped = prune_to_schema(data, ENTRETIEN_SCHEMA)
    validate(cleaned, ENTRETIEN_SCHEMA)  # aboutit
    assert set(dropped) == {"fiche.budget_max", "fiche.perimetre.zzz",
                            "inventé_au_top", "questions[0].chips[0].bogus"}
    # les valeurs légitimes sont conservées intactes
    assert cleaned["fiche"]["type_programme"] == "bureaux"
    assert cleaned["questions"][0]["chips"] == [{"label": "A", "value": "a"}, {"label": "B", "value": "b"}]


def test_prune_ne_touche_pas_une_donnee_valide():
    valide = _entretien({"type_programme": "logements", "ampleur": {"logements": 20, "niveaux": 2},
                         "perimetre": {"mode": "ile"}}, nom="X")
    cleaned, dropped = prune_to_schema(valide, ENTRETIEN_SCHEMA)
    assert dropped == []
    assert cleaned == valide
