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
# ETUDE-V6 (Lot B) — 5ᵉ état : ambiguïté de DONNÉE ou de TEXTE (PPR présent non interprété, prospect
# non chiffrable, servitude présente, barème manquant). ≠ « Non effectué » (non calculé, ex. locaux
# vélos) et ≠ « Non applicable » (contrainte absente). « À confirmer » interdit un verdict « Exploitable ».
A_CONFIRMER = "À confirmer"

ETATS = (REUSSI, ECHOUE, NON_EFFECTUE, NON_APPLICABLE, A_CONFIRMER)

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
        # ETUDE-V6-2 (Lot 3) — la rampe de sous-sol est un objet du PLAN DE SOL : elle PAVE l'assiette
        # au même titre que l'accès aérien (sinon la somme des surfaces ne boucle pas).
        if o.kind in ("place", "allee", "acces", "rampe", "espace_libre"):
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
    tiles = [(o.geom_world if o.geom_world.is_valid else o.geom_world.buffer(0))
             for o in _ground_tiles(scene)]
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

    # allée COUPÉE au droit des places : aucun tronçon mort (ni place desservie, ni jonction d'accès).
    # Une place touche l'allée sur sa largeur ; on couvre l'allée par (places ∪ accès) bufferisé d'une
    # profondeur de place. Un prolongement d'allée dans le vide (ex. au-delà de la dernière place) reste.
    if places and allee_u is not None:
        couvre = unary_union(places + acces).buffer(conv.place_longueur_m)
        mort = allee_u.difference(couvre)
        checks.append(CheckGeo("allée sans tronçon mort (coupée au droit des places)",
                               mort.area < 1.0, f"{mort.area:.1f} m² morts"))

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

    # ETUDE-V6-2 (Lot 3) — en sous-sol, les places sont au niveau −1 (aucun objet « place » au sol) :
    # on confronte alors le nombre annoncé au nombre logé au sous-sol, pas aux places dessinées.
    places_dessinees = (getattr(cap, "places_sous_sol", 0)
                        if getattr(cap, "stationnement_mode", "aerien") == "sous_sol" else len(places))
    nb_ok = (cap.logements == len(modules)) and (cap.places == places_dessinees)
    checks.append(CheckGeo("nb annoncé = nb dessiné (logements, places)", nb_ok))

    # SDP mesurée = modules + noyaux (coursive ouverte HORS SDP, art. R111-22 c. urb. — LOT D)
    sdp_mes = round(sum(o.geom_local.area for o in scene.objets
                        if o.kind in ("module", "noyau")), 1)
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


def _distance_min_batiments(scene: Scene) -> Optional[float]:
    """Plus petite distance MESURÉE (bord à bord) entre deux emprises bâties, en m. None si < 2."""
    batis = [o.geom_world for o in scene.of("batiment_emprise")]
    if len(batis) < 2:
        return None
    return min(batis[i].distance(batis[j]) for i in range(len(batis)) for j in range(i + 1, len(batis)))


def _distance_requise(dc, cap: Capacite, conv: Conventions) -> tuple[float, str, str]:
    """(distance requise en m, libellé de règle, mention) pour une règle de distance CHIFFRABLE.
    La hauteur retenue est celle du bâtiment proposé (niveaux × hauteur d'étage) ; `cumulee` = H+h
    (deux volumes identiques dans le modèle → 2×h), `plus_haut` = H du plus haut (= h)."""
    h = cap.niveaux * conv.hauteur_etage_m
    if dc.forme == "fixe":
        return float(dc.min_m or 0.0), f"≥ {dc.min_m:.1f} m (distance fixe)", ""
    if dc.forme == "relative":
        base = 2.0 * h if dc.base_hauteur == "cumulee" else h
        req = (dc.fraction_hauteur or 0.0) * base
        plancher = float(dc.min_m or 0.0)
        req_final = max(req, plancher)
        quoi = "H+h" if dc.base_hauteur == "cumulee" else "H"
        lib = f"≥ {dc.fraction_hauteur:g}×{quoi} = {req:.1f} m" + (f", min {plancher:.0f} m" if plancher else "")
        mention = f"hauteur retenue {h:.1f} m (R+{cap.niveaux - 1})"
        return req_final, lib, mention
    if dc.forme == "conditionnelle":
        # cas le plus strict = façades AVEC ouvertures
        req = float(dc.avec_ouvertures_m or 0.0)
        mention = "cas le plus strict retenu (façades avec ouvertures)"
        if dc.fraction_hauteur is not None:
            base = 2.0 * h if dc.base_hauteur == "cumulee" else h
            req = max(req, dc.fraction_hauteur * base)
            mention += f" ; hauteur retenue {h:.1f} m"
        lib = f"≥ {req:.1f} m (avec ouvertures ; sans : {dc.sans_ouvertures_m:g} m)" if dc.sans_ouvertures_m \
            else f"≥ {req:.1f} m (façades avec ouvertures)"
        return req, lib, mention
    # contiguité
    if dc.contiguite_autorisee:
        return 0.0, "contiguïté autorisée (aucune distance imposée)", "les volumes peuvent être accolés"
    return 1e-6, "contiguïté non autorisée (volumes disjoints)", ""


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

    # Prospect / hauteur relative (ex. L ≥ h/2) : non chiffrable par le moteur -> Non effectué
    if regles.prospect is not None:
        out.append(ControleReg("Prospect (hauteur relative)", "non chiffrable par le moteur",
                               "hauteur bornée par la seule règle absolue", A_CONFIRMER,
                               citation=None,
                               detail=(regles.prospect.citation or "règle de prospect L ≥ h/2 — "
                                       "à vérifier par l'architecte")))
    else:
        out.append(ControleReg("Prospect (hauteur relative)", "pas de règle de prospect", "—", NON_APPLICABLE))

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
    sous_sol = getattr(cap, "stationnement_mode", "aerien") == "sous_sol"
    place_mot = "places au sous-sol" if sous_sol else "places dessinées"
    if b.validee and cap.places_imposees is not None:
        ok = cap.places >= cap.places_imposees
        out.append(ControleReg("Stationnement", f"≥ {cap.places_imposees} places (barème validé)",
                               f"{cap.places} {place_mot}", REUSSI if ok else ECHOUE,
                               b.citation_complete, f"écart {cap.places - cap.places_imposees:+d}"))
    else:
        # ETUDE-V6 — barème manquant = ambiguïté (exigence non chiffrée) → À confirmer, pas « Non effectué ».
        out.append(ControleReg("Stationnement", "barème non servi pour cette zone", f"{cap.places} {place_mot}",
                               A_CONFIRMER, detail="exigence de stationnement non chiffrée ici — à confirmer au règlement"))

    # ETUDE-V6-2 (Lot 3) — en SOUS-SOL, l'emprise du parking enterré doit tenir sous l'EMPRISE
    # RÉGLEMENTAIRE (CES × contenance) ; c'est ce contrôle (pas le comptage) qui plafonne la capacité.
    if sous_sol:
        rc = regles.emprise_ces
        if rc.validee and rc.valeur is not None:
            emp_max = contenance * rc.valeur / 100.0
            ok = cap.emprise_sous_sol_m2 <= emp_max + 1e-6
            out.append(ControleReg(
                "Emprise du sous-sol", f"≤ {emp_max:.0f} m² (emprise réglementaire, CES {rc.valeur:.0f} %)",
                f"{cap.emprise_sous_sol_m2:.0f} m² ({cap.places_sous_sol} places × {cap.emprise_sous_sol_m2 / cap.places_sous_sol:.0f} m²)"
                if cap.places_sous_sol else f"{cap.emprise_sous_sol_m2:.0f} m²",
                REUSSI if ok else ECHOUE, rc.citation_complete,
                f"écart {emp_max - cap.emprise_sous_sol_m2:+.0f} m²"))
        else:
            out.append(ControleReg("Emprise du sous-sol", "CES non servi — emprise réglementaire non chiffrée",
                                   f"{cap.emprise_sous_sol_m2:.0f} m²", A_CONFIRMER,
                                   detail="emprise réglementaire du sous-sol à confirmer au règlement"))

    # Distance entre constructions (PLU-CALIBRAGE-10, ex-art. 8) : MESURÉE sur la géométrie et
    # confrontée à la règle de la zone. Convention des 4 états :
    #   · Non applicable = UN SEUL BÂTIMENT (contrainte absente du projet, cf. ci-dessous) OU silence
    #                      prouvé (le règlement dit qu'il ne réglemente pas) ;
    #   · Non effectué   = PLUSIEURS bâtiments + règle NON servie (zone/commune non calibrée, non lue,
    #                      forme hors schéma) ;
    #   · Réussi/Échoué  = PLUSIEURS bâtiments + règle servie chiffrable, confrontée à la mesure.
    nb_bati = _n_batiments(scene)
    dc = regles.distance_constructions
    dmes = _distance_min_batiments(scene)
    if nb_bati <= 1:
        # IMPLANTATION-4 (distance mono-bâtiment) — un SEUL bâtiment (annexes dessinées comprises dans
        # le compte des emprises) : aucune distance entre constructions à mesurer, la contrainte est
        # ABSENTE du projet → « Non applicable · un seul bâtiment », zone calibrée ou non. On INVERSE le
        # choix d'origine (qui classait une lacune de calibrage en « Non effectué » même en mono-bâtiment) :
        # c'est exactement la définition de « Non applicable » posée dès IMPLANTATION-1 (contrainte absente).
        out.append(ControleReg("Distance entre constructions", "sans objet (un seul bâtiment)",
                               "un seul bâtiment", NON_APPLICABLE,
                               detail="un seul bâtiment : aucune construction en vis-à-vis à mesurer"))
    elif dc.est_silence:
        cmin = conv.retrait_inter_barre_m
        mes = f"{dmes:.1f} m mesurés · convention {cmin:.0f} m (Estimé)"
        out.append(ControleReg("Distance entre constructions", "non réglementé (silence prouvé)", mes,
                               NON_APPLICABLE, dc.citation_complete,
                               detail=(f"le règlement ne fixe pas de distance entre constructions ; "
                                       f"distance de convention {cmin:.0f} m appliquée au tracé (Estimé)")))
    elif dc.est_chiffrable:
        requis, lib, mention = _distance_requise(dc, cap, conv)
        ok = dmes >= requis - 1e-6
        out.append(ControleReg("Distance entre constructions", lib, f"{dmes:.1f} m mesurés",
                               REUSSI if ok else ECHOUE, dc.citation_complete, detail=(mention or None)))
    else:
        out.append(ControleReg("Distance entre constructions", "règle non servie (zone non calibrée)",
                               f"{nb_bati} bâtiments · {dmes:.1f} m mesurés", NON_EFFECTUE,
                               detail="distance inter-bâtiments non calibrée sur cette zone — à vérifier"))

    out.append(ControleReg("Locaux vélos · déchets", "non modélisés", "—", NON_EFFECTUE))

    # PPR rouge (interdiction) : déduite de l'implantation, mais l'interdiction reste à CONFIRMER au
    # règlement (on la retire par prudence, ce n'est pas une preuve de constructibilité du reste).
    if terrain.contraintes.get("ppr_rouge"):
        out.append(ControleReg("PPR zone rouge (interdiction)", "retirée de la zone (prudence)",
                               f"{terrain.ppr_rouge_m2:.0f} m²", A_CONFIRMER,
                               detail="partie interdite retirée de l'implantation ; interdiction à confirmer au règlement PPR"))
    else:
        out.append(ControleReg("PPR zone rouge (interdiction)", "absente du terrain", "—", NON_APPLICABLE))

    # PPR bleue (prescription) : signalée, non interprétée → à confirmer (prescriptions à lire).
    if terrain.contraintes.get("ppr_bleue"):
        touche = _ppr_bleue_touche_bati(scene, terrain)
        out.append(ControleReg("PPR zone bleue (prescription)", "signalée, non interprétée",
                               ("touche le bâti proposé" if touche else "ne touche pas le bâti"),
                               A_CONFIRMER, detail=("prescriptions à lire : tant qu'elles ne le sont pas, l'étude "
                                                    "n'est pas exploitable" if touche else "signalée, prescriptions à lire")))
    else:
        out.append(ControleReg("PPR zone bleue (prescription)", "absente du terrain", "—", NON_APPLICABLE))

    # ER / EBC / SUP
    autres = [k for k in ("emplacement_reserve", "ebc", "sup", "servitude") if terrain.contraintes.get(k)]
    if autres:
        out.append(ControleReg("ER / EBC / SUP / servitudes", "présente(s)", ", ".join(autres),
                               A_CONFIRMER, detail="servitude(s) présente(s) non interprétée(s) par ce moteur — à confirmer"))
    else:
        out.append(ControleReg("ER / EBC / SUP / servitudes", "absentes du terrain", "—", NON_APPLICABLE))
    return out


def statut_etude(controles: list[ControleReg], geo_ok: bool, *, scene: Scene, terrain, regles) -> str:
    if not geo_ok:
        return "simulation impossible"
    if any(c.resultat == ECHOUE for c in controles):
        return "à compléter"
    # une règle de HAUTEUR non chiffrable (prospect L>H) ne laisse jamais l'étude exploitable
    if regles.hauteur_non_chiffrable:
        return "à compléter"
    # PLU-CALIBRAGE-10 : plusieurs bâtiments ne bloquent plus l'étude SI la distance inter-bâtiments
    # est servie (contrôle Réussi ou Non applicable=silence+convention). Elle ne reste bloquante que
    # si la règle n'est pas servie (contrôle Non effectué).
    if _n_batiments(scene) > 1:
        dc_ctrl = next((c for c in controles if c.nom == "Distance entre constructions"), None)
        if dc_ctrl is None or dc_ctrl.resultat == NON_EFFECTUE:
            return "à compléter"
    if _ppr_bleue_touche_bati(scene, terrain):
        return "à compléter"
    return "exploitable en pré-faisabilité"


# ETUDE-V6 (Lot B) — verdict GLOBAL de l'étude, dans les trois libellés du mandat. Distinct de
# `statut_etude` (conservé pour l'écran historique). Règle clé : un PPR, un accès ou un stationnement
# INDÉTERMINÉ (À confirmer) interdit « Exploitable » — trois contrôles verts ne suffisent pas.
VERDICT_EXPLOITABLE = "Exploitable sous hypothèses"
VERDICT_A_COMPLETER = "À compléter"
VERDICT_IMPOSSIBLE = "Impossible pour cause établie"

# contrôles dont l'état « À confirmer » est RÉDHIBITOIRE pour un verdict exploitable (mandat §4).
_A_CONFIRMER_BLOQUANTS = frozenset({
    "PPR zone rouge (interdiction)", "PPR zone bleue (prescription)",
    "Stationnement", "Prospect (hauteur relative)", "ER / EBC / SUP / servitudes",
})


def verdict_global(controles: list[ControleReg], *, statut_base: str, terrain,
                   cause_etablie: str | None = None) -> str:
    """Traduit l'état de l'étude dans les 3 verdicts du mandat. `cause_etablie` (non None) force
    « Impossible pour cause établie » (ex. assiette entièrement inconstructible, dépassement prouvé)."""
    if cause_etablie:
        return VERDICT_IMPOSSIBLE
    if statut_base == "simulation impossible":
        return VERDICT_IMPOSSIBLE
    if any(c.resultat == ECHOUE for c in controles):
        return VERDICT_A_COMPLETER
    if any(c.resultat == A_CONFIRMER and c.nom in _A_CONFIRMER_BLOQUANTS for c in controles):
        return VERDICT_A_COMPLETER
    if not getattr(terrain, "has_voie", True):      # accès à la voie non établi
        return VERDICT_A_COMPLETER
    if statut_base != "exploitable en pré-faisabilité":
        return VERDICT_A_COMPLETER
    return VERDICT_EXPLOITABLE
