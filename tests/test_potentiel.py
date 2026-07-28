"""M22-D — RAPPORT DE POTENTIEL : garde-fous (sans réseau ni DB).

Interdits du mandat, testés :
 · divisibilité : l'encadré du RAPPORT reste sans chiffre du détecteur (« étude
   complémentaire ») ; O12 est EXPOSÉ depuis le 28/07/2026 (clôture O12-PARTIEL-2 J,
   feu vert Vic) — le test atteste le nouvel invariant : pool figé 35, recheck branché ;
 · aucune identité de propriétaire dans le document ;
 · aucune valorisation en euros de la division ;
 · incertitude SDP dite en clair (« estimation sur la base d'un bâti de N niveau(x) ») ;
 · « pas de potentiel identifié » est un résultat honnête, rendu tel quel.
"""
from __future__ import annotations

from labuse.api import potentiel as pt


def _out(residuel=None, couches=None):
    return {
        "parcelle": {"idu": "97415000AC0197", "commune": "Saint-Paul", "section": "AC",
                     "numero": "197", "surface_m2": 1500, "geojson": "{}"},
        "rapport": {"identite": {"prescriptions": []},
                    "risques": {"couches": couches or []},
                    "patrimoine": {"couches": [], "abf": []},
                    "sources": [{"section": "risques", "source": "Géorisques", "millesime": "2026"}]},
        "residuel": residuel if residuel is not None else {
            "disponible": True, "sdp_max_m2": 900, "sdp_existante_m2": 250,
            "sdp_residuelle_m2": 650, "taux_emprise_pct": 25, "pct_potentiel": 28,
            "sous_densite": True, "niveaux_existants": 1.0, "niveaux_reels": False,
            "estimation_sdp": True, "capacite_estimee": False,
            "libelle": "Forte sous-densité — potentiel d'extension."},
        "prix_dvf": None, "permits": None,
    }


def test_o12_expose_par_decision():
    """O12 EXPOSÉ (feu vert Vic 28/07/2026, clôture O12-PARTIEL-2 J — 2 revues visuelles
    exhaustives + verdict de calibrage PLU). Ce test atteste la DÉCISION : re-masquer (ou
    ré-exposer autrement) casse la suite par construction — grille dette-repo, catégorie A."""
    from labuse.ingestion import division_or as d
    assert d.EXPOSE is True


def _pool_o12_reference():
    """Référence VERSIONNÉE du pool revu (clôture O12) : (lignes pool_complet, idus découpes)."""
    import csv
    from pathlib import Path
    rep = Path(__file__).resolve().parent.parent / "reports" / "o12-ile"
    with open(rep / "pool_complet.csv", encoding="utf-8") as fh:
        complet = list(csv.DictReader(fh))
    with open(rep / "pool_decoupe.csv", encoding="utf-8") as fh:
        decoupes = {r["idu"] for r in csv.DictReader(fh)}
    return complet, decoupes


def test_o12_pool_reference_35_fige():
    """Pool servi conforme à la clôture : 35 candidats (27 découpes + 8 résiduels), les
    découpes coïncident avec les tracés revus, BO0089 (tombé au verdict emprise) absent."""
    complet, decoupes = _pool_o12_reference()
    idus = {r["idu"] for r in complet}
    assert len(complet) == 35 and len(idus) == 35            # 35 uniques, pas de doublon
    n_dec = sum(1 for r in complet if r["type_division"] == "decoupe")
    assert n_dec == 27 and len(complet) - n_dec == 8         # 27 découpes + 8 résiduels
    assert {r["idu"] for r in complet if r["type_division"] == "decoupe"} == decoupes
    assert "97418000BO0089" not in idus                      # faux positif du verdict emprise


def test_o12_emprise_recheck_branche():
    """La dépendance récurrente reste CÂBLÉE : le script de re-vérification d'emprise existe,
    le module la documente (à relancer après chaque évolution PLU), le script vise le pool."""
    from pathlib import Path
    racine = Path(__file__).resolve().parent.parent
    script = racine / "scripts" / "o12_emprise_recheck.py"
    assert script.exists()
    src = (racine / "src" / "labuse" / "ingestion" / "division_or.py").read_text(encoding="utf-8")
    assert "o12_emprise_recheck" in src                      # dépendance documentée côté module
    assert "division_or" in script.read_text(encoding="utf-8")


def test_divisibilite_encadre_sans_aucun_chiffre():
    import re
    html = pt._divisibilite()
    assert "étude complémentaire" in html
    # aucun chiffre du détecteur (surfaces, façades, seuils) — hors numéro de section du titre
    corps = re.sub(r"<h2>.*?</h2>", "", html)
    assert not any(ch.isdigit() for ch in corps)


def test_division_jamais_valorisee_en_euros():
    out = _out()
    doc = "".join([pt._synthese(out), pt._extension(out), pt._divisibilite(),
                   pt._avant_compromis(out), pt._limites(out)])
    # les seules mentions € viendraient du marché DVF (contexte) — pas des sections potentiel
    assert "€" not in doc


def test_aucune_identite_proprietaire():
    out = _out()
    doc = "".join([pt._synthese(out), pt._extension(out), pt._avant_compromis(out)])
    for mot in ("propriétaire", "SIREN", "dénomination"):
        assert mot.lower() not in doc.lower()


def test_estimation_sdp_dite_en_clair():
    html = pt._extension(_out())
    assert "ESTIMATION" in html and "1 niveau(x)" in html


def test_sans_potentiel_resultat_honnete():
    r = {"disponible": True, "sdp_max_m2": 300, "sdp_existante_m2": 530,
         "sdp_residuelle_m2": 0, "taux_emprise_pct": 133, "pct_potentiel": 177,
         "sous_densite": False, "niveaux_existants": 1.3, "niveaux_reels": True,
         "estimation_sdp": False, "capacite_estimee": False, "libelle": "Densité atteinte."}
    import html as _h
    html = _h.unescape(pt._synthese(_out(residuel=r)))
    assert "Pas de potentiel d'extension identifié" in html


def test_rien_a_signaler_affirme_sur_le_verifie_seulement():
    html = pt._avant_compromis(_out(couches=[]))
    assert "couches vérifiées" in html and "ne remplace pas" in html
    html2 = pt._avant_compromis(_out(couches=[{"label": "Aléa inondation", "detail": "fort"}]))
    assert "Aléa inondation" in html2
