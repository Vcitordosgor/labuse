"""Modèle de données LA BUSE (brief §5) + couches spatiales pré-ingérées.

Géométries stockées en EPSG:4326 (cf. geo.py) ; index GIST automatiques.
Toute mesure métrique passe par ST_Transform(geom, 2975).
"""
from __future__ import annotations

from datetime import date, datetime

from geoalchemy2 import Geometry
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
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
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # date d'INGESTION
    # M32 Phase B §2 (spec millésime amont) — « la fraîcheur d'une donnée est celle de sa SOURCE
    # amont, jamais celle de son ingestion ». Renseignées PAR l'ingester de chaque couche, jamais
    # à la main. `last_sync_at` reste la date d'ingestion (méta d'exploitation, jamais servie client).
    source_millesime: Mapped[str | None] = mapped_column(String(64))          # édition fournisseur (texte normé)
    source_horizon_at: Mapped[date | None] = mapped_column(Date)             # fait le plus récent DANS la donnée
    source_cadence: Mapped[str | None] = mapped_column(String(32))            # trimestriel/semestriel/hebdo/continu
    prochain_millesime_at: Mapped[date | None] = mapped_column(Date)          # prochaine publication attendue (si connue)
    reliability_level: Mapped[enums.ReliabilityLevel | None] = mapped_column(
        _enum(enums.ReliabilityLevel, "reliability_level")
    )
    rate_limit: Mapped[str | None] = mapped_column(String(64))
    legal_notes: Mapped[str | None] = mapped_column(Text)
    technical_notes: Mapped[str | None] = mapped_column(Text)
    # CONNEXIONS-2 Lot 6.3 (M2) — DÉSACTIVER une source depuis le dashboard : flag EN BASE (remplace
    # `SOURCES_MASQUEES` en dur, désormais vestigial). Désactivée ⇒ retirée de la vitrine ET les
    # consommateurs (couches/outils) servent « source désactivée » à la place d'un chiffre périmé.
    affichage_desactive: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))


# ───────────────────────────── source_veille ─────────────────────────────

class SourceVeille(Base, TimestampMixin):
    """SENTINELLE-1 (W1) — la ligne de surveillance amont d'UNE source. La sentinelle SURVEILLE et
    PRÉVIENT : elle ne télécharge rien, n'ingère rien, n'écrit JAMAIS dans `data_sources`. Une source
    sans ligne ici n'est simplement pas surveillée — état normal, pas une erreur.

    `methode` ∈ {api, page, entete} (W2) : trois façons de lire le millésime amont.
      · `api`    — JSON de versions ; `selecteur` = chemin JSON pointé (a.b.0.c).
      · `page`   — page HTML ; `selecteur` = regex de millésime (ex. `20\\d{2}-S[12]`), on garde le PLUS récent.
      · `entete` — pas de millésime lisible : on compare l'ETag/Last-Modified au dernier vu (`dernier_entete`).
    `dernier_statut` ∈ {ok, nouvelle_version, injoignable, illisible}. injoignable/illisible = la
    SENTINELLE a échoué, PAS la donnée (les deux états restent distincts, cf. W3.5)."""

    __tablename__ = "source_veille"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(
        ForeignKey("data_sources.id", ondelete="CASCADE"), unique=True, index=True)
    url_version: Mapped[str | None] = mapped_column(Text)           # URL amont sondée (jamais inventée)
    methode: Mapped[str | None] = mapped_column(String(8))          # api | page | entete
    selecteur: Mapped[str | None] = mapped_column(Text)            # chemin JSON (api) OU regex (page)
    cadence_heures: Mapped[int] = mapped_column(Integer, default=24, server_default=text("24"))
    dernier_passage_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dernier_vu: Mapped[str | None] = mapped_column(String(64))      # millésime constaté amont
    dernier_statut: Mapped[str | None] = mapped_column(String(16))  # ok|nouvelle_version|injoignable|illisible
    dernier_message: Mapped[str | None] = mapped_column(Text)
    dernier_entete: Mapped[str | None] = mapped_column(Text)        # methode entete : ETag/Last-Modified mémorisé
    # SENTINELLE-2 (X5) — mémoire de notification. `dernier_notifie_vu` : le millésime amont déjà ANNONCÉ
    # à Vic (dédup du digest : on ne ré-annonce pas ce qu'il a déjà vu). `echecs_consecutifs` : compteur
    # de sondes en échec d'affilée (X5.2 : on ne prévient qu'à partir de 3 — un serveur public tombe,
    # ça se relève ; remis à 0 dès qu'une sonde repasse ok).
    dernier_notifie_vu: Mapped[str | None] = mapped_column(String(64))
    echecs_consecutifs: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    # SENTINELLE-2 (X6) — trace de l'INJECTION supervisée : quand Vic a cliqué « Injecter cette version »
    # (jamais la sentinelle : elle n'ingère rien), et pour quel millésime amont. Le job d'ingestion
    # EXISTANT est lancé ; ces colonnes rendent le geste visible au tableau (« injection lancée le … »).
    injection_lancee_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    injection_vu: Mapped[str | None] = mapped_column(String(64))
    actif: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))

    source: Mapped[DataSource] = relationship()


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
    """La couche d'explicabilité — la traçabilité EST le produit (brief §2/§5).

    OBSOLÈTE (CONNEXIONS-2, 2026-09-01) : table LIVE non run-scopée (DELETE+INSERT par parcelle,
    cascade/pipeline.py). Plus AUCUN chemin servi ne la lit (anti_fiche + shortlist basculés sur
    `dryrun_cascade_results` run-scopé, KO-2). Encore écrite par le pipeline et lue par Copilote v1
    (à trancher Lot 10). Conservée — la suppression viendra dans un mandat d'hygiène (cf rapport)."""

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
    # M37 : le VERDICT legacy `status` est ÉTEINT (rail mort depuis M34 — le verdict servi
    # vient du tier `parcel_p_score_v2`). La colonne physique est ARCHIVÉE par renommage
    # (rail legacy) SUPPRIMÉE physiquement via ensure_parcel_eval_status_dropped (M46) — plus mappée ici,
    # plus écrite, plus lue. Suppression physique = geste ultérieur Vic, à froid.
    ai_payload: Mapped[dict | None] = mapped_column(JSONB)
    model_version: Mapped[str | None] = mapped_column(String(64))
    rules_version: Mapped[str | None] = mapped_column(String(64))
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    parcel: Mapped[Parcel] = relationship(back_populates="evaluations")


# ─────────────────── DRY-RUN scoring (étages 1+2) — tables PARALLÈLES ───────────────────
# Isolées : jamais lues par l'app. Le calcul à blanc n'écrase JAMAIS parcel_evaluations /
# cascade_results live. Plusieurs runs coexistent par `run_label` (baseline/etape1/etape2/etape3)
# → DIFF entre étapes. Traçabilité : base + Σ(weight_applied) = score, chaque ligne cliquable à sa
# source (source_table + source_id). # dry-run, bascule réelle = chantier ultérieur.

class DryrunParcelEvaluation(Base):
    __tablename__ = "dryrun_parcel_evaluations"
    __table_args__ = (UniqueConstraint("run_label", "parcel_id", name="uq_dryrun_eval"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    run_label: Mapped[str] = mapped_column(String(32))
    parcel_id: Mapped[int] = mapped_column(ForeignKey("parcels.id", ondelete="CASCADE"))
    completeness_score: Mapped[int] = mapped_column(Integer)
    opportunity_score: Mapped[int] = mapped_column(Integer)
    opportunity_base: Mapped[int | None] = mapped_column(Integer)   # base pour tester base+Σ=score
    status: Mapped[str | None] = mapped_column(String(32))          # statut cascade (opportunite/a_creuser…)
    # Matrice Q×A (étape 3) — remplies par compute_matrice()
    q_score: Mapped[int | None] = mapped_column(Integer)            # qualité (étages 0/1)
    a_score: Mapped[int | None] = mapped_column(Integer)            # accessibilité (étage 2)
    a_completude: Mapped[int | None] = mapped_column(Integer)       # % des signaux A connus (≠ UNKNOWN)
    matrice_statut: Mapped[str | None] = mapped_column(String(24))  # chaude/a_surveiller/a_creuser/ecartee
    rules_version: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DryrunCascadeResult(Base):
    __tablename__ = "dryrun_cascade_results"
    __table_args__ = (
        Index("ix_dryrun_cascade", "run_label", "parcel_id"),
        # M5.1 perf : la sous-requête « événement rouge » du panneau seq-scannait 14,2 M
        # de lignes (2,8 s) pour en retenir ~40 — index PARTIEL minuscule, requête en ms.
        Index("ix_dryrun_cascade_evenement", "run_label", "parcel_id",
              postgresql_where=text("evenement = 'rouge'")),
        # M15-B perf : le NOT EXISTS « déjà bâti » de /promesses (Promesses mortes) coûtait ~3,6 s
        # (filtre layer/result sur le tas via ix_dryrun_cascade). Index PARTIEL → probe pur, ~0,6 s.
        Index("ix_dryrun_cascade_bati_exclude", "run_label", "parcel_id",
              postgresql_where=text("layer_name = 'bati' AND result = 'HARD_EXCLUDE'")),
        # M45 (P1) perf : le filtre `flags`/`flags_exclus` (vigilances par type) EXISTS-scannait
        # dryrun_cascade_results en entier (~4-9 s île entière, seq scan de 9,7 M lignes). Index
        # (run_label, layer_name, parcel_id) PARTIEL sur les non-francs (SOFT_FLAG + abf/UNKNOWN)
        # → le filtre par couche de vigilance devient un probe indexé (compteur sous la barre).
        Index("ix_dryrun_cascade_flag_probe", "run_label", "layer_name", "parcel_id",
              postgresql_where=text("result IN ('SOFT_FLAG', 'UNKNOWN')")),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    run_label: Mapped[str] = mapped_column(String(32))
    parcel_id: Mapped[int] = mapped_column(ForeignKey("parcels.id", ondelete="CASCADE"))
    layer_name: Mapped[str] = mapped_column(String(64))
    result: Mapped[str] = mapped_column(String(16))                 # CascadeVerdict.value
    severity: Mapped[str | None] = mapped_column(String(16))
    weight_applied: Mapped[float | None] = mapped_column(Float)     # points signés (∅ si 0)
    detail: Mapped[str | None] = mapped_column(Text)
    data_source_id: Mapped[int | None] = mapped_column(ForeignKey("data_sources.id"))
    source_table: Mapped[str | None] = mapped_column(String(48))    # cliquable : table
    source_id: Mapped[str | None] = mapped_column(String(64))       # cliquable : id de l'enregistrement
    evenement: Mapped[str | None] = mapped_column(String(16))       # 'rouge' (BODACC ouverte) → bascule chaude (étape 3)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


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


# ──────────────── veille_succession + gel des scores (M1 v1.3, 12/07/2026) ────────────────

class ParcelVeilleSuccession(Base):
    """Tag RADAR PATRIMONIAL (horizon 3-7 ans) — HORS Score V, jamais brûlante.

    PM à identité SIREN confirmée (jamais match nom) ∧ (dirigeant ≥ 70 ans OU SCI dormante).
    Reconstruite à chaque run Score V (idempotent)."""

    __tablename__ = "parcel_veille_succession"

    parcelle_id: Mapped[str] = mapped_column(String(14), primary_key=True)
    siren: Mapped[str] = mapped_column(String(9))
    dirigeant_age: Mapped[int | None] = mapped_column(Integer)   # NULL = motif SCI seule
    sci_dormante: Mapped[bool] = mapped_column(default=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ScoreSnapshot(Base):
    """GEL d'un état de scoring (M1 lot 4) — base de la validation forward DVF 2026.
    Un label ne s'écrase JAMAIS (protocole d'arbitrage : reports/m1-v13/snapshots.md)."""

    __tablename__ = "score_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(String(64), unique=True)
    run_label: Mapped[str] = mapped_column(String(32))
    brulante_threshold: Mapped[int] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ScoreSnapshotParcelle(Base):
    __tablename__ = "score_snapshot_parcelles"

    id: Mapped[int] = mapped_column(primary_key=True)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey("score_snapshots.id", ondelete="CASCADE"), index=True)
    parcelle_id: Mapped[str] = mapped_column(String(14), index=True)
    statut: Mapped[str | None] = mapped_column(String(32))   # 32 : reçoit le tier (declasse_* 26 car.)
    v_score: Mapped[int | None] = mapped_column(Integer)
    v_band: Mapped[str | None] = mapped_column(String(8))
    brulante: Mapped[bool] = mapped_column(default=False)
    veille_succession: Mapped[bool] = mapped_column(default=False)


# ──────────── pm_proprietaires_millesimes (M2 panel point-in-time, 12/07/2026) ────────────

class PmProprietaireMillesime(Base):
    """Panel POINT-IN-TIME des propriétaires PM (DGFiP, situation au 1er janvier du
    millésime) — département 974 entier, millésimes 2021-2024. Table VERSIONNÉE, séparée :
    `parcelle_personne_morale` (situation 2025, prod) et le moteur V restent intacts."""

    __tablename__ = "pm_proprietaires_millesimes"
    __table_args__ = (UniqueConstraint("millesime", "idu", name="uq_pm_millesime_idu"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    millesime: Mapped[int] = mapped_column(Integer, index=True)
    idu: Mapped[str] = mapped_column(String(14), index=True)
    groupe: Mapped[int | None] = mapped_column(Integer)
    groupe_label: Mapped[str | None] = mapped_column(String(80))
    forme_juridique: Mapped[str | None] = mapped_column(String(20))
    denomination: Mapped[str | None] = mapped_column(String(200))
    siren: Mapped[str | None] = mapped_column(String(20))
    url_source: Mapped[str | None] = mapped_column(Text)
    date_import: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ─────────────────────── source_checks (VUES item 4, 12/07/2026) ───────────────────────

class SourceCheck(Base):
    """Vérification qu'une source est bien à sa DERNIÈRE version publiée (fraîcheur prouvée).

    Remplie par le mandat d'audit data — vide en attendant. Le front n'affiche la mention
    « dernière version publiée — vérifié le X » QUE si une ligne existe ici : on n'invente
    JAMAIS une date de vérification."""

    __tablename__ = "source_checks"

    id: Mapped[int] = mapped_column(primary_key=True)
    data_source_id: Mapped[int] = mapped_column(
        ForeignKey("data_sources.id", ondelete="CASCADE"), index=True)
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    note: Mapped[str | None] = mapped_column(Text)


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
    date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # DATE_REELLE_AUTORISATION
    # M38 : date de DÉPÔT (Sitadel3 DR_DEPOT), validée. Le permis n'entre au dataset qu'une
    # fois AUTORISÉ (les refus/en-instance ne sont pas publiés) — cette date DATE le dépôt du
    # permis abouti, ~9 mois avant `date` (délai médian 276 j mesuré M38-P0). Informatif seul.
    date_depot: Mapped[date | None] = mapped_column(Date)
    idu_codes: Mapped[list | None] = mapped_column(JSONB)    # IDU 14 car. reconstitués (1..3)
    commune: Mapped[str | None] = mapped_column(String(64))
    geom: Mapped[object | None] = mapped_column(Geometry("POINT", srid=SRID, spatial_index=True))
    raw: Mapped[dict | None] = mapped_column(JSONB)


class BodaccProcedure(Base):
    """Annonce BODACC de PROCÉDURE COLLECTIVE (Vague A1 — signal accessibilité du deal).

    Source ouverte DILA (Licence Ouverte v2.0, API Opendatasoft, sans clé). Un SIREN peut
    porter plusieurs annonces (jugements successifs) → plusieurs lignes ; dédup par `annonce_id`.
    Le croisement SIREN ↔ parcelle_personne_morale produit le flag « foncier sous pression »
    (vue v_foncier_sous_pression). NE touche PAS au scoring (# TODO étage 2)."""

    __tablename__ = "bodacc_procedures"
    __table_args__ = (
        UniqueConstraint("annonce_id", name="uq_bodacc_annonce"),
        Index("ix_bodacc_siren", "siren"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    annonce_id: Mapped[str] = mapped_column(String(20))       # id ODS « A200902491993 » (dédup)
    siren: Mapped[str] = mapped_column(String(9))
    type_procedure: Mapped[str | None] = mapped_column(String(200))   # jugement.nature
    famille_jugement: Mapped[str | None] = mapped_column(String(100))  # jugement.famille
    date_annonce: Mapped[date | None] = mapped_column(Date)            # dateparution (ISO)
    date_jugement_txt: Mapped[str | None] = mapped_column(String(64))  # jugement.date (texte FR brut)
    tribunal: Mapped[str | None] = mapped_column(Text)
    numero_annonce: Mapped[int | None] = mapped_column(Integer)
    publication: Mapped[str | None] = mapped_column(String(4))         # « A »
    url_source: Mapped[str | None] = mapped_column(Text)
    raw: Mapped[dict | None] = mapped_column(JSONB)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PmDirigeant(Base):
    """Dirigeant / représentant d'une personne morale foncière (Vague A3 — INPI RNE).

    Source : API REST publique du RNE (INPI), croisée par SIREN avec parcelle_personne_morale.
    Un SIREN porte N dirigeants (`composition.pouvoirs[]`) → N lignes ; dédup par
    (siren, representant_id). Le signal « âge dirigeant » (aîné des dirigeants PHYSIQUES)
    alimente `propension_vendre` via la vue v_pm_propension_vendre.

    RGPD (règle d'archi #2) : personnes morales en open data complet ; on ne conserve les
    données d'une personne PHYSIQUE que si l'entreprise est DIFFUSIBLE (`diffusible`), et le
    signal reste INTERNE (priorisation), jamais un export nominatif de masse. Date de naissance
    au MOIS uniquement ('YYYY-MM', granularité diffusible RNE). NE touche PAS au score (# TODO étage 2)."""

    __tablename__ = "pm_dirigeants"
    __table_args__ = (
        UniqueConstraint("siren", "representant_id", name="uq_pm_dirigeant"),
        Index("ix_pm_dirigeant_siren", "siren"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    siren: Mapped[str] = mapped_column(String(9))                      # SIREN de la société détenue
    representant_id: Mapped[str | None] = mapped_column(String(40))    # UUID RNE du pouvoir (dédup)
    type_personne: Mapped[str | None] = mapped_column(String(12))      # INDIVIDU | ENTREPRISE
    nom: Mapped[str | None] = mapped_column(String(120))               # si INDIVIDU diffusible
    prenoms: Mapped[str | None] = mapped_column(String(200))
    date_naissance: Mapped[str | None] = mapped_column(String(7))      # 'YYYY-MM' (mois, jamais le jour)
    role_entreprise: Mapped[str | None] = mapped_column(String(8))     # code rôle RNE (« 30 » = gérant…)
    date_prise_fonction: Mapped[date | None] = mapped_column(Date)     # dateEffetRoleDeclarant (souvent absent)
    gerant_siren: Mapped[str | None] = mapped_column(String(9))        # si dirigeant = personne morale (gigogne)
    actif: Mapped[bool | None] = mapped_column(Boolean)
    diffusible: Mapped[bool | None] = mapped_column(Boolean)           # entreprise en diffusion commerciale
    raw: Mapped[dict | None] = mapped_column(JSONB)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PmDirigeantGigogne(Base):
    """Dirigeant PHYSIQUE résolu par récursion DEPTH-1 (Vague A3, 2ᵉ itération).

    Pour un SIREN foncier dont TOUS les dirigeants sont des personnes morales (`age_source =
    'aucun_individu'`), on suit le SIREN gérant-société (`gerant_siren`) sur UN seul niveau et on
    rattache ici les personnes physiques trouvées → la vue calcule alors `age_source =
    'gerant_societe'`. Bornée à 1 niveau, détection de cycle côté ingestion. La table depth-0
    `pm_dirigeants` n'est PAS modifiée. RGPD : mêmes gardes (diffusibilité). # TODO étage 2."""

    __tablename__ = "pm_dirigeant_gigogne"
    __table_args__ = (
        UniqueConstraint("siren", "gerant_siren", "representant_id", name="uq_pm_dirigeant_gigogne"),
        Index("ix_pm_gigogne_siren", "siren"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    siren: Mapped[str] = mapped_column(String(9))                      # SIREN foncier CIBLE
    gerant_siren: Mapped[str] = mapped_column(String(9))              # SIREN de la société gérante suivie
    representant_id: Mapped[str | None] = mapped_column(String(40))    # UUID RNE du pouvoir chez le gérant
    nom: Mapped[str | None] = mapped_column(String(120))
    prenoms: Mapped[str | None] = mapped_column(String(200))
    date_naissance: Mapped[str | None] = mapped_column(String(7))      # 'YYYY-MM'
    role_entreprise: Mapped[str | None] = mapped_column(String(8))
    diffusible: Mapped[bool | None] = mapped_column(Boolean)
    raw: Mapped[dict | None] = mapped_column(JSONB)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DpeRecord(Base):
    """Diagnostic de Performance Énergétique (Vague C2 — ADEME `dpe03existant`, logements existants).

    Un DPE par logement (dédup `numero_dpe`). Signal `passoire_thermique` (F/G) = pression
    réglementaire datée sur le propriétaire (cf. vue v_passoire_thermique). Rattachement parcelle
    100 % LOCAL (le `_geopoint` ADEME est FAUX au 974) : `identifiant_ban` → table `adresses`
    ('ban_locale'), sinon point BAN natif EPSG:2975 → ST_Contains ('point_ban'), sinon adresse
    brute normalisée → `adresses` ('adresse_locale'), sinon 'aucun'.

    Représentativité : gisement ADEME complet = ~912 DPE pour toute l'île (11/07/2026), flux
    ~10/mois depuis 07/2021 — signal « positif quand présent », JAMAIS exhaustif. Alimente le
    Score V (famille E)."""

    __tablename__ = "dpe_records"
    __table_args__ = (
        UniqueConstraint("numero_dpe", name="uq_dpe_numero"),
        Index("ix_dpe_insee", "code_insee"),
        Index("ix_dpe_parcelle", "parcelle_idu"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    numero_dpe: Mapped[str] = mapped_column(String(40))               # identifiant ADEME (dédup)
    etiquette_dpe: Mapped[str | None] = mapped_column(String(1))      # A…G (énergie)
    etiquette_ges: Mapped[str | None] = mapped_column(String(1))      # A…G (climat)
    type_batiment: Mapped[str | None] = mapped_column(String(20))     # maison / appartement / immeuble
    surface_habitable: Mapped[float | None] = mapped_column(Float)
    annee_construction: Mapped[int | None] = mapped_column(Integer)
    adresse: Mapped[str | None] = mapped_column(Text)
    code_insee: Mapped[str | None] = mapped_column(String(5))
    code_postal: Mapped[str | None] = mapped_column(String(5))
    date_etablissement: Mapped[date | None] = mapped_column(Date)
    lon: Mapped[float | None] = mapped_column(Float)                  # point local (pas le _geopoint ADEME)
    lat: Mapped[float | None] = mapped_column(Float)
    geocode_score: Mapped[float | None] = mapped_column(Float)        # score_ban ADEME
    parcelle_idu: Mapped[str | None] = mapped_column(String(14))      # rattachement local, nullable
    rattachement: Mapped[str | None] = mapped_column(String(16))      # 'ban_locale'|'point_ban'|'adresse_locale'|'aucun'
    raw: Mapped[dict | None] = mapped_column(JSONB)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ParcelAmenite(Base):
    """Signal d'aménités par parcelle (Vague C bonus — OSM). Distance (m, en 2975) au plus proche
    POI de chaque catégorie depuis le centroïde. Les POI bruts sont dans spatial_layers kind='amenite'.

    Signal CALCULÉ (pas des icônes) : distances stockées BRUTES ; l'agrégation pondérée en
    « score d'aménités » est # TODO étage 1 (poids tranchés au calibrage). NE touche PAS au score."""

    __tablename__ = "parcel_amenites"
    __table_args__ = (UniqueConstraint("parcel_id", name="uq_parcel_amenite"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    parcel_id: Mapped[int] = mapped_column(ForeignKey("parcels.id", ondelete="CASCADE"))
    dist_ecole_m: Mapped[float | None] = mapped_column(Float)
    dist_sante_m: Mapped[float | None] = mapped_column(Float)
    dist_commerce_m: Mapped[float | None] = mapped_column(Float)
    dist_tcsp_m: Mapped[float | None] = mapped_column(Float)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ─────────────────────── pipeline de prospection (Kanban) ───────────────────────

class PipelineEntry(Base, TimestampMixin):
    """Une parcelle suivie dans le pipeline de prospection (Kanban).

    `status` (colonne) et `priority` sont des CLÉS validées contre config/pipeline.yaml
    (colonnes en config, pas en dur). Une parcelle = au plus une entrée (parcel_id unique).
    `created_at` (mixin) sert de date d'ajout.
    """

    __tablename__ = "pipeline_entries"
    # AUDIT PAIEMENT · SEC-IDOR — la cloison change la clé d'unicité : une parcelle est
    # unique PAR COMPTE (compte_id, parcel_id), plus globalement (api/tenant.ensure_scoping
    # rekeye en base). L'ancien uq_pipeline_parcel est retiré là-bas.
    __table_args__ = (UniqueConstraint("compte_id", "parcel_id", name="uq_pipeline_compte_parcel"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    compte_id: Mapped[int | None] = mapped_column(Integer, index=True)  # FK+cascade posée hors ORM
    parcel_id: Mapped[int] = mapped_column(ForeignKey("parcels.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(48))          # clé de colonne (config)
    priority: Mapped[str] = mapped_column(String(16))        # clé de priorité (config)
    notes: Mapped[str] = mapped_column(Text, default="", server_default="")
    reminder_date: Mapped[date | None] = mapped_column(Date)  # rappel optionnel
    # Prospection MANUELLE (Niveau 1) : statut propriétaire, contact saisi, action suivante…
    # AUCUNE donnée nominative externe — tout est renseigné par l'utilisateur. RGPD : effaçable.
    prospection: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    # référence du PROJET d'où vient la piste (copilote-projet) — le kanban sait « d'où vient »
    projet_id: Mapped[int | None] = mapped_column(ForeignKey("projets.id", ondelete="SET NULL"))
    # M137 — ARCHIVAGE réversible (« aucune carte perdue ») : NULL = active ; sinon date d'archivage.
    # Plus de suppression dure. Filtré partout (listes/compteurs), toujours conjoint à compte_id.
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    parcel: Mapped[Parcel] = relationship()


# ─────────────────────── projets (copilote-projet) ───────────────────────

class Projet(Base, TimestampMixin):
    """Un PROJET de promoteur — M120 : IDENTITÉ + CADRAGE + SHORTLIST FIGÉE.

    UN SEUL système de critères : le `cadrage` EST un jeu de filtres FiltreCriteres
    sauvegardé (la dérivation parallèle `derive_filtres` a disparu — M120). Le run part
    UNE FOIS à la fin du cadrage : la shortlist (projet_parcelles) est ÉCRITE puis FIGÉE,
    datée par `derniere_execution_at`. Elle ne bouge JAMAIS seule — seul un rejeu explicite
    la rafraîchit (en conservant les tris).

    Colonnes vivantes (M120) :
      - `filtres`  : le CADRAGE — jeu de filtres `Filters` (forme front camelCase :
        communes, surfaceMin, sdpMin, flags, flagsExclus, signaux…). Point unique des critères.
      - `identite` : métadonnées INFORMATIVES (budget_eur, type_logement, date_livraison) —
        affichées telles quelles, elles n'alimentent AUCUN filtre (mesuré M119/M120).
      - `derniere_execution_at` : date de la shortlist figée (« cadrage du JJ/MM/AAAA »).
      - `shortlist_perimee` : le cadrage a changé depuis le dernier run → un rejeu est proposé.

    Legacy (M120, non lus/écrits — conservés le temps de la migration, non destructif) :
      `fiche` (ancienne fiche 7 champs), `programme` (ancien paramétrage M22).
    """

    __tablename__ = "projets"

    id: Mapped[int] = mapped_column(primary_key=True)
    # AUDIT PAIEMENT · SEC-IDOR — cloison multi-tenant : le projet appartient à UN compte
    # (NULL = bucket pilote/démo hérité). Toute lecture/écriture est filtrée par le compte de
    # la session (api/tenant.py). Colonne aussi posée hors ORM (ADD COLUMN IF NOT EXISTS).
    compte_id: Mapped[int | None] = mapped_column(Integer, index=True)  # FK+cascade posée hors ORM
    nom: Mapped[str] = mapped_column(String(160))             # éditable
    filtres: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")  # M120 : LE CADRAGE
    identite: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")  # M120 : infos (budget/type/date)
    statut: Mapped[str] = mapped_column(String(16), default="actif", server_default="actif")
    derniere_execution_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # date shortlist figée
    shortlist_perimee: Mapped[bool] = mapped_column(default=False, server_default="false")  # cadrage changé → rejeu proposé
    # FIX-PROJETS (fin M140) — CACHE du total VIF du cadrage (count ~0,2-1 s) : sert le compteur
    # « proposées » à la LISTE sans le payer à chaque rendu ; fraîcheur = `cadrage_total_at`.
    # Rafraîchi à la création / au rejeu / à l'ouverture / au changement de cadrage.
    cadrage_total: Mapped[int | None] = mapped_column(Integer)
    cadrage_total_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fiche: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")  # M120 legacy (migration, EN EXTINCTION — lu une fois au backfill identite, jamais après)
    programme: Mapped[dict | None] = mapped_column(JSONB)     # M120 legacy EN EXTINCTION — jamais lu ni écrit (conservé, non-destructif)


class ProjetParcelle(Base, TimestampMixin):
    """Liaison projet × parcelle × STATUT — le cœur du parcours de sélection (Tinder).

    ADDITIVE : le modèle Projet reste piloté par les critères (fiche/filtres) ; cette table
    porte l'ÉTAT de tri d'une parcelle DANS un projet. Le tri fait passer `proposee` →
    `retenue` | `ecartee`. RIEN n'est détruit : `ecartee` reste en base, récupérable (la
    boussole « ne jamais perdre une parcelle »). `rang` = ordre de proposition (best-first,
    rejoué à chaque proposition) ; `proposee_at` fige la 1re proposition. Aucune touche au
    scoring : les parcelles viennent du run servi, on ne stocke qu'un statut.
    """

    __tablename__ = "projet_parcelles"
    __table_args__ = (UniqueConstraint("projet_id", "parcel_id", name="uq_projet_parcelle"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    projet_id: Mapped[int] = mapped_column(ForeignKey("projets.id", ondelete="CASCADE"), index=True)
    parcel_id: Mapped[int] = mapped_column(ForeignKey("parcels.id", ondelete="CASCADE"))
    statut: Mapped[str] = mapped_column(String(16))   # proposee | retenue | ecartee | a_analyser
    rang: Mapped[int | None] = mapped_column()        # ordre de proposition (best-first)
    proposee_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # M2 — non-perte au rejeu : une décision (retenue…) qui ne matche plus les critères du jour
    # RESTE, marquée « hors critères actuels » (jamais évincée en silence). ADDITIF, défaut false.
    hors_criteres: Mapped[bool] = mapped_column(server_default="false", default=False)

    parcel: Mapped[Parcel] = relationship()


# ───────────────────────────── Score V — Vendabilité (Stage 3 additif) ─────────────────────────────
# Mandat SPEC-LABUSE-SCORE-V v1.0. ADDITIF : ne touche ni la cascade, ni Q/A, ni la matrice.


class OwnerEnrichment(Base):
    """Cache par SIREN des enrichissements propriétaire (Score V).

    Une ligne = la réponse BRUTE cachée d'une source (`rne` — déjà en base via pm_dirigeants —
    ou `recherche_entreprises`, fallback sans auth). Resumable : un SIREN présent n'est jamais
    re-requêté ; `payload` garde tout (état administratif, siège, NAF, dirigeants…)."""

    __tablename__ = "owner_enrichment"

    siren: Mapped[str] = mapped_column(String(9), primary_key=True)
    denomination: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(String(32))      # rne | recherche_entreprises
    payload: Mapped[dict] = mapped_column(JSONB)                # réponse brute cachée (resumable)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class OwnerDenomLookup(Base):
    """Cache des recherches PAR DÉNOMINATION (fallback matching §4.2 — liens DGFiP sans SIREN).

    Clé = dénomination NORMALISÉE (uppercase, unaccent, sans tokens de forme juridique).
    `status` : found (1 candidat → siren) | ambiguous (candidats en review queue) | not_found.
    Table de cache technique (resumabilité) — la vérité du match reste parcel_v_score."""

    __tablename__ = "owner_denom_lookup"

    denomination_norm: Mapped[str] = mapped_column(Text, primary_key=True)
    status: Mapped[str] = mapped_column(String(12))             # found | ambiguous | not_found
    siren: Mapped[str | None] = mapped_column(String(9))
    candidats: Mapped[dict | None] = mapped_column(JSONB)       # liste brute si ambigu
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BodaccAnnonceOwner(Base):
    """Annonces BODACC des SIREN propriétaires, TOUTES familles utiles au Score V.

    Familles : `pcl` (procédures collectives), `radiation`, `vente_cession`. Complète
    bodacc_procedures (Vague A1, procédures collectives seulement) SANS y toucher.
    Détermination d'état (en cours / clôturée) faite par le moteur, pas ici."""

    __tablename__ = "bodacc_annonces_owner"
    __table_args__ = (Index("ix_bodacc_owner_siren", "siren"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True)   # « <id ODS>:<siren> » (dédup)
    siren: Mapped[str] = mapped_column(String(9))
    famille: Mapped[str | None] = mapped_column(String(16))         # pcl | radiation | vente_cession
    nature: Mapped[str | None] = mapped_column(String(200))         # ex. jugement d'ouverture LJ, clôture…
    date_annonce: Mapped[date | None] = mapped_column(Date)
    payload: Mapped[dict] = mapped_column(JSONB)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MatchingReviewQueue(Base):
    """File de revue humaine des matchs AMBIGUS (fallback dénomination, plusieurs candidats)."""

    __tablename__ = "matching_review_queue"

    id: Mapped[int] = mapped_column(primary_key=True)
    parcelle_id: Mapped[str | None] = mapped_column(String(14))     # idu
    denomination: Mapped[str | None] = mapped_column(Text)
    candidats: Mapped[dict | None] = mapped_column(JSONB)           # SIREN candidats ambigus
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ParcelVScore(Base):
    """Score V (Vendabilité) par parcelle — Stage 3 additif, matérialisé par le batch score-v.

    v_score NULL = non applicable (propriétaire public / bailleur social, D4).
    `signals` = JSONB des signaux RETENUS (format §5.4), lu tel quel par le panneau UI."""

    __tablename__ = "parcel_v_score"
    __table_args__ = (
        Index("ix_parcel_v_score_band", "v_band"),
        Index("ix_parcel_v_score_siren", "owner_siren"),
    )

    parcelle_id: Mapped[str] = mapped_column(String(14), primary_key=True)   # idu
    v_score: Mapped[int | None] = mapped_column(SmallInteger)                # 0-100, NULL si N.A.
    v_band: Mapped[str | None] = mapped_column(String(8))                    # fort|present|faible|aucun|na
    v_coverage: Mapped[str] = mapped_column(String(8))                       # full | partial
    v_confidence: Mapped[float | None] = mapped_column(Numeric(3, 2))
    owner_type: Mapped[str | None] = mapped_column(String(12))               # pm|pp|public|bailleur|copro
    owner_siren: Mapped[str | None] = mapped_column(String(9))
    owner_denomination: Mapped[str | None] = mapped_column(Text)
    signals: Mapped[dict] = mapped_column(JSONB, default=list, server_default="[]")
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class DvfMutationParcelle(Base):
    """Mutations géo-DVF au NIVEAU PARCELLE (remédiation P1 Score V).

    Lignes brutes utiles des CSV files.data.gouv.fr/geo-dvf (dept 974). Distincte de
    dvf_mutations (points, cascade « marché actif ») qui reste intouchée. ⚠ Fenêtre
    observable : millésimes 2021→2025 seulement (2014-2020 retirés de la distribution
    officielle — fenêtre glissante 5 ans DGFiP). Un futur mandat data l'étendra."""

    __tablename__ = "dvf_mutations_parcelle"
    __table_args__ = (
        Index("ix_dvfp_parcelle", "id_parcelle"),
        Index("ix_dvfp_date", "date_mutation"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    id_mutation: Mapped[str] = mapped_column(Text)
    date_mutation: Mapped[date | None] = mapped_column(Date)
    nature_mutation: Mapped[str | None] = mapped_column(Text)
    valeur_fonciere: Mapped[float | None] = mapped_column(Float)
    code_commune: Mapped[str | None] = mapped_column(Text)
    id_parcelle: Mapped[str] = mapped_column(String(14))
    type_local: Mapped[str | None] = mapped_column(Text)
    surface_reelle_bati: Mapped[float | None] = mapped_column(Float)
    surface_terrain: Mapped[float | None] = mapped_column(Float)
    nature_culture: Mapped[str | None] = mapped_column(Text)
    longitude: Mapped[float | None] = mapped_column(Float)
    latitude: Mapped[float | None] = mapped_column(Float)
    millesime: Mapped[int] = mapped_column(SmallInteger)


# ──────────────── scoring v2 produit — P × C (M5, 12/07/2026) ────────────────

class PScoreV2Run(Base):
    """Un RUN de scoring v2 = une exécution de `labuse score-v2` — versionné,
    jamais d'écrasement silencieux (run_id unique, refus si existant)."""

    __tablename__ = "p_score_v2_runs"

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    model_version: Mapped[str] = mapped_column(String(32))
    model_sha256: Mapped[str] = mapped_column(String(64))
    params: Mapped[dict | None] = mapped_column(JSONB)      # N_e, N_s, seuils brûlante…
    n_parcelles: Mapped[int | None] = mapped_column(Integer)
    duration_s: Mapped[int | None] = mapped_column(Integer)
    snapshot_label: Mapped[str | None] = mapped_column(String(64))
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ParcelPScoreV2(Base):
    """Score P v2 par parcelle et par run (M5 lot 1.1).

    p_raw est STOCKÉ mais jamais montré par défaut (saturation isotonique en
    tête) : l'affichage produit = mult_base (« ×N vs moyenne ») + percentile +
    rang. Le rang est calculé HORS copro (univers produit par défaut)."""

    __tablename__ = "parcel_p_score_v2"
    __table_args__ = (
        UniqueConstraint("run_id", "parcelle_id", name="uq_p_v2_run_parcelle"),
        Index("ix_p_v2_run_rang", "run_id", "rang"),
        Index("ix_p_v2_run_tier", "run_id", "tier"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), index=True)
    parcelle_id: Mapped[str] = mapped_column(String(14), index=True)
    p_raw: Mapped[float] = mapped_column(Float)
    mult_base: Mapped[float] = mapped_column(Float)          # P / taux de base
    percentile: Mapped[float | None] = mapped_column(Float)  # 0-100 ; NULL = copro
    rang: Mapped[int | None] = mapped_column(Integer)        # NULL = copro (hors ranking)
    contrib_z: Mapped[float] = mapped_column(Float)
    contrib_d: Mapped[float] = mapped_column(Float)
    top5_contributions: Mapped[list | None] = mapped_column(JSONB)
    copro: Mapped[bool] = mapped_column(default=False)
    # 32 (et non 24) : les tiers de déclassement `declasse_non_constructible` (26 car.) débordaient
    # varchar(24) → erreur d'écriture SQLAlchemy (bascule 29/07). Idem score_snapshot_parcelles.statut.
    tier: Mapped[str | None] = mapped_column(String(32))
    event_date: Mapped[date | None] = mapped_column(Date)    # dernier événement daté v1.3
    model_version: Mapped[str] = mapped_column(String(32))
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # Indice de confiance données (M9 lot 1) — méta d'affichage, CLOISONNÉE du score P.
    # Ne participe NI au rang NI au tier NI à p_raw : complétude pondérée des 9 groupes
    # nullables (spec §1.4 A.4). Backfill LECTURE depuis p_model_ext_dataset, cf. scoring/icd.py.
    icd: Mapped[int | None] = mapped_column(SmallInteger)    # 0-100, NULL = non évalué
    icd_detail: Mapped[dict | None] = mapped_column(JSONB)   # {groupe: bool} des 9 groupes


def ensure_parcel_eval_status_dropped(engine) -> None:
    """M46 (Lot C) — SUPPRESSION PHYSIQUE du rail legacy `parcel_evaluations.status` (le geste
    « à froid » prévu en M37, exécuté à froid ici).

    Le rail est éteint depuis M37 (verdict 100 % tier) et l'archive `status_pre_m37` a tenu
    plusieurs jours sans anomalie. Vérifié M46 : AUCUN lecteur de données ne subsiste — toutes
    les mentions de `parcel_evaluations.status` sont des commentaires « éteint » ; les lecteurs
    vivants lisent `dryrun_parcel_evaluations.status` (table DISTINCTE, servie, conservée).
    Idempotent : DROP des colonnes `status` (si jamais restée) et `status_pre_m37` si présentes ;
    sur base neuve aucune n'existe → no-op. (M37 renommait status→status_pre_m37 ; M46 solde.)"""
    from sqlalchemy import text as _t
    with engine.begin() as c:
        c.execute(_t("ALTER TABLE parcel_evaluations DROP COLUMN IF EXISTS status_pre_m37"))
        c.execute(_t("ALTER TABLE parcel_evaluations DROP COLUMN IF EXISTS status"))


def ensure_sitadel_depot(engine) -> None:
    """M38 — colonne `date_depot` (Sitadel3 DR_DEPOT) sur sitadel_permits. Idempotent
    (ADD COLUMN IF NOT EXISTS) — durable au rebuild, présent pour la fiche même avant
    ré-ingestion. Informatif seul, jamais lu par le scoring."""
    from sqlalchemy import text as _t
    with engine.begin() as c:
        c.execute(_t("ALTER TABLE sitadel_permits ADD COLUMN IF NOT EXISTS date_depot date"))


def _ensure_schema_steps(engine, *, geom_backfill: bool) -> None:
    """P2-37 — LISTE UNIQUE des réconciliations de schéma idempotentes, partagée par `create_all`
    (première création, backfill geom) et `ensure_schema` (boot/doctor, sans backfill). Avant, les
    deux tenaient chacune leur liste et elles DIVERGEAIENT (4 ensures seulement dans create_all :
    status legacy droppé, sitadel_depot, icd, signalements ; 2 seulement dans ensure_schema :
    promesses_index, data_sources_millesime). Toute nouvelle table/colonne/index ADDITIVE s'ajoute
    ICI, une seule fois → plus de dérive possible. Seul `backfill` du geom_2975 diffère (paramétré)."""
    ensure_parcel_eval_status_dropped(engine)    # M46 (Lot C) : rail legacy status SUPPRIMÉ (à froid)
    ensure_sitadel_depot(engine)                 # M38 : date de dépôt Sitadel (DR_DEPOT)
    ensure_geom_2975(engine, backfill=geom_backfill)
    ensure_parcel_origine(engine)
    ensure_residuel_cache(engine)
    ensure_constructibilite_cache(engine)   # déclassement étage 0 (tête de liste non constructible)
    ensure_au_statut_cache(engine)          # AU-OUVERTURE : statut d'ouverture des zones AU non lu
    ensure_saved_filters(engine)
    ensure_personnes_morales(engine)
    ensure_bodacc_view(engine)
    ensure_pm_propension_view(engine)
    ensure_passoire_thermique_view(engine)
    ensure_bilan_params(engine)
    ensure_watch_zones(engine)
    ensure_watch_snap_no_orphans(engine)    # FIX-C6 (GB-063) : purge orphelins snap + FK CASCADE
    ensure_derived_read_stubs(engine)       # FIX-C6 (GB-049) : stubs vides tables dérivées lues
    ensure_pipeline_prospection(engine)
    ensure_pipeline_projet(engine)
    ensure_pipeline_archived(engine)
    ensure_enrichment_cache(engine)
    ensure_score_v_view(engine)
    ensure_dvf_marche(engine)
    ensure_zone_filtre(engine)              # M99 : clé normalisée du filtre zonage
    ensure_data_sources_millesime(engine)   # M32 Phase B §2 : colonnes millésime amont
    ensure_data_sources_status_norm(engine)  # FIX-SOURCES S2 : statut normalisé (casse enum)
    ensure_source_veille(engine)            # SENTINELLE-1 W1/W5 : table de veille amont + seed
    ensure_icd_columns(engine)              # M9 lot 1
    ensure_signalements(engine)             # M9 lot 3
    from . import reglages as _reglages     # CONNEXIONS-2 Lot 7.1 : table app_reglages (toggles runtime)
    _reglages.ensure_reglages(engine)
    ensure_suggestions(engine)              # M16-C
    ensure_promesses_index(engine)          # index partiel /promesses
    ensure_flags_probe_index(engine)        # M45 (P1)
    ensure_parcel_flags(engine)             # M45 (P2)


def create_all(engine) -> None:
    Base.metadata.create_all(engine)
    _ensure_schema_steps(engine, geom_backfill=True)


def ensure_icd_columns(engine) -> None:
    """Colonnes ICD (indice de confiance données) sur parcel_p_score_v2 — M9 lot 1.
    Méta d'affichage annexe (cf. scoring/icd.py), CLOISONNÉE du score P. Idempotent."""
    from sqlalchemy import text as _t

    with engine.begin() as c:
        c.execute(_t("ALTER TABLE parcel_p_score_v2 "
                     "ADD COLUMN IF NOT EXISTS icd smallint"))
        c.execute(_t("ALTER TABLE parcel_p_score_v2 "
                     "ADD COLUMN IF NOT EXISTS icd_detail jsonb"))
        # FIX-C6 (GB-058) — /map/tiles/meta fait `max(computed_at) WHERE run_id=…` (tiles.py:332,
        # appelé au 1er paint carte) : sans index sur (run_id, computed_at) c'est un Parallel Seq
        # Scan de ~430k lignes (p95 mesuré ~3,9 s au cycle 6). Index couvrant → max index-only.
        c.execute(_t("CREATE INDEX IF NOT EXISTS ix_p_v2_run_computed "
                     "ON parcel_p_score_v2 (run_id, computed_at)"))


def ensure_signalements(engine) -> None:
    """Table `signalements` (M9 lot 3) — file de QA humaine. Aucune action
    automatique sur les données : un signalement est un ticket horodaté.
    Idempotent (CREATE TABLE IF NOT EXISTS) ; durable au rebuild.

    CONNEXIONS-2 Lot 3 (KO-4) : c'est LA table UNIQUE de signalement. Le « Signaler » de la fiche
    (type='fiche', parcelle_id) ET le « Signaler » du Radar (type='annonce', bien_id) écrivent ici.
    L'admin les voit et les traite au dashboard (plus de revue CLI-only) : colonnes `type`, `bien_id`,
    `parcelle_id` nullable pour l'annonce."""
    from sqlalchemy import text as _t

    with engine.begin() as c:
        c.execute(_t("""
            CREATE TABLE IF NOT EXISTS signalements (
                id           bigserial PRIMARY KEY,
                parcelle_id  varchar(14) NOT NULL,
                type_erreur  varchar(48) NOT NULL,
                champ        varchar(64),
                commentaire  text,
                utilisateur  varchar(128),
                statut       varchar(24) NOT NULL DEFAULT 'nouveau',
                created_at   timestamptz NOT NULL DEFAULT now()
            )"""))
        # KO-4 — colonnes d'unification (idempotent). type='fiche' par défaut = comportement legacy.
        c.execute(_t("ALTER TABLE signalements ADD COLUMN IF NOT EXISTS type varchar(16) NOT NULL DEFAULT 'fiche'"))
        c.execute(_t("ALTER TABLE signalements ADD COLUMN IF NOT EXISTS bien_id bigint"))
        c.execute(_t("ALTER TABLE signalements ADD COLUMN IF NOT EXISTS traite_at timestamptz"))
        # un signalement d'annonce n'a pas de parcelle_id → la contrainte NOT NULL doit sauter.
        c.execute(_t("ALTER TABLE signalements ALTER COLUMN parcelle_id DROP NOT NULL"))
        c.execute(_t("CREATE INDEX IF NOT EXISTS ix_signalements_parcelle "
                     "ON signalements (parcelle_id)"))
        c.execute(_t("CREATE INDEX IF NOT EXISTS ix_signalements_statut "
                     "ON signalements (statut, created_at)"))


def ensure_suggestions(engine) -> None:
    """Table `suggestions` (M16-C) — retours utilisateur (« proposer une amélioration ») envoyés
    depuis le menu compte. Destination CONSULTABLE et durable (pas d'e-mail : aucune infra e-mail
    dans l'app). Vic lit via `labuse suggestions` ou SELECT. Idempotent."""
    from sqlalchemy import text as _t

    with engine.begin() as c:
        c.execute(_t("""
            CREATE TABLE IF NOT EXISTS suggestions (
                id           bigserial PRIMARY KEY,
                categorie    varchar(24) NOT NULL DEFAULT 'idee',   -- bug | idee | autre
                texte        text NOT NULL,
                contexte     varchar(160),                          -- vue/URL d'où vient le retour
                compte_mode  varchar(16),                           -- pilote | compte
                statut       varchar(24) NOT NULL DEFAULT 'nouveau',
                created_at   timestamptz NOT NULL DEFAULT now()
            )"""))
        c.execute(_t("CREATE INDEX IF NOT EXISTS ix_suggestions_statut "
                     "ON suggestions (statut, created_at)"))


def ensure_promesses_index(engine) -> None:
    """Index PARTIEL pour le NOT EXISTS « déjà bâti » de /promesses (Promesses mortes).
    `create_all` ne l'ajoute PAS (il saute les index d'une table déjà existante) → ensure explicite.
    Sans lui, le filtre layer/result se fait sur le tas (~3,6 s) ; avec, probe pur (~0,6 s). Idempotent."""
    from sqlalchemy import text as _t

    with engine.begin() as c:
        c.execute(_t("CREATE INDEX IF NOT EXISTS ix_dryrun_cascade_bati_exclude "
                     "ON dryrun_cascade_results (run_label, parcel_id) "
                     "WHERE layer_name = 'bati' AND result = 'HARD_EXCLUDE'"))


def ensure_parcel_flags(engine) -> None:
    """M45 (P2) — la table `parcel_flags` (vigilances dénormalisées, run-scopée) est MATÉRIALISÉE
    par le geste de bascule (`labuse build-mvt` → build_parcel_flags_table, avec garde de cohérence).
    Ici on garantit seulement son EXISTENCE (schéma) pour que le filtre `flags` ne casse jamais sur
    une base neuve/de test : vide tant que build-mvt n'a pas tourné (le filtre renvoie 0, pas d'erreur).
    Idempotent."""
    from sqlalchemy import text as _t

    with engine.begin() as c:
        c.execute(_t("CREATE TABLE IF NOT EXISTS parcel_flags "
                     "(run_label varchar(48), parcel_id integer, layer_name varchar(48))"))
        c.execute(_t("CREATE INDEX IF NOT EXISTS parcel_flags_probe "
                     "ON parcel_flags (run_label, layer_name, parcel_id)"))


def ensure_flags_probe_index(engine) -> None:
    """M45 (P1) — index PARTIEL pour le filtre `flags`/`flags_exclus` (vigilances par type).
    Sans lui, l'EXISTS sur dryrun_cascade_results seq-scanne 9,7 M lignes (~4-9 s île entière) ;
    avec, probe indexé (compteur sous la barre). `create_all` saute les index d'une table déjà
    existante → ensure explicite. Idempotent."""
    from sqlalchemy import text as _t

    with engine.begin() as c:
        c.execute(_t("CREATE INDEX IF NOT EXISTS ix_dryrun_cascade_flag_probe "
                     "ON dryrun_cascade_results (run_label, layer_name, parcel_id) "
                     "WHERE result IN ('SOFT_FLAG', 'UNKNOWN')"))


def ensure_pipeline_projet(engine) -> None:
    """Colonne `projet_id` sur pipeline_entries (copilote-projet) — la piste porte la
    référence du projet d'où elle vient. Idempotent, durable au rebuild sur base existante."""
    from sqlalchemy import text as _t

    with engine.begin() as c:
        c.execute(_t("ALTER TABLE pipeline_entries "
                     "ADD COLUMN IF NOT EXISTS projet_id integer "
                     "REFERENCES projets(id) ON DELETE SET NULL"))


def ensure_pipeline_prospection(engine) -> None:
    """Colonne `prospection` (jsonb) sur pipeline_entries — module prospection manuel.
    Idempotent ; ADD COLUMN IF NOT EXISTS → durable au rebuild sur base existante."""
    from sqlalchemy import text as _t

    with engine.begin() as c:
        c.execute(_t("ALTER TABLE pipeline_entries "
                     "ADD COLUMN IF NOT EXISTS prospection jsonb NOT NULL DEFAULT '{}'::jsonb"))


def ensure_pipeline_archived(engine) -> None:
    """M137 — colonne `archived_at` sur pipeline_entries (archivage réversible, plus de DELETE dur).
    Idempotent ; ADD COLUMN IF NOT EXISTS → durable au rebuild sur base existante."""
    from sqlalchemy import text as _t

    with engine.begin() as c:
        c.execute(_t("ALTER TABLE pipeline_entries ADD COLUMN IF NOT EXISTS archived_at timestamptz"))
        c.execute(_t("CREATE INDEX IF NOT EXISTS ix_pipeline_archived ON pipeline_entries (archived_at)"))


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
    # Boot SANS verrou (M6.1 ops) : quand colonnes ET triggers sont déjà en place, on ne
    # rejoue AUCUN DDL sur parcels/spatial_layers — un ALTER « IF NOT EXISTS » ou un
    # DROP/CREATE TRIGGER même no-op prend un verrou ACCESS EXCLUSIVE et, pendant un run
    # cascade ou un build, met en FILE toutes les lectures derrière lui (prod gelée sur
    # /parcels — vécu 3 fois pendant M6). Le chemin nominal (schéma déjà posé) ne prend
    # plus aucun verrou exclusif ; le chemin réparation reste identique. ⚠ Si la fonction
    # trigger labuse_set_geom_2975 doit évoluer un jour : DROP TRIGGER au préalable pour
    # repasser par le chemin de pose complet.
    with engine.connect() as _c:
        schema_pose = bool(_c.execute(_t(
            """SELECT (SELECT count(*) FROM information_schema.columns
                       WHERE table_name IN ('parcels', 'spatial_layers')
                         AND column_name = 'geom_2975') = 2
                  AND (SELECT count(*) FROM pg_trigger
                       WHERE tgname IN ('trg_parcels_geom_2975', 'trg_layers_geom_2975')
                         AND NOT tgisinternal) = 2""")).scalar())
    ddl = [] if schema_pose else [
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
        # Index GIST PARTIEL voirie : la cascade calcule la distance à la voirie la plus proche
        # (proxy d'accès/enclavement) via un KNN « ORDER BY geom_2975 <-> p.geom_2975 LIMIT 1 »
        # filtré sur kind='voirie'. Sans index dédié, le KNN parcourt l'index complet (dont les
        # ~84 000 bâtiments à Saint-Paul complet) en rejetant les non-voirie → recalcul cascade de
        # plusieurs heures (mesuré LOT 2). Le prédicat est EXACTEMENT « kind='voirie' » (PAS de
        # « AND geom_2975 IS NOT NULL » : la requête ne garantissant pas cette condition, le planner
        # ne pourrait pas matcher l'index partiel et retomberait sur l'index complet).
        "CREATE INDEX IF NOT EXISTS idx_spatial_layers_voirie_geom2975 ON spatial_layers USING gist (geom_2975) WHERE kind = 'voirie'",
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
        # MANDAT HYPOTHÈSES BILAN (décision Vic 28/07/2026) — purge du coût GLOBAL « estimé »
        # 2100 du 14/06 (ancré sur la fourchette YAML périmée d'avant-audit O2, cf.
        # RAPPORT_CALIBRATION_WEB.md « MISE À JOUR 28/07/2026 »). CIBLÉE : la valeur exacte du
        # socle système, provenance « estimee », secteur global — un override saisi/sourcé par
        # Vic (autre valeur, autre provenance ou autre secteur) survit. Le coût vient désormais
        # de la source unique (fourchette YAML auditée, repli cout=0 dans compute_bilan).
        c.execute(_t(
            "DELETE FROM bilan_params WHERE secteur = '*' AND param = 'cout_construction_m2_sdp' "
            "AND provenance = 'estimee' AND value = 2100"))
        # MANDAT CALIBRATION ESTIMÉES (décision Vic 28/07/2026) — purge du SOCLE global « prix de
        # sortie neuf » 4900 (prix saint-paulois servi à toute l'île, back-test contre le réel).
        # CIBLÉE : valeur exacte 4900, provenance « sourcee », secteur global — un override saisi
        # par Vic (autre valeur/provenance/secteur) et les overrides de bassin (secteur ≠ '*')
        # survivent. Sans cette purge, `seed()` le ré-injecterait au boot (piège exact du 2100).
        # Le prix vient désormais de `dvf_prix_sortie_neuf` (résolution par commune, préséance).
        c.execute(_t(
            "DELETE FROM bilan_params WHERE secteur = '*' AND param = 'prix_m2_neuf' "
            "AND provenance = 'sourcee' AND value = 4900"))
        # MANDAT PRIX SORTIE CONSOMMATEURS (décision Vic 28/07/2026) — DÉMOTION des overrides de
        # BASSIN « prix de sortie neuf » : ils viennent d'un OBSERVATOIRE de l'EXISTANT (calibration
        # web 14/06, famille du 2100), jamais confirmés par DVF neuf → ne peuvent primer sur la
        # médiane communale DVF. Passés en `estimee` (is_placeholder=true) → hors préséance
        # (`resolve_prix_neuf_marche` n'honore que `sourcee`). CIBLÉE aux valeurs SYSTÈME
        # (provenance='sourcee') : un override de bassin re-saisi par Vic (provenance NULL) survit.
        c.execute(_t(
            "UPDATE bilan_params SET provenance = 'estimee', is_placeholder = true, updated_at = now() "
            "WHERE param = 'prix_m2_neuf' AND provenance = 'sourcee' "
            "AND secteur IN ('Saint-Gilles','La Saline','Plateau Caillou','La Plaine-Bois de Nèfles','Le Guillaume')"))
        # Décision Vic 28/07/2026 : une valeur ESTIMÉE non confirmée reste placeholder (visible
        # aux bandeaux) — aligne l'existant, idempotent.
        c.execute(_t(
            "UPDATE bilan_params SET is_placeholder = (provenance = 'estimee') "
            "WHERE is_placeholder IS DISTINCT FROM (provenance = 'estimee')"))
        # Décision Vic 28/07/2026 (mandat calibration estimées §3) — purge des paramètres MORTS :
        # `ratio_vendable` (doublon inactif de `coef_rendement` YAML) et `bonus_vue_mer_pct`
        # (jamais au registre) n'étaient lus par AUCUN moteur ; leurs curseurs laissaient croire
        # qu'ils calibraient le modèle. Retirés du registre et du seed ; purge idempotente.
        c.execute(_t(
            "DELETE FROM bilan_params WHERE param IN ('ratio_vendable', 'bonus_vue_mer_pct')"))


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


def ensure_bodacc_view(engine) -> None:
    """Vue `v_foncier_sous_pression` (Vague A1) : croisement SIREN entre les procédures
    collectives BODACC et les parcelles détenues par une personne morale. Une ligne par
    parcelle (idu), la procédure la PLUS RÉCENTE. Signal INTERNE de priorisation (RGPD,
    règle d'archi #2) — calculable/interrogeable.

    # TODO étage 2 : à brancher au scoring « accessibilité du deal » quand les 3 sources de
    la Vague A seront en base. Cette session INGÈRE la donnée, ne touche PAS au score.

    Vue reconstruite (CREATE OR REPLACE) sans échouer si les tables sont vides ; suppose
    bodacc_procedures (ORM) et parcelle_personne_morale (ensure_personnes_morales) déjà créées."""
    from sqlalchemy import text as _t

    with engine.begin() as c:
        c.execute(_t(
            "CREATE OR REPLACE VIEW v_foncier_sous_pression AS "
            "SELECT DISTINCT ON (pm.idu) "
            "  pm.idu, pm.siren, pm.denomination, "
            "  b.type_procedure, b.date_annonce, b.tribunal, b.url_source, "
            "  'BODACC'::text AS source "
            "FROM parcelle_personne_morale pm "
            # SIREN normalisé des deux côtés : bodacc_procedures.siren est déjà 9 chiffres nus,
            # mais parcelle_personne_morale.siren peut arriver formaté (espaces) selon la source.
            # Un join brut sous-compterait alors silencieusement les parcelles BODACC.
            "JOIN bodacc_procedures b ON b.siren = regexp_replace(pm.siren, '[^0-9]', '', 'g') "
            "ORDER BY pm.idu, b.date_annonce DESC NULLS LAST"))


def ensure_pm_propension_view(engine) -> None:
    """Vues du signal « propension à vendre » (Vague A3 — INPI RNE, âge dirigeant).

    `v_pm_propension_vendre` (grain SIREN) : agrège pm_dirigeants → âge de l'AÎNÉ des dirigeants
    PHYSIQUES (un décideur vieillissant = horizon de transmission), effectifs, provenance et
    bande de propension. L'âge est recalculé À LA REQUÊTE (age(date de naissance)) → jamais
    périmé. `age_source` : 'direct' (au moins un individu daté) | 'aucun_individu' (dirigeants
    tous personnes morales / non datés → mesure du taux gigogne, cf. brief) | 'sans_dirigeant'.

    `v_foncier_propension_vendre` (grain PARCELLE, mirroir de v_foncier_sous_pression) : croise
    par SIREN normalisé avec parcelle_personne_morale.

    Signal INTERNE de priorisation (RGPD, règle d'archi #2), calculable/interrogeable.
    # TODO étage 2 : à brancher au scoring « accessibilité » quand les sources A seront là.
    NE touche PAS au score dans cette session. Reconstruit sans échouer si les tables sont vides."""
    from sqlalchemy import text as _t

    # Bandes de propension (l'étage 2 posera sa propre courbe ; on stocke aussi l'âge brut).
    # S'applique à l'âge retenu = âge DIRECT sinon âge résolu par gigogne (depth-1).
    band = ("CASE WHEN age_max_dirigeant IS NULL THEN NULL "
            "     WHEN age_max_dirigeant >= 75 THEN 'tres_eleve' "
            "     WHEN age_max_dirigeant >= 65 THEN 'eleve' "
            "     WHEN age_max_dirigeant >= 55 THEN 'modere' "
            "     ELSE 'faible' END")

    with engine.begin() as c:
        c.execute(_t(
            "CREATE OR REPLACE VIEW v_pm_propension_vendre AS "
            # depth-0 : dirigeants DIRECTS (pm_dirigeants)
            "WITH direct AS ("
            "  SELECT d.siren, "
            "    count(*) AS nb_dirigeants, "
            "    count(*) FILTER (WHERE d.type_personne = 'INDIVIDU') AS nb_individus, "
            # âge = plancher en années depuis 'YYYY-MM' (jour inconnu → 1er du mois) ; l'AÎNÉ = max
            "    max(date_part('year', age(to_date(d.date_naissance, 'YYYY-MM')))::int) "
            "      FILTER (WHERE d.type_personne = 'INDIVIDU' AND d.date_naissance IS NOT NULL) "
            "      AS age_direct "
            "  FROM pm_dirigeants d GROUP BY d.siren"
            "), "
            # depth-1 : dirigeants physiques du gérant-société (pm_dirigeant_gigogne), fallback
            "gigogne AS ("
            "  SELECT g.siren, "
            "    max(date_part('year', age(to_date(g.date_naissance, 'YYYY-MM')))::int) AS age_gigogne "
            "  FROM pm_dirigeant_gigogne g WHERE g.date_naissance IS NOT NULL GROUP BY g.siren"
            ") "
            "SELECT direct.siren, direct.nb_dirigeants, direct.nb_individus, "
            "  COALESCE(direct.age_direct, gigogne.age_gigogne) AS age_max_dirigeant, "
            f"  {band.replace('age_max_dirigeant', 'COALESCE(direct.age_direct, gigogne.age_gigogne)')}"
            "     AS propension_band, "
            "  CASE WHEN direct.age_direct IS NOT NULL THEN 'direct' "
            "       WHEN gigogne.age_gigogne IS NOT NULL THEN 'gerant_societe' "
            "       WHEN direct.nb_dirigeants = 0 THEN 'sans_dirigeant' "
            "       ELSE 'aucun_individu' END AS age_source "
            "FROM direct LEFT JOIN gigogne ON gigogne.siren = direct.siren"))

        c.execute(_t(
            "CREATE OR REPLACE VIEW v_foncier_propension_vendre AS "
            "SELECT DISTINCT ON (pm.idu) "
            "  pm.idu, sig.siren, pm.denomination, "
            "  sig.age_max_dirigeant, sig.propension_band, sig.age_source, "
            "  sig.nb_dirigeants, sig.nb_individus "
            "FROM parcelle_personne_morale pm "
            "JOIN v_pm_propension_vendre sig "
            "  ON sig.siren = regexp_replace(pm.siren, '[^0-9]', '', 'g') "
            "ORDER BY pm.idu, sig.age_max_dirigeant DESC NULLS LAST"))


def ensure_passoire_thermique_view(engine) -> None:
    """Vue `v_passoire_thermique` (Vague C2 — DPE ADEME) : signal « passoire thermique » par parcelle.

    Une parcelle est signalée si elle porte AU MOINS un DPE de MAISON individuelle classé F ou G
    et RÉCENT (< 5 ans) — le propriétaire fait face à un mur réglementaire daté (voir ci-dessous),
    signal de propension à vendre pour l'étage 2.

    ⚖️ Calendrier réglementaire DOM (source unique : score_v_constants.DPE_DOM_INTERDICTION_LOCATION,
       loi Climat & Résilience, application outre-mer différée) :
      - gel des loyers des logements F et G depuis le 01/07/2024 ;
      - interdiction de LOUER les G au 01/01/2028 ;
      - interdiction de louer les F au 01/01/2031 (calendrier DOM — PAS 2034, qui est la métropole).
    (En DROM le DPE n'est obligatoire que depuis le 01/07/2024 → base jeune, signal « positif
    quand présent », jamais exhaustif.)

    # TODO étage 2 : à brancher au score « propension à vendre » quand les sources seront prêtes.
    NE touche PAS au score dans cette session. Une ligne par parcelle (la pire étiquette, la plus
    récente). Reconstruite sans échouer si la table est vide."""
    from sqlalchemy import text as _t

    with engine.begin() as c:
        c.execute(_t(
            "CREATE OR REPLACE VIEW v_passoire_thermique AS "
            "SELECT DISTINCT ON (d.parcelle_idu) "
            "  d.parcelle_idu AS idu, d.code_insee, d.etiquette_dpe, d.type_batiment, "
            "  d.surface_habitable, d.date_etablissement, d.rattachement "
            "FROM dpe_records d "
            "WHERE d.parcelle_idu IS NOT NULL "
            "  AND d.type_batiment = 'maison' "
            "  AND d.etiquette_dpe IN ('F', 'G') "
            "  AND d.date_etablissement >= (CURRENT_DATE - INTERVAL '5 years') "
            "ORDER BY d.parcelle_idu, d.etiquette_dpe DESC, d.date_etablissement DESC"))


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
        # M-K (P1-9) : `compte_id` porté par watch_zones ET alertes (fresh installs via le
        # CREATE ; bases en place via l'ALTER plus bas). La cloison (FK cascade + index compte)
        # est posée par api/tenant.ensure_scoping — watch_zones/alertes ∈ SCOPED_TABLES.
        c.execute(_t(
            "CREATE TABLE IF NOT EXISTS watch_zones ("
            " id serial PRIMARY KEY, name varchar(120) NOT NULL, commune varchar(64) NOT NULL,"
            " compte_id integer,"
            " geom geometry(Polygon, 4326) NOT NULL,"
            " created_at timestamptz NOT NULL DEFAULT now(), last_run_at timestamptz)"))
        c.execute(_t("CREATE INDEX IF NOT EXISTS idx_watch_zones_geom ON watch_zones USING gist (geom)"))
        c.execute(_t("CREATE INDEX IF NOT EXISTS ix_watch_zones_commune ON watch_zones (commune)"))
        c.execute(_t(
            "CREATE TABLE IF NOT EXISTS alertes ("
            " id serial PRIMARY KEY, kind varchar(32) NOT NULL,"
            " zone_id integer REFERENCES watch_zones(id) ON DELETE CASCADE,"
            " parcel_id integer REFERENCES parcels(id) ON DELETE CASCADE,"
            " compte_id integer,"
            " source_ref varchar(64) NOT NULL, label text NOT NULL, payload jsonb,"
            " acknowledged boolean NOT NULL DEFAULT false,"
            " detected_at timestamptz NOT NULL DEFAULT now())"))
        # ALTER idempotent : les bases créées avant M-K n'ont pas la colonne (CREATE IF NOT
        # EXISTS ne la rajoute pas sur une table existante).
        c.execute(_t("ALTER TABLE watch_zones ADD COLUMN IF NOT EXISTS compte_id integer"))
        c.execute(_t("ALTER TABLE alertes ADD COLUMN IF NOT EXISTS compte_id integer"))
        # dvf_in_zone : la dédup par (zone_id, source_ref) est DÉJÀ cloisonnée — une zone
        # appartient à un seul compte, donc son zone_id ne fuit pas entre comptes.
        c.execute(_t("CREATE UNIQUE INDEX IF NOT EXISTS uq_alertes_zone_dvf "
                     "ON alertes (zone_id, source_ref) WHERE kind = 'dvf_in_zone'"))
        # permit_near_followed : la dédup DOIT inclure compte_id. Deux comptes suivant la MÊME
        # parcelle doivent chacun recevoir l'alerte ; l'ancienne clé (parcel_id, source_ref)
        # faisait manger l'alerte du 2e compte par ON CONFLICT DO NOTHING.
        c.execute(_t("DROP INDEX IF EXISTS uq_alertes_parcel_permit"))
        c.execute(_t("CREATE UNIQUE INDEX IF NOT EXISTS uq_alertes_compte_parcel_permit "
                     "ON alertes (compte_id, parcel_id, source_ref) WHERE kind = 'permit_near_followed'"))


def ensure_derived_read_stubs(engine) -> None:
    """FIX-C6 (GB-049 étendu) — tables DÉRIVÉES construites par l'ingestion/scoring mais LUES
    par des endpoints : créées VIDES au heal pour qu'une base neuve rende des états vides
    propres au lieu d'un 500 `UndefinedTable`. Le vrai build les remplace/remplit ensuite.
      · parcel_zone_plu (~20 lecteurs : patrimoine, marché, filtres, accueil, alertes…) — le
        builder `tiles.build_parcel_zone_plu` fait DROP+CREATE AS ; le déclencheur build-mvt a
        été ajusté pour reconstruire si la table est ABSENTE OU VIDE (le stub n'inhibe rien).
      · entonnoir_motifs (/stats/entonnoir) — repeuplée par run via CREATE IF NOT EXISTS+DELETE.
    Idempotent (`IF NOT EXISTS`)."""
    from sqlalchemy import text as _t

    from .db import sql_statements
    # DDL CANONIQUES réutilisées telles quelles (zéro dérive de schéma vs l'ingestion)
    from .ingestion.ban_adresses import DDL_ADRESSES as _ADRESSES_DDL
    from .ingestion.dvf_prix_neuf import DDL as _DVF_NEUF_DDL
    from .ingestion.ortho_equipements import DDL as _EQUIP_DDL

    with engine.begin() as c:
        c.execute(_t("CREATE TABLE IF NOT EXISTS parcel_zone_plu ("
                     " idu varchar, zone_lib varchar, zone_fam varchar,"
                     " zone_libelle text, zone_filtre varchar)"))
        c.execute(_t("CREATE TABLE IF NOT EXISTS entonnoir_motifs ("
                     " run_label text, commune text, ord int, motif text, n bigint,"
                     " PRIMARY KEY (run_label, commune, motif))"))
        # mvt_meta (KV de version des tuiles) — schéma identique à tiles.build_mvt_table ;
        # `_mvt_version` la lit avant la garde mvt_parcels → 500 sans elle sur base neuve.
        c.execute(_t("CREATE TABLE IF NOT EXISTS mvt_meta"
                     " (key varchar(48) PRIMARY KEY, value varchar(64), updated_at timestamptz)"))
        # contexte-commune (SRU + conso ENAF/ZAN) — pas de DDL en code (chargées par script) :
        # stubs au schéma réel pour /communes/{c}/contexte, /comparateur-communes, /projets/reperes,
        # /moteurs/zan.
        c.execute(_t("CREATE TABLE IF NOT EXISTS commune_contexte_sru ("
                     " insee varchar, commune text, millesime text, taux_lls numeric,"
                     " objectif_pct numeric, statut text, prelevement_eur numeric, detail jsonb,"
                     " source_nom text, source_url text, importe_le timestamptz)"))
        c.execute(_t("CREATE TABLE IF NOT EXISTS commune_conso_enaf ("
                     " insee varchar, commune varchar, conso_2011_2021_m2 double precision,"
                     " conso_2021_2024_m2 double precision, hab_2011_2021_m2 double precision,"
                     " hab_2021_2024_m2 double precision, source_nom text, source_url text,"
                     " millesime varchar, importe_le timestamptz)"))
        # commune_insee_logement (contexte-commune INSEE) — /communes/{c}/contexte.
        c.execute(_t("CREATE TABLE IF NOT EXISTS commune_insee_logement ("
                     " insee varchar, commune text, millesime text, logements integer,"
                     " res_principales integer, res_secondaires integer, vacants integer,"
                     " proprietaires_pct numeric, locataires_pct numeric, maisons_pct numeric,"
                     " apparts_pct numeric, typologie jsonb, source_nom text, source_url text,"
                     " importe_le timestamptz)"))
        # p_model_bati (emprise bâtie BD TOPO) — /modules/prospection-piscines ; le builder
        # scoring/p_model/sql.py fait DROP+CREATE, le stub est remplacé sans dommage.
        c.execute(_t("CREATE TABLE IF NOT EXISTS p_model_bati"
                     " (idu varchar PRIMARY KEY, emprise_bati_m2 float)"))
        # parcel_terrain (pente/terrassement) — /ortho/equipements ; construit par l'ingestion.
        c.execute(_t("CREATE TABLE IF NOT EXISTS parcel_terrain ("
                     " idu varchar, pente_moy_deg real, pente_max_deg real,"
                     " flag_terrassement_lourd boolean, computed_at timestamptz,"
                     " pente_non_batie_deg real, motif_absence text)"))
        # anru_quartiers + plh_epci (contexte-commune ANRU/PLH) — /communes/{c}/contexte.
        c.execute(_t("CREATE TABLE IF NOT EXISTS anru_quartiers ("
                     " id integer, commune text, insee varchar, nom text, interet text,"
                     " code_qpv text, source_nom text, source_url text, importe_le timestamptz)"))
        c.execute(_t("CREATE TABLE IF NOT EXISTS plh_epci ("
                     " epci text, periode text, statut text, obj_logements_an integer,"
                     " part_sociale_pct numeric, detail jsonb, refs jsonb, importe_le timestamptz)"))
        # DDL canoniques des ingesters (CREATE IF NOT EXISTS → no-op quand déjà là) :
        #   adresses (BAN, /adresses/autocomplete — lue en source, non buildée paresseusement) ;
        #   dvf_prix_sortie_neuf (/moteurs/barometre) ; parcel_equipements (/ortho/equipements).
        for _ddl in (_ADRESSES_DDL, _DVF_NEUF_DDL, _EQUIP_DDL):
            for stmt in sql_statements(_ddl):
                if stmt.strip():
                    c.execute(_t(stmt))


def ensure_watch_snap_no_orphans(engine) -> None:
    """FIX-C6 (GB-063) — MIGRATION idempotente + garde durable de `watch_zone_zonage_snap`.

    La photo zonage (idu×zone pour la détection de changement) était créée SANS FK vers
    watch_zones (contrairement à `alertes` qui a ON DELETE CASCADE) → ses lignes fuyaient à
    chaque suppression de veille (3 330 orphelins au cycle 6). On (1) purge les orphelins
    existants, puis (2) pose la FK ON DELETE CASCADE manquante — la base garantit désormais
    le nettoyage même si un appelant l'oublie. Idempotent : ne fait rien si la table n'existe
    pas encore (créée paresseusement à la détection) ou si la FK est déjà là."""
    from sqlalchemy import text as _t

    with engine.begin() as c:
        if not c.execute(_t("SELECT to_regclass('watch_zone_zonage_snap')")).scalar():
            return  # table pas encore matérialisée (aucune détection n'a tourné) — rien à faire
        # (1) purge des orphelins accumulés (zone supprimée sans purge du snap)
        c.execute(_t("DELETE FROM watch_zone_zonage_snap s"
                     " WHERE NOT EXISTS (SELECT 1 FROM watch_zones w WHERE w.id = s.zone_id)"))
        # (2) FK ON DELETE CASCADE si absente (après la purge, toutes les zone_id sont valides)
        has_fk = c.execute(_t(
            "SELECT 1 FROM pg_constraint"
            " WHERE conrelid = 'watch_zone_zonage_snap'::regclass AND contype = 'f'")).first()
        if not has_fk:
            c.execute(_t(
                "ALTER TABLE watch_zone_zonage_snap"
                " ADD CONSTRAINT fk_snap_zone FOREIGN KEY (zone_id)"
                " REFERENCES watch_zones(id) ON DELETE CASCADE"))


def ensure_residuel_cache(engine) -> None:
    """Cache du potentiel résiduel (Lot B) — alimente le filtre « sous-densité » sans
    relancer la faisabilité par parcelle à chaque chargement de carte. Idempotent.

    M135 — le schéma de versionnement (`parcel_residuel_runs` + `residuel_runs`) est
    toujours assuré. Si `parcel_residuel` est déjà une VUE (migration M135 faite), on
    n'y touche pas (un `ALTER` sur une vue casserait). Sinon (pré-migration / base
    fraîche), on garde la table de base historique — la migration vue est explicite
    (`residuel-migrate`)."""
    from sqlalchemy import text as _t

    from .faisabilite.residuel_runs import ensure_runs_schema

    with engine.begin() as c:
        ensure_runs_schema(c)
        if c.execute(_t("SELECT relkind FROM pg_class WHERE relname='parcel_residuel'")).scalar() == "v":
            return  # M135 : déjà migré en vue — rien à faire sur la vue
        c.execute(_t(
            "CREATE TABLE IF NOT EXISTS parcel_residuel ("
            " parcel_id integer PRIMARY KEY REFERENCES parcels(id) ON DELETE CASCADE,"
            " taux_emprise_pct integer, pct_potentiel integer, sous_densite boolean,"
            " sdp_residuelle_m2 integer, capacite_estimee boolean,"
            " computed_at timestamptz NOT NULL DEFAULT now())"))
        # Migration des bases existantes (table déjà créée sans la colonne).
        c.execute(_t("ALTER TABLE parcel_residuel ADD COLUMN IF NOT EXISTS capacite_estimee boolean"))
        # M125 — la CAUSE du non-calculé (arbitrage Vic, Option 1) : NULL = ligne CALCULÉE
        # (constructible, valeurs pleines) ; sinon le code structuré du refus
        # (zone_non_constructible:<zone> / terrain_exigu / redhibitoire / zone_non_resolue:<lib> /
        # hors_plu / capacite_nulle / habitat_interdit:<zone> / hauteur_indispo). Les LECTEURS
        # VIVANTS (filtres carte, fiche, flash) ne lisent QUE cause IS NULL — comportement servi
        # inchangé ; les lignes à cause n'existent que pour le dataset M127 et le run M128.
        c.execute(_t("ALTER TABLE parcel_residuel ADD COLUMN IF NOT EXISTS cause text"))


def ensure_spatial_layers_sub(engine, force: bool = False) -> int:
    """Cache PRÉ-SUBDIVISÉ des couches spatiales (pièces ≤256 sommets + GiST) — évite de
    re-subdiviser les mêmes couches PPR/aléa à CHAQUE lot de cascade (ST_Subdivide = 95 % du coût
    de EvalContext.prime ; ×64 mesuré, coverage strictement identique). Dérivé de la géométrie
    STATIQUE de spatial_layers : reconstruire (`force=True`) si les couches changent. `prime`
    utilise cette table si présente, sinon repli sur le découpage à la volée (comportement inchangé).
    Idempotent : ne reconstruit que si absente ou `force`."""
    from sqlalchemy import text as _t

    with engine.begin() as c:
        if not force and c.execute(_t("SELECT to_regclass('spatial_layers_sub') IS NOT NULL")).scalar():
            return int(c.execute(_t("SELECT count(*) FROM spatial_layers_sub")).scalar())
        c.execute(_t("DROP TABLE IF EXISTS spatial_layers_sub"))
        c.execute(_t(
            "CREATE TABLE spatial_layers_sub AS "
            " SELECT id AS lid, kind, subtype, name, attrs, data_source_id, ST_Subdivide(geom_2975,256) AS g "
            "   FROM spatial_layers WHERE kind<>'batiment' AND ST_Dimension(geom_2975)=2 "
            " UNION ALL "
            " SELECT id, kind, subtype, name, attrs, data_source_id, geom_2975 "
            "   FROM spatial_layers WHERE kind<>'batiment' AND ST_Dimension(geom_2975)<2"))
        c.execute(_t("CREATE INDEX idx_sls_geom ON spatial_layers_sub USING gist (g)"))
        c.execute(_t("ANALYZE spatial_layers_sub"))
        return int(c.execute(_t("SELECT count(*) FROM spatial_layers_sub")).scalar())


def ensure_constructibilite_cache(engine) -> None:
    """Cache du verdict de constructibilité (déclassement étage 0) — évite de relancer la
    faisabilité par parcelle au scoring. `label` : declasse_zone_fermee (A) / declasse_non_
    constructible (B) / non_verifiable (C) ; NULL = constructible. `motif` = phrase produit.
    Idempotent. Rafraîchi par `labuse compute-constructibilite`."""
    from sqlalchemy import text as _t

    with engine.begin() as c:
        c.execute(_t(
            "CREATE TABLE IF NOT EXISTS parcel_constructibilite ("
            " parcel_id integer PRIMARY KEY REFERENCES parcels(id) ON DELETE CASCADE,"
            " label varchar(32), motif text, cause varchar(24),"
            " computed_at timestamptz NOT NULL DEFAULT now())"))
        # Élargissement des colonnes qui reçoivent le TIER : le déclassement ajoute
        # `declasse_non_constructible` (26 car.) qui débordait varchar(24) (bascule 29/07).
        # ALTER TYPE d'agrandissement = métadonnée-only en Postgres (instantané, pas de réécriture).
        c.execute(_t("ALTER TABLE parcel_p_score_v2 ALTER COLUMN tier TYPE varchar(32)"))
        c.execute(_t("ALTER TABLE score_snapshot_parcelles ALTER COLUMN statut TYPE varchar(32)"))


def ensure_au_statut_cache(engine) -> None:
    """Cache du statut d'OUVERTURE des zones AU (mandat AU-OUVERTURE, Vic 30/07). Marque les
    parcelles en zone AU dont l'article d'ouverture (Art. 1/2) n'a JAMAIS été lu.

    `classe` (modèle AFFINÉ GPU-PILOTE, Vic 30/07) : `declasse_au_fermee` (AU fermée → déclassée),
    `declasse_au_statut_inconnu` (phasage 2AU→1AU / legacy 'générique' → déclassée),
    `conditionnelle_operation` (servie, mention seule) ou `au_sous_plancher` (servie, candidate à
    l'assemblage). `zone_lib` : libellé de zone servi (ex. '2AUd', 'AUm'). `computed_at` :
    HORODATAGE DE POSE — un déclassement temporaire sans date devient permanent par oubli ; le
    compteur de péremption (`labuse au-statut-compteur`) lit cette colonne. Idempotent.
    Peuplé par `labuse compute-au-statut`."""
    from sqlalchemy import text as _t

    with engine.begin() as c:
        c.execute(_t(
            "CREATE TABLE IF NOT EXISTS parcel_au_statut ("
            " parcel_id integer PRIMARY KEY REFERENCES parcels(id) ON DELETE CASCADE,"
            " idu varchar(20), classe varchar(40) NOT NULL, zone_lib varchar(64),"
            " motif text, computed_at timestamptz NOT NULL DEFAULT now())"))
        # AFFINÉ GPU-PILOTE : les libellés de statut se sont allongés (declasse_au_statut_inconnu = 26,
        # conditionnelle_operation = 24) — élargir une table déjà créée en varchar(20). Idempotent.
        c.execute(_t("ALTER TABLE parcel_au_statut ALTER COLUMN classe TYPE varchar(40)"))


def ensure_schema(engine) -> None:
    """Réconciliation LÉGÈRE et idempotente du schéma (boot / doctor / prepare-pilot).

    Garantit : tables ORM, colonnes critiques (geom_2975, prospection), fonction+triggers,
    index GIST (dont l'index fonctionnel DVF) et table de cache enrichment — en SECONDES.
    NE fait JAMAIS : backfill massif, téléchargement, ré-évaluation. Si des DONNÉES
    manquent (geom_2975 NULL, couches absentes), c'est /readyz et `labuse doctor` qui le
    disent, et `rebuild-demo` qui reconstruit."""
    # FIX-C6 (GB-047) — amorçage d'un Postgres NU : les tables ORM portent des colonnes
    # `geometry`, donc PostGIS doit exister AVANT `create_all` (sinon `type "geometry" does
    # not exist`). Les chemins CLI (api/doctor/prepare-pilot) l'appelaient déjà séparément ;
    # le boot uvicorn ne passait QUE par ici → base neuve non amorçable hors docker. En le
    # posant DANS ensure_schema (import local = pas de cycle), tous les chemins convergent.
    from .db import ensure_postgis
    ensure_postgis(engine)
    Base.metadata.create_all(engine)
    _ensure_schema_steps(engine, geom_backfill=False)


def ensure_data_sources_millesime(engine) -> None:
    """M32 Phase B §2 (spec millésime amont) — 4 colonnes de fraîcheur AMONT sur data_sources,
    renseignées par les ingesters. `ADD COLUMN IF NOT EXISTS` → durable au rebuild, idempotent."""
    with engine.begin() as c:
        c.execute(text("ALTER TABLE data_sources ADD COLUMN IF NOT EXISTS source_millesime varchar(64)"))
        c.execute(text("ALTER TABLE data_sources ADD COLUMN IF NOT EXISTS source_horizon_at date"))
        c.execute(text("ALTER TABLE data_sources ADD COLUMN IF NOT EXISTS source_cadence varchar(32)"))
        c.execute(text("ALTER TABLE data_sources ADD COLUMN IF NOT EXISTS prochain_millesime_at date"))
        # CRON-2 — statut de fraîcheur servi aux badges (posé par le job sources-fraicheur ; ici aussi
        # pour que le schéma soit complet dès le heal, pas seulement au 1er passage du job).
        c.execute(text("ALTER TABLE data_sources ADD COLUMN IF NOT EXISTS fraicheur_statut varchar(16)"))
        c.execute(text("ALTER TABLE data_sources ADD COLUMN IF NOT EXISTS fraicheur_calcule_at timestamptz"))
        # CONNEXIONS-2 Lot 6.2 (KO-14) — date + motif du dernier échec d'ingestion (état « en erreur »).
        c.execute(text("ALTER TABLE data_sources ADD COLUMN IF NOT EXISTS fraicheur_erreur_at timestamptz"))
        c.execute(text("ALTER TABLE data_sources ADD COLUMN IF NOT EXISTS fraicheur_erreur_message text"))
        # CONNEXIONS-2 Lot 6.3 (M2) — flag « désactivée au dashboard » (remplace SOURCES_MASQUEES en dur).
        c.execute(text("ALTER TABLE data_sources ADD COLUMN IF NOT EXISTS affichage_desactive "
                       "boolean NOT NULL DEFAULT false"))


def ensure_source_veille(engine) -> None:
    """SENTINELLE-1 (W1) — table de veille amont `source_veille` + peuplement initial (W5). Idempotent
    (CREATE IF NOT EXISTS + ensemencement non destructif). La sentinelle n'écrit JAMAIS dans data_sources ;
    tout son état vit ici."""
    with engine.begin() as c:
        c.execute(text("""
            CREATE TABLE IF NOT EXISTS source_veille (
                id                 serial PRIMARY KEY,
                source_id          integer NOT NULL UNIQUE REFERENCES data_sources(id) ON DELETE CASCADE,
                url_version        text,
                methode            varchar(8),
                selecteur          text,
                cadence_heures     integer NOT NULL DEFAULT 24,
                dernier_passage_at timestamptz,
                dernier_vu         varchar(64),
                dernier_statut     varchar(16),
                dernier_message    text,
                dernier_entete     text,
                actif              boolean NOT NULL DEFAULT true,
                created_at         timestamptz NOT NULL DEFAULT now(),
                updated_at         timestamptz NOT NULL DEFAULT now()
            )"""))
        c.execute(text("CREATE INDEX IF NOT EXISTS ix_source_veille_source ON source_veille (source_id)"))
        # SENTINELLE-2 (X5) — colonnes de mémoire de notification, ajoutées idempotemment aux bases
        # SENTINELLE-1 existantes (ADD COLUMN IF NOT EXISTS ; jamais destructif).
        c.execute(text("ALTER TABLE source_veille ADD COLUMN IF NOT EXISTS dernier_notifie_vu varchar(64)"))
        c.execute(text("ALTER TABLE source_veille ADD COLUMN IF NOT EXISTS "
                       "echecs_consecutifs integer NOT NULL DEFAULT 0"))
        # SENTINELLE-2 (X6) — trace de l'injection supervisée (déclenchée à la main par Vic).
        c.execute(text("ALTER TABLE source_veille ADD COLUMN IF NOT EXISTS injection_lancee_at timestamptz"))
        c.execute(text("ALTER TABLE source_veille ADD COLUMN IF NOT EXISTS injection_vu varchar(64)"))
    # peuplement : dans une session (rattachement par nom aux sources en base), idempotent.
    from .db import session_scope
    from . import sentinelle
    try:
        with session_scope() as s:
            sentinelle.ensemencer(s)
            s.commit()
    except Exception:  # noqa: BLE001 — un souci de seed ne doit JAMAIS bloquer le boot (table déjà créée)
        pass


def ensure_data_sources_status_norm(engine) -> None:
    """FIX-SOURCES S2 — NORMALISE le statut des sources vers la valeur d'enum (minuscule), de façon
    REPRODUCTIBLE en prod (idempotent, non destructif) — jamais un UPDATE manuel local. Un statut
    mal casé ('CONNECTE' au lieu de 'connecte', posé par un ingester bavard) sortait la source de la
    vitrine ET de son comptage (cas CoSIA). Ici on ne touche QUE la casse (lower) quand la valeur
    minuscule est un statut d'enum valide — aucune valeur inventée, aucune ligne réécrite à tort.
    La garde `sources_catalog.normalize_status` empêche la RÉ-introduction côté ingestion."""
    with engine.begin() as c:
        normalize_data_sources_status(c)


def normalize_data_sources_status(conn) -> int:
    """Corps SQL de la normalisation (isolé pour être testable sur une connexion/session). Ne touche
    QUE la casse (lower) quand la minuscule est un statut d'enum valide. Renvoie le nb de lignes réparées."""
    from .enums import DataSourceStatus

    valides = [m.value for m in DataSourceStatus]
    return conn.execute(
        text("UPDATE data_sources SET status = lower(status) "
             "WHERE status <> lower(status) AND lower(status) = ANY(:ok)"),
        {"ok": valides}).rowcount


def ensure_zone_filtre(engine) -> None:
    """M99 (arbitrage Vic) — clé normalisée du filtre zonage sur la table dérivée
    `parcel_zone_plu` : `zone_filtre = upper(zone_lib)` (graphie réglementaire MAJUSCULE —
    coexistence intra-commune nulle, règlement jamais en casse mixte, AUDIT_M99_ZONAGE.md).
    Idempotent ; le builder (tiles.build_parcel_zone_plu) l'écrit désormais nativement, cette
    migration couvre la table déjà matérialisée sans rebuild spatial (~20-40 min évitées).
    `zone_lib` d'origine n'est JAMAIS écrasé."""
    with engine.begin() as c:
        if not c.execute(text("SELECT to_regclass('parcel_zone_plu') IS NOT NULL")).scalar():
            return                       # table dérivée pas encore matérialisée — le builder l'écrira
        c.execute(text("ALTER TABLE parcel_zone_plu ADD COLUMN IF NOT EXISTS zone_filtre varchar"))
        c.execute(text("UPDATE parcel_zone_plu SET zone_filtre = upper(zone_lib) "
                       "WHERE zone_filtre IS DISTINCT FROM upper(zone_lib)"))
        c.execute(text("CREATE INDEX IF NOT EXISTS idx_pzp_zone_filtre "
                       "ON parcel_zone_plu (zone_filtre)"))


def ensure_dvf_marche(engine) -> None:
    """Vue v_parcel_dvf_last + table dvf_secteur_medianes (LOT 1 data-gap) — idempotent."""
    from sqlalchemy import text as _t

    from .ingestion.dvf_marche import DDL_MEDIANES, ensure_dvf_views
    ensure_dvf_views(engine)
    with engine.begin() as c:
        c.execute(_t(DDL_MEDIANES.text))


def ensure_score_v_view(engine) -> None:
    """ALGO-1 item 3 — la vue legacy `v_parcelles_brulantes` est SUPPRIMÉE (drop idempotent).

    Elle portait la DEUXIÈME définition de « brûlante » (chaude Q×A ∧ v_score ≥ 17, v1.3) :
    112 lignes vs 120 au tier v2 servi — deux vérités en base pour le même mot
    (SCORING_SPEC §7-C), et le Score V est mesuré contre-prédictif pour la mutation
    (RR@1158 = 0,51, §7-D). LA seule définition servie est le tier `brulante` de
    `parcel_p_score_v2`. Le DROP est rejoué à chaque boot (mêmes points d'appel que
    l'ancienne création) : la vue disparaît aussi en prod au prochain déploiement.
    Rollback : git revert de ce commit (la définition complète est dans l'historique)."""
    from sqlalchemy import text as _t

    with engine.begin() as c:
        c.execute(_t("DROP VIEW IF EXISTS v_parcelles_brulantes"))


def ensure_parcel_origine(engine) -> None:
    """Colonne `origine` sur parcels (Lot A — audit pull). Idempotent."""
    from sqlalchemy import text as _t

    with engine.begin() as c:
        c.execute(_t("ALTER TABLE parcels ADD COLUMN IF NOT EXISTS origine varchar(16)"))


def drop_all(engine) -> None:
    Base.metadata.drop_all(engine)
