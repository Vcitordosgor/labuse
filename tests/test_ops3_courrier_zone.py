"""OPS-3 (B) — le Courrier lit la zone PAR LE LECTEUR DE LA FICHE (`zone_servie.zone_dominante`),
jamais en direct dans `parcel_zone_plu`. L'écart « courrier-zone-bizone » : le Courrier servait la
1re ligne brute (« A ») quand la fiche sert la dominante/à-cheval — ils doivent servir LA MÊME zone.

Deux tests :
  · UNITAIRE (sans base) — `_synthese` prend bien sa zone de `zone_dominante` (une ZoneServie
    sentinelle), pas d'une lecture SQL directe de `zone_lib` ;
  · LOCAL (base réelle) — sur la parcelle de l'incident (BZ0005, bizone à cheval, dominante « A »),
    la zone servie par le Courrier composé == la zone dominante servie par la fiche.
"""
from __future__ import annotations

import pytest

from labuse import courrier_compose as cc
from labuse.faisabilite.zone_servie import ZoneServie


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def mappings(self):
        return self

    def first(self):
        return self._rows[0] if self._rows else None

    def all(self):
        return self._rows

    def scalar(self):
        if not self._rows:
            return None
        r = self._rows[0]
        return next(iter(r.values())) if isinstance(r, dict) else r


class _FakeDB:
    """Session minimale : dispatch par fragment SQL. Aucune vraie base."""

    def execute(self, stmt, params=None):
        sql = str(stmt)
        if "FROM parcels p" in sql and "fb.idu" in sql:
            return _FakeResult([{"id": 1, "idu": "97415000BZ0005", "section": "BZ",
                                 "numero": "0005", "commune": "Saint-Paul", "surface_m2": 1000.0,
                                 "contenance_m2": 1000.0, "batie": False, "pm": True}])
        if "zone_libelle FROM parcel_zone_plu" in sql:
            return _FakeResult([{"zone_libelle": "A — zone agricole"}])
        if "dvf_mutations_parcelle" in sql:
            return _FakeResult([{"n": 0, "y0": None, "y1": None}])
        return _FakeResult([])


def test_synthese_zone_vient_du_lecteur_fiche(monkeypatch):
    """La zone servie par le Courrier = celle rendue par `zone_dominante` (lecteur de la fiche),
    y compris quand la dominante est à cheval (a_cheval=True)."""
    sentinelle = ZoneServie(zone="A", zone_fam="A", a_cheval=True,
                            parts=[{"zone": "A", "fam": "A", "pct": 70.0},
                                   {"zone": "N", "fam": "N", "pct": 28.0}],
                            pct_constructible=0.0, source="parcel_zone_plu")
    appels = {"n": 0}

    def _fake_zone_dominante(session, pid):
        appels["n"] += 1
        return sentinelle

    monkeypatch.setattr("labuse.faisabilite.zone_servie.zone_dominante", _fake_zone_dominante)
    monkeypatch.setattr(cc.ca.courrier, "adresse_ban_parcelle", lambda db, idu: None)
    monkeypatch.setattr("labuse.plu_reglement.resolve_reglement",
                        lambda commune, zone: {"calibree": False})

    d = cc._synthese(_FakeDB(), "97415000BZ0005")

    assert appels["n"] == 1, "le Courrier doit appeler zone_dominante (lecteur de la fiche)"
    assert d["zone"] == "A", "la zone servie doit venir de zone_dominante, pas d'une lecture brute"
    assert d["zone_document"] == "A — zone agricole"


def test_choisir_ouverture_utilise_zone_servie():
    """L'ouverture D (neutre avec zone) sert la zone venue de `zone_dominante`."""
    d = {"pm": False, "batie": False, "zone": "A", "commune": "Saint-Paul",
         "reference": "BZ 0005", "adresse": None, "surface": None, "n_mutations": 0}
    code, texte = cc.choisir_ouverture(d)
    assert code == "D" and "zone A" in texte


@pytest.mark.local
def test_courrier_zone_egale_fiche_sur_incident():
    """Base RÉELLE — sur la bizone de l'incident (BZ0005), le Courrier sert LA zone de la fiche."""
    from sqlalchemy import text

    from labuse.db import session_scope
    from labuse.faisabilite.zone_servie import zone_dominante

    idu = "97415000BZ0005"
    with session_scope() as db:
        pid = db.execute(text("SELECT id FROM parcels WHERE idu = :i"), {"i": idu}).scalar()
        if pid is None:
            pytest.skip("BZ0005 absente de la base locale")
        zs = zone_dominante(db, int(pid))
        d = cc._synthese(db, idu)
        assert d["zone"] == zs.zone, (
            f"Courrier « {d['zone']} » ≠ fiche dominante « {zs.zone} » — lecture directe revenue")
