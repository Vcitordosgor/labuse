"""Ingestion DPE ADEME (Vague C2, complétée Wave copro-data) → table `dpe_records`  [data pure].

Un DPE par logement (dédup `numero_dpe`). Rattachement parcelle 100 % LOCAL (mandat 11/07 :
« géocodage = table adresses locale », plus aucun appel api-adresse), en cascade :
  1. `identifiant_ban` ADEME → `adresses.id_ban` (IDU déjà rattaché par ban_adresses)  → 'ban_locale'
  2. point BAN natif EPSG:2975 (`coordonnee_cartographique_x/y_ban`) → ST_Contains     → 'point_ban'
  3. `adresse_brut` normalisée (numéro + voie) → `adresses` de la commune              → 'adresse_locale'
  4. sinon 'aucun' (un « aucun » honnête vaut mieux qu'un rattachement faux).

Gisement réel : ~912 DPE pour toute l'île (11/07/2026) — le DPE réglementaire reste marginal
en DROM (~10/mois depuis 07/2021). Signal « positif quand présent », JAMAIS exhaustif.
La donnée d'abord, le scoring ensuite : ce module PEUPLE `dpe_records` ; le signal est branché
par le Score V (famille E) et la vue v_passoire_thermique.
"""
from __future__ import annotations

import json
import re
import unicodedata
from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..connectors.dpe import DpeConnector

SOURCE_NAME = "DPE ADEME (logements existants)"


def _to_int(v) -> int | None:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def _to_float(v) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _to_date(v) -> date | None:
    try:
        return date.fromisoformat(str(v)[:10])
    except (TypeError, ValueError):
        return None


def parse_record(rec: dict) -> dict | None:
    """Enregistrement /lines → dict DPE normalisé. None si pas de `numero_dpe` (dédup impossible)."""
    numero = rec.get("numero_dpe")
    if not numero:
        return None
    return {
        "numero_dpe": str(numero),
        "etiquette_dpe": rec.get("etiquette_dpe"),
        "etiquette_ges": rec.get("etiquette_ges"),
        "type_batiment": rec.get("type_batiment"),
        "surface_habitable": _to_float(rec.get("surface_habitable_logement")),
        "annee_construction": _to_int(rec.get("annee_construction")),
        "adresse": rec.get("adresse_ban") or rec.get("adresse_brut"),
        "adresse_brut": rec.get("adresse_brut"),
        "code_insee": rec.get("code_insee_ban"),
        "code_postal": rec.get("code_postal_ban") or rec.get("code_postal_brut"),
        "date_etablissement": _to_date(rec.get("date_etablissement_dpe")),
        "id_ban": rec.get("identifiant_ban"),
        "score_ban": _to_float(rec.get("score_ban")),
        "x_ban": _to_float(rec.get("coordonnee_cartographique_x_ban")),
        "y_ban": _to_float(rec.get("coordonnee_cartographique_y_ban")),
    }


_UPSERT = text(
    "INSERT INTO dpe_records "
    " (numero_dpe, etiquette_dpe, etiquette_ges, type_batiment, surface_habitable, "
    "  annee_construction, adresse, code_insee, code_postal, date_etablissement, "
    "  lon, lat, geocode_score, parcelle_idu, rattachement, raw) "
    "VALUES (:num,:ed,:eg,:tb,:surf,:ac,:adr,:ci,:cp,:de,:lon,:lat,:sc,:idu,:rat, CAST(:raw AS jsonb)) "
    "ON CONFLICT (numero_dpe) DO UPDATE SET "
    "  etiquette_dpe=EXCLUDED.etiquette_dpe, etiquette_ges=EXCLUDED.etiquette_ges, "
    "  type_batiment=EXCLUDED.type_batiment, surface_habitable=EXCLUDED.surface_habitable, "
    "  annee_construction=EXCLUDED.annee_construction, adresse=EXCLUDED.adresse, "
    "  code_insee=EXCLUDED.code_insee, code_postal=EXCLUDED.code_postal, "
    "  date_etablissement=EXCLUDED.date_etablissement, lon=EXCLUDED.lon, lat=EXCLUDED.lat, "
    "  geocode_score=EXCLUDED.geocode_score, parcelle_idu=EXCLUDED.parcelle_idu, "
    "  rattachement=EXCLUDED.rattachement, raw=EXCLUDED.raw, ingested_at=now()")


# ───────────────────────── géocodage local (table `adresses`) ─────────────────────────

def _norm(s: str | None) -> str:
    """Normalisation adresse : minuscules, sans accents, ponctuation → espace, espaces réduits."""
    if not s:
        return ""
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


# « 12 bis rue des Lilas 97440 Saint-André » → numero='12', voie='rue des lilas' (coupe au CP 974xx).
_RE_BRUT = re.compile(r"^(?:(\d{1,5})\s*(?:bis|ter|quater|[a-z])?\s+)?(.+?)(?:\s+974\d\d\b.*)?$")


def _parse_brut(adresse: str | None) -> tuple[str | None, str] | None:
    m = _RE_BRUT.match(_norm(adresse))
    if not m or not m.group(2):
        return None
    return m.group(1), m.group(2)


def _index_adresses(session: Session, insee: str) -> dict:
    """Index (numero, voie) normalisés → liste (idu, lon, lat) des adresses rattachées de la commune."""
    idx: dict[tuple[str, str], list] = {}
    rows = session.execute(text(
        "SELECT numero, voie, idu, ST_X(geom), ST_Y(geom) FROM adresses "
        "WHERE insee = :i AND idu IS NOT NULL"), {"i": insee})
    for numero, voie, idu, lon, lat in rows:
        idx.setdefault((_norm(numero), _norm(voie)), []).append((idu, lon, lat))
    return idx


def _parcelle_at_2975(session: Session, x: float, y: float) -> tuple | None:
    """(idu, lon, lat) de la parcelle contenant le point BAN natif EPSG:2975. None si aucune."""
    return session.execute(text(
        "SELECT idu, ST_X(pt), ST_Y(pt) FROM parcels, LATERAL ("
        "  SELECT ST_Transform(ST_SetSRID(ST_Point(:x,:y),2975),4326) AS pt) q "
        "WHERE ST_Contains(geom_2975, ST_SetSRID(ST_Point(:x,:y),2975)) LIMIT 1"),
        {"x": x, "y": y}).first()


def _rattacher(session: Session, p: dict, idx_adresses: dict) -> dict:
    """Cascade locale id_ban → point BAN → adresse brute. Retourne lon/lat/score/idu/rattachement."""
    out = {"lon": None, "lat": None, "sc": p["score_ban"], "idu": None, "rat": "aucun"}
    # 1. clé BAN → table adresses (IDU déjà rattaché en 3 passes par ban_adresses)
    if p["id_ban"]:
        row = session.execute(text(
            "SELECT idu, ST_X(geom), ST_Y(geom) FROM adresses WHERE id_ban = :b AND idu IS NOT NULL"),
            {"b": p["id_ban"]}).first()
        if row:
            out.update(idu=row[0], lon=row[1], lat=row[2], rat="ban_locale")
            return out
    # 2. point BAN natif 2975 (aussi les identifiants niveau voie, absents de `adresses`)
    if p["x_ban"] and p["y_ban"]:
        row = _parcelle_at_2975(session, p["x_ban"], p["y_ban"])
        if row:
            out.update(idu=row[0], lon=row[1], lat=row[2], rat="point_ban")
            return out
    # 3. adresse brute normalisée contre les adresses de la commune (numéro + voie exacts,
    #    accepté seulement si toutes les candidates pointent la MÊME parcelle — pas de pari)
    parsed = _parse_brut(p["adresse_brut"] or p["adresse"])
    if parsed:
        cands = idx_adresses.get((parsed[0] or "", parsed[1]), [])
        if cands and len({c[0] for c in cands}) == 1:
            out.update(idu=cands[0][0], lon=cands[0][1], lat=cands[0][2], rat="adresse_locale")
    return out


# ───────────────────────── ingestion ─────────────────────────

def _upsert(session: Session, rec: dict, p: dict, geo: dict) -> None:
    session.execute(_UPSERT, {
        "num": p["numero_dpe"], "ed": p["etiquette_dpe"], "eg": p["etiquette_ges"],
        "tb": p["type_batiment"], "surf": p["surface_habitable"], "ac": p["annee_construction"],
        "adr": p["adresse"], "ci": p["code_insee"], "cp": p["code_postal"],
        "de": p["date_etablissement"], "lon": geo["lon"], "lat": geo["lat"], "sc": geo["sc"],
        "idu": geo["idu"], "rat": geo["rat"], "raw": json.dumps(rec, ensure_ascii=False)})


def ingest_commune(session: Session, insee: str, commune: str,
                   connector: DpeConnector | None = None) -> dict:
    """Ingère les DPE d'une commune dans `dpe_records` (rattachement 100 % local, cf. module).

    Idempotent (upsert sur `numero_dpe`). ⚠ ÉCRIT + APPELS RÉSEAU (data-fair uniquement).
    Retourne des compteurs. Ne touche PAS au score (recalcul Score V séparé).
    """
    connector = connector or DpeConnector()
    idx_adresses: dict | None = None
    n = n_geo = n_rat = 0
    for rec in connector.fetch_commune(insee):
        p = parse_record(rec)
        if not p:
            continue
        if idx_adresses is None:
            idx_adresses = _index_adresses(session, insee)
        geo = _rattacher(session, p, idx_adresses)
        n_geo += 1 if geo["lon"] is not None else 0
        n_rat += 1 if geo["idu"] else 0
        _upsert(session, rec, p, geo)
        n += 1
    _touch_source(session)
    session.flush()
    return {"dpe": n, "geocodes": n_geo, "rattaches_parcelle": n_rat}


def ingest_orphelins(session: Session, connector: DpeConnector | None = None) -> dict:
    """DPE réunionnais SANS géocodage BAN (CP brut 974xx) — invisibles du filtre commune.

    La commune est déduite du CP brut via `adresses` ; le rattachement retombe sur la passe 3
    (adresse brute). code_insee reste NULL si le CP couvre plusieurs communes sans match adresse.
    """
    connector = connector or DpeConnector()
    n = n_rat = 0
    for rec in connector.fetch_orphelins_974():
        p = parse_record(rec)
        if not p:
            continue
        geo = {"lon": None, "lat": None, "sc": None, "idu": None, "rat": "aucun"}
        insees = [r[0] for r in session.execute(text(
            "SELECT DISTINCT insee FROM adresses WHERE code_postal = :cp"),
            {"cp": p["code_postal"]}).all()] if p["code_postal"] else []
        for insee in insees:
            geo = _rattacher(session, p, _index_adresses(session, insee))
            if geo["idu"]:
                p["code_insee"] = insee
                break
        if p["code_insee"] is None and len(insees) == 1:
            p["code_insee"] = insees[0]
        n_rat += 1 if geo["idu"] else 0
        _upsert(session, rec, p, geo)
        n += 1
    session.flush()
    return {"dpe": n, "rattaches_parcelle": n_rat}


def sample_report(session: Session, insee: str) -> dict:
    """Rapport (commune) depuis dpe_records DÉJÀ ingérée — sans réseau."""
    etiq = {r[0]: r[1] for r in session.execute(text(
        "SELECT etiquette_dpe, count(*) FROM dpe_records WHERE code_insee=:c GROUP BY 1 ORDER BY 1"),
        {"c": insee}).all()}
    total = int(session.execute(text("SELECT count(*) FROM dpe_records WHERE code_insee=:c"),
                                {"c": insee}).scalar() or 0)
    maisons_fg = int(session.execute(text(
        "SELECT count(*) FROM dpe_records WHERE code_insee=:c AND type_batiment='maison' "
        "AND etiquette_dpe IN ('F','G')"), {"c": insee}).scalar() or 0)
    parcelles = int(session.execute(text(
        "SELECT count(DISTINCT parcelle_idu) FROM dpe_records WHERE code_insee=:c "
        "AND parcelle_idu IS NOT NULL"), {"c": insee}).scalar() or 0)
    passoires_parc = int(session.execute(text(
        "SELECT count(*) FROM v_passoire_thermique WHERE code_insee=:c"), {"c": insee}).scalar() or 0)
    ex = [dict(r) for r in session.execute(text(
        "SELECT etiquette_dpe, adresse, surface_habitable, date_etablissement, parcelle_idu "
        "FROM dpe_records WHERE code_insee=:c AND type_batiment='maison' "
        "AND etiquette_dpe IN ('F','G') AND parcelle_idu IS NOT NULL "
        "ORDER BY date_etablissement DESC LIMIT 5"), {"c": insee}).mappings().all()]
    return {"insee": insee, "dpe": total, "distribution_etiquette": etiq,
            "maisons_fg": maisons_fg, "parcelles_rattachees": parcelles,
            "parcelles_passoire": passoires_parc, "exemples": ex}


def _touch_source(session: Session) -> None:
    session.execute(
        text("UPDATE data_sources SET last_sync_at = now() WHERE name = :n"), {"n": SOURCE_NAME})
