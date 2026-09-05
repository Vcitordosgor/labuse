"""CIRCUIT-3 lot 1.1/1.2 — LE CADRE DES FILTRES.

Un réservoir = un filtre = une liste de contrôles joués sur UNE version de la source.
Vocabulaire (mandat CIRCUIT-3) :
  - filtre        : l'ensemble des contrôles joués sur une version d'un réservoir.
  - bloquant      : un KO empêche de servir (met la version en QUARANTAINE).
  - avertissant   : un KO s'affiche mais ne bloque pas.
  - quarantaine   : la version est ingérée, mesurée, PAS servie.

Règle d'or (mandat) : « aucun seuil bloquant sans mesure qui le fonde ». Un seuil que CC ne
sait pas fixer est posé en `avertissant` avec la valeur observée, jamais en `bloquant` inventé :
un filtre trop sévère qui bloque une source saine est pire qu'un filtre qui avertit.

Le cadre porte les CONTRÔLES UNIVERSELS (lot 1.2) hérités par tout filtre sans rien écrire :
présence des 24 communes, non-vide, couloir de lignes ±30 %, doublon sur la clé, géométries
valides et dans l'emprise, dates plausibles, millésime déclaré. Un filtre n'active un universel
que si sa configuration le permet (pas de colonne géométrie → pas de contrôle géométrie).
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Callable

from sqlalchemy import text

from ..ingestion.run_all import REUNION_COMMUNES

log = logging.getLogger("labuse.filtres")

# Les 24 codes INSEE officiels de La Réunion (référentiel embarqué, source unique).
INSEE_24 = tuple(insee for insee, _ in REUNION_COMMUNES)

# Emprise de La Réunion en WGS84 (lon/lat) — enveloppe large, sert au contrôle « dans l'emprise ».
REUNION_BBOX_4326 = (55.0, -21.45, 55.95, -20.8)  # (lon_min, lat_min, lon_max, lat_max)

NATURES = ("completude", "referentiel", "rattachement", "plage",
           "doublon", "geometrie", "distribution", "echantillon")
SEVERITES = ("bloquant", "avertissant")

DDL = """
CREATE TABLE IF NOT EXISTS filtre_resultats (
  id bigserial PRIMARY KEY,
  source     varchar(64)  NOT NULL,
  version    varchar(128) NOT NULL,
  controle   varchar(64)  NOT NULL,
  nature     varchar(16)  NOT NULL,
  severite   varchar(12)  NOT NULL,
  valeur     text,
  seuil      text,
  verdict    varchar(8)   NOT NULL,   -- ok | ko | skip
  details_json jsonb,
  joue_le    timestamptz  NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_filtre_resultats_sv ON filtre_resultats (source, version, joue_le DESC);
CREATE TABLE IF NOT EXISTS filtre_versions (
  id bigserial PRIMARY KEY,
  source        varchar(64)  NOT NULL,
  version       varchar(128) NOT NULL,
  verdict       varchar(16)  NOT NULL,   -- ok | quarantaine | avertissements
  bloquants_ko  integer NOT NULL DEFAULT 0,
  avertissants_ko integer NOT NULL DEFAULT 0,
  servir_quand_meme boolean NOT NULL DEFAULT false,  -- geste de Vic (lot 4/5)
  servi_par     varchar(120),
  servi_motif   text,
  joue_le       timestamptz  NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_filtre_versions_sv ON filtre_versions (source, version, joue_le DESC);
"""


def ensure_tables(engine) -> None:
    """Idempotent — branchée dans models._ensure_schema_steps (boot)."""
    with engine.begin() as c:
        for stmt in DDL.split(";"):
            if stmt.strip():
                c.execute(text(stmt))


def _ensure_sur_session(db) -> None:
    """Crée les tables via la connexion de la session (déjà en transaction — pas de begin())."""
    for stmt in DDL.split(";"):
        if stmt.strip():
            db.execute(text(stmt))


# ─────────────────────────────── résultat d'un contrôle ───────────────────────────────

@dataclass
class Resultat:
    """Le fruit d'un `mesure()` : la valeur observée, le verdict, des détails pour la page."""
    valeur: str
    verdict: str  # ok | ko | skip
    details: dict = field(default_factory=dict)


def ok(valeur, details=None) -> Resultat:
    return Resultat(str(valeur), "ok", details or {})


def ko(valeur, details=None) -> Resultat:
    return Resultat(str(valeur), "ko", details or {})


def skip(motif: str, details=None) -> Resultat:
    d = {"motif": motif}
    if details:
        d.update(details)
    return Resultat("—", "skip", d)


# ─────────────────────────────── contrôle & filtre ───────────────────────────────

@dataclass
class Controle:
    id: str
    nature: str
    severite: str
    libelle: str
    seuil: str          # écrit AVEC la mesure qui l'a fixé (fait, pas opinion)
    mesure: Callable[["Session", "Filtre", str], Resultat]  # (db, filtre, version) -> Resultat

    def __post_init__(self):
        assert self.nature in NATURES, f"nature inconnue: {self.nature}"
        assert self.severite in SEVERITES, f"sévérité inconnue: {self.severite}"


@dataclass
class Filtre:
    """Un filtre par source. Les universels sont ajoutés automatiquement à `controles_effectifs()`
    selon la configuration (insee/cle/geom/dates)."""
    source: str                       # clé du filtre (= label de la vanne quand il existe)
    libelle: str
    table: str | None = None          # table servie principale (pour les universels)
    cle: tuple[str, ...] = ()          # colonnes de la clé déclarée (doublon)
    insee_col: str | None = None      # colonne code INSEE (présence des 24 communes)
    geom_col: str | None = None       # colonne géométrie (validité + emprise)
    geom_srid: int = 4326             # SRID de la géométrie (transformée en 4326 pour l'emprise)
    date_cols: tuple[str, ...] = ()    # colonnes de date (plage plausible)
    source_motif: str | None = None   # motif SQL ILIKE sur data_sources.name (version/millésime)
    portee_run: bool = False          # alimente au moins une donnée à portée `run` (garde pompe)
    live: bool = False                # alimente au moins une donnée à portée `live` (quarantaine)
    propres: list[Controle] = field(default_factory=list)  # contrôles propres (lot 2)
    a_job: bool = True                # source à job d'ingestion (test 1.5)
    note: str | None = None           # note de contexte (raison d'un skip structurel, etc.)

    def controles_effectifs(self) -> list[Controle]:
        """Universels applicables (selon config) + propres, dans un ordre stable."""
        return universels_pour(self) + list(self.propres)


# ─────────────────────────────── version servie ───────────────────────────────

def version_servie(db, filtre: "Filtre") -> str:
    """L'étiquette de la version courante d'une source (rule 2 : le filtre se joue sur une VERSION).

    Priorité : source_millesime > last_sync_at (date) > 'courante'. Lue depuis data_sources par
    le motif du filtre ; sans motif, 'courante' (la source n'a pas de ligne data_sources dédiée)."""
    if filtre.source_motif:
        row = db.execute(text(
            "SELECT source_millesime, last_sync_at FROM data_sources "
            "WHERE name ILIKE :m ORDER BY id LIMIT 1"), {"m": filtre.source_motif}).first()
        if row:
            mill, sync = row
            if mill and str(mill).strip():
                return str(mill).strip()[:128]
            if sync:
                return f"sync {sync.date().isoformat()}"
    return "courante"


def _count(db, table: str, where: str = "") -> int:
    q = f"SELECT count(*) FROM {table}" + (f" WHERE {where}" if where else "")
    return int(db.execute(text(q)).scalar() or 0)


def _table_existe(db, table: str) -> bool:
    # table peut être « schema.name » ; on ne gère que public ici (regclass).
    return bool(db.execute(text("SELECT to_regclass(:t)"), {"t": table}).scalar())


def _lignes_version_precedente(db, source: str, version: str) -> int | None:
    """Le nombre de lignes enregistré au dernier passage d'une AUTRE version (couloir ±30 %)."""
    row = db.execute(text(
        "SELECT valeur FROM filtre_resultats "
        "WHERE source=:s AND controle='u_couloir_lignes' AND version<>:v AND verdict<>'skip' "
        "ORDER BY joue_le DESC LIMIT 1"), {"s": source, "v": version}).first()
    if row and row[0] is not None:
        try:
            return int(str(row[0]).replace(" ", ""))
        except ValueError:
            return None
    return None


# ─────────────────────────────── contrôles universels ───────────────────────────────

def _u_communes(db, f: Filtre, version: str) -> Resultat:
    if not (f.table and f.insee_col and _table_existe(db, f.table)):
        return skip("pas de colonne INSEE ou table absente")
    rows = db.execute(text(
        f"SELECT DISTINCT {f.insee_col} FROM {f.table} "
        f"WHERE {f.insee_col} IS NOT NULL")).scalars().all()
    presents = {str(r).strip()[:5] for r in rows}
    manquantes = [i for i in INSEE_24 if i not in presents]
    d = {"presentes": len(INSEE_24) - len(manquantes), "attendues": 24, "manquantes": manquantes}
    return ok(f"{24 - len(manquantes)}/24", d) if not manquantes else ko(f"{24 - len(manquantes)}/24", d)


def _u_non_vide(db, f: Filtre, version: str) -> Resultat:
    if not (f.table and _table_existe(db, f.table)):
        return skip("table absente")
    n = _count(db, f.table)
    return ok(n, {"lignes": n}) if n > 0 else ko(0, {"lignes": 0})


def _u_couloir_lignes(db, f: Filtre, version: str) -> Resultat:
    if not (f.table and _table_existe(db, f.table)):
        return skip("table absente")
    n = _count(db, f.table)
    prec = _lignes_version_precedente(db, f.source, version)
    if prec is None or prec == 0:
        # première version mesurée : on POSE la référence, on n'accuse pas.
        return ok(n, {"lignes": n, "reference": None, "note": "première version mesurée"})
    bas, haut = int(prec * 0.7), int(prec * 1.3)
    d = {"lignes": n, "reference": prec, "couloir": [bas, haut]}
    return ok(n, d) if bas <= n <= haut else ko(n, d)


def _u_doublon_cle(db, f: Filtre, version: str) -> Resultat:
    if not (f.table and f.cle and _table_existe(db, f.table)):
        return skip("pas de clé déclarée ou table absente")
    cols = ", ".join(f.cle)
    dup = int(db.execute(text(
        f"SELECT count(*) FROM (SELECT {cols} FROM {f.table} "
        f"GROUP BY {cols} HAVING count(*) > 1) t")).scalar() or 0)
    d = {"cle": list(f.cle), "clés_dupliquées": dup}
    return ok(0, d) if dup == 0 else ko(dup, d)


def _u_geom_valide(db, f: Filtre, version: str) -> Resultat:
    if not (f.table and f.geom_col and _table_existe(db, f.table)):
        return skip("pas de géométrie ou table absente")
    invalides = int(db.execute(text(
        f"SELECT count(*) FROM {f.table} "
        f"WHERE {f.geom_col} IS NOT NULL AND NOT ST_IsValid({f.geom_col})")).scalar() or 0)
    d = {"invalides": invalides}
    return ok(0, d) if invalides == 0 else ko(invalides, d)


def _u_geom_emprise(db, f: Filtre, version: str) -> Resultat:
    if not (f.table and f.geom_col and _table_existe(db, f.table)):
        return skip("pas de géométrie ou table absente")
    lon0, lat0, lon1, lat1 = REUNION_BBOX_4326
    g = f.geom_col if f.geom_srid == 4326 else f"ST_Transform({f.geom_col}, 4326)"
    hors = int(db.execute(text(
        f"SELECT count(*) FROM {f.table} WHERE {f.geom_col} IS NOT NULL "
        f"AND NOT ST_Intersects({g}, ST_MakeEnvelope(:a,:b,:c,:d,4326))"),
        {"a": lon0, "b": lat0, "c": lon1, "d": lat1}).scalar() or 0)
    d = {"hors_emprise": hors, "emprise": REUNION_BBOX_4326}
    return ok(0, d) if hors == 0 else ko(hors, d)


def _u_dates_plausibles(db, f: Filtre, version: str) -> Resultat:
    if not (f.table and f.date_cols and _table_existe(db, f.table)):
        return skip("pas de colonne date ou table absente")
    borne_haute = date.today().isoformat()
    total_hors = 0
    detail: dict[str, int] = {}
    for col in f.date_cols:
        n = int(db.execute(text(
            f"SELECT count(*) FROM {f.table} WHERE {col} IS NOT NULL AND "
            f"({col} < CAST('2000-01-01' AS date) OR {col} > CAST(:h AS date))"),
            {"h": borne_haute}).scalar() or 0)
        detail[col] = n
        total_hors += n
    d = {"hors_plage": total_hors, "par_colonne": detail, "plage": ["2000-01-01", borne_haute]}
    return ok(0, d) if total_hors == 0 else ko(total_hors, d)


def _u_millesime(db, f: Filtre, version: str) -> Resultat:
    declare = version != "courante"
    return ok(version, {"version": version}) if declare else ko(
        "non déclaré", {"version": version, "note": "ni source_millesime ni last_sync_at"})


_UNIVERSELS: list[tuple[Controle, Callable[[Filtre], bool]]] = [
    (Controle("u_communes", "referentiel", "avertissant", "Présence des 24 communes",
              "24/24 codes INSEE du référentiel embarqué", _u_communes),
     lambda f: bool(f.insee_col)),
    (Controle("u_non_vide", "completude", "bloquant", "Version non vide",
              "> 0 ligne (0 ligne = quarantaine)", _u_non_vide),
     lambda f: bool(f.table)),
    (Controle("u_couloir_lignes", "distribution", "avertissant", "Couloir de lignes ±30 %",
              "±30 % autour de la version précédente (référence posée au 1er passage)", _u_couloir_lignes),
     lambda f: bool(f.table)),
    (Controle("u_doublon_cle", "doublon", "avertissant", "Pas de doublon sur la clé",
              "0 clé dupliquée sur la clé déclarée", _u_doublon_cle),
     lambda f: bool(f.cle)),
    (Controle("u_geom_valide", "geometrie", "avertissant", "Géométries valides",
              "0 géométrie invalide (ST_IsValid)", _u_geom_valide),
     lambda f: bool(f.geom_col)),
    (Controle("u_geom_emprise", "geometrie", "avertissant", "Géométries dans l'emprise",
              "0 géométrie hors emprise Réunion (55.0..55.95 / -21.45..-20.8)", _u_geom_emprise),
     lambda f: bool(f.geom_col)),
    (Controle("u_dates_plausibles", "plage", "avertissant", "Dates plausibles",
              "aucune date < 2000-01-01 ni future", _u_dates_plausibles),
     lambda f: bool(f.date_cols)),
    (Controle("u_millesime", "completude", "avertissant", "Millésime déclaré",
              "source_millesime ou last_sync_at non nul", _u_millesime),
     lambda f: bool(f.source_motif)),
]


def universels_pour(f: Filtre) -> list[Controle]:
    return [c for c, applic in _UNIVERSELS if applic(f)]


# ─────────────────────────────── exécuteur ───────────────────────────────

@dataclass
class Verdict:
    source: str
    version: str
    verdict: str        # ok | avertissements | quarantaine
    bloquants_ko: int
    avertissants_ko: int
    resultats: list[dict]


def jouer(db, filtre: Filtre, version: str | None = None) -> Verdict:
    """Joue tous les contrôles d'un filtre sur la version courante (ou celle passée), écrit
    filtre_resultats + filtre_versions, retourne le verdict. Un contrôle qui LÈVE est un `ko`
    avertissant (il n'a pas su mesurer) — jamais un blocage silencieux."""
    _ensure_sur_session(db)
    version = version or version_servie(db, filtre)
    resultats: list[dict] = []
    bloquants_ko = avertissants_ko = 0
    # on efface les résultats du dernier passage de CETTE version (rejeu propre).
    db.execute(text("DELETE FROM filtre_resultats WHERE source=:s AND version=:v"),
               {"s": filtre.source, "v": version})
    for c in filtre.controles_effectifs():
        try:
            r = c.mesure(db, filtre, version)
        except Exception as exc:  # noqa: BLE001
            log.error("filtre %s / contrôle %s : %s", filtre.source, c.id, exc)
            r = Resultat("erreur", "ko", {"exception": f"{type(exc).__name__}: {exc}"})
        if r.verdict == "ko":
            if c.severite == "bloquant":
                bloquants_ko += 1
            else:
                avertissants_ko += 1
        db.execute(text(
            "INSERT INTO filtre_resultats "
            "(source, version, controle, nature, severite, valeur, seuil, verdict, details_json) "
            "VALUES (:s,:v,:c,:n,:se,:val,:seu,:ver,:d)"),
            {"s": filtre.source, "v": version, "c": c.id, "n": c.nature, "se": c.severite,
             "val": r.valeur, "seu": c.seuil, "ver": r.verdict,
             "d": json.dumps(r.details, ensure_ascii=False, default=str)})
        resultats.append({"controle": c.id, "nature": c.nature, "severite": c.severite,
                          "libelle": c.libelle, "seuil": c.seuil, "valeur": r.valeur,
                          "verdict": r.verdict, "details": r.details})
    verdict = "quarantaine" if bloquants_ko else ("avertissements" if avertissants_ko else "ok")
    db.execute(text(
        "INSERT INTO filtre_versions (source, version, verdict, bloquants_ko, avertissants_ko) "
        "VALUES (:s,:v,:ver,:b,:a)"),
        {"s": filtre.source, "v": version, "ver": verdict,
         "b": bloquants_ko, "a": avertissants_ko})
    return Verdict(filtre.source, version, verdict, bloquants_ko, avertissants_ko, resultats)


def dernier_verdict(db, source: str, version: str | None = None) -> dict | None:
    """Le dernier verdict enregistré pour une source (une version précise ou la plus récente).
    Tient compte d'un « servir quand même » posé après coup (lot 4/5)."""
    _ensure_sur_session(db)
    if version:
        row = db.execute(text(
            "SELECT source, version, verdict, bloquants_ko, avertissants_ko, "
            "servir_quand_meme, servi_par, servi_motif, joue_le "
            "FROM filtre_versions WHERE source=:s AND version=:v "
            "ORDER BY joue_le DESC LIMIT 1"), {"s": source, "v": version}).first()
    else:
        row = db.execute(text(
            "SELECT source, version, verdict, bloquants_ko, avertissants_ko, "
            "servir_quand_meme, servi_par, servi_motif, joue_le "
            "FROM filtre_versions WHERE source=:s ORDER BY joue_le DESC LIMIT 1"),
            {"s": source}).first()
    if not row:
        return None
    return {"source": row[0], "version": row[1], "verdict": row[2], "bloquants_ko": row[3],
            "avertissants_ko": row[4], "servir_quand_meme": row[5], "servi_par": row[6],
            "servi_motif": row[7], "joue_le": row[8].isoformat() if row[8] else None}


def en_quarantaine(db, source: str, version: str | None = None) -> bool:
    """VRAI si la version (servie) est en quarantaine ET que Vic n'a pas dit « servir quand même »."""
    v = dernier_verdict(db, source, version)
    if not v:
        return False
    return v["verdict"] == "quarantaine" and not v["servir_quand_meme"]
