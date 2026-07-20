"""PHASE A-1 clôture — BASCULE PROTOCOLÉE du run servi vers `q_v7_defisc`.

Matérialise le nouveau run servi versionné `q_v7_defisc` = `q_v6_m8` (champion, INTOUCHÉ, gardé en
hystérésis pour rollback) + la composante V « fenêtre de sortie de défiscalisation ».

Convention de label : `q_v{N}_{tag}` — v7 = 7ᵉ version servie ; tag `defisc` = composante V ajoutée.
Le modèle P (M3.6 / m8, sha256 gelé) est INCHANGÉ ; V ne module que le rang (p_raw), jamais le tier.

Copie VERBATIM les tables clés-run (triplet gelé), SEUL `p_raw` est nudgé (+V_CAP) sur les 131 parcelles
défisc-actives ∩ mono ∩ non-écartées. `ia_cache` n'est PAS copié (cache — se régénère via CONTEXT_VERSION).
Idempotent (purge de la cible avant copie). `computed_at` de la cible = champion + 1 min → `q_v7_defisc`
devient le « dernier run » (champion de référence des prochains challengers).

Rollback : voir docs/mandats/A1_BASCULE_ROLLBACK.md (env LABUSE_SERVED_RUN=q_v6_m8 + VITE_RUN_LABEL + build).

Usage : python scripts/a1_bascule_v7.py
"""
from __future__ import annotations
import os
import sys
from sqlalchemy import text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from labuse.db import session_scope  # noqa: E402

SOURCE = "q_v6_m8"
TARGET = "q_v7_defisc"
V_CAP = 0.01
# tables clés-run à copier verbatim (hors p_score_v2_runs, traité à part) : (table, colonne_run)
TABLES = [
    ("dryrun_cascade_results", "run_label"),
    ("dryrun_parcel_evaluations", "run_label"),
    ("parcel_p_score_v2", "run_id"),
]


def _cols(session, table: str) -> list[str]:
    """Colonnes non-serial (on exclut la PK auto-incrémentée)."""
    rows = session.execute(text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = :t AND table_schema = 'public' "
        "AND (column_default IS NULL OR column_default NOT LIKE 'nextval%') "
        "ORDER BY ordinal_position"), {"t": table}).all()
    return [r[0] for r in rows]


def bascule(session) -> dict:
    # ensemble V : défisc-actif ∩ mono ∩ non-écarté dans le champion
    v_idus = [r[0] for r in session.execute(text(
        "SELECT s.parcelle_id FROM parcel_p_score_v2 s "
        "JOIN defisc_fenetres d ON d.idu = s.parcelle_id AND d.fenetre_active "
        "WHERE s.run_id = :src AND NOT s.copro AND s.tier <> 'ecartee'"), {"src": SOURCE}).all()]

    # purge cible (idempotence)
    for tbl, runcol in TABLES:
        session.execute(text(f"DELETE FROM {tbl} WHERE {runcol} = :t"), {"t": TARGET})
    session.execute(text("DELETE FROM p_score_v2_runs WHERE run_id = :t"), {"t": TARGET})

    counts = {}
    for tbl, runcol in TABLES:
        cols = _cols(session, tbl)
        select_exprs = []
        for c in cols:
            if c == runcol:
                select_exprs.append(":tgt")                                   # swap du label
            elif tbl == "parcel_p_score_v2" and c == "p_raw":
                select_exprs.append("p_raw + CASE WHEN parcelle_id = ANY(:vids) THEN :cap ELSE 0 END")
            else:
                select_exprs.append(c)
        sql = (f"INSERT INTO {tbl} ({', '.join(cols)}) "
               f"SELECT {', '.join(select_exprs)} FROM {tbl} WHERE {runcol} = :src")
        params = {"tgt": TARGET, "src": SOURCE}
        if tbl == "parcel_p_score_v2":
            params |= {"vids": v_idus, "cap": V_CAP}
        counts[tbl] = session.execute(text(sql), params).rowcount

    # header de run : computed_at POSTÉRIEUR au champion → q_v7_defisc devient le run de référence
    session.execute(text(
        "INSERT INTO p_score_v2_runs (run_id, model_version, model_sha256, params, n_parcelles, "
        " duration_s, snapshot_label, computed_at) "
        "SELECT :t, model_version, model_sha256, "
        "  COALESCE(params,'{}'::jsonb) || jsonb_build_object('bascule','v7_defisc','base',CAST(:src AS text),"
        "                                                     'v_cap',CAST(:cap AS double precision)), "
        "  n_parcelles, duration_s, 'servi_q_v7_defisc', computed_at + interval '1 minute' "
        "FROM p_score_v2_runs WHERE run_id = :src"), {"t": TARGET, "src": SOURCE, "cap": V_CAP})

    return {"v_parcelles": len(v_idus), **counts}


def main():
    with session_scope() as s:
        r = bascule(s)
    print(f"BASCULE → {TARGET} (base {SOURCE}, gardé en hystérésis) :")
    print(f"  composante V : {r['v_parcelles']} parcelles nudgées (+{V_CAP} p_raw), triplet gelé verbatim")
    for tbl, _ in TABLES:
        print(f"  {tbl:28s} : {r[tbl]:>10} lignes")
    print(f"\n  golden   : LABUSE_GOLDEN_RUN_LABEL={TARGET} python qa/golden_check.py")
    print(f"  baseline : labuse arene --challenger {TARGET} --champion {TARGET}")


if __name__ == "__main__":
    main()
