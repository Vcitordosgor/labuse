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
                        poser_sous_sol, poser_stationnement, scene_depuis)

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
    # ETUDE-V6-2 (Lot 2) — faisable SI l'on IGNORE le contrôle de stationnement (tous les autres
    # contrôles durs + géométrie passent). Sert à prouver, SANS 2ᵉ recherche, l'impact du stationnement
    # sur la capacité (contrefactuel « sans places »).
    faisable_sans_stationnement: bool = False


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


def _evaluer(terrain, frame, conv, regles, forme, niveaux, fraction, repartition=None,
             stationnement_mode="aerien", niveaux_sous_sol=1):
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
    # ETUDE-V6-2 (Lot 3) — sous-sol : places au niveau −1 (le sol reste libre → plus de logements) ;
    # aérien par défaut (places + allée + accès au sol).
    if stationnement_mode == "sous_sol":
        poser_sous_sol(scene, conv, cible=cible, niveaux=niveaux_sous_sol)
    else:
        poser_stationnement(scene, conv, cible=cible)
    poser_espaces_libres(scene)
    scene.finaliser_monde()
    cap = cap_mod.calculer(scene, conv, regles, terrain)
    checks = ctrl_mod.verifier_geometrie(scene, terrain, conv, cap, regles)
    controles = ctrl_mod.controles_reglementaires(scene, terrain, conv, cap, regles)
    geo_ok = ctrl_mod.geometrie_valide(checks)
    sans_echec = not any(c.resultat == ctrl_mod.ECHOUE for c in controles)
    faisable = geo_ok and sans_echec
    # ETUDE-V6-2 (Lot 2) — faisable si l'on RETIRE le stationnement : on lève les DEUX contrôles que les
    # places consomment — « Stationnement » (comptage) ET « Perméabilité (pleine terre) » (le parking
    # mange la pleine terre). Vérifié : ce drapeau reproduit EXACTEMENT un 2ᵉ passage « sans places »
    # (44 logts à Étang-Salé), sans recherche supplémentaire → budget 30 s tenu.
    # (en sous-sol, le gabarit du parking se lit dans « Emprise du sous-sol » → on le lève aussi).
    _hors_stat = {"Stationnement", "Perméabilité (pleine terre)", "Emprise du sous-sol"}
    sans_echec_hors_stat = not any(c.resultat == ctrl_mod.ECHOUE and c.nom not in _hors_stat
                                   for c in controles)
    faisable_sans_stat = geo_ok and sans_echec_hors_stat
    statut = (ctrl_mod.statut_etude(controles, geo_ok, scene=scene, terrain=terrain, regles=regles)
              if geo_ok else "simulation impossible")
    motif = "" if faisable else "; ".join(
        [c.nom for c in checks if not c.ok] + [c.nom for c in controles if c.resultat == ctrl_mod.ECHOUE])
    candidat = Candidat(forme, niveaux, fraction, faisable, statut, cap.logements, cap.shab_estimee_m2,
                        cap.places, cap.places_imposees, motif, faisable_sans_stationnement=faisable_sans_stat)
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


def _rechercher(terrain, regles, conv, objectif, *, repartition=None, stationnement_mode="aerien",
                niveaux_sous_sol=1):
    """Parcourt la grille ORDONNÉE forme×niveaux×fraction et renvoie (ranked, candidats) :
    `ranked` = liste des candidats FAISABLES, triée par la clef d'objectif décroissante, chaque
    item = (clef, paquet, forme, niveaux, fraction). `candidats` = la trace complète.
    `stationnement_mode` ∈ {aerien, sous_sol} (Lot 3)."""
    frame = Frame.depuis(terrain.zone_implantation)
    candidats: list[Candidat] = []
    faisables: list = []
    for forme in _FORMES:
        for niveaux in _NIVEAUX:
            for fraction in _FRACTIONS:
                paquet, cand = _evaluer(terrain, frame, conv, regles, forme, niveaux, fraction,
                                        repartition=repartition, stationnement_mode=stationnement_mode,
                                        niveaux_sous_sol=niveaux_sous_sol)
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

    # IMPLANTATION-4 (scénarios dominés) — ne proposer que des scénarios NON DOMINÉS (filtre de Pareto
    # sur logements, surface habitable, simplicité=moins de bâtiments ; les places ne comptent pas).
    # `faisables` est déjà trié par l'objectif (meilleur d'abord) → A reste le meilleur pour l'objectif.
    survivants = _pareto(faisables)

    choisis = [_paquet_en_scenario(terrain, conv, regles, objectif, candidats, it)
               for it in survivants[:max_scenarios]]
    return choisis, None, terrain, regles, conv


def _n_batiments(scene) -> int:
    """Nombre de bâtiments DESSINÉS (emprises). Sert la « simplicité » (moins de bâtiments = plus
    simple) du filtre de Pareto et la règle de distance mono-bâtiment."""
    return sum(1 for o in scene.objets if o.kind == "batiment_emprise")


def _logts_it(it) -> int:
    return it[1][1].logements


def _depassement(faisables, programme: dict[str, int]) -> dict:
    """La demande ne tient pas entièrement : combien de logements tiennent par type, lesquels manquent
    (au MIEUX atteignable sur l'ensemble des candidats faisables). Jamais « impossible » sans ce chiffre."""
    max_par_type: dict[str, int] = {}
    for it in faisables:
        for t, n in it[1][1].par_type.items():
            max_par_type[t] = max(max_par_type.get(t, 0), n)
    tiennent = {t: min(programme[t], max_par_type.get(t, 0)) for t in programme if programme[t] > 0}
    manquent = {t: programme[t] - tiennent.get(t, 0) for t in programme if programme[t] - tiennent.get(t, 0) > 0}
    return {
        "demande": {t: n for t, n in programme.items() if n > 0},
        "tiennent": tiennent,
        "manquent": manquent,
        "total_demande": sum(n for n in programme.values() if n > 0),
        "total_tiennent": sum(tiennent.values()),
    }


def _metrique_it(it) -> tuple:
    """Métrique de Pareto d'un candidat : (logements, SHAB, nb de bâtiments)."""
    return (it[1][1].logements, it[1][1].shab_estimee_m2, _n_batiments(it[1][0]))


def _sig_it(it) -> tuple:
    return (it[2], it[3])   # (forme, niveaux)


def _roles(base: list, programme: Optional[dict[str, int]]) -> list[tuple[str, object, Optional[str]]]:
    """Les 3 rôles mandat, chacun = (role, candidat ou None, raison d'absence ou None).

    votre_programme = le plus serré qui tient la demande (au mieux si dépassement). optimisation =
    max logements, DISTINCT de votre_programme. alternative = un candidat DISTINCT, **jamais dominé**
    par optimisation ni votre_programme, et jamais un doublon de l'optimisation ; s'il n'en existe pas
    d'utile, l'onglet reste mais dit pourquoi. Même logique pour une variante absente. Pas de 2ᵉ recherche."""
    if not base:
        return [("votre_programme", None, "Aucune implantation ne passe les contrôles sur cette assiette."),
                ("optimisation", None, None), ("alternative", None, None)]
    by_max = sorted(base, key=lambda it: (_logts_it(it), -_n_batiments(it[1][0]), -it[3]), reverse=True)
    if programme:
        couvr = [it for it in base if _contient(it[1][1], programme)]
        votre = (sorted(couvr, key=lambda it: (_logts_it(it), _n_batiments(it[1][0]), it[3]))[0]
                 if couvr else by_max[0])
    else:
        votre = base[0]
    out: list[tuple[str, object, Optional[str]]] = [("votre_programme", votre, None)]
    seen = {_sig_it(votre)}
    m_votre = _metrique_it(votre)

    # Optimisation : la MEILLEURE occupation, distincte et STRICTEMENT meilleure que « votre programme »
    # (ni doublon, ni dominée par lui) — sinon il n'y a rien à optimiser, et on le dit.
    optim = next((it for it in by_max if _sig_it(it) not in seen
                  and _metrique_it(it) != m_votre and not _domine(m_votre, _metrique_it(it))), None)
    if optim is not None:
        out.append(("optimisation", optim, None)); seen.add(_sig_it(optim))
    else:
        out.append(("optimisation", None, "Votre programme atteint déjà le maximum sur ce terrain."))

    # Alternative : distincte, NON dominée par optimisation NI par votre programme, et NON un doublon
    # (mêmes logements/SHAB/bâtiments) de l'une ou l'autre — sinon elle n'apporte rien.
    m_optim = _metrique_it(optim) if optim is not None else None
    utiles = [it for it in by_max if _sig_it(it) not in seen
              and _metrique_it(it) != m_votre and _metrique_it(it) != m_optim
              and not _domine(m_votre, _metrique_it(it))
              and not (m_optim and _domine(m_optim, _metrique_it(it)))]
    if utiles:
        # on préfère une AUTRE FORME que « votre programme », puis le plus de logements.
        alt = sorted(utiles, key=lambda it: (it[2] != votre[2], _logts_it(it)), reverse=True)[0]
        out.append(("alternative", alt, None))
    else:
        out.append(("alternative", None, "Aucune autre forme ne fait mieux que l'optimisation sur ce terrain."))
    return out


def etudier_complet(session=None, *, idus: Optional[list[str]] = None, zone: Optional[str] = None,
                    objectif: str = "equilibre", conv: Optional[Conventions] = None,
                    avec_pente: bool = True, programme: Optional[dict[str, int]] = None,
                    repartition: Optional[list[str]] = None, max_scenarios: int = 3,
                    stationnement_ratio: Optional[float] = None, stationnement_mode: str = "aerien",
                    niveaux_sous_sol: int = 1):
    """ETUDE-V6 (Lot B) — UN SEUL passage de recherche, deux vues :
    `scenarios` = sémantique historique (Pareto des candidats couvrant la demande ; [] si la demande
    ne tient pas), et `variantes` = les 3 rôles du mandat (best-effort si dépassement). Renvoie
    (scenarios, variantes, depassement, message, terrain, regles, conv).

    ETUDE-V6 (Lot C) — `stationnement_ratio` (ex. 0,5) remplace le barème servi par un plafond par
    logement, pour chiffrer la capacité SOUS un régime réduit (plafond national L151-35, à confirmer)."""
    idus = idus or IDUS_ETANG_SALE
    conv = conv or charger_conventions()
    terrain, regles, _zone = _charger(session, idus, zone, conv, avec_pente)
    if stationnement_ratio is not None:
        from dataclasses import replace

        from .regles import BaremeStationnement
        regles = replace(regles, stationnement=BaremeStationnement(
            validee=True, mode="par_logement", base=None, arrondi="superieur",
            flat_places=stationnement_ratio, lignes=(), article="L151-35 (plafond national)",
            page_pdf=None, citation=f"plafond {stationnement_ratio:g} place / logement sous condition d'éligibilité"))
    zi = terrain.zone_implantation
    if zi is None or zi.is_empty or terrain.aire_zone_m2 < 60:
        return [], [], None, _message_impossible(terrain, regles, []), terrain, regles, conv, None
    faisables, candidats = _rechercher(terrain, regles, conv, objectif, repartition=repartition,
                                       stationnement_mode=stationnement_mode,
                                       niveaux_sous_sol=niveaux_sous_sol)
    if not faisables:
        return [], [], None, _message_impossible(terrain, regles, candidats), terrain, regles, conv, None

    message, depassement = None, None
    couvrants = faisables
    if programme:
        couvrants = [it for it in faisables if _contient(it[1][1], programme)]

    if programme and not couvrants:
        message = _message_ne_tient_pas(faisables, programme, regles, conv)
        depassement = _depassement(faisables, programme)
        scenarios = []                       # vue historique : la demande ne tient pas
        base_var = faisables                 # variantes : best-effort
    else:
        scenarios = [_paquet_en_scenario(terrain, conv, regles, objectif, candidats, it)
                     for it in _pareto(couvrants)[:max_scenarios]]
        base_var = couvrants

    variantes = [(role,
                  _paquet_en_scenario(terrain, conv, regles, objectif, candidats, it) if it is not None else None,
                  reason)
                 for role, it, reason in _roles(base_var, programme)]
    # ETUDE-V6-2 (Lot 2/3) — CAPACITÉ MAXIMALE = le candidat FAISABLE au plus grand nombre de logements
    # de CETTE recherche (même répartition que la demande, donc ≥ toute variante dessinée, et stable :
    # deux demandes de même répartition → même maximum). Aucune 2ᵉ recherche → budget tenu, < 20 s.
    scn_max = _paquet_en_scenario(terrain, conv, regles, objectif, candidats, _best_faisable(faisables))
    return scenarios, variantes, depassement, message, terrain, regles, conv, scn_max


def limite_capacite(scenario, regles) -> Optional[str]:
    """IMPLANTATION-4 (recette Vic) — EN UNE LIGNE, ce qui PLAFONNE la capacité du scénario retenu
    (pourquoi pas plus de logements / pas plus haut). Lu dans la trace des candidats :

    - si monter en niveaux N'AJOUTE PAS de logements → c'est le stationnement aérien + la taille de
      la parcelle (cas Saint-Denis : R+2 atteint déjà le plafond, R+5 n'ajoute rien) ;
    - sinon, le motif dominant des candidats plus hauts INFAISABLES (stationnement / largeur de zone /
      distance entre bâtiments / hauteur) ;
    - en préfixe, le prospect quand la hauteur relative n'est pas chiffrée (hauteur bornée par prudence).
    """
    from collections import Counter

    cand = getattr(scenario, "candidats", None) or []
    niv0, logts0 = scenario.niveaux, scenario.capacite.logements
    best: dict[int, int] = {}
    for c in cand:
        if c.faisable:
            best[c.niveaux] = max(best.get(c.niveaux, 0), c.logements)
    plus_haut = [best[n] for n in best if n > niv0]
    monte = any(v > logts0 for v in plus_haut)

    raisons: list[str] = []
    if getattr(regles, "hauteur_non_chiffrable", False):
        raisons.append("le prospect (hauteur relative non chiffrée) borne la hauteur par prudence")
    if plus_haut and not monte:
        raisons.append("le stationnement aérien et la taille de la parcelle "
                       "(monter plus haut n'ajoute pas de logements)")
    else:
        sup = [c for c in cand if c.niveaux > niv0 and not c.faisable and c.motif]
        motifs = Counter(mo.strip() for c in sup for mo in c.motif.split(";") if mo.strip())
        if motifs:
            top = motifs.most_common(1)[0][0].lower()
            if "stationnement" in top:
                raisons.append("le stationnement aérien")
            elif "module" in top or "largeur" in top or "zone" in top or " l " in f" {top} ":
                raisons.append("la largeur de la zone d'implantation après reculs")
            elif "distance" in top:
                raisons.append("la distance entre bâtiments")
            elif "hauteur" in top:
                raisons.append("la hauteur réglementaire")
    return " ; ".join(raisons) or None


# ------------------------------------------------------------------ ETUDE-V6-2 (Lot 2)
def _best_faisable(faisables):
    """Le candidat FAISABLE maximal (plus de logements, puis moins de bâtiments, moins de niveaux).
    `faisables` = sortie de `_rechercher`. None si vide."""
    if not faisables:
        return None
    return max(faisables, key=lambda it: (it[1][1].logements, -_n_batiments(it[1][0]), -it[3]))


def facteurs_limitants(terrain, regles, conv, scenario_max, *, stationnement_mode="aerien") -> list[dict]:
    """ETUDE-V6-2 (Lot 2) — ce qui PLAFONNE la capacité, CLASSÉ par impact (logements perdus). Chaque
    impact est PROUVÉ par un contrefactuel ou chiffré depuis la trace ; un facteur sans impact mesuré
    n'est jamais présenté comme limitant. En particulier, on n'affirme « le stationnement limite » (ou
    « ne limite pas ») qu'après avoir rejoué SANS stationnement imposé et comparé le maximum de logements."""
    if scenario_max is None:
        return []
    logts0 = scenario_max.capacite.logements
    niv0 = scenario_max.niveaux
    cand = scenario_max.candidats or []
    facteurs: list[dict] = []
    sous_sol = stationnement_mode == "sous_sol"

    # (1) STATIONNEMENT — contrefactuel « sans places » LU DANS LA MÊME recherche (pas de 2ᵉ passage,
    # pour tenir le budget même sur une assiette lourde) : le maximum de logements si l'on IGNORE le
    # contrôle de stationnement (en sous-sol, l'emprise enterrée). Si c'est > au maximum réel, il plafonne.
    logts_sans = max((c.logements for c in cand if c.faisable_sans_stationnement), default=logts0)
    delta_stat = max(0, logts_sans - logts0)
    cap = scenario_max.capacite
    stat_m2 = (cap.emprise_sous_sol_m2 if sous_sol else cap.surface_stationnement_m2) or 0.0
    contenance = terrain.contenance_totale_m2 or 0.0
    label = "stationnement en sous-sol" if sous_sol else "stationnement aérien"
    occupe = ("emprise enterrée" if sous_sol else "occupés")
    facteurs.append({
        "facteur": label,
        "impact_logements": delta_stat,
        "limitant": delta_stat > 0,
        "preuve": "contrefactuel sans stationnement imposé",
        "mesure": (f"{stat_m2:.0f} m² {occupe} sur {contenance:.0f} m² d'assiette"
                   if stat_m2 else "aucune place dessinée"),
        "detail": (f"sans stationnement imposé : {logts_sans} logements au maximum "
                   f"(vs {logts0} avec) → +{delta_stat} logement(s)" if delta_stat
                   else f"retirer les places n'ajoute aucun logement ({logts_sans} = {logts0}) : "
                        f"le stationnement n'est pas le facteur limitant ici"),
    })

    # (2) HAUTEUR — le plafond réglementaire borne les niveaux. Impact ESTIMÉ (un niveau de plus ≈ les
    # logements d'un niveau) : on ne peut le MESURER qu'en dépassant une règle, ce qu'on refuse.
    r = regles.hauteur_plafond
    bloque_hauteur = any(c.niveaux > niv0 and not c.faisable and "hauteur" in (c.motif or "").lower()
                         for c in cand)
    if bloque_hauteur and niv0 > 0:
        par_niveau = max(1, round(logts0 / niv0))
        facteurs.append({
            "facteur": "hauteur réglementaire",
            "impact_logements": par_niveau,
            "limitant": True,
            "preuve": "estimé (un niveau de plus)",
            "mesure": (f"R+{niv0 - 1} atteint (plafond {r.valeur:.0f} m)"
                       if r.valeur is not None else f"R+{niv0 - 1} atteint"),
            "detail": f"un niveau de plus ajouterait ≈ {par_niveau} logements, interdit par la hauteur",
        })

    # (3) AUTRES CONTRAINTES — motifs récurrents des candidats écartés (largeur de zone, distance), SANS
    # chiffre d'impact (on ne l'invente pas) : signalées pour transparence, classées après les facteurs mesurés.
    from collections import Counter
    autres: Counter = Counter()
    for c in cand:
        if c.faisable or not c.motif:
            continue
        for mo in c.motif.split(";"):
            mo = mo.strip().lower()
            if "hauteur" in mo or "stationnement" in mo:
                continue  # (1) et (2) déjà traités
            if "largeur" in mo or "zone" in mo or "module" in mo:
                autres["largeur de la zone d'implantation après reculs"] += 1
            elif "distance" in mo:
                autres["distance entre bâtiments"] += 1
    for nom, n in autres.most_common():
        facteurs.append({"facteur": nom, "impact_logements": 0, "limitant": False,
                         "preuve": "motif récurrent des candidats écartés",
                         "mesure": f"{n} candidats écartés", "detail": "impact en logements non chiffré"})

    facteurs.sort(key=lambda f: (f["impact_logements"], f["limitant"]), reverse=True)
    return facteurs


def _domine(a: tuple, b: tuple) -> bool:
    """a domine b : a ≥ b sur (logements, SHAB) ET ≤ sur (nb de bâtiments), avec AU MOINS une inégalité
    stricte. Métrique = (logements, shab_m2, n_batiments)."""
    return (a[0] >= b[0] and a[1] >= b[1] and a[2] <= b[2]
            and (a[0] > b[0] or a[1] > b[1] or a[2] < b[2]))


def _pareto(faisables: list) -> list:
    """Garde les candidats non dominés. Métriques identiques (logements, SHAB arrondi, nb bâtiments) →
    on garde le PREMIER, càd le plus simple à objectif égal (ordre d'entrée = ordre de l'objectif).
    Un scénario strictement inférieur sur les trois (ou ≤ partout et < quelque part) disparaît ; un
    seul survivant = un seul scénario affiché."""
    def metrique(it) -> tuple:
        cap, scene = it[1][1], it[1][0]
        return (cap.logements, cap.shab_estimee_m2, _n_batiments(scene))

    pts = [(metrique(it), it) for it in faisables]
    survivants, vus = [], set()
    for i, (m, it) in enumerate(pts):
        if any(_domine(mo, m) for j, (mo, _) in enumerate(pts) if j != i):
            continue                                   # dominé par un autre → écarté
        cle = (m[0], round(m[1], 1), m[2])
        if cle in vus:
            continue                                   # métriques identiques → on garde le 1er
        vus.add(cle)
        survivants.append(it)
    return survivants


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
