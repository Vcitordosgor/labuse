"""Ingestion DPE ADEME (Vague C2) → table `dpe_records`  [data pure].

Un DPE par logement (dédup `numero_dpe`). Rattachement parcelle APPROXIMATIF : re-géocodage BAN
(le `_geopoint` ADEME est faux au 974) puis `ST_Contains` sur `parcels` → `rattachement='geocode'`.
Signal `passoire_thermique` (maison F/G récente) exposé par la vue v_passoire_thermique.

La donnée d'abord, le scoring ensuite : ce module PEUPLE `dpe_records` ; le signal est branché
PLUS TARD (# TODO étage 2). Représentativité : biens diagnostiqués depuis 2021 (DPE obligatoire en
DROM depuis le 01/07/2024) — « positif quand présent », jamais exhaustif.
"""
from __future__ import annotations

import json
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
        "code_insee": rec.get("code_insee_ban"),
        "code_postal": rec.get("code_postal_ban"),
        "date_etablissement": _to_date(rec.get("date_etablissement_dpe")),
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


def _parcelle_at(session: Session, commune: str, lon: float, lat: float) -> str | None:
    """IDU de la parcelle contenant le point (dans la commune). None si aucune."""
    return session.execute(text(
        "SELECT idu FROM parcels WHERE commune = :c "
        "AND ST_Contains(geom, ST_SetSRID(ST_Point(:lon,:lat),4326)) LIMIT 1"),
        {"c": commune, "lon": lon, "lat": lat}).scalar()


def ingest_commune(session: Session, insee: str, commune: str,
                   connector: DpeConnector | None = None) -> dict:
    """Ingère les DPE d'une commune dans `dpe_records` (géocodage BAN + rattachement parcelle).

    Idempotent (upsert sur `numero_dpe`). ⚠ ÉCRIT + APPELS RÉSEAU (data-fair + BAN/logement).
    Retourne des compteurs. Ne touche PAS au score (# TODO étage 2).
    """
    connector = connector or DpeConnector()
    n = n_geo = n_rat = 0
    for rec in connector.fetch_commune(insee):
        p = parse_record(rec)
        if not p:
            continue
        lon = lat = score = idu = None
        rattachement = "aucun"
        geo = connector.geocode(p["adresse"], insee)
        if geo:
            lon, lat, score = geo
            n_geo += 1
            idu = _parcelle_at(session, commune, lon, lat)
            if idu:
                rattachement = "geocode"
                n_rat += 1
        session.execute(_UPSERT, {
            "num": p["numero_dpe"], "ed": p["etiquette_dpe"], "eg": p["etiquette_ges"],
            "tb": p["type_batiment"], "surf": p["surface_habitable"], "ac": p["annee_construction"],
            "adr": p["adresse"], "ci": p["code_insee"], "cp": p["code_postal"],
            "de": p["date_etablissement"], "lon": lon, "lat": lat, "sc": score,
            "idu": idu, "rat": rattachement, "raw": json.dumps(rec, ensure_ascii=False)})
        n += 1
    _touch_source(session)
    session.flush()
    return {"dpe": n, "geocodes": n_geo, "rattaches_parcelle": n_rat}


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
