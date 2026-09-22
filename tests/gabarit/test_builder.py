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

    def scalar(self):
        r = self._row
        return r[0] if isinstance(r, (tuple, list)) else r


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
        if "ravine" in sql or "trait_de_cote" in sql:
            return _Res((False,))                        # _touche_ravine
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


def _fake_limites(has_voie=True, non_classees=None, enclave=False, empub=False):
    """LimitesResult factice sans DB, pour tester le branchement builder."""
    from shapely.geometry import LineString

    from labuse.gabarit.limites import Edge, LimitesResult
    if enclave:
        edges = [Edge(LineString([(0, 0), (10, 0)]), "rear", 10.0),
                 Edge(LineString([(10, 0), (10, 10)]), "rear", 10.0)]
        has_voie = False
    elif empub:
        edges = [Edge(LineString([(0, 0), (10, 0)]), "voie", 10.0, source_kind="emprise_publique"),
                 Edge(LineString([(10, 0), (10, 10)]), "side", 10.0)]
    else:
        edges = [Edge(LineString([(0, 0), (10, 0)]), "voie", 10.0, source_kind="bdtopo"),
                 Edge(LineString([(10, 0), (10, 10)]), "side", 10.0)]
    return LimitesResult(edges=edges, has_voie=has_voie, non_classees=non_classees or [], blocking=None)


def test_parcelle_inconnue(monkeypatch):
    s = FakeSession(None, None)
    assert B.build_gabarit_input(s, "00000000AA0000") is None


def test_propose_bloque(monkeypatch):
    monkeypatch.setattr(B, "zone_dominante", lambda s, pid: _zone())
    monkeypatch.setattr(B, "resolve_zone",
                        lambda code, com: _rules(regle_non_validee="hauteur.faitage (propose)"))
    b = B.build_gabarit_input(FakeSession(_PARCEL, _PPR_NONE), "97415000U2xxxxx")
    assert any("propose" in x for x in b.blocking)


def _rec(code, pct, tz_cons=True):
    return {"code": code, "pct": pct, "area": 500.0,
            "gj": {"type": "Polygon", "coordinates": [[[55.29, -21.03], [55.2903, -21.03],
                   [55.2903, -21.0303], [55.29, -21.0303], [55.29, -21.03]]]},
            "wkt": "POLYGON((0 0,10 0,10 10,0 10,0 0))"}


def test_multizone_2_constructibles_bloque(monkeypatch):
    monkeypatch.setattr(B, "zone_dominante", lambda s, pid: _zone(cheval=True))
    monkeypatch.setattr(B, "_multizone_split", lambda s, pid: ([_rec("U1", 50), _rec("U2", 45)], [], []))
    b = B.build_gabarit_input(FakeSession(_PARCEL, _PPR_NONE), "x")
    assert any("2 zones constructibles" in x for x in b.blocking)


def test_multizone_tout_non_constructible_bloque(monkeypatch):
    monkeypatch.setattr(B, "zone_dominante", lambda s, pid: _zone(cheval=True))
    monkeypatch.setattr(B, "_multizone_split", lambda s, pid: ([], [_rec("N", 60), _rec("A", 40)], []))
    b = B.build_gabarit_input(FakeSession(_PARCEL, _PPR_NONE), "x")
    assert any("non constructible" in x for x in b.blocking)


def test_multizone_1_constructible_servie(monkeypatch):
    """Une seule zone constructible (le reste A/N) → servie sur ce morceau ; bande < 5 % signalée."""
    monkeypatch.setattr(B, "zone_dominante", lambda s, pid: _zone(cheval=True))
    monkeypatch.setattr(B, "_multizone_split",
                        lambda s, pid: ([_rec("Uc", 80)], [_rec("N", 17)], [("Nr", 3.0)]))
    monkeypatch.setattr(B, "resolve_zone", lambda code, com: _rules())
    monkeypatch.setattr(B, "classify_parcel_limits", lambda s, pid, **kw: _fake_limites())
    b = B.build_gabarit_input(FakeSession(_PARCEL, _PPR_NONE), "x")
    assert b.blocking == []
    assert b.raccordement["multizone"]["servie_sur"].startswith("Uc")
    assert any("Nr non retenue" in x for x in b.raccordement.get("bandes_ignorees", []))


def test_non_calibre_bloque(monkeypatch):
    monkeypatch.setattr(B, "zone_dominante", lambda s, pid: _zone())
    monkeypatch.setattr(B, "resolve_zone", lambda code, com: _rules(calibree=False))
    b = B.build_gabarit_input(FakeSession(_PARCEL, _PPR_NONE), "x")
    assert any("non calibré" in x for x in b.blocking)


def test_reel_calibre_mais_classification_differee(monkeypatch):
    """PLU calibré + limites classées → parcelle SERVIE (GABARIT-2, aucun blocage)."""
    monkeypatch.setattr(B, "zone_dominante", lambda s, pid: _zone())
    monkeypatch.setattr(B, "resolve_zone", lambda code, com: _rules())
    monkeypatch.setattr(B, "classify_parcel_limits", lambda s, pid, **kw: _fake_limites())
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
                        lambda s, pid, **kw: _fake_limites(non_classees=["emprise publique non routière"]))
    b = B.build_gabarit_input(FakeSession(_PARCEL, _PPR_NONE), "x")
    assert any("non qualifiées" in x for x in b.blocking)
    assert b.input.setbacks == []                 # rien servi si limites non qualifiées


def test_enclave_E1_servie_separatives(monkeypatch):
    """E1 (enclave sans chemin) → servie en séparatives seules, recul voie « sans objet »."""
    monkeypatch.setattr(B, "zone_dominante", lambda s, pid: _zone())
    monkeypatch.setattr(B, "resolve_zone", lambda code, com: _rules())
    monkeypatch.setattr(B, "classify_parcel_limits", lambda s, pid, **kw: _fake_limites(enclave=True))
    monkeypatch.setattr(B, "_has_chemin_neighbor", lambda s, pid: False)
    b = B.build_gabarit_input(FakeSession(_PARCEL, _PPR_NONE), "x")
    assert b.blocking == []
    assert b.raccordement["enclave"].startswith("E1")
    assert b.input.setbacks and all(sb.type in ("side", "rear") for sb in b.input.setbacks)
    assert any(ar.id == "limite-voie-sansobjet" for ar in b.input.applicableRules)


def test_enclave_E2_chemin_prive_bloque(monkeypatch):
    """E2 (enclave desservie par chemin privé) → bloquée (pas de citation voies privées)."""
    monkeypatch.setattr(B, "zone_dominante", lambda s, pid: _zone())
    monkeypatch.setattr(B, "resolve_zone", lambda code, com: _rules())
    monkeypatch.setattr(B, "classify_parcel_limits", lambda s, pid, **kw: _fake_limites(enclave=True))
    monkeypatch.setattr(B, "_has_chemin_neighbor", lambda s, pid: True)
    b = B.build_gabarit_input(FakeSession(_PARCEL, _PPR_NONE), "x")
    assert any("voie privée" in x for x in b.blocking)
    assert b.input.setbacks == []


def test_P1_emprise_publique_servie_par_citation(monkeypatch):
    """P1 : citation « voies ET emprises publiques » → l'arête ouverte est servie en voie,
    source dédiée domaine public + citation PLU."""
    monkeypatch.setattr(B, "zone_dominante", lambda s, pid: _zone())
    monkeypatch.setattr(B, "resolve_zone", lambda code, com: _rules())
    monkeypatch.setattr(B, "_voie_citation_flags", lambda com, z: (True, False, "Art. 6", "voies et emprises publiques"))
    monkeypatch.setattr(B, "classify_parcel_limits", lambda s, pid, **kw: _fake_limites(empub=True))
    b = B.build_gabarit_input(FakeSession(_PARCEL, _PPR_NONE), "x")
    assert b.blocking == []
    assert b.raccordement["citation_voie"]["emprises_publiques"] is True
    assert b.raccordement["classification"]["emprise_publique"] == 1
    ep = [ar for ar in b.input.applicableRules if ar.id == "limite-emprise-publique"]
    assert ep and "domaine public" in (ep[0].source.provider or "")
    empub_sb = [sb for sb in b.input.setbacks if sb.type == "road" and "domaine public" in (sb.source.provider or "")]
    assert empub_sb and empub_sb[0].setbackM == 5.0


def test_P1_emprise_publique_non_couverte_bloque(monkeypatch):
    """P1 sans citation « emprises publiques » → l'arête ouverte reste non qualifiée (bloc)."""
    monkeypatch.setattr(B, "zone_dominante", lambda s, pid: _zone())
    monkeypatch.setattr(B, "resolve_zone", lambda code, com: _rules())
    monkeypatch.setattr(B, "_voie_citation_flags", lambda com, z: (False, False, "", ""))
    monkeypatch.setattr(B, "classify_parcel_limits",
                        lambda s, pid, **kw: _fake_limites(non_classees=["arête sans voie ni voisin"]))
    b = B.build_gabarit_input(FakeSession(_PARCEL, _PPR_NONE), "x")
    assert any("non qualifiées" in x for x in b.blocking)


def test_ppr_analyse_toujours_presente(monkeypatch):
    monkeypatch.setattr(B, "zone_dominante", lambda s, pid: _zone())
    monkeypatch.setattr(B, "resolve_zone", lambda code, com: _rules())
    monkeypatch.setattr(B, "classify_parcel_limits", lambda s, pid, **kw: _fake_limites())
    b = B.build_gabarit_input(FakeSession(_PARCEL, _PPR_NONE), "x")
    ppr = [ar for ar in b.input.applicableRules if ar.id == "PPR"]
    assert len(ppr) == 1 and ppr[0].integrationStatus == "not_integrated"
    assert ppr[0].source and ppr[0].source.document
