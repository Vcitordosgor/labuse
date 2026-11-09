"""ALGO-FIX-1 (suite) — PERSISTANCE des scénarios V2 par le CALCUL DU RUN.

Le résultat de scénario (statut, cause, bande, score, C, E, C_rebuild, D_net, R, portion
productive, vigilances) est ÉCRIT par un batch dans une table de run DÉDIÉE
`parcel_scenario_v2_runs` — jamais calculé à la volée par l'endpoint, qui se contente de LIRE. Le
Signal reste INTACT (relayé à la lecture depuis `score_labuse`, pas stocké ici).

Deux modes d'écriture :
  · `enrich=True`  — C et E viennent du moteur de faisabilité (`compute_residuel`, ≈ 80 ms/parcelle) :
    reconstruction EXACTE (C_rebuild, D_net signé), y compris sur les parcelles saturées. Écrit les
    DEUX scénarios (conservation + reconstruction).
  · `enrich=False` — rapide (caches seuls) : écrit la CONSERVATION exacte (R caché) + le STATUT de
    reconstruction (dérivable sans la magnitude de C), en laissant les quantités de reconstruction
    à `enriched=false` (à chiffrer au run de nuit). Permet de peupler toute l'île pour l'endpoint.

Table ADDITIVE : aucune table historique n'est touchée (spec §12/§14).
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from . import scenarios_v2 as v2
from . import scenarios_v2_build as build
from .. import runs

DDL = """
CREATE TABLE IF NOT EXISTS parcel_scenario_v2_runs (
  run_label             text    NOT NULL,
  parcel_id             integer NOT NULL,
  idu                   text,
  commune               text,
  scenario              text    NOT NULL,            -- 'keep' | 'rebuild'
  status                text,
  cause                 jsonb,
  band                  text,
  score                 integer,
  band_provisional      text,
  additional_m2         integer,                     -- R (conservation)
  project_total_m2      integer,                     -- C_rebuild
  existing_m2           integer,                     -- E
  net_signed_m2         integer,                     -- D_net signé
  conditional_future_m2 integer,
  residual_m2           integer,
  zone_prod_zone        text,
  zone_prod_area_m2     integer,
  vigilance             jsonb,
  bande_v1              text,                         -- bande servie (comparaison avant/après)
  enriched              boolean NOT NULL DEFAULT false,
  provenance            text,                         -- 'live' | 'cache' (P2 : provenance unique)
  assiette_source       text,                         -- 'gabarit' | 'residuel_legacy', même calcul
  analysis_version      text,
  score_version         text,                         -- version du barème ENREGISTRÉE avec le résultat
  cascade_label         text,                         -- run cascade servi au calcul
  surface_m2            integer,                       -- surface terrain (tri area, P3)
  enrich_state          text,                          -- not_requested/ok/failed (par parcelle, P2)
  computed_at           timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (run_label, parcel_id, scenario)
);
CREATE INDEX IF NOT EXISTS parcel_scenario_v2_commune
  ON parcel_scenario_v2_runs (run_label, commune, scenario);
ALTER TABLE parcel_scenario_v2_runs ADD COLUMN IF NOT EXISTS provenance text;
ALTER TABLE parcel_scenario_v2_runs ADD COLUMN IF NOT EXISTS assiette_source text;
ALTER TABLE parcel_scenario_v2_runs ADD COLUMN IF NOT EXISTS score_version text;
ALTER TABLE parcel_scenario_v2_runs ADD COLUMN IF NOT EXISTS cascade_label text;
ALTER TABLE parcel_scenario_v2_runs ADD COLUMN IF NOT EXISTS surface_m2 integer;
ALTER TABLE parcel_scenario_v2_runs ADD COLUMN IF NOT EXISTS enrich_state text;
"""

_UPSERT = text("""
INSERT INTO parcel_scenario_v2_runs
  (run_label, parcel_id, idu, commune, scenario, status, cause, band, score, band_provisional,
   additional_m2, project_total_m2, existing_m2, net_signed_m2, conditional_future_m2, residual_m2,
   zone_prod_zone, zone_prod_area_m2, vigilance, bande_v1, enriched, provenance, assiette_source,
   analysis_version, score_version, cascade_label, surface_m2, enrich_state)
VALUES
  (:run,:pid,:idu,:commune,:scn,:status,:cause,:band,:score,:bandp,
   :add,:ptot,:exist,:net,:fut,:res,:zz,:za,:vig,:v1,:enr,:prov,:asrc,:ver,:sver,:clabel,:surf,:estate)
ON CONFLICT (run_label, parcel_id, scenario) DO UPDATE SET
  idu=EXCLUDED.idu, commune=EXCLUDED.commune, status=EXCLUDED.status, cause=EXCLUDED.cause,
  band=EXCLUDED.band, score=EXCLUDED.score, band_provisional=EXCLUDED.band_provisional,
  additional_m2=EXCLUDED.additional_m2, project_total_m2=EXCLUDED.project_total_m2,
  existing_m2=EXCLUDED.existing_m2, net_signed_m2=EXCLUDED.net_signed_m2,
  conditional_future_m2=EXCLUDED.conditional_future_m2, residual_m2=EXCLUDED.residual_m2,
  zone_prod_zone=EXCLUDED.zone_prod_zone, zone_prod_area_m2=EXCLUDED.zone_prod_area_m2,
  vigilance=EXCLUDED.vigilance, bande_v1=EXCLUDED.bande_v1, enriched=EXCLUDED.enriched,
  provenance=EXCLUDED.provenance, assiette_source=EXCLUDED.assiette_source,
  analysis_version=EXCLUDED.analysis_version, score_version=EXCLUDED.score_version,
  cascade_label=EXCLUDED.cascade_label, surface_m2=EXCLUDED.surface_m2,
  enrich_state=EXCLUDED.enrich_state, computed_at=now()
""")


def ensure_table(session: Session) -> None:
    for stmt in DDL.strip().split(";\n"):
        if stmt.strip():
            session.execute(text(stmt))
    session.commit()


def _as_int(x):
    return None if x is None or not v2._finite(x) else round(x)


def _rebuild_statut_sans_C(rec: v2.ScenarioRecord, keep_res) -> str:
    """Statut de RECONSTRUCTION sans la magnitude de C_rebuild (mode rapide). On ne DÉDUIT JAMAIS
    « Capacité estimée » sans C/E/D_net calculés (avis Astra §5.A / P1) : tout statut qui exigerait
    C passe en « Calcul à compléter » (COMPUTE_PENDING), distinct des problèmes de données.
    Les statuts définitifs SANS C (hors projet, à vérifier, à différer, préétude, et le zéro
    réglementaire `capacite_nulle`) sont conservés."""
    if keep_res.status in ("OUTSIDE_OBJECTIVE", "TO_VERIFY", "DEFERRED", "PRESTUDY"):
        return keep_res.status
    if keep_res.status == "NO_MARGIN" and rec.cause_engine == "capacite_nulle":
        return "NO_MARGIN"
    return "COMPUTE_PENDING"       # ESTIMATED / NO_MARGIN-saturé : capacité à chiffrer


def _tone(status):
    return ("green" if status == "ESTIMATED" else "blue" if status == "PRESTUDY"
            else "amber" if status in ("TO_VERIFY", "DEFERRED", "COMPUTE_PENDING") else "neutral")


def _row(run_label, pid, rec, bande_v1, res, scenario, enriched, score_version, cascade_label,
         surface=None):
    q = res.quantities
    zp = res.zone_portion or {}
    import json
    return {
        "run": run_label, "pid": pid, "idu": rec.id, "commune": None, "scn": scenario,
        "status": res.status, "cause": json.dumps(res.cause_codes), "band": res.band,
        "score": res.score, "bandp": res.band_provisional,
        "add": _as_int(q["additional"]), "ptot": _as_int(q["project_total"]),
        "exist": _as_int(q["existing"]), "net": _as_int(q["net_signed"]),
        "fut": _as_int(q["conditional_future"]), "res": _as_int(rec.residual_m2),
        "zz": zp.get("zone"), "za": _as_int(zp.get("area_m2")),
        "vig": json.dumps(res.vigilance, ensure_ascii=False), "v1": bande_v1,
        "enr": enriched, "prov": rec.provenance, "asrc": rec.assiette_source,
        "ver": v2.VERSION, "sver": score_version, "clabel": cascade_label,
        "surf": _as_int(surface), "estate": rec.enrich_state}


def compute_scenarios_v2_batch(session: Session, parcel_ids: list[int], *,
                               run_label: str | None = None, enrich: bool = False,
                               chunk: int = 2000, log=None) -> dict:
    """Calcule et PERSISTE les scénarios V2 pour `parcel_ids`. Écrit la conservation (exacte) pour
    tous ; la reconstruction EXACTE si `enrich`, sinon son seul STATUT (quantités à `enriched=false`).
    Idempotent (upsert). Renvoie un petit bilan."""
    run_label = run_label or runs.current()
    ensure_table(session)
    from . import score_labuse as sl
    _, score_version = sl.charger_bareme()
    cascade_label = runs.cascade()
    bilan = {"parcelles": 0, "keep": 0, "rebuild": 0, "enriched": enrich}
    commune_by_id = {}
    for i in range(0, len(parcel_ids), chunk):
        lot = parcel_ids[i:i + chunk]
        recs = build.records_for_parcels(session, lot, run_label=run_label, enrich=enrich,
                                          with_zone=enrich)
        # commune + surface par parcelle (une requête groupée par lot)
        surface_by_id = {}
        for r in session.execute(text("SELECT id, commune, ST_Area(geom_2975) FROM parcels "
                                      "WHERE id = ANY(:i)"), {"i": lot}):
            commune_by_id[r[0]] = r[1]
            surface_by_id[r[0]] = r[2]
        id_by_idu = {}
        for r in session.execute(text("SELECT idu, id FROM parcels WHERE id = ANY(:i)"), {"i": lot}):
            id_by_idu[r[0]] = r[1]
        rows = []
        for rec, v1 in recs:
            pid = id_by_idu.get(rec.id)
            if pid is None:
                continue
            surf = surface_by_id.get(pid)
            # `enriched` est désormais PAR PARCELLE : vrai seulement si le calcul live a réussi (P2).
            enr_ok = enrich and rec.enrich_state == "ok"
            keep = v2.evaluate(rec, {"mode": "potential", "scenario": "keep"})
            rk = _row(run_label, pid, rec, v1, keep, "keep", enr_ok, score_version, cascade_label, surf)
            rk["commune"] = commune_by_id.get(pid)
            rows.append(rk)
            bilan["keep"] += 1
            if enrich and rec.enrich_state == "ok":
                reb = v2.evaluate(rec, {"mode": "potential", "scenario": "rebuild"})
                rr = _row(run_label, pid, rec, v1, reb, "rebuild", True, score_version, cascade_label, surf)
            else:
                # Statut de reconstruction SANS chiffrer C : « Calcul à compléter » si C est requis
                # (P1) — jamais « Capacité estimée » déduite. Quantités/bande nulles, cause distincte.
                reb = v2.evaluate(rec, {"mode": "potential", "scenario": "keep"})  # base statut
                reb.status = _rebuild_statut_sans_C(rec, keep)
                if reb.status == "COMPUTE_PENDING":
                    reb.cause_codes = ["RECONSTRUCTION_NON_CHIFFREE"]
                    reb.band = None
                    reb.band_provisional = None
                    reb.quantities = {k: None for k in reb.quantities}
                rr = _row(run_label, pid, rec, v1, reb, "rebuild", False, score_version,
                          cascade_label, surf)
            rr["commune"] = commune_by_id.get(pid)
            rows.append(rr)
            bilan["rebuild"] += 1
            bilan["parcelles"] += 1
        session.execute(_UPSERT, rows)
        session.commit()
        if log:
            log(f"{min(i + chunk, len(parcel_ids))}/{len(parcel_ids)} parcelles persistées")
    return bilan


# ── lecture (l'endpoint LIT, ne calcule pas) ─────────────────────────────────
_READ_SQL = text("""
SELECT s.idu, s.status, s.cause, s.band, s.score, s.band_provisional,
       s.additional_m2, s.project_total_m2, s.existing_m2, s.net_signed_m2,
       s.conditional_future_m2, s.residual_m2, s.zone_prod_zone, s.zone_prod_area_m2,
       s.vigilance, s.bande_v1, s.enriched, s.surface_m2, s.enrich_state, s.analysis_version,
       sl.signal_p, sl.signal_niveau, sl.cascade_exclue
FROM parcel_scenario_v2_runs s
LEFT JOIN score_labuse sl ON sl.run_label = s.run_label AND sl.idu = s.idu
WHERE s.run_label = :run AND s.scenario = :scn AND {where}
ORDER BY s.idu
""")

# Signal (état interne) → état de la vue Prospection, IDENTIQUE au moteur pur (contrat unique, P3).
_SALE_STATE = {"AVAILABLE": "SIGNAL_AVAILABLE", "TO_VERIFY": "SIGNAL_TO_VERIFY",
               "NOT_AVAILABLE": "SIGNAL_NOT_AVAILABLE", "OUT_OF_SCOPE": "SIGNAL_OUT_OF_SCOPE"}


def _filtre(commune, idus):
    """Clause SQL de sélection : commune ET IDU en INTERSECTION (jamais l'un OU l'autre — P6)."""
    clauses, params = [], {}
    if commune:
        clauses.append("s.commune = :c")
        params["c"] = commune
    if idus:
        clauses.append("s.idu = ANY(:i)")
        params["i"] = list(idus)
    return (" AND ".join(clauses) if clauses else "TRUE"), params


def _signal_persiste(p, niveau, cascade_exclue) -> dict:
    """Signal servi RELAYÉ, MÊME validation ET MÊME état que le moteur pur (avis Astra passe-3 §6) :
    une valeur hors [0,1], NaN ou infinie donne l'état `TO_VERIFY` (comme le moteur pur), jamais
    « disponible », jamais en tête de classement."""
    if p is None:
        return {"status": "NOT_AVAILABLE", "p": None, "niveau": None,
                "reason": "ECARTEE_ETAGE_0" if cascade_exclue else "SIGNAL_NON_CALCULE"}
    if not v2._finite(p) or p < 0 or p > 1:
        return {"status": "TO_VERIFY", "p": None, "niveau": None,
                "reason": "PROBABILITE_SERVIE_INVALIDE"}
    return {"status": "AVAILABLE", "p": p, "niveau": niveau, "reason": "PROBABILITE_SERVIE"}


def read_scenarios(session: Session, *, run_label: str, scenario: str,
                   commune: str | None = None, idus: list[str] | None = None) -> list[dict]:
    """LIT les scénarios persistés (+ relaie le Signal servi, validé). Aucun calcul. Sélection =
    commune ∩ IDU (P6)."""
    where, params = _filtre(commune, idus)
    params.update({"run": run_label, "scn": scenario})
    sql = text(str(_READ_SQL).replace("{where}", where))
    out = []
    for r in session.execute(sql, params):
        m = r._mapping
        out.append({
            "idu": m["idu"], "statut": m["status"], "cause": m["cause"], "bande": m["band"],
            "score": m["score"], "bande_provisoire": m["band_provisional"],
            "quantites": {"additional": m["additional_m2"], "project_total": m["project_total_m2"],
                          "existing": m["existing_m2"], "net_signed": m["net_signed_m2"],
                          "conditional_future": m["conditional_future_m2"]},
            "residual_m2": m["residual_m2"], "surface_m2": m["surface_m2"],
            "zone_productive": ({"zone": m["zone_prod_zone"], "area_m2": m["zone_prod_area_m2"]}
                                if m["zone_prod_zone"] else None),
            "vigilance": m["vigilance"], "bande_v1": m["bande_v1"],
            "quantites_calculees": m["enriched"], "etat_calcul": m["enrich_state"],
            "analysis_version": m["analysis_version"],
            "signal": _signal_persiste(m["signal_p"], m["signal_niveau"], m["cascade_exclue"]),
        })
    return out


def _rank_value(row: dict, scenario: str, sort: str) -> float | None:
    q = row["quantites"]
    if sort == "id":
        return None                                          # tri par IDU seul
    if sort == "area":
        return row.get("surface_m2")                         # surface persistée (P3)
    if row["statut"] == "DEFERRED":
        return None
    if scenario == "rebuild":
        return q["net_signed"] if sort == "gain" else q["project_total"]
    return q["additional"]


def _trier(rows: list[dict], *, mode: str, scenario: str, sort: str) -> list[dict]:
    """Tri déterministe D10 appliqué aux lignes LUES. `sort=id` = IDU seul ; `sort=area` = surface
    persistée ; sinon groupe → bande → quantité → IDU (valeurs absentes après les connues)."""
    if mode == "sale":
        def key(r):
            p = r["signal"]["p"]
            av = r["signal"]["status"] == "AVAILABLE"
            return (0 if av else 1, -(p if av and v2._finite(p) else 0.0), r["idu"])
        return sorted(rows, key=key)
    if sort == "id":
        return sorted(rows, key=lambda r: r["idu"])

    def key(r):
        grp = v2.GROUP_ORDER.get(r["statut"], 9)
        band = 0 if sort == "area" else v2._BANDE_RANG.get(r["bande"], v2._BANDE_RANG["NC"])
        rv = _rank_value(r, scenario, sort)
        known = v2._finite(rv)
        return (grp, band, 0 if known else 1, -rv if known else 0.0, r["idu"])
    return sorted(rows, key=key)


def analyse_payload_persiste(session: Session, *, run_label: str, mode: str, scenario: str,
                             sort: str | None, commune: str | None = None,
                             idus: list[str] | None = None, limit: int = 100, offset: int = 0,
                             as_of: str | None = None) -> dict:
    """Réponse d'analyse V2 LUE de la table de run (l'endpoint ne calcule pas). Effectifs sur
    EXACTEMENT la sélection servie (commune ∩ IDU, avant pagination), Y COMPRIS en prospection (P6).
    Versions ENREGISTRÉES avec le résultat (pas lues à la requête — P2)."""
    if sort and sort not in ("signal", "capacity", "gain", "area", "id"):
        raise ValueError(f"tri inconnu : {sort}")
    scn_read = "keep" if mode == "sale" else scenario
    rows = read_scenarios(session, run_label=run_label, scenario=scn_read,
                          commune=commune, idus=idus)
    sort = sort or ("signal" if mode == "sale" else "area" if scenario == "divide" else "capacity")
    ordered = _trier(rows, mode=mode, scenario=scn_read, sort=sort)
    # Contrat UNIQUE persisté = live (P3) : en prospection, le STATUT servi est l'état de Signal
    # (SIGNAL_*), le statut foncier passe dans un champ séparé ; les compteurs portent sur les
    # états de Signal — dans les DEUX chemins.
    if mode == "sale":
        par_etat: dict = {}
        for r in ordered:
            etat = _SALE_STATE.get(r["signal"]["status"], "SIGNAL_NOT_AVAILABLE")
            par_etat[etat] = par_etat.get(etat, 0) + 1
            r["statut_foncier"] = r["statut"]
            r["statut"] = etat
        eff = {"par_statut": par_etat, "par_bande": {}}
    else:
        eff = effectifs_persistes(session, run_label=run_label, scenario=scn_read,
                                  commune=commune, idus=idus)
    ver = _versions_servies(session, run_label, scn_read, commune, idus)
    page = ordered[offset:offset + limit]
    return {
        "analysis_version": ver.get("analysis_version") or v2.VERSION,   # LUE des lignes servies (P3)
        "scenario_engine_version": ver.get("score_version"),
        "cascade_run": ver.get("cascade_label"),
        "signal_recette": ver.get("signal_recette"),                     # lue, pas codée en dur
        "signal_run": run_label, "run_servi": run_label,
        "source_donnees": "run_persiste", "provenance": ver.get("provenance"),
        "lot_mixte": ver.get("mixte", False),
        "reference": ("calculs V2 actuels comparés au Signal servi " + run_label),  # wording honnête
        "mode": mode, "scenario": scenario, "sort": sort, "as_of": as_of,
        "n_selection": len(rows),
        "effectifs": {"par_statut": eff["par_statut"], "par_bande": eff["par_bande"]},
        "page": {"limit": limit, "offset": offset, "n": len(page)},
        "parcelles": page,
    }


def _versions_servies(session, run_label, scenario, commune, idus) -> dict:
    """Versions ENREGISTRÉES avec les résultats servis (pas la config lue à la requête — P2/P3).
    Vérifie l'HOMOGÉNÉITÉ de la provenance : un lot cache+live est ANNONCÉ comme mixte, pas réduit
    à une provenance arbitraire. La recette du Signal est LUE du run servi (pas codée en dur)."""
    where, params = _filtre(commune, idus)
    where = where.replace("s.commune", "commune").replace("s.idu", "idu")   # table sans alias
    params.update({"run": run_label, "scn": scenario})
    rows = session.execute(text(
        f"SELECT score_version, cascade_label, analysis_version, provenance, count(*) "
        f"FROM parcel_scenario_v2_runs WHERE run_label=:run AND scenario=:scn AND {where} "
        f"GROUP BY 1,2,3,4"), params).fetchall()
    if not rows:
        return {}
    provs = {r[3] for r in rows}
    top = max(rows, key=lambda r: r[4])
    recette = _signal_recette_servie(session, run_label)
    return {"score_version": top[0], "cascade_label": top[1], "analysis_version": top[2],
            "provenance": "mixte" if len(provs) > 1 else top[3],
            "mixte": len(provs) > 1, "signal_recette": recette}


def _signal_recette_servie(session, run_label) -> str | None:
    """Recette (version de modèle) du Signal servi, LUE de `score_labuse.signal_version` — pas codée
    en dur (P3). Repli : le préfixe de version s'il n'y a pas de ligne."""
    v = session.execute(text(
        "SELECT signal_version FROM score_labuse WHERE run_label=:r AND signal_version IS NOT NULL "
        "LIMIT 1"), {"r": run_label}).scalar()
    return v


def effectifs_persistes(session: Session, *, run_label: str, scenario: str,
                        commune: str | None = None, idus: list[str] | None = None) -> dict:
    """Effectifs par statut et par bande, lus de la table (tous les statuts dans les comptes), sur
    EXACTEMENT la sélection (commune ∩ IDU — P6)."""
    where, params = _filtre(commune, idus)
    where = where.replace("s.commune", "commune").replace("s.idu", "idu")
    params.update({"run": run_label, "scn": scenario})
    stat = session.execute(text(
        f"SELECT status, count(*) FROM parcel_scenario_v2_runs WHERE run_label=:run "
        f"AND scenario=:scn AND {where} GROUP BY status"), params).fetchall()
    band = session.execute(text(
        f"SELECT band, count(*) FROM parcel_scenario_v2_runs WHERE run_label=:run "
        f"AND scenario=:scn AND {where} AND band IS NOT NULL GROUP BY band"), params).fetchall()
    return {"par_statut": {s[0]: s[1] for s in stat},
            "par_bande": {b[0]: b[1] for b in band},
            "n": sum(s[1] for s in stat)}
