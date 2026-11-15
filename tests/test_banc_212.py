"""ETUDE-STATIONNEMENT-FIX-2 (LOT 1) — BANC D'EXÉCUTION des 267 couples commune-zone (les « 212 » + renvois).

La preuve n'est plus « la citation est présente » mais « le nombre de places calculé est JUSTE », sur TOUTE
l'île. Chaque règle distincte a été recalculée à la main par un agent qui LIT L'IMAGE de la page officielle
(jamais le code), pour quatre programmes types (mandat) :
  - maison T4 120 m² (individuel) ;
  - collectif privé 20 × T3 = 1 400 m² ;
  - le même en logement aidé ;
  - collectif mixte 10 × 110 m² + 10 × 30 m².
Les valeurs attendues (lues sur l'image) sont figées dans docs/audit-2026-11/stationnement-fix-2/banc212/
results/<insee>.json ; ce test confronte le moteur (`BaremeStationnement.exiger`) à ces valeurs, pour
chaque règle × chaque programme. 267/267 couples concordants au dernier recalage.
"""
import glob
import json
import os
from types import SimpleNamespace

import pytest

from labuse.implantation import regles as R

_BANC = os.path.join(os.path.dirname(__file__), "..", "docs", "audit-2026-11",
                     "stationnement-fix-2", "banc212")
_PROGS = {
    "maison_T4_120": ("individuel", lambda: [SimpleNamespace(pieces=4, surface_m2=120.0)]),
    "collectif_20T3_1400": ("collectif", lambda: [SimpleNamespace(pieces=3, surface_m2=70.0) for _ in range(20)]),
    "aide_20T3_1400": ("social", lambda: [SimpleNamespace(pieces=3, surface_m2=70.0) for _ in range(20)]),
    "mixte_10x110_10x30": ("collectif", lambda: [SimpleNamespace(pieces=4, surface_m2=110.0) for _ in range(10)]
                           + [SimpleNamespace(pieces=1, surface_m2=30.0) for _ in range(10)]),
}


def _cas():
    """(insee, rule_id, zone témoin, programme, total attendu, publiques attendues) pour chaque règle lue."""
    out = []
    for rf in sorted(glob.glob(os.path.join(_BANC, "results", "*.json"))):
        insee = os.path.basename(rf)[:5]
        res = json.load(open(rf, encoding="utf-8"))
        spec = json.load(open(os.path.join(_BANC, "specs", f"{insee}.json"), encoding="utf-8"))
        zbyid = {r["id"]: r["zones"] for r in spec["regles"]}
        for rr in res["regles"]:
            if not rr.get("found"):
                continue
            zones = zbyid.get(rr["rule_id"]) or []
            if not zones:
                continue
            for prog, pr in rr["programs"].items():
                out.append((insee, rr["rule_id"], zones[0], prog,
                            pr.get("total"), pr.get("publiques", 0)))
    return out


_CAS = _cas()


def test_banc_non_vide():
    # garde-fou : les fichiers du banc sont présents et lus (sinon le paramétrage serait vide = faux vert).
    assert len(_CAS) >= 260, f"banc 212 incomplet : {len(_CAS)} cas lus"


# ETUDE-STATIONNEMENT-FIX-2 (banc 212, reliquat) — 5ᵉ PROGRAMME : 20 logements tombant EXACTEMENT sur le
# seuil de surface de chaque règlement. C'est là que l'inclusivité de la borne se révèle : « ≤ 50 m² »
# (La Possession, Salazie) met 50 m² dans la tranche BASSE (1 place) ; « < 50 m² » / « ≥ 50 m² » (Saint-André,
# Sainte-Rose…) la met dans la tranche HAUTE. Valeurs LUES SUR L'IMAGE de la page officielle.
_SEUILS = [
    ("97402", "Ua", 100.0, 30, 0),    # Bras-Panon : ≤100→1 / ≥100→1,5 ; à 100 le minimum supérieur gouverne → 1,5
    ("97408", "UA", 50.0, 24, 0),     # La Possession : « ≤ 50 m² » → 1/logt (+ visiteur 1/5 = 4) = 24, PAS 44
    ("97409", "UC", 50.0, 30, 0),     # Saint-André : « ≥ 50 m² » → 1,5/logt = 30
    ("97411", "Uavap", 100.0, 30, 0), # Saint-Denis : « ≥ 100 m² » → 1,5/logt = 30
    ("97418", "UA", 100.0, 30, 0),    # Sainte-Marie : « ≥ 100 m² » (plusieurs logts) → 1,5/logt = 30
    ("97419", "Ua", 50.0, 30, 0),     # Sainte-Rose : « ≥ 50 m² » → 1,5/logt = 30
    ("97420", "UA", 50.0, 40, 10),    # Sainte-Suzanne : « ≥ 50 m² » → 2/logt = 40 (+ 10 publiques, opération > 10)
    ("97421", "UA", 50.0, 20, 0),     # Salazie : « ≤ 50 m² » → 1/logt = 20, PAS 40
]


@pytest.mark.parametrize("insee,zone,seuil,total,publiques", _SEUILS)
def test_banc_seuil_surface(insee, zone, seuil, total, publiques):
    """5ᵉ programme : 20 logements à la surface EXACTE du seuil → la bonne tranche selon l'inclusivité lue
    sur l'image (La Possession 50 m² = 24, pas 44)."""
    b = R.charger(insee, zone).stationnement
    ex = b.exiger([SimpleNamespace(pieces=2, surface_m2=seuil) for _ in range(20)], destination="collectif")
    assert ex.places == total, f"{insee}/{zone} 20×{seuil:g} m² : moteur {ex.places} ≠ {total} ({ex.formule})"
    assert ex.places_publiques == publiques


@pytest.mark.parametrize("insee,rule_id,zone,prog,total,publiques",
                         _CAS, ids=[f"{c[0]}:{c[1]}:{c[3]}" for c in _CAS])
def test_banc_212(insee, rule_id, zone, prog, total, publiques):
    """Le moteur rend le nombre de places LU SUR L'IMAGE, pour chaque règle × programme."""
    dest, prog_fn = _PROGS[prog]
    b = R.charger(insee, zone).stationnement
    assert b.validee, f"{insee}/{zone} : barème non servi"
    ex = b.exiger(prog_fn(), destination=dest)
    assert ex.places == total, (f"{insee} {rule_id} {prog} ({zone}) : moteur {ex.places} ≠ "
                                f"{total} lu sur l'image ({ex.formule})")
    assert ex.places_publiques == publiques, (f"{insee} {rule_id} {prog} ({zone}) : publiques "
                                              f"{ex.places_publiques} ≠ {publiques} lu sur l'image")
