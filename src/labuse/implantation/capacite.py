"""Tableau de capacité — TIRÉ de la géométrie dessinée (jamais l'inverse).

Surfaces MESURÉES séparément sur la géométrie (bâti, places, allées, accès, pleine terre, reste
non affecté) ; leur somme = l'assiette. m² par place = (places + allées + accès) / nb places.
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
    sdp_m2: float
    shab_estimee_m2: float
    shab_par_type_m2: dict[str, float]
    # surfaces mesurées séparément (somme = assiette)
    bati_m2: float
    places_m2: float
    allees_m2: float
    acces_m2: float
    pleine_terre_m2: float
    reste_non_affecte_m2: float
    surface_stationnement_m2: float
    m2_par_place: Optional[float]
    emprise_sol_m2: float
    places: int
    places_imposees: Optional[int]
    distribution_niveaux: list[dict]
    mixite_applicable: Optional[bool]
    logements_aides_imposes: Optional[int]
    sdp_aidee_imposee_m2: Optional[float]
    ratio_shab_sdp: Optional[float] = None
    ratio_shab_sdp_par_batiment: dict = field(default_factory=dict)
    details_places: dict = field(default_factory=dict)
    # PLU-CALIBRAGE-10 LOT D : la coursive extérieure OUVERTE n'est pas close et couverte → hors
    # surface de plancher (art. R111-22 c. urb.). On la MESURE quand même, pour transparence.
    coursive_m2: float = 0.0           # plancher de coursive ouverte (TOUS niveaux), HORS SDP
    noyau_m2: float = 0.0              # plancher des noyaux (TOUS niveaux), DANS la SDP
    noyaux_par_batiment: dict = field(default_factory=dict)   # ref -> {m2_par_niveau, niveaux, m2_total}


def _sdp_logement(conv: Conventions, type_logement: str) -> float:
    m = conv.modules.get(type_logement)
    return m.surface_m2 if m else 0.0


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
        unit = bareme.places_pour(pieces=m.pieces, sdp_m2=m.surface_m2, destination="collectif")
        detail[t] = (n, unit)
        if unit is not None:
            total += n * unit
    if not detail:
        return 0, {}
    return bareme.arrondir(total), detail


def calculer(scene: Scene, conv: Conventions, regles: ReglesZone, terrain=None) -> Capacite:
    modules = scene.of("module")
    niveaux = (max((o.niveau for o in modules), default=-1) + 1)
    par_type: dict[str, int] = {}
    shab_par_type: dict[str, float] = {}
    for o in modules:
        par_type[o.type_logement] = par_type.get(o.type_logement, 0) + 1
        shab_par_type[o.type_logement] = shab_par_type.get(o.type_logement, 0.0) + \
            o.geom_local.area * conv.coef_plancher_habitable

    # PLU-CALIBRAGE-10 LOT D : SDP = modules + noyaux (parties closes et couvertes). La coursive
    # extérieure OUVERTE n'entre PAS dans la surface de plancher (art. R111-22 c. urb.).
    sdp = sum(o.geom_local.area for o in scene.objets if o.kind in ("module", "noyau"))
    coursive = sum(o.geom_local.area for o in scene.of("coursive"))
    shab = sum(o.geom_local.area for o in modules) * conv.coef_plancher_habitable

    def aire(kind):
        gs = [o.geom_local for o in scene.of(kind)]
        return float(unary_union(gs).area) if gs else 0.0

    bati = aire("batiment_emprise")
    places_m2 = aire("place")
    allees_m2 = aire("allee")
    acces_m2 = aire("acces")
    pleine_terre = aire("espace_libre")
    assiette = scene.assiette_local.area
    reste = assiette - (bati + places_m2 + allees_m2 + acces_m2 + pleine_terre)
    stat = places_m2 + allees_m2 + acces_m2
    places = len(scene.of("place"))

    places_imp, details = _places_imposees(scene, conv, regles)

    # ratio SHAB / SDP par bâtiment (et global) : part habitable du plancher construit (SDP = modules
    # + noyaux, coursive ouverte exclue). Surface des NOYAUX exposée par niveau et par bâtiment.
    refs = sorted({o.ref for o in scene.objets if o.kind in ("module", "noyau", "coursive") and o.ref})
    ratio_bat = {}
    noyaux_bat: dict[str, dict] = {}
    for ref in refs:
        shab_ref = sum(o.geom_local.area for o in modules if o.ref == ref) * conv.coef_plancher_habitable
        sdp_ref = sum(o.geom_local.area for o in scene.objets
                      if o.kind in ("module", "noyau") and o.ref == ref)
        if sdp_ref > 0:
            ratio_bat[ref] = round(shab_ref / sdp_ref, 3)
        noy_ref = [o for o in scene.of("noyau") if o.ref == ref]
        niv_ref = sorted({o.niveau for o in noy_ref})
        if noy_ref and niv_ref:
            m2_niv = round(sum(o.geom_local.area for o in noy_ref if o.niveau == niv_ref[0]), 1)
            noyaux_bat[ref] = {"m2_par_niveau": m2_niv, "niveaux": len(niv_ref),
                               "m2_total": round(sum(o.geom_local.area for o in noy_ref), 1)}
    ratio_global = round(shab / sdp, 3) if sdp > 0 else None

    distribution = []
    for n in range(niveaux):
        mods_n = [o for o in modules if o.niveau == n]
        pt = {}
        for o in mods_n:
            pt[o.type_logement] = pt.get(o.type_logement, 0) + 1
        sdp_n = sum(o.geom_local.area for o in scene.objets
                    if o.kind in ("module", "noyau") and o.niveau == n)
        noyau_n = sum(o.geom_local.area for o in scene.of("noyau") if o.niveau == n)
        coursive_n = sum(o.geom_local.area for o in scene.of("coursive") if o.niveau == n)
        distribution.append({"niveau": n, "par_type": pt, "sdp_m2": round(sdp_n, 1),
                             "noyau_m2": round(noyau_n, 1), "coursive_m2": round(coursive_n, 1)})

    # mixité : applicable si seuil en SDP franchi, OU seuil en nombre de logements franchi, OU
    # quota validé sans seuil (s'applique à tout). Quota appliqué à la SDP d'habitation.
    mix = regles.mixite
    mix_app = aides = sdp_aidee = None
    if mix.validee and mix.quota_pct is not None:
        if mix.seuil_m2 is not None:
            mix_app = sdp > mix.seuil_m2
        elif mix.seuil_logements is not None:
            mix_app = len(modules) >= mix.seuil_logements
        else:
            mix_app = True
        if mix_app:
            sdp_aidee = sdp * mix.quota_pct / 100.0
            aides = math.ceil(len(modules) * mix.quota_pct / 100.0)
        else:
            sdp_aidee, aides = 0.0, 0

    return Capacite(
        logements=len(modules), par_type=par_type, niveaux=niveaux,
        sdp_m2=round(sdp, 1), shab_estimee_m2=round(shab, 1),
        shab_par_type_m2={k: round(v, 1) for k, v in shab_par_type.items()},
        bati_m2=round(bati, 1), places_m2=round(places_m2, 1), allees_m2=round(allees_m2, 1),
        acces_m2=round(acces_m2, 1), pleine_terre_m2=round(pleine_terre, 1),
        reste_non_affecte_m2=round(reste, 1), surface_stationnement_m2=round(stat, 1),
        m2_par_place=(round(stat / places, 1) if places else None),
        emprise_sol_m2=round(bati, 1), places=places, places_imposees=places_imp,
        distribution_niveaux=distribution,
        mixite_applicable=mix_app, logements_aides_imposes=aides,
        sdp_aidee_imposee_m2=(round(sdp_aidee, 1) if sdp_aidee is not None else None),
        ratio_shab_sdp=ratio_global, ratio_shab_sdp_par_batiment=ratio_bat,
        details_places={k: {"nb": v[0], "places_unitaires": v[1]} for k, v in details.items()},
        coursive_m2=round(coursive, 1),
        noyau_m2=round(sum(o.geom_local.area for o in scene.of("noyau")), 1),
        noyaux_par_batiment=noyaux_bat,
    )
