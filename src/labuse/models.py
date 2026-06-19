"""Modèle de données LA BUSE (brief §5) + couches spatiales pré-ingérées.

Géométries stockées en EPSG:4326 (cf. geo.py) ; index GIST automatiques.
Toute mesure métrique passe par ST_Transform(geom, 2975).
"""
from __future__ import annotations

from datetime import date, datetime

from geoalchemy2 import Geometry
from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from . import enums

SRID = 4326  # stockage (voir geo.py)
SRID_M = 2975  # RGR92 UTM 40S — CRS métrique (mesures + intersections cascade)


def _enum(enum_cls, name: str) -> SAEnum:
    """Colonne VARCHAR+CHECK stockant la VALEUR de l'enum (pas son nom)."""
    return SAEnum(
        enum_cls,
        name=name,
        native_enum=False,
        validate_strings=True,
        values_callable=lambda e: [m.value for m in e],
    )


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# ───────────────────────────── parcels ─────────────────────────────

class Parcel(Base, TimestampMixin):
    __tablename__ = "parcels"

    id: Mapped[int] = mapped_column(primary_key=True)
    idu: Mapped[str] = mapped_column(String(14), unique=True, index=True)  # INSEE+section+numéro
    commune: Mapped[str] = mapped_column(String(64), index=True)
    section: Mapped[str | None] = mapped_column(String(10))
    numero: Mapped[str | None] = mapped_column(String(10))

    geom: Mapped[object] = mapped_column(Geometry("GEOMETRY", srid=SRID, spatial_index=True))
    geom_2975: Mapped[object | None] = mapped_column(  # pré-projeté (perf cascade), auto-maintenu par trigger
        Geometry("GEOMETRY", srid=SRID_M, spatial_index=False))
    surface_m2: Mapped[float | None] = mapped_column(Float)  # calculée en 2975
    centroid: Mapped[object | None] = mapped_column(Geometry("POINT", srid=SRID, spatial_index=False))
    bbox: Mapped[object | None] = mapped_column(Geometry("POLYGON", srid=SRID, spatial_index=False))
    # Provenance : NULL/'referentiel' = ingestion en masse ; 'audit' = ajoutée à la demande
    # (Lot A — audit pull). Sert au bandeau « audit à la demande » et au filtrage.
    origine: Mapped[str | None] = mapped_column(String(16))

    ingestion_run_id: Mapped[int | None] = mapped_column(ForeignKey("ingestion_runs.id"))

    source_results: Mapped[list["ParcelSourceResult"]] = relationship(back_populates="parcel")
    cascade_results: Mapped[list["CascadeResult"]] = relationship(back_populates="parcel")
    evaluations: Mapped[list["ParcelEvaluation"]] = relationship(back_populates="parcel")


# ───────────────────────────── data_sources ─────────────────────────────

class DataSource(Base, TimestampMixin):
    __tablename__ = "data_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True)
    category: Mapped[str | None] = mapped_column(String(64))
    provider: Mapped[str | None] = mapped_column(String(128))
    access_type: Mapped[str | None] = mapped_column(String(32))  # REST/WFS/WMS/CSV/GeoJSON/import/externe
    status: Mapped[enums.DataSourceStatus] = mapped_column(
        _enum(enums.DataSourceStatus, "data_source_status"),
        default=enums.DataSourceStatus.A_FAIRE,
    )
    documentation_url: Mapped[str | None] = mapped_column(Text)
    endpoint_url: Mapped[str | None] = mapped_column(Text)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reliability_level: Mapped[enums.ReliabilityLevel | None] = mapped_column(
        _enum(enums.ReliabilityLevel, "reliability_level")
    )
    rate_limit: Mapped[str | None] = mapped_column(String(64))
    legal_notes: Mapped[str | None] = mapped_column(Text)
    technical_notes: Mapped[str | None] = mapped_column(Text)


# ───────────────────────── parcel_source_results ─────────────────────────

class ParcelSourceResult(Base):
    __tablename__ = "parcel_source_results"
    __table_args__ = (
        Index("ix_psr_parcel_source", "parcel_id", "data_source_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    parcel_id: Mapped[int] = mapped_column(ForeignKey("parcels.id", ondelete="CASCADE"))
    data_source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.id"))
    status: Mapped[enums.SourceResultStatus] = mapped_column(
        _enum(enums.SourceResultStatus, "source_result_status")
    )
    raw_payload: Mapped[dict | None] = mapped_column(JSONB)
    summary: Mapped[str | None] = mapped_column(Text)
    confidence_level: Mapped[enums.ConfidenceLevel | None] = mapped_column(
        _enum(enums.ConfidenceLevel, "confidence_level")
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    parcel: Mapped[Parcel] = relationship(back_populates="source_results")
    data_source: Mapped[DataSource] = relationship()


# ───────────────────── cascade_results (explicabilité) ─────────────────────

class CascadeResult(Base):
    """La couche d'explicabilité — la traçabilité EST le produit (brief §2/§5)."""

    __tablename__ = "cascade_results"
    __table_args__ = (
        Index("ix_cascade_parcel", "parcel_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    parcel_id: Mapped[int] = mapped_column(ForeignKey("parcels.id", ondelete="CASCADE"))
    layer_name: Mapped[str] = mapped_column(String(64))
    result: Mapped[enums.CascadeVerdict] = mapped_column(_enum(enums.CascadeVerdict, "cascade_verdict"))
    severity: Mapped[enums.Severity | None] = mapped_column(_enum(enums.Severity, "severity"))
    weight_applied: Mapped[float | None] = mapped_column(Float)  # signé (pénalité < 0, bonus > 0)
    detail: Mapped[str] = mapped_column(Text)  # motif humain : POURQUOI
    data_source_id: Mapped[int | None] = mapped_column(ForeignKey("data_sources.id"))
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    parcel: Mapped[Parcel] = relationship(back_populates="cascade_results")


# ───────────────────── parcel_evaluations (versionnée) ─────────────────────

class ParcelEvaluation(Base):
    __tablename__ = "parcel_evaluations"
    __table_args__ = (
        CheckConstraint("completeness_score BETWEEN 0 AND 100", name="ck_completeness_range"),
        CheckConstraint("opportunity_score BETWEEN 0 AND 100", name="ck_opportunity_range"),
        Index("ix_eval_parcel_time", "parcel_id", "evaluated_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    parcel_id: Mapped[int] = mapped_column(ForeignKey("parcels.id", ondelete="CASCADE"))
    completeness_score: Mapped[int] = mapped_column(Integer)
    opportunity_score: Mapped[int] = mapped_column(Integer)
    status: Mapped[enums.EvaluationStatus] = mapped_column(_enum(enums.EvaluationStatus, "evaluation_status"))
    ai_payload: Mapped[dict | None] = mapped_column(JSONB)
    model_version: Mapped[str | None] = mapped_column(String(64))
    rules_version: Mapped[str | None] = mapped_column(String(64))
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    parcel: Mapped[Parcel] = relationship(back_populates="evaluations")


# ───────────────────────────── ingestion_runs ─────────────────────────────

class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    commune: Mapped[str | None] = mapped_column(String(64))
    data_source_id: Mapped[int | None] = mapped_column(ForeignKey("data_sources.id"))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    parcels_count: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str | None] = mapped_column(String(32))


# ─────────────────────── parcel_signals (offre C) ───────────────────────

class ParcelSignal(Base):
    __tablename__ = "parcel_signals"

    id: Mapped[int] = mapped_column(primary_key=True)
    parcel_id: Mapped[int] = mapped_column(ForeignKey("parcels.id", ondelete="CASCADE"))
    signal_type: Mapped[enums.SignalType] = mapped_column(_enum(enums.SignalType, "signal_type"))
    payload: Mapped[dict | None] = mapped_column(JSONB)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# ─────────────────────────── parcel_feedback ───────────────────────────

class ParcelFeedback(Base):
    __tablename__ = "parcel_feedback"

    id: Mapped[int] = mapped_column(primary_key=True)
    parcel_id: Mapped[int] = mapped_column(ForeignKey("parcels.id", ondelete="CASCADE"))
    user_id: Mapped[str | None] = mapped_column(String(128))
    verdict: Mapped[enums.FeedbackVerdict] = mapped_column(_enum(enums.FeedbackVerdict, "feedback_verdict"))
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ─────────────────────── watch_snapshots (veille, offre C) ───────────────────────

class WatchSnapshot(Base):
    """Photo de l'état surveillé d'une parcelle (veille, offre C).

    Un run de veille compare l'état courant à cette photo pour détecter les deltas
    (zonage_change, mutation/permis récents) puis met la photo à jour. Première
    photo = référence (aucune alerte)."""

    __tablename__ = "watch_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    parcel_id: Mapped[int] = mapped_column(ForeignKey("parcels.id", ondelete="CASCADE"), unique=True, index=True)
    gpu_zone: Mapped[str | None] = mapped_column(String(48))
    dvf_last: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    permit_last: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# ═══════════════════ Couches spatiales pré-ingérées (découverte) ═══════════════════
# Brief §4 : on n'appelle pas 15 API pour 40 000 parcelles. On pré-ingère les couches
# structurantes dans PostGIS et la cascade phase 1 tourne en batch sur le local.

class SpatialLayer(Base):
    """Entités géographiques structurantes (eau, Parc, SAR, PLU, SAFER, PPR, aléas…).

    Discriminées par `kind` ; `subtype` porte la nuance (cœur/adhésion, rouge/aléa,
    libellé de zone…). La cascade phase 1 intersecte la parcelle contre ces lignes.
    """

    __tablename__ = "spatial_layers"
    __table_args__ = (
        Index("ix_spatial_kind", "kind"),
        Index("ix_spatial_kind_subtype", "kind", "subtype"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(48))     # water, parc_national, sar, plu_gpu_zone, ppr…
    subtype: Mapped[str | None] = mapped_column(String(48))
    name: Mapped[str | None] = mapped_column(String(255))
    geom: Mapped[object] = mapped_column(Geometry("GEOMETRY", srid=SRID, spatial_index=True))
    geom_2975: Mapped[object | None] = mapped_column(  # pré-projeté (perf cascade), auto-maintenu par trigger
        Geometry("GEOMETRY", srid=SRID_M, spatial_index=False))
    attrs: Mapped[dict | None] = mapped_column(JSONB)
    data_source_id: Mapped[int | None] = mapped_column(ForeignKey("data_sources.id"))
    commune: Mapped[str | None] = mapped_column(String(64))
    ingestion_run_id: Mapped[int | None] = mapped_column(ForeignKey("ingestion_runs.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DvfMutation(Base):
    """Mutations DVF ingérées (brief §6/§7bis : requête PAR RAYON, pas par IDU)."""

    __tablename__ = "dvf_mutations"
    __table_args__ = (Index("ix_dvf_commune", "commune"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    mutation_id: Mapped[str | None] = mapped_column(String(64))
    date_mutation: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    valeur_fonciere: Mapped[float | None] = mapped_column(Float)
    type_local: Mapped[str | None] = mapped_column(String(64))
    surface_reelle_bati: Mapped[float | None] = mapped_column(Float)
    surface_terrain: Mapped[float | None] = mapped_column(Float)
    nature_mutation: Mapped[str | None] = mapped_column(String(64))
    commune: Mapped[str | None] = mapped_column(String(64))
    geom: Mapped[object] = mapped_column(Geometry("POINT", srid=SRID, spatial_index=True))
    raw: Mapped[dict | None] = mapped_column(JSONB)


class SitadelPermit(Base):
    """Autorisations d'urbanisme SITADEL (non géolocalisées nativement — §7bis).

    Chaque dossier porte 1 à 3 codes parcelle ; on reconstitue l'IDU 14 car. et on
    apparie par jointure attributaire à parcels.idu. Géométrie = centroïde si rattaché.
    """

    __tablename__ = "sitadel_permits"
    __table_args__ = (Index("ix_sitadel_commune", "commune"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    permit_id: Mapped[str | None] = mapped_column(String(64))
    type: Mapped[str | None] = mapped_column(String(8))      # PC / PA / PD / DP
    date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    idu_codes: Mapped[list | None] = mapped_column(JSONB)    # IDU 14 car. reconstitués (1..3)
    commune: Mapped[str | None] = mapped_column(String(64))
    geom: Mapped[object | None] = mapped_column(Geometry("POINT", srid=SRID, spatial_index=True))
    raw: Mapped[dict | None] = mapped_column(JSONB)


# ─────────────────────── pipeline de prospection (Kanban) ───────────────────────

class PipelineEntry(Base, TimestampMixin):
    """Une parcelle suivie dans le pipeline de prospection (Kanban).

    `status` (colonne) et `priority` sont des CLÉS validées contre config/pipeline.yaml
    (colonnes en config, pas en dur). Une parcelle = au plus une entrée (parcel_id unique).
    `created_at` (mixin) sert de date d'ajout.
    """

    __tablename__ = "pipeline_entries"
    __table_args__ = (UniqueConstraint("parcel_id", name="uq_pipeline_parcel"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    parcel_id: Mapped[int] = mapped_column(ForeignKey("parcels.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(48))          # clé de colonne (config)
    priority: Mapped[str] = mapped_column(String(16))        # clé de priorité (config)
    notes: Mapped[str] = mapped_column(Text, default="", server_default="")
    reminder_date: Mapped[date | None] = mapped_column(Date)  # rappel optionnel
    # Prospection MANUELLE (Niveau 1) : statut propriétaire, contact saisi, action suivante…
    # AUCUNE donnée nominative externe — tout est renseigné par l'utilisateur. RGPD : effaçable.
    prospection: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")

    parcel: Mapped[Parcel] = relationship()


def create_all(engine) -> None:
    Base.metadata.create_all(engine)
    ensure_geom_2975(engine)
    ensure_parcel_origine(engine)
    ensure_residuel_cache(engine)
    ensure_saved_filters(engine)
    ensure_personnes_morales(engine)
    ensure_bilan_params(engine)
    ensure_vue_mer_cache(engine)
    ensure_watch_zones(engine)
    ensure_pipeline_prospection(engine)
    ensure_enrichment_cache(engine)


def ensure_pipeline_prospection(engine) -> None:
    """Colonne `prospection` (jsonb) sur pipeline_entries — module prospection manuel.
    Idempotent ; ADD COLUMN IF NOT EXISTS → durable au rebuild sur base existante."""
    from sqlalchemy import text as _t

    with engine.begin() as c:
        c.execute(_t("ALTER TABLE pipeline_entries "
                     "ADD COLUMN IF NOT EXISTS prospection jsonb NOT NULL DEFAULT '{}'::jsonb"))


def ensure_geom_2975(engine, commune: str | None = None, backfill: bool = True) -> None:
    """Géométrie pré-projetée en 2975 (perf cascade), auto-maintenue par TRIGGER.

    `geom_2975 = ST_Transform(geom, 2975)` sur parcels + spatial_layers : la cascade
    n'a plus à reprojeter à la volée (la géométrie d'une parcelle était re-transformée
    une fois PAR couche croisée). C'est la MÊME valeur, pré-calculée et indexée en GIST
    → coverage/verdicts INCHANGÉS. Idempotent ; remplit l'existant et pose le trigger
    qui couvre tous les écrivains (cadastre, couches, démo, MakeValid).

    `commune` : si fourni, le BACKFILL/RÉPARATION ne portent que sur cette commune (rapide,
    pour un rebuild mono-commune) ; le trigger et les index restent globaux. Défaut = global.

    `backfill=False` : ne pose QUE le schéma (colonnes, fonction, triggers, index) sans
    les UPDATE massifs — pour le démarrage de l'app (réparer le schéma en secondes, jamais
    recalculer 300k lignes au boot). Les données manquantes sont alors signalées par
    /readyz et `labuse doctor`, et reconstruites par `rebuild-demo`."""
    from sqlalchemy import text as _t

    scope = " AND commune = :c" if commune else ""
    ddl = [
        "ALTER TABLE parcels ADD COLUMN IF NOT EXISTS geom_2975 geometry(Geometry, 2975)",
        "ALTER TABLE spatial_layers ADD COLUMN IF NOT EXISTS geom_2975 geometry(Geometry, 2975)",
        # ST_MakeValid : la reprojection 4326→2975 d'une géométrie pourtant valide peut
        # produire un polygone INVALIDE (auto-intersection au mm près) ; non réparé, il
        # fait planter ST_Intersection côté cascade (GEOS « side location conflict ») et
        # tue l'évaluation de toute la commune. MakeValid est un no-op sur une géométrie
        # déjà valide → verdicts INCHANGÉS, et répare les rares cas pathologiques.
        "CREATE OR REPLACE FUNCTION labuse_set_geom_2975() RETURNS trigger AS $$ "
        "BEGIN NEW.geom_2975 := ST_MakeValid(ST_Transform(NEW.geom, 2975)); RETURN NEW; END; $$ LANGUAGE plpgsql",
        "DROP TRIGGER IF EXISTS trg_parcels_geom_2975 ON parcels",
        "CREATE TRIGGER trg_parcels_geom_2975 BEFORE INSERT OR UPDATE OF geom ON parcels "
        "FOR EACH ROW EXECUTE FUNCTION labuse_set_geom_2975()",
        "DROP TRIGGER IF EXISTS trg_layers_geom_2975 ON spatial_layers",
        "CREATE TRIGGER trg_layers_geom_2975 BEFORE INSERT OR UPDATE OF geom ON spatial_layers "
        "FOR EACH ROW EXECUTE FUNCTION labuse_set_geom_2975()",
    ]
    if backfill:
        ddl += [
            f"UPDATE parcels SET geom_2975 = ST_MakeValid(ST_Transform(geom, 2975)) WHERE geom_2975 IS NULL AND geom IS NOT NULL{scope}",
            f"UPDATE spatial_layers SET geom_2975 = ST_MakeValid(ST_Transform(geom, 2975)) WHERE geom_2975 IS NULL AND geom IS NOT NULL{scope}",
            # Réparation de l'existant : geom_2975 déjà peuplé mais invalide (avant ce correctif).
            f"UPDATE parcels SET geom_2975 = ST_MakeValid(geom_2975) WHERE geom_2975 IS NOT NULL AND NOT ST_IsValid(geom_2975){scope}",
            f"UPDATE spatial_layers SET geom_2975 = ST_MakeValid(geom_2975) WHERE geom_2975 IS NOT NULL AND NOT ST_IsValid(geom_2975){scope}",
        ]
    ddl += [
        "CREATE INDEX IF NOT EXISTS idx_parcels_geom_2975 ON parcels USING gist (geom_2975)",
        "CREATE INDEX IF NOT EXISTS idx_spatial_layers_geom_2975 ON spatial_layers USING gist (geom_2975)",
        # Index FONCTIONNEL pour DVF : la cascade interroge les ventes par rayon métrique via
        # ST_DWithin(ST_Transform(centroid,2975), ST_Transform(d.geom,2975), r). Sans cet index,
        # la reprojection à la volée empêche tout index spatial → scan de toutes les ventes par
        # parcelle. Result-preserving (un index ne change AUCUN résultat), gain mesuré ~98 %.
        "CREATE INDEX IF NOT EXISTS idx_dvf_geom_2975 ON dvf_mutations USING gist (ST_Transform(geom, 2975))",
    ]
    params = {"c": commune} if commune else {}
    with engine.begin() as c:
        for stmt in ddl:
            c.execute(_t(stmt), params)
        c.execute(_t("ANALYZE parcels"))
        c.execute(_t("ANALYZE spatial_layers"))
        c.execute(_t("ANALYZE dvf_mutations"))


def ensure_enrichment_cache(engine) -> None:
    """Table de cache du bloc « promoteur » (même DDL que enrichment._ensure_cache_table,
    garantie ici dès le boot plutôt qu'au premier accès)."""
    from sqlalchemy import text as _t

    with engine.begin() as c:
        c.execute(_t(
            "CREATE TABLE IF NOT EXISTS parcel_enrichment ("
            " parcel_id integer PRIMARY KEY REFERENCES parcels(id) ON DELETE CASCADE,"
            " payload jsonb NOT NULL, computed_at timestamptz NOT NULL DEFAULT now())"))


def ensure_vue_mer_cache(engine) -> None:
    """Cache de la vue mer (2.B) — mémoïse le calcul line-of-sight (RGE ALTI) ; lu par le bilan
    (bonus prix) sans appel live. Idempotent."""
    from sqlalchemy import text as _t

    with engine.begin() as c:
        c.execute(_t(
            "CREATE TABLE IF NOT EXISTS parcel_vue_mer ("
            " parcel_id integer PRIMARY KEY REFERENCES parcels(id) ON DELETE CASCADE,"
            " vue varchar(10), distance_cote_m integer, obstruction_pct integer,"
            " computed_at timestamptz NOT NULL DEFAULT now())"))


def ensure_bilan_params(engine) -> None:
    """Overrides de paramètres du bilan par SECTEUR (1.C). secteur='*' = global. Idempotent.
    Pose la colonne `provenance` (sourcee|estimee) et injecte le SOCLE web sourcé (sans écraser
    un override déjà saisi) → le bilan est défendable dès le boot."""
    from sqlalchemy import text as _t

    with engine.begin() as c:
        c.execute(_t(
            "CREATE TABLE IF NOT EXISTS bilan_params ("
            " secteur varchar(64) NOT NULL, param varchar(48) NOT NULL, value double precision NOT NULL,"
            " is_placeholder boolean NOT NULL DEFAULT false, updated_at timestamptz NOT NULL DEFAULT now(),"
            " PRIMARY KEY (secteur, param))"))
        c.execute(_t("ALTER TABLE bilan_params ADD COLUMN IF NOT EXISTS provenance varchar(16)"))
        from .faisabilite.bilan_calibration import CALIBRATION
        from .faisabilite.bilan_calibration import seed as _seed
        _seed(c)
        # LOT 3 — recale la marge cible par DÉFAUT (système, secteur '*') sur la fourchette
        # promoteur 8–10 %. Ne touche QUE l'estimée système au-dessus de la fourchette : jamais
        # un override saisi (les overrides utilisateur vivent sur un secteur, pas '*').
        c.execute(_t(
            "UPDATE bilan_params SET value = :v, updated_at = now() "
            "WHERE secteur = '*' AND param = 'marge_cible_pct' "
            "AND provenance = 'estimee' AND value > 10"),
            {"v": CALIBRATION["marge_cible_pct"][0]})


def ensure_personnes_morales(engine) -> None:
    """Propriétaires personnes morales (1.A — fichier DGFiP, Licence Ouverte). Donnée PUBLIQUE,
    par parcelle (idu). Idempotent. `source`/`url_source`/`millesime`/`date_import` tracés (§3)."""
    from sqlalchemy import text as _t

    with engine.begin() as c:
        c.execute(_t(
            "CREATE TABLE IF NOT EXISTS parcelle_personne_morale ("
            " idu varchar(14) PRIMARY KEY,"
            " groupe smallint, groupe_label varchar(80), forme_juridique varchar(20),"
            " denomination varchar(200), siren varchar(20), millesime varchar(8),"
            " source varchar(120), url_source text, date_import timestamptz NOT NULL DEFAULT now())"))


def ensure_saved_filters(engine) -> None:
    """Filtres de recherche sauvegardés (Lot D3) — pilote mono-compte, params en JSONB. Idempotent."""
    from sqlalchemy import text as _t

    with engine.begin() as c:
        c.execute(_t(
            "CREATE TABLE IF NOT EXISTS saved_filters ("
            " id serial PRIMARY KEY, name varchar(80) NOT NULL, params jsonb NOT NULL,"
            " created_at timestamptz NOT NULL DEFAULT now())"))


def ensure_watch_zones(engine) -> None:
    """3.C — Alertes intelligentes : ZONES DE VEILLE (polygones dessinés) + table `alertes`
    (les « nouveautés »). Idempotent. La dédup d'une alerte par fait-source repose sur deux
    index uniques PARTIELS (une vente ne crée qu'une alerte par zone ; un permis qu'une par
    parcelle suivie) → re-rafraîchir sans donnée neuve n'ajoute rien."""
    from sqlalchemy import text as _t

    with engine.begin() as c:
        c.execute(_t(
            "CREATE TABLE IF NOT EXISTS watch_zones ("
            " id serial PRIMARY KEY, name varchar(120) NOT NULL, commune varchar(64) NOT NULL,"
            " geom geometry(Polygon, 4326) NOT NULL,"
            " created_at timestamptz NOT NULL DEFAULT now(), last_run_at timestamptz)"))
        c.execute(_t("CREATE INDEX IF NOT EXISTS idx_watch_zones_geom ON watch_zones USING gist (geom)"))
        c.execute(_t("CREATE INDEX IF NOT EXISTS ix_watch_zones_commune ON watch_zones (commune)"))
        c.execute(_t(
            "CREATE TABLE IF NOT EXISTS alertes ("
            " id serial PRIMARY KEY, kind varchar(32) NOT NULL,"
            " zone_id integer REFERENCES watch_zones(id) ON DELETE CASCADE,"
            " parcel_id integer REFERENCES parcels(id) ON DELETE CASCADE,"
            " source_ref varchar(64) NOT NULL, label text NOT NULL, payload jsonb,"
            " acknowledged boolean NOT NULL DEFAULT false,"
            " detected_at timestamptz NOT NULL DEFAULT now())"))
        c.execute(_t("CREATE UNIQUE INDEX IF NOT EXISTS uq_alertes_zone_dvf "
                     "ON alertes (zone_id, source_ref) WHERE kind = 'dvf_in_zone'"))
        c.execute(_t("CREATE UNIQUE INDEX IF NOT EXISTS uq_alertes_parcel_permit "
                     "ON alertes (parcel_id, source_ref) WHERE kind = 'permit_near_followed'"))


def ensure_residuel_cache(engine) -> None:
    """Cache du potentiel résiduel (Lot B) — alimente le filtre « sous-densité » sans
    relancer la faisabilité par parcelle à chaque chargement de carte. Idempotent."""
    from sqlalchemy import text as _t

    with engine.begin() as c:
        c.execute(_t(
            "CREATE TABLE IF NOT EXISTS parcel_residuel ("
            " parcel_id integer PRIMARY KEY REFERENCES parcels(id) ON DELETE CASCADE,"
            " taux_emprise_pct integer, pct_potentiel integer, sous_densite boolean,"
            " sdp_residuelle_m2 integer, computed_at timestamptz NOT NULL DEFAULT now())"))


def ensure_schema(engine) -> None:
    """Réconciliation LÉGÈRE et idempotente du schéma (boot / doctor / prepare-pilot).

    Garantit : tables ORM, colonnes critiques (geom_2975, prospection), fonction+triggers,
    index GIST (dont l'index fonctionnel DVF) et table de cache enrichment — en SECONDES.
    NE fait JAMAIS : backfill massif, téléchargement, ré-évaluation. Si des DONNÉES
    manquent (geom_2975 NULL, couches absentes), c'est /readyz et `labuse doctor` qui le
    disent, et `rebuild-demo` qui reconstruit."""
    Base.metadata.create_all(engine)
    ensure_geom_2975(engine, backfill=False)
    ensure_pipeline_prospection(engine)
    ensure_enrichment_cache(engine)
    ensure_parcel_origine(engine)
    ensure_residuel_cache(engine)
    ensure_saved_filters(engine)
    ensure_personnes_morales(engine)
    ensure_bilan_params(engine)
    ensure_vue_mer_cache(engine)
    ensure_watch_zones(engine)


def ensure_parcel_origine(engine) -> None:
    """Colonne `origine` sur parcels (Lot A — audit pull). Idempotent."""
    from sqlalchemy import text as _t

    with engine.begin() as c:
        c.execute(_t("ALTER TABLE parcels ADD COLUMN IF NOT EXISTS origine varchar(16)"))


def drop_all(engine) -> None:
    Base.metadata.drop_all(engine)
