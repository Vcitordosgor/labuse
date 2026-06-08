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

    parcel: Mapped[Parcel] = relationship()


def create_all(engine) -> None:
    Base.metadata.create_all(engine)
    ensure_geom_2975(engine)


def ensure_geom_2975(engine) -> None:
    """Géométrie pré-projetée en 2975 (perf cascade), auto-maintenue par TRIGGER.

    `geom_2975 = ST_Transform(geom, 2975)` sur parcels + spatial_layers : la cascade
    n'a plus à reprojeter à la volée (la géométrie d'une parcelle était re-transformée
    une fois PAR couche croisée). C'est la MÊME valeur, pré-calculée et indexée en GIST
    → coverage/verdicts INCHANGÉS. Idempotent ; remplit l'existant et pose le trigger
    qui couvre tous les écrivains (cadastre, couches, démo, MakeValid)."""
    from sqlalchemy import text as _t

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
        "UPDATE parcels SET geom_2975 = ST_MakeValid(ST_Transform(geom, 2975)) WHERE geom_2975 IS NULL AND geom IS NOT NULL",
        "UPDATE spatial_layers SET geom_2975 = ST_MakeValid(ST_Transform(geom, 2975)) WHERE geom_2975 IS NULL AND geom IS NOT NULL",
        # Réparation de l'existant : geom_2975 déjà peuplé mais invalide (avant ce correctif).
        "UPDATE parcels SET geom_2975 = ST_MakeValid(geom_2975) WHERE geom_2975 IS NOT NULL AND NOT ST_IsValid(geom_2975)",
        "UPDATE spatial_layers SET geom_2975 = ST_MakeValid(geom_2975) WHERE geom_2975 IS NOT NULL AND NOT ST_IsValid(geom_2975)",
        "CREATE INDEX IF NOT EXISTS idx_parcels_geom_2975 ON parcels USING gist (geom_2975)",
        "CREATE INDEX IF NOT EXISTS idx_spatial_layers_geom_2975 ON spatial_layers USING gist (geom_2975)",
        "ANALYZE parcels",
        "ANALYZE spatial_layers",
    ]
    with engine.begin() as c:
        for stmt in ddl:
            c.execute(_t(stmt))


def drop_all(engine) -> None:
    Base.metadata.drop_all(engine)
