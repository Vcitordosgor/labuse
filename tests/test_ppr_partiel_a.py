"""PPR-PARTIEL-A — garde-fous de la partie hors zone rouge (lot 2).

Tests par injection (sans base) : on simule la ligne du plus grand fragment hors rouge et la
classification des limites, et on vérifie que chaque garde-fou rend le bon motif — jamais un 0 muet.
Plus : les motifs rendent un libellé client « en clair » (engine)."""
import types

import labuse.faisabilite.db as dbmod
from labuse.faisabilite.db import _hors_rouge_fragment_servable, SEUIL_HORS_PPR_ROUGE_M2
from labuse.faisabilite.engine import cause_libelle, _verdict_assiette_vide, _EXIGU_LIB


class _FakeNested:
    def __enter__(self): return self
    def __exit__(self, *a): return False


class _FakeSession:
    """Session minimale : begin_nested() + execute().first() renvoyant une ligne fragment injectée."""
    def __init__(self, row):
        self._row = row

    def begin_nested(self):
        return _FakeNested()

    def execute(self, *a, **k):
        row = self._row
        return types.SimpleNamespace(first=lambda: row)


def _row(wkt, m2):
    return types.SimpleNamespace(wkt=wkt, m2=m2)


def _patch_limits(monkeypatch, has_voie):
    monkeypatch.setattr(
        "labuse.gabarit.limites.classify_parcel_limits",
        lambda *a, **k: (None if has_voie is None
                         else types.SimpleNamespace(has_voie=has_voie)))


def test_fragment_servable_assez_grand_avec_voie(monkeypatch):
    _patch_limits(monkeypatch, has_voie=True)
    ok, motif = _hors_rouge_fragment_servable(_FakeSession(_row("POLYGON(...)", 4732.0)), 1)
    assert ok is True and motif is None


def test_fragment_trop_petit(monkeypatch):
    _patch_limits(monkeypatch, has_voie=True)  # peu importe : surface d'abord
    ok, motif = _hors_rouge_fragment_servable(_FakeSession(_row("POLYGON(...)", 180.0)), 1)
    assert ok is False and motif == "hors_rouge_trop_petit"


def test_seuil_200_exact(monkeypatch):
    _patch_limits(monkeypatch, has_voie=True)
    assert _hors_rouge_fragment_servable(_FakeSession(_row("P", SEUIL_HORS_PPR_ROUGE_M2)), 1)[0] is True
    assert _hors_rouge_fragment_servable(
        _FakeSession(_row("P", SEUIL_HORS_PPR_ROUGE_M2 - 0.1)), 1)[1] == "hors_rouge_trop_petit"


def test_fragment_sans_acces(monkeypatch):
    _patch_limits(monkeypatch, has_voie=False)
    ok, motif = _hors_rouge_fragment_servable(_FakeSession(_row("POLYGON(...)", 5000.0)), 1)
    assert ok is False and motif == "hors_rouge_sans_acces"


def test_hors_rouge_vide_est_trop_petit(monkeypatch):
    _patch_limits(monkeypatch, has_voie=True)
    ok, motif = _hors_rouge_fragment_servable(_FakeSession(None), 1)   # parcelle ~100 % rouge
    assert ok is False and motif == "hors_rouge_trop_petit"


def test_decoupage_qui_leve_est_invalide(monkeypatch):
    class _Boom(_FakeSession):
        def execute(self, *a, **k): raise RuntimeError("geometry is invalid")
    ok, motif = _hors_rouge_fragment_servable(_Boom(None), 1)
    assert ok is False and motif == "hors_rouge_invalide"


def test_motifs_rendent_un_libelle_en_clair():
    # Jamais un 0 muet : chaque motif a un libellé client (verdict d'assiette vide + raison fine).
    for raison in ("hors_rouge_trop_petit", "hors_rouge_sans_acces", "hors_rouge_invalide"):
        verdict, chiffre = _verdict_assiette_vide(raison, 4.0)
        assert "hors zone rouge" in verdict and "0 m²" in chiffre
        assert raison in _EXIGU_LIB
        lib = cause_libelle("terrain_exigu", raison)
        assert lib and "Non retenue" in lib
