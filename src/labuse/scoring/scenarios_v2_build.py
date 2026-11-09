"""ALGO-FIX-1 — adaptateur : des caches réels vers le `ScenarioRecord` du moteur V2.

Ce module est la SEULE frontière entre le moteur pur (`scenarios_v2`, aucun SIG) et les données du
dépôt. Il LIT (jamais n'écrit) les caches du run servi et construit, par parcelle, un
`ScenarioRecord` normalisé :

  · conservation — R = SDP résiduelle (cache `parcel_residuel`, déjà servie) ;
  · reconstruction — C_rebuild = `sdp_max` et E = `sdp_existante`, calculés LIVE par le moteur de
    faisabilité (`compute_residuel`) quand `enrich=True` (seul chemin qui expose C et E séparément,
    y compris pour les parcelles saturées où D_net est négatif) ;
  · pente / forme / accès / AU — lus de la même requête d'entrées que le Score V1 (`_ENTREES_SQL`) ;
  · Signal — RELAYÉ depuis `score_labuse` (D6, spec §12) : probabilité servie, niveau servi, état
    « évalué / non évalué » ; jamais recalculé ;
  · diagnostic géométrique de `terrain_exigu` (D5, spec §9.3) : constats SANS règle de taille.

Aucune écriture, aucun nouveau run : la V2 se calcule EN PARALLÈLE du service (spec §14.4), à
partir de l'instantané servi.
"""
from __future__ import annotations

import math

from sqlalchemy import text
from sqlalchemy.orm import Session

from . import scenarios_v2 as v2
from . import score_labuse as sl
from .. import runs

# Lecture conjointe : entrées de score (résiduel + pente/aire/périmètre/accès/AU) ET état Signal
# servi (score_labuse). Une ligne par parcelle de la sélection.
_SIGNAL_SQL = text("""
SELECT parcel_id, idu, commune, bande, score, cause,
       signal_p, signal_niveau, cascade_exclue, cascade_motifs,
       sdp_residuelle_m2
FROM score_labuse
WHERE run_label = :run AND parcel_id = ANY(:ids)
""")

# Métriques géométriques pour le diagnostic de `terrain_exigu` (D5). AUCUN seuil de taille : on
# mesure validité, multipolygone et compacité (4πA/P²) — une forme très découpée (ravines,
# concavités) a une compacité faible, d'où un contour utile potentiellement vidé par les reculs.
_GEOM_SQL = text("""
SELECT p.id,
       ST_IsValid(p.geom_2975)                                   AS valide,
       ST_NumGeometries(p.geom_2975)                             AS n_geom,
       ST_Area(p.geom_2975)                                      AS aire,
       ST_Perimeter(p.geom_2975)                                 AS perim
FROM parcels p WHERE p.id = ANY(:ids)
""")


def _diagnostic_geometrie(g: dict) -> dict:
    """Constats géométriques (spec §9.3). Distingue le DÉFAUT DUR (géométrie invalide — à traiter
    quelle que soit la cause) des simples INDICES d'investigation (multipolygone, faible compacité)
    qui ne sont PAS des preuves d'erreur (avis Astra §4). Ne conclut jamais « terrain trop étroit »
    d'une taille, et n'affirme aucun retrait vérifié."""
    constats, invalide = [], False
    if g.get("valide") is False:
        constats.append("Géométrie invalide (auto-intersection ou anneau incohérent) — à traiter.")
        invalide = True
    if (g.get("n_geom") or 1) > 1:
        constats.append(f"Multipolygone ({g['n_geom']} composantes) : indice (emprise fragmentée), "
                        "pas une preuve d'erreur.")
    aire, perim = g.get("aire"), g.get("perim")
    if aire and perim and perim > 0:
        compacite = 4 * math.pi * aire / (perim * perim)       # 1 = disque ; →0 = très découpé
        g["compacite"] = round(compacite, 3)
        if compacite < 0.25:
            constats.append(f"Contour très découpé (compacité {compacite:.2f}) : indice, pas une "
                            "preuve que l'assiette utile soit vidée.")
    return {"constats": constats, "invalide": invalide, "compacite": g.get("compacite")}


def _signal_state(row: dict) -> dict:
    """État du Signal servi, relayé (D6). Jamais de probabilité fabriquée."""
    p = row.get("signal_p")
    if p is not None:
        return {"signal_status": "AVAILABLE", "signal_p": float(p),
                "signal_niveau": row.get("signal_niveau"), "signal_reason": "PROBABILITE_SERVIE"}
    if row.get("cascade_exclue"):
        return {"signal_status": "NOT_AVAILABLE", "signal_p": None, "signal_niveau": None,
                "signal_reason": "ECARTEE_ETAGE_0"}
    return {"signal_status": "NOT_AVAILABLE", "signal_p": None, "signal_niveau": None,
            "signal_reason": "SIGNAL_NON_CALCULE"}


def _eligibilite(cause: str | None, cascade_exclue: bool, cascade_motifs) -> dict:
    """Traduit la cause brute du moteur + l'exclusion dure de cascade en champs d'éligibilité /
    horizon / hauteur du `ScenarioRecord`, selon la taxonomie §5.1 et les décisions Vic D3.

    Une famille de zone seule n'est jamais une preuve (spec §5.1) ; mais le verdict
    `zone_non_constructible:<zone>` du moteur EST le règlement opposable appliqué à l'assiette
    (ALGO.md §3.3, Vic D3 « Hors projet : zone A/N … avec la preuve »). De même une exclusion dure
    de cascade (route, DPF, forêt publique, cœur de Parc, PPR rouge total) est une preuve sourcée."""
    out = {"eligibility": "allowed", "horizon": "now", "height_status": "present",
           "geometry_status": "valid", "eligibility_proof": None, "cause_engine": cause}
    c = cause or ""
    # §5.1 étape 1 AVANT l'étape 2 : une anomalie géométrique critique (surface incohérente
    # plan≠cadastre) l'emporte sur toute preuve d'incompatibilité — « une intersection sur une
    # géométrie douteuse ne devient pas une preuve certaine » (spec §5.1).
    if c == "surface_incertaine":
        out.update(geometry_status="suspect")
        return out
    if cascade_exclue:
        motifs = cascade_motifs if isinstance(cascade_motifs, list) else []
        out.update(eligibility="incompatible",
                   eligibility_proof={"verified": True, "rule": "exclusion dure de la cascade",
                                      "source": "cascade v2", "portion": "entière",
                                      "motifs": motifs})
        return out
    if c.startswith("zone_non_constructible"):
        zone = c.split(":", 1)[1] if ":" in c else None
        out.update(eligibility="incompatible",
                   eligibility_proof={"verified": True,
                                      "rule": f"zone {zone or ''} inconstructible au PLU".strip(),
                                      "source": "PLU / GPU", "portion": "entière", "zone": zone})
        return out
    if c.startswith("habitat_interdit"):
        zone = c.split(":", 1)[1] if ":" in c else None
        out.update(eligibility="incompatible",
                   eligibility_proof={"verified": True,
                                      "rule": f"habitat interdit en zone {zone or ''}".strip(),
                                      "source": "règlement PLU", "portion": "entière", "zone": zone})
        return out
    if c == "redhibitoire":
        # Rédhibitoire SANS exclusion dure sourcée : on ne conclut pas « hors projet » à l'aveugle.
        out.update(eligibility="unknown")
        return out
    if c.startswith(("zone_non_resolue", "regle_plu_non_validee")) or c in ("hors_plu", "indetermine"):
        out.update(eligibility="unknown")           # ignorance → À vérifier (spec §8.1)
        return out
    if c == "hauteur_indispo":
        out.update(height_status="missing")
        return out
    return out


def _contraintes_partielles(motifs) -> dict:
    """Extrait des motifs de cascade les contraintes rédhibitoires PARTIELLES (spec §9.2) : PPR
    rouge, EBC, pente forte. Sert (a) aux points de vigilance, (b) à décider si une assiette de
    repli (`residuel_legacy`) est douteuse parce qu'elle n'a pas découpé ces portions."""
    out = {"ppr_rouge_pct": None, "ebc": False, "pente_forte_pct": None}
    if not isinstance(motifs, list):
        return out
    for m in motifs:
        if not isinstance(m, dict):
            continue
        layer, detail, res, pct = (m.get("layer"), m.get("detail") or "",
                                   m.get("result"), m.get("recouvrement_pct"))
        if layer == "risques" and ("rouge" in detail or res == "HARD_EXCLUDE"):
            if pct is not None:
                out["ppr_rouge_pct"] = max(out["ppr_rouge_pct"] or 0, pct)
        if layer == "prescription_plu" and ("boisé" in detail or "EBC" in detail):
            out["ebc"] = True
        if layer == "pente" and pct is not None:
            out["pente_forte_pct"] = max(out["pente_forte_pct"] or 0, pct)
    return out


def record_from_rows(sig: dict, ent: dict | None, geom: dict | None,
                     residuel: dict | None = None, assiette_source: str | None = None,
                     zone_parts: list | None = None) -> tuple[v2.ScenarioRecord, str]:
    """Construit un `ScenarioRecord` (+ bande V1 servie, pour la comparaison avant/après) depuis :
      · `sig`   — ligne `score_labuse` (Signal servi, cascade, bande V1) ;
      · `ent`   — ligne d'entrées de score (pente, aire, périmètre, accès, AU, cause résiduel) ;
      · `geom`  — métriques géométriques (diagnostic D5) ;
      · `residuel` — dict `compute_residuel` LIVE (C, E) si enrichi, sinon None ;
      · `assiette_source` — 'gabarit' (découpé) / 'residuel_legacy' (repli) ;
      · `zone_parts` — portions de zone [{zone, fam, pct}] (zone_dominante), si disponibles.
    """
    notes: list[str] = []
    contr = _contraintes_partielles(sig.get("cascade_motifs"))
    au_classe = (ent or {}).get("au_classe")      # parcel_au_statut.classe (hors run)

    # ── PROVENANCE UNIQUE (avis Astra §5.B / P2) : cause, assiette et quantités du MÊME calcul ──
    # Enrichi ⇒ tout vient du calcul LIVE `compute_residuel` (jamais mélangé au cache). Rapide ⇒
    # tout vient du cache servi. Le drapeau `prov` tracé est servi au résultat.
    C = E = None
    if residuel is not None and residuel.get("disponible"):
        C = residuel.get("sdp_max_m2")
        E = residuel.get("sdp_existante_m2")
        R = residuel.get("sdp_residuelle_m2")
        cause = None
        eff_assiette = residuel.get("assiette_source")
        prov = "live"
    elif residuel is not None:                    # live mais non constructible
        cause = residuel.get("cause")
        R = residuel.get("sdp_ecrite")
        eff_assiette = residuel.get("assiette_source") or assiette_source
        prov = "live"
    else:                                         # cache servi
        cause = (ent or {}).get("cause") if ent else sig.get("cause")
        R = (ent or {}).get("sdp") if ent else sig.get("sdp_residuelle_m2")
        eff_assiette = assiette_source
        prov = "cache"

    el = _eligibilite(cause, bool(sig.get("cascade_exclue")), sig.get("cascade_motifs"))

    # Portion productive (spec §9.2 / D9) : parts CONSTRUCTIBLES (U/AU) ; surface = pct × aire.
    aire = (ent or geom or {}).get("aire")
    zp, prod_fam = None, None
    if zone_parts:
        zp = [{"zone": p.get("zone"), "fam": p.get("fam"),
               "area_m2": round((p.get("pct") or 0) / 100.0 * (aire or 0)),
               "constructible": (p.get("fam") in ("U", "AU"))}
              for p in zone_parts]
        constr = [p for p in zp if p["constructible"] and p["area_m2"]]
        if constr:
            prod_fam = max(constr, key=lambda p: p["area_m2"])["fam"]

    # ── HORIZON (avis Astra §4/§3 — P4/P5) ──────────────────────────────────────────────────────
    #  · `declasse_au_fermee` (AU fermée établie) → À différer.
    #  · `declasse_au_statut_inconnu` → horizon INCONNU (jamais « À différer » ; reste à vérifier).
    #  · capacité portée par une portion AU SANS régime établi (pas de `parcel_au_statut`, ouverture
    #    / OAP / conditions d'équipement non prouvées) → horizon INCONNU (cas EH0043).
    horizon = el["horizon"]
    future = None
    if au_classe == "declasse_au_fermee":
        horizon = "deferred"
        future = C if C is not None else R
    elif au_classe == "declasse_au_statut_inconnu":
        horizon = "unknown"
    elif prod_fam == "AU" and not au_classe and horizon == "now":
        horizon = "unknown"
        notes.append("La capacité repose sur une portion AU (à urbaniser) dont le régime (ouverture, "
                     "OAP, conditions d'équipement) n'est pas établi — disponibilité actuelle à vérifier.")

    # ── GÉOMÉTRIE : un défaut DUR (invalide) est traité QUELLE QUE SOIT la cause (P4) ───────────
    geometry_status = el["geometry_status"]
    diagnostic = _diagnostic_geometrie(geom) if geom is not None else None
    if diagnostic and diagnostic["invalide"]:
        geometry_status = "suspect"

    # ── terrain_exigu : assiette non obtenue → calcul douteux. Métriques = INDICES, jamais une
    # affirmation de retraits vérifiés ; on ne force pas R à 0 (P4, avis Astra §4). ──────────────
    calc_reliable, calc_doubt = True, None
    if cause == "terrain_exigu":
        calc_reliable = False
        calc_doubt = ("Assiette non obtenue par le moteur (terrain exigu) — métriques géométriques "
                      "indicatives ; les retraits ne sont pas tracés, surface productive à confirmer.")

    if cause == "capacite_nulle" and C is None:
        C = 0.0

    # ── Contraintes partielles (spec §9.2) — vigilances SOURCÉES, SANS prétendre connaître le
    # découpage réel (P4, avis Astra §3.2 : aucun texte « découpé/soustrait » dérivé du nom du
    # chemin ; on signale la PRÉSENCE de la contrainte, l'assiette nette restant à vérifier). ────
    if contr["ppr_rouge_pct"]:
        notes.append(f"PPR zone rouge présent sur ~{round(contr['ppr_rouge_pct'])} % de la parcelle "
                     "(aléa rédhibitoire) — assiette nette de la portion productive à vérifier.")
    if contr["ebc"]:
        notes.append("Espace boisé classé (EBC) présent — emprise boisée inconstructible ; part dans "
                     "la portion productive à vérifier.")
    if contr["pente_forte_pct"] and contr["pente_forte_pct"] >= 30:
        notes.append(f"Pente forte signalée (~{round(contr['pente_forte_pct'])} % en cascade) — "
                     "difficulté physique, pas une exclusion ; à rapprocher de la pente moyenne du Score.")

    # ── Legacy (P3, avis Astra §2) : TOUTE capacité d'assiette de repli NON QUALIFIÉE est À
    # VÉRIFIER (chiffre provisoire consultable). L'absence de PPR/EBC dans les motifs ne prouve PAS
    # que le repli est correct ; seule une assiette `gabarit` (ou une version qualifiée) qualifie. ─
    if eff_assiette == "residuel_legacy" and (R or 0) > 0 and calc_reliable:
        calc_reliable = False
        calc_doubt = ("Assiette calculée par un chemin de repli non qualifié (`residuel_legacy`) — "
                      "capacité provisoire à confirmer (version et opérations réellement appliquées "
                      "non établies ici).")

    rec = v2.ScenarioRecord(
        id=sig["idu"],
        area_m2=aire,
        perimeter_m=(ent or geom or {}).get("perim"),
        geometry_status=geometry_status,
        capacity_rebuild_m2=C,
        existing_m2=E,
        residual_m2=float(R) if R is not None else None,
        eligibility=el["eligibility"],
        eligibility_proof=el["eligibility_proof"],
        horizon=horizon,
        future_capacity_m2=float(future) if future is not None else None,
        height_status=el["height_status"],
        height_required=True,
        slope_deg=(ent or {}).get("pente_moy_deg"),
        access=(ent or {}).get("acces"),
        access_known=(ent is not None and (ent or {}).get("acces") is not None),
        built_coverage_pct=(ent or {}).get("emp"),
        calc_reliable=calc_reliable,
        calc_doubt_reason=calc_doubt,
        zone_main=(zone_parts[0].get("zone") if zone_parts else None),
        zone_parts=zp,
        capacity_estimated=bool((ent or {}).get("capacite_estimee")),
        cause_engine=cause,
        diagnostic=diagnostic,
        notes=notes,
        provenance=prov,
        assiette_source=eff_assiette,
        **_signal_state(sig))
    return rec, (sig.get("bande") or "")


_ASSIETTE_SQL = text(
    "SELECT parcel_id, assiette_source FROM parcel_residuel WHERE parcel_id = ANY(:ids)")


def records_for_parcels(session: Session, parcel_ids: list[int], *, run_label: str | None = None,
                        cascade_label: str | None = None, enrich: bool = False,
                        with_zone: bool | None = None
                        ) -> list[tuple[v2.ScenarioRecord, str]]:
    """Construit les `ScenarioRecord` d'une liste de parcelles pour le run servi. `enrich=True`
    calcule C/E live (reconstruction exacte, ~80 ms/parcelle). `with_zone` (défaut = enrich) ajoute
    la portion productive (zone_dominante, une requête par parcelle). Renvoie [(record, bande_v1)]."""
    run_label = run_label or runs.current()
    cascade_label = cascade_label or runs.cascade()
    with_zone = enrich if with_zone is None else with_zone
    if not parcel_ids:
        return []
    sig_rows = {r._mapping["parcel_id"]: dict(r._mapping)
                for r in session.execute(_SIGNAL_SQL, {"run": run_label, "ids": parcel_ids})}
    ent_rows = {r._mapping["id"]: dict(r._mapping)
                for r in session.execute(sl._ENTREES_SQL, {"ids": parcel_ids, "clabel": cascade_label})}
    geom_rows = {r._mapping["id"]: dict(r._mapping)
                 for r in session.execute(_GEOM_SQL, {"ids": parcel_ids})}
    assiette = {r._mapping["parcel_id"]: r._mapping["assiette_source"]
                for r in session.execute(_ASSIETTE_SQL, {"ids": parcel_ids})}
    residuel = {}
    if enrich:
        from ..faisabilite.residuel import compute_residuel
        for pid in parcel_ids:
            try:
                residuel[pid] = compute_residuel(session, pid)
            except Exception:
                residuel[pid] = None
    zones = {}
    if with_zone:
        from ..faisabilite.zone_servie import zone_dominante
        for pid in parcel_ids:
            try:
                zones[pid] = zone_dominante(session, pid).parts
            except Exception:
                zones[pid] = None
    out = []
    for pid in parcel_ids:
        sig = sig_rows.get(pid)
        if sig is None:
            continue
        out.append(record_from_rows(sig, ent_rows.get(pid), geom_rows.get(pid), residuel.get(pid),
                                    assiette_source=assiette.get(pid), zone_parts=zones.get(pid)))
    return out


def _result_to_dict(res) -> dict:
    """Contrat de sortie par parcelle (D9, spec §11.1) : statut + cause, bande + score, quantités,
    points de vigilance, portion productive, Signal et son état."""
    return {
        "idu": res.id,
        "statut": res.status,
        "libelle": res.label,
        "ton": res.tone,
        "cause": res.cause_codes,
        "bande": res.band,
        "score": res.score,
        "bande_provisoire": res.band_provisional,
        "horizon": res.horizon,
        "quantites": res.quantities,
        "bornes": res.bounds,
        "vigilance": res.vigilance,
        "zone_productive": res.zone_portion,
        "signal": {k: res.signal.get(k) for k in ("status", "p", "niveau", "label", "reason")},
        "tri_valeur": res.rank_value,
        "details": res.details,
    }


def analyse_scenarios_payload(session: Session, parcel_ids: list[int], *, mode: str = "potential",
                              scenario: str = "keep", sort: str | None = None,
                              run_label: str | None = None, enrich: bool = False,
                              limit: int = 100, offset: int = 0,
                              as_of: str | None = None) -> dict:
    """Réponse d'analyse V2 pour une sélection : versions (spec §2.2), effectifs par statut et par
    bande sur TOUTE la sélection (spec §2.1 — tous les statuts dans les comptes), et la page
    courante de parcelles triée (spec §10). LECTURE SEULE."""
    run_label = run_label or runs.current()
    from . import score_labuse as sl
    _, score_version = sl.charger_bareme()
    opts = {"mode": mode, "scenario": scenario}
    if sort:
        opts["sort"] = sort

    records = [rec for rec, _ in records_for_parcels(session, parcel_ids, run_label=run_label,
                                                      enrich=enrich)]
    rows = v2.order(records, opts)
    eff = v2.effectifs(rows)
    page = rows[offset:offset + limit]
    return {
        "analysis_version": v2.VERSION,
        "scenario_engine_version": score_version,       # barème/coefficients réutilisés (gravés)
        "signal_recette": "q_v15",                       # modèle gelé relayé (D6) — jamais recalculé
        "signal_run": run_label,
        "run_servi": run_label,
        "mode": mode, "scenario": scenario, "sort": opts.get("sort"),
        "as_of": as_of,
        "n_selection": eff["n"],
        "effectifs": {"par_statut": eff["par_statut"], "par_bande": eff["par_bande"]},
        "page": {"limit": limit, "offset": offset, "n": len(page)},
        "parcelles": [_result_to_dict(r) for r in page],
    }


def parcel_ids_for_commune(session: Session, commune: str, run_label: str | None = None) -> list[int]:
    run_label = run_label or runs.current()
    rows = session.execute(
        text("SELECT parcel_id FROM score_labuse WHERE run_label = :run AND commune = :c "
             "ORDER BY idu"), {"run": run_label, "c": commune})
    return [r[0] for r in rows]
