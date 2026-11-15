"""ETUDE-STATIONNEMENT-FIX-3 (LOT 1) — BANC D'EXÉCUTION des 267 couples commune-zone × CINQ programmes.

FIX-2 ne jouait que la 1ʳᵉ zone de chaque règle (76 zones × 4 programmes) : les zones à TAUX VARIABLE
partageant une règle (Saint-Paul U1a=1/logt vs U1g=2/logt ; U2a=1,5 vs U2c=2) héritaient d'une valeur
fausse. FIX-3 joue RÉELLEMENT les 267 couples × 5 programmes (1 335 cellules), chaque valeur attendue
PROPRE AU COUPLE. Le 5ᵉ programme tombe EXACTEMENT sur le seuil de surface de l'article (20 T2 à la borne,
ou 20 T2 de 50 m² sans borne).

Les attendus par couple sont figés dans banc212/couples_267.json. Ils ont été confrontés à l'IMAGE : le
relecteur a rejoué 20 couples tirés au sort × 5 programmes (100 calculs) et le moteur reproduit l'image
(0 écart, places publiques comprises) — voir `test_banc_ancres_image_relecteur`. Tout désaccord antérieur
du banc (60 sur 1 068, 20 zones) était une valeur de banc périmée ; sur U1g/U2c le règlement confirme le
moteur. Ce test VERROUILLE donc l'état image-vérifié, par couple, sur TOUTE l'île.
"""
import glob
import json
import os
from types import SimpleNamespace

import pytest

from labuse.implantation import regles as R

_BANC = os.path.join(os.path.dirname(__file__), "..", "docs", "audit-2026-11",
                     "stationnement-fix-2", "banc212")
_COUPLES = json.load(open(os.path.join(_BANC, "couples_267.json"), encoding="utf-8"))["couples"]


def _mods(prog, seuil):
    if prog == "maison_T4_120":
        return "individuel", [SimpleNamespace(pieces=4, surface_m2=120.0)]
    if prog == "collectif_20T3_1400":
        return "collectif", [SimpleNamespace(pieces=3, surface_m2=70.0) for _ in range(20)]
    if prog == "aide_20T3_1400":
        return "social", [SimpleNamespace(pieces=3, surface_m2=70.0) for _ in range(20)]
    if prog == "mixte_10x110_10x30":
        return "collectif", ([SimpleNamespace(pieces=4, surface_m2=110.0) for _ in range(10)]
                             + [SimpleNamespace(pieces=1, surface_m2=30.0) for _ in range(10)])
    if prog == "seuil_20T2":
        return "collectif", [SimpleNamespace(pieces=2, surface_m2=float(seuil)) for _ in range(20)]
    raise AssertionError(prog)


_CAS = [(c["insee"], c["zone"], c["seuil_m2"], p, v["total"], v.get("publiques", 0))
        for c in _COUPLES for p, v in c["programs"].items()]


def test_banc_couverture():
    # garde-fou : 267 couples × 5 programmes = 1 335 cellules réellement jouées (sinon faux vert).
    assert len({(c["insee"], c["zone"]) for c in _COUPLES}) == 267, f"{len(_COUPLES)} couples ≠ 267"
    assert len(_CAS) == 267 * 5, f"{len(_CAS)} cellules ≠ 1335"


@pytest.mark.parametrize("insee,zone,seuil,prog,total,publiques", _CAS,
                         ids=[f"{c[0]}:{c[1]}:{c[3]}" for c in _CAS])
def test_banc_267x5(insee, zone, seuil, prog, total, publiques):
    """Le moteur rend, pour CHAQUE couple × programme, la valeur image-vérifiée propre au couple."""
    b = R.charger(insee, zone).stationnement
    assert b.validee, f"{insee}/{zone} : barème non servi"
    dest, mods = _mods(prog, seuil)
    ex = b.exiger(mods, destination=dest)
    assert ex.places == total, f"{insee}/{zone} {prog} : moteur {ex.places} ≠ {total} ({ex.formule})"
    assert ex.places_publiques == publiques, (f"{insee}/{zone} {prog} : publiques {ex.places_publiques} "
                                              f"≠ {publiques}")


# ── 20 couples TIRÉS AU SORT par le relecteur, valeurs LUES SUR L'IMAGE (contrôle indépendant du moteur).
# Ordre : maison T4 120 / collectif 20×T3 / aidé 20×T3 (social) / mixte 10×110+10×30 / seuil 20×T2 ;
# chaque valeur = (places privées, places publiques).
_ANCRES = [
    ("97412", "2AU5cvd", (2, 0), (40, 0), (20, 0), (40, 0), (40, 0)),
    ("97415", "U1g", (2, 0), (44, 0), (22, 0), (44, 0), (44, 0)),        # banc FIX-2 disait 1/24/22/24 (faux)
    ("97407", "1AUc", (3, 0), (20, 0), (16, 0), (20, 0), (16, 0)),
    ("97422", "1AUc", (1, 0), (30, 0), (20, 0), (30, 0), (30, 0)),
    ("97405", "UCe", (1, 0), (20, 0), (20, 0), (20, 0), (20, 0)),
    ("97411", "Udo", (1, 0), (20, 0), (20, 0), (25, 0), (30, 0)),
    ("97415", "AU3b", (1, 0), (34, 0), (22, 0), (34, 0), (34, 0)),
    ("97405", "UDe", (1, 0), (20, 0), (20, 0), (20, 0), (20, 0)),
    ("97414", "1AUa", (2, 0), (40, 10), (20, 10), (40, 10), (40, 10)),
    ("97422", "Ua", (1, 0), (30, 0), (20, 0), (30, 0), (30, 0)),
    ("97412", "3AU3", (2, 0), (40, 0), (20, 0), (40, 0), (40, 0)),
    ("97402", "Uc", (2, 0), (20, 0), (20, 0), (25, 0), (30, 0)),
    ("97414", "2AUd", (2, 0), (40, 10), (20, 10), (40, 10), (40, 10)),
    ("97415", "U3b", (1, 0), (34, 0), (22, 0), (34, 0), (34, 0)),
    ("97414", "1AUc1", (2, 0), (40, 10), (20, 10), (40, 10), (40, 10)),
    ("97408", "UA", (3, 0), (44, 0), (20, 0), (34, 0), (24, 0)),
    ("97401", "Ua", (2, 0), (40, 0), (20, 0), (40, 0), (29, 0)),
    ("97418", "1AUc", (2, 0), (20, 0), (20, 0), (25, 0), (30, 0)),
    ("97412", "2AU2", (1, 0), (20, 0), (20, 0), (20, 0), (20, 0)),
    ("97412", "U5ma", (2, 0), (40, 0), (20, 0), (40, 0), (40, 0)),
]
_ORDRE = ["maison_T4_120", "collectif_20T3_1400", "aide_20T3_1400", "mixte_10x110_10x30", "seuil_20T2"]


@pytest.mark.parametrize("ancre", _ANCRES, ids=[f"{a[0]}:{a[1]}" for a in _ANCRES])
def test_banc_ancres_image_relecteur(ancre):
    """Contrôle INDÉPENDANT : le moteur reproduit les 5 programmes lus sur l'image par le relecteur
    (20 couples × 5 = 100 calculs), places publiques comprises."""
    insee, zone = ancre[0], ancre[1]
    attendus = ancre[2:]
    b = R.charger(insee, zone).stationnement
    assert b.validee, f"{insee}/{zone} : barème non servi"
    ss = sorted({l.sdp_max for l in b.lignes if l.sdp_max} | {l.sdp_min for l in b.lignes if l.sdp_min})
    seuil = float(ss[0]) if ss else 50.0
    for prog, (tot, pub) in zip(_ORDRE, attendus):
        dest, mods = _mods(prog, seuil)
        ex = b.exiger(mods, destination=dest)
        assert (ex.places, ex.places_publiques) == (tot, pub), (
            f"{insee}/{zone} {prog} : moteur ({ex.places},{ex.places_publiques}) ≠ image ({tot},{pub})")


def test_regle_complete_le_tampon_type_et_operation():
    """reliquat #6 — la règle servie au Dossier = celle de l'Étude, COMPLÈTE : par type ET par opération."""
    from labuse.implantation.service import _regle_stationnement_courte
    rc = _regle_stationnement_courte(R.charger("97422", "Ua").stationnement)
    assert rc and "1 place / logement" not in rc
    assert "T2" in rc and "T3+" in rc and "opération" in rc and "> 5" in rc, rc
