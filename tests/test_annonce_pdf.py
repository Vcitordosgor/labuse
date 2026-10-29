"""ANNONCE-5 — le document « Analyse d'annonce » REFONDU (miroir de l'outil Analyser une annonce).

Famille UNITAIRE (aucun marqueur db/local/reel/network → tourne dans le filet pre-push) : on teste
l'ASSEMBLAGE HTML (pur, sans base) des deux variantes à partir du RAPPORT (le point unique écran == PDF),
les garde-fous du mandat, et les helpers PURS du rapport. Le bout-en-bout (rapport_parcelle /
rapport_lien → base + WeasyPrint) est joué à la recette.

Garde-fous vérifiés ici :
  · « jamais un champ vide imprimé » — une valeur absente ne produit NI « — » NI case vide ;
  · le PDF outil == PDF Docs — même route, même builder, donc HTML DÉTERMINISTE à entrées égales ;
  · variante parcelle = 2 pages (saut `.apage2`) ; estimation + valeur indicative + comparables ;
  · variante lien = deux lectures CHIFFRÉES (bâti % + foncière €) + bloc commune complet + encart ;
  · le message d'échec du lien est IDENTIQUE à celui de l'outil (frontend messageErreur).
"""
from __future__ import annotations

from datetime import date

from labuse.exports import builder, numeros
from labuse.exports.blocs import annonce as bloc
from labuse.pige.api import (_a_verifier, _classement_phrase, _regles_zone, _risques_rows,
                             _valeur_indicative)

J = date(2026, 10, 27)

_RAPPORT_BATI = {
    "idu": "97411000AB0123", "adresse": "12 rue des Camélias", "commune": "Saint-Denis",
    "zone": "UA", "surface_m2": 504.3, "nature_label": "Parcelle bâtie, maison", "exposition": "Sud-Ouest",
    "_ref_droite": "AA-20261027-0123 · 27/10/2026",
    "estimation": {
        "type_comparateur": "bati", "type_bien": "maison", "type_label_pluriel": "maisons",
        "median": 3602, "q1": 3000, "q3": 4200, "n": 42, "radius_m": 500, "periode": [2022, 2025],
        "fiabilite": "fiable", "commune_fallback": False,
        "comparables": [{"date": "08/2025", "type": "Maison", "surface_m2": 120, "prix_eur": 450000,
                         "prix_m2": 3750, "distance_m": 103}],
        "n_total": 42, "surface_batie": {"surface_m2": 197, "niveaux": 1, "niveaux_estimes": False},
        "valeur_indicative": {"surface_m2": 197, "eur_m2": 3602, "valeur_eur": 709594,
                              "valeur_basse": 591000, "valeur_haute": 827400},
        "repere_terrain_nu": {"eur_m2": 369, "n": 15, "perimetre": "secteur", "periode": "2021–2025"},
    },
    "classement": {"bande": "D", "libelle": "Faible",
                   "phrase": "Classement D · Faible : le bâti existant consomme presque tout."},
    "foncier": {"zone": "UA", "commune": "Saint-Denis",
                "regles": [{"cle": "Hauteur maximale", "valeur": "7 m"},
                           {"cle": "Stationnement", "valeur": "1 place / logement"}],
                "parcelle": [{"cle": "Assiette constructible, aléa déduit", "valeur": "1 625 m²"},
                             {"cle": "SDP restante estimée", "valeur": "26 m²"}]},
    "risques": [{"alea": "Inondation, Mouvement de terrain", "niveau": "Zone bleue",
                 "document": "PPR Saint-Denis, 2012", "implique": "Constructible sous prescriptions."}],
    "marche": {"ventes_maison_12m": 289, "median_maison_eur_m2": 3235, "median_appartement_eur_m2": 2600,
               "median_terrain_eur_m2": 459, "evolution_maison_12m_pct": -3.3,
               "serie_maison_5a": [{"annee": 2021, "median": 3031, "n": 5},
                                   {"annee": 2024, "median": 3345, "n": 7},
                                   {"annee": 2025, "median": 3235, "n": 8}]},
    "a_verifier": ["L'état du bâti et les travaux récents, non connus du modèle.",
                   "La conformité du bâti existant avant tout projet d'extension."],
}

_RAPPORT_NUE = {
    "idu": "97413000CX0800", "adresse": None, "commune": "Saint-Leu", "zone": "UD",
    "surface_m2": 1819.0, "nature_label": "Parcelle nue", "exposition": "Ouest",
    "estimation": {"type_comparateur": "terrain_nu", "type_bien": "terrain", "median": 495,
                   "n": 78, "periode": "2021–2025", "perimetre": "secteur", "fiabilite": "fiable",
                   "commune_fallback": False, "comparables": [], "n_total": 78,
                   "valeur_indicative": {"surface_m2": 1819, "eur_m2": 495, "valeur_eur": 900405},
                   "repere_terrain_nu": {"eur_m2": 495, "n": 78, "perimetre": "secteur"}},
    "classement": {"bande": "C", "libelle": "À étudier", "phrase": "Classement C · À étudier : …"},
    "foncier": {"zone": "UD", "commune": "Saint-Leu", "regles": [], "parcelle": []},
    "risques": [], "marche": None, "a_verifier": ["La desserte et la viabilisation du terrain."],
}


# ═══════════════════════════════════════ VARIANTE PARCELLE ═══════════════════════════════════════
def test_parcelle_structure_maquette():
    html = bloc.rendu_parcelle(_RAPPORT_BATI, plan_ortho_html="<i>O</i>", plan_zonage_html="<i>Z</i>").replace("\u00a0", " ")
    # en-tête : titre = adresse, sous-titre IDU · zone · surface · nature
    assert "12 rue des Camélias" in html and "97411000AB0123" in html
    assert "Zone UA" in html and "Parcelle bâtie, maison" in html
    # les deux cartes posées dans la grille
    assert '<div class="amaps">' in html and "<i>O</i>" in html and "<i>Z</i>" in html
    # 6 tuiles + estimation + fiabilité niveau seul
    assert "Sud-Ouest" in html and "D · Faible" in html
    assert "3 602 €/m²" in html and "Fiabilité Élevée" in html
    # valeur indicative : surface × €/m² + fourchette + repère terrain nu
    assert "Valeur indicative du bien" in html and "709 594 €" in html
    assert "Maison" in html and "197 m²" in html and "× 3 602 €/m²" in html
    assert "591 000 – 827 400 €" in html and "Repère terrain nu, secteur" in html and "369 €/m²" in html
    # tableau des comparables + total
    assert "Les 8 ventes les plus proches retenues" in html and "08/2025" in html and "103 m" in html
    assert "41 autres ventes" in html and "Source : DVF, ventes de maisons" in html  # 42 - 1 montrée
    # page 2 : foncier (règles face parcelle) + classement + risques + marché + à vérifier
    assert '<div class="apage2">' in html
    assert "Le foncier" in html and "Hauteur maximale" in html and "Assiette constructible, aléa déduit" in html
    assert "Classement D · Faible : le bâti existant" in html
    assert "Risques et contraintes" in html and "Inondation, Mouvement de terrain" in html
    assert "PPR" in html and "Saint-Denis" in html and "2012" in html  # document (esc_noms insère un span nb)
    assert "Le marché · Saint-Denis" in html and "3 235 €/m²" in html
    assert "Prix médian maison" in html and 'class="barchart"' in html     # graphique 5 ans
    assert "reste à vérifier" in html and "état du bâti" in html  # items esc(apostrophe → &#x27;)


def test_parcelle_nue_pas_de_tableau_comparables():
    """Parcelle NUE : estimation terrain nu + valeur indicative = surface × repère ; AUCUN tableau de
    comparables bâti (le repère secteur tient lieu d'échantillon)."""
    html = bloc.rendu_parcelle(_RAPPORT_NUE, plan_ortho_html="", plan_zonage_html="").replace("\u00a0", " ")
    assert "Parcelle nue" in html and "495 €/m²" in html
    assert "Terrain" in html and "900 405 €" in html          # valeur indicative = contenance × repère
    assert "Les 8 ventes les plus proches retenues" not in html   # pas de tableau bâti pour une nue
    assert "(repère €/m² de terrain)." in html


def test_parcelle_jamais_un_champ_vide():
    """Tuiles/lignes sans valeur OMISES ; jamais une case de tuile vide ni un « — » imprimé."""
    r = {**_RAPPORT_BATI, "exposition": None,
         "classement": {"bande": None, "libelle": None, "phrase": None},
         "foncier": {"zone": "UA", "commune": "Saint-Denis", "regles": [], "parcelle": []},
         "marche": None, "risques": []}
    html = bloc.rendu_parcelle(r, plan_ortho_html="", plan_zonage_html="").replace("\u00a0", " ")
    assert "Exposition" not in html                       # tuile absente
    assert '<div class="v"></div>' not in html            # jamais une case de tuile vide
    assert "Le foncier" not in html                       # section vide → disparaît
    assert "Risques et contraintes" not in html and "Le marché" not in html


def test_parcelle_estimation_absente_est_sourcee():
    r = {**_RAPPORT_BATI, "estimation": {"type_comparateur": "bati", "median": None,
                                          "note": "Pas assez de ventes comparables dans le secteur."}}
    html = bloc.rendu_parcelle(r, plan_ortho_html="", plan_zonage_html="").replace("\u00a0", " ")
    assert "Estimation du prix" in html and "Pas assez de ventes comparables" in html
    assert "€/m²" not in html.split("Estimation du prix")[1].split("apage2")[0]


# ═══════════════════════════════════════ VARIANTE LIEN ═══════════════════════════════════════════
_RAPPORT_LIEN = {
    "annonce": {"type": "maison", "prix": 360000, "surface_hab": 134.0, "surface_terrain": 625.0,
                "pieces": 6, "prix_m2": 2687, "commune": "La Possession", "releve_le": "2026-10-28",
                "url": "https://www.leboncoin.fr/ad/ventes_immobilieres/1234567890",
                "description": "Maison F6 sur terrain plat de 625 m², 3 chambres à l'étage, garage double."},
    "lectures": {
        "bati": {"calculable": True, "ecart_pct": -28, "referentiel_eur_m2": 3728, "n": 114,
                 "type_label_pluriel": "maisons", "periode": 2021},
        "fonciere": {"terrain_m2": 625, "terrain_eur_m2": 474, "valeur_eur": 296250, "pct_du_prix": 82,
                     "conclusion": "Le terrain seul vaut 82 % du prix demandé : bien à valeur surtout foncière."},
    },
    "commune": {"commune": "La Possession", "ventes_maison_12m": 114, "median_maison_eur_m2": 3728,
                "median_terrain_eur_m2": 474, "evolution_maison_12m_pct": 2.2, "permis_12m": 31,
                "plu_statut": "à jour", "aleas": ["inondation", "mouvement de terrain"], "parc_national": True},
    "_ref_droite": "AA-20261027-1234567890 · 27/10/2026",
}


def test_lien_deux_lectures_chiffrees():
    html = bloc.rendu_lien(_RAPPORT_LIEN, plan_commune_html="<b>carte</b>", releve_html="Annonce Leboncoin").replace("\u00a0", " ")
    assert "Maison 6 pièces · La Possession" in html
    # ce que dit l'annonce + extrait en base (2 lignes max)
    assert "Prix demandé" in html and "360 000 €" in html and "6" in html
    assert "Maison F6 sur terrain plat" in html and "extrait, texte complet sur l'annonce" in html
    # DEUX lectures CHIFFRÉES
    assert "Lecture bâti" in html and "-28 %" in html and "face aux maisons de la commune" in html
    assert "Lecture foncière" in html and "296 250 €" in html
    assert "625 m² × 474 €/m² de terrain nu" in html
    assert "Le terrain seul vaut 82 % du prix demandé : bien à valeur surtout foncière." in html
    assert "Fiabilité Limitée" in html
    # bloc commune COMPLET : ventes, médianes, évolution, PLU, aléas, permis
    assert "La commune · La Possession" in html
    assert "3 728 €/m²" in html and "474 €/m²" in html and "+2,2 %" in html
    assert "à jour" in html and "inondation, mouvement de terrain" in html
    assert "cœur de parc" in html and "Permis déposés, 12 mois" in html and "31" in html
    # encart vers le rapport complet
    assert "Pour le rapport complet sur 2 pages" in html and "C'est cette parcelle" in html
    assert "carte" in html                      # la carte commune insérée dans .lienmap


def test_construire_lien_document_deterministe():
    res1 = builder.construire_analyse_annonce_lien(_RAPPORT_LIEN, jour=J)
    res2 = builder.construire_analyse_annonce_lien(_RAPPORT_LIEN, jour=J)
    assert res1.html == res2.html                    # même entrée → même HTML (PDF outil == PDF Docs)
    assert "Analyse d'annonce" in res1.cartouche.doc_title
    assert res1.numero == "AA-20261027-7890"   # suffixe = 4 derniers chiffres du list_id (ASCII, stable)
    assert "Voir l'annonce" in res1.html and "leboncoin.fr/ad" in res1.html
    assert "comparative" in res1.cartouche.doc_foot and "pas un avis de valeur" in res1.cartouche.doc_foot
    assert "DVF" in res1.cartouche.doc_foot and "Radar LABUSE" in res1.cartouche.doc_foot


# ═══════════════════════════════════════ HELPERS PURS ═══════════════════════════════════════════
def test_valeur_indicative_omet_si_surface_ou_mediane_absente():
    assert _valeur_indicative(197, 3602, 3000, 4200) == {
        "surface_m2": 197, "eur_m2": 3602, "valeur_eur": 709594,
        "valeur_basse": 591000, "valeur_haute": 827400}
    assert _valeur_indicative(None, 3602, None, None) is None     # pas de surface → pas de ligne
    assert _valeur_indicative(197, None, None, None) is None       # pas de médiane → pas de ligne
    assert "valeur_basse" not in _valeur_indicative(1819, 495, None, None)  # sans quartiles : pas de fourchette


def test_classement_phrase_vocabulaire_grave():
    d = _classement_phrase("D", "Faible", "bati_max")
    assert d.startswith("Classement D · Faible :") and "extension, pas dans une opération" in d
    assert _classement_phrase(None, None, "nu") is None            # pas de bande → pas de phrase
    assert "analyse incomplète" in _classement_phrase("NC", "Analyse incomplète", "nu").lower()


def test_risques_rows_tires_de_la_fiche():
    fiche = {"aleas": {"n": 1, "liste": [{
        "nature": "PPR — zone bleue",
        "libelle": "Zone bleue PPR inondation et mouvement de terrain — constructible SOUS PRESCRIPTIONS.",
        "redhibitoire": False, "source": "DEAL", "ppr": [{"document": "PPR", "approbation": "2012-10-17"}]}]}}
    rows = _risques_rows(fiche, "Saint-Denis")
    assert len(rows) == 1
    assert rows[0]["alea"] == "Inondation, Mouvement de terrain"    # aléas extraits du libellé
    assert rows[0]["niveau"] == "Zone bleue"
    assert rows[0]["document"] == "PPR Saint-Denis, 2012"           # document assemblé (PPR + commune + année)
    assert rows[0]["implique"].startswith("Constructible")
    assert _risques_rows({"aleas": {"n": 0, "liste": []}}, "X") == []


def test_a_verifier_derive_des_donnees_max_3():
    batie = _a_verifier({"aleas": {"n": 1}}, "bati_max", "Uh")
    assert len(batie) <= 3 and any("bâti" in p for p in batie) and any("PPR" in p for p in batie)
    nue = _a_verifier({"aleas": {"n": 0}}, "nu", "UD")
    assert len(nue) <= 3 and any("viabilisation" in p or "desserte" in p for p in nue)


def test_regles_zone_omet_les_non_calibrees():
    """Les règles viennent du calibrage (resolve_zone, config, sans base) ; une zone inconnue → []."""
    assert _regles_zone(None, "Saint-Denis") == []
    assert _regles_zone("ZONE_INEXISTANTE_XYZ", "Saint-Denis") == []


# ═══════════════════════════════════ CADRE / NUMÉRO / MESSAGES ═══════════════════════════════════
def test_parcelle_dans_cadre_detecte_debordement():
    assert not builder._parcelle_dans_cadre([[(100, -5), (200, -5), (200, 210)]], 720, 200, 3.0)
    assert not builder._parcelle_dans_cadre([[(-5, 50), (730, 50), (730, 150)]], 720, 200, 3.0)
    assert builder._parcelle_dans_cadre([[(50, 20), (300, 20), (300, 180), (50, 180)]], 720, 200, 3.0)
    assert not builder._parcelle_dans_cadre([], 720, 200, 3.0)


def test_plan_cadre_parcelle_allongee_verticalement():
    W, H = 720, 200
    def rendre(zd):
        if zd == 0:
            return {"ok": True, "width": W, "height": H,
                    "parcel_px": [[(350, -30), (370, -30), (370, H + 30), (350, H + 30)]]}
        return {"ok": True, "width": W, "height": H,
                "parcel_px": [[(345, 40), (375, 40), (375, H - 40), (345, H - 40)]]}
    res = builder._choisir_cadre_plan(rendre, marge_px=3.0)
    assert builder._parcelle_dans_cadre(res["parcel_px"], W, H, 3.0)
    assert res["parcel_px"][0][0] == (345, 40)


def test_numero_prefixe_analyse_annonce():
    assert numeros.numero_rapport("analyse-annonce", "97411000AB0123", J) == "AA-20261027-0123"


def test_message_echec_lien_identique_a_l_outil():
    from labuse.api.documents import _ANNONCE_ECHEC
    assert _ANNONCE_ECHEC["url_bloquee"] == (
        "Cette annonce n'a pas encore été relevée par LABUSE et Leboncoin bloque sa lecture "
        "automatique. Entrez l'adresse du bien pour l'analyser.")
    assert "pas une annonce exploitable" in _ANNONCE_ECHEC["url_illisible"]
    assert "Collez un lien" in _ANNONCE_ECHEC["url_invalide"]
