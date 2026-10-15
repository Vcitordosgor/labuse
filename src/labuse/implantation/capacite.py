"""Tableau de capacité — TIRÉ de la géométrie dessinée (jamais l'inverse).

logements = nombre d'objets « module » ; SDP = aire mesurée des planchers ; SHAB = coef × aire
habitable mesurée ; emprise = aire de l'union des emprises ; pleine terre = aire des espaces libres ;
places = nombre d'objets « place ».
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from shapely.ops import unary_union

from .conventions import Conventions
from .geometrie import Scene
from .regles import ReglesZone


@dataclass
class Capacite:
    logements: int
    par_type: dict[str, int]
    niveaux: int
    sdp_m2: float                      # surface de plancher mesurée (modules + noyau + coursive)
    shab_estimee_m2: float             # habitable estimée = coef × aire des modules
    shab_par_type_m2: dict[str, float]
    emprise_sol_m2: float              # union des emprises bâties
    pleine_terre_m2: float             # espaces libres mesurés
    places: int
    places_imposees: Optional[int]     # du barème validé, sinon None
    distribution_niveaux: list[dict]   # [{niveau, par_type:{...}, sdp_m2}]
    # mixité (règle sourcée)
    mixite_applicable: Optional[bool]
    logements_aides_imposes: Optional[int]
    sdp_aidee_imposee_m2: Optional[float]
    details_places: dict = field(default_factory=dict)  # type -> (nb, places_unitaires)


def _places_imposees(scene: Scene, conv: Conventions, regles: ReglesZone) -> tuple[Optional[int], dict]:
    bareme = regles.stationnement
    if not bareme.validee:
        return None, {}
    total = 0.0
    detail: dict[str, tuple[int, Optional[float]]] = {}
    for t, m in conv.modules.items():
        n = len([o for o in scene.of("module") if o.type_logement == t])
        if n == 0:
            continue
        unit = bareme.places_pour(m.pieces, "collectif")
        detail[t] = (n, unit)
        if unit is not None:
            total += n * unit
    return (math.ceil(total) if detail else 0), detail


def calculer(scene: Scene, conv: Conventions, regles: ReglesZone) -> Capacite:
    modules = scene.of("module")
    niveaux = (max((o.niveau for o in modules), default=-1) + 1)
    par_type: dict[str, int] = {}
    shab_par_type: dict[str, float] = {}
    for o in modules:
        par_type[o.type_logement] = par_type.get(o.type_logement, 0) + 1
        shab_par_type[o.type_logement] = shab_par_type.get(o.type_logement, 0.0) + \
            o.geom_local.area * conv.coef_plancher_habitable

    sdp = sum(o.geom_local.area for o in scene.objets if o.kind in ("module", "noyau", "coursive"))
    shab = sum(o.geom_local.area for o in modules) * conv.coef_plancher_habitable
    emprises = [o.geom_local for o in scene.of("batiment_emprise")]
    emprise_sol = float(unary_union(emprises).area) if emprises else 0.0
    pleine_terre = sum(o.geom_local.area for o in scene.of("espace_libre"))
    places = len(scene.of("place"))

    places_imp, details = _places_imposees(scene, conv, regles)

    # distribution par niveau (mesurée)
    distribution = []
    for n in range(niveaux):
        mods_n = [o for o in modules if o.niveau == n]
        pt = {}
        for o in mods_n:
            pt[o.type_logement] = pt.get(o.type_logement, 0) + 1
        sdp_n = sum(o.geom_local.area for o in scene.objets
                    if o.kind in ("module", "noyau", "coursive") and o.niveau == n)
        distribution.append({"niveau": n, "par_type": pt, "sdp_m2": round(sdp_n, 1)})

    # mixité (règle validée) : seuil sur la SDP d'habitation
    mix_app = aides = sdp_aidee = None
    if regles.mixite.validee and regles.mixite_seuil_m2 is not None and regles.mixite_quota_pct is not None:
        mix_app = sdp > regles.mixite_seuil_m2
        if mix_app:
            sdp_aidee = sdp * regles.mixite_quota_pct / 100.0
            aides = math.ceil(len(modules) * regles.mixite_quota_pct / 100.0)
        else:
            sdp_aidee = 0.0
            aides = 0

    return Capacite(
        logements=len(modules), par_type=par_type, niveaux=niveaux,
        sdp_m2=round(sdp, 1), shab_estimee_m2=round(shab, 1),
        shab_par_type_m2={k: round(v, 1) for k, v in shab_par_type.items()},
        emprise_sol_m2=round(emprise_sol, 1), pleine_terre_m2=round(pleine_terre, 1),
        places=places, places_imposees=places_imp,
        distribution_niveaux=distribution,
        mixite_applicable=mix_app, logements_aides_imposes=aides,
        sdp_aidee_imposee_m2=(round(sdp_aidee, 1) if sdp_aidee is not None else None),
        details_places={k: {"nb": v[0], "places_unitaires": v[1]} for k, v in details.items()},
    )
