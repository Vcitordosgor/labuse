"""OUTILS-À-CLIENTS (Vague 5) — M19 matching terrain↔promoteur · M20 pack apporteur ·
M21 API partenaire. Construits FONCTIONNELS avec données de démo ÉTIQUETÉES (demo=true),
prêts à s'activer avec de vrais utilisateurs.
"""
from __future__ import annotations

import secrets
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

router = APIRouter(tags=["partners"])
RUN = "q_v2"


def get_db():
    from .app import get_db as _g
    yield from _g()


DDL = """
CREATE TABLE IF NOT EXISTS match_profiles (
  id serial PRIMARY KEY, nom varchar(80) NOT NULL, commune varchar(64),
  surface_min integer, surface_max integer, sdp_min integer,
  demo boolean DEFAULT false, created_at timestamptz DEFAULT now()
);
CREATE TABLE IF NOT EXISTS share_links (
  token varchar(24) PRIMARY KEY, idu varchar(14) NOT NULL,
  created_by varchar(80) DEFAULT 'Vic — LABUSE', created_at timestamptz DEFAULT now(),
  views integer DEFAULT 0
);
CREATE TABLE IF NOT EXISTS api_keys (
  key varchar(48) PRIMARY KEY, nom varchar(80), quota_jour integer DEFAULT 500,
  demo boolean DEFAULT false, jour date DEFAULT current_date, utilise integer DEFAULT 0
);
"""


def ensure_tables(engine) -> None:
    with engine.begin() as c:
        for stmt in DDL.split(";"):
            if stmt.strip():
                c.execute(text(stmt))
        # deux profils de DÉMO étiquetés + une clé API de démo (idempotent)
        c.execute(text("""
            INSERT INTO match_profiles (nom, commune, surface_min, surface_max, sdp_min, demo)
            SELECT 'Promoteur démo — collectif (île)', NULL, 800, 20000, 800, true
            WHERE NOT EXISTS (SELECT 1 FROM match_profiles WHERE nom LIKE 'Promoteur démo — collectif%')"""))
        c.execute(text("""
            INSERT INTO match_profiles (nom, commune, surface_min, surface_max, sdp_min, demo)
            SELECT 'CMiste démo — maisons (île)', NULL, 300, 1500, 150, true
            WHERE NOT EXISTS (SELECT 1 FROM match_profiles WHERE nom LIKE 'CMiste démo%')"""))
        c.execute(text("""
            INSERT INTO api_keys (key, nom, quota_jour, demo)
            SELECT 'demo-labuse-partner-key', 'Partenaire de démonstration', 500, true
            WHERE NOT EXISTS (SELECT 1 FROM api_keys WHERE key = 'demo-labuse-partner-key')"""))


# ───────────────────────── M19 — MATCHING TERRAIN ↔ PROMOTEUR ─────────────────────────

class ProfileIn(BaseModel):
    nom: str
    commune: str = "Saint-Paul"
    surface_min: int | None = None
    surface_max: int | None = None
    sdp_min: int | None = None


@router.get("/partners/profiles")
def profiles(db: Session = Depends(get_db)) -> list[dict]:
    return [dict(r) for r in db.execute(text(
        "SELECT id, nom, commune, surface_min, surface_max, sdp_min, demo FROM match_profiles ORDER BY id")).mappings()]


@router.post("/partners/profiles")
def profile_add(body: ProfileIn, db: Session = Depends(get_db)) -> dict:
    db.execute(text("""INSERT INTO match_profiles (nom, commune, surface_min, surface_max, sdp_min)
                       VALUES (:n, :c, :smin, :smax, :sdp)"""),
               {"n": body.nom[:80], "c": body.commune, "smin": body.surface_min,
                "smax": body.surface_max, "sdp": body.sdp_min})
    return {"ok": True}


@router.post("/partners/match/run")
def match_run(db: Session = Depends(get_db)) -> dict:
    """Matche les BASCULES → chaude (event_log) contre les profils → événements kind='match'
    (alimentent la cloche M11). Idempotent."""
    rows = db.execute(text("""
        SELECT e.idu, mp.id AS profile_id, mp.nom, e.demo
        FROM event_log e
        JOIN parcels p ON p.idu = e.idu
        LEFT JOIN parcel_residuel r ON r.parcel_id = p.id
        JOIN match_profiles mp ON (mp.commune IS NULL OR mp.commune = p.commune)
          AND (mp.surface_min IS NULL OR p.surface_m2 >= mp.surface_min)
          AND (mp.surface_max IS NULL OR p.surface_m2 <= mp.surface_max)
          AND (mp.sdp_min IS NULL OR COALESCE(r.sdp_residuelle_m2, 0) >= mp.sdp_min)
        WHERE e.kind = 'bascule' AND e.titre LIKE '▲%chaude'"""), ).mappings().all()
    n = 0
    for r in rows:
        n += db.execute(text("""
            INSERT INTO event_log (kind, idu, titre, detail, demo)
            SELECT 'match', CAST(:idu AS varchar), CAST(:titre AS varchar), CAST(:detail AS text), CAST(:demo AS boolean)
            WHERE NOT EXISTS (SELECT 1 FROM event_log WHERE kind='match' AND idu=:idu AND detail=:detail)"""),
            {"idu": r["idu"], "titre": f"🎯 Match : {r['idu'][8:]} correspond à « {r['nom']} »",
             "detail": f"Bascule chaude + critères du profil #{r['profile_id']} réunis.",
             "demo": r["demo"]}).rowcount
    db.flush()
    return {"matches": n}


# ───────────────────────── M20 — PACK APPORTEUR (lien de partage) ─────────────────────────

@router.post("/partners/share/{idu}")
def share_create(idu: str, db: Session = Depends(get_db)) -> dict:
    if not db.execute(text("SELECT 1 FROM parcels WHERE idu = :i"), {"i": idu}).scalar():
        raise HTTPException(404, "Parcelle inconnue")
    token = secrets.token_urlsafe(12)[:16]
    db.execute(text("INSERT INTO share_links (token, idu) VALUES (:t, :i)"), {"t": token, "i": idu})
    return {"token": token, "url": f"/p/{token}"}


@router.get("/partners/share/{idu}/list")
def share_list(idu: str, db: Session = Depends(get_db)) -> list[dict]:
    return [dict(r) for r in db.execute(text(
        """SELECT token, created_at::date::text AS date, views FROM share_links
           WHERE idu = :i ORDER BY created_at DESC"""), {"i": idu}).mappings()]


@router.get("/p/{token}", response_class=HTMLResponse)
def share_public(token: str, db: Session = Depends(get_db)) -> str:
    """Page publique MINIMALE, lecture seule, filigranée + horodatée, compteur de consultations."""
    link = db.execute(text("SELECT idu, created_by, created_at FROM share_links WHERE token = :t"),
                      {"t": token}).mappings().first()
    if not link:
        raise HTTPException(404, "Lien inconnu ou révoqué")
    db.execute(text("UPDATE share_links SET views = views + 1 WHERE token = :t"), {"t": token})
    from .app import _q_v2_fiche
    f = _q_v2_fiche(db, link["idu"])
    horodatage = datetime.now().strftime("%d/%m/%Y à %H:%M")
    cree = link["created_at"].strftime("%d/%m/%Y à %H:%M")
    lignes = "".join(
        f"<div style='display:flex;gap:10px;padding:7px 0;border-bottom:1px solid #1E2A23'>"
        f"<span style='min-width:38px;text-align:right;font:600 12px monospace;"
        f"color:{'#5CE6A1' if (ln['weight'] or 0) > 0 else '#E8695A' if (ln['weight'] or 0) < 0 else '#5C7268'}'>"
        f"{('+' + str(ln['weight'])) if (ln['weight'] or 0) > 0 else ln['weight'] if ln['weight'] is not None else '·'}</span>"
        f"<div><div style='font:500 12px sans-serif;color:#C9DCD1'>{ln['layer']}</div>"
        f"<div style='font:11px sans-serif;color:#8FA69A'>{ln['detail']}</div>"
        f"<div style='font:9px monospace;color:#5C7268'>{ln['source'] or ''} · {ln['date'] or ''}</div></div></div>"
        for ln in f["lines"] if ln["weight"] or ln["result"] in ("SOFT_FLAG", "UNKNOWN"))
    ev = (f"<div style='background:#3a1614;border-radius:8px;padding:10px 14px;margin:12px 0;"
          f"color:#E8695A;font:12px sans-serif'>● ÉVÉNEMENT — {f['evenement_detail']}</div>"
          if f.get("evenement") == "rouge" else "")
    return f"""<!doctype html><html lang=fr><head><meta charset=utf-8><meta name=robots content=noindex>
<title>LABUSE — {f['idu']} (lecture seule)</title></head>
<body style="margin:0;background:#060A08;font-family:sans-serif">
<div style="max-width:640px;margin:0 auto;padding:28px 20px">
  <div style="display:flex;justify-content:space-between;align-items:baseline">
    <span style="display:inline-flex;align-items:center;gap:8px"><svg viewBox="0 0 240 82" style="height:16px;filter:drop-shadow(0 0 6px rgba(47,224,160,.35))" fill="#2FE0A0"><path d="M2 15 C58 10 100 18 120 27 C140 18 182 10 238 15 C202 29 162 40 135 46 C127 49 122 53 120 60 C118 53 113 49 105 46 C78 40 38 29 2 15 Z"/></svg><span style="font:700 15px sans-serif;color:#5CE6A1">LA BUSE</span></span>
    <span style="font:10px monospace;color:#5C7268">PACK APPORTEUR · LECTURE SEULE</span>
  </div>
  <div style="margin-top:6px;background:#171221;border:1px solid #2a2138;border-radius:8px;padding:8px 12px;
       font:10.5px monospace;color:#B497F0">
    identifié par {link['created_by']} le {cree} · consulté le {horodatage} · lien traçable
  </div>
  {ev}
  <h1 style="font:600 20px monospace;color:#ECF5EF;margin:16px 0 2px">{f['idu']}</h1>
  <p style="color:#8FA69A;font-size:12px;margin:0">{f['surface_m2'] or '?'} m² · {f['commune']}</p>
  <div style="display:flex;gap:10px;margin:14px 0">
    <div style="flex:1;background:#111814;border-radius:8px;padding:10px 14px">
      <div style="font:700 22px sans-serif;color:#5CE6A1">{f['q_score']}</div>
      <div style="font:9px monospace;color:#5C7268">QUALITÉ /100</div></div>
    <div style="flex:1;background:#111814;border-radius:8px;padding:10px 14px">
      <div style="font:700 22px sans-serif;color:#4ADE96">{f['a_score']}</div>
      <div style="font:9px monospace;color:#5C7268">ACCESSIBILITÉ /100</div></div>
    <div style="flex:1;background:#111814;border-radius:8px;padding:10px 14px">
      <div style="font:700 22px sans-serif;color:#5CE6A1">{f['completeness_score']}</div>
      <div style="font:9px monospace;color:#5C7268">COMPLÉTUDE %</div></div>
  </div>
  {lignes}
  <p style="margin-top:18px;font:10px sans-serif;color:#5C7268;line-height:1.5">Estimations indicatives
  issues de données publiques — ne valent ni conseil juridique/notarial ni garantie de constructibilité.
  Document de présentation généré par LABUSE — reproduction encadrée.</p>
</div></body></html>"""


# ───────────────────────── M21 — API PARTENAIRE (B2B2C) ─────────────────────────

def _check_key(db: Session, key: str | None) -> dict:
    if not key:
        raise HTTPException(401, "Clé API requise (paramètre ?key=…)")
    k = db.execute(text("SELECT key, nom, quota_jour, jour, utilise FROM api_keys WHERE key = :k"),
                   {"k": key}).mappings().first()
    if not k:
        raise HTTPException(401, "Clé API inconnue")
    if k["jour"] != date.today():
        db.execute(text("UPDATE api_keys SET jour = current_date, utilise = 0 WHERE key = :k"), {"k": key})
    elif k["utilise"] >= k["quota_jour"]:
        raise HTTPException(429, f"Quota journalier atteint ({k['quota_jour']} appels/jour)")
    db.execute(text("UPDATE api_keys SET utilise = utilise + 1 WHERE key = :k"), {"k": key})
    return dict(k)


@router.get("/api/v1/parcels")
def api_v1_parcels(key: str | None = None, statut: str | None = None, min_q: int = 0,
                   commune: str = "Saint-Paul", limit: int = Query(50, ge=1, le=200),
                   offset: int = Query(0, ge=0), db: Session = Depends(get_db)) -> dict:
    """API partenaire — le robinet B2B2C. Clé simple + quota journalier. Doc : /api/v1/docs."""
    _check_key(db, key)
    rows = db.execute(text("""
        SELECT p.idu, p.commune, round(p.surface_m2) AS surface_m2, d.matrice_statut AS statut,
               d.q_score, d.a_score, d.completeness_score, r.sdp_residuelle_m2
        FROM parcels p
        JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = :run
        LEFT JOIN parcel_residuel r ON r.parcel_id = p.id
        WHERE p.commune = :c AND d.q_score >= :q
          AND (CAST(:s AS text) IS NULL OR d.matrice_statut = :s)
        ORDER BY d.q_score DESC LIMIT :lim OFFSET :off"""),
        {"run": RUN, "c": commune, "q": min_q, "s": statut, "lim": limit, "off": offset}).mappings().all()
    return {"count": len(rows), "offset": offset,
            "mention": "Données indicatives LABUSE (scoring q_v2) — usage selon convention partenaire.",
            "items": [dict(r) for r in rows]}


@router.get("/api/v1/docs", response_class=HTMLResponse)
def api_v1_docs() -> str:
    return """<!doctype html><html lang=fr><head><meta charset=utf-8><title>LABUSE — API partenaire v1</title></head>
<body style="margin:0;background:#060A08;color:#C9DCD1;font-family:sans-serif">
<div style="max-width:680px;margin:0 auto;padding:32px 20px">
<span style="display:inline-flex;align-items:center;gap:8px"><svg viewBox="0 0 240 82" style="height:16px;filter:drop-shadow(0 0 6px rgba(47,224,160,.35))" fill="#2FE0A0"><path d="M2 15 C58 10 100 18 120 27 C140 18 182 10 238 15 C202 29 162 40 135 46 C127 49 122 53 120 60 C118 53 113 49 105 46 C78 40 38 29 2 15 Z"/></svg><span style="font:700 16px sans-serif;color:#5CE6A1">LA BUSE</span></span>
<span style="color:#5C7268;font-size:12px"> · API partenaire v1</span>
<h1 style="font-size:20px;color:#ECF5EF">GET /api/v1/parcels</h1>
<p style="font-size:13px;color:#8FA69A">Parcelles scorées (run premium q_v2). Authentification par
clé, quota 500 appels/jour.</p>
<table style="width:100%;font-size:12.5px;border-collapse:collapse">
<tr style="color:#5C7268;text-align:left"><th style="padding:6px 8px">Paramètre</th><th>Type</th><th>Description</th></tr>
<tr style="border-top:1px solid #1E2A23"><td style="padding:6px 8px;font-family:monospace;color:#5CE6A1">key</td><td>string</td><td>clé API (obligatoire)</td></tr>
<tr style="border-top:1px solid #1E2A23"><td style="padding:6px 8px;font-family:monospace;color:#5CE6A1">statut</td><td>enum</td><td>chaude · a_surveiller · a_creuser · ecartee</td></tr>
<tr style="border-top:1px solid #1E2A23"><td style="padding:6px 8px;font-family:monospace;color:#5CE6A1">min_q</td><td>int</td><td>score Qualité minimal (0-100)</td></tr>
<tr style="border-top:1px solid #1E2A23"><td style="padding:6px 8px;font-family:monospace;color:#5CE6A1">commune</td><td>string</td><td>défaut Saint-Paul (périmètre V1)</td></tr>
<tr style="border-top:1px solid #1E2A23"><td style="padding:6px 8px;font-family:monospace;color:#5CE6A1">limit / offset</td><td>int</td><td>pagination (limit ≤ 200)</td></tr>
</table>
<h2 style="font-size:14px;color:#ECF5EF;margin-top:22px">Exemple</h2>
<pre style="background:#111814;border:1px solid #1E2A23;border-radius:8px;padding:12px;font-size:11.5px;color:#C9DCD1;overflow-x:auto">curl "https://…/api/v1/parcels?key=demo-labuse-partner-key&statut=chaude&min_q=70&limit=10"</pre>
<p style="font-size:11px;color:#5C7268">Erreurs : 401 clé absente/inconnue · 429 quota atteint.
Clé de démonstration : <code style="color:#B497F0">demo-labuse-partner-key</code> (étiquetée démo).
Réponses indicatives — usage selon convention partenaire.</p>
</div></body></html>"""
