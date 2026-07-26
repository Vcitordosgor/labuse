"""M22-B — LETTRE DE VÉRIFICATION DE ZONAGE : l'attestation courte que personne ne fait.

2-3 pages print, sobres (briques M22-0, thème clair) — une ATTESTATION, pas une plaquette :
 · identification : parcelle (IDU, adresse BAN, surface, commune), date d'édition ;
 · zonage : zone(s) du PLU applicables, intitulé exact + référence du document d'urbanisme
   (nom du PLU, date d'approbation quand elle est calibrée, identifiant GPU sinon) ;
 · règles principales de la zone, CHACUNE AVEC SON ARTICLE (hauteur, emprise, reculs,
   pleine terre, stationnement) — telles que calibrées (`config/plu_<commune>.yaml`,
   clés `*_src`). RÈGLE D'OR : une règle sans article ne s'imprime PAS ;
 · servitudes et prescriptions cartographiées touchant la parcelle — celles EN BASE
   uniquement (jamais « aucune servitude » : on n'affirme pas l'absence du non-modélisé) ;
 · encadré de LIMITES : la lettre n'est pas un certificat d'urbanisme (art. L.410-1,
   seul opposable) ; la taille minimale de lot n'est pas modélisée → « non vérifiée ».

Interdits (mandat) : affirmer l'absence d'une contrainte non modélisée ; le mot
« opposable » appliqué à la lettre elle-même ; toute règle sans son article.
Quota : hors périmètre M22 — point de branchement documenté dans le rapport
(plans.acces("dossier_parcelle") + usage_compteurs, comme api/dossier.py).
"""
from __future__ import annotations

import logging
from datetime import date

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from . import briques_pdf as bq
from .briques_pdf import esc

log = logging.getLogger("labuse.lettre_zonage")
router = APIRouter(prefix="/lettre-zonage", tags=["lettre-zonage"])

LIBELLE = ("Lettre de vérification de zonage établie à partir des documents d'urbanisme tels que "
           "numérisés (GPU / PLU calibré LABUSE) — ne constitue pas un certificat d'urbanisme "
           "(art. L.410-1 du code de l'urbanisme). À vérifier en mairie.")

LIMITES = ("Cette lettre reflète les documents d'urbanisme tels que numérisés à la date d'édition. "
           "Elle ne constitue pas un certificat d'urbanisme au sens de l'art. L.410-1 du code de "
           "l'urbanisme, seul opposable. La taille minimale de lot n'est pas une donnée "
           "modélisée : non vérifiée.")


def get_db():
    from .app import get_db as _g
    yield from _g()


# ───────────────────────── règles calibrées → lignes (article OBLIGATOIRE) ─────────────────────────

def _fmt_regle(valeur, unite: str, src: str | None) -> tuple[str, str] | None:
    """(valeur affichée, article) ou None si la ligne ne DOIT pas s'imprimer.
    - nombre → « 12 m » ; texte (ex. stationnement) → tel quel ;
    - 'a_verifier' → « à vérifier — règlement ambigu pour cette sous-zone » ;
    - None AVEC source → « non réglementé » (l'article le dit, ex. Art. 9 « il n'est pas
      fixé de règle ») ; None SANS source → pas de ligne (on n'invente ni règle ni article)."""
    from ..faisabilite.plu_rules import A_VERIFIER
    if not src:
        return None
    if valeur == A_VERIFIER:
        return ("à vérifier — règlement ambigu pour cette sous-zone", src)
    if valeur is None:
        return ("non réglementé", src)
    if isinstance(valeur, (int, float)):
        v = f"{valeur:g}{(' ' + unite) if unite else ''}"
    else:
        v = str(valeur)
    return (v, src)


def _regles_zone(code: str, commune: str | None) -> dict:
    """Règles calibrées d'une zone, chacune avec son article — via le MÊME resolver que la
    faisabilité (`resolve_zone`, YAML `*_src`). `calibree=False` → repli honnête (pas de règles)."""
    from ..faisabilite.plu_rules import resolve_zone
    r = resolve_zone(code, commune)
    if r is None or not r.calibree:
        return {"calibree": False, "code": code, "lignes": [], "notes": [], "prospect": False}
    src = r.sources or {}
    lignes: list[tuple[str, str, str]] = []          # (règle, valeur, article)
    hauteur = None
    if r.he_m is not None or r.hf_m is not None:
        parts = []
        if r.he_m is not None:
            parts.append(f"égout {r.he_m:g} m" if isinstance(r.he_m, (int, float)) else f"égout {r.he_m}")
        if r.hf_m is not None:
            parts.append(f"faîtage {r.hf_m:g} m" if isinstance(r.hf_m, (int, float)) else f"faîtage {r.hf_m}")
        hauteur = _fmt_regle(" · ".join(parts), "", src.get("hauteur"))
    for label, item in [
        ("Hauteur maximale", hauteur),
        ("Emprise au sol", _fmt_regle(r.emprise_sol_pct, "%", src.get("emprise"))),
        ("Recul / voirie", _fmt_regle(r.recul_voirie_m, "m", src.get("recul_voirie"))),
        ("Recul / limites séparatives", _fmt_regle(r.recul_limites_sep_m, "m", src.get("recul_limites"))),
        ("Pleine terre", _fmt_regle(r.pleine_terre_pct, "%", src.get("pleine_terre"))),
        ("Stationnement", _fmt_regle(r.stat_logement, "", src.get("stat"))),
    ]:
        if item:
            lignes.append((label, item[0], item[1]))
    notes = list(r.notes or [])
    if r.raw.get("hauteur_note"):
        notes.insert(0, str(r.raw["hauteur_note"]))
    return {"calibree": True, "code": code, "lignes": lignes, "notes": notes,
            "prospect": r.hauteur_mode == "prospect"}


# ───────────────────────── sections HTML (layout attestation) ─────────────────────────

def _identification(p: dict, rap: dict) -> str:
    rows = [("Références cadastrales", f"{p['idu']} · section {p['section']} n° {p['numero']}"),
            ("Commune", p["commune"]),
            ("Surface du terrain (cadastre)", f"{p['surface_m2']:.0f} m²")]
    if rap.get("adresse"):
        rows.append(("Adresse (Base Adresse Nationale)", rap["adresse"]))
    rows.append(("Date d'édition", date.today().strftime("%d/%m/%Y")))
    table = "".join(f"<tr><td style='width:38%'>{esc(k)}</td><td>{esc(v)}</td></tr>" for k, v in rows)
    return (f"<h1>Lettre de vérification de zonage</h1>"
            f"<p class='cover-sub'>Parcelle {esc(p['idu'])} — {esc(p['commune'])}</p>"
            f"<div class='bandeau'>{LIBELLE}</div>"
            f"<h2>1 · Identification</h2><table>{table}</table>"
            f"{bq.map_html(p['geojson'], ign=True)}")


def _zonage(zones: list[dict], commune: str | None) -> str:
    from ..plu_reglement import resolve_reglement
    if not zones:
        return ("<h2>2 · Zonage applicable</h2><p class='note'>Zonage non résolu dans les couches "
                "numérisées (GPU) à la date d'édition — vérification en mairie indispensable.</p>")
    rows, docs = [], {}
    for z in zones:
        code = z.get("libelle") or z.get("classe") or "—"
        reg = resolve_reglement(commune, str(code), z.get("idurba")) or {}
        nom = reg.get("document")                      # nom du PDF règlement (calibré) ou None
        if nom:
            approb = reg.get("approbation")
            docs[nom] = f"{nom}" + (f" — approuvé le {approb}" if approb else "")
        ref_doc = nom or (f"GPU {z['idurba']}" if z.get("idurba") else "document non calibré")
        rows.append(f"<tr><td><b>{esc(code)}</b></td><td class='n'>{esc(z.get('pct'))} %</td>"
                    f"<td>{esc(ref_doc)}</td></tr>")
    body = (f"<h2>2 · Zonage applicable</h2>"
            f"<table><tr><th>Zone (intitulé du règlement)</th><th class='n'>Part de la parcelle</th>"
            f"<th>Document d'urbanisme</th></tr>{''.join(rows)}</table>")
    if docs:
        body += "<p class='note'>" + " · ".join(esc(d) for d in docs.values()) + "</p>"
    body += ("<p class='note'>Source zonage : Géoportail de l'urbanisme (GPU), couche numérisée "
             "intersectée avec la géométrie cadastrale de la parcelle.</p>")
    return body


def _regles(zones: list[dict], commune: str | None) -> str:
    body = "<h2>3 · Règles principales des zones (avec leurs articles)</h2>"
    imprimees = 0
    for z in zones[:3]:
        code = z.get("libelle") or z.get("classe")
        if not code:
            continue
        rz = _regles_zone(str(code), commune)
        if not rz["calibree"]:
            body += (f"<h3>Zone {esc(code)}</h3><p class='note'>Règlement non calibré pour cette "
                     f"zone/commune : règles non vérifiées — se reporter au règlement écrit "
                     f"(consultable sur le Géoportail de l'urbanisme).</p>")
            continue
        if not rz["lignes"]:
            continue
        rows = "".join(f"<tr><td>{esc(l)}</td><td>{esc(v)}</td><td class='note'>{esc(a)}</td></tr>"
                       for l, v, a in rz["lignes"])
        body += (f"<h3>Zone {esc(code)}</h3>"
                 f"<table><tr><th>Règle</th><th>Valeur calibrée</th><th>Article / page du règlement</th></tr>"
                 f"{rows}</table>")
        if rz["prospect"]:
            body += ("<p class='note'>Hauteur en prospect : la hauteur admissible dépend de la largeur "
                     "de la voie au droit de la parcelle (L ≥ H) — valeur par parcelle, pas par zone.</p>")
        for n in rz["notes"][:2]:
            body += f"<p class='note'>{esc(n)}</p>"
        imprimees += 1
    if imprimees:
        body += ("<p class='note'>Valeurs calibrées par LABUSE depuis le règlement écrit cité — le "
                 "règlement complet (dispositions générales, renvois, annexes) peut les compléter.</p>")
    return body


def _servitudes(rap: dict) -> str:
    items: list[tuple[str, str, str]] = []
    for it in (rap.get("identite") or {}).get("prescriptions", []):
        items.append(("Prescription PLU", it.get("libelle") or "—", it.get("code") or ""))
    for it in (rap.get("risques") or {}).get("couches", []):
        items.append(("Risque cartographié", it.get("label") or "—", it.get("detail") or ""))
    for it in (rap.get("patrimoine") or {}).get("couches", []):
        items.append(("Servitude / protection", it.get("label") or "—", it.get("detail") or ""))
    for m in (rap.get("patrimoine") or {}).get("abf", []) or []:
        items.append(("Patrimoine", "Abords de monument historique (~500 m) — avis ABF probable",
                      m.get("name") or ""))
    body = "<h2>4 · Servitudes et prescriptions cartographiées</h2>"
    if items:
        rows = "".join(f"<tr><td>{esc(t)}</td><td>{esc(l)}</td><td>{esc(d)}</td></tr>"
                       for t, l, d in items)
        body += f"<table><tr><th>Nature</th><th>Élément</th><th>Détail</th></tr>{rows}</table>"
        body += ("<p class='note'>Liste limitée aux couches numérisées en base à la date d'édition "
                 "— elle ne vaut pas état exhaustif des servitudes.</p>")
    else:
        body += ("<p class='note'>Aucun élément dans les couches numérisées en base à la date "
                 "d'édition — ce constat ne vaut pas absence de servitude : seules les servitudes "
                 "cartographiées et ingérées sont vérifiées ici.</p>")
    return body


def _limites(rap: dict) -> str:
    src_rows = "".join(
        f"<tr><td>{esc(s.get('source'))}</td><td>{esc(s.get('millesime'))}</td></tr>"
        for s in (rap.get("sources") or [])
        if s.get("section") in ("identite", "risques", "patrimoine", "adresse"))
    body = (f"<h2>5 · Limites de la présente lettre</h2>"
            f"<div class='bandeau'>{LIMITES}</div>")
    if src_rows:
        body += (f"<h3>Sources et millésimes</h3>"
                 f"<table><tr><th>Source</th><th>Millésime / synchronisation</th></tr>{src_rows}</table>")
    return body


# ───────────────────────── endpoint ─────────────────────────

def _build_pdf(db: Session, idu: str) -> bytes:
    from ..flash.data import collect_report_data
    from sqlalchemy import text as _t
    row = db.execute(_t(
        "SELECT idu, commune, section, numero, round(surface_m2) AS surface_m2, "
        "ST_AsGeoJSON(geom, 7) AS geojson FROM parcels WHERE idu = :i"), {"i": idu}).mappings().first()
    if not row:
        from fastapi import HTTPException
        raise HTTPException(404, f"Parcelle {idu} inconnue.")
    p = dict(row)
    rap = collect_report_data(db, idu) or {}
    zones = (rap.get("identite") or {}).get("zones", [])
    sections = [
        _identification(p, rap),
        _zonage(zones, p.get("commune")),
        _regles(zones, p.get("commune")),
        _servitudes(rap),
        _limites(rap),
    ]
    pdf = bq.render_pdf(sections, LIBELLE)
    log.info("lettre zonage %s générée (%d ko)", idu, len(pdf) // 1024)
    return pdf


@router.get("/{idu}.pdf")
def lettre_zonage_pdf(idu: str, db: Session = Depends(get_db)) -> Response:
    """Sert la lettre de vérification de zonage (synchrone : document court)."""
    pdf = _build_pdf(db, idu)
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="lettre_zonage_{idu}.pdf"'})
