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

from math import gcd
from typing import Any, Optional

from shapely.geometry import mapping

from labuse.geo import to_4326

from . import contexte as contexte_mod
from . import moteur as moteur_mod
from . import planche as planche_mod
from . import rendu as rendu_mod
from .conventions import avec_surcharges, charger as charger_conventions
from .controles import ECHOUE, NON_APPLICABLE, NON_EFFECTUE, REUSSI

OBJECTIFS = {"equilibre", "plus_logements", "plus_surface", "plus_simple"}
TYPES_LOGEMENT = ("T2", "T3", "T4")
_REFS = ["A", "B", "C"]


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
    c = {REUSSI: 0, ECHOUE: 0, NON_EFFECTUE: 0, NON_APPLICABLE: 0}
    for ct in controles:
        if ct.resultat in c:
            c[ct.resultat] += 1
    return {"reussi": c[REUSSI], "echoue": c[ECHOUE],
            "non_effectue": c[NON_EFFECTUE], "non_applicable": c[NON_APPLICABLE]}


def _scenario_public(scenario, ref: str) -> dict:
    """Vue servie d'un scénario : résumé (3 chiffres clés), sections repliables, contrôles, GeoJSON."""
    cap = scenario.capacite
    sd = rendu_mod.scenario_dict(scenario)
    controles = sd["controles_reglementaires"]
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
        "controles_compte": _compte_controles(scenario.controles),
        "programme": {
            "par_type": cap.par_type,
            "shab_par_type_m2": cap.shab_par_type_m2,
            "shab_estimee_m2": cap.shab_estimee_m2,
            "ratio_shab_sdp": cap.ratio_shab_sdp,
            "mixite_applicable": cap.mixite_applicable,
            "logements_aides_imposes": cap.logements_aides_imposes,
            "sdp_aidee_imposee_m2": cap.sdp_aidee_imposee_m2,
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
        },
        "surfaces_mesurees_m2": sd["tableau_capacite"]["surfaces_mesurees_m2"],
        "emprise_sol_m2": cap.emprise_sol_m2,
        "pleine_terre_m2": cap.pleine_terre_m2,
        "controles": controles,
        "checks_geometriques": sd["controles_geometriques"],
        "geojson": _geojson_scenario(scenario),
    }


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
    repartition: list[str] = []
    for t in TYPES_LOGEMENT:            # ordre stable T2, T3, T4
        repartition += [t] * (demande[t] // g) if t in demande else []
    return demande, repartition, surfaces


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
    type_projet = entree.get("type_projet") or "collectif"
    if type_projet != "collectif":
        raise ValueError("seul le collectif est actif dans cette version")
    stationnement = entree.get("stationnement") or "aerien"
    terrain_mode = entree.get("terrain") or "libere"

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

    scenarios, message, terrain, regles, conv = moteur_mod.etudier_multi(
        session=session, idus=idus, objectif=objectif, conv=conv,
        programme=demande or None, repartition=repartition, max_scenarios=3,
    )

    # entêtes partagés (terrain / règles / versions) — depuis le 1er scénario, sinon un scénario vide
    # (même terrain/règles, scène vide) : aucune 2e recherche coûteuse.
    ref_scn = scenarios[0] if scenarios else moteur_mod._scenario_vide(
        terrain, conv, regles, objectif, [])
    sd0 = rendu_mod.scenario_dict(ref_scn)
    t = ref_scn.terrain

    scenarios_pub = [_scenario_public(s, _REFS[i]) for i, s in enumerate(scenarios)]

    # IMPLANTATION-4 (planche plan masse) — UN SEUL SVG par scénario, le même à l'écran et dans le PDF,
    # DESSINÉ depuis la géométrie (contexte cadastre/bâti/voies + TN LiDAR chargé UNE fois pour l'assiette).
    # Robuste : toute panne de contexte/dessin laisse `planche_svg` vide (l'écran retombe sur le plan
    # schématique) — l'étude est toujours servie.
    if scenarios_pub:
        try:
            from labuse.tz import today_reunion
            genere_le = today_reunion().strftime("%d/%m/%Y")
        except Exception:
            genere_le = ""
        numero = planche_mod.numero_etude(idus, genere_le)
        ent_planche = {"commune": t.commune, "zone": ref_scn.regles.zone, "idus": idus}
        try:
            ctx = contexte_mod.charger_contexte(session, t.assiette, idus, avec_tn=True)
        except Exception:
            ctx = contexte_mod.Contexte()
        for pub, scn in zip(scenarios_pub, scenarios):
            try:
                pub["planche_svg"] = planche_mod.planche_svg(
                    scn, ctx, ref=pub["ref"], genere_le=genere_le, numero=numero, entrees=ent_planche)
            except Exception:
                pub["planche_svg"] = ""

    if scenarios_pub:
        statut_global = scenarios_pub[0]["statut_etude"]
    elif demande:
        statut_global = "ne tient pas"
    else:
        statut_global = "simulation impossible"

    return {
        "moteur": {"livrable": "IMPLANTATION-2",
                   "version_conventions": conv.version, "etiquette": conv.etiquette,
                   "crs_dessin": "EPSG:2975", "crs_carte": "EPSG:4326"},
        "entrees": {
            "idus": idus, "commune": t.commune, "insee": t.insee, "zone": ref_scn.regles.zone,
            "type_projet": type_projet, "objectif": objectif,
            "programme_mode": "saisi" if demande else "propose",
            "stationnement": stationnement, "terrain": terrain_mode,
        },
        "regles": {
            "zone": ref_scn.regles.zone, "insee": ref_scn.regles.insee,
            "lignes": _regles_affichables(sd0),
        },
        "terrain": {
            "contenance_totale_m2": sd0["terrain"]["contenance_totale_m2"],
            "aire_dessin_m2": sd0["terrain"]["aire_dessin_m2"],
            "zone_implantation_m2": sd0["terrain"]["zone_implantation_m2"],
            "has_voie": t.has_voie, "note_limites": t.note_limites,
            "contraintes": sd0["terrain"]["contraintes"],
            "ppr_rouge_m2": sd0["terrain"]["ppr_rouge_m2"],
            "ppr_bleue_m2": sd0["terrain"]["ppr_bleue_m2"],
            "pente_lidar": sd0["terrain"]["pente_lidar"],
            "parcelles": sd0["terrain"]["parcelles"],
        },
        "hypotheses": {
            "profondeur_m": conv.profondeur_m,
            "coef_plancher_habitable": conv.coef_plancher_habitable,
            "surfaces": {k: m.surface_m2 for k, m in conv.modules.items()},
            "largeur_coursive_m": conv.largeur_coursive_m,
            "hauteur_etage_m": conv.hauteur_etage_m,
            "place_m": [conv.place_largeur_m, conv.place_longueur_m],
            "allee_largeur_m": conv.allee_largeur_m,
            "etiquette": conv.etiquette,
        },
        "programme_saisi": ({"demande": demande} if demande else None),
        "statut_global": statut_global,
        "message": message,
        "scenarios": scenarios_pub,
    }
