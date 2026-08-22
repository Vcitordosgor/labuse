"""MANDAT RNU — communes sans document local d'urbanisme (règlement national d'urbanisme).

Flag COMMUNE-LEVEL, GÉNÉRAL (mandat C) : la liste vit dans config/rnu_communes.yaml
(déclaratif, vérifié à la main, sourcé — le flag GPU `is_rnu` est prouvé périmé).
Un PLU annulé/caduc fait retomber n'importe quelle commune au RNU : on AJOUTE une
entrée au yaml, aucun code à toucher.

Le module porte : le flag, l'étiquetage produit (fiche + exports) et — depuis la
VALIDATION Vic du 26/07/2026 (méthode « médian », critère centre, plancher uniforme) —
le moteur PAU : `build_pau()` matérialise `commune_pau` (enveloppes) + `parcel_pau`
(parcelles dont le point-sur-surface est dans l'enveloppe), consommées par le
plancher C (p_v2/statuts.py, branche RNU) et l'étiquetage.

Doctrine wording : « commune au règlement national d'urbanisme — pas de PLU local ».
On n'affirme JAMAIS une constructibilité au RNU, et la PAU est toujours présentée
comme une ESTIMATION (AVERTISSEMENT_PAU — wording validé Vic, ne pas reformuler).
"""
from __future__ import annotations

import json
from functools import lru_cache

from sqlalchemy import text

from .config import load_yaml_config

#: Étiquette produit — wording DOCTRINAL (fiche + exports), exigé par le mandat B.
LIBELLE_RNU = "Commune au règlement national d'urbanisme — pas de PLU local"

#: Complément honnête affiché avec l'étiquette (fiche) : pourquoi les règles locales manquent.
DETAIL_RNU = ("Aucun document local approuvé : les règles nationales s'appliquent "
              "(constructibilité limitée aux parties actuellement urbanisées — "
              "analyse au cas par cas, non couverte par le zonage LABUSE).")

#: PAU = ESTIMATION — wording VALIDÉ Vic (26/07/2026), affiché fiche + exports, ne pas reformuler.
AVERTISSEMENT_PAU = ("Enveloppe urbanisée estimée par LABUSE — la délimitation des parties "
                     "actuellement urbanisées relève de l'appréciation du service instructeur.")

#: Mention « non applicable » des règles de capacité en export RNU (ajout Vic : jamais un
#: tableau vide qui laisserait croire à une absence de contrainte).
NON_APPLICABLE_RNU = "non applicable — RNU"


@lru_cache(maxsize=1)
def _entries() -> dict[str, dict]:
    """insee → entrée du yaml. Cache module (le yaml ne bouge pas en cours de run)."""
    try:
        cfg = load_yaml_config("rnu_communes") or {}
    except Exception:
        return {}
    out: dict[str, dict] = {}
    for e in cfg.get("communes") or []:
        insee = str(e.get("insee") or "").strip()
        if insee:
            out[insee] = e
    return out


def is_rnu_insee(insee: str | None) -> bool:
    """La commune (code INSEE 5 chiffres) est-elle au RNU ?"""
    return bool(insee) and str(insee)[:5] in _entries()


def is_rnu_idu(idu: str | None) -> bool:
    """La parcelle (IDU) est-elle dans une commune au RNU ? (insee = left(idu, 5))"""
    return bool(idu) and str(idu)[:5] in _entries()


def pau_params() -> dict:
    """Paramètres PAU VALIDÉS (config, jamais en dur — exigence Vic). REFUS si incomplets."""
    cfg = load_yaml_config("rnu_communes") or {}
    p = cfg.get("pau") or {}
    out = {"eps_m": float(p.get("eps_m", 0)), "min_batiments": int(p.get("min_batiments", 0)),
           "buffer_m": float(p.get("buffer_m", 0)), "critere": str(p.get("critere", ""))}
    if not (out["eps_m"] > 0 and out["min_batiments"] > 0 and out["buffer_m"] > 0
            and out["critere"] == "centre"):
        raise ValueError(f"rnu_communes.yaml › pau incomplet/invalide : {out} — la méthode "
                         "validée exige eps_m/min_batiments/buffer_m > 0 et critere: centre.")
    return out


def rnu_block(idu: str | None, session=None) -> dict | None:
    """Bloc d'étiquetage produit pour la fiche/exports — None hors commune RNU.

    Avec `session` : ajoute l'état PAU de la parcelle — `dans_pau` True/False si
    l'enveloppe est calculée (parcel_pau), None sinon — TOUJOURS accompagné de
    l'avertissement ESTIMATION (wording validé)."""
    if not is_rnu_idu(idu):
        return None
    e = _entries()[str(idu)[:5]]
    out = {
        "libelle": LIBELLE_RNU,
        "detail": DETAIL_RNU,
        "commune_nom": e.get("nom"),
        "statut_detail": e.get("detail"),
        "verifie_le": e.get("verifie_le"),
        "dans_pau": None,
        "avertissement_pau": AVERTISSEMENT_PAU,
    }
    if session is not None:
        try:
            if session.execute(text("SELECT to_regclass('parcel_pau') IS NOT NULL")).scalar():
                out["dans_pau"] = bool(session.execute(
                    text("SELECT EXISTS (SELECT 1 FROM parcel_pau WHERE idu = :i)"),
                    {"i": idu}).scalar())
        except Exception:   # noqa: BLE001 — l'étiquette ne casse jamais une fiche
            pass
    return out


# ═══════════════ MOTEUR PAU (méthode médiane VALIDÉE Vic 26/07/2026) ═══════════════

DDL_PAU = """
CREATE TABLE IF NOT EXISTS commune_pau (
  insee        varchar(5) PRIMARY KEY,
  n_noyaux     int NOT NULL,
  n_batiments  int NOT NULL,       -- bâtiments clusterisés (dans un noyau)
  pau_ha       int NOT NULL,
  params       jsonb NOT NULL,     -- eps_m/min_batiments/buffer_m/critere (config, tracés)
  pau          geometry NOT NULL,  -- enveloppe (EPSG:2975)
  computed_at  timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS parcel_pau (
  idu    varchar(14) PRIMARY KEY,
  insee  varchar(5) NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_parcel_pau_insee ON parcel_pau (insee);
"""


def build_pau(session, *, commit: bool = True, log=lambda *_: None) -> dict:
    """Matérialise les PAU des communes flaggées RNU (rebuild complet idempotent).

    Méthode VALIDÉE : noyaux = ST_ClusterDBSCAN(centroïdes bâtiments, eps=eps_m,
    minpoints=min_batiments) ; enveloppe = ST_Union(ST_Buffer(bâtiment, buffer_m)) des
    bâtiments clusterisés ; parcelle dans la PAU ssi ST_PointOnSurface ∈ enveloppe
    (critère « centre »). Paramètres en CONFIG, jamais en dur.

    SOURCE BÂTI = BD TOPO (ortho ~2023) ∪ CoSIA (imagerie 2025, kind='batiment_cosia'),
    la seconde EN COMPLÉMENT et DÉDUPLIQUÉE DANS LE GESTE (les footprints CoSIA qui
    recouvrent un bâti BD TOPO sont exclus — jamais comptés deux fois ; cf. test
    test_pau_cosia). Si la couche CoSIA est absente/vide, l'union se réduit à BD TOPO
    (comportement d'avant, aucune régression). Le jeu de paramètres est INCHANGÉ (médian).

    LECTURE SEULE des sources ; n'écrit que commune_pau/parcel_pau. Les tiers ne bougent
    qu'au prochain `labuse score-v2` — jamais rétroactivement."""
    p = pau_params()
    for stmt in DDL_PAU.strip().split(";"):
        if stmt.strip():
            session.execute(text(stmt))
    session.execute(text("DELETE FROM parcel_pau"))
    session.execute(text("DELETE FROM commune_pau"))
    out: dict[str, dict] = {}
    for insee, e in _entries().items():
        nom = e.get("nom")
        row = session.execute(text("""
            WITH src AS (
                -- BD TOPO bâti (ortho ~2023)
                SELECT geom_2975 AS g
                FROM spatial_layers WHERE kind = 'batiment' AND commune = :nom
                UNION ALL
                -- CoSIA bâti (imagerie 2025) EN COMPLÉMENT, DÉDUPLIQUÉ DANS LE GESTE :
                -- on n'ajoute QUE les footprints CoSIA sans recouvrement d'un bâti BD TOPO,
                -- pour ne jamais compter deux fois un bâtiment vu par les deux sources.
                SELECT c.geom_2975 AS g
                FROM spatial_layers c
                WHERE c.kind = 'batiment_cosia' AND c.commune = :nom
                  AND NOT EXISTS (
                      SELECT 1 FROM spatial_layers b
                      WHERE b.kind = 'batiment' AND b.commune = :nom
                        AND ST_Intersects(b.geom_2975, c.geom_2975))
            ), bats AS (
                SELECT g,
                       ST_ClusterDBSCAN(ST_Centroid(g),
                                        eps => :eps, minpoints => :minpts) OVER () AS cid
                FROM src
            ), env AS (
                SELECT count(DISTINCT cid) AS n_noyaux, count(*) AS n_bats,
                       ST_Union(ST_Buffer(g, :buf)) AS pau
                FROM bats WHERE cid IS NOT NULL
            )
            INSERT INTO commune_pau (insee, n_noyaux, n_batiments, pau_ha, params, pau)
            SELECT :insee, n_noyaux, n_bats, round(ST_Area(pau) / 10000.0)::int,
                   :params, pau
            FROM env WHERE pau IS NOT NULL
            RETURNING n_noyaux, n_batiments, pau_ha"""), {
            "eps": p["eps_m"], "minpts": p["min_batiments"], "buf": p["buffer_m"],
            "nom": nom, "insee": insee,
            "params": json.dumps(p)}).mappings().first()
        if row is None:
            # HONNÊTETÉ (mandat D) : pas de bâtiments en base → PAU NON CALCULÉE, on le dit —
            # jamais une enveloppe vide silencieuse (la commune reste « non traitée — RNU »).
            log(f"rnu-pau {nom} ({insee}) : AUCUN bâtiment en base — PAU NON calculée "
                "(commune explicitement non traitée)")
            out[insee] = {"calculee": False}
            continue
        n_parc = session.execute(text("""
            INSERT INTO parcel_pau (idu, insee)
            SELECT pa.idu, :insee
            FROM parcels pa JOIN commune_pau cp ON cp.insee = :insee
            WHERE left(pa.idu, 5) = :insee
              AND ST_Intersects(ST_PointOnSurface(pa.geom_2975), cp.pau)
            RETURNING idu"""), {"insee": insee}).rowcount
        out[insee] = {"calculee": True, "n_noyaux": row["n_noyaux"],
                      "n_batiments": row["n_batiments"], "pau_ha": row["pau_ha"],
                      "parcelles_dans_pau": int(n_parc)}
        log(f"rnu-pau {nom} ({insee}) : {row['n_noyaux']} noyaux · {row['pau_ha']} ha · "
            f"{n_parc} parcelles dans la PAU (critère centre)")
    if commit:
        session.commit()
    return {"params": p, "communes": out}


def clear_cache() -> None:
    """Tests : invalide le cache du yaml."""
    _entries.cache_clear()
