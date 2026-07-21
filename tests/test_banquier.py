"""O1 — DOSSIER BANQUIER : tests des briques d'affichage (sans réseau ni DB).

Garde-fous : chaque section porte Sourcé/Estimé ; « non estimable » (jamais un chiffre inventé)
quand la donnée manque ; la synthèse de repli ne concatène QUE des faits fournis (aucune invention) ;
jamais de score interne / RR en vitrine.
"""
from __future__ import annotations

from types import SimpleNamespace as NS

from labuse.api import banquier as b


def _step(label, valeur, prov=""):
    return NS(label=label, formule="x", valeur=valeur, source="src", prov=prov)


def _out_complet():
    fais = NS(zone="U", zone_resolue="UB", constructible=True, verdict="ok",
              steps=[_step("Surface de plancher", "600 m²", "derive"),
                     _step("Prix DVF", "3500 €/m²", "sourcee")],
              hypotheses=[], avertissements=["recul à vérifier"], modulation=[],
              fourchette={"shab_vendable_m2": 480, "logements_au_sol": (6, 9), "hauteur_m": 9},
              bandeau="Pré-faisabilité indicative.")
    bilan = NS(fiable=True, fiabilite="fiable", verdict="ok", prix_dvf={}, ca={},
               charge_fonciere={"bas": 200000, "central": 350000, "haut": 500000, "par_m2_terrain": 350},
               steps=[_step("Chiffre d'affaires", "1,7 M€", "derive")],
               hypotheses=[], avertissements=[], bandeau="Bilan indicatif.")
    return {
        "parcelle": {"idu": "97411000AB0001", "commune": "Saint-Denis", "section": "AB",
                     "numero": "1", "surface_m2": 1000, "geojson": "{}"},
        "rapport": {"adresse": "1 rue Test", "identite": {
            "zones": [{"libelle": "UB", "classe": "U", "pct": 100, "idurba": "974xxx"}],
            "regles": {"emprise_max_m2": 400, "hauteur_max_m": 12}, "prescriptions": []},
            "risques": {"couches": [{"label": "Aléa inondation", "detail": "faible"}]},
            "patrimoine": {"couches": [], "abf": [{"name": "Cathédrale"}]}},
        "faisabilite": fais, "bilan": bilan,
        "prix_dvf": {"median": 3500, "q1": 3000, "q3": 4000, "n": 22, "periode": "2021-2024",
                     "fiabilite": "fiable", "radius_m": 1000, "commune_fallback": False,
                     "comparables": {"n_ancien": 15, "mediane_ancien": 3200, "n_vefa": 7,
                                     "mediane_vefa": 3900, "ecart_vefa_ancien_pct": 22}},
        "score_e": {"estimable": True, "marge_estimee": 250000, "charge_supportable": 350000,
                    "prix_probable": 100000, "niveau_prix": "secteur", "libelle_court": "…",
                    "detail": "Marge estimée …"},
        "permits": {"n": 3, "items": [{"date": "2023-01", "type_label": "PC", "distance_m": 120, "statut": "accordé"}]},
        "zan": {"insee": "97411", "commune": "Saint-Denis", "conso_2011_2021_m2": 1_200_000,
                "conso_2021_2024_m2": 300_000, "source_nom": "Cerema", "millesime": "2024"},
    }


def test_puce_source_estime_absent():
    assert "Sourcé" in b._s("S") and "Estimé" in b._s("E") and "non estimable" in b._s("A")


def test_eur_format():
    assert b._eur(None) == "—" and "M€" in b._eur(2_500_000) and "k€" in b._eur(350_000)


def test_bilan_porte_score_e_et_estime():
    html = b._bilan(_out_complet())
    assert "Score É" in html and "charge foncière" in html.lower()
    assert "Estimé" in html and "250 k€" in html          # marge Score É rendue
    assert "RR" not in html and "percentile" not in html   # jamais de score interne en vitrine


def test_comparables_ancien_vefa_sources():
    html = b._comparables(_out_complet())
    assert "Sourcé" in html and "VEFA" in html and "3900" in html and "SITADEL" in html


def test_bilan_niveau_prix_visible_wording_vic():
    # exigence Vic (flag Score É levé) : le niveau du prix visible en clair dans le dossier banquier
    out = _out_complet()
    out["score_e"]["niveau_prix"] = "commune"
    assert "estimation niveau commune (repli)" in b._bilan(out)
    out["score_e"]["niveau_prix"] = "secteur"
    assert "estimation niveau secteur" in b._bilan(out)


def test_score_e_non_estimable_pas_de_chiffre():
    out = _out_complet()
    out["score_e"] = {"estimable": False, "marge_estimee": None, "charge_supportable": None,
                      "prix_probable": None, "niveau_prix": None, "libelle_court": "", "detail": ""}
    html = b._bilan(out)
    assert "non estimable" in html and "None" not in html


def test_faisabilite_absente_non_estimable():
    out = _out_complet(); out["faisabilite"] = None
    html = b._faisabilite(out)
    assert "non estimable" in html


def test_synthese_facts_sans_invention():
    out = _out_complet()
    facts = b._facts_synthese(out, __import__("labuse.ai.core", fromlist=["core"]))
    # tous les faits ont une provenance ; le repli déterministe ne cite que ces faits
    assert all(hasattr(f, "provenance") for f in facts.values())
    fallback = " · ".join(f.value for f in facts.values())
    assert "1000 m²" in fallback and "charge foncière" in fallback
    assert "RR" not in fallback                              # aucun score interne
