"""MOTEUR-VERITE-FIX-1 — gardes des lots 1 et 2 (moteur pur, aucune base).

LOT 1 : le recul séparatif en formule H/n s'évalue à l'égout du bâtiment ENVISAGÉ, niveau par
niveau, et le scénario retenu maximise le plancher (aire × niveaux, bornée au CES).
LOT 2 : les modes d'implantation par côté — limite admise → recul 0 ; feuille non validée ou
mode inconnu → ignorée (le retrait s'applique seul).
"""
from __future__ import annotations

from labuse.faisabilite.zonage import _implantation_leaf
from labuse.gabarit.contract import (
    ApplicableRule,
    Exclusion,
    GabaritInput,
    MaxFootprint,
    MaxHeight,
    ParcelInput,
    ReculSepFormule,
    RegulatorySource,
    Setback,
)
from labuse.gabarit.engine import compute_gabarit

SRC = RegulatorySource(document="PLU — Test", zone="Ut")


import math

LON0, LAT0 = 55.50, -21.00     # La Réunion — le moteur projette en UTM 40S (EPSG:2975)
DLAT = 1 / 111_320.0
DLON = 1 / (111_320.0 * math.cos(math.radians(abs(LAT0))))


def _pt(x_m, y_m):
    return (LON0 + x_m * DLON, LAT0 + y_m * DLAT)


def _carre(cote=30.0):
    return {"type": "Polygon", "coordinates": [[
        list(_pt(0, 0)), list(_pt(cote, 0)), list(_pt(cote, cote)),
        list(_pt(0, cote)), list(_pt(0, 0))]]}


def _ligne(p1, p2):
    return {"type": "LineString", "coordinates": [list(p1), list(p2)]}


def _input(recul_sep=3.0, formule=None, cotes_en_limite=()):
    cote = 30.0
    bords = [(_pt(0, 0), _pt(cote, 0), "road"), (_pt(cote, 0), _pt(cote, cote), "side"),
             (_pt(cote, cote), _pt(0, cote), "rear"), (_pt(0, cote), _pt(0, 0), "side")]
    setbacks = []
    for i, (a, b, t) in enumerate(bords):
        en_limite = i in cotes_en_limite
        setbacks.append(Setback(
            id=f"l{i}", ruleId=("limite-voie" if t == "road"
                                else "limite-sep-limite" if en_limite else "limite-sep"),
            type=t, geometry=_ligne(a, b),
            setbackM=0.0 if en_limite else (3.0 if t == "road" else recul_sep), source=SRC))
    rules = [ApplicableRule(id=rid, label=rid, category="setback",
                            integrationStatus="integrated", source=SRC)
             for rid in {"limite-voie", "limite-sep", "limite-sep-limite"}]
    rules.append(ApplicableRule(id="emp", label="Emprise", category="maxFootprint",
                                integrationStatus="integrated", source=SRC))
    rules.append(ApplicableRule(id="h", label="Hauteur", category="maxHeight",
                                integrationStatus="integrated", source=SRC))
    rules.append(ApplicableRule(id="risques", label="Risques", category="exclusion",
                                integrationStatus="integrated", detail="aucun", source=SRC))
    return GabaritInput(
        parcel=ParcelInput(id="TEST", geometry=_carre(cote), areaM2=cote * cote, source=SRC),
        setbacks=setbacks,
        reculSepFormule=formule,
        maxFootprint=MaxFootprint(ruleId="emp", percent=100.0, status="integrated", source=SRC),
        maxHeight=MaxHeight(ruleId="h", meters=12.0, status="integrated", basis="faitage", source=SRC),
        exclusions=[], applicableRules=rules, sources=[SRC])


def test_lot1_scenario_retenu_maximise_le_plancher():
    """Carré 30×30, voie 3 m, formule H/2 min 3 m, 4 niveaux admis : recul(n)=max(3, 1,5n).
    n=2 → recul 3 m, aire 24×24=576, plancher 1 152 ; n=4 → recul 6 m, aire 21×18=378 (voie 3),
    plancher 1 512 → le scénario n=4 l'emporte ; à l'inverse avec un CES bas le n bas gagne."""
    f = ReculSepFormule(fraction=0.5, minimumM=3.0, etageM=3.0, niveauxMax=4, formule="H/2 min 3 m")
    r = compute_gabarit(_input(formule=f))
    assert r.status == "ok"
    assert r.niveauxRetenus == 4 and abs(r.reculSepRetenuM - 6.0) < 0.01
    assert abs(r.zoneImplantationM2 - 378.0) < 15        # 21 (voie+fond) × 18 (2 latérales à 6 m)

    # CES 10 % (plafond 90 m²) : l'aire sature le plafond dès n=2 → proxy = 90×n, n=4 encore
    # devant… mais avec niveauxMax=1 le scénario est forcé à R+0, recul 3 m.
    f1 = ReculSepFormule(fraction=0.5, minimumM=3.0, etageM=3.0, niveauxMax=1, formule="H/2")
    r1 = compute_gabarit(_input(formule=f1))
    assert r1.niveauxRetenus == 1 and abs(r1.reculSepRetenuM - 3.0) < 0.01
    assert abs(r1.zoneImplantationM2 - 576.0) < 15       # 24×24


def test_lot1_sans_formule_comportement_inchange():
    r = compute_gabarit(_input())
    assert r.status == "ok" and r.niveauxRetenus is None and r.reculSepRetenuM is None
    assert abs(r.zoneImplantationM2 - 576.0) < 15        # inset uniforme 3 m


def test_lot2_arete_en_limite_recul_zero():
    """Deux latérales posées en limite (`limite-sep-limite`, 0 m) : l'assiette ne perd que la
    voie (3 m) et le fond (3 m) → 30×24 = 720 m². La formule H/n ne re-insète PAS ces arêtes."""
    f = ReculSepFormule(fraction=0.5, minimumM=3.0, etageM=3.0, niveauxMax=4, formule="H/2")
    r = compute_gabarit(_input(formule=f, cotes_en_limite=(1, 3)))
    assert r.status == "ok"
    # scénario : seules les arêtes `limite-sep` (le fond) varient ; n=4 → fond 6 m → 30×21=630×4
    # bat n=2 (30×24=720×2) → niveaux retenus 4, et les latérales restent à 0.
    assert r.niveauxRetenus == 4
    assert abs(r.zoneImplantationM2 - 630.0) < 15


def test_lot2_feuille_validee_seulement():
    assert _implantation_leaf({"retraits": {"limites_separatives": {
        "implantation_laterales": {"mode": "limite_ou_retrait", "statut": "valide"}}}},
        "implantation_laterales") == {"mode": "limite_ou_retrait", "statut": "valide"}
    # propose → None ; mode inconnu → None
    assert _implantation_leaf({"retraits": {"limites_separatives": {
        "implantation_laterales": {"mode": "limite_ou_retrait", "statut": "propose"}}}},
        "implantation_laterales") is None
    assert _implantation_leaf({"retraits": {"limites_separatives": {
        "implantation_laterales": {"mode": "nimporte", "statut": "valide"}}}},
        "implantation_laterales") is None
