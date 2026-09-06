"""MOTEURS (Vague 4) — M15 simulateur PLU · M16 assemblage · M17 ZAN · M18 baromètre.

Doctrine inchangée : rien n'est persisté dans le scoring, tout est étiqueté (estimation /
à instruire / indicatif). Les simulations sont des recalculs À BLANC en mémoire.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

router = APIRouter(prefix="/moteurs", tags=["moteurs"])
from .. import runs


def get_db():
    from .app import get_db as _g
    yield from _g()


def _v2run(db: Session) -> str | None:
    """Run scoring v2 servi (M5.1 lot 3.1) — import différé (cycle app ↔ moteurs)."""
    from .app import _score_v2_run_id
    return _score_v2_run_id(db)


def _moteurs_cap(name: str, defaut: int) -> int:
    """M137-O — plafonds des moteurs EN CONFIG (config/moteurs.yaml), plus jamais en dur.
    Repli sur le défaut historique si la config est absente (base de test nue)."""
    try:
        from ..config import load_yaml_config
        return int(load_yaml_config("moteurs").get(name, defaut))
    except Exception:  # noqa: BLE001
        return defaut


# ───────────────────────── M15 — SIMULATEUR PLU ─────────────────────────
# « Et si cette zone AU passait en U ? » — recalcul À BLANC, JAMAIS persisté.
# Méthode (documentée, honnête) : ESTIMATION PAR ANALOGIE — la SDP estimée des parcelles AU
# = surface × ratio médian (SDP résiduelle / surface) observé sur les parcelles U de la commune
# qui ont un résiduel calculé. Périmètre V1 : une commune, un zonage à la fois.

@router.get("/simulplu/zones")
def simulplu_zones(commune: str | None = None, db: Session = Depends(get_db)) -> list[dict]:
    rows = db.execute(text("""
        SELECT sl.subtype AS zone, count(*) AS n_ilots
        FROM spatial_layers sl WHERE sl.kind = 'plu_gpu_zone' AND (CAST(:c AS text) IS NULL OR sl.commune = :c)
          AND upper(sl.subtype) LIKE 'AU%'
        GROUP BY sl.subtype ORDER BY n_ilots DESC"""), {"c": commune}).mappings().all()
    return [dict(r) for r in rows]


@router.get("/simulplu")
def simulplu(zone: str, commune: str | None = None, offset: int = Query(0, ge=0),   # FIX-C5
             db: Session = Depends(get_db)) -> dict:
    # PERF : le zonage par parcelle est DÉJÀ résolu dans les lignes de cascade du run (detail
    # « Zone PLU « X » … ») → zéro jointure spatiale (l'ancienne version : 2 min 33 s ; celle-ci < 2 s).
    ratio = db.execute(text("""
        SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY r.sdp_residuelle_m2 / NULLIF(p.surface_m2, 0))
        FROM dryrun_cascade_results cr
        JOIN parcels p ON p.id = cr.parcel_id AND (CAST(:c AS text) IS NULL OR p.commune = :c)
        JOIN parcel_residuel r ON r.parcel_id = p.id AND r.sdp_residuelle_m2 > 0
        WHERE cr.run_label = :run AND cr.layer_name = 'zonage_plu_gpu'
          AND cr.detail LIKE 'Zone PLU « U%'"""),
        {"c": commune, "run": runs.current()}).scalar() or 0.0
    # M137-O — le plafond de liste sort du DUR (config/moteurs.yaml) ; on sert AUSSI le total réel pour
    # que l'écran DISE « les N premières sur M » (un plafond muet ment — leçon M120-B).
    # PLU Lot A (pagination SOCLE) : `offset` pagine la liste (cap par page) → « Voir N de plus » jusqu'à
    # épuisement. Les TOTAUX (n_total, SDP estimée, bascules) sont calculés sur TOUT le zonage (agrégat
    # dédié) → ils restent STABLES quelle que soit la page servie (un total par page dériverait à chaque
    # « voir plus »).
    cap = _moteurs_cap("simulplu_max", 400)
    agg = db.execute(text("""
        SELECT count(*) AS n_total,
               count(*) FILTER (WHERE round(p.surface_m2) * :ratio >= 300
                                  AND s2.tier IN ('ecartee', 'a_creuser')) AS bascules,
               coalesce(round(sum(round(p.surface_m2) * :ratio)), 0) AS sdp_totale
        FROM dryrun_cascade_results cr
        JOIN parcels p ON p.id = cr.parcel_id AND (CAST(:c AS text) IS NULL OR p.commune = :c)
        LEFT JOIN parcel_p_score_v2 s2 ON s2.parcelle_id = p.idu AND s2.run_id = :v2run
        WHERE cr.run_label = :run AND cr.layer_name = 'zonage_plu_gpu'
          AND cr.detail ILIKE ('%« ' || :z || ' »%') AND p.surface_m2 >= 300"""),
        {"c": commune, "z": zone, "run": runs.current(), "v2run": _v2run(db), "ratio": float(ratio)}).mappings().one()
    n_total = int(agg["n_total"])
    rows = db.execute(text("""
        SELECT p.idu, round(p.surface_m2) AS surface_m2, s2.tier AS statut_actuel,
               s2.tier AS tier_v2, s2.rang AS rang_v2,
               (d.status IN ('exclue', 'faux_positif_probable')) AS etage0,
               ST_AsGeoJSON(ST_Transform(p.geom_2975, 4326)) AS g
        FROM dryrun_cascade_results cr
        JOIN parcels p ON p.id = cr.parcel_id AND (CAST(:c AS text) IS NULL OR p.commune = :c)
        JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = :run
        LEFT JOIN parcel_p_score_v2 s2 ON s2.parcelle_id = p.idu AND s2.run_id = :v2run
        -- M99 (périmètre point 4) : ILIKE — le seul comparateur de zone servi sensible à la casse ;
        -- la graphie GPU brute est retrouvée quelle que soit sa casse.
        WHERE cr.run_label = :run AND cr.layer_name = 'zonage_plu_gpu'
          AND cr.detail ILIKE ('%« ' || :z || ' »%') AND p.surface_m2 >= 300
        ORDER BY p.surface_m2 DESC LIMIT :cap OFFSET :off"""),
        {"c": commune, "z": zone, "run": runs.current(), "v2run": _v2run(db), "cap": cap, "off": max(0, offset)}).mappings().all()
    items = []
    for r in rows:
        sdp_est = round(float(r["surface_m2"] or 0) * float(ratio))
        # bandes du socle v2 : ≥300 m² = un signal positif s'ouvre (bascule potentielle)
        bascule = sdp_est >= 300 and r["statut_actuel"] in ("ecartee", "a_creuser")
        items.append({"idu": r["idu"], "surface_m2": r["surface_m2"], "statut_actuel": r["statut_actuel"],
                      "tier_v2": r["tier_v2"], "rang_v2": r["rang_v2"], "etage0": bool(r["etage0"]),
                      "sdp_estimee_m2": sdp_est, "bascule_potentielle": bascule,
                      "geom": json.loads(r["g"])})
    servis = max(0, offset) + len(items)
    return {
        "zone": zone, "commune": commune or "Toute l'île", "ratio_analogie": round(float(ratio), 3),
        "methode": ("SIMULATION À BLANC (rien n'est persisté) — SDP estimée par ANALOGIE : "
                    f"surface × ratio médian SDP/surface des parcelles U de {commune or 'toute l’île'} "
                    f"({round(float(ratio), 3)}). Le vrai recalcul = règlement U appliqué au moteur "
                    "de faisabilité (prochain cycle)."),
        "n_parcelles": len(items), "n_total": n_total, "cap": cap, "offset": max(0, offset),
        "tronquee": n_total > servis,
        "bascules_potentielles": int(agg["bascules"]),           # TOTAL (tout le zonage), stable
        "sdp_totale_estimee_m2": int(agg["sdp_totale"]),         # TOTAL (tout le zonage), stable
        "items": items,
    }


@router.get("/simulplu/procedures")
def simulplu_procedures(db: Session = Depends(get_db)) -> dict:
    """M137-Q — communes RÉELLEMENT en procédure PLU (radar Sudocuh via `veille_plu`, point de
    calcul UNIQUE). Sert le nom de commune CANONIQUE (tel qu'en base) afin que « Simuler → »
    préremplisse EXACTEMENT le périmètre : le registre dit « Trois-Bassins », la base « Les
    Trois-Bassins ». Aucun calcul — on LIT le radar et on joint le nom base par INSEE."""
    from .. import veille_plu as V
    items = V.communes_en_procedure()
    # nom canonique base par INSEE (table 24 lignes) — `to_regclass` évite de lever si la table
    # de contexte n'est pas matérialisée (base de test nue) : on retombe alors sur le nom registre.
    canon: dict[str, str] = {}
    if db.execute(text("SELECT to_regclass('public.commune_conso_enaf')")).scalar():
        canon = {r[0]: r[1] for r in
                 db.execute(text("SELECT insee, commune FROM commune_conso_enaf")).all()}
    for it in items:
        it["commune_radar"] = it["commune"]
        it["commune"] = canon.get(it["insee"]) or it["commune"]   # nom base = préremplissage exact
    return {"communes": items,
            "source": "Radar procédures PLU — SuDocUH (squelette) + registre curaté LABUSE"}


# ───────────────────────── M16 — ASSEMBLAGE MULTI-PARCELLES ─────────────────────────

class AssemblageIn(BaseModel):
    idus: list[str]


@router.post("/assemblage")
def assemblage(body: AssemblageIn, db: Session = Depends(get_db)) -> dict:
    from types import SimpleNamespace

    from ..assemblage import ADJ_BUFFER_M, aggregate_assiette
    from ..faisabilite.marche_commune import prix_terrain_nu_zone
    cap = _moteurs_cap("assemblage_max_parcelles", 30)   # M137-O : plafond EN CONFIG, plus jamais en dur
    demandes = [i.strip().upper() for i in body.idus if i.strip()]
    idus = demandes[:cap]
    tronquee = len(demandes) > cap                        # on le DIRA, jamais une coupe muette
    if len(idus) < 2:
        raise HTTPException(422, "Sélectionnez au moins 2 parcelles")
    # tier SERVI (parcel_p_score_v2) + étage 0 (dry-run servi) + propriétaire moral — plus de vestige
    # de matrice (opportunity_score retiré) ni de champ `statut` doublon (= tier_v2).
    rows = db.execute(text("""
        SELECT p.id, p.idu, round(p.surface_m2) AS surface_m2, p.commune,
               s2.tier AS tier_v2, s2.rang AS rang_v2,
               (d.status IN ('exclue', 'faux_positif_probable')) AS etage0,
               pm.denomination, pm.siren, pm.groupe_label
        FROM parcels p
        LEFT JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = :run
        LEFT JOIN parcel_p_score_v2 s2 ON s2.parcelle_id = p.idu AND s2.run_id = :v2run
        LEFT JOIN parcelle_personne_morale pm ON pm.idu = p.idu
        WHERE p.idu = ANY(:idus)"""), {"idus": idus, "run": runs.current(), "v2run": _v2run(db)}).mappings().all()
    if len(rows) < 2:
        raise HTTPException(404, f"{len(rows)} parcelle(s) trouvée(s) sur {len(idus)}")
    # contiguïté : graphe des adjacences (contact cadastral ADJ_BUFFER_M — MÊME seuil que la détection
    # assemblage.py, plus de 1 m ad hoc) → l'assiette est-elle d'un seul tenant ?
    ids = [r["id"] for r in rows]
    pairs = db.execute(text("""
        SELECT a.id AS a, b.id AS b FROM parcels a JOIN parcels b
          ON a.id < b.id AND ST_DWithin(a.geom_2975, b.geom_2975, :buf)
        WHERE a.id = ANY(:ids) AND b.id = ANY(:ids)"""), {"ids": ids, "buf": ADJ_BUFFER_M}).all()
    adj: dict[int, set[int]] = {i: set() for i in ids}
    for a, b in pairs:
        adj[a].add(b)
        adj[b].add(a)
    seen, stack = {ids[0]}, [ids[0]]
    while stack:
        for nb in adj[stack.pop()]:
            if nb not in seen:
                seen.add(nb)
                stack.append(nb)
    contigu = len(seen) == len(ids)
    # PRIVACY (B) : personne morale = dénomination + SIREN (public) ; particulier = JAMAIS nommé.
    def _proprio(r: dict) -> dict:
        if r["denomination"]:
            return {"type": "personne_morale", "denomination": r["denomination"],
                    "siren": r["siren"], "groupe": r["groupe_label"]}
        return {"type": "particulier"}   # aucune identité — non communiqué
    proprios = [_proprio(r) for r in rows]
    n_particuliers = sum(1 for pr in proprios if pr["type"] == "particulier")
    tous_pm = n_particuliers == 0
    owners_pm = sorted({pr["denomination"] for pr in proprios if pr["type"] == "personne_morale"})
    # #1 — LE BILAN RÉEL : capacité + bilan CUMULÉS par agrégation des fiche_payload (source unique
    # aggregate_assiette, partagée avec /assemblage/study). Plus jamais la somme frustre des résiduels.
    parcels_lite = [SimpleNamespace(id=r["id"], surface_m2=r["surface_m2"], idu=r["idu"], commune=r["commune"])
                    for r in rows]
    agg = aggregate_assiette(db, parcels_lite)
    sdp = agg["sdp_m2"]
    sdp_par = agg["sdp_par_parcelle"]
    sdp_max_seule = max(sdp_par.values()) if sdp_par else 0
    # CONNEXIONS-2 Lot 9.3 (KO-15) — le ratio de gain est calculé ET arrondi ICI (backend), à la
    # précision servie à l'écran (2 déc. : « ×1,03 », plus le « ×1,0 » trompeur d'un arrondi à 1 déc.).
    # Le pourcentage servi aussi → le front N'A PLUS À RE-DIVISER (fini les deux expressions du ratio).
    gain_ratio = round(sdp / sdp_max_seule, 2) if sdp_max_seule else None
    gain_pct = round((sdp / sdp_max_seule - 1) * 100) if sdp_max_seule else None
    # #2 — VALORISATION : prix du terrain nu de la zone (référentiel UNIQUE prix_terrain_nu_zone),
    # sur la zone dominante de l'assiette. None si hors U/AU ou pas de vente terrain.
    from collections import Counter
    zc = Counter((c, z) for c, z in agg["zones"] if c and z)
    terrain_zone = None
    zones_mixtes = len({z for _, z in zc}) > 1
    if zc:
        (commune_dom, zone_dom), _ = zc.most_common(1)[0]
        terrain_zone = prix_terrain_nu_zone(db, commune_dom, zone_dom)
    # #3 — le SCORE reste calculé mais DORMANT (jamais servi à l'écran : doctrine M120, pas de
    # « qualité N/100 »). Conservé pour un tri éventuel ; l'écran montre les FAITS qu'il agrégeait.
    sans_potentiel = sdp <= 0 or all(bool(r["etage0"]) for r in rows)
    score_dormant = 0 if sans_potentiel else round(min(100, (45 if contigu else 10)
                  + 20 * min(1, 2 / max(1, len(owners_pm) + n_particuliers))
                  + (10 if tous_pm else 0) + 25 * min(1, sdp / 3000)))
    return {
        "n": len(rows), "contigu": contigu, "surface_totale_m2": agg["surface_cumulee_m2"],
        "tronquee": tronquee, "cap": cap,
        # #1 — capacité + bilan cumulés RÉELS (fiche_payload agrégé)
        "sdp_combinee_m2": sdp, "sdp_max_seule_m2": sdp_max_seule,
        "gain_ratio": gain_ratio, "gain_pct": gain_pct,
        "logements_combine": agg["logements"], "n_chiffrables": agg["n_chiffrables"],
        "ca": agg["ca"], "charge_fonciere": agg["charge_fonciere"],
        "note_sdp": "Capacité et bilan CUMULÉS par agrégation des parcelles. À la fusion, les reculs "
                    "INTERNES disparaissent — l'assiette réelle porte GÉNÉRALEMENT PLUS que cette "
                    "estimation ; les seuils d'ensemble (mixité, pleine terre) restent à instruire.",
        # #2 — valorisation (référentiel unique prix terrain nu de zone)
        "terrain_zone_eur_m2": (terrain_zone or {}).get("eur_m2"),
        "terrain_zone_fiabilite": (terrain_zone or {}).get("fiabilite"),
        "terrain_zone_n": (terrain_zone or {}).get("n"), "zones_mixtes": zones_mixtes,
        # B — approche propriétaire (privacy)
        "proprietaires_pm": owners_pm, "n_proprietaires": len(owners_pm) + n_particuliers,
        "n_personnes_morales": len(owners_pm), "n_particuliers": n_particuliers,
        "tous_personnes_morales": tous_pm,
        # C — indivision : NON détectable en base (aucune structure de propriété physique en open data)
        "indivision_detectable": False,
        "score_assemblage": score_dormant, "sans_potentiel": sans_potentiel,
        "items": [{"idu": r["idu"], "surface_m2": r["surface_m2"], "sdp_m2": sdp_par.get(r["id"], 0),
                   "tier_v2": r["tier_v2"], "rang_v2": r["rang_v2"], "etage0": bool(r["etage0"]),
                   "proprio": pr}
                  for r, pr in zip(rows, proprios)],
    }


# OUTILS-MUSCLER-1 Lot B (B2) — les VOISINES CONTIGUËS d'une parcelle, servies à l'utilisateur
# (le moteur ST_DWithin/union-find suivait la sélection ; il la propose désormais). Premier anneau
# seulement : contact cadastral ADJ_BUFFER_M (0,5 m) sur `parcels` — le domaine public NON CADASTRÉ
# (voirie…) est absent de la table et coupe l'anneau par construction (une route > 0,5 m sépare).
# « Même propriétaire » = ÉGALITÉ DE SIREN (fichiers PM DGFiP), jamais un match par nom (doctrine
# Scan patrimoine) ; deux particuliers ne sont JAMAIS déclarés « même propriétaire » (aucune
# identité de personne physique en base — dit plutôt qu'inventé).

@router.get("/assemblage/voisines")
def assemblage_voisines(idu: str, db: Session = Depends(get_db)) -> dict:
    """Voisines contiguës (1ᵉʳ anneau) de la parcelle `idu` : surface/zonage Sourcés, SDP
    résiduelle Estimée (même grandeur que la fiche — p_model_ext_dataset à l'année de scoring),
    propriétaire sous la règle privacy de l'assemblage. Tri : même propriétaire d'abord."""
    from ..assemblage import ADJ_BUFFER_M
    from .app import _check_idu
    _check_idu(idu)
    ref = db.execute(text("SELECT p.id, pm.siren FROM parcels p "
                          "LEFT JOIN parcelle_personne_morale pm ON pm.idu = p.idu "
                          "WHERE p.idu = :i"), {"i": idu.strip().upper()}).mappings().first()
    if not ref:
        raise HTTPException(404, "Parcelle inconnue")
    # `p_model_ext_dataset` (feature store, non-ORM) peut manquer sur une base neuve — même garde
    # que models.py : la SDP est alors servie inconnue, jamais un 500.
    has_ext = bool(db.execute(text("SELECT to_regclass('p_model_ext_dataset') IS NOT NULL")).scalar())
    annee = db.execute(text("SELECT max(annee) FROM p_model_ext_dataset")).scalar() if has_ext else None
    join_ext = "LEFT JOIN p_model_ext_dataset d ON d.idu = b.idu AND d.annee = :annee" if has_ext else ""
    sdp_expr = "round(d.sdp_residuelle_m2)::int" if has_ext else "NULL::int"
    ordre = ("meme_proprietaire DESC, d.sdp_residuelle_m2 DESC NULLS LAST, b.idu" if has_ext
             else "meme_proprietaire DESC, b.idu")
    rows = db.execute(text(f"""
        SELECT b.idu, round(b.surface_m2)::int AS surface_m2,
               coalesce(z.zone_lib, z.zone_fam) AS zone,
               {sdp_expr} AS sdp_residuelle_m2,
               pm.denomination, pm.siren,
               (pm.siren IS NOT NULL AND pm.siren = CAST(:siren AS text)) AS meme_proprietaire
        FROM parcels a
        JOIN parcels b ON b.id <> a.id AND ST_DWithin(a.geom_2975, b.geom_2975, :buf)
        LEFT JOIN parcel_zone_plu z ON z.idu = b.idu
        {join_ext}
        LEFT JOIN parcelle_personne_morale pm ON pm.idu = b.idu
        WHERE a.id = :pid
        ORDER BY {ordre}"""),
        {"pid": ref["id"], "buf": ADJ_BUFFER_M, "annee": annee,
         "siren": ref["siren"]}).mappings().all()
    items = []
    for r in rows:
        d_ = dict(r)
        d_["meme_proprietaire"] = bool(r["meme_proprietaire"])
        # MÊME règle privacy que l'assemblage : PM = dénomination + SIREN ; particulier jamais nommé.
        d_["proprio"] = ({"type": "personne_morale", "denomination": r["denomination"],
                          "siren": r["siren"]} if r["denomination"] else {"type": "particulier"})
        d_.pop("denomination", None); d_.pop("siren", None)
        items.append(d_)
    return {"idu": idu.strip().upper(), "n": len(items),
            "n_meme_proprietaire": sum(1 for i in items if i["meme_proprietaire"]),
            "depart_pm": ref["siren"] is not None,   # départ = particulier → « même propriétaire » indécidable, dit à l'écran
            "items": items}


# ───────────────────────── M17 — SIMULATEUR ZAN ─────────────────────────

# Point 41 — RÈGLE D'OR : distinction Sourcé (observé) / Estimé (dérivé) stricte, caveat systématique.
_ZAN_CAVEAT = ("Estimation — cadre ZAN en réforme (loi TRACE : échéance 2031 possiblement reportée à "
               "2034). Le Schéma d'Aménagement Régional (SAR) de La Réunion n'a pas finalisé la territorialisation → règle par défaut de "
               "-50 % appliquée. À confirmer auprès des documents d'urbanisme.")
_ENAF_SOURCE = "Portail national de l'artificialisation · Cerema · Fichiers fonciers (CONSOENAF 2009-2024)"


def _zan_indicateur(db: Session, commune: str | None = None) -> list[dict]:
    """Indicateur ZAN par commune : consommé OBSERVÉ (Sourcé) + budget/reste DÉRIVÉS -50 % (Estimé).
    Aucune fabrication : uniquement les communes présentes dans commune_conso_enaf."""
    rows = db.execute(text(
        "SELECT commune, conso_2011_2021_m2 AS c1121, conso_2021_2024_m2 AS c2124, "
        "hab_2011_2021_m2 AS h1121, millesime, source_nom FROM commune_conso_enaf "
        "WHERE (CAST(:c AS text) IS NULL OR commune = :c) ORDER BY conso_2011_2021_m2 DESC NULLS LAST"),
        {"c": commune}).mappings().all()
    out = []
    for r in rows:
        c1121, c2124 = float(r["c1121"] or 0), float(r["c2124"] or 0)
        budget = c1121 / 2.0                       # règle -50 % (Estimé)
        reste = budget - c2124                     # peut être négatif (commune ayant « dépassé »)
        # audit-zan — le budget en POURCENTAGE (plus parlant que les ha bruts) : part du budget déjà
        # consommée sur 2021-24, et part restante. HÉRITE du même caveat que le reste (ESTIMÉ, -50 %) ;
        # « % restant » se lit encore plus vite comme un droit ferme → le caveat le suit à l'écran.
        pct_consomme = round(100 * c2124 / budget) if budget > 0 else None
        out.append({
            "commune": r["commune"],
            "conso_2011_2021_ha": round(c1121 / 10000, 1),          # Sourcé
            "part_habitat_pct": round(100 * float(r["h1121"] or 0) / c1121) if c1121 else None,
            "conso_2021_2024_ha": round(c2124 / 10000, 1),          # Sourcé
            "budget_2021_2031_ha": round(budget / 10000, 1),        # Estimé (-50 %)
            "reste_theorique_ha": round(reste / 10000, 1),          # Estimé (± )
            "pct_consomme": pct_consomme,                            # Estimé (% du budget estimé)
            "pct_restant": (100 - pct_consomme) if pct_consomme is not None else None,  # ± (négatif = dépassé)
            "depasse": reste < 0,
            "millesime": r["millesime"], "source": r["source_nom"],
        })
    return out


@router.get("/zan/parcelle/{idu}")
def zan_parcelle(idu: str, db: Session = Depends(get_db)) -> dict:
    """Signal ZAN PAR PARCELLE — robuste, indépendant des quotas mouvants, entièrement SOURCÉ
    (OCS-GE + Cartofriches + zonage + SRU). Déterministe, pas d'IA. `aligne` = va dans le sens du
    ZAN (densification/friche/zone U) ; `contrainte` = consomme de l'ENAF en extension (AU)."""
    p = db.execute(text("SELECT id, commune FROM parcels WHERE idu = :i"), {"i": idu}).mappings().first()
    if not p:
        raise HTTPException(404, "Parcelle inconnue")
    ocs = db.execute(text(
        "SELECT sl.subtype, sum(ST_Area(ST_Intersection(sl.geom_2975, pp.geom_2975))) AS cov "
        "FROM spatial_layers sl JOIN parcels pp ON pp.id = :pid "
        "WHERE sl.kind = 'ocs_ge' AND ST_Intersects(sl.geom_2975, pp.geom_2975) "
        "GROUP BY sl.subtype ORDER BY cov DESC LIMIT 1"), {"pid": p["id"]}).scalar()
    friche = db.execute(text(
        "SELECT EXISTS (SELECT 1 FROM spatial_layers sl JOIN parcels pp ON pp.id = :pid "
        "WHERE sl.kind = 'friche' AND ST_Intersects(sl.geom_2975, pp.geom_2975))"),
        {"pid": p["id"]}).scalar()
    zone_fam = db.execute(text("SELECT zone_fam FROM parcel_zone_plu WHERE idu = :i"),
                          {"i": idu}).scalar()
    sru = db.execute(text("SELECT statut FROM commune_contexte_sru WHERE commune = :c"),
                     {"c": p["commune"]}).scalar()
    # audit-zan #2 — OCS-GE natif (974) n'est PAS exposé en WFS : la couche `ocs_ge` est un PROXY
    # BD CARTO V5 (occupation du sol IGN), lu par le scoring. Un signal ZAN bâti dessus DOIT le dire —
    # même honnêteté que la ligne cascade de la fiche (« occupation du sol BD CARTO V5 »).
    _OCS_SRC = "occupation du sol BD CARTO V5, proxy OCS-GE"
    raisons: list[str] = []
    if ocs == "artificialise":
        raisons.append(f"Sol déjà artificialisé ({_OCS_SRC}) — densification, le sens du ZAN")
    if friche:
        raisons.append("Friche recensée (Cartofriches) — mobilisation bonifiée par la loi TRACE")
    if zone_fam == "U":
        raisons.append("Zone U (renouvellement urbain, zonage PLU)")
    aligne = ocs == "artificialise" or bool(friche) or zone_fam == "U"
    contrainte = ocs in ("naturel", "agricole") and zone_fam == "AU"
    if contrainte:
        raisons.append(f"Sol {ocs} ({_OCS_SRC}) en zone AU — extension qui consomme de l'ENAF")
    signal = "aligne" if aligne else "contrainte" if contrainte else "neutre"
    exemption_sru = None
    if sru == "carencee":
        exemption_sru = ("Commune carencée SRU — le logement social est exempté du décompte ZAN "
                         "jusqu'en 2036 (loi TRACE) : atout majeur pour un projet social.")
    ind = _zan_indicateur(db, p["commune"])
    return {"idu": idu, "commune": p["commune"], "signal": signal,
            "ocs_ge": ocs, "friche": bool(friche), "zone_fam": zone_fam,
            "raisons": raisons, "exemption_sru": exemption_sru,
            "indicateur": ind[0] if ind else None, "caveat": _ZAN_CAVEAT}


@router.get("/zan")
def zan(db: Session = Depends(get_db)) -> dict:
    communes = db.execute(text("""
        SELECT sl.commune, count(*) FILTER (WHERE sl.subtype = 'artificialise') AS ilots_artif,
               round(sum(ST_Area(sl.geom_2975)) FILTER (WHERE sl.subtype = 'artificialise') / 10000) AS ha_artif,
               round(sum(ST_Area(sl.geom_2975)) / 10000) AS ha_couverts
        FROM spatial_layers sl WHERE sl.kind = 'ocs_ge' AND sl.commune IS NOT NULL
        GROUP BY sl.commune ORDER BY ha_artif DESC NULLS LAST"""), ).mappings().all()
    # parcelles « ZAN-compatibles » : artificialisées NON bâties, promues (bonus ocs_ge > 0 au run)
    rows = db.execute(text("""
        SELECT p.idu, round(p.surface_m2) AS surface_m2, s2.tier AS statut, d.opportunity_score,
               s2.tier AS tier_v2, s2.rang AS rang_v2,
               (d.status IN ('exclue', 'faux_positif_probable')) AS etage0,
               ST_AsGeoJSON(ST_Transform(p.geom_2975, 4326)) AS g
        FROM dryrun_cascade_results cr
        JOIN parcels p ON p.id = cr.parcel_id
        JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = :run
        LEFT JOIN parcel_p_score_v2 s2 ON s2.parcelle_id = p.idu AND s2.run_id = :v2run
        WHERE cr.run_label = :run AND cr.layer_name = 'ocs_ge' AND cr.weight_applied > 0
          AND s2.tier IN ('brulante', 'chaude', 'reserve_fonciere', 'a_creuser')
        ORDER BY d.opportunity_score DESC LIMIT 400"""), {"run": runs.current(), "v2run": _v2run(db)}).mappings().all()
    return {
        "bandeau": ("Signal parcelle robuste (OCS-GE + friches + zonage) + consommation ENAF OBSERVÉE "
                    "par commune. Le budget/reste ZAN est une ESTIMATION (règle -50 %) — pas un droit "
                    "à construire ferme. Construire sur de l'artificialisé = zéro dette ZAN."),
        "caveat": _ZAN_CAVEAT, "source_conso": _ENAF_SOURCE,
        "indicateurs": _zan_indicateur(db),   # consommé Sourcé + budget/reste Estimé, par commune
        "communes": [dict(r) for r in communes],
        "zan_compatibles": [{**{k: r[k] for k in ("idu", "surface_m2", "statut", "opportunity_score")},
                             "tier_v2": r["tier_v2"], "rang_v2": r["rang_v2"], "etage0": bool(r["etage0"]),
                             "geom": json.loads(r["g"])} for r in rows],
    }


# ───────────────────────── M18 — BAROMÈTRE FONCIER ─────────────────────────

#: Critère P1-03 (M6 Phase 2a) : une mutation n'entre dans le Baromètre — médianes ET
#: volumes affichés — que si elle est une VENTE au sens strict. Voir `_barometre_data`.
#: P2-48 — ÉCART ASSUMÉ avec le bilan (`faisabilite.bilan._trim_aberrants`) : là, le €/m² est
#: planché à 1000 (échantillon de comparables robuste). Ici, plancher €/m² lâche à 100 (garde-fou
#: anti-ratio-aberrant) + filtre absolu `valeur_fonciere > 1000` : on OBSERVE tout le marché, on
#: n'en sélectionne pas un sous-échantillon fiable. Les deux planchers sont voulus, pas à aligner.
_BAROMETRE_RETENUE = """nature_mutation = 'Vente'
                 AND valeur_fonciere > 1000
                 AND valeur_fonciere / NULLIF(surface_reelle_bati, 0) BETWEEN 100 AND 12000"""


def prix_ancien_communes(db: Session, min_ventes: int = 100) -> dict[str, dict]:
    """SOURCE UNIQUE du « €/m² ancien » PAR COMMUNE (médiane DVF des ventes strictes `_BAROMETRE_RETENUE`,
    ≥ `min_ventes`). LUE par le tableau Communes (comparateur) ET le Rapport PDF (baromètre) → un seul
    chiffre par commune dans tout le produit, plus une formule recopiée. À NE PAS confondre avec le
    `sector_price` parcellaire de la fiche (marche_service, EXPORTS-1) : celui-là est un AUTRE métrique —
    des comparables au RAYON d'une parcelle (valorisation), pas un baromètre commune-entière.
    None (< min_ventes) → « — » à l'écran, jamais un zéro inventé."""
    rows = db.execute(text(f"""
        SELECT commune, count(*) AS n,
               round(percentile_cont(0.5) WITHIN GROUP (
                 ORDER BY valeur_fonciere / NULLIF(surface_reelle_bati, 0)))::int AS median
        FROM dvf_mutations WHERE {_BAROMETRE_RETENUE}
        GROUP BY commune HAVING count(*) >= :mv"""), {"mv": min_ventes}).mappings().all()
    return {r["commune"]: {"median": r["median"], "n": int(r["n"])} for r in rows}


def _marque_partiel(serie: list[dict], vol_key: str = "mutations") -> None:
    """§1a VÉRACITÉ — un trimestre partiel (délai de publication DVF) ne doit PAS s'afficher comme
    une barre courte muette (baisse artificielle en fin de série). Règle : le trimestre le PLUS
    RÉCENT (serie[0], la liste est DESC) est marqué `partiel` si son volume < 60 % de la MÉDIANE des
    4 trimestres précédents. Le front le grise et dit « données partielles (délai DVF) »."""
    if len(serie) < 2:
        return
    for r in serie:
        r["partiel"] = False
    precedents = sorted(int(x[vol_key] or 0) for x in serie[1:5])
    if precedents:
        n = len(precedents)
        med = precedents[n // 2] if n % 2 else (precedents[n // 2 - 1] + precedents[n // 2]) / 2
        if med > 0 and int(serie[0][vol_key] or 0) < 0.6 * med:
            serie[0]["partiel"] = True


def _tendance_pct(serie: list[dict], med_key: str) -> int | None:
    """Tendance en % : dernier trimestre COMPLET vs le MÊME trimestre un an avant (glissement annuel,
    neutralise la saisonnalité). None si l'un manque. On saute un dernier trimestre partiel."""
    pts = [r for r in serie if not r.get("partiel")]   # DESC ; on ignore le partiel en tête
    if len(pts) < 5:
        return None
    dernier, an_avant = pts[0], pts[4]                 # 4 trimestres = 1 an
    a, b = dernier.get(med_key), an_avant.get(med_key)
    return round(100 * (a - b) / b) if (a and b) else None


def _barometre_data(db: Session, insee: str | None = None) -> dict:
    """Baromètre foncier M18 — séries DVF et Sitadel (JSON + PDF marketing).

    RETOURS-11F M13 (O15) — `insee` optionnel : île entière (défaut) OU une commune. Les tables
    DVF/Sitadel portent le NOM de commune (dvf_mutations, sitadel_permits) ou l'INSEE
    (dvf_mutations_parcelle) → on résout le nom une fois et on filtre les trois séries de façon
    cohérente ; le neuf de la commune vient du moteur unique M1 (`neuf_vefa_commune`).

    Critère outliers (P1-03, audit M6 §1.1b BLOC B) — appliqué aux MÉDIANES ET AUX
    VOLUMES (`_BAROMETRE_RETENUE`) ; avant P1-03 les volumes n'avaient AUCUN filtre :

    - ``nature_mutation = 'Vente'`` : écarte la VEFA (du neuf — comparable à part, pas
      la même série de prix que l'ancien : médiane VEFA ~4 700-5 300 €/m² contre ~2 800
      servis), les adjudications, échanges, expropriations et « vente terrain à bâtir »
      (hors-objet d'une médiane €/m² bâti) ;
    - ``valeur_fonciere > 1000`` € : prix symboliques — donations déguisées, apports,
      régularisations (211 mutations ≤ 1 € au grain source, 31 ≤ 1 000 € dans la table).
      Seuil 1 000 € retenu car (a) déjà la convention du module marché (`dvf_marche.py`,
      « ventes à 1 € symbolique écartées ») et (b) creux net de la distribution : 18
      mutations ≤ 100 €, 13 entre 100 et 1 000 €, puis reprise (77 entre 1 et 5 k€) —
      aucun bien bâti réel ne se vend sous 1 000 € ;
    - ``€/m² ∈ [100, 12 000]`` : garde-fou historique contre les ratios aberrants
      (surfaces mal agrégées résiduelles). La cause principale — lignes d'un même local
      répétées par nature de culture et SOMMÉES (1 440 surfaces ×2,6) — est corrigée à
      la racine dans `_geo_dvf_aggregate` (layers_ingest.py) + re-fabrication SQL
      `reports/m6-audit/sql/p1_03_dvf_surfaces_fix.sql` (rollback fourni).

    Transparence : chaque trimestre porte `ecartees` (mutations hors critère) et le
    payload global `ecartees` ventile la fenêtre entière — « médiane sur N ventes,
    M écartées (VEFA, prix symboliques…) ».
    """
    # RETOURS-11F M13 — résolution du nom de commune (tables DVF/Sitadel portent le nom) une seule fois.
    nom = None
    if insee:
        nom = db.execute(text("SELECT commune FROM parcels WHERE left(idu, 5) = :i LIMIT 1"),
                         {"i": insee}).scalar()
    par = {"nom": nom, "insee": insee}
    dvf = db.execute(text(f"""
        SELECT to_char(date_trunc('quarter', date_mutation), 'YYYY"T"Q') AS trimestre,
               count(*) FILTER (WHERE {_BAROMETRE_RETENUE}) AS mutations,
               (count(*) - count(*) FILTER (WHERE {_BAROMETRE_RETENUE}))::int AS ecartees,
               round(percentile_cont(0.5) WITHIN GROUP (
                 ORDER BY valeur_fonciere / NULLIF(surface_reelle_bati, 0))
                 FILTER (WHERE {_BAROMETRE_RETENUE}))::int AS median_eur_m2_bati
        FROM dvf_mutations WHERE date_mutation IS NOT NULL
          AND date_trunc('quarter', date_mutation) < date_trunc('quarter', CURRENT_DATE)
          AND (CAST(:nom AS text) IS NULL OR commune = :nom)
        GROUP BY 1 ORDER BY 1 DESC LIMIT 8"""), par).mappings().all()
    permis = db.execute(text("""
        SELECT to_char(date_trunc('quarter', date), 'YYYY"T"Q') AS trimestre, count(*) AS permis
        FROM sitadel_permits WHERE date_trunc('quarter', date) < date_trunc('quarter', CURRENT_DATE)
          AND (CAST(:nom AS text) IS NULL OR commune = :nom)
        GROUP BY 1 ORDER BY 1 DESC LIMIT 8"""), par).mappings().all()
    # §2 — SÉRIE TERRAIN NU par trimestre (dvf_mutations_parcelle, ventes terrain, €/m² dédupliqué
    # par mutation comme ligne2_terrain_zone : val / terrain TOTAL de la mutation, jamais val÷un-bout).
    # Échantillon robuste (~600-770 ventes/trim) — contrairement à la VEFA (neuf), trop rare pour une série.
    terrain = db.execute(text("""
        WITH parc AS (
          SELECT DISTINCT m.id_mutation, m.id_parcelle, m.valeur_fonciere AS val, m.date_mutation AS dm,
                 max(COALESCE(m.surface_terrain, 0)) OVER (PARTITION BY m.id_mutation, m.id_parcelle) AS terr_parc
          FROM dvf_mutations_parcelle m
          WHERE m.nature_mutation = 'Vente' AND COALESCE(m.surface_reelle_bati, 0) = 0 AND m.surface_terrain > 0
            AND m.valeur_fonciere > 1000 AND m.date_mutation IS NOT NULL
            AND date_trunc('quarter', m.date_mutation) < date_trunc('quarter', CURRENT_DATE)
            AND (CAST(:insee AS text) IS NULL OR m.code_commune = :insee)),
        tot AS (SELECT id_mutation, sum(terr_parc) AS terr_tot, max(val) AS val, max(dm) AS dm
                FROM parc GROUP BY id_mutation)
        SELECT to_char(date_trunc('quarter', dm), 'YYYY"T"Q') AS trimestre, count(*) AS mutations,
               round(percentile_cont(0.5) WITHIN GROUP (ORDER BY val / NULLIF(terr_tot, 0)))::int AS median_eur_m2_terrain
        FROM tot WHERE terr_tot > 0 AND val / NULLIF(terr_tot, 0) BETWEEN 5 AND 5000
        GROUP BY 1 ORDER BY 1 DESC LIMIT 8"""), par).mappings().all()
    # §2 — NEUF : PAS de série (VEFA DVF trop rare : 0-4 ventes/trim récents → une courbe sur 2 points
    # mentirait). On sert la RÉFÉRENCE actuelle. Île : dvf_prix_sortie_neuf. Commune : le moteur UNIQUE
    # M1 (`neuf_vefa_commune`, même chiffre que la fiche/la table Communes/la carte).
    if insee:
        from ..ingestion.dvf_marche import neuf_vefa_commune
        _nv = neuf_vefa_commune(db, insee)
        neuf_ref = ({"prix_m2_neuf": _nv["mediane_prix_m2_bati"], "n": _nv["n"]}
                    if _nv.get("mediane_prix_m2_bati") is not None else None)
    else:
        neuf_ref = db.execute(text(
            "SELECT prix_m2_neuf, n FROM dvf_prix_sortie_neuf WHERE niveau = 'ile' LIMIT 1")).mappings().first()
    # M137-Z — le plafond du classement prix sort du DUR (config/moteurs.yaml). §1b — le « prix par
    # commune » du PDF lit la SOURCE UNIQUE `prix_ancien_communes` (la même que le tableau Communes) :
    # un seul chiffre par commune dans tout le produit, plus une 2ᵉ requête qui pourrait dériver.
    cap = _moteurs_cap("barometre_top_communes", 8)
    pa = prix_ancien_communes(db)                       # {commune: {median, n}} — ≥ 100 ventes
    top_ordonne = sorted(pa.items(), key=lambda kv: (kv[1]["median"] is not None, kv[1]["median"]), reverse=True)
    top_communes = [{"commune": c, "mutations": v["n"], "median_eur_m2": v["median"]} for c, v in top_ordonne[:cap]]
    n_communes = len(pa)
    ecartees = db.execute(text(f"""
        SELECT (count(*) - count(*) FILTER (WHERE {_BAROMETRE_RETENUE}))::int AS total,
               count(*) FILTER (WHERE nature_mutation = 'Vente en l''état futur d''achèvement')::int AS vefa,
               count(*) FILTER (WHERE nature_mutation NOT IN
                 ('Vente', 'Vente en l''état futur d''achèvement'))::int AS autres_natures,
               count(*) FILTER (WHERE nature_mutation = 'Vente'
                 AND (valeur_fonciere IS NULL OR valeur_fonciere <= 1000))::int AS prix_symboliques,
               count(*) FILTER (WHERE nature_mutation = 'Vente' AND valeur_fonciere > 1000
                 AND (surface_reelle_bati IS NULL OR surface_reelle_bati <= 0
                      OR valeur_fonciere / NULLIF(surface_reelle_bati, 0)
                         NOT BETWEEN 100 AND 12000))::int AS ratio_hors_bande
        FROM dvf_mutations WHERE (CAST(:nom AS text) IS NULL OR commune = :nom)"""),
        par).mappings().one()
    # listes MUTABLES (RowMapping = lecture seule) pour poser `partiel` + calculer la tendance YoY.
    dvf_l = [dict(r) for r in dvf]
    terrain_l = [dict(r) for r in terrain]
    permis_l = [dict(r) for r in permis]
    for s in (dvf_l, terrain_l, permis_l):
        _marque_partiel(s, "mutations" if s is not permis_l else "permis")
    return {"perimetre": (f"{nom} (DVF communal, Sitadel)" if nom
                          else "île entière (24 communes DVF, flux Sitadel régional)"),
            "commune": nom, "insee": insee,   # RETOURS-11F M13 — écho du filtre pour le sélecteur front
            "criteres": ("Ventes strictes uniquement (P1-03) : nature 'Vente', prix > 1 000 €, "
                         "€/m² bâti dans [100, 12 000] — médianes ET volumes. Écartées : VEFA (neuf), "
                         "adjudications/échanges/expropriations, prix symboliques, ratios aberrants."),
            # §2 — TROIS séries (ancien bâti, terrain nu) + neuf en RÉFÉRENCE (VEFA trop rare pour une série).
            "dvf_trimestres": dvf_l, "terrain_trimestres": terrain_l, "permis_trimestres": permis_l,
            "tendance_ancien_pct": _tendance_pct(dvf_l, "median_eur_m2_bati"),
            "tendance_terrain_pct": _tendance_pct(terrain_l, "median_eur_m2_terrain"),
            "tendance_permis_pct": _tendance_pct(permis_l, "permis"),
            "neuf_reference": ({"prix_m2_neuf": neuf_ref["prix_m2_neuf"], "n": neuf_ref["n"]} if neuf_ref else None),
            "top_communes_prix": [{k: r[k] for k in ("commune", "mutations", "median_eur_m2")} for r in top_communes],
            # M137-Z — le plafond DIT, jamais muet : « les N premières sur M » (les M ont la donnée).
            "top_communes_cap": cap, "top_communes_total": n_communes,
            "top_communes_tronquee": n_communes > len(top_communes),
            "ecartees": dict(ecartees)}


@router.get("/barometre")
def barometre(insee: str | None = Query(None, min_length=5, max_length=5),
              db: Session = Depends(get_db)) -> dict:
    """RETOURS-11F M13 (O15) — `insee` optionnel : île entière (défaut) ou une commune (sélecteur)."""
    return _barometre_data(db, insee=insee)


@router.get("/marche/{commune}")
def marche_commune(commune: str, db: Session = Depends(get_db)) -> dict:
    """M-U — bloc « Marché » par commune (9 lignes Sourcées, chacune avec sa date amont). Point de
    calcul unique lu par l'outil, la fiche et market_signal. Auth standard + rail rate-limité /moteurs."""
    from ..faisabilite.marche_commune import build_marche_commune
    return build_marche_commune(db, commune)


# M141 Partie 1 — l'export PDF du baromètre est RETIRÉ (décision Vic : le baromètre n'a pas
# vocation à sortir en PDF). La route `GET /barometre.pdf` et son générateur fpdf (self-contained :
# imports fpdf/pdf_premium locaux, helpers internes) sont supprimés en entier — aucun code mort.
# L'onglet « Évolution » du hub Communes reste inchangé à l'écran (données via `GET /barometre`).
