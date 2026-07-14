"""M-VIA lot 2 — construction batch de `parcel_viabilisation`.

Calcule, par parcelle, les signaux du faisceau (permis < 100/200 m, façade voie
urbanisée, adjacence bâti, zone PLU, poste source S3REnR, zonage assainissement) et
le score 0-100. Le score est calculé en SQL avec EXACTEMENT les mêmes poids/seuils
que faisabilite.viabilisation.compute_score (parité vérifiée par test).

Aucun tracé de réseau : uniquement des signaux déjà en base + géométries publiques.
"""
from __future__ import annotations

import time

from sqlalchemy import text
from sqlalchemy.orm import Session

from . import viabilisation as V

_DDL = """
CREATE TABLE IF NOT EXISTS parcel_viabilisation (
    idu           VARCHAR(14) PRIMARY KEY,
    commune       VARCHAR(64),
    score         INTEGER,
    band          VARCHAR(16),
    zone_fam      VARCHAR(4),
    c100          INTEGER,
    c200          INTEGER,
    c100_recent   INTEGER,
    c100_acheve   INTEGER,
    voie10        BOOLEAN,
    voie75        BOOLEAN,
    bati10        BOOLEAN,
    bati30        BOOLEAN,
    bati75        BOOLEAN,
    assainissement_zonage VARCHAR(12),
    computed_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_parcel_viab_commune ON parcel_viabilisation (commune);
CREATE INDEX IF NOT EXISTS ix_parcel_viab_band ON parcel_viabilisation (band);
"""

# Permis Sitadel AUTORISÉS et géolocalisés, projetés en 2975 (helper indexé, refait
# à chaque run). Un permis n'a de DATE_REELLE_AUTORISATION que s'il a été accordé.
_PERMITS_DDL = """
DROP TABLE IF EXISTS via_permits_geo;
CREATE TABLE via_permits_geo AS
SELECT permit_id, date::date AS d, (raw->>'etat') AS etat, ST_Transform(geom, 2975) AS g
FROM sitadel_permits WHERE geom IS NOT NULL AND date IS NOT NULL;
CREATE INDEX ON via_permits_geo USING gist (g);
"""

# Score SQL — miroir EXACT de viabilisation.compute_score (poids W_*).
_SCORE_SQL = f"""
  (CASE WHEN c100>=6 THEN {V.W_PERMIS} WHEN c100>=3 THEN 30 WHEN c100>=1 THEN 18
        WHEN c200>=3 THEN 8 ELSE 0 END)
+ (CASE WHEN voie10 AND bati30 THEN {V.W_FACADE} WHEN voie10 THEN 8 WHEN voie75 THEN 4 ELSE 0 END)
+ (CASE WHEN bati10 THEN {V.W_BATI} WHEN bati30 THEN 9 WHEN bati75 THEN 3 ELSE 0 END)
+ (CASE zone_fam WHEN 'U' THEN {V.W_ZONE} WHEN 'AU' THEN 13 WHEN 'A' THEN 4 ELSE 0 END)
"""

_BAND_SQL = (
    "CASE WHEN score>=70 THEN 'confirmee' WHEN score>=45 THEN 'probable' "
    "WHEN score>=25 THEN 'incertaine' ELSE 'lourde' END"
)

# Insertion par commune : signaux (sous-requêtes ST_DWithin index-friendly) → score → band.
_INSERT_COMMUNE = f"""
INSERT INTO parcel_viabilisation
  (idu, commune, zone_fam, c100, c200, c100_recent, c100_acheve,
   voie10, voie75, bati10, bati30, bati75, assainissement_zonage, score, band)
SELECT idu, commune, zone_fam, c100, c200, c100_recent, c100_acheve,
       voie10, voie75, bati10, bati30, bati75, assainissement_zonage,
       ({_SCORE_SQL}) AS score,
       ({_BAND_SQL.replace('score', '(' + _SCORE_SQL + ')')})
FROM (
  SELECT p.idu, p.commune, z.zone_fam,
    (SELECT count(*) FROM via_permits_geo w WHERE ST_DWithin(p.geom_2975,w.g,100)) c100,
    (SELECT count(*) FROM via_permits_geo w WHERE ST_DWithin(p.geom_2975,w.g,200)) c200,
    (SELECT count(*) FROM via_permits_geo w WHERE ST_DWithin(p.geom_2975,w.g,100) AND w.d>=make_date(:annee,1,1)) c100_recent,
    (SELECT count(*) FROM via_permits_geo w WHERE ST_DWithin(p.geom_2975,w.g,100) AND w.etat='6') c100_acheve,
    EXISTS(SELECT 1 FROM spatial_layers v WHERE v.kind='voirie' AND v.commune=p.commune AND ST_DWithin(p.geom_2975,v.geom_2975,10)) voie10,
    EXISTS(SELECT 1 FROM spatial_layers v WHERE v.kind='voirie' AND v.commune=p.commune AND ST_DWithin(p.geom_2975,v.geom_2975,75)) voie75,
    EXISTS(SELECT 1 FROM spatial_layers b WHERE b.kind='batiment' AND b.commune=p.commune AND ST_DWithin(p.geom_2975,b.geom_2975,10)) bati10,
    EXISTS(SELECT 1 FROM spatial_layers b WHERE b.kind='batiment' AND b.commune=p.commune AND ST_DWithin(p.geom_2975,b.geom_2975,30)) bati30,
    EXISTS(SELECT 1 FROM spatial_layers b WHERE b.kind='batiment' AND b.commune=p.commune AND ST_DWithin(p.geom_2975,b.geom_2975,75)) bati75,
    (SELECT za.subtype FROM spatial_layers za WHERE za.kind='zonage_assainissement'
       AND za.commune=p.commune AND ST_Intersects(p.geom_2975, za.geom_2975)
       ORDER BY CASE za.subtype WHEN 'collectif' THEN 0 ELSE 1 END LIMIT 1) assainissement_zonage
  FROM parcels p
  LEFT JOIN parcel_zone_plu z ON z.idu = p.idu
  WHERE p.commune = :commune AND p.geom_2975 IS NOT NULL
) s
ON CONFLICT (idu) DO UPDATE SET
  commune=EXCLUDED.commune, zone_fam=EXCLUDED.zone_fam, c100=EXCLUDED.c100, c200=EXCLUDED.c200,
  c100_recent=EXCLUDED.c100_recent, c100_acheve=EXCLUDED.c100_acheve, voie10=EXCLUDED.voie10,
  voie75=EXCLUDED.voie75, bati10=EXCLUDED.bati10, bati30=EXCLUDED.bati30, bati75=EXCLUDED.bati75,
  assainissement_zonage=EXCLUDED.assainissement_zonage,
  score=EXCLUDED.score, band=EXCLUDED.band, computed_at=now();
"""


def ilot_s3renr_note(session: Session) -> dict | None:
    """Note PV S3REnR au niveau ÎLE (les 24 postes sources ne sont pas géolocalisés en
    base : pas d'attribution par parcelle → message honnête d'îlot). Volet PV, hors 0-100."""
    row = session.execute(text(
        "SELECT count(*) n, count(*) FILTER (WHERE capa_dispo_mw<=0) sat, "
        "max(source) src FROM grid_capacity")).mappings().first()
    if not row or not row["n"]:
        return None
    n, sat = row["n"], row["sat"]
    if sat >= n:
        note = (f"Capacité d'accueil PV NULLE sur les {n} postes sources de La Réunion "
                "(S3REnR) → toute injection photovoltaïque est en file d'attente réseau.")
        statut = "saturee"
    else:
        note = (f"{n - sat}/{n} postes sources avec capacité d'accueil PV disponible (S3REnR).")
        statut = "partielle"
    return {"portee": "ile", "n_postes": n, "n_satures": sat, "statut": statut,
            "note": note, "source": row["src"],
            "disclaimer": "Volet PV — capacité réseau au niveau poste source (non géolocalisé "
                          "par parcelle). À confirmer auprès d'EDF SEI."}


def build_viabilisation(session: Session, communes: list[str] | None = None) -> dict:
    """Construit/rafraîchit parcel_viabilisation. `communes=None` → les 24."""
    t0 = time.time()
    for stmt in _DDL.strip().split(";\n"):
        if stmt.strip():
            session.execute(text(stmt))
    session.execute(text(_PERMITS_DDL.replace("\n", " ")))
    session.commit()

    if communes is None:
        communes = [r[0] for r in session.execute(text(
            "SELECT DISTINCT commune FROM parcels WHERE geom_2975 IS NOT NULL ORDER BY 1")).all()]

    total = 0
    per_commune = {}
    for c in communes:
        session.execute(text(_INSERT_COMMUNE), {"commune": c, "annee": V.ANNEE_RECENTE})
        n = session.execute(text(
            "SELECT count(*) FROM parcel_viabilisation WHERE commune=:c"), {"c": c}).scalar()
        session.commit()
        per_commune[c] = n
        total += 0  # total recomputed below
    total = session.execute(text("SELECT count(*) FROM parcel_viabilisation")).scalar()
    return {"n": total, "communes": len(communes), "per_commune": per_commune,
            "duree_s": round(time.time() - t0, 1)}
