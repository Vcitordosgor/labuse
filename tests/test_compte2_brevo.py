"""COMPTE-2 · Lot 1 — le registre unique des seize templates Brevo.

Ces tests GRAVENT la table de correspondance (ID canonique · nom · params) telle que le mandat la
décrit : toute dérive accidentelle (un ID déplacé, un param oublié) casse ici, pas chez un client
qui reçoit un « {{ params.X }} » brut. Le test réseau (`local`) confirme la correspondance côté Brevo.
"""
from __future__ import annotations

import os

import pytest

from labuse import brevo

# Table du mandat COMPTE-2 Lot 1 : clé code → (ID Brevo, nom, params substitués attendus).
ATTENDU = {
    # 4 & 6 : LIEN_INVITATION (décision Vic — onboarding par lien, jamais un mot de passe provisoire).
    "essai":          (4,  "LABUSE-E-ESSAI-48H",     {"PRENOM", "EMAIL", "LIEN_INVITATION", "FIN_ESSAI"}),
    "souscription":   (5,  "LABUSE-0-SOUSCRIPTION",  {"PRENOM", "LIEN_SOUSCRIPTION"}),
    "onboarding1":    (6,  "LABUSE-1-BIENVENUE",     {"PRENOM", "EMAIL", "LIEN_INVITATION"}),
    "onboarding2":    (7,  "LABUSE-2-METHODE",       {"PRENOM"}),
    "onboarding3":    (8,  "LABUSE-3-POINT-ETAPE",   {"PRENOM"}),
    "relance_carte":  (9,  "LABUSE-A-CARTE-REFUSEE", {"PRENOM", "LIEN_PAIEMENT"}),
    "suspension":     (10, "LABUSE-B-SUSPENSION",    {"PRENOM", "LIEN_PAIEMENT"}),
    "retablissement": (11, "LABUSE-C-RETABLI",       {"PRENOM"}),
    "radar_digest":   (12, "LABUSE-12-RADAR-DIGEST", {"PRENOM", "DATE", "NB_BIENS", "CARTES"}),
    "radar_alerte":   (13, "LABUSE-13-RADAR-ALERTE", {"PRENOM", "VEILLE", "NB_BIENS", "CRITERES", "CARTES"}),
    "mdp_oublie":     (14, "LABUSE-D-MDP-OUBLIE",    {"PRENOM", "LIEN_RESET", "VALIDITE"}),
    "mdp_modifie":    (15, "LABUSE-D-MDP-MODIFIE",   {"PRENOM", "DATE_HEURE"}),
    "resiliation":    (16, "LABUSE-F-RESILIATION",   {"PRENOM", "DATE_FIN_ACCES"}),
    "flash_pret":     (17, "LABUSE-G-FLASH-PRET",    {"LIEN_PDF", "VALIDITE", "IDU", "COMMUNE"}),
    "email_change":   (18, "LABUSE-H-EMAIL-CHANGE",  {"PRENOM", "ANCIEN_EMAIL", "NOUVEL_EMAIL"}),
    "retour_traite":  (19, "LABUSE-I-RETOUR-TRAITE", {"PRENOM", "SON_MESSAGE", "REPONSE"}),
}


def test_registre_couvre_les_seize_et_rien_de_plus():
    assert set(brevo.REGISTRE) == set(ATTENDU), "le registre doit contenir EXACTEMENT les seize clés"


@pytest.mark.parametrize("key", list(ATTENDU))
def test_id_nom_params_canoniques(key):
    tid, nom, params = ATTENDU[key]
    t = brevo.REGISTRE[key]
    assert t.id == tid, f"{key}: ID canonique attendu {tid}, trouvé {t.id}"
    assert t.nom == nom
    assert set(t.params) == params, f"{key}: params attendus {params}, trouvés {set(t.params)}"


def test_ids_uniques():
    ids = [t.id for t in brevo.REGISTRE.values()]
    assert len(ids) == len(set(ids)), "aucun ID Brevo ne doit être partagé par deux templates"


def test_template_id_sans_env_rend_l_id_canonique(monkeypatch):
    # aucune surcharge .env → l'app connaît les bons IDs sans configuration.
    for champ in (t.env_champ for t in brevo.REGISTRE.values() if t.env_champ):
        monkeypatch.delenv(champ.upper(), raising=False)
    for key, (tid, _n, _p) in ATTENDU.items():
        assert brevo.template_id(key) == tid


def test_alias_radar_legacy_route_vers_digest():
    # l'ancienne clé 'radar' (doublon ID 12) ne casse aucun lecteur : elle route vers radar_digest.
    assert brevo.template_id("radar") == 12
    assert brevo.template("radar").id == 12


def test_flags_conditionnels_hors_params():
    # RENVOI (4/5) et JAMAIS_CONNECTE (7) sont des booléens de bloc {% if %}, jamais substitués.
    assert "RENVOI" in brevo.REGISTRE["essai"].flags
    assert "RENVOI" in brevo.REGISTRE["souscription"].flags
    assert "JAMAIS_CONNECTE" in brevo.REGISTRE["onboarding2"].flags
    for key in ("essai", "souscription", "onboarding2"):
        assert not (set(brevo.REGISTRE[key].flags) & set(brevo.REGISTRE[key].params))


def test_evaluer_conditions_offline():
    ev = brevo._evaluer_conditions
    assert ev("a{% if params.RENVOI %}RENVOI{% endif %}b", {"RENVOI": True}) == "aRENVOIb"
    assert ev("a{% if params.RENVOI %}RENVOI{% endif %}b", {"RENVOI": False}) == "ab"
    assert ev("{% if params.JAMAIS_CONNECTE %}jamais{% else %}déjà{% endif %}",
              {"JAMAIS_CONNECTE": True}) == "jamais"
    assert ev("{% if params.JAMAIS_CONNECTE %}jamais{% else %}déjà{% endif %}",
              {"JAMAIS_CONNECTE": False}) == "déjà"
    # param absent = falsy → branche else (ou vide)
    assert ev("x{% if params.NB %}y{% endif %}", {}) == "x"


@pytest.mark.local
def test_apercu_seize_rendus_sans_reste_brut():
    """Recette réelle (`pytest -m local`) : les 16 templates rendus avec des params représentatifs —
    zéro « {{ params.X }} » brut, zéro bloc {% %} visible, aucun « Bonjour , » vide."""
    import re
    if not (os.environ.get("BREVO_API_KEY") or os.environ.get("LABUSE_BREVO_API_KEY")):
        pytest.skip("BREVO_API_KEY absente")
    # MDP_PROVISOIRE et LIEN_INVITATION tous deux fournis : rendu propre que le template Brevo porte
    # encore l'ancien param ou déjà le nouveau (transition Vic).
    ech = {"PRENOM": "Victor", "EMAIL": "v@labuse.test", "MDP_PROVISOIRE": "x",
           "LIEN_INVITATION": "https://x", "FIN_ESSAI": "le 12/09",
           "LIEN_SOUSCRIPTION": "https://x", "LIEN_PAIEMENT": "https://x", "LIEN_RESET": "https://x",
           "LIEN_PDF": "https://x", "VALIDITE": "1 heure", "DATE_HEURE": "le 07/09", "DATE": "jeudi",
           "DATE_FIN_ACCES": "le 30/09", "NB_BIENS": 7, "CARTES": "<p>x</p>", "VEILLE": "v",
           "CRITERES": "c", "IDU": "974 AB", "COMMUNE": "Saint-Paul", "ANCIEN_EMAIL": "a@x",
           "NOUVEL_EMAIL": "b@x", "SON_MESSAGE": "m", "REPONSE": "r", "RENVOI": False,
           "JAMAIS_CONNECTE": True}
    for key in brevo.REGISTRE:
        a = brevo.apercu_template(key, ech)
        assert a.get("configure"), f"{key}: {a.get('raison')}"
        blob = a["subject"] + " " + a["html"]
        assert not re.search(r"\{\{\s*params\.", blob), f"{key}: reste brut"
        assert not re.search(r"\{%[^%]*%\}", blob), f"{key}: bloc conditionnel visible"
        assert "Bonjour ," not in blob


@pytest.mark.local
def test_verification_api_brevo_reelle():
    """CIRCUIT-P3 — joué à la main avec la vraie clé (`pytest -m local`). Confirme, côté Brevo :
    les seize existent, actifs, nom attendu, params présents, expéditeur unique victor@labuse.immo."""
    if not (os.environ.get("BREVO_API_KEY") or os.environ.get("LABUSE_BREVO_API_KEY")):
        pytest.skip("BREVO_API_KEY absente")
    res = brevo.verifier_templates()
    assert res["api"] is True
    assert res["expediteur_unique"] == "victor@labuse.immo"
    ecarts = [l for l in res["lignes"]
              if not (l.get("existe") and l.get("actif") and l.get("nom_ok") and not l.get("params_manquants"))]
    # ÉCART ATTENDU et documenté : 4 & 6 attendent LIEN_INVITATION (décision Vic) mais le template
    # Brevo porte encore MDP_PROVISOIRE tant que Vic ne l'a pas changé. Tout autre écart = 🔴.
    for l in ecarts:
        assert l["key"] in ("essai", "onboarding1"), f"écart Brevo inattendu : {l}"
        assert l.get("existe") and l.get("actif") and l.get("nom_ok")
        assert l.get("params_manquants") == ["LIEN_INVITATION"], l
