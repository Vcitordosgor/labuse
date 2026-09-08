"""EXPORTS-2 lot 6 — l'Apporteur (brief confidentiel + questionnaire remplissable adaptatif).

Vérifie : mention de non-mandat, émetteur = compte (non modifiable), date d'émission + validité
90 jours, D-a quand la mutation existe, case « propriétaire joignable », champs remplissables
(<input>/<textarea> appearance:auto), blocs adaptatifs (bâti / personne morale), aucun ◌ ni mot
interdit. La génération d'AcroForm dépend du build WeasyPrint (mandat : vérifier Aperçu/Acrobat).
"""
from __future__ import annotations

from pathlib import Path

import yaml

from labuse.exports.blocs import apporteur
from labuse.registre.valeur import Valeur

MOTS = yaml.safe_load((Path(__file__).resolve().parents[1] / "config" / "mots_interdits.yaml").read_text())["mots"]


def _V(cid, valeur, **kw):
    return Valeur(valeur=valeur, chiffre_id=cid, version_def="x", run=None, **kw)


def _valeurs(bati=True):
    v = {"surface_parcelle_m2": _V("surface_parcelle_m2", 742),
         "zone_plu_famille": _V("zone_plu_famille", "U"),
         "type_proprietaire": _V("type_proprietaire", "Personne morale — MCA3 (SIREN 824160717)"),
         "distance_arret_m": _V("distance_arret_m", {"arret": {"nom": "Rue du Commerce", "distance_m": 143}})}
    if bati:
        v["emprise_batie_m2"] = _V("emprise_batie_m2", 540)
        v["n_batiments"] = _V("n_batiments", 2)
        v["hauteur_bati_m"] = _V("hauteur_bati_m", 9.4)
    return v


def _ctx(**kw):
    base = {"idu": "97415000BO0852", "adresse": "103 Chaussée Royale, Saint-Paul",
            "emetteur": {"raison": "Groupe Océan Promotion", "contact": "s.d@ocean.re"},
            "emission": "05/09/2026", "validite": "04/12/2026",
            "is_bati": True, "is_pm": True, "industriel_proche": False}
    base.update(kw)
    return base


def test_confidentiel_non_mandat_et_emission():
    html = apporteur.rendu(_valeurs(), _ctx())
    assert "Confidentiel" in html and "Un terrain à sonder" in html
    assert "ne vaut pas mandat" in html                       # A-a
    # RECETTE-2 (S7) — la section « Qui vous envoie ce brief » est RETIRÉE (décision Vic) : ni
    # titre, ni raison sociale de l'émetteur, ni ligne « Contact ». La date d'émission + validité
    # 90 jours SURVIT, déplacée en tête (métadonnée du brief, pas identité de l'émetteur).
    assert "Qui vous envoie" not in html
    assert "Groupe Océan Promotion" not in html
    assert "Émis le" in html and "90 jours" in html and "04/12/2026" in html


def test_parcelle_enrichie_s7():
    # RECETTE-2 (S7) — l'apporteur a la parcelle EN MAIN : contraintes + prix de secteur en plus.
    v = _valeurs()
    v["aleas_parcelle_liste"] = _V("aleas_parcelle_liste", [{"nature": "Mouvement de terrain"}])
    v["dpu_perimetre"] = _V("dpu_perimetre", True)
    v["prix_terrain_secteur_eur_m2"] = _V("prix_terrain_secteur_eur_m2", {"prix_m2": 320})
    v["sdp_residuelle_m2"] = _V("sdp_residuelle_m2", 1200)
    v["capacite_logements"] = _V("capacite_logements", 14)
    html = apporteur.rendu(v, _ctx())
    assert "Contraintes" in html and "Mouvement de terrain" in html and "préemption (DPU)" in html
    assert "Prix de secteur" in html and "terrain nu" in html
    assert "Potentiel" in html and "plancher résiduel" in html


def test_champs_remplissables():
    html = apporteur.rendu(_valeurs(), _ctx())
    assert html.count("<input") >= 4 and "<textarea" in html
    assert "appearance:auto" in html                          # champs de formulaire PDF
    assert "joignable" in html                                # case propriétaire joignable


def test_blocs_adaptatifs():
    # personne morale → question « société » ; bâti → section occupation
    pm = apporteur.rendu(_valeurs(bati=True), _ctx(is_pm=True, is_bati=True))
    assert "société" in pm and "occupés" in pm
    # terrain nu, personne physique → pas de section occupation, question générique
    nu = apporteur.rendu(_valeurs(bati=False), _ctx(is_pm=False, is_bati=False))
    assert "occupés" not in nu and "société" not in nu


def test_industriel_proche_adapte_la_question_du_sol():
    sans = apporteur.rendu(_valeurs(), _ctx(industriel_proche=False))
    avec = apporteur.rendu(_valeurs(), _ctx(industriel_proche=True))
    assert "établissement classé" not in sans
    assert "établissement classé" in avec


def test_section_emetteur_retiree_s7():
    # RECETTE-2 (S7) — même sans émetteur au contexte, aucune section « qui vous envoie » ni
    # placeholder « (votre compte) » : la section entière a disparu.
    html = apporteur.rendu(_valeurs(), _ctx(emetteur=None))
    assert "(votre compte)" not in html
    assert "Qui vous envoie" not in html


def test_da_present_si_mutation():
    v = _valeurs()
    v["prix_achat_historique_eur"] = _V("prix_achat_historique_eur", {"valeur": 180000})
    html = apporteur.rendu(v, _ctx())
    assert "achat de la parcelle" in html and "180" in html


def test_aucun_ocro_ni_mot_interdit():
    html = apporteur.rendu(_valeurs(), _ctx())
    assert "◌" not in html
    assert [m for m in MOTS if m in html] == []
