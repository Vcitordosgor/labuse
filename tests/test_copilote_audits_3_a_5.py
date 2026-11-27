"""Contrats des audits 3 à 5, par le point d'entrée du chat, sur deux parcelles fixes."""
from types import SimpleNamespace

import pytest

from labuse.copilote_v2 import resume_fiche as rf
from labuse.copilote_v2.answering import answer

A = "97411000BZ1281"
B = "97415000BY0083"


@pytest.fixture
def donnees(monkeypatch):
    from labuse.api import modules
    from labuse.registre.moteurs import parcelle

    def fiche(db, idu):
        return {
            "contenance_m2": 2458 if idu == B else 599,
            "le_bien": {"emprise_batie_m2": 900, "surface_libre_m2": 1558,
                        "toit": {"pans_orientation_deg": [45, 225]}},
            "terrain": {"pente_moy_deg": 9.7},
            "reglement_plu": {"zones": [{"zone": "U4c", "part": .75}, {"zone": "AU", "part": .25}]},
            "viabilisation": {"cout_raccordement": {"assainissement": "Zonage non collectif."}},
            "iris_quartier": {"nom": "Le Ruisseau", "logements": 964, "vacants": 94, "menages": 826,
                              "habitants": 2210, "vacance_pct": 9.8, "part_hlm_pct": 0, "millesime": "RP2022"},
        }

    def valeurs(db, idu, data, ids):
        v = {"surface_libre_sol_m2": 1558, "emprise_batie_m2": 900, "surface_parcelle_m2": data["contenance_m2"],
             "casias_statut": None, "sdp_residuelle_m2": 453, "taxe_amenagement_estimee_eur": {"taux_communal_pct": 5},
             "distance_arret_m": {"arret": {"nom": "Le Ruisseau", "distance_m": 64}}}
        return {k: SimpleNamespace(valeur=v.get(k)) for k in ids}

    def ecole(db, idu, kind, subtype, *, sdom):
        assert (kind, subtype, sdom) == ("amenite_bpe", "C", "C1")
        return {"nom": "École témoin", "distance_m": 370}

    monkeypatch.setattr(rf, "_fiche", fiche)
    monkeypatch.setattr(rf, "_valeurs", valeurs)
    monkeypatch.setattr(parcelle, "plus_proche", ecole)
    monkeypatch.setattr(modules, "prospection_solaire_parcelle", lambda *a, **kw: {
        "kwc": 270.4, "prod_annuel": 364229, "productible": 1347, "toit_m2": 1352, "piscine": False})


@pytest.mark.parametrize(("cas", "question", "attendu"), [
    ("3.01", "Quelle est la surface non bâtie de {B} ?", "1558 m²"),
    ("3.02", "Quel est l’azimut des pans du toit de {B} ?", "45°, 225°"),
    ("3.03", "Assainissement collectif sur {B} ?", "non collectif"),
    ("3.05", "Risque CASIAS sur {B} ?", "CASIAS"),
    ("3.06", "Surface de {B} en ha ?", "0,2458 ha"),
    ("3.07", "Quel écart de surface entre {A} et {B} ?", "1859 m²"),
    ("3.08", "Quelle population dans le quartier de {B} ?", "2210 habitants"),
    ("3.08", "Quel taux de vacance dans le quartier de {B} ?", "9,8%"),
    ("3.09", "Quelle puissance photovoltaïque sur {B} ?", "270,4 kWc"),
    ("3.11", "Combien de logements dans le quartier de {B} ?", "964 logements"),
    ("3.12", "Taxe d’aménagement sur {B} ?", "5,0%"),
    ("3.12", "Taxe d'aménagement sur {B} ?", "5,0%"),
    ("3.13", "Quelle école primaire est la plus proche de {B} ?", "École témoin à 370 m"),
    ("3.14", "Quel pourcentage de {B} est bâti ?", "36,6%"),
    ("4.02", "Surface de la piscine sur {B} ?", "aucune piscine détectée"),
    ("4.02", "Emprise du toit de {B} ?", "1352 m²"),
    ("4.03", "Quel pourcentage non bâti sur {B} ?", "63,4%"),
    ("4.04", "Quel productible solaire en kWh/kWc sur {B} ?", "1347 kWh/kWc/an"),
    ("4.04", "Quelle production annuelle en kWh sur {B} ?", "364229 kWh/an"),
    ("4.05", "Combien de logements vacants dans le quartier de {B} ?", "94 logements vacants"),
    ("4.05", "Combien de ménages dans le quartier de {B} ?", "826 ménages"),
    ("4.05", "Part de HLM dans le quartier de {B} ?", "0,0%"),
    ("4.06", "Surface de plancher constructible restante sur {B} ?", "453 m²"),
    ("4.07", "Surface moyenne de {B} et {A} ?", "1528,5 m²"),
    ("4.08", "Montant de taxe foncière sur {B} ?", "base imposable"),
    ("4.08", "Montant de taxe d’aménagement sur {B} ?", "surface taxable"),
    ("4.09", "Distance en km à l’arrêt de bus de {B} ?", "0,064 km"),
    ("5.01", "Calcule 3 % de 1,2 million d’euros.", "= 36000 €"),
    ("5.01", "Combien font 5 pour cent de 300 milliers d'euros ?", "= 15000 €"),
    ("5.02", "Calcule -10 % de 600 €.", "= -60 €"),
    ("5.02", "Calcule −5 % de 900 euros.", "= -45 €"),
    ("5.03", "Quel prix après une remise de 10 % sur 600 € ?", "final : 540 €"),
    ("5.03", "Prix après une hausse de 5 % sur 900 € ?", "final : 945 €"),
    ("5.03", "Quel est le total TTC, TVA de 20 % sur 500 € HT comprise ?", "600 €"),
    ("5.04", "Calcule 10 % de 2 ha en m².", "= 2000 m²"),
    ("5.04", "Calcule 25 % de 400 m² en hectares.", "= 0,01 ha"),
    ("5.05", "Calcule 10 % de la surface de la parcelle {B}.", "= 245,8 m²"),
    ("5.06", "Quelle est la pente du terrain en pourcentage sur {B} ?", "17,1%"),
    ("5.07", "Combien de panneaux photovoltaïques de 400 Wc sur {B} ?", "676"),
    ("5.07", "Combien de panneaux de 0,4 kWc sur {B} ?", "676"),
    ("5.08", "Quelle production photovoltaïque moyenne par mois sur {B} ?", "30352,4 kWh/mois"),
    ("5.09", "Quelle est la surface de la zone U sur {B} ?", "1844 m²"),
    ("5.09", "Superficie en ha de la zone AU sur {B} ?", "0,06145 ha"),
])
def test_reponse(donnees, cas, question, attendu):
    rep = answer(None, question.format(A=A, B=B))
    assert not rep.get("erreur")
    assert compact(attendu) in compact(rep["text"])


def compact(s):
    return "".join(s.lower().split())


@pytest.mark.parametrize(("suite", "attendu"), [
    ("Et en hectares ?", "0,2458 ha"),  # 3.04
    ("Calcule 10 % de ce chiffre.", "245,8 m²"),  # 5.05
])
def test_reprise_de_la_mesure(donnees, suite, attendu):
    q = f"Quelle est la surface de {B} ?"
    premiere = answer(None, q, contexte={"idu": A})  # 4.01
    assert premiere["voie"]["idu"] == B and "2458" in compact(premiere["text"])
    h = [{"role": "user", "content": q}, {"role": "assistant", "content": premiere["text"]}]
    seconde = answer(None, suite, history=h, prior_params=premiere["_route"]["params"])
    assert compact(attendu) in compact(seconde["text"])
