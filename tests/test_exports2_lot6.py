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
            # RECETTE-12 E1 — émetteur nommé (nom + téléphone), format servi par builder._emetteur.
            "emetteur": {"nom": "Groupe Océan Promotion",
                         "coordonnees": "12 rue du Port, 97420 · 0262 00 00 00", "email": "s.d@ocean.re"},
            "emission": "05/09/2026", "validite": "04/12/2026",
            "is_bati": True, "is_pm": True, "industriel_proche": False,
            "voisines": {"n": 0, "membres": [], "surface_totale_m2": None}, "plan": None}
    base.update(kw)
    return base


def test_confidentiel_non_mandat_et_emission():
    html = apporteur.rendu(_valeurs(), _ctx())
    # RECETTE-6 (F1) — is_bati=True → titre « bien bâti » (jamais « terrain »).
    assert "Confidentiel" in html and "Un bien bâti à sonder" in html
    # RECETTE-3 (T1) — UN SEUL bandeau : confidentiel + non-mandat fusionnés.
    assert "sans mandat" in html and "habilité" in html
    assert html.count('class="confidential"') == 1           # un seul bandeau, pas deux
    assert "ne vaut pas mandat" not in html                  # l'ancien second bloc a disparu
    # RECETTE-12 E1 — l'ÉMETTEUR est NOMMÉ (nom + téléphone) : Vic a refusé l'anonymat le 05/09.
    assert "Émetteur : " in html and "Groupe Océan Promotion" in html and "0262 00 00 00" in html
    assert "renvoyez vos réponses et vos photos" in html
    assert "Émis le" in html and "90 jours" in html and "04/12/2026" in html


def test_parcelle_enrichie_spec_e1():
    # RECETTE-12 E1 — « Ce qui gêne » RESTE ; « Prix du secteur » et « Ce qu'on peut y bâtir » RETIRÉS
    # (prix = ancre du vendeur ; capacité = répétée au propriétaire). Spec fermée APPORTEUR-SPEC.md.
    v = _valeurs()
    v["aleas_parcelle_liste"] = _V("aleas_parcelle_liste", [{"nature": "Mouvement de terrain"}])
    v["dpu_perimetre"] = _V("dpu_perimetre", True)
    v["prix_terrain_secteur_eur_m2"] = _V("prix_terrain_secteur_eur_m2", {"prix_m2": 320})
    v["sdp_residuelle_m2"] = _V("sdp_residuelle_m2", 1200)
    v["capacite_logements"] = _V("capacite_logements", 14)
    html = apporteur.rendu(v, _ctx())
    assert "Ce qui gêne" in html and "Mouvement de terrain" in html and "préemption (DPU)" in html
    assert "Prix du secteur" not in html and "€/m²" not in html
    assert "peut y bâtir" not in html and "plancher restant" not in html


def test_recette12_e1_contact_essentiel_voisines_photos():
    # RECETTE-12 E1 — contact = 1er champ OBLIGATOIRE SANS étiquette ; TROIS « l'essentiel » (prix,
    # bail, voisines) ; photos + retour à l'ÉMETTEUR nommé (jamais « n'imprimez rien »).
    v = _valeurs()
    v["prix_achat_historique_eur"] = _V("prix_achat_historique_eur",
                                        {"valeur": 186000, "date_mutation": "2019-03-15"})
    ctx = _ctx(voisines={"n": 2, "membres": [{"idu": "97415000CY0045", "ref": "CY 0045", "surface_m2": 670},
                                             {"idu": "97415000CY0046", "ref": "CY 0046", "surface_m2": 670}],
                         "surface_totale_m2": 1340})
    html = apporteur.rendu(v, ctx)
    # contact = 1re question, SANS badge « l'essentiel », marqué « (obligatoire) »
    assert "Nom et coordonnées" in html and "(obligatoire)" in html
    assert html.index("Nom et coordonnées") < html.index("Tous les décideurs")
    # EXACTEMENT trois « l'essentiel » : prix + bail (bâti) + voisines
    assert html.count("ESSENTIEL") == 3
    # dernière vente datée + chiffrée (S8 : présente ici)
    assert "Dernière vente" in html and "mars 2019" in html and "186" in html
    # à côté (Blocs fonciers) + question voisinage citant les références
    assert "À côté" in html and "CY 0045" in html and "340" in html
    # photos à l'émetteur nommé, jamais « n'imprimez rien »
    assert "Envoyez-les à Groupe Océan Promotion" in html and "97415000BO0852" in html
    assert "n'imprimez rien" not in html and "Si loué : sous quel bail" in html


def test_champs_remplissables():
    html = apporteur.rendu(_valeurs(), _ctx())
    assert html.count("<input") >= 4 and "<textarea" in html
    assert "appearance:auto" in html                          # champs de formulaire PDF
    assert "Par quel canal" in html                           # RECETTE-3 (T1) : par quel canal le joindre


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


def test_emetteur_absent_du_contexte_pas_de_bloc():
    # RECETTE-12 E1 — l'émetteur est RENDU quand il est connu (cf. test_confidentiel…), mais SANS
    # compte au contexte on n'imprime NI bloc émetteur NI placeholder « (votre compte) ».
    html = apporteur.rendu(_valeurs(), _ctx(emetteur=None))
    assert "(votre compte)" not in html
    assert "Émetteur : " not in html


def test_da_present_si_mutation():
    # RECETTE-3 (T1) — « Dernière vente » (ex « Prix d'achat de la parcelle ») ; sans date → montant seul.
    v = _valeurs()
    v["prix_achat_historique_eur"] = _V("prix_achat_historique_eur", {"valeur": 180000})
    html = apporteur.rendu(v, _ctx())
    assert "Dernière vente" in html and "180" in html


def test_derniere_vente_omise_si_inconnue():
    # RECETTE-3 (T1, règle S8) — mutation inconnue → la ligne « Dernière vente » ne s'imprime PAS.
    html = apporteur.rendu(_valeurs(), _ctx())
    assert "Dernière vente" not in html


def test_aucun_ocro_ni_mot_interdit():
    html = apporteur.rendu(_valeurs(), _ctx())
    assert "◌" not in html
    assert [m for m in MOTS if m in html] == []
