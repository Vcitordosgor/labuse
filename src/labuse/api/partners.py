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
from ..scoring.score_v_constants import Q_A_RUN_LABEL as RUN  # run de référence (bascule centralisée)


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


@router.get("/partners/match/compatibilite/{idu}")
def match_compatibilite(idu: str, db: Session = Depends(get_db)) -> dict:
    """A + B — pour UNE parcelle, score de compatibilité DÉCOMPOSÉ contre chaque profil (les critères
    qui collent, plus de oui/non opaque). Déterministe. Les profils sont des DÉMOS (labellisés)."""
    p = db.execute(text("""
        SELECT p.commune, round(p.surface_m2) AS surf, COALESCE(r.sdp_residuelle_m2, 0) AS sdp,
               zp.zone_fam, zp.zone_lib, d.matrice_statut AS statut
        FROM parcels p
        LEFT JOIN parcel_residuel r ON r.parcel_id = p.id
        LEFT JOIN parcel_zone_plu zp ON zp.idu = p.idu
        LEFT JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = :run
        WHERE p.idu = :idu"""), {"idu": idu, "run": RUN}).mappings().first()
    if not p:
        raise HTTPException(404, "Parcelle inconnue")
    profs = db.execute(text("SELECT id, nom, commune, surface_min, surface_max, sdp_min, demo "
                            "FROM match_profiles ORDER BY id")).mappings().all()
    surf, sdp = float(p["surf"] or 0), float(p["sdp"] or 0)
    constructible = p["zone_fam"] in ("U", "AU")
    chaude = p["statut"] in ("chaude", "a_surveiller")
    out = []
    for mp in profs:
        s_ok = ((mp["surface_min"] is None or surf >= mp["surface_min"])
                and (mp["surface_max"] is None or surf <= mp["surface_max"]))
        sdp_ok = mp["sdp_min"] is None or sdp >= mp["sdp_min"]
        c_ok = mp["commune"] is None or mp["commune"] == p["commune"]
        fac = [
            {"critere": f"Surface {int(mp['surface_min'] or 0)}–{int(mp['surface_max'] or 0)} m²",
             "ok": s_ok, "valeur": f"{int(surf)} m²", "poids": 30},
            {"critere": f"SDP résiduelle ≥ {int(mp['sdp_min'] or 0)} m²",
             "ok": sdp_ok, "valeur": f"{int(sdp)} m²", "poids": 30},
            {"critere": f"Commune ({mp['commune'] or 'toute l’île'})",
             "ok": c_ok, "valeur": p["commune"], "poids": 20},
            {"critere": "Terrain constructible (U/AU)", "ok": constructible,
             "valeur": p["zone_lib"] or "—", "poids": 10},
            {"critere": "Signal marché (chaude)", "ok": chaude, "valeur": p["statut"] or "—", "poids": 10},
        ]
        score = sum(f["poids"] for f in fac if f["ok"])
        out.append({"profil": mp["nom"], "demo": bool(mp["demo"]), "score": score, "facteurs": fac})
    out.sort(key=lambda x: -x["score"])
    return {"idu": idu, "commune": p["commune"], "demo": True, "profils": out}


@router.get("/partners/promoteurs-actifs")
def promoteurs_actifs(commune: str | None = None, db: Session = Depends(get_db)) -> dict:
    """C — ANCRAGE RÉEL : promoteurs (personnes morales) ayant déposé des permis récemment dans le
    secteur (SITADEL). Donnée réelle, distincte du matching démo. PRIVACY : seuls les déposants avec
    SIREN (personnes morales, public) — les particuliers ne sont JAMAIS exposés."""
    rows = db.execute(text("""
        SELECT raw->>'petitioner_name' AS nom, raw->>'petitioner_siren' AS siren,
               count(*) AS n_permis, max(date)::date AS dernier,
               sum(CASE WHEN raw->>'nb_lgt' ~ '^[0-9]+$' THEN (raw->>'nb_lgt')::int ELSE 0 END) AS logements
        FROM sitadel_permits
        WHERE (CAST(:c AS text) IS NULL OR commune = :c)
          AND raw->>'petitioner_siren' ~ '^[0-9]{9}$'          -- PM (SIREN public) uniquement
          AND date > now() - interval '5 years'
        GROUP BY 1, 2 HAVING count(*) >= 2
        ORDER BY count(*) DESC, sum(CASE WHEN raw->>'nb_lgt' ~ '^[0-9]+$' THEN (raw->>'nb_lgt')::int ELSE 0 END) DESC NULLS LAST
        LIMIT 12"""), {"c": commune}).mappings().all()
    return {"commune": commune, "reel": True,
            "source": "SITADEL — permis déposés, 5 dernières années (déposants personnes morales, SIREN public)",
            "promoteurs": [{"nom": r["nom"], "siren": r["siren"], "n_permis": r["n_permis"],
                            "dernier": r["dernier"].isoformat() if r["dernier"] else None,
                            "logements": r["logements"] or None} for r in rows]}


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


# Points clés = FORMATAGE déterministe des facteurs de scoring (aucune IA). Titre de pitch par
# couche ; le `detail` déjà tracé donne les spécifiques. Forces = poids > 0 ; attentions = poids < 0
# (les pénalités RÉELLES apparaissent — honnêteté : ex. residuel_socle « hors cible collectif »).
_FORCE_TITLE = {
    "zonage_plu_gpu": "Terrain constructible", "sitadel": "Dynamique de construction active",
    "dvf": "Marché porteur", "amenites": "Équipements à proximité", "acces": "Accès voirie",
    "viabilisation": "Réseaux au contact", "residuel_socle": "Potentiel de densification",
    "assemblage": "Regroupement possible",
}
_ATTENTION_TITLE = {
    "residuel_socle": "SDP résiduelle limitée", "parc_national": "Zonage protégé (Parc national)",
    "risques": "Aléa naturel", "abf": "Périmètre patrimonial (ABF)", "sol_pollue": "Sol à vérifier",
    "icpe": "Installation classée à proximité", "cinquante_pas": "Bande littorale (50 pas)",
    "safer": "Vocation agricole (SAFER)", "foret_publique": "Forêt publique / régime forestier",
}


def _points_cles(lines: list) -> tuple[list, list]:
    """Dérive (forces, attentions) des facteurs — pur formatage, jamais d'invention."""
    forces, attentions = [], []
    for ln in lines:
        w = ln.get("weight") or 0
        layer = ln.get("layer") or ""
        detail = (ln.get("detail") or "").strip()
        if not detail:
            continue
        if w > 0:
            forces.append((w, _FORCE_TITLE.get(layer, layer.replace("_", " ").capitalize()), detail))
        elif w < 0:
            attentions.append((w, _ATTENTION_TITLE.get(layer, layer.replace("_", " ").capitalize()), detail))
    forces.sort(key=lambda x: -x[0])
    attentions.sort(key=lambda x: x[0])            # la pénalité la plus forte d'abord
    return forces[:5], attentions[:4]


def _points_cles_html(lines: list) -> str:
    forces, attentions = _points_cles(lines)
    if not forces and not attentions:
        return ""

    def row(icon: str, color: str, title: str, detail: str) -> str:
        return (f"<div style='display:flex;gap:8px;padding:5px 0'>"
                f"<span style='color:{color};font-size:12px;line-height:1.4'>{icon}</span>"
                f"<div style='min-width:0'><b style='font:600 12px sans-serif;color:#ECF5EF'>{title}</b>"
                f"<span style='font:12px sans-serif;color:#8FA69A'> — {detail}</span></div></div>")
    fh = "".join(row("✓", "#5CE6A1", t, d) for _, t, d in forces)
    ah = "".join(row("⚠", "#E8B44C", t, d) for _, t, d in attentions)
    return ("<div style='margin:16px 0;background:#0d1310;border:1px solid #1E2A23;border-radius:10px;padding:12px 14px'>"
            "<p style='font:10px monospace;letter-spacing:1.5px;color:#5C7268;margin:0 0 4px'>POINTS CLÉS</p>"
            + fh + ah + "</div>")


def _pack_photo_html(m: dict, target_w: int = 596) -> str:
    """Photo aérienne STATIQUE (tuiles ortho IGN positionnées + contour parcelle en SVG), mise à
    l'échelle pour la largeur du pack. data-URI → imprimable, aucune carte interactive."""
    scale = target_w / m["width"]
    h = round(m["height"] * scale)
    imgs = "".join(f'<img src="{t["data_uri"]}" width="256" height="256" '
                   f'style="position:absolute;left:{t["left"]}px;top:{t["top"]}px">' for t in m["tiles"])
    polys = "".join(f'<polygon points="{p}" fill="rgba(180,151,240,0.20)" stroke="#B497F0" '
                    f'stroke-width="2.5" stroke-linejoin="round"/>' for p in m["polygons"])
    return (f'<div style="position:relative;width:{target_w}px;height:{h}px;overflow:hidden;'
            f'border-radius:10px;border:1px solid #2a2138;margin:14px 0 3px">'
            f'<div style="position:absolute;top:0;left:0;width:{m["width"]}px;height:{m["height"]}px;'
            f'transform:scale({scale:.4f});transform-origin:top left">{imgs}'
            f'<svg width="{m["width"]}" height="{m["height"]}" style="position:absolute;top:0;left:0">{polys}</svg>'
            f'</div></div>'
            f'<div style="font:9px monospace;color:#5C7268;margin-bottom:6px">'
            f'{m["attribution"]} · vue aérienne · contour cadastral</div>')


# Variante IMPRESSION / PDF en thème CLAIR — l'écran reste en charte sombre, mais un apporteur
# imprime/partage ce document à un promoteur : le sombre bave sur papier et fait cheap. On n'inverse
# QU'À l'impression, sans dupliquer le HTML : sélecteurs d'attribut sur les hex des styles inline
# (une règle @media print `!important` prime sur un style inline non-important). Zéro impact écran.
_PACK_PRINT_CSS = """<style>
@media print {
  @page { margin: 14mm; }
  * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
  /* fonds sombres → clairs */
  [style*="#060A08"] { background: #ffffff !important; }
  [style*="#171221"] { background: #f4f1fb !important; }
  [style*="#3a1614"] { background: #fdecea !important; }
  [style*="#111814"] { background: #f4f6f5 !important; }
  [style*="#0d1310"] { background: #f6f8f7 !important; }
  /* bordures sombres → claires */
  [style*="#2a2138"] { border-color: #e4e0f0 !important; }
  [style*="#1E2A23"] { border-color: #e6e9e7 !important; }
  /* textes neutres clairs → sombres sur blanc */
  [style*="#ECF5EF"] { color: #121814 !important; }
  [style*="#C9DCD1"] { color: #2a322d !important; }
  [style*="#8FA69A"] { color: #55635b !important; }
  [style*="#5C7268"] { color: #6b746f !important; }
  /* accents assombris pour rester lisibles sur papier (mais reconnaissables) */
  [style*="#5CE6A1"] { color: #0c8a4f !important; }
  [style*="#4ADE96"] { color: #0c8a4f !important; }
  [style*="#B497F0"] { color: #5b3fa6 !important; }
  [style*="#E8695A"] { color: #c0392b !important; }
  [style*="#E8B44C"] { color: #9a6510 !important; }
  svg[fill] { fill: #0c8a4f !important; }   /* logo LA BUSE (fill en attribut) */
}
</style>"""


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
    # Photo aérienne IGN (ortho) + contour — image STATIQUE. Défensif : réseau/géométrie absents → pas
    # de photo (jamais d'erreur), le pack reste valide.
    photo = ""
    try:
        from ..flash.carte import IGN_ORTHO_ATTRIBUTION, IGN_ORTHO_URL, build_situation_map
        from ..flash.report import storage_dir
        gj = db.execute(text("SELECT ST_AsGeoJSON(ST_Transform(geom_2975, 4326)) FROM parcels WHERE idu = :i"),
                        {"i": link["idu"]}).scalar()
        m = build_situation_map(gj, storage_dir() / "tiles", tile_url=IGN_ORTHO_URL, tile_mime="image/jpeg",
                                cache_prefix="ign_ortho", attribution=IGN_ORTHO_ATTRIBUTION) if gj else None
        if m:
            photo = _pack_photo_html(m)
    except Exception:  # noqa: BLE001 — la photo est un plus, jamais un bloqueur
        photo = ""
    points_cles = _points_cles_html(f["lines"])   # pitch dérivé des facteurs (forces + attentions)
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
<title>LABUSE — {f['idu']} (lecture seule)</title>{_PACK_PRINT_CSS}</head>
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
  <h1 style="font:600 18px monospace;color:#8FA69A;margin:16px 0 2px">{f['idu']}</h1>
  {f'''<p style="font:600 17px sans-serif;color:#ECF5EF;margin:2px 0 0">{f["adresse"]}</p>''' if f.get("adresse") else ""}
  <p style="color:#8FA69A;font-size:12px;margin:3px 0 0">{f['surface_m2'] or '?'} m² · {f['commune']}</p>
  {photo}
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
  {points_cles}
  <p style="font:10px monospace;letter-spacing:1.5px;color:#5C7268;margin:18px 0 4px">DÉTAIL SOURCÉ</p>
  <p style="font:10.5px sans-serif;color:#5C7268;margin:0 0 6px">Chaque donnée porte sa source — pour le promoteur qui vérifie.</p>
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
