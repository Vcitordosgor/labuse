"""LOT 10 (data-gap) — RNIC : Registre National d'Immatriculation des Copropriétés (ANAH).

Source : data.gouv.fr, fichier national CSV (~453 Mo, T3 2025 ; URL stable testée live
10/07/2026), **2 220 copropriétés au 974**. Champs vérifiés sur données réelles : jusqu'à
3 références cadastrales DÉJÀ AU FORMAT IDU 14 car. (`reference_cadastrale_n`), long/lat,
`nombre_total_de_lots`, `nombre_de_lots_a_usage_d_habitation`, `periode_de_construction`,
syndic (type, raison sociale, SIRET), mandat en cours.

Rattachement parcelle : référence cadastrale → `parcels.idu` (direct) ; fallback point
long/lat dans la parcelle. Cible marchands de biens : **pas de scoring** (mandat) — fiche
parcelle (bloc copro) + table interrogeable/filtrable.

CLI : labuse ingest-rnic --csv <chemin>   (le CSV national n'est pas conservé au repo)
"""
from __future__ import annotations

import csv
import json

from sqlalchemy import text
from sqlalchemy.orm import Session

SOURCE_NAME = "RNIC — copropriétés (ANAH)"
URL_STABLE = "https://www.data.gouv.fr/fr/datasets/r/132ed35f-db38-48d9-a31f-3dd7a0942cd9"

DDL = text("""
CREATE TABLE IF NOT EXISTS rnic_coproprietes (
  numero_immatriculation varchar(12) PRIMARY KEY,
  insee                  varchar(5),
  commune                varchar(64),
  nom_usage              text,
  adresse                text,
  nb_lots_total          integer,
  nb_lots_habitation     integer,
  periode_construction   varchar(24),
  syndic_type            varchar(16),
  syndic_nom             text,
  syndic_siret           varchar(14),
  mandat_en_cours        boolean,
  idu_codes              jsonb NOT NULL DEFAULT '[]',
  parcelle_idu           varchar(14),          -- rattachement (réf cadastrale, sinon point)
  rattachement           varchar(12),          -- cadastre | geocode | aucun
  geom                   geometry(Point, 4326),
  raw                    jsonb,
  ingested_at            timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_rnic_parcelle ON rnic_coproprietes (parcelle_idu);
CREATE INDEX IF NOT EXISTS ix_rnic_insee ON rnic_coproprietes (insee);
""")


def _int(v) -> int | None:
    try:
        return int(float(v)) if v not in (None, "") else None
    except (TypeError, ValueError):
        return None


def ingest_rnic(session: Session, csv_path: str, log=print) -> dict:
    """Filtre le CSV national sur le 974 et charge rnic_coproprietes (rebuild idempotent)."""
    for stmt in DDL.text.split(";"):
        if stmt.strip():
            session.execute(text(stmt))
    session.execute(text("TRUNCATE rnic_coproprietes"))
    n = 0
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("code_officiel_departement") != "974":
                continue
            idus = [row.get(f"reference_cadastrale_{i}") for i in (1, 2, 3)]
            idus = [i.strip() for i in idus if i and len(i.strip()) == 14]
            lon, lat = row.get("long"), row.get("lat")
            session.execute(text("""
                INSERT INTO rnic_coproprietes
                  (numero_immatriculation, insee, commune, nom_usage, adresse, nb_lots_total,
                   nb_lots_habitation, periode_construction, syndic_type, syndic_nom,
                   syndic_siret, mandat_en_cours, idu_codes, geom, raw)
                VALUES (:num, :insee, :com, :nom, :adr, :lots, :lots_hab, :periode,
                        :styp, :snom, :ssiret, :mandat, CAST(:idus AS jsonb),
                        CASE WHEN :lon <> '' AND :lat <> ''
                             THEN ST_SetSRID(ST_MakePoint(CAST(:lon AS float), CAST(:lat AS float)), 4326)
                        END,
                        CAST(:raw AS jsonb))
                ON CONFLICT (numero_immatriculation) DO NOTHING"""), {
                "num": row.get("numero_d_immatriculation"),
                "insee": row.get("code_officiel_commune"),
                "com": row.get("commune_adresse_de_reference") or row.get("nom_officiel_commune"),
                "nom": row.get("nom_d_usage_de_la_copropriete") or None,
                "adr": row.get("adresse_de_reference") or None,
                "lots": _int(row.get("nombre_total_de_lots")),
                "lots_hab": _int(row.get("nombre_de_lots_a_usage_d_habitation")),
                "periode": row.get("periode_de_construction") or None,
                "styp": (row.get("type_de_syndic_benevole_professionnel_non_connu") or "")[:16] or None,
                "snom": row.get("raison_sociale_du_representant_legal") or None,
                "ssiret": (row.get("siret_du_representant_legal") or "")[:14] or None,
                "mandat": (row.get("mandat_en_cours_dans_la_copropriete") or "").lower()
                          in ("oui", "true", "1"),
                "idus": json.dumps(idus), "lon": lon or "", "lat": lat or "",
                "raw": json.dumps({k: v for k, v in row.items() if v}, ensure_ascii=False)})
            n += 1
    # Rattachement parcelle : réf cadastrale directe, sinon point dans la parcelle.
    session.execute(text("""
        UPDATE rnic_coproprietes r SET parcelle_idu = sub.idu, rattachement = 'cadastre'
        FROM (SELECT r2.numero_immatriculation, min(p.idu) AS idu
              FROM rnic_coproprietes r2, jsonb_array_elements_text(r2.idu_codes) c(idu)
              JOIN parcels p ON p.idu = c.idu GROUP BY 1) sub
        WHERE sub.numero_immatriculation = r.numero_immatriculation"""))
    session.execute(text("""
        UPDATE rnic_coproprietes r SET parcelle_idu = p.idu, rattachement = 'geocode'
        FROM parcels p
        WHERE r.parcelle_idu IS NULL AND r.geom IS NOT NULL
          AND ST_Contains(p.geom, r.geom)"""))
    session.execute(text(
        "UPDATE rnic_coproprietes SET rattachement = 'aucun' WHERE parcelle_idu IS NULL"))
    session.flush()
    stats = session.execute(text(
        "SELECT count(*), count(*) FILTER (WHERE rattachement='cadastre'), "
        "count(*) FILTER (WHERE rattachement='geocode') FROM rnic_coproprietes")).one()
    return {"copros_974": n, "rattachees_cadastre": stats[1], "rattachees_geocode": stats[2]}
