"""GABARIT-1 lot C — raccordement (builder). Sans base : session factice + monkeypatch
de zonage.py, pour prouver les blocages honnêtes (propose, multi-zone) et le réel.
"""
from __future__ import annotations

from types import SimpleNamespace

from labuse.gabarit import builder as B

_GEOJSON = ('{"type":"Polygon","coordinates":[[[55.29,-21.03],[55.2905,-21.03],'
            '[55.2905,-21.0305],[55.29,-21.0305],[55.29,-21.03]]]}')


class _Res:
    def __init__(self, row):
        self._row = row

    def mappings(self):
        return self

    def first(self):
        return self._row


class FakeSession:
    def __init__(self, parcel_row, ppr_row):
        self._parcel, self._ppr = parcel_row, ppr_row

    def execute(self, stmt, params=None):
        sql = str(stmt)
        if "cascade_results" in sql:
            return _Res(self._ppr)
        if "data_sources" in sql:
            return _Res(("BD TOPO test v3",))          # _bdtopo_millesime
        if "INTERDICTION" in sql:
            return _Res((None,))                         # géométrie d'exclusion PPR : aucune → ignorée
        return _Res(self._parcel)


_PARCEL = {"id": 42, "commune": "Saint-Paul", "surface_m2": 1000.0, "geojson": _GEOJSON}
_PPR_ROUGE = {"result": "HARD_EXCLUDE", "severity": "fort",
              "detail": "Exclue : PPR zone rouge (inconstructible)."}
_PPR_NONE = {"result": "PASS", "severity": None, "detail": "hors zone"}


def _zone(zone="U2", fam="U", cheval=False):
    return SimpleNamespace(zone=zone, zone_fam=fam, a_cheval=cheval)


def _rules(**kw):
    base = dict(regle_non_validee=None, calibree=True, emprise_sol_pct=40.0,
                hf_m=10.0, he_m=7.0, recul_voirie_m=5.0, recul_limites_sep_m=3.0,
                recul_voirie_alignement=False, recul_limites_alignement=False)
    base.update(kw)
    return SimpleNamespace(**base)


def _fake_limites(blocking=None):
    """LimitesResult factice (voie + séparative) sans DB, pour tester le branchement builder."""
    from shapely.geometry import LineString

    from labuse.gabarit.limites import Edge, LimitesResult
    edges = [Edge(LineString([(0, 0), (10, 0)]), "voie", 10.0),
             Edge(LineString([(10, 0), (10, 10)]), "side", 10.0)]
    return LimitesResult(edges=edges, has_voie=True, non_classees=[], blocking=blocking)


def test_parcelle_inconnue(monkeypatch):
    s = FakeSession(None, None)
    assert B.build_gabarit_input(s, "00000000AA0000") is None


def test_propose_bloque(monkeypatch):
    monkeypatch.setattr(B, "zone_dominante", lambda s, pid: _zone())
    monkeypatch.setattr(B, "resolve_zone",
                        lambda code, com: _rules(regle_non_validee="hauteur.faitage (propose)"))
    b = B.build_gabarit_input(FakeSession(_PARCEL, _PPR_NONE), "97415000U2xxxxx")
    assert any("propose" in x for x in b.blocking)


def test_multizone_bloque(monkeypatch):
    monkeypatch.setattr(B, "zone_dominante", lambda s, pid: _zone(cheval=True))
    monkeypatch.setattr(B, "resolve_zone", lambda code, com: _rules())
    b = B.build_gabarit_input(FakeSession(_PARCEL, _PPR_NONE), "x")
    assert any("cheval" in x for x in b.blocking)


def test_non_calibre_bloque(monkeypatch):
    monkeypatch.setattr(B, "zone_dominante", lambda s, pid: _zone())
    monkeypatch.setattr(B, "resolve_zone", lambda code, com: _rules(calibree=False))
    b = B.build_gabarit_input(FakeSession(_PARCEL, _PPR_NONE), "x")
    assert any("non calibré" in x for x in b.blocking)


def test_reel_calibre_mais_classification_differee(monkeypatch):
    """PLU calibré + limites classées → parcelle SERVIE (GABARIT-2, aucun blocage)."""
    monkeypatch.setattr(B, "zone_dominante", lambda s, pid: _zone())
    monkeypatch.setattr(B, "resolve_zone", lambda code, com: _rules())
    monkeypatch.setattr(B, "classify_parcel_limits", lambda s, pid: _fake_limites())
    b = B.build_gabarit_input(FakeSession(_PARCEL, _PPR_ROUGE), "x")
    assert b.blocking == []                       # tout est réuni → servie
    assert b.raccordement["plu"]["emprise_pct"] == 40.0
    assert b.raccordement["ppr"]["rouge"] is True
    assert b.raccordement["classification"]["voie"] == 1
    assert b.input.maxFootprint.percent == 40.0
    assert b.input.maxHeight.meters == 10.0
    # setbacks servis : recul voie sur la voie, recul séparatif sur la latérale
    setbacks = b.input.setbacks
    assert len(setbacks) == 2
    voie = [s for s in setbacks if s.type == "road"]
    assert voie and voie[0].setbackM == 5.0
    assert all("BD TOPO" in (s.source.provider or "") for s in setbacks)
    # analyse des risques présente et sourcée
    assert any(ar.category == "exclusion" for ar in b.input.applicableRules)


def test_limites_non_qualifiees_bloque(monkeypatch):
    monkeypatch.setattr(B, "zone_dominante", lambda s, pid: _zone())
    monkeypatch.setattr(B, "resolve_zone", lambda code, com: _rules())
    monkeypatch.setattr(B, "classify_parcel_limits",
                        lambda s, pid: _fake_limites(blocking="parcelle sans façade sur voie"))
    b = B.build_gabarit_input(FakeSession(_PARCEL, _PPR_NONE), "x")
    assert any("sans façade" in x for x in b.blocking)
    assert b.input.setbacks == []                 # rien servi si limites non qualifiées


def test_ppr_analyse_toujours_presente(monkeypatch):
    monkeypatch.setattr(B, "zone_dominante", lambda s, pid: _zone())
    monkeypatch.setattr(B, "resolve_zone", lambda code, com: _rules())
    monkeypatch.setattr(B, "classify_parcel_limits", lambda s, pid: _fake_limites())
    b = B.build_gabarit_input(FakeSession(_PARCEL, _PPR_NONE), "x")
    ppr = [ar for ar in b.input.applicableRules if ar.id == "PPR"]
    assert len(ppr) == 1 and ppr[0].integrationStatus == "not_integrated"
    assert ppr[0].source and ppr[0].source.document
