"""Outil « Densifier l'existant » (clé interne `renouvellement`) — l'ENDPOINT /renouvellement/liste
n'avait AUCUN test (seul le build en avait). Ici : « ne lève pas » + la puce d'action servie
(tier v2, jamais « Classement historique ») + zéro vestige de matrice + le renommage §5 (grep=0)."""
from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import text

from labuse.scoring.score_v_constants import Q_A_RUN_LABEL

_ROOT = Path(__file__).resolve().parents[1]
_WKT = "POLYGON((55.3 -21.0,55.3003 -21.0,55.3003 -20.9997,55.3 -20.9997,55.3 -21.0))"


@pytest.mark.db
def test_liste_ne_leve_pas_puce_action_et_sans_vestige(db_session):
    from labuse.api.app import renouvellement_liste
    from labuse.renouvellement import DDL
    db_session.execute(text(DDL))   # table additive (idempotent)
    pid = db_session.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2, centroid, bbox) VALUES "
        "('97499000RN0001','Renouvville','S','1', ST_GeomFromText(:w,4326),"
        " ST_Transform(ST_GeomFromText(:w,4326),2975), 900,"
        " ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326))) RETURNING id"),
        {"w": _WKT}).scalar()
    # tier v2 SERVI (a_creuser) sous le run servi → la puce d'action a sa donnée
    db_session.execute(text(
        "INSERT INTO parcel_p_score_v2 (run_id, parcelle_id, p_raw, mult_base, percentile, rang, "
        "contrib_z, contrib_d, top5_contributions, copro, tier, model_version) "
        "VALUES (:r,'97499000RN0001',0.5,30,90,1,0.2,1.5,'[]',false,'a_creuser','test')"), {"r": Q_A_RUN_LABEL})
    db_session.execute(text(
        "INSERT INTO parcel_renouvellement (idu, renouv_score, comp_potentiel, comp_assiette, comp_marche, "
        "code_bati_origine, sdp_residuelle_m2, surface_m2, zone_plu, commune, rang_segment, rang_commune, run_label) "
        "VALUES ('97499000RN0001',80,40,25,15,'deja_bati',500,900,'U','97499',1,1,:r)"), {"r": Q_A_RUN_LABEL})
    out = renouvellement_liste(commune=None, sort="score", limit=0, offset=0, db=db_session)   # ne lève pas
    assert out["total"] == 1 and out["n"] == 1
    assert out["cap"] == 400 and out["tronquee"] is False        # §2 : plafond EN CONFIG, dit
    it = out["items"][0]
    assert it["tier_v2"] == "a_creuser" and "etage0" in it        # §1 : la puce d'action est servie
    # §4 : plus aucun vestige de matrice dans le payload
    for k in ("q_score", "a_score", "opportunity_score", "completeness_score", "statut"):
        assert k not in it


def test_densifier_retire_du_menu_plie_dans_filtre():
    """DENSIFIER-PLI (PISCINES-2 Lot B) — l'outil « Densifier l'existant » (clé `renouvellement`) est
    RETIRÉ du menu registry.ts et plié dans le filtre Capacité (« Déjà bâti » + « SDP restante »). La
    table `parcel_renouvellement` reste en base mais n'est plus servie à un écran."""
    registry = (_ROOT / "frontend/src/components/outils/registry.ts").read_text(encoding="utf-8")
    assert "key: 'renouvellement'" not in registry, "l'outil Densifier doit être retiré du menu"
    filtre = (_ROOT / "frontend/src/components/panel/FiltreLabuse.tsx").read_text(encoding="utf-8")
    assert "data-filtre-deja-bati" in filtre and "Déjà bâti" in filtre
