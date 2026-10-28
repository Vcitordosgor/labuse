"""ANNONCE-3 — le document « Analyse d'annonce » (miroir de l'outil Analyser une annonce).

Famille UNITAIRE (aucun marqueur db/local/reel/network → tourne dans le filet pre-push) : on teste
l'ASSEMBLAGE HTML (pur, sans base) des deux variantes + les garde-fous du mandat. Le rendu PDF réel
(WeasyPrint) et la variante parcelle de bout en bout (parcel_fiche → base) sont joués à la recette.

Garde-fous vérifiés ici :
  · « jamais un champ vide imprimé » — une valeur absente ne produit NI « — » NI case vide, et les
    champs non applicables au type restent masqués (comme à l'écran) ;
  · le PDF outil == PDF Docs — même route, même builder, donc HTML DÉTERMINISTE à entrées égales ;
  · l'estimation est COMPARATIVE (pied de page) ; la phrase « localisez la parcelle… » est présente ;
  · le message d'échec du lien est IDENTIQUE à celui de l'outil (frontend messageErreur).
"""
from __future__ import annotations

from datetime import date

from labuse.exports import builder, numeros
from labuse.exports.blocs import annonce as bloc

J = date(2026, 10, 27)

_FICHE = {
    "idu": "97411000AB0123", "adresse": "12 rue des Camélias", "commune": "Saint-Denis",
    "surface_m2": 504.3,
    "reglement_plu": {"zones": [{"zone": "UA"}]},
    "potentiel_transformation": {"sdp_residuelle_m2": 320.0, "hauteur_regle_m": 9.0,
                                 "estimation_simplifiee": True},
    "aleas": {"n": 0},
    "prix_ancien": {"median": 3602, "q1": 3000, "q3": 4200, "n": 15, "radius_m": 1000,
                    "periode": [2023, 2025], "fiabilite": "fiable", "type_prix": "maison"},
}


# ANNONCE-3-FIX — l'estimation est un dict UNIFIÉ (point `estimation_annonce`) passé au bloc.
_EST_BATI = {"type_comparateur": "bati", "nature": "batie", "median": 3602, "q1": 3000, "q3": 4200,
             "n": 15, "radius_m": 1000, "periode": [2023, 2025], "fiabilite": "fiable", "type_prix": "maison"}
_EST_TERRAIN = {"type_comparateur": "terrain_nu", "nature": "nue", "median": 210,
                "fiabilite": "fiable", "commune_fallback": False,
                "note": "médiane DVF terrain du secteur (n ≥ 3)"}


def test_parcelle_contenu_miroir_ecran():
    html = bloc.rendu_parcelle(_FICHE, {"orientation": "Sud-Ouest"}, {"bande": "B", "libelle": "Bonne"}, _EST_BATI)
    # titre de section « La parcelle » (ANNONCE-3-FIX), 6 tuiles, estimation, foncier
    assert "La parcelle" in html and "Analyse d&#x27;annonce" not in html
    assert "UA" in html and "Sud-Ouest" in html and "B · Bonne" in html
    assert "aucun aléa" in html                      # 0 aléa = donnée présente, pas un vide
    assert "€/m²" in html
    # badge fiabilité = niveau SEUL (« Fiabilité » est l'étiquette kv à côté), pas « Fiabilité : élevée »
    assert "Élevée" in html and "Fiabilité : élevée" not in html and "Fiabilité : Élevée" not in html
    assert "Parcelle bâtie" in html and "bâti ancien" in html      # la note DIT le comparateur
    assert "Estimation du prix" in html and "Le foncier" in html
    assert "Hauteur réglementaire" in html and "estimation simplifiée" in html
    assert "à" in html and "3" in html and "200" in html           # fourchette q1/q3


def test_parcelle_estimation_selon_nature_terrain():
    """Parcelle NUE → repère €/m² de TERRAIN NU ; la note dit qu'on compare au terrain nu."""
    html = bloc.rendu_parcelle(_FICHE, {"orientation": "Est"}, {}, _EST_TERRAIN)
    assert "Parcelle nue" in html and "TERRAIN NU" in html
    assert "210" in html and "€/m²" in html
    assert "Ventes comparables" not in html          # pas de N pour le repère terrain (jamais un vide)


def test_parcelle_jamais_un_champ_vide():
    """Exposition, classement et SDP absents → tuiles OMISES, aucune case de tuile vide."""
    fiche = {**_FICHE, "potentiel_transformation": {}, "aleas": {"n": 2}}
    html = bloc.rendu_parcelle(fiche, {"orientation": None}, {"bande": None, "libelle": None}, _EST_BATI)
    assert "Exposition" not in html            # tuile absente (pas de valeur)
    assert "Classement LABUSE" not in html     # tuile absente
    assert "SDP restante" not in html          # tuile absente
    assert '<div class="v"></div>' not in html  # jamais une case de tuile vide
    assert "2 aléas" in html                   # mais le compte d'aléas (présent) s'imprime


def test_parcelle_estimation_absente_est_sourcee():
    """Sans médiane, l'estimation dit une absence SOURCÉE (pas un vide), comme l'écran."""
    html = bloc.rendu_parcelle(_FICHE, {"orientation": "Est"}, {}, {"type_comparateur": "bati", "median": None})
    assert "Indisponible" in html and "ventes comparables" in html
    assert "€/m²" not in html.split("Estimation du prix")[1].split("Le foncier")[0]


def test_estimation_annonce_helper_nature():
    """`estimation_annonce` choisit le comparateur selon la NATURE lue de `parcel_residuel.taux_emprise_pct`
    (l'indicateur du résiduel/scoring), PAS du champ `etat_bien` de la fiche : bâtie (taux ≥ 5) → bâti
    (prix_ancien) ; nue (taux < 5) → terrain nu (`_prix_terrain_local`)."""
    from labuse.pige.api import estimation_annonce

    class _FakeDB:
        """Simule `parcel_residuel` : le mapping porte t (taux), s (sdp) ET prix (médiane terrain)."""
        def __init__(self, row): self._row = row
        def execute(self, *a, **k):
            row = self._row
            class _R:
                def mappings(self_):
                    class _M:
                        def first(self__): return row
                    return _M()
            return _R()

    # BÂTIE : taux ≥ 5 → comparateur bâti (prix_ancien de la fiche)
    batie = estimation_annonce(_FakeDB({"t": 30.0, "s": 0}), "97411000AB0123",
                               {"prix_ancien": {"median": 3602, "n": 15}})
    assert batie["type_comparateur"] == "bati" and batie["median"] == 3602

    # NUE : taux < 5 → repère terrain nu (médiane secteur via _prix_terrain_local)
    nue = estimation_annonce(_FakeDB({"t": 0.0, "s": 1412, "prix": 210.0}), "97411000AB0123", {})
    assert nue["type_comparateur"] == "terrain_nu" and round(nue["median"]) == 210


def test_commune_type_pilote_les_lignes():
    """terrain → « Surface du terrain », JAMAIS « Pièces » ; champs non applicables masqués (écran)."""
    annonce = {"type": "terrain", "prix": 150000, "prix_m2": 300, "surface_terrain": 500,
               "surface_hab": None, "pieces": None, "commune": "Saint-Denis", "releve_le": "2026-10-27"}
    html = bloc.rendu_commune(annonce, None, None)
    assert "Surface du terrain" in html and "Pièces" not in html
    assert "Prix demandé" in html and "150" in html


def test_commune_np_pour_attendu_absent_pas_de_tiret():
    """Un champ ATTENDU pour le type mais absent → « non précisé dans l'annonce » (pas « — »)."""
    annonce = {"type": "appartement", "prix": None, "surface_hab": 60, "pieces": None,
               "commune": "Saint-Paul", "releve_le": "2026-10-27"}
    html = bloc.rendu_commune(annonce, None, None)
    assert "non précisé dans l'annonce" in html      # prix + pièces attendus et absents
    assert "Pièces" in html                          # applicable à l'appartement → affiché


def test_commune_prix_face_marche_et_phrase_gravee():
    marche = {"calculable": True, "ecart_libelle": "+33 %", "repere_perimetre": "appartements",
              "referentiel_eur_m2": 2700, "n_referentiel": 40, "periode": "2024", "fiabilite": "limitee"}
    ctx = {"plu_statut": {"statut": "PLU"}, "risques": {"ppr_pct": 5, "parc_national": True}}
    annonce = {"type": "appartement", "prix": 300000, "surface_hab": 60, "pieces": 3,
               "commune": "Saint-Denis", "releve_le": "2026-10-27"}
    html = bloc.rendu_commune(annonce, marche, ctx)
    # badge = niveau SEUL « Limitée » (l'étiquette « Fiabilité » est la clé kv), pas « Fiabilité : limitée »
    assert "+33 %" in html and "Limitée" in html and "Fiabilité : limitée" not in html
    assert "Localisez la parcelle" in html           # phrase gravée du mandat
    assert "inondation" in html and "parc national" in html    # aléas déduits comme l'écran
    assert "La commune · Saint-Denis" in html


def test_commune_la_commune_omet_les_lignes_absentes():
    """Repère non calculable + contexte vide → « La commune » n'imprime aucune ligne « — »."""
    annonce = {"type": "maison", "prix": 400000, "surface_hab": 90, "surface_terrain": 600,
               "pieces": 4, "commune": "Le Port", "releve_le": "2026-10-27"}
    html = bloc.rendu_commune(annonce, {"calculable": False, "motif": "échantillon insuffisant"}, {})
    assert "—" not in html
    assert "Comparaison au marché indisponible" in html or "échantillon insuffisant" in html


def test_construire_lien_document_complet_et_deterministe():
    """Le document commun (variante lien) : titre, numéro AA-, pied comparatif, « relevée le ». Même
    entrée → HTML IDENTIQUE (preuve que PDF outil == PDF Docs : même route, même builder)."""
    annonce = {"type": "terrain", "prix": 150000, "prix_m2": 300, "surface_terrain": 500,
               "commune": "Saint-Denis", "releve_le": "2026-10-27"}
    marche = {"calculable": True, "ecart_libelle": "+10 %", "repere_perimetre": "terrains",
              "referentiel_eur_m2": 270, "n_referentiel": 22, "periode": "2024"}
    res1 = builder.construire_analyse_annonce_lien(annonce, marche, None, jour=J)
    res2 = builder.construire_analyse_annonce_lien(annonce, marche, None, jour=J)
    assert res1.html == res2.html                    # déterministe → outil et Docs rendent la MÊME chose
    assert "Analyse d'annonce" in res1.cartouche.doc_title   # titre humain (le HTML l'échappe en d&#x27;)
    assert res1.numero.startswith("AA-20261027-")
    assert "Annonce Leboncoin" in res1.html and "relevée le 27/10/2026" in res1.html
    assert "Terrain · Saint-Denis" in res1.html
    # pied de page (cartouche) : estimation COMPARATIVE, pas un avis de valeur
    assert "comparative" in res1.cartouche.doc_foot and "pas un avis de valeur" in res1.cartouche.doc_foot
    assert "DVF" in res1.cartouche.doc_foot and "Radar LABUSE" in res1.cartouche.doc_foot


def test_numero_prefixe_analyse_annonce():
    assert numeros.numero_rapport("analyse-annonce", "97411000AB0123", J) == "AA-20261027-0123"


def test_message_echec_lien_identique_a_l_outil():
    """Le message d'échec du lien (route Docs/outil) reprend MOT POUR MOT celui de l'outil (front)."""
    from labuse.api.documents import _ANNONCE_ECHEC
    assert _ANNONCE_ECHEC["url_bloquee"] == (
        "Cette annonce n'a pas encore été relevée par LABUSE et Leboncoin bloque sa lecture "
        "automatique. Entrez l'adresse du bien pour l'analyser.")
    assert "pas une annonce exploitable" in _ANNONCE_ECHEC["url_illisible"]
    assert "Collez un lien" in _ANNONCE_ECHEC["url_invalide"]
