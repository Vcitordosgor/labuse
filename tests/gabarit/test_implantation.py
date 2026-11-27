import pytest
from fastapi import HTTPException

from labuse.api import gabarit


@pytest.fixture
def plan(monkeypatch):
    monkeypatch.setattr(gabarit, "plan_implantation", lambda *_: {
        "zone": [[[(0, 0), (10, 0), (10, 10), (0, 10)],
                  [(4, 4), (6, 4), (6, 6), (4, 6)]]],
        "limites": [{"nom": "1 · Voie", "ligne": [(0, 0), (10, 0)]},
                    {"nom": "2 · Latérale", "ligne": [(10, 0), (10, 10)]}],
    })


def test_cotes_en_metres_et_cour_exclue(plan):
    bilan = gabarit.cotes_implantation("test", [(2, 2), (10, 2), (10, 8), (2, 8)], None)
    assert bilan["aire"] == 48
    assert bilan["horsZone"] == 4
    assert [c["m"] for c in bilan["cotes"]] == [2, 0]


def test_contour_croise_refuse(plan):
    with pytest.raises(HTTPException) as erreur:
        gabarit.cotes_implantation("test", [(0, 0), (5, 5), (5, 0), (0, 5)], None)
    assert erreur.value.status_code == 422
