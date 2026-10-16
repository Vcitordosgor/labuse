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


def _construire(forme: str, scene: Scene, conv: Conventions, *, niveaux: int, fraction: float) -> int:
    zx0, _zy0, zx1, _zy1 = scene.zone_local.bounds
    L = zx1 - zx0
    x_end = zx0 + fraction * L
    rep = conv.repartition_equilibre
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


def _evaluer(terrain, frame, conv, regles, forme, niveaux, fraction):
    # hauteur : nb de niveaux borné par la hauteur réglementaire (plafond / étage)
    r = regles.hauteur_plafond
    if r.validee and r.valeur is not None and niveaux * conv.hauteur_etage_m > r.valeur + 1e-9:
        return None, Candidat(forme, niveaux, fraction, False, "—", 0, 0.0, 0, None, "dépasse la hauteur")
    scene = scene_depuis(terrain, frame)
    n_mod = _construire(forme, scene, conv, niveaux=niveaux, fraction=fraction)
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
    statut = ctrl_mod.statut_etude(controles, geo_ok, scene=scene, terrain=terrain) if geo_ok else "simulation impossible"
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


def etudier(session=None, *, idus: Optional[list[str]] = None, zone: Optional[str] = None,
            objectif: str = "equilibre", conv_path=None, avec_pente: bool = True) -> Scenario:
    idus = idus or IDUS_ETANG_SALE
    conv = charger_conventions(conv_path)
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

    frame = Frame.depuis(terrain.zone_implantation)
    candidats: list[Candidat] = []
    meilleur = None
    for forme in _FORMES:
        for niveaux in _NIVEAUX:
            for fraction in _FRACTIONS:
                paquet, cand = _evaluer(terrain, frame, conv, regles, forme, niveaux, fraction)
                candidats.append(cand)
                if paquet is None:
                    continue
                scene, cap, _ctrl, _chk, _geo, statut = paquet
                rank = 1 if statut.startswith("exploitable") else 0
                clef = (rank, cap.logements, cap.shab_estimee_m2, -niveaux, fraction)
                if meilleur is None or clef > meilleur[0]:
                    meilleur = (clef, paquet, forme, niveaux)

    if meilleur is None:
        scene = scene_depuis(terrain, frame)
        scene.finaliser_monde()
        cap = cap_mod.calculer(scene, conv, regles, terrain)
        controles = ctrl_mod.controles_reglementaires(scene, terrain, conv, cap, regles)
        checks = ctrl_mod.verifier_geometrie(scene, terrain, conv, cap, regles)
        return Scenario(terrain, conv, regles, scene, cap, controles, checks,
                        "simulation impossible", "—", 0, objectif, candidats, terrain.note_limites)

    _clef, paquet, forme, niveaux = meilleur
    scene, cap, controles, checks, geo_ok, statut = paquet
    return Scenario(terrain, conv, regles, scene, cap, controles, checks, statut, forme, niveaux,
                    objectif, candidats, terrain.note_limites)
