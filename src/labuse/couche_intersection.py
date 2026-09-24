"""VITESSE-FIX-1 lot B — matérialisation des intersections parcelle × couche.

L'audit VITESSE-AUDIT-1 (VIT-001/VIT-004) a montré que `ST_Area(ST_Intersection(parcelle, couche))`
calculé AU VOL coûte ~8,4 s sur la fiche (servitudes dpu/peb/sup/prescription) et ~4,8 s sur le
Gabarit (zone `plu_gpu_zone`). La géométrie d'intersection est ici précalculée UNE fois par
`build-mvt` et rangée dans `parcel_couche_intersection` ; les lecteurs (fiche, Gabarit) la lisent.

RÈGLE « RÉSULTAT IDENTIQUE ». On range la géométrie BRUTE `ST_Intersection(p.geom_2975, sl.geom_2975)`
(stockage PostGIS double précision = sans perte), PAS une version simplifiée : aucun `ST_MakeValid`
ajouté, aucun changement de SRID, aucune tolérance. Les lecteurs réappliquent EXACTEMENT les mêmes
expressions aval (`ST_Area`, `ST_CollectionExtract`, `ST_Transform`, `ST_AsGeoJSON`, `ST_AsText`) sur
la géométrie rangée → sortie identique au calcul au vol.

FRAÎCHEUR. La table porte la version des sources dont elle dépend (couches SUP/servitudes/zone +
cadastre). `fraiche()` compare la version rangée à la version courante ; en cas de désalignement le
lecteur REPASSE au calcul au vol (jamais de surface périmée). Reconstruite par `build-mvt`
(orchestration unique `rebuild_mvt_servies`, comme `parcel_zone_plu`).
"""
from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import text
from sqlalchemy.orm import Session

TABLE = "parcel_couche_intersection"
_STAGING = TABLE + "_build"
_META = TABLE + "_meta"

# Filtre des couches matérialisées : servitudes de la fiche (dpu/peb/sup + prescription 01/05) ET
# zone PLU du Gabarit (plu_gpu_zone). EXACTEMENT les mêmes prédicats que les requêtes au vol remplacées.
_KIND_FILTER = ("(sl.kind IN ('dpu','peb','sup','plu_gpu_zone') "
                "OR (sl.kind = 'plu_gpu_prescription' AND sl.subtype IN ('01','05')))")
# Les kinds « fiche » servent au garde-fou de présence (kinds_presents) et à la version.
_KINDS_ALL = ("dpu", "peb", "sup", "plu_gpu_prescription", "plu_gpu_zone")


def source_version(db: Session) -> str:
    """Empreinte des sources : couches concernées (max updated/created + compte) + cadastre (compte +
    max id parcelle). Change dès qu'une nouvelle version de SUP/servitude/zone OU du cadastre est
    injectée. Volontairement grossière mais SÛRE (toute divergence force le recalcul au vol)."""
    row = db.execute(text(
        """
        SELECT
          (SELECT coalesce(to_char(max(created_at), 'YYYYMMDDHH24MISSMS'), '0') || ':' || count(*)
             FROM spatial_layers WHERE kind = ANY(:kinds)) AS couches,
          (SELECT count(*) || ':' || coalesce(max(id), 0) FROM parcels) AS cadastre
        """
    ), {"kinds": list(_KINDS_ALL)}).mappings().first()
    return f"c={row['couches']}|p={row['cadastre']}"


def fraiche(db: Session) -> bool:
    """La table matérialisée existe ET sa version colle aux sources courantes."""
    if not db.execute(text("SELECT to_regclass(:t)"), {"t": TABLE}).scalar():
        return False
    if not db.execute(text("SELECT to_regclass(:t)"), {"t": _META}).scalar():
        return False
    stored = db.execute(text(f"SELECT value FROM {_META} WHERE key = 'source_version'")).scalar()
    return bool(stored) and stored == source_version(db)


def build(db: Session, log: Callable[..., None] = lambda *_: None, chunk: int = 4000) -> int:
    """(Re)construit `parcel_couche_intersection` PAR TRANCHES de parcelles, dans une table de
    STAGING, puis bascule atomiquement (RENAME) — ne tient jamais un verrou long sur la table servie,
    ne bloque pas la base partagée. Idempotent. Renvoie le nombre de lignes.

    `lock_timeout` court : si le cadastre/les couches sont verrouillés par un autre run, la tranche
    échoue vite et le batch est relançable — plutôt que de faire la file d'attente."""
    version = source_version(db)
    db.execute(text("SET lock_timeout = '5s'"))
    db.execute(text(f"DROP TABLE IF EXISTS {_STAGING}"))
    # Schéma figé (pas de CREATE AS, pour maîtriser types + colonne géométrie).
    db.execute(text(f"""
        CREATE TABLE {_STAGING} (
            parcel_id integer NOT NULL,
            layer_id  integer NOT NULL,
            kind      varchar NOT NULL,
            subtype   varchar,
            area_m2   double precision,
            geom_2975 geometry
        )
    """))
    db.commit()

    # bornes de tranches sur parcels.id
    lo, hi = db.execute(text("SELECT coalesce(min(id),0), coalesce(max(id),0) FROM parcels")).first()
    total = 0
    start = lo
    while start <= hi:
        end = start + chunk
        db.execute(text("SET lock_timeout = '5s'"))
        # ORDRE DES ARGUMENTS de ST_Intersection = celui du LECTEUR de chaque kind (les kinds sont
        # disjoints entre lecteurs) : la fiche fait ST_Intersection(parcelle, couche) (ne lit que l'aire),
        # le Gabarit fait ST_Intersection(zone, parcelle) (lit la GÉOMÉTRIE). L'ordre change l'ordre des
        # sommets → la chaîne WKT/GeoJSON ET l'aire au 1e-13 près. On range donc chaque ligne dans
        # l'ordre EXACT de son lecteur → sortie bit-à-bit identique de part ET d'autre.
        n = db.execute(text(f"""
            INSERT INTO {_STAGING} (parcel_id, layer_id, kind, subtype, area_m2, geom_2975)
            SELECT p.id, sl.id, sl.kind, sl.subtype,
                   ST_Area(inter.g) AS area_m2, inter.g AS geom_2975
            FROM parcels p
            JOIN spatial_layers sl
              ON ST_Intersects(p.geom_2975, sl.geom_2975) AND {_KIND_FILTER}
            CROSS JOIN LATERAL (SELECT CASE
                     WHEN sl.kind = 'plu_gpu_zone'
                       THEN ST_Intersection(sl.geom_2975, p.geom_2975)   -- ordre Gabarit (zone, parcelle)
                       ELSE ST_Intersection(p.geom_2975, sl.geom_2975)   -- ordre fiche (parcelle, couche)
                     END AS g) inter
            WHERE p.id >= :a AND p.id < :b
        """), {"a": start, "b": end}).rowcount
        db.commit()
        total += n or 0
        if start // chunk % 25 == 0:
            log(f"  {TABLE}: parcelles {start}..{end} (+{n}, cumul {total})")
        start = end

    # index avant bascule
    db.execute(text(f"CREATE INDEX ON {_STAGING} (parcel_id)"))
    db.execute(text(f"CREATE INDEX ON {_STAGING} (kind, subtype)"))
    db.execute(text(f"CREATE INDEX ON {_STAGING} USING gist (geom_2975)"))
    db.commit()

    # bascule atomique + meta version
    db.execute(text("SET lock_timeout = '5s'"))
    db.execute(text(f"DROP TABLE IF EXISTS {TABLE}"))
    db.execute(text(f"ALTER TABLE {_STAGING} RENAME TO {TABLE}"))
    db.execute(text(f"""
        CREATE TABLE IF NOT EXISTS {_META} (key varchar PRIMARY KEY, value varchar, updated_at timestamptz)
    """))
    db.execute(text(f"""
        INSERT INTO {_META} (key, value, updated_at) VALUES ('source_version', :v, now())
        ON CONFLICT (key) DO UPDATE SET value = excluded.value, updated_at = now()
    """), {"v": version})
    db.commit()
    log(f"{TABLE} : {total} intersections matérialisées (version {version}).")
    return total
