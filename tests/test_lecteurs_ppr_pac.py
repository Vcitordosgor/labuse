"""Une assiette PM1, une carte d’aléa et un zonage PPR ont trois effets distincts."""
from types import SimpleNamespace

from labuse.cascade.layers.phase1 import RisquesLayer
from labuse.enums import CascadeVerdict, Severity
from labuse.pige.api import distinct_hazards


def _risques(ppr=None, alea=None):
    couches = {"ppr": ppr or [], "georisque_alea": alea or []}
    contexte = SimpleNamespace(kind_present=lambda kind: True,
                               intersections=lambda pid, kind: couches[kind])
    parcelle = SimpleNamespace(id=1, commune="Saint-Denis", surface_m2=100)
    return RisquesLayer().evaluate(parcelle, contexte,
                                    {"spatial_kind_ppr": "ppr", "spatial_kind_alea": "georisque_alea"})


def test_pm1_sans_zonage():
    for couverture in [0.01, 0.05, 0.1, 0.2, 0.5, 1.0]:
        pm1 = SimpleNamespace(subtype="i", coverage=couverture, attrs={"suptype": "PM1"})
        assert all(v.result is CascadeVerdict.PASS for v in _risques(ppr=[pm1]))


def test_alea_pac():
    cas = [("negligeable", "negligeable", CascadeVerdict.PASS, None),
           ("fort", "tres_fort", CascadeVerdict.SOFT_FLAG, Severity.FORT)]
    for niveau, classe, resultat, severite in cas:
        alea = SimpleNamespace(subtype="inondation", coverage=1, attrs={
            "document": "PAC", "date_pac": "2026-11-26", "niveau": niveau, "classe": classe})
        verdict, = _risques(alea=[alea])
        assert (verdict.result, verdict.severity) == (resultat, severite)
        assert "PAC" in verdict.detail and "2026-11-26" in verdict.detail


def test_seul_alea_expose_entre_dans_le_compteur():
    nul = {"nature":"Aléa inondation", "niveau":"negligeable"}
    mouvement = {"nature":"Aléa mouvement de terrain", "niveau":"tres_eleve"}
    assert distinct_hazards([nul]) == []
    assert distinct_hazards([nul,mouvement]) == ["Mouvement de terrain"]
