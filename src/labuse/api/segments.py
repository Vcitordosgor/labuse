"""API du MOTEUR DE SEGMENTS Habitat (Lot 1/3/4/5 backend).

- GET  /segments                    presets + disponibilité + registry de filtres + compteurs
- POST /segments/query              évalue un preset (éventuellement modifié à la volée)
- POST /segments/export             CSV « à l'occupant » (RGPD : zéro donnée nominative)
- POST /segments/presets            admin (Vic) : créer / dupliquer
- PUT  /segments/presets/{slug}     admin : éditer (argumentaire, filtres, actif…)
- DELETE /segments/presets/{slug}   admin : supprimer
- POST /segments/refresh-counts     recalcul des compteurs (bouton admin + job)

SÉCURITÉ : aucune requête SQL construite depuis du texte client — les clés passent
par le registry (segments/registry.py), les valeurs par des paramètres bindés.
Un preset modifié à la volée n'est JAMAIS persisté ; la sauvegarde passe par les
routes admin. L'app étant mono-utilisateur authentifié (Vic — cf. api/auth.py), les
routes admin sont couvertes par le même garde que le reste ; en local, auth off.
"""
from __future__ import annotations

import csv
import io
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..segments import catnat as catnat_mod
from ..segments import engine as seg
from ..segments import presets as presets_mod
from ..segments import residuel_bati
from ..segments.registry import (EXPORT_COLS, FILTERS, SORTS,
                                 compute_availability)

router = APIRouter(prefix="/segments", tags=["segments"])


def get_db():
    from .app import get_db as _g
    yield from _g()


def ensure_tables(engine) -> None:
    """Tables du moteur + seed des presets manquants (jamais d'écrasement d'édition admin)."""
    presets_mod.ensure_tables(engine)
    catnat_mod.ensure_tables(engine)
    residuel_bati.ensure_tables(engine)
    from sqlalchemy.orm import Session as _S
    with _S(engine) as s:
        presets_mod.seed_presets(s)
        s.commit()


# ───────────────────────── lecture ─────────────────────────

@router.get("")
def segments_home(db: Session = Depends(get_db)) -> dict:
    """Galerie : presets par catégorie, disponibilité (complet/partiel), compteurs
    (cache 24 h — recalcul par /segments/refresh-counts ou le job), registry de
    filtres pour le query builder (filtres indisponibles = grisés côté UI)."""
    avail = compute_availability(db)
    cnts = presets_mod.counts(db)
    cat = catnat_mod.communes_recentes(db)
    out = []
    for p in presets_mod.list_presets(db):
        dispo, inactifs = presets_mod.preset_disponibilite(p, avail)
        out.append({**p,
                    "disponibilite": dispo, "filtres_inactifs": inactifs,
                    "count": cnts.get(p["slug"], {}).get("n"),
                    "count_at": (cnts.get(p["slug"], {}).get("computed_at") or None)})
    return {
        "categories": presets_mod.CATEGORIES,
        "presets": out,
        "filtres": [{
            "cle": f.cle, "libelle": f.libelle, "type": f.type, "unite": f.unite,
            "groupe": f.groupe, "enum_values": list(f.enum_values),
            "description": f.description,
            **avail.get(f.cle, {"disponible": True, "raison": None, "mandat": None}),
        } for f in FILTERS.values()],
        "tris": [{"cle": s.cle, "libelle": s.libelle} for s in SORTS.values()],
        "colonnes_export": [{"cle": k, "libelle": v[0]} for k, v in EXPORT_COLS.items()],
        "catnat": cat,
        "libelle_residuel": residuel_bati.LIBELLE_UI,
    }


class QueryIn(BaseModel):
    slug: str | None = None                       # preset de départ (filtres par défaut)
    filtres: list[dict] | None = None             # override « à la volée » (jamais persisté)
    tri: str | None = None
    colonnes_export: list[str] | None = None
    limit: int = Field(100, ge=1, le=seg.MAX_LIMIT)
    offset: int = Field(0, ge=0)
    geojson: bool = False


def _resolve_body(db: Session, body: QueryIn) -> tuple[list[dict], str | None, list[str]]:
    filtres, tri, cols = body.filtres, body.tri, body.colonnes_export
    if body.slug:
        p = presets_mod.get_preset(db, body.slug)
        if p is None:
            raise HTTPException(404, f"preset inconnu : {body.slug}")
        filtres = filtres if filtres is not None else (p["filtres"] or [])
        tri = tri or p.get("tri_defaut")
        cols = cols if cols is not None else (p["colonnes_export"] or [])
    return filtres or [], tri, cols or []


@router.post("/query")
def segments_query(body: QueryIn, db: Session = Depends(get_db)) -> dict:
    filtres, tri, cols = _resolve_body(db, body)
    try:
        q = seg.build(db, filtres, tri, colonnes_export=cols)
    except seg.FiltreInvalide as exc:
        raise HTTPException(422, str(exc))
    count = seg.run_count(db, q)
    items = seg.run_items(db, q, body.limit, body.offset)
    resp: dict[str, Any] = {
        "count": count, "items": items, "tri": q.tri,
        "filtres_actifs": q.actifs, "filtres_inactifs": q.inactifs,
        "colonnes": [{"cle": k, "libelle": h} for k, h in q.export_cols],
        "limit": body.limit, "offset": body.offset,
    }
    if body.geojson:
        rows = seg.run_items(db, q, seg.MAX_GEOJSON, 0)
        resp["geojson"] = {
            "type": "FeatureCollection",
            "features": [{"type": "Feature",
                          "geometry": {"type": "Point", "coordinates": [r["lon"], r["lat"]]},
                          "properties": {"idu": r["idu"], "commune": r["commune"]}}
                         for r in rows if r.get("lon") is not None],
        }
    return resp


@router.post("/export")
def segments_export(body: QueryIn, db: Session = Depends(get_db)) -> Response:
    """Export CSV « à l'occupant » : adresse (si connue), commune, caractéristiques du
    preset — JAMAIS de nom de personne physique (RGPD). En-têtes en français lisible
    (c'est l'artisan qui ouvre ce fichier dans Excel)."""
    filtres, tri, cols = _resolve_body(db, body)
    try:
        q = seg.build(db, filtres, tri, colonnes_export=cols)
    except seg.FiltreInvalide as exc:
        raise HTTPException(422, str(exc))
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")           # Excel FR : point-virgule
    headers = ["Parcelle (IDU)", "Commune", "Surface parcelle (m²)"] + \
              [h for k, h in q.export_cols if k != "surface_m2"]
    w.writerow(headers)
    n = 0
    for r in seg.run_export_rows(db, q):
        row = [r["idu"], r["commune"], r["surface_m2"]]
        for k, _h in q.export_cols:
            if k == "surface_m2":
                continue
            v = r.get(k)
            if isinstance(v, bool):
                v = "oui" if v else "non"
            row.append(v if v is not None else "")
        w.writerow(row)
        n += 1
    name = (body.slug or "segment").replace("/", "-")
    return Response(
        buf.getvalue().encode("utf-8-sig"),      # BOM : accents corrects dans Excel
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{name}_occupants.csv"',
                 "X-Rows": str(n)})


# ───────────────────────── admin (Vic) ─────────────────────────

class PresetIn(BaseModel):
    slug: str = Field(min_length=2, max_length=60, pattern=r"^[a-z0-9][a-z0-9-]*$")
    nom: str
    categorie: str
    description: str | None = None
    argumentaire: str | None = None
    filtres: list[dict] = []
    colonnes_export: list[str] = []
    tri_defaut: str | None = None
    boost_catnat: bool = False
    actif: bool = True
    ordre: int = 100
    copie_de: str | None = None                   # duplication : slug source


@router.post("/presets")
def preset_create(body: PresetIn, db: Session = Depends(get_db)) -> dict:
    if presets_mod.get_preset(db, body.slug):
        raise HTTPException(409, f"slug déjà pris : {body.slug}")
    data = body.model_dump(exclude={"copie_de"})
    if body.copie_de:
        src = presets_mod.get_preset(db, body.copie_de)
        if src is None:
            raise HTTPException(404, f"preset source inconnu : {body.copie_de}")
        for k in ("categorie", "description", "argumentaire", "filtres",
                  "colonnes_export", "tri_defaut", "boost_catnat"):
            if not data.get(k):
                data[k] = src[k]
    try:
        return presets_mod.upsert_preset(db, data, created_by="admin")
    except seg.FiltreInvalide as exc:
        raise HTTPException(422, str(exc))


@router.put("/presets/{slug}")
def preset_update(slug: str, body: PresetIn, db: Session = Depends(get_db)) -> dict:
    if presets_mod.get_preset(db, slug) is None:
        raise HTTPException(404, f"preset inconnu : {slug}")
    if body.slug != slug:
        raise HTTPException(422, "le slug ne se renomme pas (dupliquer puis supprimer)")
    try:
        return presets_mod.upsert_preset(db, body.model_dump(exclude={"copie_de"}),
                                         created_by="admin")
    except seg.FiltreInvalide as exc:
        raise HTTPException(422, str(exc))


@router.delete("/presets/{slug}")
def preset_delete(slug: str, db: Session = Depends(get_db)) -> dict:
    if presets_mod.get_preset(db, slug) is None:
        raise HTTPException(404, f"preset inconnu : {slug}")
    db.execute(text("DELETE FROM segment_presets WHERE slug = :s"), {"s": slug})
    db.execute(text("DELETE FROM segment_preset_counts WHERE slug = :s"), {"s": slug})
    return {"supprime": slug}


@router.post("/refresh-counts")
def refresh_counts(stale_hours: float | None = 24.0, db: Session = Depends(get_db)) -> dict:
    """Recalcule les compteurs par preset (cache 24 h). `stale_hours=0` force tout."""
    done = presets_mod.refresh_counts(
        db, only_stale_hours=None if not stale_hours else stale_hours)
    return {"recalcules": done}
