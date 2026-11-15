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
    # 4 & 6 : LIEN_INVITATION (décision Vic — onboarding par lien ; ni mot de passe provisoire, ni EMAIL).
    "essai":          (4,  "LABUSE-E-ESSAI-48H",     {"PRENOM", "LIEN_INVITATION", "FIN_ESSAI"}),
    "souscription":   (5,  "LABUSE-0-SOUSCRIPTION",  {"PRENOM", "LIEN_SOUSCRIPTION"}),
    "onboarding1":    (6,  "LABUSE-1-BIENVENUE",     {"PRENOM", "LIEN_INVITATION"}),
    "onboarding2":    (7,  "LABUSE-2-METHODE",       {"PRENOM"}),
    "onboarding3":    (8,  "LABUSE-3-POINT-ETAPE",   {"PRENOM"}),
    "relance_carte":  (9,  "LABUSE-A-CARTE-REFUSEE", {"PRENOM", "LIEN_PAIEMENT"}),
    "suspension":     (10, "LABUSE-B-SUSPENSION",    {"PRENOM", "LIEN_PAIEMENT"}),
    "retablissement": (11, "LABUSE-C-RETABLI",       {"PRENOM"}),
    # CHIRURGICAL-FIX-1 (E119) — radar_digest (12) retiré du registre (legacy sans déclencheur live).
    "radar_alerte":   (13, "LABUSE-13-RADAR-ALERTE", {"PRENOM", "VEILLE", "NB_BIENS", "CRITERES", "CARTES"}),
    "mdp_oublie":     (14, "LABUSE-D-MDP-OUBLIE",    {"PRENOM", "LIEN_RESET", "VALIDITE"}),
    "mdp_modifie":    (15, "LABUSE-D-MDP-MODIFIE",   {"PRENOM", "DATE_HEURE"}),
    "resiliation":    (16, "LABUSE-F-RESILIATION",   {"PRENOM", "DATE_FIN_ACCES"}),
    "flash_pret":     (17, "LABUSE-G-FLASH-PRET",    {"LIEN_PDF", "VALIDITE", "IDU", "COMMUNE"}),
    # CHIRURGICAL-FIX-1 (E109) — email_change (18) retiré du registre (aucun déclencheur, code mort).
    "retour_traite":  (19, "LABUSE-I-RETOUR-TRAITE", {"PRENOM", "SON_MESSAGE", "REPONSE"}),
    # NU5-FIX-1 (C-F7) — avertissement J-1 de fin d'essai (template Brevo id 20 à créer, geste console).
    "essai_fin_proche": (20, "LABUSE-J-ESSAI-FIN-PROCHE", {"PRENOM", "DATE_FIN", "LIEN_PAIEMENT"}),
}


#: NU5-FIX-1 (C-F7) — templates DONT LE CODE RÉFÈRE LA CLÉ mais dont le template Brevo est un geste
#: console pas encore appliqué (brevo-stripe.md). Exclus des vérifications LIVE tant que non créés ;
#: à retirer de ce set dès que le template existe côté Brevo (les tests `-m local` les couvriront alors).
_PENDING_BREVO = {"essai_fin_proche"}


def test_registre_couvre_exactement_les_cles_attendues():
    assert set(brevo.REGISTRE) == set(ATTENDU), "le registre doit contenir EXACTEMENT les clés attendues"


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


def test_alias_radar_legacy_retire():
    # CHIRURGICAL-FIX-1 (E119) — l'alias legacy 'radar' est retiré en même temps que radar_digest :
    # la clé ne résout plus aucun template (le registre est la seule source).
    assert brevo.template_id("radar") is None
    assert brevo.template("radar") is None


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


def test_apercu_branche_sur_le_rendu_local():
    """CHIRURGICAL-FIX-1 (E110) — l'aperçu est désormais le RENDU LOCAL réel (plus le HTML mort de
    Brevo), SANS clé Brevo : chaque clé du registre rend `configure:true`, sans reste de gabarit
    ({{ }} / {% %}) ni « Bonjour , » vide. C'est le mail qui PART qu'on prévisualise."""
    import re

    from labuse import mails_contenu as mc
    for key in brevo.REGISTRE:
        a = brevo.apercu_template(key, mc.SPECIMENS.get(key, {}))
        assert a.get("configure"), f"{key}: {a.get('raison')}"
        assert a.get("source", "").startswith("rendu local"), f"{key}: l'aperçu n'est pas le rendu local"
        blob = f"{a['subject']} {a['html']}"
        assert "{{" not in blob and "{%" not in blob, f"{key}: reste brut"
        assert "Bonjour ," not in blob, f"{key}: salutation vide"


def test_verification_branchee_sur_le_rendu_local():
    """CHIRURGICAL-FIX-1 (E110) — la vérification porte sur le RENDU LOCAL (source de vérité), sans
    appel Brevo : chaque clé du registre a un rendu local propre (rend_ok, aucun résidu)."""
    res = brevo.verifier_templates()
    assert res.get("source", "").startswith("rendu local")
    ecarts = [l for l in res["lignes"] if not l.get("rend_ok")]
    assert not ecarts, f"écarts de rendu local : {ecarts}"
    assert res["ok"] is True
