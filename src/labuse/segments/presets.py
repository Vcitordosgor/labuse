"""Presets métiers (Lot 4) — seed versionné (config/segment_presets.yaml) + compteurs.

Le seed n'ÉCRASE JAMAIS un preset existant (édité en admin) : insertion des slugs
manquants uniquement. Ajouter le 31e métier = une entrée YAML (ou l'admin), zéro dev.
"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text

from .. import config
from . import engine as seg_engine
from .registry import EXPORT_COLS, FILTERS, SORTS, compute_availability

CATEGORIES = {
    "exterieur": "Extérieur", "renovation": "Rénovation", "energie": "Énergie",
    "securite": "Sécurité", "foncier_bati": "Foncier bâti",
}

DDL = """
CREATE TABLE IF NOT EXISTS segment_presets (
  id serial PRIMARY KEY,
  slug varchar(60) UNIQUE NOT NULL,
  nom varchar(120) NOT NULL,
  categorie varchar(30) NOT NULL,
  description text,
  argumentaire text,
  filtres jsonb NOT NULL DEFAULT '[]',
  colonnes_export jsonb NOT NULL DEFAULT '[]',
  tri_defaut varchar(40),
  boost_catnat boolean NOT NULL DEFAULT false,
  actif boolean NOT NULL DEFAULT true,
  ordre integer NOT NULL DEFAULT 100,
  created_by varchar(60) DEFAULT 'seed',
  updated_at timestamptz DEFAULT now()
);
CREATE TABLE IF NOT EXISTS segment_preset_counts (
  slug varchar(60) PRIMARY KEY,
  n integer,
  computed_at timestamptz DEFAULT now()
)
"""


def ensure_tables(engine) -> None:
    with engine.begin() as c:
        for stmt in DDL.split(";"):
            if stmt.strip():
                c.execute(text(stmt))


def validate_preset(p: dict) -> list[str]:
    """Erreurs de contrat d'un preset (clés de filtres/tri/colonnes inconnues)."""
    errs: list[str] = []
    if not p.get("slug") or not p.get("nom"):
        errs.append("slug et nom requis")
    if p.get("categorie") not in CATEGORIES:
        errs.append(f"categorie inconnue : {p.get('categorie')!r}")
    for f in p.get("filtres") or []:
        subs = f.get("ou") if isinstance(f, dict) and "ou" in f else [f]
        if not isinstance(subs, list):
            errs.append("« ou » : liste attendue")
            continue
        for s in subs:
            cle = isinstance(s, dict) and s.get("cle")
            if not cle or cle not in FILTERS:
                errs.append(f"filtre inconnu : {cle!r}")
    if p.get("tri_defaut") and p["tri_defaut"] not in SORTS:
        errs.append(f"tri inconnu : {p['tri_defaut']!r}")
    for c in p.get("colonnes_export") or []:
        if c not in EXPORT_COLS:
            errs.append(f"colonne d'export inconnue : {c!r}")
    return errs


def seed_presets(session) -> dict:
    """Insère les presets du YAML absents de la base. Renvoie {inseres, ignores, erreurs}."""
    doc = config.load_yaml_config("segment_presets")
    existing = set(session.execute(text("SELECT slug FROM segment_presets")).scalars())
    inseres, ignores, erreurs = [], [], {}
    for i, p in enumerate(doc.get("presets") or []):
        slug = p.get("slug")
        errs = validate_preset(p)
        if errs:
            erreurs[slug or f"#{i}"] = errs
            continue
        if slug in existing:
            ignores.append(slug)
            continue
        session.execute(text("""
            INSERT INTO segment_presets (slug, nom, categorie, description, argumentaire,
                                         filtres, colonnes_export, tri_defaut, boost_catnat,
                                         actif, ordre, created_by)
            VALUES (:slug, :nom, :categorie, :description, :argumentaire,
                    CAST(:filtres AS jsonb), CAST(:colonnes AS jsonb), :tri, :boost,
                    true, :ordre, 'seed')"""), {
            "slug": slug, "nom": p["nom"], "categorie": p["categorie"],
            "description": p.get("description"), "argumentaire": p.get("argumentaire"),
            "filtres": json.dumps(p.get("filtres") or [], ensure_ascii=False),
            "colonnes": json.dumps(p.get("colonnes_export") or [], ensure_ascii=False),
            "tri": p.get("tri_defaut"), "boost": bool(p.get("boost_catnat")),
            "ordre": int(p.get("ordre", (i + 1) * 10)),
        })
        inseres.append(slug)
    session.flush()
    return {"inseres": inseres, "ignores": ignores, "erreurs": erreurs}


def list_presets(session, *, actifs_seulement: bool = False) -> list[dict]:
    rows = session.execute(text(
        "SELECT slug, nom, categorie, description, argumentaire, filtres, colonnes_export,"
        "       tri_defaut, boost_catnat, actif, ordre, created_by, updated_at"
        " FROM segment_presets"
        + (" WHERE actif" if actifs_seulement else "")
        + " ORDER BY ordre, slug")).mappings().all()
    return [dict(r) for r in rows]


def get_preset(session, slug: str) -> dict | None:
    r = session.execute(text(
        "SELECT slug, nom, categorie, description, argumentaire, filtres, colonnes_export,"
        "       tri_defaut, boost_catnat, actif, ordre, created_by, updated_at"
        " FROM segment_presets WHERE slug = :s"), {"s": slug}).mappings().one_or_none()
    return dict(r) if r else None


def preset_disponibilite(preset: dict, avail: dict[str, dict]) -> tuple[str, list[dict]]:
    """('complet'|'partiel', filtres_inactifs) d'un preset selon la disponibilité."""
    inactifs: list[dict] = []
    for f in preset.get("filtres") or []:
        subs = f.get("ou") if "ou" in f else [f]
        for s in subs:
            cle = s.get("cle")
            fd = FILTERS.get(cle)
            a = avail.get(cle, {})
            if fd and not a.get("disponible", False):
                inactifs.append({"cle": cle, "libelle": fd.libelle,
                                 "raison": a.get("raison"), "mandat": fd.mandat})
    return ("partiel" if inactifs else "complet"), inactifs


def counts(session) -> dict[str, dict]:
    rows = session.execute(text(
        "SELECT slug, n, computed_at FROM segment_preset_counts")).mappings().all()
    return {r["slug"]: {"n": r["n"], "computed_at": r["computed_at"]} for r in rows}


def refresh_counts(session, *, only_stale_hours: float | None = None) -> dict[str, int]:
    """Compteur live de parcelles matchées par preset actif (cache 24 h côté lecture).
    `only_stale_hours` : ne recalcule que les compteurs plus vieux que N heures."""
    avail = compute_availability(session)
    stale_ok: set[str] = set()
    if only_stale_hours is not None:
        stale_ok = set(session.execute(text(
            "SELECT slug FROM segment_preset_counts"
            " WHERE computed_at > now() - make_interval(hours => :h)"),
            {"h": float(only_stale_hours)}).scalars())
    out: dict[str, int] = {}
    for p in list_presets(session, actifs_seulement=True):
        if p["slug"] in stale_ok:
            continue
        q = seg_engine.build(session, p["filtres"] or [], p.get("tri_defaut"), avail=avail)
        n = seg_engine.run_count(session, q)
        session.execute(text(
            "INSERT INTO segment_preset_counts (slug, n, computed_at)"
            " VALUES (:s, :n, now())"
            " ON CONFLICT (slug) DO UPDATE SET n = :n, computed_at = now()"),
            {"s": p["slug"], "n": n})
        out[p["slug"]] = n
    session.flush()
    return out


def upsert_preset(session, data: dict[str, Any], *, created_by: str = "admin") -> dict:
    """Création/édition admin (Vic). Valide le contrat avant écriture."""
    errs = validate_preset(data)
    if errs:
        raise seg_engine.FiltreInvalide(" ; ".join(errs))
    session.execute(text("""
        INSERT INTO segment_presets (slug, nom, categorie, description, argumentaire,
                                     filtres, colonnes_export, tri_defaut, boost_catnat,
                                     actif, ordre, created_by)
        VALUES (:slug, :nom, :categorie, :description, :argumentaire,
                CAST(:filtres AS jsonb), CAST(:colonnes AS jsonb), :tri, :boost,
                :actif, :ordre, :by)
        ON CONFLICT (slug) DO UPDATE SET
          nom = EXCLUDED.nom, categorie = EXCLUDED.categorie,
          description = EXCLUDED.description, argumentaire = EXCLUDED.argumentaire,
          filtres = EXCLUDED.filtres, colonnes_export = EXCLUDED.colonnes_export,
          tri_defaut = EXCLUDED.tri_defaut, boost_catnat = EXCLUDED.boost_catnat,
          actif = EXCLUDED.actif, ordre = EXCLUDED.ordre, updated_at = now()"""), {
        "slug": data["slug"], "nom": data["nom"], "categorie": data["categorie"],
        "description": data.get("description"), "argumentaire": data.get("argumentaire"),
        "filtres": json.dumps(data.get("filtres") or [], ensure_ascii=False),
        "colonnes": json.dumps(data.get("colonnes_export") or [], ensure_ascii=False),
        "tri": data.get("tri_defaut"), "boost": bool(data.get("boost_catnat")),
        "actif": bool(data.get("actif", True)), "ordre": int(data.get("ordre", 100)),
        "by": created_by,
    })
    session.flush()
    return get_preset(session, data["slug"])
