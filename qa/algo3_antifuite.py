#!/usr/bin/env python
"""ALGO-3 — TEST ANTI-FUITE OBLIGATOIRE (règle 4 + LOT B), à exécuter AVANT tout
entraînement. Si UN de ces contrôles échoue, tout le reste est invalide.

Contrôles (recomptes INDÉPENDANTS des tables de paires — SQL direct sur les sources) :
  1. AUCUNE paire où la cible est son propre voisin (idu_a = idu porteur) ;
  2. AUCUNE paire portant une mutation À LAQUELLE LA CIBLE PARTICIPE (multi-parcelles) ;
  3. AS-OF : pour un échantillon aléatoire seedé, ventes_100m_24m de l'année Y recompté
     À LA MAIN (ST_DWithin direct sur p_model_ext_mut_l2, cible et ses mutations exclues,
     fenêtre [max(01/01/Y-2, 2014) ; 01/01/Y[ ) == valeur de la table — et le recompte
     n'inclut par construction AUCUNE mutation ≥ 01/01/Y ;
  4. idem permis (permis_100m_24m) sur le même échantillon.
"""
from __future__ import annotations

import os
import sys

from sqlalchemy import create_engine, text

DB = os.environ.get("LABUSE_DATABASE_URL", "postgresql+psycopg://openclaw@localhost:5432/labuse")
N_ECH = 12          # parcelles recomptées à la main (seed SQL déterministe)
ANNEES = (2020, 2023, 2025)


def main() -> int:
    eng = create_engine(DB)
    ok = True
    with eng.connect() as cx:
        n1 = cx.execute(text("""
            SELECT count(*) FROM algo3_pairs_mut pm
            JOIN p_model_ext_mut_l2 m ON m.id_mutation = pm.id_mutation AND m.idu = pm.idu
        """)).scalar()
        print(f"1. paires où la cible porte la mutation (attendu 0) : {n1}")
        ok &= (n1 == 0)

        n2 = cx.execute(text("""
            SELECT count(*) FROM algo3_pairs_permis pp
            JOIN sitadel_permits s ON s.permit_id = pp.permit_id
            WHERE s.idu_codes ? pp.idu
        """)).scalar()
        print(f"2. paires permis rattachés à la cible (attendu 0) : {n2}")
        ok &= (n2 == 0)

        ech = [r[0] for r in cx.execute(text("""
            SELECT idu FROM (SELECT idu, md5('974' || idu) h FROM algo3_dens WHERE n100 > 3) t
            ORDER BY h LIMIT :n"""), {"n": N_ECH}).all()]
        print(f"3-4. recompte manuel sur {len(ech)} parcelles × {ANNEES} :")
        bad = 0
        for idu in ech:
            for y in ANNEES:
                row = cx.execute(text("""
                  WITH cible AS (SELECT c FROM algo3_c WHERE idu = :i),
                  manuel AS (
                    SELECT count(DISTINCT m.id_mutation) AS v
                    FROM p_model_ext_mut_l2 m JOIN algo3_c cm ON cm.idu = m.idu, cible
                    WHERE NOT m.exclue_l2f AND m.idu <> :i
                      AND NOT EXISTS (SELECT 1 FROM p_model_ext_mut_l2 x
                                      WHERE x.id_mutation = m.id_mutation AND x.idu = :i)
                      AND ST_DWithin(cible.c, cm.c, 100)
                      AND m.date_mutation >= greatest(make_date(:y - 2, 1, 1), DATE '2014-01-01')
                      AND m.date_mutation <  make_date(:y, 1, 1)),
                  manuel_p AS (
                    SELECT count(DISTINCT s.permit_id) AS p
                    FROM sitadel_permits s, cible
                    WHERE s.geom IS NOT NULL AND NOT (s.idu_codes ? CAST(:i AS text))
                      AND ST_DWithin(cible.c, ST_Transform(s.geom, 2975), 100)
                      AND s.date::date >= greatest(make_date(:y - 2, 1, 1), DATE '2014-01-01')
                      AND s.date::date <  make_date(:y, 1, 1)),
                  tbl AS (SELECT ventes_100m_24m, permis_100m_24m
                          FROM algo3_voisinage WHERE idu = :i AND annee = :y),
                  dens AS (SELECT n100 FROM algo3_dens WHERE idu = :i)
                  SELECT manuel.v, manuel_p.p, tbl.ventes_100m_24m, tbl.permis_100m_24m, dens.n100
                  FROM manuel, manuel_p, tbl, dens"""),
                  {"i": idu, "y": y}).one()
                v_att = row[0] / row[4] if row[4] else None
                p_att = row[1] / row[4] if row[4] else None
                ok_v = (row[2] is None and v_att is None) or (row[2] is not None and abs(row[2] - v_att) < 1e-9)
                ok_p = (row[3] is None and p_att is None) or (row[3] is not None and abs(row[3] - p_att) < 1e-9)
                if not (ok_v and ok_p):
                    bad += 1
                    print(f"   ✗ {idu} annee={y} : table=({row[2]},{row[3]}) manuel=({v_att},{p_att})")
        print(f"   écarts : {bad}/{len(ech) * len(ANNEES)} (attendu 0)")
        ok &= (bad == 0)
    print("VERDICT ANTI-FUITE :", "PASS ✓" if ok else "FAIL ✗ — TOUT ENTRAÎNEMENT INTERDIT")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
