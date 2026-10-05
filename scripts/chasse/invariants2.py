"""CHASSE-2 angle 2 — invariants du SCORING q_v16 (en plus des 29 de CHASSE-1, rejoués par
`python -m scripts.chasse.invariants`).

    python -m scripts.chasse.invariants2       # → docs/audit-2026-10/CHASSE-2/INVARIANTS2.csv

Mandat CHASSE-2 : bande cohérente avec le score (seuils GRAVÉS de config/score_labuse.yaml :
A ≥ 80, B ≥ 50, C ≥ 30, D = 1-29, « 0 » = score exactement 0, NC = score NULL) ; NC jamais 0 ;
0 jamais D ; bande « 0 » ⇔ SDP 0 ou cause ; le score gravé reflète le run résiduel servi (13).
Les deux invariants de LIBELLÉ (capacite_differee ⇒ « différé » partout, terrain_exigu ⇒ la
vraie raison nommée) sont joués sur l'échantillon par `scripts.chasse.libelles2` (fiche servie).

Lecture seule (SELECT uniquement). Le run scoring contrôlé = celui du manifeste servi.
"""
from __future__ import annotations

import csv
import json
import pathlib

import psycopg

RACINE = pathlib.Path(__file__).resolve().parents[2]
SORTIE = RACINE / "docs" / "audit-2026-10" / "CHASSE-2" / "INVARIANTS2.csv"
DSN = "postgresql://openclaw@localhost:5432/labuse"

MANIFESTE = json.loads((RACINE / "config" / "served_manifest.json").read_text())
RUN = MANIFESTE["scoring_run"]              # q_v16
SEQ = MANIFESTE["residuel_run_seq"]         # 13

INVARIANTS: list[tuple[str, str, str, str]] = [
    ("bande_coherente_score",
     "bande = f(score) avec les seuils gravés (A≥80, B≥50, C≥30, D=1-29, 0=0, NC=score NULL)",
     f"score_labuse run {RUN} (île)",
     """SELECT idu, format('score=%%s bande=%%s attendu=%%s', score, bande,
            CASE WHEN score IS NULL THEN 'NC' WHEN score = 0 THEN '0'
                 WHEN score >= 80 THEN 'A' WHEN score >= 50 THEN 'B'
                 WHEN score >= 30 THEN 'C' ELSE 'D' END)
        FROM score_labuse WHERE run_label = %(run)s
        AND bande IS DISTINCT FROM (
            CASE WHEN score IS NULL THEN 'NC' WHEN score = 0 THEN '0'
                 WHEN score >= 80 THEN 'A' WHEN score >= 50 THEN 'B'
                 WHEN score >= 30 THEN 'C' ELSE 'D' END)"""),

    ("nc_jamais_0",
     "non calculable ⇒ bande NC avec cause dite, JAMAIS la bande « 0 » (et réciproque : NC ⇒ non_calculable + score NULL)",
     f"score_labuse run {RUN} (île)",
     """SELECT idu, format('bande=%%s non_calculable=%%s score=%%s cause=%%s',
                           bande, non_calculable, score, coalesce(cause,'NULL'))
        FROM score_labuse WHERE run_label = %(run)s
        AND ((non_calculable AND bande IS DISTINCT FROM 'NC')
          OR (bande = 'NC' AND (NOT coalesce(non_calculable, false)
                                OR score IS NOT NULL OR cause IS NULL)))"""),

    ("zero_jamais_d",
     "score = 0 ⇒ bande « 0 » (jamais D) ; bande « 0 » ⇒ score = 0",
     f"score_labuse run {RUN} (île)",
     """SELECT idu, format('score=%%s bande=%%s', score, bande)
        FROM score_labuse WHERE run_label = %(run)s
        AND ((score = 0 AND bande IS DISTINCT FROM '0')
          OR (bande = '0' AND score IS DISTINCT FROM 0))"""),

    ("bande0_sdp_ou_cause",
     "bande « 0 » ⇔ SDP résiduelle 0 ou cause posée (run résiduel servi) — jamais un 0 muet sur une parcelle à SDP > 0",
     f"score_labuse run {RUN} × parcel_residuel_runs seq {SEQ}",
     """SELECT sl.idu, format('bande=0 sdp_run=%%s cause_run=%%s sdp_score=%%s',
                              coalesce(r.sdp_residuelle_m2::text,'∅'),
                              coalesce(r.cause,'NULL'),
                              coalesce(sl.sdp_residuelle_m2::text,'∅'))
        FROM score_labuse sl
        JOIN parcel_residuel_runs r ON r.parcel_id = sl.parcel_id AND r.run_seq = %(seq)s
        WHERE sl.run_label = %(run)s AND sl.bande = '0'
          AND NOT (coalesce(r.sdp_residuelle_m2, 0) = 0 OR r.cause IS NOT NULL)"""),

    ("score_grave_reflete_run13",
     "la SDP portée par le score gravé = la SDP du run résiduel servi (pas un run périmé) — "
     "hors bande NC (mesuré : les 10 776 NC portent sdp NULL côté score et 0+cause côté run, "
     "vocabulaire d'absence attendu, pas une contradiction)",
     f"score_labuse run {RUN} × parcel_residuel_runs seq {SEQ}",
     """SELECT sl.idu, format('sdp_score=%%s sdp_run13=%%s',
                              coalesce(sl.sdp_residuelle_m2::text,'∅'),
                              coalesce(r.sdp_residuelle_m2::text,'∅'))
        FROM score_labuse sl
        JOIN parcel_residuel_runs r ON r.parcel_id = sl.parcel_id AND r.run_seq = %(seq)s
        WHERE sl.run_label = %(run)s AND sl.bande <> 'NC'
          AND sl.sdp_residuelle_m2 IS DISTINCT FROM r.sdp_residuelle_m2"""),

    ("score_couvre_ile",
     "le run scoring servi couvre toute l'île (même compte que parcels), 0 manquant / 0 orphelin",
     f"score_labuse run {RUN} vs parcels",
     """SELECT coalesce(p.idu, 'orphelin:'||sl.parcel_id), 'présent d''un seul côté'
        FROM parcels p
        FULL OUTER JOIN (SELECT parcel_id, idu FROM score_labuse WHERE run_label = %(run)s) sl
          ON sl.parcel_id = p.id
        WHERE p.id IS NULL OR sl.parcel_id IS NULL"""),

    ("bande_servie_est_q_v16",
     "garde-fou harnais : le manifeste pointe bien q_v16 (sinon tout l'angle contrôle le mauvais run)",
     "config/served_manifest.json",
     """SELECT 'manifeste', 'scoring_run='||%(run)s WHERE %(run)s <> 'q_v16'"""),
]


def main() -> None:
    conn = psycopg.connect(DSN, options="-c statement_timeout=600000")
    cur = conn.cursor()
    lignes = []
    for inv, lib, perim, sql in INVARIANTS:
        try:
            cur.execute(sql, {"run": RUN, "seq": SEQ})
            rows = cur.fetchmany(100000)
        except Exception as e:  # noqa: BLE001
            conn.rollback()
            lignes.append({"invariant": inv, "libelle": lib, "perimetre": perim,
                           "violations": "ERREUR", "exemples": str(e)[:200]})
            print(f"  ! {inv}: {e}")
            continue
        ex = "; ".join(f"{r[0]} ({r[1]})" for r in rows[:5])
        n = len(rows)
        suffixe = " [≥100000 : tronqué]" if n == 100000 else ""
        lignes.append({"invariant": inv, "libelle": lib, "perimetre": perim,
                       "violations": n, "exemples": ex + suffixe})
        print(f"  {inv}: {n} violation(s)")
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    with open(SORTIE, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["invariant", "libelle", "perimetre",
                                          "violations", "exemples"])
        w.writeheader()
        w.writerows(lignes)
    print(f"→ {SORTIE}")
    conn.close()


if __name__ == "__main__":
    main()
