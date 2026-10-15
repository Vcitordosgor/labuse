"""Contrôles.

Deux familles :
  - GÉOMÉTRIQUES (bool) : cohérence interne, utilisées par le moteur pour accepter/refuser un
    candidat, ET re-vérifiées indépendamment par les tests du LOT C.
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

_TOL_AIRE = 1e-6        # aire d'intersection considérée nulle (bruit flottant)
_TOL_CONTENU = 0.05     # tolérance de contenance (m) sur buffer


# --------------------------------------------------------------- géométriques (bool)
@dataclass
class CheckGeo:
    nom: str
    ok: bool
    detail: str = ""


def _plan_objs(scene: Scene):
    return [o for o in scene.objets
            if o.kind in ("batiment_emprise", "place", "allee", "acces", "espace_libre")]


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

    # 1. bâtiments contenus dans la zone d'implantation
    hors = [b for b in batis if not zone.buffer(_TOL_CONTENU).contains(b)]
    checks.append(CheckGeo("bâtiments ⊆ zone d'implantation", not hors,
                           f"{len(hors)} hors zone" if hors else f"{len(batis)} bâtiment(s) dans la zone"))

    # 2. places et allées dans l'assiette, hors bâtiments
    bati_u = unary_union(batis) if batis else None
    dedans = all(assiette.buffer(_TOL_CONTENU).contains(g) for g in places + allees + acces)
    hors_bati = True
    if bati_u is not None:
        hors_bati = all(g.intersection(bati_u).area <= _TOL_AIRE for g in places + allees + acces)
    checks.append(CheckGeo("places/allées/accès ⊆ assiette, hors bâti", dedans and hors_bati))

    # 3. aucun chevauchement entre objets plan (aire d'intersection = 0)
    plan = [o.geom_world for o in _plan_objs(scene)]
    chev = 0
    for i in range(len(plan)):
        for j in range(i + 1, len(plan)):
            if plan[i].intersection(plan[j]).area > _TOL_AIRE:
                chev += 1
    checks.append(CheckGeo("aucun chevauchement (aire ∩ = 0)", chev == 0, f"{chev} paire(s)"))

    # 4. chaque place touche une allée
    allee_u = unary_union(allees) if allees else None
    if places and allee_u is not None:
        touche = all(p.distance(allee_u) < 1e-6 for p in places)
    else:
        touche = not places
    checks.append(CheckGeo("chaque place touche une allée", touche))

    # 5. allées reliées à l'accès ; accès sur une limite classée voie
    acc_ok = False
    if acces and allee_u is not None:
        acc_u = unary_union(acces)
        relie = acc_u.distance(allee_u) < 1e-6
        voie_u = unary_union(terrain.voie_edges) if terrain.voie_edges else None
        sur_voie = (voie_u is not None and acc_u.distance(voie_u) < 0.5)
        acc_ok = relie and sur_voie
    elif not places:
        acc_ok = True
    checks.append(CheckGeo("allées reliées à l'accès, accès sur voie", acc_ok))

    # 6. largeur d'allée ≥ convention
    larg_ok = True
    for o in scene.of("allee"):
        minx, miny, maxx, maxy = o.geom_local.bounds
        if min(maxx - minx, maxy - miny) < conv.allee_largeur_m - 0.05:
            larg_ok = False
    checks.append(CheckGeo(f"largeur d'allée ≥ {conv.allee_largeur_m} m", larg_ok))

    # 7. dimensions des modules ≥ minimum de la convention
    dim_ok = True
    for o in modules:
        minx, miny, maxx, maxy = o.geom_local.bounds
        w, d = (maxx - minx), (maxy - miny)
        lref = conv.largeur_module(o.type_logement)
        if w < lref - 0.05 or d < conv.profondeur_logement_m() - 0.05:
            dim_ok = False
    checks.append(CheckGeo("dimensions modules ≥ convention", dim_ok))

    # 8. nombre annoncé = nombre d'objets dessinés
    nb_ok = (cap.logements == len(modules)) and (cap.places == len(places))
    checks.append(CheckGeo("nb annoncé = nb dessiné (logements, places)", nb_ok))

    # 9. surfaces du tableau = surfaces mesurées
    sdp_mes = round(sum(o.geom_local.area for o in scene.objets
                        if o.kind in ("module", "noyau", "coursive")), 1)
    emp_mes = round(unary_union([o.geom_local for o in scene.of("batiment_emprise")]).area, 1) if batis else 0.0
    surf_ok = abs(sdp_mes - cap.sdp_m2) < 0.2 and abs(emp_mes - cap.emprise_sol_m2) < 0.2
    checks.append(CheckGeo("surfaces tableau = surfaces mesurées", surf_ok))

    # 10. niveaux × hauteur ≤ règle (si validée)
    if regles.hauteur_egout.validee and regles.hauteur_egout.valeur is not None:
        h = cap.niveaux * conv.hauteur_etage_m
        checks.append(CheckGeo("niveaux × hauteur ≤ hauteur égout",
                               h <= regles.hauteur_egout.valeur + 1e-9,
                               f"{h:.1f} m ≤ {regles.hauteur_egout.valeur:.1f} m"))
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


def controles_reglementaires(scene: Scene, terrain, conv: Conventions, cap: Capacite,
                             regles: ReglesZone) -> list[ControleReg]:
    out: list[ControleReg] = []

    # Emprise au sol (CES) — règle validée
    r = regles.emprise_ces
    if r.validee and r.valeur is not None:
        plafond = terrain.contenance_totale_m2 * r.valeur / 100.0
        ok = cap.emprise_sol_m2 <= plafond + 1e-6
        out.append(ControleReg("Emprise au sol", f"≤ {plafond:.0f} m² ({r.valeur:.0f} %)",
                               f"{cap.emprise_sol_m2:.0f} m²", REUSSI if ok else ECHOUE,
                               r.citation_complete, f"écart {plafond - cap.emprise_sol_m2:+.0f} m²"))
    else:
        out.append(ControleReg("Emprise au sol", "—", f"{cap.emprise_sol_m2:.0f} m²", NON_EFFECTUE))

    # Hauteur (égout) — règle validée
    r = regles.hauteur_egout
    if r.validee and r.valeur is not None:
        h = cap.niveaux * conv.hauteur_etage_m
        ok = h <= r.valeur + 1e-9
        out.append(ControleReg("Hauteur", f"≤ {r.valeur:.0f} m à l'égout",
                               f"R+{cap.niveaux - 1} ≈ {h:.0f} m", REUSSI if ok else ECHOUE,
                               r.citation_complete))
    else:
        out.append(ControleReg("Hauteur", "—", f"R+{cap.niveaux - 1}", NON_EFFECTUE))

    # Reculs (voie + séparatives) — règles validées ; bâti dans la zone construite avec ces reculs
    rv, rs = regles.recul_voie, regles.recul_separatives
    batis = [o.geom_world for o in scene.of("batiment_emprise")]
    dans_zone = all(terrain.zone_implantation.buffer(_TOL_CONTENU).contains(b) for b in batis)
    if rv.validee and rs.validee:
        cit = " ; ".join(c for c in (rv.citation_complete, rs.citation_complete) if c)
        out.append(ControleReg("Reculs", f"voie {rv.valeur:.0f} m · séparatives {rs.valeur:.0f} m",
                               "bâti dans la zone d'implantation", REUSSI if dans_zone else ECHOUE, cit))
    else:
        out.append(ControleReg("Reculs", "—", "bâti dans la zone", NON_EFFECTUE))

    # Perméabilité (pleine terre) — règle validée
    r = regles.pleine_terre
    if r.validee and r.valeur is not None:
        requis = terrain.contenance_totale_m2 * r.valeur / 100.0
        ok = cap.pleine_terre_m2 >= requis - 1e-6
        out.append(ControleReg("Perméabilité (pleine terre)", f"≥ {requis:.0f} m² ({r.valeur:.0f} %)",
                               f"{cap.pleine_terre_m2:.0f} m²", REUSSI if ok else ECHOUE,
                               r.citation_complete, f"écart {cap.pleine_terre_m2 - requis:+.0f} m²"))
    else:
        out.append(ControleReg("Perméabilité (pleine terre)", "—", f"{cap.pleine_terre_m2:.0f} m²", NON_EFFECTUE))

    # Stationnement — barème validé
    b = regles.stationnement
    if b.validee and cap.places_imposees is not None:
        ok = cap.places >= cap.places_imposees
        out.append(ControleReg("Stationnement", f"≥ {cap.places_imposees} places (barème par typologie)",
                               f"{cap.places} places dessinées", REUSSI if ok else ECHOUE,
                               b.citation_complete,
                               f"écart {cap.places - cap.places_imposees:+d}"))
    else:
        out.append(ControleReg("Stationnement", "—", f"{cap.places} places dessinées", NON_EFFECTUE))

    # Espaces verts — AUCUNE règle validée distincte (seule la pleine terre l'est)
    out.append(ControleReg("Espaces verts", "règle non validée (distincte de la pleine terre)", "—",
                           NON_EFFECTUE, detail="le règlement UA ne fixe pas d'espaces verts chiffrés hors pleine terre"))

    # Destination — non modélisée par ce moteur
    out.append(ControleReg("Destination", "non modélisée", "logements seuls", NON_EFFECTUE))

    # Non modélisées
    out.append(ControleReg("Distance entre constructions", "non modélisée", "—", NON_EFFECTUE))
    out.append(ControleReg("Locaux vélos · déchets", "non modélisés", "—", NON_EFFECTUE))

    # Contraintes cartographiées — absentes du terrain => Non applicable
    presentes = terrain.contraintes_presentes
    if not presentes:
        out.append(ControleReg("PPR / ER / EBC / SUP", "aucune contrainte sur le terrain", "—",
                               NON_APPLICABLE, detail="aucun objet PPR/ER/EBC/SUP n'intersecte l'assiette"))
    else:
        out.append(ControleReg("PPR / ER / EBC / SUP", "contrainte présente", ", ".join(presentes),
                               NON_EFFECTUE, detail="présente mais non interprétée par ce moteur"))
    return out


def statut_etude(controles: list[ControleReg], geo_ok: bool) -> str:
    if not geo_ok:
        return "simulation impossible"
    if any(c.resultat == ECHOUE for c in controles):
        return "à compléter"
    return "exploitable en pré-faisabilité"
