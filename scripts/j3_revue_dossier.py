#!/usr/bin/env python
"""PHASE 0 J3 étape 1-bis — DOSSIER DE REVUE des propositions golden (LECTURE SEULE).

Pour CHAQUE proposition : (a) vignette ortho IGN + contour parcelle (build_situation_map) ; (b) IDU,
commune, tier/verdict servi, motif ; (c) 2-3 sources tracées décisives avec leurs valeurs ; (d) lien
fiche locale. PLUS trois CONTRE-VÉRIFICATIONS automatiques affichées :
  1. la source tracée existe en base ;
  2. le verdict RECALCULÉ sur la parcelle isolée (cascade, persist=False) == le verdict servi ;
  3. pour les motifs géométriques, une mesure PostGIS DIRECTE (hors cascade) concorde.
Tout écart = drapeau rouge. Assemblé en HTML (→ PDF via weasyprint), NÉGATIVES d'abord.

Usage : python scripts/j3_revue_dossier.py [--limit N] [--no-pdf]
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

from sqlalchemy import text

from labuse.db import session_scope

RUN = "q_v6_m8"
PROP = Path("docs/golden/PROPOSITION_GOLDEN_120.md")
OUT_DIR = Path("reports/j3-revue")
TILE_CACHE = OUT_DIR / "_tiles"

MOTIF_LABEL = {"eau": "eau/hydrographie", "zonage_plu_gpu": "zone A/N inconstructible",
               "risques": "PPR/aléa fort", "pente": "pente forte", "surface": "micro-surface",
               "osm_faux_positif": "OSM faux positif", "foncier_public": "foncier public",
               "emprise_lineaire": "emprise linéaire (délaissé)", "emprise_routiere": "emprise routière",
               "prescription_plu": "prescription PLU (ER/EBC)"}
LABEL_MOTIF = {v: k for k, v in MOTIF_LABEL.items()}
NEG_TIERS = {"ecartee"}


def parse_proposition() -> list[dict]:
    """Lit les lignes du tableau de la proposition committée (source de vérité de la revue)."""
    out = []
    for ln in PROP.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*\d+\s*\|\s*`([^`]+)`\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|", ln)
        if m:
            idu, commune, tier, motif_lbl, edge = (x.strip() for x in m.groups())
            out.append({"idu": idu, "commune": commune, "tier": tier,
                        "motif": LABEL_MOTIF.get(motif_lbl), "motif_lbl": motif_lbl,
                        "edge": None if edge == "—" else edge})
    return out


def served(session, idu: str) -> dict:
    r = session.execute(text(
        "SELECT p.id pid, d.status, d.matrice_statut, s2.tier "
        "FROM parcels p LEFT JOIN dryrun_parcel_evaluations d ON d.parcel_id=p.id AND d.run_label=:r "
        "LEFT JOIN parcel_p_score_v2 s2 ON s2.parcelle_id=p.idu AND s2.run_id=:r "
        "WHERE p.idu=:i"), {"r": RUN, "i": idu}).mappings().first()
    return dict(r) if r else {}


def traced_sources(session, pid: int) -> list[dict]:
    """Sources décisives : les HARD_EXCLUDE d'abord, puis les SOFT_FLAG forts, avec leur détail."""
    rows = session.execute(text(
        "SELECT layer_name, result, detail FROM dryrun_cascade_results "
        "WHERE run_label=:r AND parcel_id=:p AND result IN ('HARD_EXCLUDE','SOFT_FLAG') "
        "ORDER BY (result='HARD_EXCLUDE') DESC, layer_name"), {"r": RUN, "p": pid}).mappings().all()
    return [dict(x) for x in rows][:4]


def geo_recheck(session, pid: int, motif: str) -> tuple[str, bool | None]:
    """Mesure PostGIS DIRECTE (hors cascade) selon le motif. Renvoie (texte, concorde|None)."""
    def q(sql):
        return session.execute(text(sql), {"p": pid}).first()
    if motif == "surface":
        r = q("SELECT round(ST_Area(geom_2975)) FROM parcels WHERE id=:p")
        return (f"surface PostGIS = {int(r[0])} m²", None) if r else ("—", None)
    if motif == "pente":
        r = q("SELECT round(pente_moy_deg::numeric,1) FROM parcel_terrain t "
              "JOIN parcels p ON p.idu=t.idu WHERE p.id=:p")
        return (f"pente_moy = {r[0]}°" if r and r[0] is not None else "pente non mesurée", None)
    if motif in ("eau", "zonage_plu_gpu", "osm_faux_positif", "parc_national", "prescription_plu"):
        kind = {"eau": "('water','ravine')", "zonage_plu_gpu": "('plu_gpu_zone')",
                "osm_faux_positif": "('osm_faux_positif')", "parc_national": "('parc_national')",
                "prescription_plu": "('plu_gpu_prescription')"}[motif]
        r = q(f"SELECT round(100*ST_Area(ST_Intersection(ST_Union(sl.geom_2975), p.geom_2975))"
              f"/NULLIF(ST_Area(p.geom_2975),0)) FROM parcels p JOIN spatial_layers sl "
              f"ON sl.kind IN {kind} AND ST_Intersects(sl.geom_2975,p.geom_2975) WHERE p.id=:p "
              f"GROUP BY p.geom_2975")
        return (f"recouvrement PostGIS ≈ {int(r[0])} %" if r and r[0] is not None
                else "aucune couche intersectée", bool(r and r[0] and r[0] > 0))
    if motif == "foncier_public":
        r = q("SELECT pm.groupe, pm.denomination FROM parcelle_personne_morale pm "
              "JOIN parcels p ON p.idu=pm.idu WHERE p.id=:p")
        ok = bool(r and r[0] in (1, 2, 3, 4, 9))
        return (f"DGFiP groupe {r[0]} ({r[1]})" if r else "aucune PM publique", ok)
    return ("mesure via cascade (motif non géométrique direct)", None)


def recompute_verdict(session, pid: int) -> str | None:
    """Verdict RECALCULÉ sur la parcelle isolée (cascade actuelle, AUCUNE écriture)."""
    from labuse.cascade import evaluate_parcels
    try:
        out = evaluate_parcels([pid], session, persist=False)
        return out[0].status if out else None
    except Exception as exc:  # noqa: BLE001
        return f"ERREUR({type(exc).__name__})"


def build_card(session, p: dict, with_ortho: bool) -> dict:
    sv = served(session, p["idu"])
    pid = sv.get("pid")
    srcs = traced_sources(session, pid) if pid else []
    geo_txt, geo_ok = geo_recheck(session, pid, p["motif"]) if (pid and p["motif"]) else ("—", None)
    recompute = recompute_verdict(session, pid) if pid else None
    verdict_ok = (recompute == sv.get("status"))
    src_exists = len(srcs) > 0
    flags = []
    if not src_exists:
        flags.append("aucune source tracée en base")
    if not verdict_ok:
        flags.append(f"verdict recalculé « {recompute} » ≠ servi « {sv.get('status')} »")
    if geo_ok is False:
        flags.append("mesure PostGIS ne confirme pas le motif")
    ortho = None
    if with_ortho and pid:
        ortho = build_ortho(session, pid)
    return {**p, "served": sv, "sources": srcs, "geo_txt": geo_txt, "geo_ok": geo_ok,
            "recompute": recompute, "verdict_ok": verdict_ok, "src_exists": src_exists,
            "flags": flags, "ortho": ortho,
            "is_neg": (p["tier"] in NEG_TIERS or sv.get("status") in ("exclue", "faux_positif_probable"))}


def build_ortho(session, pid: int):
    from labuse.flash.carte import IGN_ORTHO_ATTRIBUTION, IGN_ORTHO_URL, build_situation_map
    gj = session.execute(text("SELECT ST_AsGeoJSON(ST_Transform(geom,4326)) FROM parcels WHERE id=:p"),
                         {"p": pid}).scalar()
    if not gj:
        return None
    return build_situation_map(gj, TILE_CACHE, tile_url=IGN_ORTHO_URL, tile_mime="image/jpeg",
                               cache_prefix="ortho", attribution=IGN_ORTHO_ATTRIBUTION)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--no-pdf", action="store_true")
    ap.add_argument("--no-ortho", action="store_true")
    args = ap.parse_args()

    props = parse_proposition()
    if args.limit:
        props = props[:args.limit]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    TILE_CACHE.mkdir(parents=True, exist_ok=True)

    cards = []
    with session_scope() as session:
        session.execute(text("SET TRANSACTION READ ONLY"))
        for i, p in enumerate(props, 1):
            cards.append(build_card(session, p, with_ortho=not args.no_ortho))
            if i % 10 == 0:
                print(f"  … {i}/{len(props)}")

    cards.sort(key=lambda c: (not c["is_neg"], c["idu"]))     # NÉGATIVES d'abord
    n_flags = sum(1 for c in cards if c["flags"])
    from labuse.flash import report as _  # noqa: F401  (garantit l'accès au module templates)
    html = render_html(cards)
    (OUT_DIR / "DOSSIER-REVUE-J3.html").write_text(html, encoding="utf-8")
    print(f"→ reports/j3-revue/DOSSIER-REVUE-J3.html  ({len(cards)} cartes, {n_flags} avec drapeau)")
    if not args.no_pdf:
        try:
            from weasyprint import HTML
            HTML(string=html, base_url=".").write_pdf(str(OUT_DIR / "DOSSIER-REVUE-J3.pdf"))
            print("→ reports/j3-revue/DOSSIER-REVUE-J3.pdf")
        except Exception as exc:  # noqa: BLE001
            print(f"PDF non généré ({type(exc).__name__}: {exc}) — HTML disponible")


def render_html(cards: list[dict]) -> str:
    from html import escape
    css = """
    body{font-family:-apple-system,Segoe UI,Roboto,sans-serif;color:#1a1a1a;margin:0;padding:20px;font-size:12px}
    h1{font-size:20px} h2{font-size:15px;border-bottom:2px solid #333;margin-top:28px}
    .card{border:1px solid #ccc;border-radius:8px;padding:12px;margin:10px 0;page-break-inside:avoid;display:flex;gap:14px}
    .map{width:220px;height:150px;position:relative;overflow:hidden;border:1px solid #999;border-radius:4px;flex-shrink:0;background:#eef}
    .map img{position:absolute;width:256px;height:256px}
    .map svg{position:absolute;inset:0}
    .body{flex:1}
    .idu{font-family:monospace;font-weight:bold;font-size:13px}
    .tier{display:inline-block;padding:1px 7px;border-radius:10px;font-size:11px;font-weight:bold}
    .ecartee{background:#f5d5d0;color:#a03020} .a_creuser{background:#e8e0c0;color:#806010}
    .chaude,.brulante{background:#d0f0dd;color:#106040} .reserve_fonciere{background:#d5e5f5;color:#204080}
    .src{font-size:11px;color:#333;margin:2px 0} .val{color:#0a5}
    .verif{margin-top:6px;font-size:11px} .ok{color:#0a7}.bad{color:#c00;font-weight:bold}
    .flag{background:#ffe0e0;border:1px solid #c00;color:#900;padding:4px 8px;border-radius:4px;margin-top:6px;font-weight:bold}
    .val-field{margin-top:6px;font-size:11px;color:#555}
    """

    def card_html(c):
        sv = c["served"]
        m = c["ortho"]
        map_html = '<div class="map">'
        if m:
            for t in m["tiles"]:
                map_html += f'<img src="{t["data_uri"]}" style="left:{t["left"]}px;top:{t["top"]}px">'
            map_html += f'<svg viewBox="0 0 {m["width"]} {m["height"]}">'
            for poly in m["polygons"]:
                map_html += f'<polygon points="{poly}" fill="rgba(240,80,40,.25)" stroke="#f04028" stroke-width="2"/>'
            map_html += "</svg>"
        else:
            map_html += '<div style="padding:40px 10px;text-align:center;color:#888">ortho indisponible</div>'
        map_html += "</div>"
        src = "".join(
            f'<div class="src">• <b>{escape(s["layer_name"])}</b> [{s["result"]}] — {escape((s["detail"] or "")[:120])}</div>'
            for s in c["sources"]) or '<div class="src" style="color:#c00">aucune source tracée</div>'
        v1 = f'<span class="{"ok" if c["src_exists"] else "bad"}">① source en base : {"OUI" if c["src_exists"] else "NON"}</span>'
        v2 = f'<span class="{"ok" if c["verdict_ok"] else "bad"}">② verdict recalculé isolé « {escape(str(c["recompute"]))} » ' \
             f'{"=" if c["verdict_ok"] else "≠"} servi « {escape(str(sv.get("status")))} »</span>'
        geo_cls = "ok" if c["geo_ok"] else ("bad" if c["geo_ok"] is False else "")
        v3 = f'<span class="{geo_cls}">③ mesure PostGIS directe : {escape(c["geo_txt"])}</span>'
        flags = "".join(f'<div class="flag">⚠ {escape(f)}</div>' for f in c["flags"])
        fiche = f'http://127.0.0.1:8010/parcels/{c["idu"]}?source={RUN}'
        return f"""<div class="card">{map_html}<div class="body">
          <div><span class="idu">{escape(c["idu"])}</span> — {escape(c["commune"])} ·
             <span class="tier {escape(c["tier"])}">{escape(c["tier"])}</span> ·
             motif <b>{escape(c["motif_lbl"])}</b>{f" · <i>{escape(c['edge'])}</i>" if c["edge"] else ""}</div>
          <div style="margin-top:4px">{src}</div>
          <div class="verif">{v1}<br>{v2}<br>{v3}</div>
          {flags}
          <div class="val-field">fiche : <a href="{fiche}">{fiche}</a> · <b>validation :</b> ☐ factuelle ☐ coherence ☐ barrée</div>
        </div></div>"""

    neg = [c for c in cards if c["is_neg"]]
    pos = [c for c in cards if not c["is_neg"]]
    body = ['<h2>NÉGATIVES — attendues du gate boussole (écartées / exclues)</h2>']
    body += [card_html(c) for c in neg]
    body.append('<h2>POSITIVES / CAS LIMITES — ancres de non-régression</h2>')
    body += [card_html(c) for c in pos]
    n_flags = sum(1 for c in cards if c["flags"])
    intro = (f"<h1>Dossier de revue golden J3 — {len(cards)} propositions</h1>"
             f"<p><b>{len(neg)} négatives</b> (gate boussole) · <b>{len(pos)} positives/cas limites</b> · "
             f"<b>{n_flags} carte(s) avec drapeau rouge</b> à examiner. Contre-vérifications : ① source tracée "
             f"en base · ② verdict recalculé sur la parcelle isolée = verdict servi · ③ mesure PostGIS directe. "
             f"Cochez <i>factuelle</i> (négatives du gate boussole) ou <i>coherence</i> (ancres positives), "
             f"ou <i>barrée</i>.</p>")
    return f"<!doctype html><html><head><meta charset='utf-8'><style>{css}</style></head><body>{intro}{''.join(body)}</body></html>"


if __name__ == "__main__":
    main()
