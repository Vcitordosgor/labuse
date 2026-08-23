"""M22-B — LETTRE DE VÉRIFICATION DE ZONAGE : garde-fous d'honnêteté (sans réseau ni DB).

Interdits du mandat, testés :
 · une règle sans article ne s'imprime PAS ;
 · on n'affirme jamais l'absence d'une contrainte non modélisée (« ne vaut pas ») ;
 · la lettre ne se dit jamais opposable — c'est le CU (art. L.410-1) qui l'est ;
 · la taille minimale de lot est « non vérifiée » (donnée non modélisée).
"""
from __future__ import annotations

from labuse.api import lettre_zonage as lz
from labuse.faisabilite.plu_rules import A_VERIFIER


def test_fmt_regle_sans_article_ne_s_imprime_pas():
    assert lz._fmt_regle(12, "m", None) is None
    assert lz._fmt_regle(12, "m", "") is None


def test_fmt_regle_a_verifier_et_non_reglemente():
    v, src = lz._fmt_regle(A_VERIFIER, "m", "Art. 6, p.16-18")
    assert "à vérifier" in v and "Art. 6" in src
    v, src = lz._fmt_regle(None, "%", "Art. 9, p.20 : « Il n'est pas fixé de règle »")
    assert v == "non réglementé" and "Art. 9" in src
    v, _ = lz._fmt_regle(3, "m", "Art. 7.2, p.17-18")
    assert v == "3 m"


def test_identification_rend_sans_nameerror_avec_et_sans_marque():
    """M31 PC1 (régression M23-A) : _identification référençait `marque` et `_marque_bloc`
    hors portée → NameError sur TOUT PDF Lettre de zonage, non couvert par un test. Ce garde
    rend la couverture avec et sans marque (le chemin abonné et le chemin Flash/sans session)."""
    p = {"idu": "97411000AB0001", "section": "AB", "numero": "1", "commune": "Saint-Paul",
         "surface_m2": 812.0, "geojson": '{"type":"Point","coordinates":[55.3,-21.0]}'}
    rap = {"adresse": "12 rue des Cocotiers"}
    for marque in (None, {"nom": "SCI Témoin", "logo_data_uri": None}):
        html = lz._identification(p, rap, "REF-TEST-001", marque)
        assert "97411000AB0001" in html and "1 · Identification" in html
        assert "Lettre de vérification de zonage" in html


def test_identification_sans_compte_pas_de_reference_officielle():
    """M149 L1 : sans compte (ref None), la couverture se rend mais SANS numéro officiel —
    mention explicite « sans référence enregistrée », jamais un « Référence LZ-… » fabriqué."""
    p = {"idu": "97411000AB0001", "section": "AB", "numero": "1", "commune": "Saint-Paul",
         "surface_m2": 812.0, "geojson": '{"type":"Point","coordinates":[55.3,-21.0]}'}
    html = lz._identification(p, {}, None, None)
    assert "sans référence enregistrée" in html
    assert "Référence <b>" not in html          # aucun numéro officiel forgé sans compte


def test_cloture_avec_et_sans_reference():
    """M149 L1 : avec réf → attestation numérotée vérifiable ; sans réf → dit clairement que
    ce n'est PAS une attestation numérotée (pas d'émission par accident)."""
    avec = lz._cloture("LZ-2026-0001")
    assert "Attestation documentaire n°" in avec and "LZ-2026-0001" in avec
    assert "vérifier l'authenticité" in avec
    sans = lz._cloture(None)
    assert "sans référence enregistrée" in sans
    assert "n'est pas une attestation numérotée" in sans
    assert "LZ-" not in sans                     # aucun numéro affiché sans compte


def test_limites_texte_exact_et_jamais_opposable():
    html = lz._limites({"sources": []})
    assert "art. L.410-1" in html and "seul opposable" in html
    assert "taille minimale de lot" in html.lower() and "non vérifiée" in html
    # le mot « opposable » n'est JAMAIS appliqué à la lettre elle-même
    assert "lettre opposable" not in html.lower()
    for txt in (lz.LIBELLE, lz.LIMITES):
        assert "opposable" not in txt or "seul opposable" in txt


def test_servitudes_vide_n_affirme_pas_l_absence():
    html = lz._servitudes({})
    assert "ne vaut pas absence" in html
    assert "Aucune servitude" not in html          # jamais un négatif affirmé global


def test_servitudes_liste_uniquement_ce_qui_est_en_base():
    rap = {"identite": {"prescriptions": [{"libelle": "OAP 2.2", "code": ""}]},
           "risques": {"couches": [{"label": "Aléa inondation", "detail": "fort"}]},
           "patrimoine": {"couches": [], "abf": [{"name": "Chapelle"}]}}
    html = lz._servitudes(rap)
    assert "OAP 2.2" in html and "Aléa inondation" in html and "ABF" in html
    assert "ne vaut pas état exhaustif" in html


def test_zonage_non_resolu_honnete():
    html = lz._zonage([], "Saint-Paul")
    assert "non résolu" in html and "mairie" in html


def test_regles_zone_calibree_saint_paul_articles_presents():
    """Sur le YAML réel Saint-Paul : chaque ligne imprimée porte un article."""
    rz = lz._regles_zone("U1b", "Saint-Paul")
    assert rz["calibree"] and rz["lignes"]
    for _label, _val, article in rz["lignes"]:
        assert "Art." in article or "art." in article.lower()


def test_regles_zone_non_calibree_repli():
    rz = lz._regles_zone("ZZZ9", "Commune-Inconnue")
    assert rz["calibree"] is False and rz["lignes"] == []
