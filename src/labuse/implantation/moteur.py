"""Moteur d'implantation — recherche déterministe du meilleur scénario.

Parcours ORDONNÉ de formes (barre, deux barres, L) × niveaux × longueur de barre. Pour chaque
candidat : on dessine la géométrie, on en TIRE la capacité, on pose le stationnement minimal imposé,
on vérifie la géométrie et les contrôles réglementaires. On garde le meilleur candidat FAISABLE
(tous contrôles durs Réussi + géométrie valide), en PRÉFÉRANT un scénario « exploitable » (un seul
bâtiment, sans PPR bleue sur le bâti) à un « à compléter », puis à capacité maximale. Déterministe.

Aucun réglage par terrain : la zone, les règles et les contraintes viennent des données.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from . import capacite as cap_mod
from . import controles as ctrl_mod
from . import regles as regles_mod
from . import terrain as terrain_mod
from .conventions import Conventions, charger as charger_conventions
from .geometrie import (Frame, Scene, poser_barre, poser_espaces_libres,
                        poser_stationnement, scene_depuis)

IDUS_ETANG_SALE = ["97404000AW0099", "97404000AW0451", "97404000AW0624", "97404000AW0625"]
IDUS_SAINT_ANDRE = ["97409000AX0255", "97409000AX0256"]
IDUS_SAINT_DENIS = ["97411000DL0247", "97411000DL0248"]

_NIVEAUX = [2, 3, 4, 5, 6]
_FRACTIONS = [round(1.0 - 0.05 * k, 2) for k in range(0, 15)]   # 1.00 .. 0.30
_FORMES = ["barre", "deux_barres", "L"]


@dataclass
class Candidat:
    forme: str
    niveaux: int
    fraction: float
    faisable: bool
    statut: str
    logements: int
    shab_m2: float
    places: int
    places_imposees: Optional[int]
    motif: str = ""


@dataclass
class Scenario:
    terrain: terrain_mod.Terrain
    conventions: Conventions
    regles: regles_mod.ReglesZone
    scene: Scene
    capacite: cap_mod.Capacite
    controles: list
    checks_geo: list
    statut: str
    forme: str
    niveaux: int
    objectif: str
    candidats: list[Candidat] = field(default_factory=list)
    note_limites: Optional[str] = None


def _construire(forme: str, scene: Scene, conv: Conventions, *, niveaux: int, fraction: float,
                repartition: Optional[list[str]] = None) -> int:
    zx0, _zy0, zx1, _zy1 = scene.zone_local.bounds
    L = zx1 - zx0
    x_end = zx0 + fraction * L
    rep = repartition or conv.repartition_equilibre
    if forme == "barre":
        return poser_barre(scene, conv, x_start=zx0, x_end=x_end, repartition=rep, niveaux=niveaux, ref="B")
    if forme == "deux_barres":
        gap = conv.retrait_inter_barre_m
        xm = (zx0 + x_end) / 2.0
        n1 = poser_barre(scene, conv, x_start=zx0, x_end=xm - gap / 2.0, repartition=rep, niveaux=niveaux, ref="B1")
        n2 = poser_barre(scene, conv, x_start=xm + gap / 2.0, x_end=x_end, repartition=rep, niveaux=niveaux, ref="B2")
        return n1 + n2
    if forme == "L":
        _, zy0, _, zy1 = scene.zone_local.bounds
        if (zy1 - zy0) < 2 * conv.profondeur_m + conv.retrait_inter_barre_m:
            return 0
        return poser_barre(scene, conv, x_start=zx0, x_end=x_end, repartition=rep, niveaux=niveaux, ref="B")
    return 0


def _evaluer(terrain, frame, conv, regles, forme, niveaux, fraction, repartition=None):
    # hauteur : nb de niveaux borné par la hauteur réglementaire (plafond / étage)
    r = regles.hauteur_plafond
    if r.validee and r.valeur is not None and niveaux * conv.hauteur_etage_m > r.valeur + 1e-9:
        return None, Candidat(forme, niveaux, fraction, False, "—", 0, 0.0, 0, None, "dépasse la hauteur")
    scene = scene_depuis(terrain, frame)
    n_mod = _construire(forme, scene, conv, niveaux=niveaux, fraction=fraction, repartition=repartition)
    if n_mod <= 0:
        motif = "forme L écartée (largeur zone insuffisante)" if forme == "L" else "aucun module implantable"
        return None, Candidat(forme, niveaux, fraction, False, "—", 0, 0.0, 0, None, motif)
    cap0 = cap_mod.calculer(scene, conv, regles, terrain)
    cible = cap0.places_imposees or 0
    poser_stationnement(scene, conv, cible=cible)
    poser_espaces_libres(scene)
    scene.finaliser_monde()
    cap = cap_mod.calculer(scene, conv, regles, terrain)
    checks = ctrl_mod.verifier_geometrie(scene, terrain, conv, cap, regles)
    controles = ctrl_mod.controles_reglementaires(scene, terrain, conv, cap, regles)
    geo_ok = ctrl_mod.geometrie_valide(checks)
    sans_echec = not any(c.resultat == ctrl_mod.ECHOUE for c in controles)
    faisable = geo_ok and sans_echec
    statut = (ctrl_mod.statut_etude(controles, geo_ok, scene=scene, terrain=terrain, regles=regles)
              if geo_ok else "simulation impossible")
    motif = "" if faisable else "; ".join(
        [c.nom for c in checks if not c.ok] + [c.nom for c in controles if c.resultat == ctrl_mod.ECHOUE])
    candidat = Candidat(forme, niveaux, fraction, faisable, statut, cap.logements, cap.shab_estimee_m2,
                        cap.places, cap.places_imposees, motif)
    paquet = (scene, cap, controles, checks, geo_ok, statut) if faisable else None
    return paquet, candidat


def _resoudre_zone(session, idus: list[str]) -> Optional[str]:
    from sqlalchemy import text
    rows = session.execute(text("SELECT zone_lib FROM parcel_zone_plu WHERE idu = ANY(:i)"),
                           {"i": idus}).fetchall()
    zones = [r[0] for r in rows if r[0]]
    if not zones:
        return None
    return max(set(zones), key=zones.count)


def _simplicite_forme(forme: str) -> int:
    """Projet « plus simple » : une barre > un L > deux barres (moins d'ouvrages, plus lisible)."""
    return {"barre": 2, "L": 1, "deux_barres": 0}.get(forme, 0)


def _clef(objectif: str, statut: str, cap: cap_mod.Capacite, niveaux: int, forme: str,
          fraction: float) -> tuple:
    """Clef de tri du meilleur candidat, PILOTÉE par l'objectif. Un scénario « exploitable » passe
    toujours avant un « à compléter » (rank). Départage stable et déterministe ensuite.

    - equilibre     : max logements, puis SHAB, puis moins de niveaux  (défaut historique, inchangé)
    - plus_logements: max logements d'abord, en acceptant de monter (niveaux)
    - plus_surface  : max surface habitable (SHAB) d'abord
    - plus_simple   : le moins de niveaux et la forme la plus simple d'abord
    """
    rank = 1 if statut.startswith("exploitable") else 0
    if objectif == "plus_logements":
        return (rank, cap.logements, niveaux, cap.shab_estimee_m2, fraction)
    if objectif == "plus_surface":
        return (rank, cap.shab_estimee_m2, cap.logements, -niveaux, fraction)
    if objectif == "plus_simple":
        return (rank, -niveaux, _simplicite_forme(forme), cap.logements, cap.shab_estimee_m2, fraction)
    # equilibre (défaut) — clef historique de `etudier`, préservée à l'identique
    return (rank, cap.logements, cap.shab_estimee_m2, -niveaux, fraction)


def _charger(session, idus, zone, conv, avec_pente):
    """(terrain, regles, zone) — résout la zone dominante puis charge règles + terrain. Gère la
    session elle-même si aucune n'est fournie."""
    insee = idus[0][:5]
    fermer = False
    if session is None:
        from labuse.db import session_scope
        _cm = session_scope()
        session = _cm.__enter__()
        fermer = True
    try:
        if zone is None:
            zone = _resoudre_zone(session, idus) or "UA"
        regles = regles_mod.charger(insee, zone)
        terrain = terrain_mod.charger(
            session, idus,
            recul_voie_m=regles.recul_voie.valeur or 0.0,
            recul_separative_m=regles.recul_separatives.valeur or 0.0,
            inset_m=conv.inset_zone_m, avec_pente=avec_pente,
        )
    finally:
        if fermer:
            _cm.__exit__(None, None, None)
    return terrain, regles, zone


def _rechercher(terrain, regles, conv, objectif, *, repartition=None):
    """Parcourt la grille ORDONNÉE forme×niveaux×fraction et renvoie (ranked, candidats) :
    `ranked` = liste des candidats FAISABLES, triée par la clef d'objectif décroissante, chaque
    item = (clef, paquet, forme, niveaux, fraction). `candidats` = la trace complète."""
    frame = Frame.depuis(terrain.zone_implantation)
    candidats: list[Candidat] = []
    faisables: list = []
    for forme in _FORMES:
        for niveaux in _NIVEAUX:
            for fraction in _FRACTIONS:
                paquet, cand = _evaluer(terrain, frame, conv, regles, forme, niveaux, fraction,
                                        repartition=repartition)
                candidats.append(cand)
                if paquet is None:
                    continue
                _scene, cap, _ctrl, _chk, _geo, statut = paquet
                clef = _clef(objectif, statut, cap, niveaux, forme, fraction)
                faisables.append((clef, paquet, forme, niveaux, fraction))
    faisables.sort(key=lambda it: it[0], reverse=True)
    return faisables, candidats


def _scenario_vide(terrain, conv, regles, objectif, candidats) -> Scenario:
    frame = Frame.depuis(terrain.zone_implantation)
    scene = scene_depuis(terrain, frame)
    scene.finaliser_monde()
    cap = cap_mod.calculer(scene, conv, regles, terrain)
    controles = ctrl_mod.controles_reglementaires(scene, terrain, conv, cap, regles)
    checks = ctrl_mod.verifier_geometrie(scene, terrain, conv, cap, regles)
    return Scenario(terrain, conv, regles, scene, cap, controles, checks,
                    "simulation impossible", "—", 0, objectif, candidats, terrain.note_limites)


def _paquet_en_scenario(terrain, conv, regles, objectif, candidats, item) -> Scenario:
    _clef_, paquet, forme, niveaux, _frac = item
    scene, cap, controles, checks, _geo, statut = paquet
    return Scenario(terrain, conv, regles, scene, cap, controles, checks, statut, forme, niveaux,
                    objectif, candidats, terrain.note_limites)


def etudier(session=None, *, idus: Optional[list[str]] = None, zone: Optional[str] = None,
            objectif: str = "equilibre", conv_path=None, conv: Optional[Conventions] = None,
            avec_pente: bool = True) -> Scenario:
    """Le MEILLEUR scénario (API historique, utilisée par les tests `reel`). `conv` permet de
    passer des conventions déjà construites (hypothèses surchargées) ; sinon chargées du YAML."""
    idus = idus or IDUS_ETANG_SALE
    conv = conv or charger_conventions(conv_path)
    terrain, regles, _zone = _charger(session, idus, zone, conv, avec_pente)
    faisables, candidats = _rechercher(terrain, regles, conv, objectif)
    if not faisables:
        return _scenario_vide(terrain, conv, regles, objectif, candidats)
    return _paquet_en_scenario(terrain, conv, regles, objectif, candidats, faisables[0])


def etudier_multi(session=None, *, idus: Optional[list[str]] = None, zone: Optional[str] = None,
                  objectif: str = "equilibre", conv_path=None, conv: Optional[Conventions] = None,
                  avec_pente: bool = True, programme: Optional[dict[str, int]] = None,
                  repartition: Optional[list[str]] = None, max_scenarios: int = 3):
    """Jusqu'à `max_scenarios` scénarios FAISABLES, GÉOMÉTRIQUEMENT DISTINCTS (signature forme+niveaux)
    et classés par l'objectif. Renvoie (scenarios, message, terrain, regles, conv).

    - Aucun faisable            → ([], "simulation impossible : …", terrain, regles, conv).
    - `programme` (demande par type) : ne garde que les candidats qui CONTIENNENT la demande ; si
      aucun ne la contient → ([], "ne tient pas : …", terrain, regles, conv) en nommant ce qui plafonne.
    """
    idus = idus or IDUS_ETANG_SALE
    conv = conv or charger_conventions(conv_path)
    terrain, regles, _zone = _charger(session, idus, zone, conv, avec_pente)
    # zone d'implantation vide ou minuscule (après reculs/PPR) : rien à chercher, pas de crash.
    zi = terrain.zone_implantation
    if zi is None or zi.is_empty or terrain.aire_zone_m2 < 60:
        return [], _message_impossible(terrain, regles, []), terrain, regles, conv
    faisables, candidats = _rechercher(terrain, regles, conv, objectif, repartition=repartition)

    if not faisables:
        return [], _message_impossible(terrain, regles, candidats), terrain, regles, conv

    if programme:
        couvrants = [it for it in faisables if _contient(it[1][1], programme)]
        if not couvrants:
            return [], _message_ne_tient_pas(faisables, programme, regles, conv), terrain, regles, conv
        faisables = couvrants

    # jusqu'à N scénarios, distincts par (forme, niveaux)
    choisis, vus = [], set()
    for it in faisables:
        sig = (it[2], it[3])
        if sig in vus:
            continue
        vus.add(sig)
        choisis.append(_paquet_en_scenario(terrain, conv, regles, objectif, candidats, it))
        if len(choisis) >= max_scenarios:
            break
    return choisis, None, terrain, regles, conv


def _contient(cap: cap_mod.Capacite, programme: dict[str, int]) -> bool:
    """Le candidat contient la demande si, pour chaque type demandé, il dessine ≥ le nombre voulu."""
    return all(cap.par_type.get(t, 0) >= n for t, n in programme.items() if n > 0)


def _message_impossible(terrain, regles, candidats) -> str:
    r = regles.hauteur_plafond
    if not terrain.has_voie:
        return ("simulation impossible : aucune limite classée « voie » sur l'assiette — un accès "
                "véhicule ne peut être tracé.")
    if terrain.aire_zone_m2 < 60:
        return (f"simulation impossible : la zone d'implantation après reculs ne fait que "
                f"{terrain.aire_zone_m2:.0f} m² — trop étroite pour une barre de logements.")
    if r.validee and r.valeur is not None and r.valeur < 6:
        return (f"simulation impossible : la hauteur réglementaire ({r.valeur:.0f} m) n'autorise "
                f"pas un niveau de logements habitable.")
    return ("simulation impossible : aucune implantation ne passe tous les contrôles durs sur cette "
            "assiette (zone trop étroite, reculs, ou stationnement aérien impossible).")


def _message_ne_tient_pas(faisables, programme, regles, conv) -> str:
    """Nomme la règle ou la géométrie qui empêche la demande de tenir : on compare la demande au
    MAXIMUM atteignable par type parmi les candidats faisables."""
    max_par_type: dict[str, int] = {}
    max_niveaux = 0
    for it in faisables:
        cap = it[1][1]
        max_niveaux = max(max_niveaux, it[3])
        for t, n in cap.par_type.items():
            max_par_type[t] = max(max_par_type.get(t, 0), n)
    manquants = [f"{t} : {programme[t]} demandés, {max_par_type.get(t, 0)} au mieux dessinés"
                 for t in programme if programme[t] > max_par_type.get(t, 0)]
    r = regles.hauteur_plafond
    plafond_h = (r.validee and r.valeur is not None
                 and (max_niveaux + 1) * conv.hauteur_etage_m > r.valeur + 1e-9)
    cause = (f"la hauteur réglementaire ({r.valeur:.0f} m, soit R+{max_niveaux - 1} atteint)"
             if plafond_h else "la largeur de la zone d'implantation après reculs")
    return ("ne tient pas : " + " ; ".join(manquants)
            + f". Ce qui plafonne la capacité : {cause}.")
