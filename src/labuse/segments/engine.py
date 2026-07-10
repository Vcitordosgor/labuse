"""Évaluateur du moteur de segments : preset.filtres (jsonb) → SQL paramétré (Lot 1).

Doctrine sécurité : le client n'envoie QUE des clés de filtres (validées contre le
registry) et des valeurs (min/max/booléens/valeurs d'énum) passées en PARAMÈTRES
BINDÉS. Toute clé inconnue → 422. Toute valeur d'énum hors liste → 422. Aucune
chaîne cliente n'est jamais concaténée dans le SQL.

Résilience : un filtre demandé dont la source manque n'est PAS une erreur — il est
ignoré et listé dans `filtres_inactifs` (le preset devient « partiel »).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import text

from .. import config
from .registry import (CASCADE_RUN, EXPORT_COLS, FILTERS, JOINS, SORTS,
                       compute_availability, export_col_available)

MAX_LIMIT = 500
MAX_EXPORT = 10_000
MAX_GEOJSON = 5_000

# Les slivers cadastraux (artefacts < 2 m²) sont masqués partout ailleurs dans le produit
# (cf. api/app.py MIN_DISPLAY_SURFACE_M2) — même règle ici.
_BASE_WHERE = "p.surface_m2 >= 2"


class FiltreInvalide(ValueError):
    """Clé de filtre inconnue ou valeur invalide (→ HTTP 422 côté API)."""


@dataclass
class Query:
    sql_items: str
    sql_count: str
    params: dict[str, Any]
    actifs: list[dict]
    inactifs: list[dict]          # [{cle, raison, mandat}]
    export_cols: list[tuple[str, str]]   # [(clé, en-tête français)] émises
    tri: str


def _catnat_params() -> dict[str, Any]:
    """Fenêtre et périls du signal CATNAT — config serveur (config/segments.yaml)."""
    try:
        cfg = (config.load_yaml_config("segments") or {}).get("catnat", {})
    except FileNotFoundError:
        cfg = {}
    perils = cfg.get("perils") or ["vent", "cyclon", "inondation"]
    return {"catnat_mois": int(cfg.get("fenetre_mois", 6)),
            "catnat_perils": [f"%{p}%" for p in perils]}


def _norm_num(cle: str, v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        raise FiltreInvalide(f"filtre « {cle} » : borne numérique attendue, reçu {v!r}")


def build(session, filtres: list[dict], tri: str | None, *,
          colonnes_export: list[str] | None = None,
          avail: dict[str, dict] | None = None,
          simulate_missing: frozenset[str] = frozenset()) -> Query:
    """Assemble la requête (items + count) depuis une liste déclarative de filtres.

    filtres : [{cle, min?, max?, value?, values?}] — la forme stockée en
    segment_presets.filtres et renvoyée par le query builder.
    """
    avail = avail if avail is not None else compute_availability(
        session, simulate_missing=simulate_missing)

    joins: list[str] = []          # ordre d'ajout stable, dédupliqué
    conds: list[str] = [_BASE_WHERE]
    params: dict[str, Any] = {}
    actifs: list[dict] = []
    inactifs: list[dict] = []

    def add_joins(keys: tuple[str, ...]) -> None:
        for k in keys:
            j = JOINS[k]
            if j not in joins:
                joins.append(j)

    def compile_one(f: dict, p: str) -> str | None:
        """Compile UN filtre → condition SQL, ou None si sa source manque (→ inactifs).
        Lève FiltreInvalide sur clé inconnue / valeur hors contrat."""
        cle = str(f["cle"])
        fd = FILTERS.get(cle)
        if fd is None:
            raise FiltreInvalide(f"filtre inconnu : « {cle} »")
        a = avail.get(cle, {})
        if not a.get("disponible", False):
            inactifs.append({"cle": cle, "libelle": fd.libelle,
                             "raison": a.get("raison"), "mandat": fd.mandat})
            return None
        add_joins(fd.joins)
        if fd.type == "range":
            parts = []
            if f.get("min") is not None:
                parts.append(f"{fd.expr} >= :{p}_min")
                params[f"{p}_min"] = _norm_num(cle, f["min"])
            if f.get("max") is not None:
                parts.append(f"{fd.expr} <= :{p}_max")
                params[f"{p}_max"] = _norm_num(cle, f["max"])
            if not parts:
                raise FiltreInvalide(f"filtre « {cle} » : min et/ou max requis")
            return "(" + " AND ".join(parts) + ")"
        if fd.type == "bool":
            v = f.get("value", True)
            if not isinstance(v, bool):
                raise FiltreInvalide(f"filtre « {cle} » : booléen attendu")
            return (f"COALESCE({fd.expr}, false)" if v
                    else f"NOT COALESCE({fd.expr}, false)")
        if fd.type == "enum":
            values = f.get("values") or ([f["value"]] if f.get("value") else [])
            if not values or not isinstance(values, list):
                raise FiltreInvalide(f"filtre « {cle} » : values (liste) requis")
            values = [str(v) for v in values]
            if fd.enum_values:
                bad = [v for v in values if v not in fd.enum_values]
                if bad:
                    raise FiltreInvalide(f"filtre « {cle} » : valeur(s) hors liste {bad}")
            params[f"{p}_in"] = values
            return f"{fd.expr} = ANY(:{p}_in)"
        raise FiltreInvalide(f"type de filtre non géré : {fd.type}")  # pragma: no cover

    if not isinstance(filtres, list):
        raise FiltreInvalide("filtres : liste attendue")
    for i, f in enumerate(filtres):
        if not isinstance(f, dict):
            raise FiltreInvalide(f"filtre #{i} : objet attendu")
        # Groupe OU (ex. extensions : résiduel ≥ 30 m² OU surélévation possible) — un
        # niveau d'imbrication ; les seuils restent dans le seed, jamais dans le code.
        if "ou" in f:
            subs = f.get("ou")
            if not isinstance(subs, list) or not subs or not all(
                    isinstance(s, dict) and s.get("cle") and "ou" not in s for s in subs):
                raise FiltreInvalide(f"filtre #{i} : « ou » = liste de filtres simples")
            compiled = [c for j, s in enumerate(subs)
                        if (c := compile_one(s, f"f{i}_{j}")) is not None]
            if compiled:            # branches indisponibles déjà listées dans inactifs
                conds.append("(" + " OR ".join(compiled) + ")")
                actifs.append(dict(f))
            continue
        if not f.get("cle"):
            raise FiltreInvalide(f"filtre #{i} : objet {{cle, …}} attendu")
        cond = compile_one(f, f"f{i}")
        if cond is not None:
            conds.append(cond)
            actifs.append(dict(f))

    # Tri : clé du registry uniquement ; repli stable si sa source manque.
    tri = tri or "surface_desc"
    sd = SORTS.get(tri)
    if sd is None:
        raise FiltreInvalide(f"tri inconnu : « {tri} »")
    tri_effectif = tri
    if sd.requires_rows:
        # même détection que les filtres : une source de tri vide → repli surface
        probe = {"dvf_mutations_parcelle": "anciennete_mutation_mois",
                 "parcel_residuel_bati": "jardin_m2", "dpe_records": "periode_construction"}
        dep = probe.get(sd.requires_rows)
        if dep and not avail.get(dep, {}).get("disponible"):
            sd = SORTS["surface_desc"]
            tri_effectif = "surface_desc"
    add_joins(sd.joins)

    # Colonnes d'export/table : celles du preset dont la source est disponible.
    export_cols: list[tuple[str, str]] = []
    select_extra: list[str] = []
    for key in (colonnes_export or []):
        if key not in EXPORT_COLS:
            raise FiltreInvalide(f"colonne d'export inconnue : « {key} »")
        if not export_col_available(key, avail):
            continue
        header, expr, jkeys = EXPORT_COLS[key]
        add_joins(jkeys)
        select_extra.append(f"{expr} AS {key}")
        export_cols.append((key, header))

    if any(":cascade_run" in j for j in joins):
        params["cascade_run"] = CASCADE_RUN
    needs_catnat = any(":catnat_mois" in c for c in conds)
    if needs_catnat:
        params.update(_catnat_params())

    join_sql = ("\n" + "\n".join(joins)) if joins else ""
    where_sql = " AND ".join(conds)
    extra_sql = (", " + ", ".join(select_extra)) if select_extra else ""
    sql_items = (
        "SELECT p.idu, p.commune, round(p.surface_m2) AS surface_m2,"
        " ST_X(p.centroid) AS lon, ST_Y(p.centroid) AS lat"
        f"{extra_sql}\nFROM parcels p{join_sql}\nWHERE {where_sql}"
        f"\nORDER BY {sd.order_by}, p.idu\nLIMIT :_limit OFFSET :_offset")
    sql_count = f"SELECT count(*)\nFROM parcels p{join_sql}\nWHERE {where_sql}"
    return Query(sql_items, sql_count, params, actifs, inactifs, export_cols, tri_effectif)


def run_count(session, q: Query) -> int:
    return int(session.execute(text(q.sql_count), q.params).scalar() or 0)


def run_items(session, q: Query, limit: int, offset: int) -> list[dict]:
    limit = max(1, min(int(limit), MAX_LIMIT))
    offset = max(0, int(offset))
    rows = session.execute(text(q.sql_items),
                           {**q.params, "_limit": limit, "_offset": offset}).mappings().all()
    return [dict(r) for r in rows]


def run_export_rows(session, q: Query, limit: int = MAX_EXPORT):
    """Lignes d'export CSV « à l'occupant » — RGPD : aucune donnée nominative de
    personne physique (aucune colonne propriétaire n'existe dans EXPORT_COLS)."""
    limit = max(1, min(int(limit), MAX_EXPORT))
    return session.execute(text(q.sql_items),
                           {**q.params, "_limit": limit, "_offset": 0}).mappings()
