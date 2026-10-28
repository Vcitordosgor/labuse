"""Service d'étude d'implantation — orchestre le moteur pour l'API (IMPLANTATION-2).

Un SEUL point d'entrée : `etudier_payload(session, entree)`. Il
  1. construit les conventions (hypothèses surchargées éventuelles) et, si le programme est saisi,
     la répartition + la demande par type ;
  2. appelle `moteur.etudier_multi` (jusqu'à 3 scénarios distincts, classés par l'objectif) ;
  3. REPROJETTE la géométrie dessinée (EPSG:2975) en GeoJSON WGS84 pour le plan masse de la carte ;
  4. assemble le payload servi : scénarios (résumé 3 chiffres, contrôles 4 états, sections repliables,
     GeoJSON), terrain, règles citées, hypothèses modifiables, versions du moteur et des règles.

Aucun calcul ici n'échappe au moteur : les chiffres sont TIRÉS de la géométrie (cf. capacite.py).
"""
from __future__ import annotations

import logging
import re
from math import gcd
from typing import Any, Optional

from shapely.geometry import mapping

from labuse.geo import to_4326

from . import contexte as contexte_mod
from . import moteur as moteur_mod
from . import planche as planche_mod
from . import rendu as rendu_mod
from .conventions import avec_surcharges, charger as charger_conventions
from .controles import (A_CONFIRMER, ECHOUE, NON_APPLICABLE, NON_EFFECTUE, REUSSI,
                        verdict_global)

OBJECTIFS = {"equilibre", "plus_logements", "plus_surface", "plus_simple"}

def _regles_non_verifiees(regles) -> list[dict]:
    """ETUDE-V6-2 (Lot 3) — obligations d'aménagement (espaces verts, marge plantée) SEULEMENT si elles ne
    sont PAS calibrées pour la zone : là où elles le sont (ex. UA Étang-Salé, correction §2), elles passent
    par un contrôle VÉRIFIÉ et ne figurent plus ici."""
    out = []
    if not (getattr(regles, "espaces_verts", None) and regles.espaces_verts.validee):
        out.append({"nom": "Espaces verts (hors stationnement)",
                    "exemple": "ex. UA : part de la parcelle à végétaliser, hors aires de stationnement",
                    "statut": "non vérifié",
                    "note": "non calibré pour cette zone — à vérifier au règlement ; réduirait la capacité."})
    if not (getattr(regles, "marge_plantee", None) and regles.marge_plantee.validee):
        out.append({"nom": "Marge plantée périphérique",
                    "exemple": "ex. UA : bande plantée en limite, sur une fraction du linéaire",
                    "statut": "non vérifié",
                    "note": "non calibré pour cette zone — à vérifier au règlement ; réduirait la capacité."})
    return out
TYPES_LOGEMENT = ("T1", "T2", "T3", "T4")  # ETUDE-V6 — le programme saisi va du T1 au T4
_REFS = ["A", "B", "C"]


def _pente_pct(deg: float) -> int:
    from labuse.pente_fmt import pente_pct
    return pente_pct(deg)


def _pente_fiche_deg(session, idus) -> Optional[float]:
    """DOCS-COHERENCE-1 (A4) — pente de la FICHE (RGE ALTI, `parcel_terrain.pente_moy_deg`), source
    UNIQUE affichée par tous les documents ; prise sur la parcelle principale (plus grande) de
    l'assiette. None si absente (le document omet alors la ligne, jamais un faux chiffre)."""
    from sqlalchemy import text
    row = session.execute(text(
        "SELECT pt.pente_moy_deg FROM parcel_terrain pt JOIN parcels p ON p.idu = pt.idu "
        "WHERE pt.idu = ANY(:i) AND pt.pente_moy_deg IS NOT NULL "
        "ORDER BY ST_Area(p.geom_2975) DESC LIMIT 1"), {"i": list(idus or [])}).scalar()
    return float(row) if row is not None else None


# ------------------------------------------------------------------ GeoJSON (4326)
def _feature(geom_2975, props: dict) -> Optional[dict]:
    if geom_2975 is None or geom_2975.is_empty:
        return None
    g = to_4326(geom_2975)
    # La reprojection 2975→4326 (pyproj) peut, en flottant, rendre AUTO-SÉCANTE une géométrie
    # pourtant valide côté métrique. On la revalide pour que le GeoJSON servi soit toujours valide.
    if not g.is_valid:
        g = g.buffer(0)
    if g.is_empty:
        return None
    return {"type": "Feature", "properties": props, "geometry": mapping(g)}


def _fc(features: list) -> dict:
    return {"type": "FeatureCollection", "features": [f for f in features if f]}


def _geojson_scenario(scenario) -> dict:
    """Une FeatureCollection par scénario : contexte terrain (parcelles, zone/reculs, voie, PPR) +
    objets du plan masse (bâtiments, modules RDC, noyaux, coursives, places, allées, accès, espaces
    libres). Chaque feature porte `kind` (+ niveau/type) pour l'activation de couches côté carte."""
    t, sc = scenario.terrain, scenario.scene
    feats: list = []
    for p in t.parcelles:
        if p.geom_2975 is not None:
            feats.append(_feature(p.geom_2975, {"kind": "parcelle", "ref": p.numero}))
    feats.append(_feature(t.assiette, {"kind": "assiette"}))
    feats.append(_feature(t.zone_implantation, {"kind": "zone"}))
    if getattr(t, "ppr_rouge", None) is not None:
        feats.append(_feature(t.ppr_rouge, {"kind": "ppr_rouge"}))
    if getattr(t, "ppr_bleue", None) is not None:
        feats.append(_feature(t.ppr_bleue, {"kind": "ppr_bleue"}))
    for g in t.voie_edges:
        feats.append({"type": "Feature", "properties": {"kind": "voie"},
                      "geometry": mapping(to_4326(g))})
    # objets du plan (vue RDC : modules/noyaux/coursives niveau 0, le reste tel quel)
    for o in sc.objets:
        if o.kind in ("module", "noyau", "coursive") and o.niveau not in (0, None):
            continue
        g = o.geom_world if o.geom_world is not None else o.geom_local
        feats.append(_feature(g, {"kind": o.kind, "niveau": o.niveau,
                                  "type_logement": o.type_logement, "ref": o.ref}))
    return _fc(feats)


# ------------------------------------------------------------------ compteurs / résumés
def _compte_controles(controles) -> dict:
    c = {REUSSI: 0, ECHOUE: 0, NON_EFFECTUE: 0, NON_APPLICABLE: 0, A_CONFIRMER: 0}
    for ct in controles:
        if ct.resultat in c:
            c[ct.resultat] += 1
    return {"reussi": c[REUSSI], "echoue": c[ECHOUE], "non_effectue": c[NON_EFFECTUE],
            "non_applicable": c[NON_APPLICABLE], "a_confirmer": c[A_CONFIRMER]}


def _facteur_limitant_phrase(facteurs_limitants: list, variante: Optional[dict]) -> Optional[str]:
    """ETUDE-V6-4 (items 10/11/13) — LA phrase « ce qui limite », calculée UNE SEULE FOIS côté serveur
    pour que l'écran et le PDF disent exactement les mêmes mots. Reprend la logique de l'écran :
    1er facteur limitant, sinon la limite de capacité de la variante ; en sous-sol, si la hauteur limite
    et que le terrain est en pente, on nomme la pente."""
    f0 = facteurs_limitants[0] if facteurs_limitants else None
    phrase = (f0 or {}).get("facteur") if f0 else None
    if phrase is None and variante is not None:
        phrase = variante.get("limite_capacite")
    if variante is not None and (variante.get("stationnement") or {}).get("mode") == "sous_sol" \
            and phrase and str(phrase).startswith("hauteur"):
        m = _relief_pente(variante)
        if m:
            phrase = f"hauteur sur la pente (relief {m} m)"
    return phrase


def _relief_pente(variante: Optional[dict]) -> Optional[str]:
    """Relief mesuré (m) du contrôle « Hauteur sur terrain en pente », ou None."""
    if variante is None:
        return None
    pente = next((c for c in (variante.get("controles") or [])
                  if c.get("nom") == "Hauteur sur terrain en pente"), None)
    m = re.search(r"relief[^\d]*([\d.,]+)\s*m", (pente or {}).get("mesure") or "") if pente else None
    return m.group(1) if m else None


def _facteur_limitant_detail(facteur: Optional[str], variante: Optional[dict]) -> Optional[str]:
    """ETUDE-V6-4 (item 10) — en sous-sol, si c'est la HAUTEUR qui plafonne, une phrase qui dit POURQUOI.
    Notre modèle enterre le parking sans surélever le RDC : la hauteur ne limite donc pas À CAUSE du
    sous-sol, mais parce que le terrain est en pente — le stationnement enterré a libéré le sol et c'est
    alors le relief qui plafonne le nombre de niveaux. On l'écrit, à l'écran comme au PDF."""
    if variante is None or (variante.get("stationnement") or {}).get("mode") != "sous_sol":
        return None
    if not (facteur and str(facteur).startswith("hauteur")):
        return None
    relief = _relief_pente(variante)
    niv = variante.get("niveaux_label")
    base = ("En sous-sol, le stationnement enterré libère le sol ; c'est alors le relief du terrain "
            f"qui plafonne la hauteur")
    if relief:
        base += f" (dénivelé {relief} m)"
    if niv:
        base += f", d'où un bâtiment limité à {niv}"
    return base + ". Le sous-sol est modélisé entièrement enterré, sans RDC surélevé."


def _scenario_public(scenario, ref: str, conv=None) -> dict:
    """Vue servie d'un scénario : résumé (3 chiffres clés), sections repliables, contrôles, GeoJSON."""
    cap = scenario.capacite
    sd = rendu_mod.scenario_dict(scenario)
    controles = sd["controles_reglementaires"]
    # ETUDE-V6-7 (item 2) — SURFACE TENUE = Σ (logements DESSINÉS par type × surface saisie du type). Une
    # seule vérité (le plan), jamais la surface de la demande. `conv.modules[t].surface_m2` = surface saisie.
    surface_tenue = None
    if conv is not None:
        surface_tenue = round(sum(n * conv.modules[t].surface_m2 for t, n in (cap.par_type or {}).items()
                                  if t in conv.modules), 1)
    return {
        "ref": ref,
        "forme": scenario.forme,
        "niveaux": scenario.niveaux,
        "niveaux_label": f"R+{max(0, scenario.niveaux - 1)}",
        "statut_etude": scenario.statut,
        "resume": {
            "logements": cap.logements,
            "places": cap.places,
            "sdp_m2": cap.sdp_m2,
        },
        # recette Vic — en une ligne, ce qui plafonne la capacité (pas plus de logements / pas plus haut).
        "limite_capacite": moteur_mod.limite_capacite(scenario, scenario.regles),
        "controles_compte": _compte_controles(scenario.controles),
        "programme": {
            "par_type": cap.par_type,
            "shab_par_type_m2": cap.shab_par_type_m2,
            "shab_estimee_m2": cap.shab_estimee_m2,
            "ratio_shab_sdp": cap.ratio_shab_sdp,
            "mixite_applicable": cap.mixite_applicable,
            "logements_aides_imposes": cap.logements_aides_imposes,
            "sdp_aidee_imposee_m2": cap.sdp_aidee_imposee_m2,
            "surface_tenue_m2": surface_tenue,
        },
        "distribution_niveaux": cap.distribution_niveaux,
        "stationnement": {
            "places": cap.places,
            "places_imposees": cap.places_imposees,
            "details_places": cap.details_places,
            "m2_par_place": cap.m2_par_place,
            "surface_stationnement_m2": cap.surface_stationnement_m2,
            "note": scenario.scene.stationnement_note,
            "acces": sd["scenario"].get("acces"),
            # ETUDE-V6-2 (Lot 3) — parking enterré : mode, places au −1, emprise du sous-sol, rampe au sol.
            "mode": cap.stationnement_mode,
            "places_sous_sol": cap.places_sous_sol,
            "emprise_sous_sol_m2": cap.emprise_sous_sol_m2,
            # ETUDE-V6-7 (item 3) — emprise AFFICHÉE = emprise DESSINÉE (le contour tracé), source unique.
            "emprise_dessinee_m2": cap.emprise_sous_sol_m2,
            "rampe_m2": cap.rampe_m2,
            # ETUDE-V6-4/5 (item 9) — plan du niveau −1 (et −2) : capacité d'un niveau + niveaux CHOISIS +
            # répartition dessinée par niveau.
            "places_sous_sol_par_niveau": cap.places_sous_sol_par_niveau,
            "niveaux_sous_sol": cap.niveaux_sous_sol,
            "places_niveau_moins1": cap.places_niveau_moins1,
            "places_niveau_moins2": cap.places_niveau_moins2,
            # ETUDE-V6-2 (Lot 3, correction §3) — calcul de la rampe : profondeur / pente → longueur × largeur.
            "rampe_detail": ({k: (scenario.scene.sous_sol or {}).get(k) for k in
                              ("rampe_profondeur_m", "rampe_pente_pct", "rampe_longueur_m", "rampe_largeur_m")}
                             if scenario.scene.sous_sol else None),
            # ETUDE-V6-2 (Lot 3, correction) — surface au-dessus du sous-sol RETRANCHÉE de la pleine terre.
            "sur_dalle_m2": cap.sur_dalle_m2,
        },
        "surfaces_mesurees_m2": sd["tableau_capacite"]["surfaces_mesurees_m2"],
        "emprise_sol_m2": cap.emprise_sol_m2,
        "pleine_terre_m2": cap.pleine_terre_m2,
        "controles": controles,
        "checks_geometriques": sd["controles_geometriques"],
        "geojson": _geojson_scenario(scenario),
    }


# ------------------------------------------------------------------ ETUDE-V6 (Lot B) : variantes
_ROLE_LABELS = {"votre_programme": "Votre programme", "optimisation": "Optimisation",
                "alternative": "Alternative"}


def _grandeurs(terrain, regles, conv, scenario) -> dict:
    """Les QUATRE grandeurs du mandat, JAMAIS confondues : sol restant au sol, emprise encore
    mobilisable, SDP autorisée (plafond réglementaire), m² de programme (plancher) envisageables.
    Chacune porte un statut : mesuré (sur le dessin), dérivé (d'une règle), non vérifié (règle absente)."""
    cap = scenario.capacite
    contenance = terrain.contenance_totale_m2
    emprise = cap.emprise_sol_m2 or 0.0
    stat = cap.surface_stationnement_m2 or 0.0
    sol_restant = max(0.0, contenance - emprise - stat)
    out = {
        "sol_restant": {"valeur_m2": round(sol_restant, 1), "statut": "mesuré",
                        "detail": f"{contenance:.0f} m² − {emprise:.0f} bâti − {stat:.0f} stationnement"},
    }
    ces = regles.emprise_ces
    if ces.validee and ces.valeur is not None:
        emprise_max = contenance * ces.valeur / 100.0
        out["emprise_mobilisable"] = {"valeur_m2": round(max(0.0, emprise_max - emprise), 1), "statut": "dérivé",
                                      "detail": f"CES {ces.valeur:.0f} % = {emprise_max:.0f} m² max − {emprise:.0f} m² dessinés"}
        h = regles.hauteur_plafond
        if h.validee and h.valeur is not None and conv.hauteur_etage_m > 0:
            niv_max = max(1, int(h.valeur // conv.hauteur_etage_m))
            out["sdp_autorisee"] = {"valeur_m2": round(emprise_max * niv_max, 1), "statut": "dérivé",
                                    "detail": f"{emprise_max:.0f} m² × R+{niv_max - 1} (plafond {h.valeur:.0f} m)"}
        else:
            out["sdp_autorisee"] = {"valeur_m2": None, "statut": "non vérifié", "detail": "hauteur non chiffrée"}
    else:
        out["emprise_mobilisable"] = {"valeur_m2": None, "statut": "non vérifié", "detail": "CES non servi"}
        out["sdp_autorisee"] = {"valeur_m2": None, "statut": "non vérifié", "detail": "CES non servi"}
    out["programme_envisageable"] = {"valeur_m2": round(cap.sdp_m2, 1), "statut": "mesuré",
                                     "detail": "SDP (plancher) dessinée de la variante"}
    return out


def _variante_absente(role: str, reason: str) -> dict:
    """Une variante ABSENTE garde son onglet et DIT pourquoi (mandat §C : une variante vide s'explique)."""
    return {"ref": role, "role": role, "role_label": _ROLE_LABELS.get(role, role),
            "absente": True, "raison": reason}


def _variante_public(role: str, scenario, terrain, conv, regles, demande: dict) -> dict:
    """Vue servie d'une variante : le scénario public + rôle (mandat), verdict global (3 libellés),
    les 4 grandeurs, et l'écart CHIFFRÉ demande ↔ variante dessinée (donc prouvé)."""
    pub = _scenario_public(scenario, role, conv)
    pub["absente"] = False
    pub["raison"] = None
    pub["role"] = role
    pub["role_label"] = _ROLE_LABELS.get(role, role)
    pub["verdict"] = verdict_global(scenario.controles, statut_base=scenario.statut, terrain=terrain)
    pub["grandeurs"] = _grandeurs(terrain, regles, conv, scenario)
    cap = scenario.capacite
    if demande:
        dem_tot = sum(n for n in demande.values() if n > 0)
        pub["ecart"] = {
            "demande_total": dem_tot, "variante_total": cap.logements,
            "reserve_logements": cap.logements - dem_tot,
            "par_type_demande": {t: n for t, n in demande.items() if n > 0},
            "par_type_variante": cap.par_type, "prouve": True,
        }
    else:
        pub["ecart"] = None
    # ETUDE-V6-7 (item 4) — en SOUS-SOL, le sol libéré (plus de parking au sol) sert à bâtir plus : une phrase
    # dit comment il est utilisé, CHIFFRÉE si le bâtiment reste sous le plafond de hauteur (R+k < R+max).
    pub["sol_libere_note"] = _sol_libere_note(scenario, conv, regles)
    # ETUDE-V6-7 (suite) — si le plan dévie du PRORATA EXACT pour tenir dans les places du −1, on l'explique.
    pub["prorata_note"] = _prorata_note(scenario, demande, conv, regles)
    return pub


def _barème_places(demande: dict, conv, regles) -> int:
    """Places EXIGÉES par le barème PLU pour la demande (par type)."""
    import math as _m
    b = regles.stationnement
    total = 0.0
    for t, n in demande.items():
        if n <= 0:
            continue
        mod = conv.modules.get(t)
        u = b.places_pour(pieces=mod.pieces, sdp_m2=mod.surface_m2, destination="collectif") if (mod and b.validee) else None
        total += n * (u if u is not None else 1.0)
    return b.arrondir(total) if b.validee else int(_m.ceil(total))


def _appliquer_programme_au_scenario(scenario, demande: dict, conv, regles) -> bool:
    """ETUDE-V6-8 (item 1) — UNE SEULE implantation : celle du programme du client. Quand le plan dessiné
    COUVRE la demande (overshoot au maximum du terrain), on rogne le SCÉNARIO LUI-MÊME (sa géométrie), puis
    on RECALCULE capacité + contrôles depuis le plan rogné. Ainsi plan masse, planche, répartition par
    niveau, coupe, SDP, places, contrôles et SHAB viennent TOUS du même plan (plus de patch de façade sur
    la vue servie). Renvoie True si le scénario a été rogné, False sinon (la demande ne couvre pas → prorata
    déjà dessiné par le moteur)."""
    from . import capacite as cap_mod
    from . import controles as ctrl_mod
    cap = scenario.capacite
    par = cap.par_type or {}
    dem = {t: int(n) for t, n in demande.items() if n > 0}
    if not dem or any(par.get(t, 0) < n for t, n in dem.items()):
        return False                                             # ne couvre pas → prorata déjà appliqué
    # OVERSHOOT seulement : si le plan dessiné est DÉJÀ la demande exacte (aucun type en trop), on NE TOUCHE
    # PAS à la géométrie (la redessiner perturberait un plan déjà propre). Rien à rogner → rien à faire.
    if not (any(par.get(t, 0) > dem.get(t, 0) for t in par) or sum(par.values()) > sum(dem.values())):
        return False
    scene = scenario.scene
    # 1) retirer les modules EN TROP, en vidant les niveaux les plus HAUTS d'abord (étage du haut partiel) ;
    #    on garde `dem[t]` modules de chaque type, pris sur les niveaux les plus BAS (plan le plus compact).
    from collections import defaultdict
    par_type_mods: dict = defaultdict(list)
    for o in scene.of("module"):
        par_type_mods[o.type_logement].append(o)
    a_retirer: set = set()
    for t, lst in par_type_mods.items():
        lst.sort(key=lambda o: (o.niveau or 0, round(o.geom_local.bounds[0], 2)))
        for o in lst[dem.get(t, 0):]:
            a_retirer.add(id(o))
    scene.objets = [o for o in scene.objets if not (o.kind == "module" and id(o) in a_retirer)]
    # 2) stationnement rogné à la demande (barème PLU) : aérien → on retire les places EN TROP ;
    #    sous-sol → on redessine le niveau −1 à la cible (le sol reste libre, pleine terre en hausse).
    places_cible = _barème_places(dem, conv, regles)
    if cap.stationnement_mode == "sous_sol":
        from .geometrie import poser_sous_sol
        for k in ("rampe", "sous_sol_emprise", "allee_ss", "place_ss"):
            scene.objets = [o for o in scene.objets if o.kind != k]
        poser_sous_sol(scene, conv, cible=places_cible, niveaux=cap.niveaux_sous_sol or 1)
    else:
        # on REDESSINE proprement le stationnement aérien à la cible (allée coupée au droit des places,
        # aucun tronçon mort — garanti par poser_stationnement) plutôt que de retirer des places une à une.
        from .geometrie import poser_stationnement
        for k in ("place", "allee", "acces"):
            scene.objets = [o for o in scene.objets if o.kind != k]
        poser_stationnement(scene, conv, cible=places_cible)
    # 3) espaces libres RECALCULÉS sur le plan rogné (le sol libéré par les objets retirés redevient libre),
    #    puis RECALCUL de tout depuis la MÊME géométrie.
    from .geometrie import poser_espaces_libres
    scene.objets = [o for o in scene.objets if o.kind != "espace_libre"]
    poser_espaces_libres(scene)
    scene.finaliser_monde()
    newcap = cap_mod.calculer(scene, conv, regles, scenario.terrain)
    scenario.capacite = newcap
    scenario.checks_geo = ctrl_mod.verifier_geometrie(scene, scenario.terrain, conv, newcap, regles)
    scenario.controles = ctrl_mod.controles_reglementaires(scene, scenario.terrain, conv, newcap, regles)
    # ETUDE-V6-8b (bug 1) — le STATUT est recalculé sur le plan rogné : « simulation impossible » ne vaut que
    # si le plan est géométriquement INVALIDE (recouvrement ou surfaces ≠ assiette). Un bâtiment rogné garde
    # un RDC pleine largeur → l'allée peut laisser un court tronçon mort (contrôle de propreté) : cela ne rend
    # pas l'étude impossible. On ne force donc « impossible » que sur les contrôles d'INTÉGRITÉ.
    _integrite = [c for c in scenario.checks_geo
                  if any(k in c.nom for k in ("chevauchement", "somme des surfaces"))]
    geo_ok = all(c.ok for c in _integrite) if _integrite else ctrl_mod.geometrie_valide(scenario.checks_geo)
    scenario.statut = (ctrl_mod.statut_etude(scenario.controles, geo_ok, scene=scene,
                                             terrain=scenario.terrain, regles=regles)
                       if geo_ok else "simulation impossible")
    return True


def _sol_libere_note(scenario, conv, regles) -> Optional[str]:
    cap = scenario.capacite
    if cap.stationnement_mode != "sous_sol":
        return None
    niv = scenario.niveaux
    h = regles.hauteur_plafond
    niv_max = int(h.valeur // conv.hauteur_etage_m) if (h.validee and h.valeur and conv.hauteur_etage_m) else niv
    nb_bat = len({o.ref for o in scenario.scene.of("batiment_emprise")}) or 1
    forme = str(scenario.forme).replace("_", " ")
    base = (f"Le stationnement enterré libère le sol : {cap.logements} logements bâtis "
            f"({forme}, {nb_bat} bâtiment{'s' if nb_bat > 1 else ''})")
    if niv < niv_max:
        return (base + f", mais le bâtiment s'arrête à R+{max(0, niv - 1)} sous le plafond R+{max(0, niv_max - 1)} "
                f"— la hauteur réglementaire (ou le relief) borne la montée.")
    return base + f" au maximum réglementaire (R+{max(0, niv - 1)})."


def _prorata_note(scenario, demande: dict, conv, regles) -> Optional[str]:
    """Si le plan dessiné dévie du PRORATA EXACT de la demande POUR tenir dans les places du −1 (le prorata
    exact exigerait plus de places que le sous-sol n'en offre), on l'explique en une phrase : types retirés
    remplacés par des types plus sobres en places, pour tenir dans les N places du sous-sol. Sinon None."""
    cap = scenario.capacite
    if cap.stationnement_mode != "sous_sol" or not demande:
        return None
    drawn = {t: int(n) for t, n in (cap.par_type or {}).items() if n > 0}
    tenus = sum(drawn.values())
    if tenus <= 0:
        return None
    dem = {t: int(n) for t, n in demande.items() if n > 0}
    from .geometrie import _repartir_prorata
    ideal = _repartir_prorata(dem, tenus)                        # prorata exact (plus grand reste)
    ideal = {t: n for t, n in ideal.items() if n > 0}
    if ideal == drawn:
        return None                                              # pas de déviation
    import math as _m
    b = regles.stationnement

    def _places(d: dict) -> int:
        tot = 0.0
        for t, n in d.items():
            mod = conv.modules.get(t)
            u = b.places_pour(pieces=mod.pieces, sdp_m2=mod.surface_m2, destination="collectif") if (mod and b.validee) else None
            tot += n * (u if u is not None else 1.0)
        return b.arrondir(tot) if b.validee else int(_m.ceil(tot))

    cap_niveau = cap.places_sous_sol_par_niveau or cap.places
    if not cap_niveau or _places(ideal) <= cap_niveau:
        return None                                              # déviation NON liée aux places → rien à expliquer

    retires = {t: ideal.get(t, 0) - drawn.get(t, 0) for t in set(ideal) | set(drawn) if ideal.get(t, 0) > drawn.get(t, 0)}
    ajoutes = {t: drawn.get(t, 0) - ideal.get(t, 0) for t in set(ideal) | set(drawn) if drawn.get(t, 0) > ideal.get(t, 0)}
    if not retires or not ajoutes:
        return None

    def _fmt(d: dict) -> str:
        return " et ".join(f"{n} {t}" for t, n in sorted(d.items()))

    return (f"{_fmt(retires)} remplacé{'s' if sum(retires.values()) > 1 else ''} par {_fmt(ajoutes)} "
            f"pour tenir dans les {cap_niveau} places du sous-sol.")


# ------------------------------------------------------------------ règles citées (affichage)
def _regles_affichables(sd: dict) -> list[dict]:
    """Lignes de règles pour l'affichage (nom, valeur, unité, citation) — depuis version_regles."""
    vr = sd["version_regles"]
    out = []
    for cle in ("recul_voie", "recul_separatives", "emprise_ces", "hauteur_egout",
                "hauteur_faitage", "pleine_terre"):
        r = vr.get(cle)
        if r:
            out.append({"nom": r["nom"], "valeur": r["valeur"], "unite": r["unite"],
                        "validee": r["validee"], "article": r["article"],
                        "page_pdf": r["page_pdf"], "citation": r["citation"]})
    mx = vr.get("mixite") or {}
    if mx.get("validee"):
        out.append({"nom": "mixité sociale", "valeur": mx.get("quota_pct"), "unite": "%",
                    "validee": True, "article": mx.get("article"), "page_pdf": mx.get("page_pdf"),
                    "citation": mx.get("citation"), "seuil_m2": mx.get("seuil_m2")})
    st = vr.get("stationnement_bareme") or {}
    if st.get("validee"):
        out.append({"nom": "stationnement (barème)", "valeur": None, "unite": None,
                    "validee": True, "article": st.get("article"), "page_pdf": st.get("page_pdf"),
                    "citation": st.get("citation")})
    return out


def _decore_regles(lignes: list[dict], source_url: Optional[str], millesime: Optional[str]) -> list[dict]:
    """ETUDE-V6-4 (item 3) — chaque règle porte le lien du document PLU officiel et son millésime, pour que
    « Lire l'article » affiche l'extrait exact (texte, article, page, millésime) avec le lien, partout."""
    for l in lignes:
        l.setdefault("source_url", source_url)
        l.setdefault("millesime", millesime)
    return lignes


# ------------------------------------------------------------------ programme saisi → demande/répartition
def _programme_vers_demande(programme: dict) -> tuple[dict[str, int], list[str], dict[str, float]]:
    """{'lignes':[{'type':'T2','nombre':12,'surface_m2':50}]} → (demande, répartition, surfaces).
    La répartition reproduit la PROPORTION demandée (réduite par le PGCD) pour que le pavage du
    moteur suive le programme ; la demande sert à filtrer les candidats qui le CONTIENNENT."""
    demande: dict[str, int] = {}
    surfaces: dict[str, float] = {}
    for ligne in programme.get("lignes", []):
        t = str(ligne.get("type", "")).upper()
        if t not in TYPES_LOGEMENT:
            continue
        n = int(ligne.get("nombre") or 0)
        if n > 0:
            demande[t] = demande.get(t, 0) + n
        s = ligne.get("surface_m2")
        if s:
            surfaces[t] = float(s)
    if not demande:
        return {}, [], surfaces
    g = 0
    for n in demande.values():
        g = gcd(g, n)
    g = g or 1
    counts = {t: demande[t] // g for t in TYPES_LOGEMENT if t in demande}
    # ETUDE-V6-7 (item 1) — répartition ENTRELACÉE (proportionnelle) et non par blocs : quand le pavage
    # tronque la séquence (le programme ne tient pas en entier), les types restent dans LA PROPORTION
    # demandée — jamais « tous les T1 d'abord » (ce qui mettait des T1 à la place des T4).
    repartition = _entrelacer(counts)
    return demande, repartition, surfaces


def _entrelacer(counts: dict[str, int]) -> list[str]:
    """Séquence entrelacée reproduisant les proportions `counts` : à chaque pas on pose le type le plus en
    retard sur sa part cible (plus grand reste). Déterministe (départage par effectif puis ordre T1..T4)."""
    total = sum(counts.values())
    if total <= 0:
        return []
    ordre = {t: i for i, t in enumerate(TYPES_LOGEMENT)}
    placed = {t: 0 for t in counts}
    seq: list[str] = []
    for k in range(total):
        best = max(counts, key=lambda t: (counts[t] * (k + 1) - placed[t] * total, counts[t], -ordre[t]))
        seq.append(best)
        placed[best] += 1
    return seq


# ------------------------------------------------------------------ ETUDE-V6 (Lot E) : study_id + bilan
def _study_id(entree: dict) -> str:
    """Identifiant STABLE de l'étude : empreinte de la configuration (idus + type + programme +
    hypothèses). Même config → même study_id → l'écran et le PDF portent le même identifiant et, le
    PDF étant rendu de la MÊME donnée, les mêmes chiffres (verrou `nombres_hors_payload`)."""
    import hashlib
    import json
    cle = {k: entree.get(k) for k in ("idus", "type_projet", "objectif", "programme", "hypotheses",
                                      "stationnement", "niveaux_sous_sol", "terrain")}
    brut = json.dumps(cle, sort_keys=True, ensure_ascii=False, default=str)
    return "EF-" + hashlib.sha1(brut.encode("utf-8")).hexdigest()[:12]


def _bilan_collectif(terrain_pub: dict, variante: Optional[dict]) -> dict:
    """Bilan surfacique CLOS d'un collectif. Deux garanties distinctes, pas une somme fallacieuse des 4
    grandeurs (qui sont volontairement séparées) : (1) la DÉCOMPOSITION DU TERRAIN est close — contenance
    = zone constructible + hors-zone (A/N, reculs, PPR) ; (2) le PLAN tile l'assiette SANS CHEVAUCHEMENT
    (contrôles géométriques verts) → aucune double comptabilisation."""
    contenance = terrain_pub["contenance_totale_m2"]
    zone = terrain_pub["zone_implantation_m2"]
    hors = round(max(0.0, contenance - zone), 1)
    decomp = abs((zone + hors) - contenance) <= 0.02 * max(1.0, contenance)
    out = {"contenance_m2": contenance, "zone_constructible_m2": zone, "hors_zone_m2": hors,
           "decomposition_close": decomp}
    if variante:
        out["emprise_batie_m2"] = round(variante["emprise_sol_m2"] or 0.0, 1)
        out["stationnement_m2"] = round(variante["stationnement"]["surface_stationnement_m2"] or 0.0, 1)
        out["pleine_terre_m2"] = round(variante["pleine_terre_m2"] or 0.0, 1)
        # « sans chevauchement » = AUCUNE double comptabilisation : pas de recouvrement entre objets ET la
        # somme des surfaces mesurées = l'assiette. (Les autres contrôles géométriques — tidiness d'allée,
        # largeur, dimensions — relèvent de la qualité du plan, pas du bilan surfacique.)
        _cle_bilan = ("chevauchement", "somme des surfaces")
        _pertinents = [c for c in (variante.get("checks_geometriques") or [])
                       if any(k in (c.get("nom") or "") for k in _cle_bilan)]
        geo = bool(_pertinents) and all(c.get("ok") for c in _pertinents)
        out["plan_sans_chevauchement"] = geo
        out["clos"] = bool(decomp and geo)
    else:
        out["clos"] = bool(decomp)
    return out


# ------------------------------------------------------------------ ETUDE-V6 (Lot C) : stationnement
_TYPES_PROJET = {"collectif", "etudiante", "senior", "social", "lotissement"}

# Destinations ouvrant une catégorie L151-34 (donc un plafond national L151-35 « sous condition
# d'éligibilité ») : le NOM commercial ne prouve pas la catégorie juridique → toujours « À confirmer ».
_L15134 = {
    "social": "logement locatif aidé (L151-34, 1°)",
    "senior": "résidence pour personnes âgées (L151-34, 3°)",
    "etudiante": "résidence universitaire (L151-34)",
}
# REMISE-1 (décision Vic) — SOURCE UNIQUE avec moteur._plafond_l151 (règle APPLIQUÉE) :
#   · L151-35 (logement aidé / RPA / résidence universitaire, 1°-3° de L151-34) : au plus 1 place/logement,
#     et au plus 0,5 À MOINS DE 500 m d'un transport collectif en site propre bien desservi.
#   · L151-36 (AUTRES logements) : au plus 1 place/logement, SEULEMENT à moins de 500 m d'un tel transport.
# (L'ancien code posait 0,5 inconditionnel « L151-35 » à < 800 m — il mélangeait L151-35 et L151-36 et
#  prenait le mauvais seuil ; corrigé ici pour que l'AFFICHAGE dise exactement ce que le moteur APPLIQUE.)
def _ratio_l15135(sous_500: bool) -> float:
    return 0.5 if sous_500 else 1.0


def _tcsp_sous_500m(session, idus: list[str]) -> tuple[bool, Optional[int]]:
    """Condition géographique des plafonds L151-35/36 : distance au plus proche TCSP (< 500 m). On réutilise
    `moteur._tcsp_dist_m` (STATIONS en site propre `tcsp_station` SEULEMENT — un simple arrêt de bus ne
    déclenche pas le plafond) → l'affichage et le calcul appliqué partagent la MÊME distance et le MÊME seuil."""
    from .moteur import _tcsp_dist_m
    d = _tcsp_dist_m(session, idus)
    return (d is not None and d < 500), (int(d) if d is not None else None)


def _plu_millesime(session, insee: str) -> Optional[str]:
    from sqlalchemy import text
    try:
        m = session.execute(text("SELECT max(millesime) FROM plu_reglement_extrait WHERE insee = :i"),
                            {"i": insee}).scalar()
        return str(m) if m else None
    except Exception:  # noqa: BLE001
        return None


def _plu_gpu_url(session, insee: str) -> Optional[str]:
    """ETUDE-V6-7 (item 9) — URL du règlement sur le GÉOPORTAIL DE L'URBANISME, construite depuis l'idurba
    (identifiant du document d'urbanisme) du PLU calibré : page officielle de consultation du document. None
    si aucun idurba (donc aucun document en ligne) → « non disponible en lien direct » côté écran."""
    from sqlalchemy import text
    try:
        idurba = session.execute(text("SELECT idurba FROM plu_reglement_extrait "
                                      "WHERE insee = :i AND idurba IS NOT NULL LIMIT 1"),
                                 {"i": insee}).scalar()
    except Exception:  # noqa: BLE001
        idurba = None
    return f"https://www.geoportail-urbanisme.gouv.fr/document/{idurba}" if idurba else None


def _plu_source_url(session, insee: str) -> Optional[str]:
    """ETUDE-V6-7 (item 9) — lien « Lire l'article » = le document sur le Géoportail de l'urbanisme (source
    officielle), remplace l'ancien lien de téléchargement geopf. La page figure dans le texte « p. N »."""
    return _plu_gpu_url(session, insee)


def _regle_stationnement_courte(b) -> Optional[str]:
    """ETUDE-V6-3 (item 3) — la règle de stationnement en clair et courte. Par logement → « N place/logt » ;
    par typologie → « p pl. Tx–Ty » par tranche de pièces (Tn = n pièces principales)."""
    if not b.validee:
        return None
    def nb(x):
        return f"{x:g}".replace(".", ",")
    if b.mode == "par_logement" and b.flat_places is not None:
        # DOCS-COHERENCE-1 (F9/A6) — format client « 2 places / logement » (jamais « 2 place/logt »).
        return f"{nb(b.flat_places)} place{'s' if b.flat_places >= 2 else ''} / logement"
    parts = []
    for lg in b.lignes:
        if lg.destination and lg.destination != "collectif":
            continue
        pmin, pmax = lg.pieces_min, lg.pieces_max
        if pmin and pmax and pmin != pmax:
            lab = f"T{pmin}–T{pmax}"
        elif pmin and pmax and pmin == pmax:
            lab = f"T{pmin}"
        elif pmin and not pmax:
            lab = f"T{pmin}+"
        elif pmax and not pmin:
            lab = f"≤T{pmax}"
        else:
            lab = "logt"
        parts.append(f"{nb(lg.places)} pl. {lab}")
    return " · ".join(parts) if parts else None


def _stationnement_regimes(session, idus: list[str], type_projet: str, regles, insee: str) -> dict:
    """Les deux régimes de stationnement du mandat : la RÈGLE GÉNÉRALE du PLU (appliquée, sourcée) et,
    pour une destination L151-34, le PLAFOND NATIONAL L151-35 « sous condition d'éligibilité » (À confirmer).
    On ne préremplit jamais un ratio réduit comme s'il était la règle du PLU."""
    b = regles.stationnement
    general = {
        "mode": b.mode, "validee": b.validee,
        "ratio_par_logement": b.flat_places if b.mode == "par_logement" else None,
        "article": b.article, "page_pdf": b.page_pdf, "millesime": _plu_millesime(session, insee),
        # ETUDE-V6-4 (item 3) — lien doc officiel pour « Lire l'article » dans le bloc stationnement.
        "source_url": _plu_source_url(session, insee),
        "citation": b.citation, "applique": True,
        "etat": ("règle vérifiée" if b.validee else "document manquant — à confirmer"),
        # ETUDE-V6-3 (item 3) — la RÈGLE en clair (ex. « 1 pl. T1–T2 · 1,5 pl. T3–T4 ») pour le récap.
        "regle_courte": _regle_stationnement_courte(b),
    }
    sous_500, dist = _tcsp_sous_500m(session, idus)
    cat = _L15134.get(type_projet)
    plafond = None
    if cat:
        # L151-35 — logement aidé / senior / résidence universitaire : au plus 1 place/logt, 0,5 si < 500 m.
        ratio = _ratio_l15135(sous_500)
        plafond = {
            "categorie": cat, "reference": "L151-35", "ratio_plafond": ratio,
            "condition_tcsp_sous_500m": sous_500, "distance_tcsp_m": dist,
            "eligibilite_categorie": "À confirmer", "statut": "À confirmer",
            # le plafond L151-35 (≤ 1/logt) vise la catégorie quelle que soit la distance ; la condition
            # TCSP < 500 m ne concerne QUE l'abaissement à 0,5 (c'est lui qu'on chiffre en « capacité réduite »).
            "applicable_si_eligible": sous_500,
            "reduction_sous_500m": sous_500,
            "citation": (
                f"Code de l'urbanisme L151-35 : pour un(e) {cat}, il ne peut être exigé plus de {ratio:g} "
                f"aire de stationnement par logement"
                + (" (terrain à moins de 500 m d'un transport collectif en site propre bien desservi)" if sous_500
                   else " ; ce plafond est abaissé à 0,5 à moins de 500 m d'un tel transport")
                + " — le PLU ne s'applique que s'il est plus favorable."),
            "note": ("Le nom « " + type_projet + " » ne prouve pas l'éligibilité juridique à la catégorie "
                     "L151-34 ; à confirmer. Le ratio affiché est le plafond LÉGAL, pas une règle du PLU."),
        }
    elif type_projet == "collectif" and sous_500:
        # L151-36 — autres logements : au plus 1 place/logt, SEULEMENT à moins de 500 m d'un TCSP.
        # Au-delà de 500 m, L151-36 N'EXISTE PAS → aucun plafond national (seule la règle PLU s'applique).
        plafond = {
            "categorie": "autres logements (hors L151-34)", "reference": "L151-36",
            "ratio_plafond": 1.0,
            "condition_tcsp_sous_500m": True, "distance_tcsp_m": dist,
            "eligibilite_categorie": "catégorie de droit commun",
            "statut": "À confirmer",
            "applicable_si_eligible": True,   # L151-36 n'existe QU'À moins de 500 m (donc applicable ici)
            "reduction_sous_500m": True,
            "citation": (
                "Code de l'urbanisme L151-36 : à moins de 500 m d'un transport collectif en site propre "
                "bien desservi, il ne peut être exigé plus de 1 aire de stationnement par logement pour les "
                "logements autres que ceux de L151-34 — le PLU ne s'applique que s'il est plus favorable."),
            "note": "S'applique aux logements de droit commun (hors aidé / senior / résidence universitaire).",
        }
    return {"general": general, "plafond_national": plafond}


def stationnement_payload(session, idus: list[str], type_projet: str) -> dict:
    """ETUDE-V6 (Lot C, étape 2) — la règle de stationnement applicable, SANS lancer le moteur : règle
    générale du PLU (commune/zone/destination : unité, article, millésime, état) + plafond L151-35
    « sous condition d'éligibilité » pour les destinations L151-34. Rapide (pas de recherche)."""
    idus = [str(i).strip() for i in (idus or []) if str(i).strip()]
    if not idus:
        raise ValueError("au moins une parcelle est requise")
    if type_projet not in _TYPES_PROJET:
        raise ValueError(f"type de projet inconnu : {type_projet}")
    conv = charger_conventions()
    terrain, regles, _zone = moteur_mod._charger(session, idus, None, conv, avec_pente=False)
    mx = regles.mixite
    return {"commune": terrain.commune, "insee": terrain.insee, "zone": regles.zone,
            "type_projet": type_projet,
            "regimes": _stationnement_regimes(session, idus, type_projet, regles, terrain.insee),
            # ETUDE-V6-4 (item 5) — mixité sociale servie dès l'étape 2 (comme dans le résultat et le PDF).
            # (item 3) — lien doc officiel + millésime pour « Lire l'article » dès cette étape.
            "mixite": ({"quota_pct": mx.quota_pct, "seuil_m2": mx.seuil_m2, "article": mx.article,
                        "page_pdf": mx.page_pdf, "citation": mx.citation,
                        "source_url": _plu_source_url(session, terrain.insee),
                        "millesime": _plu_millesime(session, terrain.insee)} if mx.validee else None)}


# ------------------------------------------------------------------ ETUDE-V6-2 (Lot 4) : jauge d'enveloppe
_M2_PAR_PLACE_AERIEN = 18.0   # place + quote-part d'allée/accès (observé sur les plans aériens, Estimé)


def jauge_payload(session, idus: list[str], type_projet: str) -> dict:
    """ETUDE-V6-2 (Lot 4, étape 3) — ENVELOPPE ESTIMÉE avant le calcul, SANS lancer le moteur (rapide :
    même chargement que la règle de stationnement, sans LiDAR ni recherche). Fournit au client de quoi
    calculer en direct : enveloppe ≈ (zone d'implantation − sol du stationnement) × niveaux (hauteur PLU)
    × coef plancher. « estimable=false » si une donnée manque (zone ou hauteur) → jauge grise côté écran."""
    idus = [str(i).strip() for i in (idus or []) if str(i).strip()]
    if not idus:
        raise ValueError("au moins une parcelle est requise")
    if type_projet not in _TYPES_PROJET:
        raise ValueError(f"type de projet inconnu : {type_projet}")
    conv = charger_conventions()
    try:
        terrain, regles, _zone = moteur_mod._charger(session, idus, None, conv, avec_pente=False)
    except ValueError:
        raise
    except Exception:  # noqa: BLE001 — assiette indisponible → jauge non estimable, jamais une erreur dure
        logging.getLogger("labuse").exception("étude v6 : jauge indisponible")
        return {"estimable": False, "manquant": ["assiette"], "etiquette": "estimé",
                "note": "Assiette indisponible — enveloppe non estimable."}
    manquant: list[str] = []
    zone_m2 = round(terrain.aire_zone_m2 or 0.0, 1)
    if zone_m2 < 1.0:
        manquant.append("zone d'implantation (reculs / PPR)")
    # ETUDE-V6-7 (item 6) — la jauge compte la VRAIE FORME : une BANDE de bâtiment (profondeur hypothèse,
    # des deux côtés d'une circulation) DANS la zone, pas toute la zone (une barre ne remplit pas une zone
    # profonde). Et la capacité des places au −1 (packing géométrique réel) pour borner le sous-sol.
    bande_m2 = zone_m2
    per_niveau_ss = int(zone_m2 / conv.m2_par_place_sous_sol) if conv.m2_par_place_sous_sol else 0
    try:
        from .geometrie import Frame, scene_depuis, _footprint_sous_sol, _capacite_niveau
        import shapely
        mrr = shapely.minimum_rotated_rectangle(terrain.zone_implantation)
        xs, ys = mrr.exterior.coords.xy
        cotes = sorted({round(((xs[i + 1] - xs[i]) ** 2 + (ys[i + 1] - ys[i]) ** 2) ** 0.5, 2) for i in range(4)})
        w_zone, l_zone = (cotes[0], cotes[-1]) if len(cotes) >= 2 else (zone_m2 ** 0.5, zone_m2 ** 0.5)
        bande_prof = 2 * conv.profondeur_m + conv.retrait_inter_barre_m   # deux rangées + retrait entre barres
        bande_m2 = round(min(zone_m2, l_zone * min(w_zone, bande_prof)), 1)
        frame = Frame.depuis(terrain.zone_implantation)
        scene = scene_depuis(terrain, frame)
        per_niveau_ss = _capacite_niveau(_footprint_sous_sol(scene), conv) or per_niveau_ss
    except Exception:  # noqa: BLE001 — la jauge reste robuste (repli sur la zone entière)
        logging.getLogger("labuse").exception("étude v6 : bande/sous-sol de la jauge indisponibles")
    he = regles.hauteur_plafond
    niveaux = int(he.valeur // conv.hauteur_etage_m) if (he.validee and he.valeur) else 0
    if niveaux < 1:
        manquant.append("hauteur réglementaire")
    # places imposées par type (barème de la zone) — pour estimer le sol du stationnement aérien
    b = regles.stationnement
    places_par_type = {}
    for t, m in conv.modules.items():
        u = b.places_pour(pieces=m.pieces, sdp_m2=m.surface_m2, destination="collectif") if b.validee else None
        places_par_type[t] = float(u) if u is not None else 1.0
    return {
        "estimable": bool(zone_m2 >= 1.0 and niveaux >= 1),
        "commune": terrain.commune, "zone": regles.zone,
        "zone_implantation_m2": zone_m2,
        "niveaux": niveaux, "niveaux_label": f"R+{max(0, niveaux - 1)}",
        "coef_plancher": conv.coef_plancher_habitable,
        "m2_par_place_aerien": _M2_PAR_PLACE_AERIEN,
        # ETUDE-V6-7 (item 6) — bande de bâtiment (vraie forme) + capacité des places au −1 (borne sous-sol).
        "bande_batiment_m2": bande_m2,
        "sous_sol_places_par_niveau": per_niveau_ss,
        "places_par_type": places_par_type,
        "hauteur_egout_m": (he.valeur if he.validee else None),
        "ces_pct": (regles.emprise_ces.valeur if regles.emprise_ces.validee else None),
        # ETUDE-V6-7 (item 3) — disponibilité du sous-sol (option grisée + raison si indisponible).
        "sous_sol_dispo": _sous_sol_dispo(session, idus, terrain.insee, regles.zone),
        "manquant": manquant, "etiquette": "estimé",
        "note": ("Estimation rapide avant calcul : (zone d'implantation − sol du stationnement aérien) "
                 "× niveaux (hauteur PLU) × coef plancher. Le calcul complet affine ce chiffre."),
    }


def _sous_sol_dispo(session, idus: list[str], insee: str, zone: Optional[str]) -> dict:
    """ETUDE-V6-7 (item 3) — le sous-sol est-il possible ? Indisponible si le terrain touche un PPR en zone
    rouge (interdiction — aléa inondation/mouvement : sous-sol à proscrire) OU si le règlement de la zone
    mentionne « sous-sol » (restriction à lire) ; sinon disponible « à confirmer : géotechnique, nappe »."""
    from sqlalchemy import text
    try:
        ppr = session.execute(text(
            "SELECT count(*) FROM spatial_layers s JOIN parcels p ON ST_Intersects(s.geom_2975, p.geom_2975) "
            "WHERE p.idu = ANY(:i) AND s.kind = 'ppr' AND lower(coalesce(s.subtype,'')) IN ('interdiction','i')"
        ), {"i": idus}).scalar() or 0
    except Exception:  # noqa: BLE001
        ppr = 0
    if ppr:
        return {"disponible": False,
                "raison": "Le terrain touche un PPR en zone rouge (interdiction) : un sous-sol est à proscrire "
                          "(aléa inondation / mouvement de terrain) — à confirmer au règlement du PPR."}
    try:
        n = session.execute(text(
            "SELECT count(*) FROM plu_reglement_extrait WHERE insee = :i AND (zone = :z OR zone IS NULL) "
            "AND texte_verbatim ILIKE '%sous-sol%'"), {"i": insee, "z": zone}).scalar() or 0
    except Exception:  # noqa: BLE001
        n = 0
    if n:
        return {"disponible": False,
                "raison": f"Le règlement de la zone {zone} mentionne le sous-sol (restriction possible) — "
                          "à vérifier au PLU avant d'enterrer le stationnement."}
    return {"disponible": True,
            "raison": "À confirmer : étude géotechnique et niveau de la nappe (sous-sol a priori possible)."}


# ------------------------------------------------------------------ ETUDE-V6 (Lot D) : lotissement
def _lotissement_payload(session, idus: list[str], entree: dict) -> dict:
    """Plan de division servi pour le type « Lotissement ». Les T1–T4 saisis = hypothèses de
    constructions futures (affichées), JAMAIS le nombre de lots. ValueError → 400 (comme l'Étude)."""
    from .lotissement import etudier_lotissement

    programme = entree.get("programme")
    demande = {}
    if isinstance(programme, dict) and programme.get("mode") == "saisi":
        demande, _rep, _surf = _programme_vers_demande(programme)
    # ETUDE-V6-6 (item 3) — hypothèses du LOTISSEMENT : taille de lot visée + largeur de voirie (jamais les
    # surfaces T1–T4). Lues de `entree.hypotheses` ; entrent dans le study_id (→ même PDF).
    hyp = entree.get("hypotheses") or {}
    from .lotissement import LOT_CIBLE_M2, VOIRIE_LARGEUR_M
    lot_cible = hyp.get("lot_cible_m2")
    voirie_l = hyp.get("voirie_largeur_m")
    lot = etudier_lotissement(
        session, idus,
        lot_cible_m2=float(lot_cible) if isinstance(lot_cible, (int, float)) and lot_cible > 0 else LOT_CIBLE_M2,
        voirie_largeur_m=float(voirie_l) if isinstance(voirie_l, (int, float)) and voirie_l > 0 else VOIRIE_LARGEUR_M)
    # ETUDE-V6-6 (item 2) — 0 lot n'est jamais muet : la raison remonte comme message de l'étude.
    nb = lot["tableau_lots"]["nombre"]
    return {
        "moteur": {"livrable": "ETUDE-V6-LOTISSEMENT", "version_conventions": "lotissement-1",
                   "etiquette": "Estimé", "crs_dessin": "EPSG:2975", "crs_carte": "EPSG:4326"},
        "entrees": {"idus": idus, "commune": lot["commune"], "insee": lot["insee"], "zone": lot["zone"],
                    "type_projet": "lotissement", "objectif": "division", "programme_mode": "saisi" if demande else "propose",
                    "stationnement": "aerien", "terrain": "libere"},
        "type_projet": "lotissement",
        "study_id": _study_id(entree),
        "lotissement": lot,
        "logements_hypothese": ({"demande": demande} if demande else None),
        "statut_global": "à compléter" if nb > 0 else "aucun lot",
        "verdict": "À compléter" if nb > 0 else "Aucun lot dessinable",
        "message": lot.get("raison"),
    }


# ------------------------------------------------------------------ point d'entrée
def etudier_payload(session, entree: dict) -> dict:
    """Payload d'étude servi par l'API. `entree` = {idus, type_projet, objectif, programme,
    stationnement, terrain, hypotheses}. Lève ValueError sur entrée invalide (→ 400 côté route)."""
    idus = [str(i).strip() for i in (entree.get("idus") or []) if str(i).strip()]
    if not idus:
        raise ValueError("au moins une parcelle est requise")
    if len(idus) > 8:
        raise ValueError("8 parcelles maximum (comme l'Assemblage)")
    objectif = entree.get("objectif") or "equilibre"
    if objectif not in OBJECTIFS:
        raise ValueError(f"objectif inconnu : {objectif}")
    # ETUDE-V6 (Lot C) — 4 destinations ouvrent (ou non) un régime de stationnement réduit (L151-34/35).
    # L'implantation reste collective (le lotissement = division, Lot D) ; seul le STATIONNEMENT dépend
    # du type : le barème PLU GÉNÉRAL s'applique toujours ; un plafond national ne s'affiche que « sous
    # condition d'éligibilité ». On n'écrit jamais « 1 place/logt » comme règle du PLU si elle ne l'est pas.
    type_projet = entree.get("type_projet") or "collectif"
    if type_projet not in _TYPES_PROJET:
        raise ValueError(f"type de projet inconnu : {type_projet}")
    stationnement = entree.get("stationnement") or "aerien"
    terrain_mode = entree.get("terrain") or "libere"
    # ETUDE-V6-7 (item 3) — le sous-sol est limité à UN SEUL niveau (on retire « 2 niveaux » : une 2ᵉ nappe
    # de parking enterré n'est pas crédible sans étude géotechnique). Toute valeur reçue est ramenée à 1.
    niveaux_sous_sol = 1

    # ETUDE-V6 (Lot D) — le LOTISSEMENT n'est pas un collectif : on branche la division foncière de
    # l'assiette (division-or à la demande, pas le batch île) et on sert un plan de division, pas des
    # scénarios d'implantation. Même borne de temps (la route 30 s enveloppe cet appel) et même message.
    if type_projet == "lotissement":
        return _lotissement_payload(session, idus, entree)

    # hypothèses modifiables → conventions surchargées
    hyp = entree.get("hypotheses") or {}
    conv = charger_conventions()
    if hyp:
        conv = avec_surcharges(
            conv,
            profondeur_m=hyp.get("profondeur_m"),
            coef_plancher_habitable=hyp.get("coef_plancher_habitable"),
            surfaces=hyp.get("surfaces"),
        )

    # programme : LABUSE propose (None) ou saisi
    programme = entree.get("programme")
    demande: dict[str, int] = {}
    repartition = None
    if isinstance(programme, dict) and programme.get("mode") == "saisi":
        demande, repartition, surfaces = _programme_vers_demande(programme)
        if surfaces:                      # les surfaces saisies surchargent aussi les modules
            conv = avec_surcharges(conv, surfaces=surfaces)
        if not demande:
            raise ValueError("programme saisi vide : indiquez au moins un type et un nombre")

    # ETUDE-V6 (Lot B) — UN SEUL passage de recherche → vue historique (scenarios) + 3 variantes mandat.
    # ETUDE-V6-2 (Lot 3) — `stationnement` ∈ {aerien, sous_sol} pilote l'implantation du parking.
    scenarios, variantes, depassement, message, terrain, regles, conv, scn_max = moteur_mod.etudier_complet(
        session=session, idus=idus, objectif=objectif, conv=conv,
        programme=demande or None, repartition=repartition, max_scenarios=3,
        stationnement_mode=stationnement, niveaux_sous_sol=niveaux_sous_sol,
        type_projet=type_projet,   # DOCS-COHERENCE-1 (F6) — plafond L151-35/36 appliqué si + restrictif que le PLU
    )

    # entêtes partagés (terrain / règles / versions) — depuis le 1er scénario/variante PRÉSENT, sinon un
    # scénario vide (même terrain/règles, scène vide) : aucune 2e recherche coûteuse.
    premiere_var = next((s for _r, s, _raison in variantes if s is not None), None)
    ref_scn = (scenarios[0] if scenarios else premiere_var) \
        or moteur_mod._scenario_vide(terrain, conv, regles, objectif, [])
    sd0 = rendu_mod.scenario_dict(ref_scn)
    t = ref_scn.terrain

    # ETUDE-V6-8 (item 1) — UNE SEULE implantation : on rogne le SCÉNARIO « votre programme » à la demande du
    # client AVANT de construire la vue servie ET les planches/coupe, pour que TOUT (plan, répartition, coupe,
    # SDP, places, contrôles, SHAB) vienne du même plan rogné. Le moteur a pu dessiner jusqu'au maximum du
    # terrain ; ici on ramène à la demande exacte quand elle tient.
    if demande:
        for role, s, _raison in variantes:
            if role == "votre_programme" and s is not None:
                _appliquer_programme_au_scenario(s, demande, conv, regles)

    scenarios_pub = [_scenario_public(s, _REFS[i], conv) for i, s in enumerate(scenarios)]
    variantes_pub = [(_variante_public(role, s, terrain, conv, regles, demande) if s is not None
                      else _variante_absente(role, raison))
                     for role, s, raison in variantes]

    # ETUDE-V6-7 (item 2) — le DÉPASSEMENT parle du PLAN DESSINÉ (« votre programme »), pas d'un optimum par
    # type pris sur des scénarios différents : « tiennent » = la typologie réellement dessinée (vérité unique).
    if depassement and demande:
        _vp = next((v for v in variantes_pub if v.get("ref") == "votre_programme" and not v.get("absente")), None)
        if _vp:
            plan = _vp["programme"]["par_type"] or {}
            tiennent = {t: min(demande[t], plan.get(t, 0)) for t in demande if demande[t] > 0}
            manquent = {t: demande[t] - tiennent.get(t, 0) for t in demande if demande[t] - tiennent.get(t, 0) > 0}
            depassement = {"demande": {t: n for t, n in demande.items() if n > 0}, "tiennent": tiennent,
                           "manquent": manquent, "total_demande": sum(n for n in demande.values() if n > 0),
                           "total_tiennent": sum(plan.values())}

    # ETUDE-V6-2 (Lot 2/3) — CAPACITÉ MAXIMALE = le meilleur candidat FAISABLE de la MÊME recherche (via
    # etudier_complet, répartition de la demande) : donc ≥ toute variante dessinée, et stable (deux demandes
    # de même répartition → même maximum). Aucune 2ᵉ recherche → budget tenu (< 20 s, Saint-Denis compris).
    # + FACTEURS LIMITANTS classés par impact, le stationnement prouvé par contrefactuel « sans places »
    # (lu dans la trace de cette recherche). La demande est ensuite CONFRONTÉE à ce maximum.
    capacite_maximale = None
    facteurs_limitants: list = []
    confrontation = None
    if scn_max is not None:
        cmax = scn_max.capacite
        capacite_maximale = {
            "logements": cmax.logements, "par_type": cmax.par_type, "sdp_m2": cmax.sdp_m2,
            "niveaux": scn_max.niveaux, "niveaux_label": f"R+{max(0, scn_max.niveaux - 1)}",
            "forme": scn_max.forme, "places": cmax.places,
            "surface_stationnement_m2": cmax.surface_stationnement_m2,
            "stationnement_mode": cmax.stationnement_mode,
            # ETUDE-V6-3 (item 11) — libellé propre (l'écran préfixe « répartition … », pas de doublon).
            "repartition": ("de votre demande" if demande else "équilibrée (proposée)"),
            "note": ("Maximum de logements que le terrain accueille sous cette répartition — indépendant "
                     "du NOMBRE demandé (deux demandes de même répartition donnent le même maximum). "
                     "La demande y est ensuite confrontée."),
        }
        facteurs_limitants = moteur_mod.facteurs_limitants(
            terrain, regles, conv, scn_max, stationnement_mode=stationnement)
        if demande:
            dem_tot = sum(n for n in demande.values() if n > 0)
            cap_tot = capacite_maximale["logements"]
            confrontation = {"demande_logements": dem_tot, "capacite_maximale_logements": cap_tot,
                             "tient": dem_tot <= cap_tot, "reserve_logements": cap_tot - dem_tot}

    # IMPLANTATION-4 (planche plan masse) — UN SEUL SVG par scénario, le même à l'écran et dans le PDF,
    # DESSINÉ depuis la géométrie (contexte cadastre/bâti/voies + TN LiDAR chargé UNE fois pour l'assiette).
    # Robuste : toute panne de contexte/dessin laisse `planche_svg` vide (l'écran retombe sur le plan
    # schématique) — l'étude est toujours servie.
    paires = list(zip(scenarios_pub, scenarios)) + [(p, s) for p, (_r, s, _raison) in zip(variantes_pub, variantes) if s is not None]
    if paires:
        try:
            from labuse.tz import today_reunion
            genere_le = today_reunion().strftime("%d/%m/%Y")
        except Exception:
            genere_le = ""
        # ETUDE-V6-8 (item 2) — UN SEUL n° de document partout : la planche et la coupe portent le MÊME
        # numéro que la page 1 / le cartouche / le pied de page, dérivé du study_id (EF-<8>), pas un numéro
        # daté distinct. L'écran et le PDF affichent donc l'unique « EF-… ».
        _sid = _study_id(entree)
        numero = _sid[:11] if _sid.startswith("EF-") else planche_mod.numero_etude(idus, genere_le)
        ent_planche = {"commune": t.commune or entree.get("commune") or "",
                       "zone": ref_scn.regles.zone, "idus": idus,
                       # DOCS-COHERENCE-1 (F1) — le mode terrain pilote le dessin « supposé démoli ».
                       "terrain": entree.get("terrain") or "libere"}
        try:
            ctx = contexte_mod.charger_contexte(session, t.assiette, idus, avec_tn=True,
                                                voie_edges=t.voie_edges)
        except Exception:
            ctx = contexte_mod.Contexte()
        for pub, scn in paires:
            # ETUDE-V6-3 (item 10) — jamais de nom technique de rôle (« votre_programme ») sur la planche :
            # un scénario Pareto garde A/B/C, une variante de rôle devient « retenu ».
            ref_aff = pub["ref"] if pub["ref"] in _REFS else "retenu"
            try:
                pub["planche_svg"] = planche_mod.planche_svg(
                    scn, ctx, ref=ref_aff, genere_le=genere_le, numero=numero, entrees=ent_planche)
            except Exception:
                pub["planche_svg"] = ""
            try:
                pub["coupe_svg"] = planche_mod.coupe_svg(
                    scn, ctx, ref=ref_aff, genere_le=genere_le, numero=numero, entrees=ent_planche)
            except Exception:
                pub["coupe_svg"] = ""

    if scenarios_pub:
        statut_global = scenarios_pub[0]["statut_etude"]
    elif demande:
        statut_global = "ne tient pas"
    else:
        statut_global = "simulation impossible"

    # ETUDE-V6 (Lot B) — verdict GLOBAL de l'étude (3 libellés mandat) : sur la 1ʳᵉ variante PRÉSENTE
    # (votre programme en tête), sinon « impossible pour cause établie » si rien n'est faisable.
    verdict = next((v["verdict"] for v in variantes_pub if not v.get("absente")),
                   "Impossible pour cause établie")

    # ETUDE-V6 (Lot C) — régimes de stationnement (règle générale PLU + plafond national à confirmer),
    # et capacité SOUS le régime réduit (2ᵉ passage moteur au ratio plafonné), seulement si le plafond est
    # géographiquement applicable (< 500 m d'un TCSP) — jamais présenté comme acquis. REMISE-1 : on prend le
    # ratio ET l'article DEPUIS le régime calculé (L151-35 à 0,5 pour aidé/senior/étudiant ; L151-36 à 1
    # pour les autres), plus de 0,5 « L151-35 » codé en dur au mauvais seuil.
    stationnement_regimes = _stationnement_regimes(session, idus, type_projet, ref_scn.regles, t.insee)
    capacite_reduite = None
    pf = stationnement_regimes["plafond_national"]
    _pf_ratio = pf.get("ratio_plafond") if pf else None
    _pf_ref = pf.get("reference") if pf else None
    # on ne lance le 2ᵉ passage (coûteux) QUE si le stationnement PLAFONNE réellement la capacité —
    # sinon le régime réduit ne change rien (et on l'écrit), et l'étude reste dans le budget de 30 s.
    # ETUDE-V6-2 (Lot 2) — « le stationnement limite » n'est affirmé que PROUVÉ (contrefactuel sans places).
    stat_limitante = any(f.get("facteur", "").startswith("stationnement") and f.get("limitant")
                         for f in facteurs_limitants)
    # ETUDE-V6-2 (Lot 3) — le plafond L151-35 est un régime AÉRIEN ; en sous-sol, il est sans objet.
    if stationnement == "sous_sol":
        pf = None
    if pf and pf["applicable_si_eligible"] and _pf_ratio is not None and demande and not stat_limitante:
        capacite_reduite = {"logements": None, "places": None, "ratio_par_logement": _pf_ratio,
                            "reference": _pf_ref, "statut": "sans effet",
                            "note": "Le stationnement n'est pas le facteur limitant ici : le plafond réduit "
                                    "ne changerait pas la capacité."}
    elif pf and pf["applicable_si_eligible"] and _pf_ratio is not None and demande:
        try:
            r_sc, r_var, r_dep, _m, _ter, _reg, _cv, _smax = moteur_mod.etudier_complet(
                session=session, idus=idus, objectif=objectif, conv=conv,
                programme=demande or None, repartition=repartition, max_scenarios=1,
                stationnement_ratio=_pf_ratio)
            best = (r_sc[0] if r_sc else next((s for _r, s, _rz in r_var if s is not None), None))
            if best is not None:
                capacite_reduite = {
                    "logements": best.capacite.logements, "places": best.capacite.places,
                    "ratio_par_logement": _pf_ratio, "reference": _pf_ref,
                    "statut": "À confirmer",
                    "note": (f"Capacité SI le projet est éligible au plafond {_pf_ref} "
                             f"({_pf_ratio:g} place / logement, terrain à moins de 500 m d'un transport "
                             "collectif) — éligibilité juridique à confirmer ; la règle générale du PLU "
                             "(appliquée ci-dessus) reste la base servie."),
                }
        except Exception:  # noqa: BLE001 — la capacité réduite est un bonus, jamais bloquante
            logging.getLogger("labuse").exception("étude v6 : passage stationnement réduit impossible")

    return {
        "moteur": {"livrable": "IMPLANTATION-2",
                   "version_conventions": conv.version, "etiquette": conv.etiquette,
                   "crs_dessin": "EPSG:2975", "crs_carte": "EPSG:4326"},
        "entrees": {
            "idus": idus, "commune": t.commune, "insee": t.insee, "zone": ref_scn.regles.zone,
            "type_projet": type_projet, "objectif": objectif,
            "programme_mode": "saisi" if demande else "propose",
            "stationnement": stationnement, "terrain": terrain_mode,
            # ETUDE-V6-5 — niveau(x) de sous-sol CHOISI (1 par défaut ; sans objet en aérien).
            "niveaux_sous_sol": (niveaux_sous_sol if stationnement == "sous_sol" else None),
        },
        "regles": {
            "zone": ref_scn.regles.zone, "insee": ref_scn.regles.insee,
            # ETUDE-V6-3 (item 2) — toute règle affichée commence par « PLU de [commune] · zone [X] · … · millésime ».
            "commune": t.commune, "millesime": _plu_millesime(session, t.insee),
            # ETUDE-V6-4 (item 3) — lien doc officiel + millésime portés sur CHAQUE règle (« Lire l'article »
            # partout : étapes 1/2, stationnement, contrôles, annexe PDF).
            "source_url": _plu_source_url(session, t.insee),
            "lignes": _decore_regles(_regles_affichables(sd0),
                                     _plu_source_url(session, t.insee), _plu_millesime(session, t.insee)),
        },
        "terrain": {
            "contenance_totale_m2": sd0["terrain"]["contenance_totale_m2"],
            "aire_dessin_m2": sd0["terrain"]["aire_dessin_m2"],
            "zone_implantation_m2": sd0["terrain"]["zone_implantation_m2"],
            "aire_hors_zone_m2": sd0["terrain"]["aire_hors_zone_m2"],
            "pct_constructible": sd0["terrain"]["pct_constructible"],
            "note_constructibilite": sd0["terrain"]["note_constructibilite"],
            "has_voie": t.has_voie, "note_limites": t.note_limites,
            "contraintes": sd0["terrain"]["contraintes"],
            "ppr_rouge_m2": sd0["terrain"]["ppr_rouge_m2"],
            "ppr_bleue_m2": sd0["terrain"]["ppr_bleue_m2"],
            "pente_lidar": sd0["terrain"]["pente_lidar"],
            # DOCS-COHERENCE-1 (A4) — pente de la FICHE (RGE ALTI, parcel_terrain.pente_moy_deg) : la
            # SEULE pente affichée dans les documents (format « 9,7° (17 %) »). La pente LiDAR du profil
            # ci-dessus sert le MOTEUR (hauteur sur terrain en pente), jamais l'affichage client.
            "pente_fiche_deg": (_pfd := _pente_fiche_deg(session, idus)),
            "pente_fiche_pct": (_pente_pct(_pfd) if _pfd is not None else None),
            "parcelles": sd0["terrain"]["parcelles"],
        },
        "hypotheses": {
            "profondeur_m": conv.profondeur_m,
            "coef_plancher_habitable": conv.coef_plancher_habitable,
            "surfaces": {k: m.surface_m2 for k, m in conv.modules.items()},
            # ETUDE-V6-2 (Lot 1) — on RENVOIE les varangues saisies (le moteur ne les utilise pas, mais le
            # résultat « Votre demande » les lit du payload — source unique de ce qui a été analysé).
            "varangues": (hyp.get("varangues") or {}),
            "largeur_coursive_m": conv.largeur_coursive_m,
            "hauteur_etage_m": conv.hauteur_etage_m,
            "place_m": [conv.place_largeur_m, conv.place_longueur_m],
            "allee_largeur_m": conv.allee_largeur_m,
            "etiquette": conv.etiquette,
        },
        "study_id": _study_id(entree),
        "bilan_surfacique": _bilan_collectif(
            sd0["terrain"], next((v for v in variantes_pub if not v.get("absente")), None)),
        "programme_saisi": ({"demande": demande} if demande else None),
        "statut_global": statut_global,
        "verdict": verdict,
        "message": message,
        "scenarios": scenarios_pub,
        "variantes": variantes_pub,
        "depassement": depassement,
        "capacite_maximale": capacite_maximale,
        "facteurs_limitants": facteurs_limitants,
        # ETUDE-V6-4 (items 10/11/13) — LA phrase « ce qui limite », une seule fois : écran et PDF la lisent.
        "facteur_limitant": _facteur_limitant_phrase(
            facteurs_limitants, next((v for v in variantes_pub if not v.get("absente")), None)),
        # ETUDE-V6-4 (item 10) — en sous-sol, si c'est la hauteur qui plafonne, POURQUOI, en une phrase.
        "facteur_limitant_detail": _facteur_limitant_detail(
            _facteur_limitant_phrase(facteurs_limitants, next((v for v in variantes_pub if not v.get("absente")), None)),
            next((v for v in variantes_pub if not v.get("absente")), None)),
        "confrontation": confrontation,
        "stationnement_regimes": stationnement_regimes,
        "capacite_reduite": capacite_reduite,
        # ETUDE-V6-2 (Lot 3) — règles d'aménagement NON calibrées pour cette zone (là où elles le sont,
        # ex. UA Étang-Salé, elles passent par un contrôle vérifié et ne figurent plus ici).
        "regles_non_verifiees": _regles_non_verifiees(ref_scn.regles),
    }
