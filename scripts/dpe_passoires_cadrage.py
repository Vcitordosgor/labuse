#!/usr/bin/env python
"""PHASE A cycle 3 — cadrage « passoires DPE F/G » (LECTURE SEULE).

Chiffre (1) la couverture DPE F/G ∩ univers non-écarté ∩ mono, (2) la faisabilité des deux juges
(J1 event-study autour du gel des loyers DOM 1/7/2024 ; J2 walk-forward as-of strict). Aucune écriture.

Verdict attendu (cf. A1_DPE_CADRAGE.md) : couverture anecdotique + deux juges sous-alimentés → NO-GO V.
"""
from __future__ import annotations
from sqlalchemy import text
from labuse.db import session_scope

MONO = "NOT (COALESCE(c.copro_rnic,false) OR COALESCE(c.copro_dvf,false))"


def main():
    with session_scope() as s:
        cov = s.execute(text(f"""
            WITH fg AS (SELECT d.parcelle_idu idu FROM dpe_records d
                        WHERE d.etiquette_dpe IN ('F','G') AND d.parcelle_idu IS NOT NULL)
            SELECT
              (SELECT count(*) FROM dpe_records) dpe_total,
              (SELECT count(*) FROM dpe_records WHERE etiquette_dpe IN ('F','G')) fg_total,
              (SELECT count(*) FROM fg WHERE EXISTS (SELECT 1 FROM parcel_p_score_v2 s
                   WHERE s.parcelle_id=fg.idu AND s.run_id='q_v7_defisc' AND s.tier<>'ecartee'
                   AND EXISTS (SELECT 1 FROM p_model_ext_copro c WHERE c.idu=fg.idu AND {MONO}))) fg_actionnable
        """)).mappings().first()
        print(f"DPE total={cov['dpe_total']} · F/G={cov['fg_total']} · "
              f"F/G ∩ non-écarté ∩ mono (ACTIONNABLE)={cov['fg_actionnable']}")

        j1 = s.execute(text(f"""
            WITH dpe AS (SELECT d.parcelle_idu idu,
                   CASE WHEN d.etiquette_dpe IN ('F','G') THEN 'FG' ELSE 'DE' END grp
                 FROM dpe_records d JOIN p_model_ext_copro c ON c.idu=d.parcelle_idu
                 WHERE d.etiquette_dpe IN ('F','G','D','E') AND {MONO}),
            mut AS (SELECT id_parcelle idu, date_mutation::date dt FROM dvf_mutations_parcelle WHERE nature_mutation LIKE 'Vente%%'
                    UNION ALL SELECT id_parcelle, date_mutation::date FROM dvf_mutations_histo WHERE nature_mutation LIKE 'Vente%%')
            SELECT dpe.grp, count(DISTINCT dpe.idu) parcelles,
              count(*) FILTER (WHERE m.dt>=DATE '2021-01-01' AND m.dt<DATE '2024-07-01') avant,
              count(*) FILTER (WHERE m.dt>=DATE '2024-07-01') apres
            FROM dpe LEFT JOIN mut m ON m.idu=dpe.idu GROUP BY dpe.grp ORDER BY dpe.grp
        """)).mappings().all()
        print("\nJ1 event-study (mono, avant/après gel 1/7/2024) :")
        for r in j1:
            print(f"  {r['grp']}: {r['parcelles']} parcelles · {r['avant']} ventes avant · {r['apres']} après")

        j2 = s.execute(text(f"""
            WITH fg AS (SELECT d.parcelle_idu idu, min(d.date_etablissement) dt FROM dpe_records d
                        JOIN p_model_ext_copro c ON c.idu=d.parcelle_idu
                        WHERE d.etiquette_dpe IN ('F','G') AND {MONO} GROUP BY d.parcelle_idu),
            mut AS (SELECT id_parcelle idu, EXTRACT(YEAR FROM date_mutation)::int y FROM dvf_mutations_parcelle WHERE nature_mutation LIKE 'Vente%%')
            SELECT N.n fold,
              count(*) FILTER (WHERE EXTRACT(YEAR FROM fg.dt) < N.n) at_risk,
              count(*) FILTER (WHERE EXTRACT(YEAR FROM fg.dt) < N.n AND EXISTS (SELECT 1 FROM mut m WHERE m.idu=fg.idu AND m.y=N.n)) mut
            FROM fg CROSS JOIN (VALUES (2024),(2025)) N(n) GROUP BY N.n ORDER BY N.n
        """)).mappings().all()
        print("\nJ2 walk-forward as-of strict (passoire au 1/1/N = DPE F/G réalisé avant) :")
        for r in j2:
            print(f"  fold {r['fold']}: {r['at_risk']} at-risk · {r['mut']} mutation(s) dans l'année")
        print("\n→ Couverture anecdotique + juges sous-alimentés (≤ 8 ventes F/G, ≤ 2 événements walk-forward)"
              " : NO-GO composante V ; badge = fait réglementaire sourcé (décision Vic).")


if __name__ == "__main__":
    main()
