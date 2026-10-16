"""Contrôles.

Deux familles :
  - GÉOMÉTRIQUES (bool) : cohérence interne, utilisées par le moteur pour accepter/refuser un
    candidat, ET re-vérifiées indépendamment par les tests du LOT C. Le non-chevauchement est testé
    sur TOUS les couples d'objets du plan de sol (module, noyau, coursive, place, allée, accès,
    espace libre) ; la somme des surfaces mesurées = l'assiette.
  - RÉGLEMENTAIRES (4 états) : Réussi · Échoué · Non effectué · Non applicable.
      * Réussi UNIQUEMENT si la règle est `validee` avec citation ET que la mesure la respecte.
      * Règle non validée ou non modélisée = Non effectué (jamais Réussi).
      * Contrainte absente du terrain = Non applicable.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from shapely.ops import unary_union

from .capacite import Capacite
from .conventions import Conventions
from .geometrie import Scene
from .regles import ReglesZone

REUSSI = "Réussi"
ECHOUE = "Échoué"
NON_EFFECTUE = "Non effectué"
NON_APPLICABLE = "Non applicable"

_TOL_AIRE = 1e-6
_TOL_CONTENU = 0.05


@dataclass
class CheckGeo:
    nom: str
    ok: bool
    detail: str = ""


def _ground_tiles(scene: Scene):
    """Objets du PLAN DE SOL (niveau 0 pour le bâti) qui pavent l'assiette sans se chevaucher."""
    out = []
    for o in scene.objets:
        if o.kind in ("place", "allee", "acces", "espace_libre"):
            out.append(o)
        elif o.kind in ("module", "noyau", "coursive") and o.niveau == 0:
            out.append(o)
    return out


def verifier_geometrie(scene: Scene, terrain, conv: Conventions, cap: Capacite,
                       regles: ReglesZone) -> list[CheckGeo]:
    checks: list[CheckGeo] = []
    zone = terrain.zone_implantation
    assiette = terrain.assiette
    batis = [o.geom_world for o in scene.of("batiment_emprise")]
    places = [o.geom_world for o in scene.of("place")]
    allees = [o.geom_world for o in scene.of("allee")]
    acces = [o.geom_world for o in scene.of("acces")]
    modules = scene.of("module")

    hors = [b for b in batis if not zone.buffer(_TOL_CONTENU).contains(b)]
    checks.append(CheckGeo("bâtiments ⊆ zone d'implantation", not hors,
                           f"{len(hors)} hors zone" if hors else f"{len(batis)} bâtiment(s) dans la zone"))

    bati_u = unary_union(batis) if batis else None
    dedans = all(assiette.buffer(_TOL_CONTENU).contains(g) for g in places + allees + acces)
    hors_bati = True
    if bati_u is not None:
        hors_bati = all(g.intersection(bati_u).area <= _TOL_AIRE for g in places + allees + acces)
    checks.append(CheckGeo("places/allées/accès ⊆ assiette, hors bâti", dedans and hors_bati))

    # non-chevauchement sur TOUS les couples du plan de sol (aire d'intersection = 0)
    tiles = [o.geom_world for o in _ground_tiles(scene)]
    chev = 0
    for i in range(len(tiles)):
        for j in range(i + 1, len(tiles)):
            if tiles[i].intersection(tiles[j]).area > _TOL_AIRE:
                chev += 1
    checks.append(CheckGeo("aucun chevauchement — TOUS couples (aire ∩ = 0)", chev == 0, f"{chev} paire(s)"))

    # somme des surfaces mesurées = assiette
    somme = sum(t.area for t in tiles)
    checks.append(CheckGeo("somme des surfaces mesurées = assiette", abs(somme - assiette.area) < 1.0,
                           f"Σ={somme:.1f} vs assiette {assiette.area:.1f}"))

    allee_u = unary_union(allees) if allees else None
    if places and allee_u is not None:
        touche = all(p.distance(allee_u) < 1e-6 for p in places)
    else:
        touche = not places
    checks.append(CheckGeo("chaque place touche une allée", touche))

    # allées reliées à l'accès ; accès sur voie ; aucune allée sans places desservies
    acc_ok = False
    if acces and allee_u is not None:
        acc_u = unary_union(acces)
        relie = acc_u.distance(allee_u) < 1e-6
        voie_u = unary_union(terrain.voie_edges) if terrain.voie_edges else None
        sur_voie = (voie_u is not None and acc_u.distance(voie_u) < 0.6)
        # chaque morceau d'allée est desservi (a au moins une place) et relié à l'accès
        places_u = unary_union(places) if places else None
        allees_desservies = all(
            (places_u is not None and a.distance(places_u) < 1e-6) and a.distance(acc_u) < 1e-6
            for a in allees)
        acc_ok = relie and sur_voie and allees_desservies
    elif not places:
        acc_ok = True
    checks.append(CheckGeo("allées reliées à l'accès (sur voie), aucune en cul-de-sac", acc_ok))

    larg_ok = all(min(o.geom_local.bounds[2] - o.geom_local.bounds[0],
                      o.geom_local.bounds[3] - o.geom_local.bounds[1]) >= conv.allee_largeur_m - 0.05
                  for o in scene.of("allee"))
    checks.append(CheckGeo(f"largeur d'allée ≥ {conv.allee_largeur_m} m", larg_ok))

    dim_ok = True
    for o in modules:
        mnx, mny, mxx, mxy = o.geom_local.bounds
        if (mxx - mnx) < conv.largeur_module(o.type_logement) - 0.05 or \
           (mxy - mny) < conv.profondeur_logement_m() - 0.05:
            dim_ok = False
    checks.append(CheckGeo("dimensions modules ≥ convention", dim_ok))

    nb_ok = (cap.logements == len(modules)) and (cap.places == len(places))
    checks.append(CheckGeo("nb annoncé = nb dessiné (logements, places)", nb_ok))

    sdp_mes = round(sum(o.geom_local.area for o in scene.objets
                        if o.kind in ("module", "noyau", "coursive")), 1)
    emp_mes = round(unary_union([o.geom_local for o in scene.of("batiment_emprise")]).area, 1) if batis else 0.0
    surf_ok = abs(sdp_mes - cap.sdp_m2) < 0.2 and abs(emp_mes - cap.emprise_sol_m2) < 0.2
    checks.append(CheckGeo("surfaces tableau = surfaces mesurées", surf_ok))

    r = regles.hauteur_plafond
    if r.validee and r.valeur is not None:
        h = cap.niveaux * conv.hauteur_etage_m
        checks.append(CheckGeo("niveaux × hauteur ≤ hauteur réglementaire",
                               h <= r.valeur + 1e-9, f"{h:.1f} m ≤ {r.valeur:.1f} m"))
    return checks


def geometrie_valide(checks: list[CheckGeo]) -> bool:
    return all(c.ok for c in checks)


# --------------------------------------------------------------- réglementaires (4 états)
@dataclass
class ControleReg:
    nom: str
    regle: str
    mesure: str
    resultat: str
    citation: Optional[str] = None
    detail: Optional[str] = None


def _n_batiments(scene: Scene) -> int:
    return len(scene.of("batiment_emprise"))


def _ppr_bleue_touche_bati(scene: Scene, terrain) -> bool:
    if terrain.ppr_bleue is None or terrain.ppr_bleue.is_empty:
        return False
    batis = [o.geom_world for o in scene.of("batiment_emprise")]
    if not batis:
        return False
    return unary_union(batis).intersection(terrain.ppr_bleue).area > _TOL_AIRE


def controles_reglementaires(scene: Scene, terrain, conv: Conventions, cap: Capacite,
                             regles: ReglesZone) -> list[ControleReg]:
    out: list[ControleReg] = []
    contenance = terrain.contenance_totale_m2

    r = regles.emprise_ces
    if r.validee and r.valeur is not None:
        plafond = contenance * r.valeur / 100.0
        ok = cap.emprise_sol_m2 <= plafond + 1e-6
        out.append(ControleReg("Emprise au sol", f"≤ {plafond:.0f} m² ({r.valeur:.0f} % de la contenance)",
                               f"{cap.emprise_sol_m2:.0f} m²", REUSSI if ok else ECHOUE,
                               r.citation_complete, f"écart {plafond - cap.emprise_sol_m2:+.0f} m²"))
    else:
        out.append(ControleReg("Emprise au sol", "règle non validée", f"{cap.emprise_sol_m2:.0f} m²", NON_EFFECTUE))

    r = regles.hauteur_plafond
    if r.validee and r.valeur is not None:
        h = cap.niveaux * conv.hauteur_etage_m
        ok = h <= r.valeur + 1e-9
        base = "à l'égout" if regles.hauteur_egout.validee else "au faîtage (pas d'égout chiffré)"
        out.append(ControleReg("Hauteur", f"≤ {r.valeur:.0f} m {base}",
                               f"R+{cap.niveaux - 1} ≈ {h:.0f} m", REUSSI if ok else ECHOUE, r.citation_complete))
    else:
        out.append(ControleReg("Hauteur", "règle non validée", f"R+{cap.niveaux - 1}", NON_EFFECTUE))

    rv, rs = regles.recul_voie, regles.recul_separatives
    batis = [o.geom_world for o in scene.of("batiment_emprise")]
    dans_zone = all(terrain.zone_implantation.buffer(_TOL_CONTENU).contains(b) for b in batis)
    if rv.validee and rs.validee:
        cit = " ; ".join(c for c in (rv.citation_complete, rs.citation_complete) if c)
        out.append(ControleReg("Reculs", f"voie {rv.valeur:.0f} m · séparatives {rs.valeur:.0f} m",
                               "bâti dans la zone d'implantation", REUSSI if dans_zone else ECHOUE, cit))
    else:
        out.append(ControleReg("Reculs", "règle non validée", "bâti dans la zone", NON_EFFECTUE))

    r = regles.pleine_terre
    if r.validee and r.valeur is not None:
        requis = contenance * r.valeur / 100.0
        ok = cap.pleine_terre_m2 >= requis - 1e-6
        out.append(ControleReg("Perméabilité (pleine terre)", f"≥ {requis:.0f} m² ({r.valeur:.0f} % de la contenance)",
                               f"{cap.pleine_terre_m2:.0f} m²", REUSSI if ok else ECHOUE,
                               r.citation_complete, f"écart {cap.pleine_terre_m2 - requis:+.0f} m²"))
    else:
        out.append(ControleReg("Perméabilité (pleine terre)", "règle non validée",
                               f"{cap.pleine_terre_m2:.0f} m²", NON_EFFECTUE))

    b = regles.stationnement
    if b.validee and cap.places_imposees is not None:
        ok = cap.places >= cap.places_imposees
        out.append(ControleReg("Stationnement", f"≥ {cap.places_imposees} places (barème validé)",
                               f"{cap.places} places dessinées", REUSSI if ok else ECHOUE,
                               b.citation_complete, f"écart {cap.places - cap.places_imposees:+d}"))
    else:
        out.append(ControleReg("Stationnement", "barème non validé", f"{cap.places} places dessinées", NON_EFFECTUE))

    # Distance entre constructions : plusieurs bâtiments => Non effectué (non modélisé) ; un seul => Non applicable
    nb_bati = _n_batiments(scene)
    if nb_bati > 1:
        out.append(ControleReg("Distance entre constructions", "non modélisée",
                               f"{nb_bati} bâtiments", NON_EFFECTUE,
                               detail="plusieurs volumes : la distance inter-bâtiments doit être vérifiée"))
    else:
        out.append(ControleReg("Distance entre constructions", "un seul bâtiment", "—", NON_APPLICABLE))

    out.append(ControleReg("Locaux vélos · déchets", "non modélisés", "—", NON_EFFECTUE))

    # PPR rouge (interdiction) : déduite de l'implantation
    if terrain.contraintes.get("ppr_rouge"):
        out.append(ControleReg("PPR zone rouge (interdiction)", "inconstructible", f"{terrain.ppr_rouge_m2:.0f} m²",
                               NON_EFFECTUE, detail="retirée de la zone d'implantation (hypothèse prudente)"))
    else:
        out.append(ControleReg("PPR zone rouge (interdiction)", "absente du terrain", "—", NON_APPLICABLE))

    # PPR bleue (prescription) : signalée, non interprétée ; à compléter si elle touche le bâti
    if terrain.contraintes.get("ppr_bleue"):
        touche = _ppr_bleue_touche_bati(scene, terrain)
        out.append(ControleReg("PPR zone bleue (prescription)", "signalée, non interprétée",
                               ("touche le bâti proposé" if touche else "ne touche pas le bâti"),
                               NON_EFFECTUE, detail=("prescriptions à lire ; l'étude passe à compléter"
                                                     if touche else "signalée")))
    else:
        out.append(ControleReg("PPR zone bleue (prescription)", "absente du terrain", "—", NON_APPLICABLE))

    # ER / EBC / SUP
    autres = [k for k in ("emplacement_reserve", "ebc", "sup", "servitude") if terrain.contraintes.get(k)]
    if autres:
        out.append(ControleReg("ER / EBC / SUP / servitudes", "présente(s)", ", ".join(autres),
                               NON_EFFECTUE, detail="non interprétées par ce moteur"))
    else:
        out.append(ControleReg("ER / EBC / SUP / servitudes", "absentes du terrain", "—", NON_APPLICABLE))
    return out


def statut_etude(controles: list[ControleReg], geo_ok: bool, *, scene: Scene, terrain) -> str:
    if not geo_ok:
        return "simulation impossible"
    if any(c.resultat == ECHOUE for c in controles):
        return "à compléter"
    # plusieurs bâtiments (distance non contrôlée) OU PPR bleue qui touche le bâti -> à compléter
    if _n_batiments(scene) > 1:
        return "à compléter"
    if _ppr_bleue_touche_bati(scene, terrain):
        return "à compléter"
    return "exploitable en pré-faisabilité"
