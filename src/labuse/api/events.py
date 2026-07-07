"""ÉVÉNEMENTS (Vague 3) — le socle de la rétention : M11 alertes · M12 portefeuille vivant ·
M13 digest hebdo · M14 suivi de cible.

`detect_events(run_from, run_to)` diffe deux runs de scoring et émet : bascule de statut,
nouvel événement BODACC, nouveau permis proche d'une parcelle suivie (pipeline + watched).
Cronable via `labuse detect-events`. Sans second run réel, un run de DÉMONSTRATION étiqueté
(`q_v2_demo`, colonne demo=true partout) fait vivre le système — bascule réelle documentée.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

router = APIRouter(prefix="/events", tags=["events"])
RUN = "q_v2"


def get_db():
    from .app import get_db as _g
    yield from _g()


DDL = """
CREATE TABLE IF NOT EXISTS event_log (
  id serial PRIMARY KEY, ts timestamptz DEFAULT now(),
  kind varchar(24) NOT NULL,            -- bascule | bodacc | permis
  idu varchar(14),
  titre varchar(200) NOT NULL,
  detail text,
  run_from varchar(40), run_to varchar(40),
  demo boolean DEFAULT false,           -- événement de DÉMONSTRATION (étiqueté à l'écran)
  lu boolean DEFAULT false
);
CREATE TABLE IF NOT EXISTS watched_parcels (
  idu varchar(14) PRIMARY KEY, created_at timestamptz DEFAULT now()
);
CREATE TABLE IF NOT EXISTS saved_searches (
  id serial PRIMARY KEY, nom varchar(80) NOT NULL, hash text NOT NULL,
  created_at timestamptz DEFAULT now()
);
"""


def ensure_tables(engine) -> None:
    with engine.begin() as c:
        for stmt in DDL.split(";"):
            if stmt.strip():
                c.execute(text(stmt))


# ───────────────────────── détection (le job cronable) ─────────────────────────

def detect_events(db: Session, run_from: str, run_to: str, demo: bool = False) -> dict:
    """Diffe deux runs → événements. Idempotent par (kind, idu, run_from, run_to)."""
    inserted = {"bascule": 0, "bodacc": 0, "permis": 0}

    # 1. bascules de statut (jointure sur les parcelles présentes dans les DEUX runs)
    rows = db.execute(text("""
        SELECT p.idu, a.matrice_statut AS de, b.matrice_statut AS vers
        FROM dryrun_parcel_evaluations a
        JOIN dryrun_parcel_evaluations b ON b.parcel_id = a.parcel_id AND b.run_label = :to
        JOIN parcels p ON p.id = a.parcel_id
        WHERE a.run_label = :from AND a.matrice_statut <> b.matrice_statut"""),
        {"from": run_from, "to": run_to}).mappings().all()
    for r in rows:
        up = r["vers"] == "chaude" or (r["vers"] == "a_surveiller" and r["de"] in ("a_creuser", "ecartee"))
        n = db.execute(text("""
            INSERT INTO event_log (kind, idu, titre, detail, run_from, run_to, demo)
            SELECT 'bascule', CAST(:idu AS varchar), CAST(:titre AS varchar), CAST(:detail AS text), CAST(:from AS varchar), CAST(:to AS varchar), CAST(:demo AS boolean)
            WHERE NOT EXISTS (SELECT 1 FROM event_log WHERE kind='bascule' AND idu=:idu
                              AND run_from=:from AND run_to=:to)"""),
            {"idu": r["idu"], "titre": f"{'▲' if up else '▼'} {r['idu'][8:]} : {r['de']} → {r['vers']}",
             "detail": f"Bascule de statut au recalcul ({run_from} → {run_to}).",
             "from": run_from, "to": run_to, "demo": demo}).rowcount
        inserted["bascule"] += n

    # 2. nouveaux événements BODACC (rouge présent dans run_to, absent de run_from)
    rows = db.execute(text("""
        SELECT DISTINCT p.idu FROM dryrun_cascade_results b
        JOIN parcels p ON p.id = b.parcel_id
        WHERE b.run_label = :to AND b.evenement = 'rouge'
          AND NOT EXISTS (SELECT 1 FROM dryrun_cascade_results a
                          WHERE a.run_label = :from AND a.parcel_id = b.parcel_id AND a.evenement = 'rouge')"""),
        {"from": run_from, "to": run_to}).mappings().all()
    for r in rows:
        n = db.execute(text("""
            INSERT INTO event_log (kind, idu, titre, detail, run_from, run_to, demo)
            SELECT 'bodacc', CAST(:idu AS varchar), CAST(:titre AS varchar), 'Procédure collective ouverte (BODACC) détectée au recalcul.', CAST(:from AS varchar), CAST(:to AS varchar), CAST(:demo AS boolean)
            WHERE NOT EXISTS (SELECT 1 FROM event_log WHERE kind='bodacc' AND idu=:idu
                              AND run_from=:from AND run_to=:to)"""),
            {"idu": r["idu"], "titre": f"● BODACC : procédure ouverte sur {r['idu'][8:]}",
             "from": run_from, "to": run_to, "demo": demo}).rowcount
        inserted["bodacc"] += n

    # 2 bis. VEILLES : une bascule vers un statut « montant » qui MATCHE une recherche sauvegardée
    # → notification nominative (M11 : « une recherche filtrée nommée = une veille »).
    _veilles_match(db, run_to, demo)

    # 3. nouveau permis proche (≤ 300 m) d'une parcelle SUIVIE (pipeline + watched) — permis
    # récents relativement à la fin des données Sitadel (12 derniers mois de données).
    rows = db.execute(text("""
        WITH suivies AS (
          SELECT p.id, p.idu, p.geom_2975 FROM parcels p
          WHERE p.id IN (SELECT parcel_id FROM pipeline_entries)
             OR p.idu IN (SELECT idu FROM watched_parcels)
        )
        SELECT s.idu, sp.permit_id, sp.type, sp.date::date::text AS date
        FROM suivies s
        JOIN sitadel_permits sp ON sp.geom IS NOT NULL
          AND ST_DWithin(s.geom_2975, ST_Transform(sp.geom, 2975), 300)
          AND sp.date >= (SELECT max(date) FROM sitadel_permits) - interval '12 months'"""),
    ).mappings().all()
    for r in rows:
        n = db.execute(text("""
            INSERT INTO event_log (kind, idu, titre, detail, run_from, run_to, demo)
            SELECT 'permis', CAST(:idu AS varchar), CAST(:titre AS varchar), CAST(:detail AS text), CAST(:from AS varchar), CAST(:to AS varchar), CAST(:demo AS boolean)
            WHERE NOT EXISTS (SELECT 1 FROM event_log WHERE kind='permis' AND idu=:idu AND detail=:detail)"""),
            {"idu": r["idu"], "titre": f"Permis {r['type']} à ≤ 300 m de {r['idu'][8:]}",
             "detail": f"{r['permit_id']} du {r['date']} — le secteur bouge autour d'une parcelle suivie.",
             "from": run_from, "to": run_to, "demo": demo}).rowcount
        inserted["permis"] += n
    db.flush()
    return inserted


def _parse_hash_filters(h: str) -> dict:
    """Filtres d'une veille depuis son hash (#f=1&st=…&vm=1…) — même sérialisation que le front."""
    from urllib.parse import parse_qs
    q = parse_qs(h.lstrip("#"))
    g = lambda k: q.get(k, [None])[0]  # noqa: E731
    return {"st": (g("st") or "").split(",") if g("st") else [], "vm": g("vm") == "1",
            "ev": g("ev") == "1", "q": int(g("q")) if g("q") else None,
            "smin": int(g("smin")) if g("smin") else None, "smax": int(g("smax")) if g("smax") else None,
            "sdp": int(g("sdp")) if g("sdp") else None, "fl": (g("fl") or "").split(",") if g("fl") else []}


def _veilles_match(db: Session, run_to: str, demo: bool) -> int:
    veilles = db.execute(text("SELECT id, nom, hash FROM saved_searches")).mappings().all()
    if not veilles:
        return 0
    # bascules « montantes » de CE diff (déjà en event_log, kind=bascule, run_to)
    rows = db.execute(text("""
        SELECT e.idu, p.surface_m2, d.matrice_statut, d.q_score, r.sdp_residuelle_m2,
               vm.vue AS vue_mer,
               EXISTS (SELECT 1 FROM dryrun_cascade_results cr WHERE cr.run_label = :to
                       AND cr.parcel_id = p.id AND cr.evenement = 'rouge') AS a_evenement
        FROM event_log e
        JOIN parcels p ON p.idu = e.idu
        JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = :to
        LEFT JOIN parcel_residuel r ON r.parcel_id = p.id
        LEFT JOIN parcel_vue_mer vm ON vm.parcel_id = p.id
        WHERE e.kind = 'bascule' AND e.run_to = :to AND e.titre LIKE '▲%'"""),
        {"to": run_to}).mappings().all()
    n = 0
    for v in veilles:
        f = _parse_hash_filters(v["hash"])
        for r in rows:
            if f["st"] and r["matrice_statut"] not in f["st"]:
                continue
            if f["vm"] and r["vue_mer"] != "oui":
                continue
            if f["ev"] and not r["a_evenement"]:
                continue
            if f["q"] is not None and (r["q_score"] or 0) < f["q"]:
                continue
            if f["smin"] is not None and (r["surface_m2"] or 0) < f["smin"]:
                continue
            if f["smax"] is not None and (r["surface_m2"] or 0) > f["smax"]:
                continue
            if f["sdp"] is not None and (r["sdp_residuelle_m2"] or 0) < f["sdp"]:
                continue
            n += db.execute(text("""
                INSERT INTO event_log (kind, idu, titre, detail, run_to, demo)
                SELECT 'veille', CAST(:idu AS varchar), CAST(:titre AS varchar), CAST(:detail AS text),
                       CAST(:to AS varchar), CAST(:demo AS boolean)
                WHERE NOT EXISTS (SELECT 1 FROM event_log WHERE kind='veille' AND idu=:idu AND titre=:titre)"""),
                {"idu": r["idu"], "titre": f"🔭 Veille « {v['nom']} » : {r['idu'][8:]} correspond",
                 "detail": f"Bascule vers {r['matrice_statut']} qui matche votre veille (run {run_to}).",
                 "to": run_to, "demo": demo}).rowcount
    return n


def seed_demo(db: Session) -> dict:
    """Run de DÉMONSTRATION `q_v2_demo` : copie de q_v2 sur 8 parcelles avec statut modifié,
    ÉTIQUETÉ démo — pour voir le système vivre avant le prochain run réel de scoring."""
    db.execute(text("DELETE FROM dryrun_parcel_evaluations WHERE run_label = 'q_v2_demo'"))
    db.execute(text("""
        INSERT INTO dryrun_parcel_evaluations (run_label, parcel_id, completeness_score,
          opportunity_score, opportunity_base, status, q_score, a_score, a_completude, matrice_statut)
        SELECT 'q_v2_demo', parcel_id, completeness_score, opportunity_score, opportunity_base,
               status, q_score, a_score, a_completude,
               CASE WHEN rn <= 5 THEN 'chaude' ELSE 'a_surveiller' END
        FROM (
          SELECT d.*, row_number() OVER (ORDER BY d.q_score DESC) AS rn
          FROM dryrun_parcel_evaluations d JOIN parcels p ON p.id = d.parcel_id
          WHERE d.run_label = :run AND p.commune = 'Saint-Paul'
            AND d.matrice_statut = CASE WHEN true THEN 'a_surveiller' ELSE '' END
          LIMIT 5
        ) monte
    """), {"run": RUN})
    db.execute(text("""
        INSERT INTO dryrun_parcel_evaluations (run_label, parcel_id, completeness_score,
          opportunity_score, opportunity_base, status, q_score, a_score, a_completude, matrice_statut)
        SELECT 'q_v2_demo', parcel_id, completeness_score, opportunity_score, opportunity_base,
               status, q_score, a_score, a_completude, 'a_surveiller'
        FROM (
          SELECT d.* FROM dryrun_parcel_evaluations d JOIN parcels p ON p.id = d.parcel_id
          WHERE d.run_label = :run AND p.commune = 'Saint-Paul' AND d.matrice_statut = 'chaude'
          ORDER BY d.q_score ASC LIMIT 3
        ) descend
    """), {"run": RUN})
    out = detect_events(db, RUN, "q_v2_demo", demo=True)
    db.flush()
    return {"run_demo": "q_v2_demo", "events": out,
            "note": "Événements de DÉMONSTRATION (étiquetés). La bascule réelle = prochain run de scoring "
                    "(labuse dryrun-evaluate --label <run> puis labuse detect-events q_v2 <run>)."}


# ───────────────────────── API ─────────────────────────

@router.get("")
def list_events(unread_only: bool = False, limit: int = 100, db: Session = Depends(get_db)) -> dict:
    rows = db.execute(text(f"""
        SELECT e.id, e.ts::date::text AS date, e.kind, e.idu, e.titre, e.detail, e.demo, e.lu,
               d.matrice_statut AS statut
        FROM event_log e
        LEFT JOIN parcels p ON p.idu = e.idu
        LEFT JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = :run
        {"WHERE NOT e.lu" if unread_only else ""}
        ORDER BY e.ts DESC, e.id DESC LIMIT :lim"""),
        {"lim": limit, "run": RUN}).mappings().all()
    unread = db.execute(text("SELECT count(*) FROM event_log WHERE NOT lu")).scalar()
    return {"unread": int(unread or 0), "items": [dict(r) for r in rows]}


@router.get("/count")
def events_count(db: Session = Depends(get_db)) -> dict:
    n = db.execute(text("SELECT count(*) FROM event_log WHERE NOT lu")).scalar()
    per = db.execute(text("SELECT idu, count(*) FROM event_log WHERE NOT lu AND idu IS NOT NULL GROUP BY idu")).all()
    return {"unread": int(n or 0), "par_parcelle": {r[0]: r[1] for r in per}}


@router.post("/{event_id}/read")
def mark_read(event_id: int, db: Session = Depends(get_db)) -> dict:
    db.execute(text("UPDATE event_log SET lu = true WHERE id = :i"), {"i": event_id})
    return {"ok": True}


@router.post("/read-all")
def mark_all_read(db: Session = Depends(get_db)) -> dict:
    n = db.execute(text("UPDATE event_log SET lu = true WHERE NOT lu")).rowcount
    return {"ok": True, "marques": n}


@router.post("/detect")
def api_detect(run_from: str = "q_v2", run_to: str = "q_v2_demo", db: Session = Depends(get_db)) -> dict:
    return detect_events(db, run_from, run_to, demo=run_to.endswith("_demo"))


@router.post("/demo")
def api_demo(db: Session = Depends(get_db)) -> dict:
    return seed_demo(db)


# ── M14 — suivi de cible ──

@router.get("/watch/{idu}")
def watch_status(idu: str, db: Session = Depends(get_db)) -> dict:
    w = db.execute(text("SELECT 1 FROM watched_parcels WHERE idu = :i"), {"i": idu}).scalar()
    return {"watched": bool(w)}


@router.post("/watch/{idu}")
def watch_toggle(idu: str, db: Session = Depends(get_db)) -> dict:
    if not db.execute(text("SELECT 1 FROM parcels WHERE idu = :i"), {"i": idu}).scalar():
        raise HTTPException(404, "Parcelle inconnue")
    if db.execute(text("SELECT 1 FROM watched_parcels WHERE idu = :i"), {"i": idu}).scalar():
        db.execute(text("DELETE FROM watched_parcels WHERE idu = :i"), {"i": idu})
        return {"watched": False}
    db.execute(text("INSERT INTO watched_parcels (idu) VALUES (:i)"), {"i": idu})
    return {"watched": True}


# ── M11 — veilles (recherches sauvegardées) ──

class SearchSaveIn(BaseModel):
    nom: str
    hash: str


@router.get("/searches")
def searches_list(db: Session = Depends(get_db)) -> list[dict]:
    return [dict(r) for r in db.execute(text(
        "SELECT id, nom, hash, created_at::date::text AS date FROM saved_searches ORDER BY id DESC")).mappings()]


@router.post("/searches")
def searches_add(body: SearchSaveIn, db: Session = Depends(get_db)) -> dict:
    db.execute(text("INSERT INTO saved_searches (nom, hash) VALUES (:n, :h)"),
               {"n": body.nom[:80], "h": body.hash})
    return {"ok": True}


@router.delete("/searches/{sid}")
def searches_del(sid: int, db: Session = Depends(get_db)) -> dict:
    db.execute(text("DELETE FROM saved_searches WHERE id = :i"), {"i": sid})
    return {"ok": True}


# ── M13 — digest hebdo ──

def _digest_data(db: Session) -> dict:
    events = db.execute(text("""
        SELECT e.kind, e.idu, e.titre, e.detail, e.demo, d.q_score, d.a_score, d.matrice_statut
        FROM event_log e
        LEFT JOIN parcels p ON p.idu = e.idu
        LEFT JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = :run
        WHERE e.ts >= now() - interval '7 days'
        ORDER BY (e.kind = 'bascule') DESC, d.q_score DESC NULLS LAST LIMIT 10"""),
        {"run": RUN}).mappings().all()
    top = db.execute(text("""
        SELECT p.idu, d.q_score, d.a_score, round(p.surface_m2) AS surface_m2, r.sdp_residuelle_m2
        FROM dryrun_parcel_evaluations d JOIN parcels p ON p.id = d.parcel_id
        LEFT JOIN parcel_residuel r ON r.parcel_id = p.id
        WHERE d.run_label = :run AND p.commune = 'Saint-Paul' AND d.matrice_statut = 'chaude'
        ORDER BY d.q_score + d.a_score DESC LIMIT 5"""), {"run": RUN}).mappings().all()
    return {"evenements": [dict(r) for r in events], "top_chaudes": [dict(r) for r in top]}


@router.get("/digest")
def digest(db: Session = Depends(get_db)) -> dict:
    return _digest_data(db)


@router.get("/digest.html", response_class=HTMLResponse)
def digest_html(db: Session = Depends(get_db)) -> str:
    """Digest « les pépites de la semaine » — HTML email-ready (styles inline, table layout).
    L'envoi SMTP = config à brancher (cf. NOTES) ; le contenu est généré ici."""
    d = _digest_data(db)
    ev_rows = "".join(
        f"<tr><td style='padding:8px 12px;border-bottom:1px solid #e5e9e7;font:13px sans-serif'>"
        f"{'🟣 DÉMO · ' if e['demo'] else ''}{e['titre']}"
        f"<div style='color:#667;font-size:11px'>{e['detail'] or ''}</div></td></tr>"
        for e in d["evenements"]) or "<tr><td style='padding:12px;font:13px sans-serif;color:#667'>Aucun événement cette semaine.</td></tr>"
    top_rows = "".join(
        f"<tr><td style='padding:6px 12px;font:600 13px monospace'>{t['idu'][8:]}</td>"
        f"<td style='padding:6px;font:13px sans-serif'>Q {t['q_score']} · A {t['a_score']}</td>"
        f"<td style='padding:6px;font:12px sans-serif;color:#667'>{t['surface_m2'] or '—'} m² · SDP {round(t['sdp_residuelle_m2'] or 0)} m²</td></tr>"
        for t in d["top_chaudes"])
    return f"""<!doctype html><html><body style="margin:0;background:#f2f5f3;padding:24px">
<table width="600" align="center" style="background:#fff;border-radius:12px;overflow:hidden">
<tr><td style="background:#060A08;padding:18px 24px">
  <span style="font:700 18px sans-serif;color:#5CE6A1">LABUSE</span>
  <span style="font:12px sans-serif;color:#8FA69A"> · la chasse au trésor de la semaine</span></td></tr>
<tr><td style="padding:16px 12px 4px;font:700 13px sans-serif;color:#111">CE QUI A BOUGÉ</td></tr>
{ev_rows}
<tr><td style="padding:16px 12px 4px;font:700 13px sans-serif;color:#111">TOP 5 CHAUDES (Saint-Paul)</td></tr>
<tr><td><table width="100%">{top_rows}</table></td></tr>
<tr><td style="padding:14px 24px;font:10px sans-serif;color:#99a">Estimations indicatives issues de
données publiques — ne valent ni conseil juridique ni garantie de constructibilité.</td></tr>
</table></body></html>"""
