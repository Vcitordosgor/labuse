"""Ingestion des couches Géorisques API (Vague B) → spatial_layers  [data pure].

Trois couches, une source (écosystème Géorisques), rangées dans `spatial_layers` (réutilise la
machinerie existante `_insert_layer` + trigger geom_2975 + croisement parcelles) :
  kind='sol_pollue'  (subtype 'casias' | 'instruction')  ← /ssp
  kind='cavite'      (subtype = type de cavité)          ← /cavites
  kind='icpe'        (subtype = régime)                  ← /installations_classees

La donnée d'abord, le scoring ensuite : ces couches deviennent des flags risque PLUS TARD
(# TODO étage 1 aux points d'accroche cascade). Ce module N'ALIMENTE PAS le score.

Couche RGA (argiles) écartée : endpoint /rga non concluant (500/vide) et aléa géologiquement
~inexistant à La Réunion (île volcanique) — documenté dans NOTES_GEORISQUES.md.
"""
from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..connectors.georisques import GeorisquesConnector
from .layers_ingest import _insert_layer

# kind → nom canonique de data_sources (fraîcheur par couche, cf. seed_sources).
KIND_SOURCE = {
    "sol_pollue": "Géorisques — sites et sols pollués",
    "cavite": "Géorisques — cavités souterraines",
    "icpe": "Géorisques — ICPE",
    "mvt": "Géorisques — mouvements de terrain",
}

# Kinds gérés par ingest_commune (les 3 couches API de la Vague B) ; 'mvt' a son propre ingest.
API_KINDS = ("sol_pollue", "cavite", "icpe")


def _point(lon, lat) -> dict | None:
    """GeoJSON Point depuis lon/lat numériques ; None si l'un manque/invalide."""
    try:
        return {"type": "Point", "coordinates": [float(lon), float(lat)]}
    except (TypeError, ValueError):
        return None


# ───────────────────────── parsing (pur, sans réseau) ─────────────────────────

def parse_sol_pollue(subtype: str, item: dict) -> dict | None:
    """Objet /ssp (casias ou instruction) → dict couche. None si pas de géométrie (inexploitable
    pour un croisement spatial ; on ne fabrique pas de point)."""
    geom = item.get("geom")
    if not isinstance(geom, dict) or not geom.get("coordinates"):
        return None
    return {
        "kind": "sol_pollue", "subtype": subtype,
        "name": item.get("nom_etablissement"),
        "geometry": geom,
        "attrs": {
            "identifiant_ssp": item.get("identifiant_ssp"),
            "identifiant_casias": item.get("identifiant_casias"),
            "statut": item.get("statut"),
            "adresse": item.get("adresse"),
            "code_insee": item.get("code_insee"),
            "fiche_risque": item.get("fiche_risque"),
            "date_maj": item.get("date_maj"),
        },
    }


def parse_cavite(item: dict) -> dict | None:
    """Objet /cavites → dict couche 'cavite'. None si pas de coordonnées."""
    geom = _point(item.get("longitude"), item.get("latitude"))
    if geom is None:
        return None
    return {
        "kind": "cavite", "subtype": (item.get("type") or None),
        "name": item.get("nom"),
        "geometry": geom,
        "attrs": {
            "identifiant": item.get("identifiant"),
            "type": item.get("type"),
            "code_insee": item.get("code_insee"),
        },
    }


def parse_mvt(item: dict) -> dict | None:
    """Objet /mvt → dict couche 'mvt' (bonus Vague C2). None si pas de coordonnées."""
    geom = _point(item.get("longitude"), item.get("latitude"))
    if geom is None:
        return None
    return {
        "kind": "mvt", "subtype": (item.get("type") or None),   # Coulée / Glissement / Éboulement…
        "name": item.get("lieu") or item.get("type"),
        "geometry": geom,
        "attrs": {
            "identifiant": item.get("identifiant"),
            "type": item.get("type"),
            "fiabilite": item.get("fiabilite"),
            "date_debut": item.get("date_debut"),
            "commentaire": item.get("commentaire_mvt"),
            "code_insee": item.get("code_insee"),
        },
    }


def parse_icpe(item: dict) -> dict | None:
    """Objet /installations_classees → dict couche 'icpe'. None si pas de coordonnées."""
    geom = _point(item.get("longitude"), item.get("latitude"))
    if geom is None:
        return None
    return {
        "kind": "icpe", "subtype": (item.get("regime") or None),
        "name": item.get("raisonSociale"),
        "geometry": geom,
        "attrs": {
            "regime": item.get("regime"),
            "statut_seveso": item.get("statutSeveso"),
            "code_naf": item.get("codeNaf"),
            "commune": item.get("commune"),
            "code_insee": item.get("codeInsee"),
        },
    }


def _iter_parsed(connector: GeorisquesConnector, insee: str) -> Iterator[dict]:
    """Itère TOUS les objets parsés des 3 couches pour une commune (casias+instruction, cavités, ICPE)."""
    for subtype, item in connector.sites_pollues(insee):
        p = parse_sol_pollue(subtype, item)
        if p:
            yield p
    for item in connector.cavites(insee):
        p = parse_cavite(item)
        if p:
            yield p
    for item in connector.installations_classees(insee):
        p = parse_icpe(item)
        if p:
            yield p


def _source_ids(session: Session) -> dict[str, int | None]:
    rows = session.execute(text("SELECT id, name FROM data_sources")).all()
    by_name = {name: sid for sid, name in rows}
    return {kind: by_name.get(src) for kind, src in KIND_SOURCE.items()}


def ingest_commune(session: Session, insee: str, commune: str, run_id: int | None = None,
                   connector: GeorisquesConnector | None = None) -> dict:
    """Ingère les 3 couches Géorisques d'une commune dans spatial_layers. Retourne le compte par kind.

    ⚠ ÉCRIT en base et FAIT DES APPELS RÉSEAU. Idempotence : purge des lignes de ces kinds pour la
    commune AVANT réinsertion (rejouable sans doublon). Ne touche PAS au score (# TODO étage 1).
    """
    connector = connector or GeorisquesConnector()
    sids = _source_ids(session)
    session.execute(
        text("DELETE FROM spatial_layers WHERE commune = :c AND kind = ANY(:k)"),
        {"c": commune, "k": list(API_KINDS)})
    counts: dict[str, int] = {k: 0 for k in API_KINDS}
    for p in _iter_parsed(connector, insee):
        _insert_layer(session, p["kind"], p["subtype"], p["name"], p["geometry"],
                      sids.get(p["kind"]), commune, run_id, p["attrs"])
        counts[p["kind"]] += 1
    _touch_sources(session)
    session.flush()
    return counts


def ingest_mvt_commune(session: Session, insee: str, commune: str, run_id: int | None = None,
                       connector: GeorisquesConnector | None = None) -> int:
    """Ingère les mouvements de terrain /mvt d'une commune → spatial_layers kind='mvt' (bonus C2).
    Idempotent (purge kind='mvt' de la commune avant réinsertion). Ne touche PAS au score."""
    connector = connector or GeorisquesConnector()
    sid = _source_ids(session).get("mvt")
    session.execute(text("DELETE FROM spatial_layers WHERE commune=:c AND kind='mvt'"), {"c": commune})
    n = 0
    for item in connector.mvt(insee):
        p = parse_mvt(item)
        if p:
            _insert_layer(session, "mvt", p["subtype"], p["name"], p["geometry"],
                          sid, commune, run_id, p["attrs"])
            n += 1
    session.execute(text("UPDATE data_sources SET last_sync_at=now() WHERE name=:n"),
                    {"n": KIND_SOURCE["mvt"]})
    session.flush()
    return n


def parcelles_croisees(session: Session, commune: str, rayon_m: float = 50.0,
                       kinds: tuple[str, ...] = API_KINDS) -> dict[str, int]:
    """Nombre de parcelles de la commune à ≤ rayon_m d'un objet de chaque couche (indicateur de
    croisement pour le rapport ; PAS un flag de score). Mesure en 2975 (geom_2975)."""
    out: dict[str, int] = {}
    for kind in kinds:
        n = session.execute(text(
            "SELECT count(DISTINCT p.id) FROM parcels p "
            "WHERE p.commune = :c AND EXISTS ("
            "  SELECT 1 FROM spatial_layers l WHERE l.kind = :k AND l.commune = :c "
            "  AND ST_DWithin(p.geom_2975, l.geom_2975, :r))"),
            {"c": commune, "k": kind, "r": rayon_m}).scalar()
        out[kind] = int(n or 0)
    return out


def sample_report(session: Session, commune: str, rayon_m: float = 50.0,
                  n_examples: int = 5) -> dict:
    """Rapport de validation (commune) depuis spatial_layers DÉJÀ ingérée — sans réseau."""
    vol = {}
    for kind in API_KINDS:
        vol[kind] = int(session.execute(text(
            "SELECT count(*) FROM spatial_layers WHERE kind = :k AND commune = :c"),
            {"k": kind, "c": commune}).scalar() or 0)
    croise = parcelles_croisees(session, commune, rayon_m)
    # Exemples DIVERSIFIÉS : au plus ceil(n/nb_kinds) par couche (utile pour vérification humaine).
    per_kind = max(1, -(-n_examples // len(API_KINDS)))
    ex = [dict(r) for r in session.execute(text(
        "SELECT kind, subtype, name, fiche, ident, statut FROM ("
        "  SELECT kind, subtype, name, attrs->>'fiche_risque' AS fiche, "
        "         attrs->>'identifiant' AS ident, attrs->>'statut' AS statut, "
        "         row_number() OVER (PARTITION BY kind ORDER BY name) AS rn "
        "  FROM spatial_layers WHERE kind = ANY(:k) AND commune = :c AND name IS NOT NULL"
        ") t WHERE rn <= :pk ORDER BY kind, name LIMIT :n"),
        {"k": list(API_KINDS), "c": commune, "pk": per_kind, "n": n_examples}).mappings().all()]
    return {"commune": commune, "volumetrie": vol, "parcelles_croisees": croise,
            "rayon_m": rayon_m, "exemples": ex}


def _touch_sources(session: Session) -> None:
    """Fraîcheur last_sync_at des 3 sources API de ingest_commune (si les lignes existent)."""
    session.execute(
        text("UPDATE data_sources SET last_sync_at = now() WHERE name = ANY(:n)"),
        {"n": [KIND_SOURCE[k] for k in API_KINDS]})
