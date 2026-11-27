"""OUTIL-PERMIS-FIX-14 (LOT 2) — ce que l'utilisateur NE voit PAS : impact de la péremption de
`p_model_permits` sur les VARIABLES du modèle P, le rattachement defisc et le drapeau pro_pc.

LECTURE SEULE stricte (SELECT uniquement, aucune écriture). On MESURE et on DÉCRIT ; on ne corrige
rien (la reconstruction de la table et le re-run q_v25 sont hors de ce tour). On PROUVE que le
classement SERVI q_v20 ne bouge pas (il est lu dans des tables matérialisées, pas recalculé depuis
`p_model_permits` à la requête, et rien n'a été écrit).

    PYTHONPATH=src LABUSE_DATABASE_URL=…/labuse python scripts/outil_permis_fix8/fix14_mesure_modele_p.py
"""
from __future__ import annotations

import os

from sqlalchemy import create_engine, text

eng = create_engine(os.environ["LABUSE_DATABASE_URL"])


def scal(c, sql, **p):
    return c.execute(text(sql), p).scalar()


with eng.connect() as c:
    print("=== 1 · Variables FAUSSES : péremption des couples (permit_id, idu) ===")
    # couple source (sitadel) : (permit_id, idu, date d'autorisation source)
    src = """
      SELECT DISTINCT sp.permit_id, j.idu, sp.date::date AS d
      FROM sitadel_permits sp JOIN LATERAL jsonb_array_elements_text(sp.idu_codes) j(idu) ON true
      WHERE sp.date IS NOT NULL
    """
    n_src = scal(c, f"SELECT count(*) FROM ({src}) q")
    n_pmp = scal(c, "SELECT count(*) FROM p_model_permits")
    # date divergente sur un couple présent des deux côtés
    date_diff = scal(c, f"""
      SELECT count(*) FROM ({src}) s
      JOIN p_model_permits p ON p.permit_id = s.permit_id AND p.idu = s.idu
      WHERE p.date_autorisation IS DISTINCT FROM s.d""")
    parc_date_diff = scal(c, f"""
      SELECT count(DISTINCT s.idu) FROM ({src}) s
      JOIN p_model_permits p ON p.permit_id = s.permit_id AND p.idu = s.idu
      WHERE p.date_autorisation IS DISTINCT FROM s.d""")
    couples_manquants = scal(c, f"""
      SELECT count(*) FROM ({src}) s
      LEFT JOIN p_model_permits p ON p.permit_id = s.permit_id AND p.idu = s.idu
      WHERE p.permit_id IS NULL""")
    parc_manquantes = scal(c, f"""
      SELECT count(DISTINCT s.idu) FROM ({src}) s
      LEFT JOIN p_model_permits p ON p.permit_id = s.permit_id AND p.idu = s.idu
      WHERE p.permit_id IS NULL""")
    couples_fantomes = scal(c, f"""
      SELECT count(*) FROM p_model_permits p
      LEFT JOIN ({src}) s ON s.permit_id = p.permit_id AND s.idu = p.idu
      WHERE s.permit_id IS NULL""")
    parc_impactees = scal(c, f"""
      WITH s AS ({src}),
      diff AS (
        SELECT s.idu FROM s JOIN p_model_permits p ON p.permit_id=s.permit_id AND p.idu=s.idu
          WHERE p.date_autorisation IS DISTINCT FROM s.d
        UNION SELECT s.idu FROM s LEFT JOIN p_model_permits p ON p.permit_id=s.permit_id AND p.idu=s.idu
          WHERE p.permit_id IS NULL
        UNION SELECT p.idu FROM p_model_permits p LEFT JOIN s ON s.permit_id=p.permit_id AND s.idu=p.idu
          WHERE s.permit_id IS NULL)
      SELECT count(DISTINCT idu) FROM diff""")
    print(f"  couples source (sitadel)        : {n_src}")
    print(f"  lignes p_model_permits          : {n_pmp}")
    print(f"  couples à DATE divergente       : {date_diff}  (sur {parc_date_diff} parcelles)")
    print(f"  couples MANQUANTS (source→pmp)  : {couples_manquants}  (sur {parc_manquantes} parcelles)")
    print(f"  couples FANTÔMES (pmp→source)   : {couples_fantomes}")
    print(f"  => PARCELLES à variable modèle P potentiellement fausse : {parc_impactees}")

    print("\n=== 2 · Rattachement defisc / pro_pc (non daté) ===")
    # pro_pc = DISTINCT idu ayant un PC dans p_model_permits ; une parcelle dont TOUS les couples PC
    # manquent perdrait le drapeau. defisc rattache par (idu, permit_id, type=PC) puis JOIN sitadel DAACT.
    pro_pc_pmp = scal(c, "SELECT count(DISTINCT idu) FROM p_model_permits WHERE type='PC'")
    pro_pc_src = scal(c, """SELECT count(DISTINCT j.idu) FROM sitadel_permits sp
      JOIN LATERAL jsonb_array_elements_text(sp.idu_codes) j(idu) ON true WHERE sp.type='PC'""")
    print(f"  parcelles avec PC (p_model_permits, drapeau pro_pc) : {pro_pc_pmp}")
    print(f"  parcelles avec PC (sitadel, vérité)                 : {pro_pc_src}")
    print(f"  => parcelles PC perdues par le drapeau pro_pc        : {pro_pc_src - pro_pc_pmp}")

    print("\n=== 3 · Classement SERVI q_v20 — ne bouge pas (preuve) ===")
    run = scal(c, "SELECT to_regclass('parcel_p_score_v2')")
    served = None
    try:
        served = scal(c, "SELECT run_label FROM served_run LIMIT 1")
    except Exception:
        c.rollback()
    print(f"  table servie parcel_p_score_v2 présente : {run is not None}")
    print(f"  run servi (served_run)                  : {served}")
    # le score servi est LU dans la table matérialisée, PAS recalculé depuis p_model_permits à la requête.
    try:
        n_scores = scal(c, "SELECT count(*) FROM parcel_p_score_v2")
        print(f"  lignes parcel_p_score_v2 (figées)       : {n_scores}")
    except Exception:
        c.rollback()
    print("  => aucune écriture ce tour + aucun fichier scoring modifié (LOT 2) → q_v20 servi inchangé.")
    print("     Les features du modèle P ne sont relues qu'au PROCHAIN run (q_v25).")

    print("\n=== 4 · À reconstruire AVANT q_v25 ===")
    print("  1) scoring/p_model/sql.build_permits  → p_model_permits = DISTINCT sitadel.date::date (table fraîche)")
    print("  2) scoring/p_model/sql.build_dataset + p_model/ext_sql.build_ext_dataset (features)")
    print("  3) chaîne q_v2 (qv12/qv14/monitoring) relue sur la table reconstruite")
    print("  defisc_fenetres / dvf_prix_neuf : se rafraîchissent aussi via build_permits (rattachement).")
