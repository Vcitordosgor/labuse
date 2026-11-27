import pytest

from labuse.copilote_v2 import resume_fiche


@pytest.mark.parametrize(("question", "champ"), [
    ("Quelle est la part non bâtie en pourcentage ?", "part_non_batie_pct"),
    ("Quelle est la surface de plancher constructible restante ?", "sdp_residuelle_m2"),
    ("Quel est le productible en kWh/kWc ?", "solaire_productible"),
    ("Quelle est la production photovoltaïque en kWh ?", "solaire_annuel"),
    ("Quelle est la puissance en kWc ?", "solaire_kwc"),
    ("Quelle est la surface de la piscine ?", "surface_piscine"),
    ("Quelle est la surface de la toiture ?", "surface_toiture"),
    ("Combien de logements vacants dans le quartier ?", "iris_vacants"),
    ("Quelle est la part de HLM dans le quartier ?", "iris_part_hlm_pct"),
    ("Combien de ménages dans le quartier ?", "iris_menages"),
    ("Quel est le montant de taxe foncière ?", "montant_foncier"),
    ("Quel est le montant de taxe d’aménagement ?", "montant_amenagement"),
])
def test_grandeur_demandee(question, champ):
    assert resume_fiche._quel_champ(question)[0] == champ


def test_part_non_batie_nulle(monkeypatch):
    fiche = {"contenance_m2": 200, "le_bien": {"surface_libre_m2": 0}}
    monkeypatch.setattr(resume_fiche, "_fiche", lambda *_: fiche)
    reponse = resume_fiche.champ_precis(None, "parcelle", "Quelle est la part non bâtie en pourcentage ?")
    assert reponse["valeur"] == 0
    assert "0,0" in reponse["texte"]
