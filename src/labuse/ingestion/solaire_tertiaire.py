"""Lot 6 Habitat Solaire — vue tertiaire : grandes toitures × santé financière.

Pur croisement de l'EXISTANT (aucune ingestion) : emprise bâtie BD TOPO > 500 m²
(non résidentielle) × parcelle support × propriétaire personne morale (DGFiP) ×
dernier bilan INPI (owner_enrichment.finances : CA, résultat net) × production
spécifique PVGIS × distance au poste source EDF SEI (NULL tant que le Lot 7 n'a
pas peuplé grid_capacity — un refresh suffit ensuite).

Vue MATÉRIALISÉE `mv_toitures_tertiaires`, triée par potentiel (emprise × score
solaire). Refresh : `labuse solaire-tertiaire --refresh` (ou après Lot 1/7).
"""
from __future__ import annotations

import csv
import io
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..config import habitat_solaire

#: usages BD TOPO retenus (grandes toitures d'activité ; « Annexe » et résidentiel exclus)
_USAGES_EXCLUS = ("Résidentiel", "Annexe")


def _seuil_m2() -> float:
    return float(habitat_solaire()["tertiaire"]["emprise_min_m2"])


def _ddl(seuil: float) -> str:
    # matview : pas de paramètre bindé possible → seuil validé (float) inliné
    return f"""
    CREATE MATERIALIZED VIEW mv_toitures_tertiaires AS
    WITH bati AS (
      SELECT sl.id AS bat_id, sl.geom_2975,
             round(ST_Area(sl.geom_2975))::int AS emprise_m2,
             sl.attrs ->> 'usage' AS usage,
             NULLIF(sl.attrs ->> 'hauteur', '')::float AS hauteur
      FROM spatial_layers sl
      WHERE sl.kind = 'batiment'
        AND ST_Area(sl.geom_2975) > {seuil:.1f}
        AND coalesce(sl.attrs ->> 'usage', '') NOT IN ('Résidentiel', 'Annexe')
    ),
    support AS (
      SELECT DISTINCT ON (b.bat_id) b.*, p.idu, p.commune
      FROM bati b
      JOIN parcels p ON ST_Intersects(p.geom_2975, b.geom_2975)
      ORDER BY b.bat_id, ST_Area(ST_Intersection(p.geom_2975, b.geom_2975)) DESC
    )
    SELECT s.bat_id, s.idu, s.commune, s.emprise_m2, s.usage, s.hauteur,
           pm.denomination AS proprio_pm, pm.siren AS proprio_siren,
           fin.annee AS bilan_annee, fin.ca, fin.resultat_net,
           sol.prod_spec_kwh_kwc, sol.score_solaire,
           ps.dist_m AS dist_poste_source_m, ps.poste_source,
           (s.emprise_m2 * coalesce(sol.score_solaire, 0)) AS potentiel,
           ST_Y(ST_Centroid(ST_Transform(s.geom_2975, 4326))) AS lat,
           ST_X(ST_Centroid(ST_Transform(s.geom_2975, 4326))) AS lon
    FROM support s
    LEFT JOIN LATERAL (
      SELECT denomination, siren FROM parcelle_personne_morale m
      WHERE m.idu = s.idu AND m.denomination IS NOT NULL
      ORDER BY (m.siren IS NULL), m.groupe LIMIT 1
    ) pm ON true
    LEFT JOIN LATERAL (
      SELECT (f.key)::int AS annee, (f.value ->> 'ca')::numeric AS ca,
             (f.value ->> 'resultat_net')::numeric AS resultat_net
      FROM owner_enrichment oe, jsonb_each(oe.payload -> 'finances') f
      WHERE oe.siren = pm.siren
        AND jsonb_typeof(oe.payload -> 'finances') = 'object'
      ORDER BY f.key DESC LIMIT 1
    ) fin ON true
    LEFT JOIN parcel_solar sol ON sol.idu = s.idu
    LEFT JOIN LATERAL (
      SELECT g.poste_source, round(ST_Distance(g.geom::geography,
               ST_Transform(ST_Centroid(s.geom_2975), 4326)::geography))::int AS dist_m
      FROM grid_capacity g WHERE g.geom IS NOT NULL
      ORDER BY g.geom <-> ST_Transform(ST_Centroid(s.geom_2975), 4326) LIMIT 1
    ) ps ON true
    """


def refresh(session: Session) -> dict[str, Any]:
    """(Re)construit la vue — DROP/CREATE : le seuil config peut avoir changé."""
    session.execute(text("DROP MATERIALIZED VIEW IF EXISTS mv_toitures_tertiaires"))
    session.execute(text(_ddl(_seuil_m2())))
    session.execute(text(
        "CREATE UNIQUE INDEX mv_toitures_tertiaires_bat_uix ON mv_toitures_tertiaires (bat_id)"))
    n, pm, fin = session.execute(text(
        "SELECT count(*), count(proprio_siren), count(bilan_annee)"
        " FROM mv_toitures_tertiaires")).one()
    return {"toitures": n, "avec_pm": pm, "avec_bilan": fin}


#: colonnes de l'export CSV (en-têtes français, RGPD : personnes MORALES uniquement)
EXPORT_COLS = [
    ("idu", "Parcelle (IDU)"), ("commune", "Commune"), ("emprise_m2", "Emprise toiture (m²)"),
    ("usage", "Usage BD TOPO"), ("proprio_pm", "Propriétaire (personne morale)"),
    ("proprio_siren", "SIREN"), ("bilan_annee", "Bilan (année)"), ("ca", "CA (€)"),
    ("resultat_net", "Résultat net (€)"), ("prod_spec_kwh_kwc", "Prod. spécifique (kWh/kWc/an)"),
    ("score_solaire", "Score solaire (/100)"), ("dist_poste_source_m", "Poste source (m)"),
]


def export_csv(session: Session, limit: int = 5000) -> str:
    rows = session.execute(text(
        "SELECT * FROM mv_toitures_tertiaires ORDER BY potentiel DESC LIMIT :lim"),
        {"lim": limit}).mappings().all()
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow([h for _, h in EXPORT_COLS])
    for r in rows:
        w.writerow([r.get(k) for k, _ in EXPORT_COLS])
    return buf.getvalue()
