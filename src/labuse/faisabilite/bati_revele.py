"""Règle « BÂTIE RÉVÉLÉE » (arbitrage Vic 04/08, dette #4) — cache `parcel_bati_revele`.

Une parcelle dont la couche BD TOPO est quasi vide (< 20 m²) mais dont max(BD TOPO, CoSIA)
atteint ≥ 40 m² porte un bâti que l'image voit et que les sources vectorielles ratent
(retard structurel sur le neuf — cf. DETTE4_COUCHE_BATIMENT_SOURCES). Elle est DÉCLASSÉE
(tier dédié `declasse_bati_revele`), motif SERVI daté et sourcé. La bande 20-40 m² n'est
JAMAIS auto-déclassée : adjudication humaine sur cartes datées.

Le motif dit aussi la limite honnête (consigne Vic) : la SDP affichée reste celle du terrain
nu théorique tant que la chaîne résiduel n'est pas recalculée avec le bâti révélé (train 5).

Table clé parcel_id, INDÉPENDANTE du run (comme parcel_au_statut) : survit aux bascules.
Peupler ≠ basculer — le pipeline la lit, kill-switch LABUSE_DISABLE_BATI_REVELE=1.

DOUBLON MARQUÉ (PAU-CoSIA) : `p_model_bati_cosia` (emprise CoSIA PAR PARCELLE, sans géométrie,
construite hors dépôt le 04/08/2026) est l'AGRÉGAT à la parcelle des MÊMES footprints CoSIA
désormais ingérés canoniquement dans `spatial_layers kind='batiment_cosia'` (ingestion/cosia.py,
source géométrique de vérité). Preuve d'équivalence : re-dérivation depuis batiment_cosia =
521 936 m² vs p_model 521 918 m² à Saint-Philippe (0,003 %). Remplacement propre (re-dériver
p_model_bati_cosia DEPUIS batiment_cosia) = follow-up hors mandat PAU (touche 9 consommateurs) ;
cf. docs/mandats/PAU_COSIA_PHASE2.md.
"""
from __future__ import annotations

from sqlalchemy import text

SEUIL_REGLE_M2 = 40.0        # déclassement automatique au-delà
SEUIL_COUCHE_VIDE_M2 = 20.0  # « servie comme nue » : couche BD TOPO sous ce seuil
COSIA_MILLESIME = "CoSIA 2025 (PVA juil.-août 2025)"


def build_parcel_bati_revele(session) -> dict:
    """(Re)peuple `parcel_bati_revele` depuis p_model_bati_cosia × spatial_layers (BD TOPO
    recalculée à la volée pour rester indépendant du build p_model_bati, qui peut être en
    mode max). Idempotent, transactionnel. Renvoie les effectifs {regle, bande_adjudication}."""
    session.execute(text("""
        CREATE TABLE IF NOT EXISTS parcel_bati_revele (
          parcel_id integer PRIMARY KEY REFERENCES parcels(id),
          idu varchar(14) NOT NULL,
          emprise_bdtopo_m2 double precision NOT NULL,
          emprise_cosia_m2 double precision NOT NULL,
          bande varchar(16) NOT NULL,           -- 'regle' (≥40) | 'adjudication' (20-40)
          motif text NOT NULL,
          computed_at timestamptz NOT NULL DEFAULT now())"""))
    session.execute(text("TRUNCATE parcel_bati_revele"))
    session.execute(text(f"""
        INSERT INTO parcel_bati_revele (parcel_id, idu, emprise_bdtopo_m2, emprise_cosia_m2, bande, motif)
        SELECT p.id, p.idu, COALESCE(bd.emprise, 0), c.emprise_cosia_m2,
               CASE WHEN GREATEST(COALESCE(bd.emprise,0), c.emprise_cosia_m2) >= {SEUIL_REGLE_M2}
                    THEN 'regle' ELSE 'adjudication' END,
               'bâti détecté {COSIA_MILLESIME}, ' || round(c.emprise_cosia_m2)::int || ' m². '
               || 'SDP affichée = terrain nu théorique (recalcul de la chaîne résiduel au train 5).'
        FROM p_model_bati_cosia c
        JOIN parcels p ON p.idu = c.idu
        LEFT JOIN LATERAL (
          SELECT sum(ST_Area(ST_Intersection(b.geom_2975, p.geom_2975))) AS emprise
          FROM spatial_layers b
          WHERE b.kind = 'batiment' AND b.geom_2975 && p.geom_2975
            AND ST_Intersects(b.geom_2975, p.geom_2975)) bd ON true
        WHERE COALESCE(bd.emprise, 0) < {SEUIL_COUCHE_VIDE_M2}
          AND GREATEST(COALESCE(bd.emprise, 0), c.emprise_cosia_m2) >= {SEUIL_COUCHE_VIDE_M2}"""))
    n = dict(session.execute(text(
        "SELECT bande, count(*) FROM parcel_bati_revele GROUP BY bande")).all())
    return {"regle": n.get("regle", 0), "adjudication": n.get("adjudication", 0)}
