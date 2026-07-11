"""LOT 10 (data-gap) — RNIC : Registre National d'Immatriculation des Copropriétés (ANAH).

Source : data.gouv.fr, fichier national CSV (~453 Mo, T3 2025 ; URL stable testée live
10/07/2026), **2 220 copropriétés au 974**. Champs vérifiés sur données réelles : jusqu'à
3 références cadastrales DÉJÀ AU FORMAT IDU 14 car. (`reference_cadastrale_n`), long/lat,
`nombre_total_de_lots`, `nombre_de_lots_a_usage_d_habitation`, `periode_de_construction`,
syndic (type, raison sociale, SIRET), mandat en cours.

Rattachement parcelle : référence cadastrale → `parcels.idu` (direct) ; fallback point
long/lat dans la parcelle ; puis adresse locale (ban_adresses.rattacher_copros_par_adresse) ;
puis parcelle la plus proche ≤ 20 m (`proche_20m`, même idiome que l'ingestion BAN).
Cible marchands de biens : **pas de scoring** (mandat) — fiche parcelle (bloc copro) +
table interrogeable/filtrable.

**RGPD strict (mandat Wave copro)** : `syndic_nom`/`syndic_siret` renseignés UNIQUEMENT si
`syndic_type='professionnel'` (personne morale). Un syndic bénévole ou « non connu » est
potentiellement une personne physique → on stocke le type, JAMAIS le nom, même si le RNIC
le fournit — y compris dans `raw` (clés représentant légal retirées).

CLI : labuse ingest-rnic --csv <chemin>   (le CSV national n'est pas conservé au repo)
      labuse rnic-complements             (purge RGPD + rattachement proche_20m, sans CSV)
"""
from __future__ import annotations

import csv
import json

from sqlalchemy import text
from sqlalchemy.orm import Session

SOURCE_NAME = "RNIC — copropriétés (ANAH)"
URL_STABLE = "https://www.data.gouv.fr/fr/datasets/r/132ed35f-db38-48d9-a31f-3dd7a0942cd9"

#: clés du CSV RNIC identifiant le représentant légal — purgées de `raw` si syndic non pro
#: (personne physique potentielle : on garde le TYPE, jamais le nom — mandat Wave copro).
_CLES_REPRESENTANT = ("raison_sociale_du_representant_legal", "siret_du_representant_legal")

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
            styp = (row.get("type_de_syndic_benevole_professionnel_non_connu") or "")[:16] or None
            pro = (styp or "").lower() == "professionnel"   # RGPD : nom/SIRET seulement si pro
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
                "styp": styp,
                "snom": (row.get("raison_sociale_du_representant_legal") or None) if pro else None,
                "ssiret": ((row.get("siret_du_representant_legal") or "")[:14] or None) if pro else None,
                "mandat": (row.get("mandat_en_cours_dans_la_copropriete") or "").lower()
                          in ("oui", "true", "1"),
                "idus": json.dumps(idus), "lon": lon or "", "lat": lat or "",
                "raw": json.dumps({k: v for k, v in row.items()
                                   if v and (pro or k not in _CLES_REPRESENTANT)},
                                  ensure_ascii=False)})
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
    rattacher_proche(session)
    session.execute(text(
        "UPDATE rnic_coproprietes SET rattachement = 'aucun' WHERE parcelle_idu IS NULL"))
    session.flush()
    stats = session.execute(text(
        "SELECT count(*), count(*) FILTER (WHERE rattachement='cadastre'), "
        "count(*) FILTER (WHERE rattachement='geocode') FROM rnic_coproprietes")).one()
    return {"copros_974": n, "rattachees_cadastre": stats[1], "rattachees_geocode": stats[2]}


def rattacher_proche(session: Session, dist_m: float = 20.0) -> int:
    """Rattache les copros restantes à la parcelle la plus proche ≤ `dist_m` (défaut 20 m,
    même idiome que l'ingestion BAN) → rattachement='proche_20m'. Le point RNIC tombe parfois
    sur la voirie, juste hors du polygone parcellaire. Retourne le nombre de copros liées."""
    res = session.execute(text("""
        UPDATE rnic_coproprietes r SET parcelle_idu = sub.idu, rattachement = 'proche_20m'
        FROM (SELECT r2.numero_immatriculation,
                     (SELECT p.idu FROM parcels p
                      WHERE ST_DWithin(p.geom_2975, ST_Transform(r2.geom, 2975), :d)
                      ORDER BY p.geom_2975 <-> ST_Transform(r2.geom, 2975) LIMIT 1) AS idu
              FROM rnic_coproprietes r2
              WHERE r2.parcelle_idu IS NULL AND r2.geom IS NOT NULL) sub
        WHERE sub.numero_immatriculation = r.numero_immatriculation AND sub.idu IS NOT NULL"""),
        {"d": dist_m})
    return res.rowcount or 0


def purge_rgpd(session: Session) -> int:
    """Applique la règle RGPD sur les lignes DÉJÀ en base : syndic non professionnel →
    nom/SIRET effacés, clés du représentant légal retirées de `raw`. Idempotent."""
    res = session.execute(text("""
        UPDATE rnic_coproprietes
        SET syndic_nom = NULL, syndic_siret = NULL,
            raw = raw - :k1 - :k2
        WHERE (syndic_type IS NULL OR syndic_type <> 'professionnel')
          AND (syndic_nom IS NOT NULL OR syndic_siret IS NOT NULL
               OR raw ?| ARRAY[:k1, :k2])"""),
        {"k1": _CLES_REPRESENTANT[0], "k2": _CLES_REPRESENTANT[1]})
    return res.rowcount or 0


def complements(session: Session, log=print) -> dict:
    """Compléments data socle sans CSV (mandat Wave copro re-scopé 11/07) :
    purge RGPD des syndics non professionnels + rattachement proche_20m du reliquat."""
    purgees = purge_rgpd(session)
    liees = rattacher_proche(session)
    session.execute(text(
        "UPDATE rnic_coproprietes SET rattachement = 'aucun' WHERE parcelle_idu IS NULL"))
    session.flush()
    stats = {r[0]: r[1] for r in session.execute(text(
        "SELECT rattachement, count(*) FROM rnic_coproprietes GROUP BY 1")).all()}
    out = {"rgpd_purgees": purgees, "proche_20m_liees": liees, "rattachement": stats}
    log(f"RNIC compléments : {out}")
    return out
