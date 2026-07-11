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

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..segments import catnat as catnat_mod
from ..segments import engine as seg
from ..segments import presets as presets_mod
from ..segments import residuel_bati
from ..segments.registry import EXPORT_COLS, FILTERS, SORTS, compute_availability

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


# ── Mentions informatives par preset (mandat ANC & Végétation) : références VÉRIFIÉES
#    sur Légifrance le 11/07/2026, formulation factuelle courte — JAMAIS un conseil
#    juridique. Le délai d'un an est au L.271-4 CCH, pas au L.1331-11-1 CSP.
MENTIONS_LEGALES: dict[str, dict] = {
    "anc-prospection": {
        "texte": ("En cas de vente d'un logement non raccordé au réseau public de "
                  "collecte, le document de contrôle de l'installation d'assainissement "
                  "non collectif (daté de moins de 3 ans) est joint au dossier de "
                  "diagnostic technique (art. L.1331-11-1 du Code de la santé publique). "
                  "En cas de non-conformité constatée à la vente, les travaux de mise en "
                  "conformité sont réalisés par l'acquéreur dans un délai d'un an après "
                  "l'acte de vente (art. L.271-4 du Code de la construction et de "
                  "l'habitation). Source : Légifrance."),
        "liens": [
            {"texte": "Art. L.1331-11-1 CSP",
             "url": "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000043975559"},
            {"texte": "Art. L.271-4 CCH",
             "url": "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000049398848"},
        ],
        "sources_donnees": ("Probabilité ANC : INSEE, RP2022 (fichier détail Logements, "
                            "variable EGOUL) agrégé à l'IRIS — statistique, jamais un "
                            "diagnostic. Zonages officiels : Géoportail de l'urbanisme. "
                            "Contours IRIS © IGN/INSEE. Calage : Office de l'eau Réunion, "
                            "Chronique de l'eau n°149 (2025)."),
    },
    "anc-travaux": None,   # rempli ci-dessous (mêmes références)
    "elagage-limite": {
        "texte": ("Le propriétaire sur le terrain duquel avancent les branches des "
                  "arbres du voisin peut contraindre celui-ci à les couper ; les "
                  "racines, ronces et brindilles peuvent être coupées soi-même à la "
                  "limite séparative. Ce droit est imprescriptible (art. 673 du Code "
                  "civil). Source : Légifrance."),
        "liens": [
            {"texte": "Art. 673 Code civil",
             "url": "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000006430148/"},
        ],
        "sources_donnees": ("Canopée : BD ORTHO IRC (NDVI) × MNH LiDAR HD © IGN "
                            "(Licence Ouverte) — détection statistique de végétation "
                            "haute (> 3 m), pas un métré."),
    },
    "elagage": {
        "texte": ("Végétation en limite : art. 673 du Code civil (élagage des branches "
                  "qui avancent chez le voisin — droit imprescriptible). "
                  "Source : Légifrance."),
        "liens": [
            {"texte": "Art. 673 Code civil",
             "url": "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000006430148/"},
        ],
        "sources_donnees": "Canopée : BD ORTHO IRC × MNH LiDAR HD © IGN (Licence Ouverte).",
    },
}
MENTIONS_LEGALES["anc-travaux"] = MENTIONS_LEGALES["anc-prospection"]


# ───────────────────────── lecture ─────────────────────────

@router.get("")
def segments_home(inclure_inactifs: bool = False, db: Session = Depends(get_db)) -> dict:
    """Galerie : presets par catégorie, disponibilité (complet/partiel), compteurs
    (cache 24 h — recalcul par /segments/refresh-counts ou le job), registry de
    filtres pour le query builder (filtres indisponibles = grisés côté UI).

    Par défaut la galerie ne liste que les presets ACTIFS (l'offre packagée — décision
    produit du 11/07/2026 : 5 presets). Les presets désactivés restent en base (données,
    filtres du builder et signaux intacts) et se pilotent via `?inclure_inactifs=true`
    (vue admin) puis le PUT de réactivation. Le query builder complet et TOUS les filtres
    du registry restent servis ci-dessous quels que soient les presets actifs."""
    avail = compute_availability(db)
    cnts = presets_mod.counts(db)
    cat = catnat_mod.communes_recentes(db)
    out = []
    for p in presets_mod.list_presets(db, actifs_seulement=not inclure_inactifs):
        dispo, inactifs = presets_mod.preset_disponibilite(p, avail)
        out.append({**p,
                    "disponibilite": dispo, "filtres_inactifs": inactifs,
                    "mention_legale": MENTIONS_LEGALES.get(p["slug"]),
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
        "mention_legale": MENTIONS_LEGALES.get(body.slug) if body.slug else None,
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


def _rows_export(db, q) -> tuple[list[str], list[list]]:
    """Matérialise l'export (en-têtes lisibles + lignes) — commun CSV/publipostage."""
    headers = ["Parcelle (IDU)", "Commune", "Surface parcelle (m²)"] + \
              [h for k, h in q.export_cols if k != "surface_m2"]
    rows: list[list] = []
    for r in seg.run_export_rows(db, q):
        row = [r["idu"], r["commune"], r["surface_m2"]]
        for k, _h in q.export_cols:
            if k == "surface_m2":
                continue
            v = r.get(k)
            if isinstance(v, bool):
                v = "oui" if v else "non"
            row.append(v if v is not None else "")
        rows.append(row)
    return headers, rows


def _garde_export_suspendu(slug: str | None) -> None:
    """Cascade de juges (11/07) : presets piscine V0 — export commercial suspendu
    tant que le juge ML n'a pas re-certifié la précision (badge « fiabilité V0 »)."""
    from ..config import load_yaml_config

    suspendus = (load_yaml_config("detection_ortho").get("materialisation", {})
                 .get("exports_suspendus") or [])
    if slug in suspendus:
        raise HTTPException(423, f"Export suspendu pour « {slug} » : détection piscine "
                                 "en fiabilité V0 (~79 %), re-certification ML en cours. "
                                 "Consultation et carte restent ouvertes.")


@router.post("/export")
def segments_export(body: QueryIn, request: Request, db: Session = Depends(get_db)) -> Response:
    """Export CSV « à l'occupant » : adresse (si connue), commune, caractéristiques du
    preset — JAMAIS de nom de personne physique (RGPD). En-têtes en français lisible
    (c'est l'artisan qui ouvre ce fichier dans Excel).
    Watermarking (Lot 3.4) : colonne `ref` + canaris tracés dans export_fingerprints."""
    filtres, tri, cols = _resolve_body(db, body)
    try:
        q = seg.build(db, filtres, tri, colonnes_export=cols)
    except seg.FiltreInvalide as exc:
        raise HTTPException(422, str(exc))
    headers, rows = _rows_export(db, q)
    from .protection import filigrane_export, sujet_de
    filigrane_export(db, sujet_de(request), headers, rows,
                     slug=body.slug or "requete-libre")
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")           # Excel FR : point-virgule
    w.writerow(headers)
    w.writerows(rows)
    name = (body.slug or "segment").replace("/", "-")
    return Response(
        buf.getvalue().encode("utf-8-sig"),      # BOM : accents corrects dans Excel
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{name}_occupants.csv"',
                 "X-Rows": str(len(rows))})


@router.post("/publipostage")
def segments_publipostage(body: QueryIn, request: Request,
                          db: Session = Depends(get_db)) -> Response:
    """Publipostage (Lot 2A wave-adresses) : ZIP = CSV normalisé (« À l'occupant »,
    Adresse L1/L2, CP, Ville — jamais de nom de personne physique) + planches
    d'étiquettes PDF (63,5 × 38,1 configurable) + gabarit de lettre du métier.
    Seules les parcelles avec adresse BAN partent ; watermarking Lot 3 appliqué."""
    _garde_export_suspendu(body.slug)
    from ..config import get_settings, load_yaml_config
    from ..segments import publipostage as pub
    from ..segments.registry import compute_availability
    from .protection import filigrane_export, sujet_de

    avail = compute_availability(db)
    if not avail.get("adresse_ban", {}).get("disponible"):
        raise HTTPException(409, "Adresses BAN non ingérées (labuse ingest-ban) — "
                                 "le publipostage a besoin d'adresses fiables.")
    filtres, tri, cols = _resolve_body(db, body)
    # adresse exigée : filtre serveur ajouté d'office (jamais un courrier sans adresse)
    filtres = list(filtres) + [{"cle": "adresse_ban", "value": True}]
    try:
        q = seg.build(db, filtres, tri, colonnes_export=cols or ["surface_m2"])
    except seg.FiltreInvalide as exc:
        raise HTTPException(422, str(exc))
    rows = [dict(r) for r in seg.run_export_rows(db, q)]
    lignes = pub.lignes_publipostage(rows)

    headers = list(pub.ENTETES)
    ref = filigrane_export(db, sujet_de(request), headers, lignes,
                           slug=body.slug or "requete-libre", fmt="publipostage")
    gabarits = (load_yaml_config("gabarits_courrier") or {}).get("gabarits", {})
    categorie = None
    if body.slug:
        p = presets_mod.get_preset(db, body.slug)
        categorie = (p or {}).get("categorie")
    gab = gabarits.get(categorie or "", {})
    gabarit_txt = (f"{gab['titre']}\n{'=' * len(gab['titre'])}\n\n{gab['corps']}"
                   if gab else None)

    data = pub.zip_publipostage(
        pub.csv_bytes(headers, lignes),
        pub.etiquettes_pdf(lignes, fmt=get_settings().etiquettes_format, ref=ref),
        gabarit_txt)
    name = (body.slug or "segment").replace("/", "-")
    return Response(data, media_type="application/zip",
                    headers={"Content-Disposition":
                             f'attachment; filename="{name}_publipostage.zip"',
                             "X-Rows": str(len(lignes))})


@router.get("/gabarits")
def segments_gabarits() -> dict:
    """Gabarits de courrier par famille de métier (page d'aide — textes ÉDITABLES,
    hors scope juridique : le contenu envoyé reste la responsabilité du client)."""
    from ..config import load_yaml_config
    try:
        g = (load_yaml_config("gabarits_courrier") or {}).get("gabarits", {})
    except FileNotFoundError:
        g = {}
    return {"gabarits": g,
            "avertissement": "Modèles de départ à adapter — mentions obligatoires de "
                             "votre métier (SIRET, assurances) à votre charge."}


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
