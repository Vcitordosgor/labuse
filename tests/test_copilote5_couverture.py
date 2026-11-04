"""COPILOTE-5 — couverture totale : chaque outil / carte a son champ Copilote, lu du MÊME robinet.

Tests DÉTERMINISTES (sans base ni IA) sur le ROUTAGE des champs (`resume_fiche._quel_champ`) et les
SOURCES par fait, + la résolution d'entrée et le bridage web. Les assertions sur la VALEUR servie
(contre une parcelle témoin) sont GARDÉES par un skip si le témoin est absent de la base du hook
(elles sont vérifiées contre la base de dev et dans la recette COPILOTE-5).
"""
from __future__ import annotations

import pytest

from labuse.copilote_v2 import answering as A
from labuse.copilote_v2 import resume_fiche as RF


# ── 1. ROUTAGE DES CHAMPS — chaque famille d'outil tombe sur le bon extracteur robinet ──
@pytest.mark.parametrize("question, cid", [
    # fiche parcelle — sections
    ("Quelle est l'adresse de la parcelle ?", "adresse_ban"),
    ("Quelle est l'emprise bâtie ?", "emprise_batie_m2"),
    ("Combien de bâtiments sur la parcelle ?", "n_batiments"),
    ("Quelle est la toiture ?", "nature_toit"),
    ("La parcelle a-t-elle la fibre ?", "fibre_parcelle"),
    ("La parcelle est-elle viabilisée ?", "viabilisation_verdict"),
    ("Quel est l'arrêt de bus le plus proche ?", "distance_arret_m"),
    ("Y a-t-il des servitudes ?", "dispositifs_parcelle"),
    ("La parcelle est-elle polluée ?", "casias_statut"),
    ("Dans quel quartier est la parcelle ?", "iris_quartier"),
    ("Quelles écoles à proximité ?", "equipements_proximite_liste"),
    ("Quelle est la surface libre au sol ?", "surface_libre_sol_m2"),
    ("Le PLU est-il à jour ?", "statut_plu"),
    # outils du menu → champ dédié
    ("Quel est le gabarit constructible ?", "gabarit_implantation_m2"),
    ("Peux-tu estimer la valeur du bien ?", "prix_sortie_bati_eur_m2"),
    ("Quel est le potentiel solaire ?", "pente_toit_deg"),
    ("Quel est l'historique de propriété / succession ?", "proprietaire_timeline_liste"),
    ("Y a-t-il une annonce à vendre ?", "radar_annonces_liste"),
    ("Que montre l'étude de zone autour ?", "voisinage_100m_liste"),
    ("Quel est le prix du terrain au secteur ?", "prix_terrain_secteur_eur_m2"),
    ("Quelles sont les dernières ventes autour ?", "dvf_parcelle_liste"),
    # non-régression des champs COPILOTE-3
    ("Quelle est la zone PLU ?", "zone_plu_famille"),
    ("Quelle est la surface ?", "surface_parcelle_m2"),
    ("À qui appartient la parcelle ?", "type_proprietaire"),
])
def test_routage_champ(question, cid):
    cible = RF._quel_champ(question)
    assert cible is not None and cible[0] == cid, (question, cible)


def test_mots_courts_ne_sont_pas_happes():
    # « plu » (≤3 car. → bornes de mot) ne doit pas être happé par « plus proche » ; « étude de zone »
    # ne doit pas tomber sur la zone PLU (ordre : la phrase spécifique d'abord).
    assert RF._quel_champ("quel est l'arrêt de bus le plus proche")[0] == "distance_arret_m"
    assert RF._quel_champ("que montre l'étude de zone")[0] == "voisinage_100m_liste"
    # une question qui ne contient QUE « plus » (pas « plu ») ne mappe pas la zone.
    c = RF._quel_champ("donne-moi un peu plus de détails")
    assert c is None or c[0] != "zone_plu_famille"


def test_chaque_champ_a_une_source():
    # tout extracteur mappé dans _CHAMPS porte une source lisible (jamais « cadastre » par défaut muet).
    for kws, (cid, _lib) in RF._CHAMPS:
        assert RF._source_champ(cid), cid


# ── 2. RÉSOLUTION D'ENTRÉE — détection déterministe (sans base) ──
def test_resolveur_detecte_adresse_et_cede_le_reste():
    from labuse.copilote_v2 import resolveur as R
    assert R._extraire_adresse("3 chemin de la Citerne 97417 La Montagne")[1] == 3
    assert R._extraire_adresse("combien de parcelles à Saint-Paul") is None
    assert R._extraire_adresse("c'est quoi une rue") is None


# ── 3. WEB BRIDÉ — `_est_domaine_labuse` = « ça nomme une parcelle/adresse/proprio/commune ? ». Si oui,
# le fallback `_sans_outil` ne part JAMAIS sur le web (honnête). Un maire NOMME une commune → True
# (domaine), mais il est routé vers recherche_web EN AMONT par le sélecteur — il n'atteint pas le
# fallback. Une pure notion (loi Girardin) ne nomme aucun objet LABUSE → False → web.
@pytest.mark.parametrize("message, labuse", [
    ("Y a-t-il des termites sur la parcelle 97404000AV0167 ?", True),
    ("le 3 chemin de la citerne est-il pollué ?", True),
    ("quel est le prix du foncier à Saint-Denis ?", True),
    ("qui est le maire de Saint-Benoît ?", True),     # nomme une commune → domaine (web décidé en amont)
    ("c'est quoi la loi Girardin ?", False),          # notion pure → web
    ("quel temps fait-il aujourd'hui ?", False),
])
def test_domaine_labuse(message, labuse):
    assert A._est_domaine_labuse(message, {}) is labuse


# ── 4. VALEUR SERVIE (gardée) — contre une parcelle témoin si présente dans la base ──
TEMOIN = "97411000BZ1065"


def _skip_si_absent(db):
    fiche = RF._fiche(db, TEMOIN)
    if fiche is None:
        pytest.skip(f"témoin {TEMOIN} absent de cette base")
    return fiche


def test_valeurs_tool_facts_db():
    from labuse.db import session_factory
    db = session_factory()()
    _skip_si_absent(db)
    # chaque outil à chiffres rend une phrase LISIBLE (jamais un dict brut) avec sa source.
    for q in ("Quel est le gabarit constructible de la parcelle %s ?" % TEMOIN,
              "Peux-tu estimer la valeur du bien sur la parcelle %s ?" % TEMOIN,
              "Quel est le potentiel constructible de la parcelle %s ?" % TEMOIN,
              "Dans quel quartier est la parcelle %s ?" % TEMOIN):
        rep = A.answer(db, q)
        txt = rep.get("text") or ""
        assert txt and "{" not in txt and "}" not in txt, q      # jamais un dict brut
        assert rep.get("sources"), q                             # une source servie
        assert not rep.get("general") and not rep.get("web"), q  # jamais le web sur une parcelle
