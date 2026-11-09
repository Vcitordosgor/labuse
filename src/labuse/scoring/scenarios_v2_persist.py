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
  analysis_version      text,
  computed_at           timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (run_label, parcel_id, scenario)
);
CREATE INDEX IF NOT EXISTS parcel_scenario_v2_commune
  ON parcel_scenario_v2_runs (run_label, commune, scenario);
"""

_UPSERT = text("""
INSERT INTO parcel_scenario_v2_runs
  (run_label, parcel_id, idu, commune, scenario, status, cause, band, score, band_provisional,
   additional_m2, project_total_m2, existing_m2, net_signed_m2, conditional_future_m2, residual_m2,
   zone_prod_zone, zone_prod_area_m2, vigilance, bande_v1, enriched, analysis_version)
VALUES
  (:run,:pid,:idu,:commune,:scn,:status,:cause,:band,:score,:bandp,
   :add,:ptot,:exist,:net,:fut,:res,:zz,:za,:vig,:v1,:enr,:ver)
ON CONFLICT (run_label, parcel_id, scenario) DO UPDATE SET
  idu=EXCLUDED.idu, commune=EXCLUDED.commune, status=EXCLUDED.status, cause=EXCLUDED.cause,
  band=EXCLUDED.band, score=EXCLUDED.score, band_provisional=EXCLUDED.band_provisional,
  additional_m2=EXCLUDED.additional_m2, project_total_m2=EXCLUDED.project_total_m2,
  existing_m2=EXCLUDED.existing_m2, net_signed_m2=EXCLUDED.net_signed_m2,
  conditional_future_m2=EXCLUDED.conditional_future_m2, residual_m2=EXCLUDED.residual_m2,
  zone_prod_zone=EXCLUDED.zone_prod_zone, zone_prod_area_m2=EXCLUDED.zone_prod_area_m2,
  vigilance=EXCLUDED.vigilance, bande_v1=EXCLUDED.bande_v1, enriched=EXCLUDED.enriched,
  analysis_version=EXCLUDED.analysis_version, computed_at=now()
""")


def ensure_table(session: Session) -> None:
    for stmt in DDL.strip().split(";\n"):
        if stmt.strip():
            session.execute(text(stmt))
    session.commit()


def _as_int(x):
    return None if x is None or not v2._finite(x) else round(x)


def _rebuild_statut_sans_C(rec: v2.ScenarioRecord, keep_res) -> str:
    """Statut de RECONSTRUCTION sans la magnitude de C (mode rapide). Il ne diffère de la
    conservation que sur un point : une parcelle « Aucun ajout » en conservation (R=0 par
    saturation, mais capacité de projet C_rebuild>0) devient « Capacité estimée » en reconstruction.
    Une capacité réglementaire nulle (`capacite_nulle`) reste « Aucun ajout » dans les deux."""
    if keep_res.status == "NO_MARGIN" and rec.cause_engine != "capacite_nulle":
        return "ESTIMATED"
    return keep_res.status


def _row(run_label, pid, rec, bande_v1, res, scenario, enriched):
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
        "enr": enriched, "ver": v2.VERSION}


def compute_scenarios_v2_batch(session: Session, parcel_ids: list[int], *,
                               run_label: str | None = None, enrich: bool = False,
                               chunk: int = 2000, log=None) -> dict:
    """Calcule et PERSISTE les scénarios V2 pour `parcel_ids`. Écrit la conservation (exacte) pour
    tous ; la reconstruction EXACTE si `enrich`, sinon son seul STATUT (quantités à `enriched=false`).
    Idempotent (upsert). Renvoie un petit bilan."""
    run_label = run_label or runs.current()
    ensure_table(session)
    bilan = {"parcelles": 0, "keep": 0, "rebuild": 0, "enriched": enrich}
    commune_by_id = {}
    for i in range(0, len(parcel_ids), chunk):
        lot = parcel_ids[i:i + chunk]
        recs = build.records_for_parcels(session, lot, run_label=run_label, enrich=enrich,
                                          with_zone=enrich)
        # commune par parcelle (une requête groupée par lot)
        for r in session.execute(text("SELECT id, commune FROM parcels WHERE id = ANY(:i)"),
                                 {"i": lot}):
            commune_by_id[r[0]] = r[1]
        id_by_idu = {}
        for r in session.execute(text("SELECT idu, id FROM parcels WHERE id = ANY(:i)"), {"i": lot}):
            id_by_idu[r[0]] = r[1]
        rows = []
        for rec, v1 in recs:
            pid = id_by_idu.get(rec.id)
            if pid is None:
                continue
            keep = v2.evaluate(rec, {"mode": "potential", "scenario": "keep"})
            rk = _row(run_label, pid, rec, v1, keep, "keep", enrich)
            rk["commune"] = commune_by_id.get(pid)
            rows.append(rk)
            bilan["keep"] += 1
            if enrich:
                reb = v2.evaluate(rec, {"mode": "potential", "scenario": "rebuild"})
                rr = _row(run_label, pid, rec, v1, reb, "rebuild", True)
            else:
                # Statut de reconstruction dérivé, quantités non chiffrées (enriched=false).
                reb = v2.evaluate(rec, {"mode": "potential", "scenario": "keep"})  # base statut
                reb.status = _rebuild_statut_sans_C(rec, keep)
                reb.band = None
                reb.quantities = {k: None for k in reb.quantities}
                rr = _row(run_label, pid, rec, v1, reb, "rebuild", False)
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
       s.vigilance, s.bande_v1, s.enriched,
       sl.signal_p, sl.signal_niveau, sl.cascade_exclue
FROM parcel_scenario_v2_runs s
LEFT JOIN score_labuse sl ON sl.run_label = s.run_label AND sl.idu = s.idu
WHERE s.run_label = :run AND s.scenario = :scn AND {where}
ORDER BY s.idu
""")


def read_scenarios(session: Session, *, run_label: str, scenario: str,
                   commune: str | None = None, idus: list[str] | None = None) -> list[dict]:
    """LIT les scénarios persistés (+ relaie le Signal servi depuis score_labuse). Aucun calcul."""
    where, params = "TRUE", {"run": run_label, "scn": scenario}
    if commune:
        where, params["c"] = "s.commune = :c", commune
    elif idus:
        where, params["i"] = "s.idu = ANY(:i)", idus
    sql = text(str(_READ_SQL).replace("{where}", where))
    out = []
    for r in session.execute(sql, params):
        m = r._mapping
        signal_eval = m["signal_p"] is not None
        out.append({
            "idu": m["idu"], "statut": m["status"], "cause": m["cause"], "bande": m["band"],
            "score": m["score"], "bande_provisoire": m["band_provisional"],
            "quantites": {"additional": m["additional_m2"], "project_total": m["project_total_m2"],
                          "existing": m["existing_m2"], "net_signed": m["net_signed_m2"],
                          "conditional_future": m["conditional_future_m2"]},
            "residual_m2": m["residual_m2"],
            "zone_productive": ({"zone": m["zone_prod_zone"], "area_m2": m["zone_prod_area_m2"]}
                                if m["zone_prod_zone"] else None),
            "vigilance": m["vigilance"], "bande_v1": m["bande_v1"],
            "quantites_calculees": m["enriched"],
            "signal": {"status": "AVAILABLE" if signal_eval else "NOT_AVAILABLE",
                       "p": m["signal_p"], "niveau": m["signal_niveau"],
                       "reason": None if signal_eval else
                       ("ECARTEE_ETAGE_0" if m["cascade_exclue"] else "SIGNAL_NON_CALCULE")},
        })
    return out


def _rank_value(row: dict, scenario: str, sort: str) -> float | None:
    q = row["quantites"]
    if sort == "area":
        return row.get("residual_m2") if False else None    # surface non stockée ici ; tri idu
    if row["statut"] == "DEFERRED":
        return None
    if scenario == "rebuild":
        return q["net_signed"] if sort == "gain" else q["project_total"]
    return q["additional"]


def _trier(rows: list[dict], *, mode: str, scenario: str, sort: str) -> list[dict]:
    """Tri déterministe D10 appliqué aux lignes LUES (groupe → bande → quantité → IDU)."""
    if mode == "sale":
        def key(r):
            p = r["signal"]["p"]
            av = r["signal"]["status"] == "AVAILABLE"
            return (0 if av else 1, -(p if av and v2._finite(p) else 0.0), r["idu"])
        return sorted(rows, key=key)

    def key(r):
        grp = v2.GROUP_ORDER.get(r["statut"], 9)
        band = v2._BANDE_RANG.get(r["bande"], v2._BANDE_RANG["NC"])
        rv = _rank_value(r, scenario, sort)
        known = v2._finite(rv)
        return (grp, band, 0 if known else 1, -rv if known else 0.0, r["idu"])
    return sorted(rows, key=key)


def analyse_payload_persiste(session: Session, *, run_label: str, mode: str, scenario: str,
                             sort: str | None, commune: str | None = None,
                             idus: list[str] | None = None, limit: int = 100, offset: int = 0,
                             as_of: str | None = None) -> dict:
    """Réponse d'analyse V2 LUE de la table de run (l'endpoint ne calcule pas). Effectifs sur toute
    la sélection, page triée, versions (spec §2.2), Signal relayé."""
    from . import score_labuse as sl
    _, score_version = sl.charger_bareme()
    scn_read = "keep" if mode == "sale" else scenario
    rows = read_scenarios(session, run_label=run_label, scenario=scn_read,
                          commune=commune, idus=idus)
    sort = sort or ("signal" if mode == "sale" else "area" if scenario == "divide" else "capacity")
    ordered = _trier(rows, mode=mode, scenario=scn_read, sort=sort)
    eff = (effectifs_persistes(session, run_label=run_label, scenario=scn_read, commune=commune)
           if mode != "sale" else {"n": len(rows), "par_statut": {}, "par_bande": {}})
    page = ordered[offset:offset + limit]
    return {
        "analysis_version": v2.VERSION, "scenario_engine_version": score_version,
        "signal_recette": "q_v15", "signal_run": run_label, "run_servi": run_label,
        "source_donnees": "run_persiste",
        "mode": mode, "scenario": scenario, "sort": sort, "as_of": as_of,
        "n_selection": len(rows),
        "effectifs": {"par_statut": eff["par_statut"], "par_bande": eff["par_bande"]},
        "page": {"limit": limit, "offset": offset, "n": len(page)},
        "parcelles": page,
    }


def effectifs_persistes(session: Session, *, run_label: str, scenario: str,
                        commune: str | None = None) -> dict:
    """Effectifs par statut et par bande, lus de la table (tous les statuts dans les comptes)."""
    where, params = "TRUE", {"run": run_label, "scn": scenario}
    if commune:
        where, params["c"] = "commune = :c", commune
    stat = session.execute(text(
        f"SELECT status, count(*) FROM parcel_scenario_v2_runs WHERE run_label=:run "
        f"AND scenario=:scn AND {where} GROUP BY status"), params).fetchall()
    band = session.execute(text(
        f"SELECT band, count(*) FROM parcel_scenario_v2_runs WHERE run_label=:run "
        f"AND scenario=:scn AND {where} AND band IS NOT NULL GROUP BY band"), params).fetchall()
    return {"par_statut": {s[0]: s[1] for s in stat},
            "par_bande": {b[0]: b[1] for b in band},
            "n": sum(s[1] for s in stat)}
