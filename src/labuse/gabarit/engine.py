"""Moteur géospatial pur et déterministe (CDC §4).

Indépendant de React, de la carte et de la base. Ne connaît pas le réel du fictif :
même contrat, même calcul. Entrée non mutée.

Étapes : partir du polygone cadastral → appliquer les reculs par limite (road/side/
rear) → soustraire les exclusions → zone finale d'implantation (Polygon,
MultiPolygon ou zone vide valide) → surface → plafond d'emprise calculé À PART.
Jamais `min(zoneImplantation, plafondEmprise)`.
"""
from __future__ import annotations

from typing import Optional

from shapely.geometry import GeometryCollection
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from ._geom import geojson_from_shape, shape_from_geojson, to_metric, to_wgs
from .contract import (
    AppliedRule,
    Coverage,
    GabaritInput,
    GabaritResult,
    NonIntegratedRule,
    RegulatorySource,
)
from .validate import validate_input

# CHIRURGICAL-FIX-1 (E107) — le message ne doit JAMAIS laisser croire que la parcelle est non
# constructible : c'est le GABARIT qui n'est pas calculable (une limite de la parcelle n'est pas
# qualifiée). La raison précise vit dans validationErrors ; la constructibilité et la capacité
# estimée restent dans la fiche. (« Calcul incomplet » se lisait comme un verdict défavorable.)
INCOMPLETE_MESSAGE = "Gabarit non calculable sur cette parcelle"


def _round(x: float, n: int = 1) -> float:
    return round(float(x), n)


def _as_polygonal(geom: BaseGeometry) -> BaseGeometry:
    """Ne garde que la part surfacique (Polygon/MultiPolygon) d'un résultat booléen."""
    if geom.is_empty:
        return geom
    if geom.geom_type in ("Polygon", "MultiPolygon"):
        return geom
    if isinstance(geom, GeometryCollection):
        polys = [g for g in geom.geoms if g.geom_type in ("Polygon", "MultiPolygon")]
        return unary_union(polys) if polys else geom
    return geom


def _grouped_setbacks(inp: GabaritInput) -> list[AppliedRule]:
    """Regroupe les reculs partageant (ruleId, valeur, source). Ne fusionne jamais si
    la valeur ou la source diffère (CDC §7)."""
    order: list[tuple] = []
    seen: dict[tuple, AppliedRule] = {}
    rules_by_id = {ar.id: ar for ar in inp.applicableRules if ar.id}
    for sb in inp.setbacks:
        src = sb.source or RegulatorySource()
        key = (sb.ruleId, round(sb.setbackM, 4) if sb.setbackM is not None else None,
               src.document, src.zone, src.article, src.versionDate, src.provider)
        if key in seen:
            continue
        ar = rules_by_id.get(sb.ruleId)
        label = (ar.label if ar and ar.label else "Recul")
        seen[key] = AppliedRule(ruleId=sb.ruleId or "", category="setback", label=label,
                                value=sb.setbackM, unit="m", source=src)
        order.append(key)
    return [seen[k] for k in order]


def compute_gabarit(inp: GabaritInput) -> GabaritResult:
    """Valide puis calcule. Ne mute jamais l'entrée."""
    errs = validate_input(inp)
    if errs:
        return GabaritResult(status="incomplete", message=INCOMPLETE_MESSAGE,
                             validationErrors=errs)

    # --- géométries en métrique (copies ; l'entrée n'est pas mutée) ----------
    parcel_4326 = shape_from_geojson(inp.parcel.geometry)
    parcel_m = to_metric(parcel_4326)

    excl_polys = [to_metric(shape_from_geojson(ex.geometry)) for ex in inp.exclusions]
    excl_union = unary_union(excl_polys) if excl_polys else None

    def _zone_apres_reculs(recul_sep_m: Optional[float]):
        """Inset de la parcelle par les reculs par côté ; `recul_sep_m` remplace, s'il est donné,
        le recul des limites séparatives (setbacks `limite-sep`) — les voies gardent le leur."""
        buffers = []
        for sb in inp.setbacks:
            line_m = to_metric(shape_from_geojson(sb.geometry))
            d = sb.setbackM
            if recul_sep_m is not None and sb.ruleId == "limite-sep":
                d = recul_sep_m
            if d and d > 0:
                buffers.append(line_m.buffer(d))
        union = unary_union(buffers) if buffers else None
        apres = parcel_m.difference(union) if union is not None else parcel_m
        apres = _as_polygonal(apres)
        zone = apres.difference(excl_union) if excl_union is not None else apres
        return _as_polygonal(zone), apres, union

    # MOTEUR-VERITE-FIX-1 (LOT 1, corrige la régression D-024 du 31/10) — recul séparatif en
    # FORMULE « L ≥ H/n, minimum X m » : H est la hauteur à l'ÉGOUT du bâtiment ENVISAGÉ, jamais
    # le faîtage maximal de la zone. On évalue chaque nombre de niveaux admis (égout envisagé =
    # n × étage) et on RETIENT le scénario au PLANCHER maximal (aire de la zone d'implantation,
    # bornée au plafond d'emprise CES s'il existe, × niveaux). À plancher égal, le recul le plus
    # petit (l'aire la plus grande) l'emporte — géométrie prudente et déterministe.
    niveaux_retenus: Optional[int] = None
    recul_sep_retenu: Optional[float] = None
    scenario_txt: Optional[str] = None
    f = inp.reculSepFormule
    if f is not None and any(sb.ruleId == "limite-sep" for sb in inp.setbacks):
        _surf = float(inp.parcel.areaM2)
        _mf = inp.maxFootprint
        _plaf = (None if (_mf is None or _mf.status == "absent" or _mf.percent is None)
                 else _surf * float(_mf.percent) / 100.0)
        best = None   # (proxy_plancher, -recul, n, zone, apres, union, recul)
        for n in range(1, max(1, int(f.niveauxMax)) + 1):
            rec_n = round(max(float(f.minimumM), float(f.fraction) * n * float(f.etageM)), 2)
            zone_n, apres_n, union_n = _zone_apres_reculs(rec_n)
            aire_n = float(zone_n.area)
            proxy = (min(aire_n, _plaf) if _plaf is not None else aire_n) * n
            cand = (proxy, -rec_n, n, zone_n, apres_n, union_n, rec_n)
            if best is None or (cand[0], cand[1]) > (best[0], best[1]):
                best = cand
        _, _, niveaux_retenus, zone_m, after_setbacks, setback_union, recul_sep_retenu = best
        scenario_txt = (f"recul séparatif = max({f.minimumM:g} m, H×{f.fraction:.3g}) avec H = "
                        f"égout du bâtiment envisagé ({niveaux_retenus} niveau(x) × {f.etageM:g} m"
                        f" = {niveaux_retenus * f.etageM:g} m) → {recul_sep_retenu:g} m ; scénario"
                        f" retenu = plancher maximal parmi R+0…R+{int(f.niveauxMax) - 1}")
    else:
        zone_m, after_setbacks, setback_union = _zone_apres_reculs(None)

    # bandes de retrait (pour la carte) = ce que les reculs retirent de la parcelle
    retrait_m = _as_polygonal(parcel_m.difference(after_setbacks)) if setback_union is not None else None
    excl_in_parcel_m = _as_polygonal(parcel_m.intersection(excl_union)) if excl_union is not None else None

    # --- métriques ------------------------------------------------------------
    mf, mh = inp.maxFootprint, inp.maxHeight
    footprint_absent = mf.status == "absent"
    hauteur_non_integree = mh.status == "not_integrated"

    surface_parcelle = float(inp.parcel.areaM2)          # valeur cadastrale sourcée
    zone_m2 = float(zone_m.area)
    # plafond calculé À PART (jamais min()) ; None si le règlement ne fixe pas de CES (silence prouvé)
    plafond_m2 = None if footprint_absent else surface_parcelle * mf.percent / 100.0
    hauteur = None if hauteur_non_integree else float(mh.meters)

    # FIX-FINAL-1 (NU-D-027) — PART de la parcelle en zone d'EXCLUSION (PPR rouge & autres interdictions,
    # retranchée du gabarit). Mesurée sur le dessin (même repère que l'emprise). Sert à dire, quand elle
    # domine, que la parcelle est « majoritairement inconstructible » plutôt que « risques intégrés ✓ ».
    part_exclue_pct = (round(excl_in_parcel_m.area / parcel_m.area * 100)
                       if excl_in_parcel_m is not None and parcel_m.area > 0 else None)
    exclusion_majoritaire = bool(part_exclue_pct is not None and part_exclue_pct > 50)

    # --- couverture réglementaire ---------------------
    # emprise absente = « vérifiée — sans plafond » (le silence est une donnée) ; hauteur prospect = non intégrée.
    # FIX-FINAL-1 (NU-D-027) — « risques intégrés » n'est PAS un ✓ serein quand la majorité de la parcelle
    # est en zone d'exclusion : le gabarit tient sur une portion résiduelle. On retire la coche dans ce cas
    # (l'écran/PDF affichent alors la mise en garde « majoritairement inconstructible »).
    risk_ok = any(ar.category == "exclusion" and ar.source and ar.source.document
                  for ar in inp.applicableRules) and not exclusion_majoritaire
    coverage = Coverage(reculs=bool(inp.setbacks), hauteur=not hauteur_non_integree,
                        emprise=True, risques=risk_ok)

    # --- règles appliquées + non intégrées -----------------------------------
    applied: list[AppliedRule] = _grouped_setbacks(inp)
    # MOTEUR-VERITE-FIX-1 (LOT 1) — la règle AFFICHÉE porte le recul RETENU du scénario (et le dit),
    # jamais le seul minimum d'entrée : écran, PDF et capacité racontent le même chiffre.
    if recul_sep_retenu is not None:
        for i, ar in enumerate(applied):
            if ar.ruleId == "limite-sep":
                applied[i] = ar.model_copy(update={"value": recul_sep_retenu,
                                                   "detail": scenario_txt})
    rules_by_id = {ar.id: ar for ar in inp.applicableRules if ar.id}
    _mfr = rules_by_id.get(mf.ruleId)
    applied.append(AppliedRule(
        ruleId=mf.ruleId or "", category="maxFootprint",
        label=(_mfr.label if _mfr and _mfr.label else ("Emprise au sol" if footprint_absent else "Emprise maximale")),
        value=None if footprint_absent else mf.percent, unit=None if footprint_absent else "%",
        detail=(_mfr.detail if footprint_absent and _mfr else None), source=mf.source))
    # la hauteur en prospect n'est PAS une règle appliquée : elle va dans « non intégrées » (ci-dessous)
    if not hauteur_non_integree:
        applied.append(AppliedRule(
            ruleId=mh.ruleId or "", category="maxHeight",
            label=(rules_by_id.get(mh.ruleId).label if rules_by_id.get(mh.ruleId) else "Hauteur maximale"),
            value=mh.meters, unit="m", source=mh.source))
    for ex in inp.exclusions:
        ar = rules_by_id.get(ex.ruleId)
        applied.append(AppliedRule(
            ruleId=ex.ruleId or "", category="exclusion",
            label=(ar.label if ar and ar.label else (ex.label or "Exclusion")),
            detail=ex.label, source=ex.source))
    # RECETTE-OUTILS-2 (R17) — exclusions VÉRIFIÉES mais SANS géométrie (ex. SUP : « Aucune SUP sur la
    # parcelle ») : le contrôle a été tenu et n'a rien trouvé → c'est une règle VÉRIFIÉE, pas « non
    # modélisée ». On les affiche donc en règles appliquées (avec leur détail), au lieu de les perdre
    # (elles ne sont plus not_integrated). Celles qui ONT une géométrie sont déjà ajoutées ci-dessus.
    _excl_ids = {ex.ruleId for ex in inp.exclusions}
    for ar in inp.applicableRules:
        if (ar.category == "exclusion" and ar.integrationStatus == "integrated"
                and ar.id and ar.id not in _excl_ids):
            applied.append(AppliedRule(
                ruleId=ar.id, category="exclusion",
                label=ar.label or ar.id, detail=ar.detail, source=ar.source))

    non_integ = [NonIntegratedRule(id=ar.id, label=ar.label or (ar.id or "règle"),
                                   detail=ar.detail, source=ar.source)
                 for ar in inp.applicableRules if ar.integrationStatus == "not_integrated"]

    def _gj(g: Optional[BaseGeometry]):
        if g is None or g.is_empty:
            return None
        return geojson_from_shape(to_wgs(g))

    return GabaritResult(
        status="ok",
        surfaceParcelleM2=_round(surface_parcelle),
        zoneImplantationM2=_round(zone_m2),
        plafondEmpriseM2=None if plafond_m2 is None else _round(plafond_m2),
        plafondEmpriseStatus=mf.status,
        hauteurReglementaireM=None if hauteur is None else _round(hauteur),
        hauteurSource=mh.source,
        hauteurStatus=mh.status,
        hauteurBase=mh.basis,
        hauteurEstimee=bool(getattr(mh, "estimee", False)),   # RECETTE-PROD-1 (A7) — étiquette « Estimé »
        hauteurEgoutM=None if mh.egoutMeters is None else _round(mh.egoutMeters),
        coverage=coverage,
        partExcluePct=part_exclue_pct,
        niveauxRetenus=niveaux_retenus,
        reculSepRetenuM=recul_sep_retenu,
        reculSepScenario=scenario_txt,
        appliedRules=applied,
        nonIntegratedRules=non_integ,
        contourGeoJSON=_gj(parcel_m),
        zoneImplantationGeoJSON=_gj(zone_m),
        retraitsGeoJSON=_gj(retrait_m),
        exclusionsGeoJSON=_gj(excl_in_parcel_m),
    )
