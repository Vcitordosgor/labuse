from types import SimpleNamespace

import pytest

from labuse.implantation.programme_maximum import ProgrammeMaximum
from labuse.implantation.service import valider_entree_etude


@pytest.mark.parametrize("parts, fixes", [
    ({"T1": 99}, {}), ({"T2": 100}, {"T2": 1}), ({"T5": 100}, {}),
    ({"T2": 100}, {"T3": -1}), ({"T2": 100}, {"T3": True}),
])
def test_composition_invalide_refusee_avant_calcul(parts, fixes):
    with pytest.raises(ValueError):
        valider_entree_etude({"idus": ["parcelle"], "programme": {
            "mode": "maximum", "parts": parts, "fixes": fixes,
        }})


def test_pourcentages_appliques_apres_les_quantites_fixes():
    programme = ProgrammeMaximum({"T4": 10}, {"T2": 97, "T3": 3})
    assert programme.cible(13) == {"T4": 10, "T2": 3, "T3": 0}
    assert programme.cible(110) == {"T4": 10, "T2": 97, "T3": 3}


def test_quantite_imposee_ne_retire_aucun_module_au_rez_de_chaussee():
    objets = [SimpleNamespace(kind="module", type_logement=t, niveau=n)
              for n in (0, 1) for t in ("T2", "T3", "T3")]
    scene = SimpleNamespace(objets=objets)
    assert not ProgrammeMaximum({"T3": 1}, {"T2": 100}).ajuster(scene)
    assert scene.objets == objets
    assert ProgrammeMaximum({"T3": 2}, {"T2": 100}).ajuster(scene)
    assert [o.type_logement for o in scene.objets] == ["T2", "T3", "T3", "T2"]
