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

import re
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


def _fr(x: float) -> str:
    """Nombre au format français (virgule), sans zéro inutile : 4.5→« 4,5 », 18.0→« 18 »."""
    return (f"{x:.1f}".rstrip("0").rstrip(".")).replace(".", ",")


def hauteur_projet_m(conv: Conventions, regles: ReglesZone, niveaux: int) -> tuple[float, str, bool]:
    """FAISA-REGLES-1 (E-059) — hauteur du PROJET mesurée SELON LA RÈGLE DU PLU (R.111-26), depuis le
    terrain naturel. Les murs = rez-de-chaussée + étages = `niveaux × hauteur d'étage` (le rez EST un
    niveau, compté). Si la règle qui plafonne se mesure au FAÎTAGE, on AJOUTE la toiture/acrotère
    (`conv.toiture_m`, faîtage = égout + toiture) — sinon un R+n passerait un plafond de faîtage en ne
    comptant que ses murs. Si elle se mesure à l'ÉGOUT, le haut des murs EST l'égout (toiture au-dessus,
    non comptée). Renvoie (hauteur_m, base, estimee) : base ∈ {« égout », « faîtage » } ; `estimee`=True
    quand la toiture a été ajoutée (marge prudente à DIRE sur le chiffre). Jamais une règle inventée :
    la hauteur d'étage et la toiture sont des conventions « Estimé »."""
    h_murs = niveaux * conv.hauteur_etage_m
    if regles.hauteur_egout.validee:
        return round(h_murs, 1), "égout", False
    return round(h_murs + conv.toiture_m, 1), "faîtage", True


@dataclass
class CheckGeo:
    nom: str
    ok: bool
    detail: str = ""
    # ETUDE-STATIONNEMENT-FIX-3 (LOT 1) — un check « consultatif » est AFFICHÉ mais n'invalide PAS la
    # géométrie (n'entre pas dans `geometrie_valide`). Utilisé pour le dégagement sur les ASSEMBLAGES
    # multi-parcelles, où le pavage irrégulier rend la mesure peu fiable (faux pincements).
    advisory: bool = False


# ETUDE-STATIONNEMENT-FIX-3 (LOT 1) — une place est jugée NON DÉGAGÉE si le couloir manquant devant elle
# dépasse ce plancher (≈ allée trop courte de > 0,4 m sur la largeur de la place) ; en deçà, c'est du bruit
# de pavage/jonction. Le contrôle échoue dès qu'une place est non dégagée (BW2635 : 13 places à 2,25 m).
# haie paysagère au pourtour des aires de stationnement : on capte la largeur imposée (« ≥ 1,50 m »).
_HAIE_RE = re.compile(r"haie[^0-9]*?(\d+(?:[.,]\d+)?)\s*m", re.IGNORECASE)
_DEGAGEMENT_PLACE_FLOOR_M2 = 1.0
_DEGAGEMENT_SEUIL_M2 = 1.0   # aire totale non dégagée au-delà de laquelle le plan échoue
_PASSAGE_MIN_M = 2.4         # largeur mini de circulation d'une voiture ; sous ce seuil l'allée s'étrangle
_COMP_SIGNIF_M2 = 8.0        # aire mini d'un morceau d'allée pour qu'un étranglement le séparant compte


def _pincement_allee(allees, places, largeur_requise: float, acces=None) -> float:
    """ETUDE-STATIONNEMENT-FIX-3 (LOT 1) — DÉGAGEMENT mesuré DEVANT CHAQUE PLACE, sur l'allée DÉSÉTRANGLÉE.
    Deux pièges du PLAN réel, traités ensemble :
      1. CLEARANCE devant la place — on sonde un rectangle de la largeur de la place extrudé de `largeur_requise`
         vers CHACUN des deux petits côtés (nez/arrière) et on garde le MEILLEUR (déficit minimal) : l'allée
         dessert la place par un seul côté, l'autre donne sur un mur. Prendre « le plus près de l'allée » se
         trompait de côté sur les parkings denses (faux déficit de 4 m sur une allée de 5 m → écroulait HT0538
         et les assemblages). Prendre le min des deux ignore le côté mur.
      2. PINCEMENT de circulation — avant de sonder, on OUVRE l'allée (érosion/dilatation de `_PASSAGE_MIN_M`/2) :
         tout étranglement plus étroit que le passage d'une voiture (BW2635 : 2,25 m) DISPARAÎT, si bien que les
         places qui n'étaient desservies QU'À TRAVERS ce goulet perdent leur dégagement et sont comptées
         manquantes. Une allée large (≥ `_PASSAGE_MIN_M`) survit à l'ouverture → aucun faux positif.
    On ne compte que les places VRAIMENT déficientes (manque > `_DEGAGEMENT_PLACE_FLOOR_M2`). Renvoie l'aire (m²)."""
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    if not allees or not places:
        return 0.0
    libre = unary_union([g if g.is_valid else g.buffer(0) for g in (list(allees) + list(acces or []))])
    if libre.is_empty:
        return 0.0
    # (2) PINCEMENT DE CIRCULATION : une place n'est desservie que si une VOITURE peut l'atteindre depuis
    # l'accès sans franchir de goulet plus étroit que `_PASSAGE_MIN_M`. On ÉRODE l'allée de la demi-largeur de
    # passage : un vrai étranglement (BW2635 : 2,25 m) SÉPARE le noyau en plusieurs morceaux ; seul celui qui
    # touche l'accès reste atteignable (une ouverture morphologique ne suffit pas — la dilatation rebouche le
    # goulet). Les places desservies uniquement par un morceau coupé de l'accès perdront leur dégagement.
    r_pass = _PASSAGE_MIN_M / 2.0
    noyau = libre.buffer(-r_pass).buffer(0)
    if noyau.is_empty:
        return float(sum((p if p.is_valid else p.buffer(0)).area for p in places))
    comps = list(noyau.geoms) if noyau.geom_type == "MultiPolygon" else [noyau]
    # on ne déclare un étranglement que si l'érosion coupe DEUX morceaux SIGNIFICATIFS (chacun capable
    # d'accueillir le dégagement d'une place) : sinon ce sont des échardes de bord d'une petite allée — qui
    # faisaient écrouler HT0538 à tort. Un vrai goulet (BW2635) sépare deux vraies zones de stationnement.
    signif = [g for g in comps if g.area >= _COMP_SIGNIF_M2]
    reach = None
    if len(signif) > 1:
        ancre = unary_union([g if g.is_valid else g.buffer(0) for g in (acces or [])]) if acces else None
        if ancre is None or ancre.is_empty:
            ancre = max(signif, key=lambda g: g.area)        # pas d'accès connu : le plus grand morceau
        reach = min(signif, key=lambda g: g.distance(ancre))  # le noyau qui touche l'accès
    from shapely.geometry import Point
    W = max(float(largeur_requise) - 0.6, 0.1)   # 0,6 m de tolérance de pavage (allée clippée ~4,9 m)
    manque = 0.0
    for p in places:
        pg = p if p.is_valid else p.buffer(0)
        c = pg.centroid
        # PLACE DE L'AUTRE CÔTÉ DU GOULET : si le noyau atteignable depuis l'accès existe et que CETTE place
        # est plus proche d'un AUTRE morceau de noyau, aucune voiture ne peut l'atteindre → place perdue. On ne
        # redilate pas `reach` (cela rebouche le goulet) : on strande par APPARTENANCE au morceau le plus proche.
        if reach is not None and signif:
            proche = min(signif, key=lambda g: g.distance(c))
            if proche is not reach and reach.distance(c) > r_pass + 0.5:
                manque += pg.area
                continue
        coords = list(pg.exterior.coords)[:-1]
        # on ne sonde que par le NEZ de la place : l'un des deux PETITS côtés (la place est 2,5 × 5 m — le nez
        # fait la largeur, 2,5 m ; les grands côtés, 5 m, sont les flancs). Sonder un flanc extruderait vers un
        # mur et créerait un faux déficit (ce qui cassait les assemblages malgré une allée large de 5 m).
        edges = []
        for i in range(len(coords)):
            a, b = coords[i], coords[(i + 1) % len(coords)]
            L = ((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5
            edges.append((L, a, b, ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)))
        if not edges:
            continue
        Lmin = min(e[0] for e in edges)
        petits = [e for e in edges if e[0] <= Lmin * 1.3]          # les deux petits côtés (nez ET arrière)
        # On SONDE les DEUX petits côtés et on garde le MEILLEUR (déficit minimal) : l'allée dessert la place
        # par UN seul côté ; l'autre donne sur le mur/la place voisine. Prendre le plus près de l'allée se
        # trompait de côté quand une allée mince longeait l'arrière (faux déficit de 4 m sur une allée de 5 m,
        # qui écroulait les parkings denses). Le côté d'accès réel = celui où le dégagement manque le MOINS.
        deficits = []
        for _L, a, b, mid in petits:
            nx, ny = mid[0] - c.x, mid[1] - c.y
            ln = (nx * nx + ny * ny) ** 0.5 or 1.0
            nx, ny = nx / ln, ny / ln
            sonde = Polygon([a, b, (b[0] + W * nx, b[1] + W * ny), (a[0] + W * nx, a[1] + W * ny)])
            if not sonde.is_valid or sonde.area < 0.5:
                continue
            deficits.append(max(0.0, sonde.area - sonde.intersection(libre).area))
        if not deficits:
            continue
        deficit = min(deficits)                      # le côté d'accès = le mieux dégagé des deux
        if deficit > _DEGAGEMENT_PLACE_FLOOR_M2:     # place VRAIMENT non dégagée des DEUX côtés
            manque += deficit
    return float(manque)


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

    # ETUDE-STATIONNEMENT-FIX-2 (LOT 3) — largeur du DÉGAGEMENT devant les places mesurée LOCALEMENT, pas sur
    # la boîte englobante : une allée clippée à un bord oblique peut pincer à 2,25 m au droit des places tout en
    # ayant une boîte de 5 m (cas BW2635 : 13 places à 2,25 m « validées » à tort). On mesure le pincement réel.
    # ETUDE-STATIONNEMENT-FIX-3 (LOT 1) — les DEUX géométries DANS LE MÊME REPÈRE : `allees` et `places` sont
    # ici en coordonnées PROJETÉES (geom_world) ; l'ancien code passait l'allée en geom_local → intersection
    # avec les places (geom_world) vide → pincement toujours 0 en production (le test unitaire, lui, était dans
    # un seul repère et passait). Sur BW2635 : 25,25 m² de pincement, 2,25 m au droit de 13 places.
    pince = _pincement_allee(allees, places, conv.allee_largeur_m, acces)
    larg_ok = pince < _DEGAGEMENT_SEUIL_M2
    # ETUDE-STATIONNEMENT-FIX-3 (reliquat) — contrôle DUR, y compris sur un ASSEMBLAGE : la mesure par sonde du
    # meilleur des deux côtés (nez/arrière) + désétranglement de la circulation ne crée plus de faux pincements
    # sur le pavage dense (L'Étang-Salé 27 places OK), donc le dégagement d'un assemblage est aussi contraignant
    # que sur une parcelle seule (plus de « consultatif »). Il se calcule sur la géométrie FUSIONNÉE des parcelles.
    checks.append(CheckGeo(f"dégagement d'allée ≥ {conv.allee_largeur_m} m au droit des places (mesuré localement)",
                           larg_ok, "" if larg_ok else f"{pince:.1f} m² de dégagement sous la largeur requise"))

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
        # FAISA-REGLES-1 (E-059) — hauteur RÉELLE du projet selon la règle (égout/faîtage, toiture comptée).
        h, base, _est = hauteur_projet_m(conv, regles, cap.niveaux)
        checks.append(CheckGeo(f"hauteur projet ({base}) ≤ hauteur réglementaire",
                               h <= r.valeur + 1e-9, f"{_fr(h)} m ≤ {_fr(r.valeur)} m"))
    return checks


def geometrie_valide(checks: list[CheckGeo]) -> bool:
    # les checks CONSULTATIFS (ex. dégagement sur assemblage) sont affichés mais n'invalident pas le candidat.
    return all(c.ok for c in checks if not getattr(c, "advisory", False))


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


def _ppr_bleue_touche_projet(scene: Scene, terrain) -> list[str]:
    """ETUDE-FIABLE-1 (LOT C5) — quelle(s) PARTIE(S) du projet touche(nt) le PPR bleu : bâtiment, accès
    OU sous-sol (plus seulement le bâti). La géométrie ne change pas ; on le SIGNALE dans les points à
    instruire (« Prescriptions PPR à vérifier »). Renvoie la liste des parties concernées (vide = aucune)."""
    if terrain.ppr_bleue is None or terrain.ppr_bleue.is_empty:
        return []
    parties: list[str] = []
    for kind, libelle in (("batiment_emprise", "bâtiment"), ("acces", "accès"),
                          ("sous_sol_emprise", "sous-sol")):
        geoms = [o.geom_world for o in scene.of(kind) if o.geom_world is not None]
        if geoms and unary_union(geoms).intersection(terrain.ppr_bleue).area > _TOL_AIRE:
            parties.append(libelle)
    return parties


def controles_reglementaires(scene: Scene, terrain, conv: Conventions, cap: Capacite,
                             regles: ReglesZone) -> list[ControleReg]:
    out: list[ControleReg] = []
    # FAISA-REGLES-1 (E-058) — MÊME BASE que le dessin pour l'emprise au sol et la pleine terre : l'emprise
    # et la pleine terre sont MESURÉES sur la géométrie (EPSG:2975) ; le plafond CES/perméabilité est donc
    # calculé sur la SURFACE DESSINÉE de la portion constructible (`aire_dessin_m2`), pas sur la contenance
    # cadastrale (qui diffère du dessin de ~1-3 %). Numérateur et dénominateur dans le même repère.
    # (Le vrai Terrain porte toujours `aire_dessin_m2` ; repli défensif sur la contenance pour une
    # scène synthétique de test qui ne l'expose pas.)
    _aire_dessin = getattr(terrain, "aire_dessin_m2", None)
    contenance = _aire_dessin if _aire_dessin is not None else terrain.contenance_totale_m2

    r = regles.emprise_ces
    if r.validee and r.valeur is not None:
        plafond = contenance * r.valeur / 100.0
        ok = cap.emprise_sol_m2 <= plafond + 1e-6
        out.append(ControleReg("Emprise au sol", f"≤ {plafond:.0f} m² ({r.valeur:.0f} % de la surface du terrain)",
                               f"{cap.emprise_sol_m2:.0f} m²", REUSSI if ok else ECHOUE,
                               r.citation_complete, f"écart {plafond - cap.emprise_sol_m2:+.0f} m²"))
    elif getattr(r, "absent", False):
        # ETUDE-STATIONNEMENT-FIX-1 (LOT 5) — le PLU NE RÉGLEMENTE PAS l'emprise (silence prouvé, cité) :
        # « Non réglementé » (sans objet), pas « Non effectué » (qui laisserait croire à une lacune LABUSE).
        out.append(ControleReg("Emprise au sol", "non réglementé (silence prouvé)", f"{cap.emprise_sol_m2:.0f} m²",
                               NON_APPLICABLE, r.citation_complete,
                               detail="le règlement ne fixe pas d'emprise au sol dans cette zone"))
    else:
        out.append(ControleReg("Emprise au sol", "règle non validée", f"{cap.emprise_sol_m2:.0f} m²", NON_EFFECTUE))

    r = regles.hauteur_plafond
    if r.validee and r.valeur is not None:
        # FAISA-REGLES-1 (E-059) — hauteur du PROJET mesurée selon la règle (égout/faîtage), rez + toiture
        # comptés ; marge prudente DITE (« hauteur estimée, toiture comprise ») quand la toiture est ajoutée.
        h, base, estimee = hauteur_projet_m(conv, regles, cap.niveaux)
        ok = h <= r.valeur + 1e-9
        base_lbl = "à l'égout" if base == "égout" else "au faîtage (pas d'égout chiffré)"
        mesure = (f"R+{cap.niveaux - 1} ≈ {_fr(h)} m {base}"
                  + (" (hauteur estimée, toiture comprise)" if estimee else ""))
        out.append(ControleReg("Hauteur", f"≤ {_fr(r.valeur)} m {base_lbl}",
                               mesure, REUSSI if ok else ECHOUE, r.citation_complete))
    else:
        out.append(ControleReg("Hauteur", "règle non validée", f"R+{cap.niveaux - 1}", NON_EFFECTUE))

    # ETUDE-V6-2 (Lot 3, correction) — HAUTEUR SUR TERRAIN EN PENTE : la hauteur à l'égout se mesure depuis
    # le terrain NATUREL. Sur une pente, la façade AVAL est plus haute que niveaux × étage du dénivelé sous
    # le bâtiment. On VÉRIFIE (dénivelé LiDAR) si un volume à toiture plate dépasserait le plafond à l'égout
    # côté aval : si oui, le bâtiment doit être EN GRADINS (partie aval possiblement R+(N-1), comme
    # l'architecte). LABUSE suppose des gradins (R+N conservé) et le SIGNALE — à confirmer par l'architecte.
    # ETUDE-V6-2 (Lot 3, correction §1) — GRADINS MESURÉS SUR LE LiDAR (plus de « à confirmer »). La hauteur
    # à l'égout se mesure depuis le TN sous chaque partie du bâtiment ; on MESURE le dénivelé sous le bâti
    # (pente LiDAR × plus grande dimension du bâti, borné par le dénivelé de la parcelle), puis on conclut :
    #   · toiture plate tenable si niveaux × étage + relief ≤ plafond égout ;
    #   · sinon bâtiment EN GRADINS (un décrochement par étage) qui tient R+N — nombre de gradins = relief/étage.
    pente = getattr(terrain, "pente", None)
    he = regles.hauteur_egout
    if isinstance(pente, dict) and pente.get("disponible") and he.validee and he.valeur is not None:
        import math
        denivele_parcelle = float(pente.get("denivele_m") or 0.0)
        pm = float(pente.get("pente_moyenne_pct") or 0.0) / 100.0
        batis_w = [o.geom_world for o in scene.of("batiment_emprise") if o.geom_world is not None]
        if batis_w:
            mnx, mny, mxx, mxy = unary_union(batis_w).bounds
            L_bati = max(mxx - mnx, mxy - mny)
        else:
            L_bati = math.sqrt(max(0.0, cap.emprise_sol_m2))
        relief_bati = round(min(denivele_parcelle, pm * L_bati), 1)
        etage = conv.hauteur_etage_m
        egout_plat = round(cap.niveaux * etage + relief_bati, 1)   # façade aval d'un volume à toiture plate
        src = pente.get("source") or "LiDAR"
        if relief_bati < 0.5:
            out.append(ControleReg("Hauteur sur terrain en pente", "terrain quasi plat",
                                   f"relief sous bâti {relief_bati:.1f} m ({src})", REUSSI, he.citation))
        elif egout_plat <= he.valeur + 1e-9:
            out.append(ControleReg(
                "Hauteur sur terrain en pente", f"≤ {he.valeur:.0f} m à l'égout (toiture plate tenable)",
                f"R+{cap.niveaux - 1}, relief sous bâti {relief_bati:.1f} m, {src} → {egout_plat:.1f} m aval",
                REUSSI, he.citation))
        else:
            # ETUDE-FIABLE-1 (LOT C4) — un volume DROIT à toiture plate dépasserait le plafond à l'égout côté
            # AVAL ; LABUSE SUPPOSE des gradins (R+N conservé) mais c'est une HYPOTHÈSE d'architecte, pas un
            # fait vérifié : le statut n'est donc plus « Réussi » mais « Implantation étagée à vérifier »
            # (À confirmer). Le prospect, lui, reste « À confirmer » (ci-dessous).
            n_gradins = max(2, math.ceil(relief_bati / etage) + 1)
            out.append(ControleReg(
                "Implantation étagée à vérifier", f"≤ {he.valeur:.0f} m à l'égout — supposerait un bâtiment EN GRADINS",
                f"R+{cap.niveaux - 1} en {n_gradins} gradins — relief {relief_bati:.1f} m mesuré, {src}",
                A_CONFIRMER, he.citation,
                detail=(f"relief sous le bâti {relief_bati:.1f} m (pente moy. {pente.get('pente_moyenne_pct')} %) : "
                        f"un volume droit à toiture plate dépasserait de {egout_plat - he.valeur:.1f} m à l'égout aval → "
                        f"il faudrait un bâtiment en {n_gradins} gradins (un décrochement d'étage chacun) pour tenir "
                        f"{he.valeur:.0f} m partout. LABUSE le suppose (R+{cap.niveaux - 1} conservé) ; à CONFIRMER par "
                        f"l'architecte (partie aval possiblement R+{max(0, cap.niveaux - 2)}).")))

    # ETUDE-STATIONNEMENT-FIX-1 — hauteur PRÈS DES LIMITES (ex. Ua10.3, bande de 3,60 m) : la règle EXISTE
    # mais le moteur ne sait pas la chiffrer → « Non vérifié », jamais traitée comme absente.
    bande = getattr(regles, "hauteur_bande_limite", None)
    if bande:
        _art = bande.get("article")
        _cit = (f"PLU art. {_art}" if _art else "") + (f" · p. {bande['page_pdf']}" if bande.get("page_pdf") else "")
        _cit = (_cit + (f" — « {bande['citation']} »" if bande.get("citation") else "")) or None
        out.append(ControleReg("Hauteur près des limites", "règle existante, non chiffrable par le moteur",
                               "à vérifier", A_CONFIRMER, _cit,
                               detail="une hauteur réduite s'applique dans une bande le long des limites "
                                      "séparatives (règle de gabarit) — non modélisée ici, à vérifier au projet"))

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
        # ETUDE-STATIONNEMENT-FIX-3 (reliquat) — « premier rideau » (implantation à l'alignement, ou sur les
        # limites séparatives : Saint-Pierre Ud3.1/Ud3.2) est une règle de POSITION que ce moteur ne modélise
        # pas : il applique un recul uniforme. « Bâti dans la zone » ne prouve donc PAS le respect du premier
        # rideau → « Non vérifié » avec la règle citée, jamais « Reculs — Réussi ».
        _rideau = "premier rideau" in cit.lower() or "limites séparatives et au maximum" in cit.lower()
        if _rideau:
            out.append(ControleReg("Reculs", f"voie {rv.valeur:.0f} m · séparatives {rs.valeur:.0f} m",
                                   "règle de « premier rideau » (alignement / sur limites) non modélisée",
                                   A_CONFIRMER if dans_zone else ECHOUE, cit,
                                   detail="implantation en premier rideau (à l'alignement ou sur limites "
                                          "séparatives) à vérifier au projet — non modélisée par ce moteur"))
        else:
            out.append(ControleReg("Reculs", f"voie {rv.valeur:.0f} m · séparatives {rs.valeur:.0f} m",
                                   "bâti dans la zone d'implantation", REUSSI if dans_zone else ECHOUE, cit))
    else:
        out.append(ControleReg("Reculs", "règle non validée", "bâti dans la zone", NON_EFFECTUE))

    # RECETTE-4 — contrôle ACCÈS, AJOUTÉ SEULEMENT quand aucune voie n'est classée : l'étude continue sous
    # l'hypothèse d'un accès (arête la plus longue), signalée « À confirmer » (réhibitoire pour un verdict
    # « Exploitable » — cf. _A_CONFIRMER_BLOQUANTS). Voie classée = rien à signaler (comportement d'origine).
    if getattr(terrain, "voie_hypothese", False):
        out.append(ControleReg("Accès (voie)", "aucune limite classée « voie »",
                               "accès supposé sur l'arête la plus longue", A_CONFIRMER,
                               detail="classement de la limite « voie » non établi — accès à confirmer"))

    r = regles.pleine_terre
    if r.validee and r.valeur is not None:
        requis = contenance * r.valeur / 100.0
        ok = cap.pleine_terre_m2 >= requis - 1e-6
        out.append(ControleReg("Perméabilité (pleine terre)", f"≥ {requis:.0f} m² ({r.valeur:.0f} % de la surface du terrain)",
                               f"{cap.pleine_terre_m2:.0f} m²", REUSSI if ok else ECHOUE,
                               r.citation_complete, f"écart {cap.pleine_terre_m2 - requis:+.0f} m²"))
    else:
        out.append(ControleReg("Perméabilité (pleine terre)", "règle non validée",
                               f"{cap.pleine_terre_m2:.0f} m²", NON_EFFECTUE))

    # ETUDE-STATIONNEMENT-FIX-3 (reliquat) — COEFFICIENT DE BIOTOPE (CBS), exigence de sol DISTINCTE de la
    # pleine terre : c'est une somme PONDÉRÉE de surfaces éco-aménageables (toiture végétalisée, dalle
    # plantée, pleine terre…) que ce moteur ne sait pas calculer → affichée SÉPARÉMENT « à vérifier », jamais
    # fondue dans la perméabilité (Saint-Pierre Ud5.1 : CBS 30 % AVEC au moins 20 % de pleine terre).
    rb = getattr(regles, "biotope", None)
    if rb is not None and rb.validee and rb.valeur is not None:
        _nom = (rb.nom or "coefficient de biotope (CBS)").strip()
        out.append(ControleReg(_nom[:1].upper() + _nom[1:], f"≥ {rb.valeur:.0f} % de la surface du terrain",
                               "non chiffré par le moteur (somme pondérée / surfaces éco-aménageables)", A_CONFIRMER,
                               rb.citation_complete,
                               detail="exigence de sol distincte de la pleine terre plantée — à vérifier au projet"))

    # ETUDE-V6-2 (Lot 3, correction §2) — ESPACES VERTS (part végétalisée du terrain, hors stationnement).
    # EV = espace libre végétalisable = pleine terre + surface sur dalle plantée (en sous-sol).
    ev = getattr(regles, "espaces_verts", None)
    if ev is not None and ev.validee and ev.pct is not None:
        requis = contenance * ev.pct / 100.0
        ev_m2 = (cap.pleine_terre_m2 or 0.0) + (getattr(cap, "sur_dalle_m2", 0.0) or 0.0)
        hs = " · hors stationnement" if ev.hors_stationnement else ""
        ok = ev_m2 >= requis - 1e-6
        out.append(ControleReg("Espaces verts", f"≥ {requis:.0f} m² ({ev.pct:.0f} %{hs})",
                               f"{ev_m2:.0f} m²", REUSSI if ok else ECHOUE, ev.citation_complete,
                               f"écart {ev_m2 - requis:+.0f} m²"))

    # ETUDE-V6-2 (Lot 3, correction §2) — MARGE PLANTÉE périphérique : une bande de largeur_m sur une
    # fraction du linéaire. Elle s'INSCRIT dans les reculs (voie/séparatives) : vérifiée si le plus
    # petit recul validé ≥ la largeur de la bande (sinon À confirmer).
    mp = getattr(regles, "marge_plantee", None)
    if mp is not None and mp.validee and mp.largeur_m is not None:
        reculs = [x.valeur for x in (regles.recul_voie, regles.recul_separatives)
                  if x.validee and x.valeur is not None]
        recul_min = min(reculs) if reculs else 0.0
        hm = " hors mitoyenneté" if mp.hors_mitoyennete else ""
        ok = recul_min >= mp.largeur_m - 1e-6
        lin = f" sur {mp.pct_lineaire:.0f} % du linéaire" if mp.pct_lineaire is not None else ""
        out.append(ControleReg("Marge plantée", f"bande {mp.largeur_m:.1f} m{lin}{hm}",
                               f"reculs ≥ {recul_min:.0f} m" if ok else f"recul {recul_min:.0f} m < {mp.largeur_m:.1f} m",
                               REUSSI if ok else A_CONFIRMER, mp.citation_complete,
                               detail=("la bande plantée s'inscrit dans les reculs (périphérie végétalisée)"
                                       if ok else "recul insuffisant pour loger la bande plantée — à confirmer")))

    b = regles.stationnement
    sous_sol = getattr(cap, "stationnement_mode", "aerien") == "sous_sol"
    place_mot = "places au sous-sol" if sous_sol else "places dessinées"
    # NB — le MOTEUR utilise ce contrôle pour la faisabilité (une place manquante plafonne la capacité) :
    # il GARDE donc son verdict géométrique REUSSI/ECHOUE (les places dessinées tiennent-elles ?). La
    # réserve CAPACITE-1 (D1) « barème par logement → règle collective non vérifiée » est portée à
    # l'AFFICHAGE par l'Étude (etude_faisabilite), SANS toucher la capacité du moteur (sinon on gonflerait
    # la capacité en retirant la contrainte — l'inverse de la prudence voulue).
    if b.validee and cap.places_imposees is not None:
        ok = cap.places >= cap.places_imposees
        # ETUDE-STATIONNEMENT-FIX-1 (LOT 1) — l'exigence expose la formule RETENUE (la plus exigeante) et la
        # part visiteur ; le détail porte la lecture écartée, pour que le document dise POURQUOI ce nombre.
        vis = getattr(cap, "places_imposees_visiteurs", 0) or 0
        res = getattr(cap, "places_imposees_residents", None)
        attendu = f"≥ {cap.places_imposees} places (barème validé)"
        if vis:
            attendu += f" — dont {res} résident + {vis} visiteur"
        det = [f"écart {cap.places - cap.places_imposees:+d}"]
        if getattr(cap, "stationnement_formule", None):
            det.append("formule retenue : " + cap.stationnement_formule)
        for f in getattr(cap, "stationnement_formules_ecartees", ()) or ():
            det.append("lecture écartée : " + f)
        out.append(ControleReg("Stationnement", attendu,
                               f"{cap.places} {place_mot}", REUSSI if ok else ECHOUE,
                               b.citation_complete, " · ".join(det)))
    elif b.validee and cap.places_imposees is None:
        # ETUDE-STATIONNEMENT-FIX-1 (LOT 1) — barème VALIDÉ mais ne couvrant pas le programme dessiné (forme
        # non modélisable ou typologie non prévue) : « Non vérifié », jamais « Réussi ». On n'invente rien.
        out.append(ControleReg("Stationnement", "règle ne couvrant pas le programme dessiné",
                               f"{cap.places} {place_mot}", A_CONFIRMER, b.citation_complete,
                               detail="le barème validé ne s'applique pas au programme tel que dessiné — "
                                      "nombre de places non vérifié ici (à confirmer au règlement)"))
    else:
        # ETUDE-V6 — barème manquant = ambiguïté (exigence non chiffrée) → À confirmer, pas « Non effectué ».
        # CAPACITE-1 (C4) — la règle EXISTE au PLU, elle n'est pas ingérée par LABUSE (jamais « non réglementé »).
        out.append(ControleReg("Stationnement", "règle existante, non ingérée par LABUSE", f"{cap.places} {place_mot}",
                               A_CONFIRMER, detail="règle de stationnement existante au PLU mais non ingérée par LABUSE — à vérifier au règlement"))

    # ETUDE-STATIONNEMENT-FIX-2 — places PUBLIQUES (hors parcelle) : exigées, à réaliser sur le domaine
    # public, PAS dessinées sur le terrain → affichées À PART, jamais ajoutées aux places à dessiner.
    _pub = getattr(cap, "places_publiques_imposees", 0) or 0
    if _pub:
        out.append(ControleReg("Stationnement public (hors parcelle)", f"{_pub} places sur le domaine public",
                               "non dessinées sur le terrain", A_CONFIRMER, b.citation_complete if b.validee else None,
                               detail="places publiques exigées par le règlement, à réaliser hors de la parcelle — à confirmer"))

    # ETUDE-STATIONNEMENT-FIX-1 (LOT 1) — conditions NON MODÉLISABLES du barème (ex. « dont au moins 0,5 place
    # à l'extérieur des espaces privatisés ») : affichées « à vérifier », JAMAIS comptées comme satisfaites.
    # ETUDE-STATIONNEMENT-FIX-3 (reliquat) — la HAIE paysagère au pourtour des aires de stationnement EST
    # mesurable : on confronte la distance aire de stationnement ↔ bâti à la largeur imposée (ex. Saint-Pierre
    # Ud6 : 1,50 m). En deçà, c'est un ÉCHEC MESURÉ du plan (le pourtour ne tient pas la haie), pas un « à
    # vérifier » (HT0538 : 1,39 m < 1,50 m). La « voie piétonne » exigée EN PLUS ne ferait que durcir le seuil.
    _places_g = [o.geom_world for o in scene.of("place")]
    _allees_g = [o.geom_world for o in scene.of("allee")]
    _parking = unary_union(_places_g + _allees_g) if (_places_g or _allees_g) else None
    _bati_g = unary_union(batis) if batis else None
    for cond in (getattr(cap, "stationnement_conditions", ()) or ()):
        _m = _HAIE_RE.search(cond)
        if (_m and _parking is not None and not _parking.is_empty
                and _bati_g is not None and not _bati_g.is_empty):
            req = float(_m.group(1).replace(",", "."))
            d = _parking.distance(_bati_g)
            ok = d >= req - 0.01
            out.append(ControleReg(
                "Stationnement — haie paysagère", f"≥ {_fr(req)} m entre l'aire de stationnement et le bâti",
                f"{_fr(round(d, 2))} m mesuré", REUSSI if ok else ECHOUE,
                b.citation_complete if b.validee else None,
                detail="haie paysagère (+ voie piétonne) au pourtour des aires de stationnement — mesuré au plan"))
            continue
        out.append(ControleReg("Stationnement — condition à vérifier", cond, "non modélisé",
                               A_CONFIRMER, b.citation_complete if b.validee else None,
                               detail="condition du barème non vérifiable par ce moteur — à confirmer au projet"))

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

    # ETUDE-STATIONNEMENT-FIX-2 (reliquat #5) — stationnement VÉLO CHIFFRÉ quand le PLU le fixe (le moteur ne
    # le dessine pas → « à prévoir : X », jamais « non modélisé »). Sinon « Non vérifié » (pas « sans règle »).
    _par_pieces = [conv.modules[o.type_logement].pieces for o in scene.of("module")
                   if o.type_logement in conv.modules]
    _velo = (regles.stationnement.velo_requis(cap.logements, cap.sdp_m2, _par_pieces)
             if regles.stationnement.validee else None)
    if _velo is not None:
        _cit = (regles.stationnement.velo or {}).get("citation")
        out.append(ControleReg("Stationnement vélo", f"{_velo[1]} (servi au PLU)", f"à prévoir : {_velo[0]}",
                               A_CONFIRMER, _cit,
                               detail="exigence vélo chiffrée ; emplacement à confirmer (non dessiné par le moteur)"))
    else:
        out.append(ControleReg("Stationnement vélo", "norme non servie pour cette zone", "—", A_CONFIRMER,
                               detail="à vérifier au règlement (local vélos) — non modélisé"))
    out.append(ControleReg("Local déchets", "non modélisé", "—", NON_EFFECTUE))

    # PPR rouge (interdiction) : déduite de l'implantation, mais l'interdiction reste à CONFIRMER au
    # règlement (on la retire par prudence, ce n'est pas une preuve de constructibilité du reste).
    if terrain.contraintes.get("ppr_rouge"):
        out.append(ControleReg("PPR zone rouge (interdiction)", "retirée de la zone (prudence)",
                               f"{terrain.ppr_rouge_m2:.0f} m²", A_CONFIRMER,
                               detail="partie interdite retirée de l'implantation ; interdiction à confirmer au règlement PPR"))
    else:
        out.append(ControleReg("PPR zone rouge (interdiction)", "absente du terrain", "—", NON_APPLICABLE))

    # PPR bleue (prescription) : signalée, non interprétée → à confirmer (prescriptions à lire).
    # ETUDE-FIABLE-1 (LOT C5) — si le bâtiment, l'accès OU le sous-sol tombe en PPR bleu : mention
    # « Prescriptions PPR à vérifier » dans les points à instruire (la géométrie ne change pas).
    if terrain.contraintes.get("ppr_bleue"):
        parties = _ppr_bleue_touche_projet(scene, terrain)
        if parties:
            out.append(ControleReg("Prescriptions PPR à vérifier",
                                   "projet en zone bleue (prescription)",
                                   "touche : " + ", ".join(parties),
                                   A_CONFIRMER, detail=("le " + ", le ".join(parties) + " tombe(nt) en PPR zone bleue : "
                                                        "prescriptions à lire (surélévation, vide sanitaire, interdiction de "
                                                        "sous-sol…) — tant qu'elles ne le sont pas, l'étude n'est pas exploitable")))
        else:
            out.append(ControleReg("PPR zone bleue (prescription)", "signalée, non interprétée",
                                   "ne touche pas le projet",
                                   A_CONFIRMER, detail="signalée, prescriptions à lire"))
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
    if _ppr_bleue_touche_projet(scene, terrain):   # ETUDE-FIABLE-1 (C5) — bâti/accès/sous-sol en PPR bleu
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
    # ETUDE-FIABLE-1 (LOT C5) — PPR bleu touchant bâtiment/accès/sous-sol : bloque « Exploitable » (comme
    # l'ancien contrôle « PPR zone bleue » qui, lorsqu'il touchait le bâti, rendait l'étude non exploitable).
    "Prescriptions PPR à vérifier",
    "Stationnement", "Stationnement — condition à vérifier",
    "Hauteur près des limites",
    "Prospect (hauteur relative)", "ER / EBC / SUP / servitudes",
    "Accès (voie)",   # RECETTE-4 — accès hypothétique (aucune voie classée) → verdict non « Exploitable »
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


def afficher_stationnement_a_confirmer(controles, regles) -> None:
    """CAPACITE-1 (D1) — AFFICHAGE : un barème « par logement » (taux unique, sans distinction de
    destination) ne garantit PAS la règle COLLECTIVE (au-delà de 5 logements, elle diffère — ex. art.
    Ud12.2). Le contrôle de stationnement s'affiche « À confirmer », jamais « Réussi » avec une règle
    qui ne s'applique pas (faute AD0887 : 8 places « Réussi » au taux individuel pour un collectif).
    N'altère PAS la capacité : le moteur a déjà décidé la faisabilité (verdict géométrique REUSSI/ÉCHOUÉ)
    AVANT ce point ; on ne mute que la LIGNE affichée du scénario packagé (compte + table la lisent)."""
    b = getattr(regles, "stationnement", None)
    if b is None or not getattr(b, "validee", False) or getattr(b, "mode", None) != "par_logement":
        return
    for c in (controles or []):
        if c.nom == "Stationnement" and c.resultat in (REUSSI, ECHOUE):
            c.resultat = A_CONFIRMER
            c.regle = "barème « par logement » — règle collective non vérifiée"
            c.detail = ("barème exprimé par logement, sans distinguer la destination ; la règle de "
                        "stationnement collectif (seuil au-delà de 5 logements) peut imposer davantage "
                        "— à vérifier au règlement")
