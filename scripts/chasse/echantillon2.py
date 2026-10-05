"""CHASSE-2 — tirage de l'échantillon NEUF (graine ≠ CHASSE-1, rejouable).

    python -m scripts.chasse.echantillon2            # écrit CHASSE-2/ECHANTILLON.csv (gelé)
    python -m scripts.chasse.echantillon2 --regenerer

Quatre blocs :
  · 200 parcelles stratifiées : mêmes strates que CHASSE-1 (24 communes × {U,AU,A,N} ×
    {nue,bâtie}) mais GRAINE NEUVE (0.77 vs 0.42) — parcelles différentes ;
  · ~300 parcelles pièges : les MÊMES classes que CHASSE-1 (SQL repris tel quel de
    scripts/chasse/echantillon.py), graine neuve ;
  · 3 classes propres au run 13 (mandat CHASSE-2) :
      - montee_0A        : les 20 plus fortes montées de bande 0 → A
                           (reports/scoring-9/montes_descentes.csv, sens=montée) ;
      - calculee_exigu   : 50 parcelles calculée (run 10, cause NULL) → terrain_exigu
                           (run 13) — les 50 de plus grande SDP run 10 (les plus « perdues ») ;
      - sdp_hausse_batie : 50 parcelles BÂTIES (parcel_filtre_bati) dont la SDP résiduelle
                           a le plus augmenté run 10 → run 13 (correction LiDAR à l'égout).

Lecture seule sur la base dev (SELECT uniquement). Sortie : CHASSE-2/ECHANTILLON.csv.
"""
from __future__ import annotations

import csv
import pathlib
import sys

import psycopg

from .echantillon import PIEGES, SQL_COMPLEMENT, SQL_STRATES, VIDES_DOCUMENTEES

RACINE = pathlib.Path(__file__).resolve().parents[2]
SORTIE = RACINE / "docs" / "audit-2026-10" / "CHASSE-2" / "ECHANTILLON.csv"
MONTEES = RACINE / "reports" / "scoring-9" / "montees_descentes.csv"
DSN = "postgresql://openclaw@localhost:5432/labuse"
GRAINE = 0.77  # ≠ 0.42 (CHASSE-1)

SQL_CALCULEE_EXIGU = """
SELECT p.idu, p.commune, 'sdp_run10=' || coalesce(r10.sdp_residuelle_m2::text, '?')
FROM parcel_residuel_runs r10
JOIN parcel_residuel_runs r13 ON r13.parcel_id = r10.parcel_id AND r13.run_seq = 13
JOIN parcels p ON p.id = r10.parcel_id
WHERE r10.run_seq = 10 AND r10.cause IS NULL AND r13.cause = 'terrain_exigu'
ORDER BY r10.sdp_residuelle_m2 DESC NULLS LAST, p.idu
LIMIT 50
"""

SQL_SDP_HAUSSE_BATIE = """
SELECT p.idu, p.commune,
       'sdp ' || coalesce(r10.sdp_residuelle_m2::text, '∅') || '→'
               || coalesce(r13.sdp_residuelle_m2::text, '∅')
FROM parcel_residuel_runs r10
JOIN parcel_residuel_runs r13 ON r13.parcel_id = r10.parcel_id AND r13.run_seq = 13
JOIN parcels p ON p.id = r10.parcel_id
JOIN parcel_filtre_bati fb ON fb.parcel_id = p.id
WHERE r10.run_seq = 10
  AND r13.sdp_residuelle_m2 IS NOT NULL AND r10.sdp_residuelle_m2 IS NOT NULL
ORDER BY (r13.sdp_residuelle_m2 - r10.sdp_residuelle_m2) DESC, p.idu
LIMIT 50
"""


def main() -> None:
    if SORTIE.exists() and "--regenerer" not in sys.argv:
        print(f"déjà tiré (gelé) : {SORTIE} — --regenerer pour refaire")
        return
    conn = psycopg.connect(DSN, options="-c statement_timeout=600000")
    cur = conn.cursor()
    cur.execute("SELECT setseed(%s)", (GRAINE,))
    sel = str(GRAINE)

    import json
    manifeste = json.loads((RACINE / "config" / "served_manifest.json").read_text())
    v2run = manifeste["scoring_run"]
    cur.execute("SELECT 1 FROM p_score_v2_runs WHERE run_id = %s", (v2run,))
    assert cur.fetchone(), f"run servi {v2run} absent de p_score_v2_runs"
    print(f"run v2 pris pour top/flop : {v2run}")

    vus: set[str] = set()
    lignes: list[dict] = []

    def ajouter(idu, commune, bloc, classe, detail=""):
        if idu in vus:
            return
        vus.add(idu)
        lignes.append({"idu": idu, "commune": commune, "bloc": bloc,
                       "classe": classe, "detail": detail})

    # bloc run13 d'abord (les classes du mandat, jamais dédoublonnées ailleurs)
    with open(MONTEES, newline="") as f:
        for r in csv.DictReader(f):
            if r["sens"] == "montée":
                ajouter(r["idu"], r["commune"], "run13", "montee_0A",
                        f"score {r['score_qv15']}→{r['score_qv16']}")
    for classe, sql in (("calculee_exigu", SQL_CALCULEE_EXIGU),
                        ("sdp_hausse_batie", SQL_SDP_HAUSSE_BATIE)):
        cur.execute(sql)
        n = 0
        for idu, commune, detail in cur.fetchall():
            ajouter(idu, commune, "run13", classe, detail)
            n += 1
        print(f"  {classe}: {n} tirées")

    # bloc 1 : stratifiées (graine neuve)
    cur.execute(SQL_STRATES, {"sel": sel})
    for idu, commune, fam, batie in cur.fetchall():
        ajouter(idu, commune, "stratifie", f"{fam}_{'batie' if batie else 'nue'}")
    manque = 200 - sum(1 for l in lignes if l["bloc"] == "stratifie")
    if manque > 0:
        cur.execute(SQL_COMPLEMENT, {"deja": list(vus), "sel": sel, "n": manque})
        for idu, commune, fam, batie in cur.fetchall():
            ajouter(idu, commune, "stratifie", f"{fam}_{'batie' if batie else 'nue'}_cplt")

    # bloc 2 : pièges (mêmes classes que CHASSE-1, graine neuve)
    for classe, sql in PIEGES:
        cur.execute("SELECT setseed(%s)", (GRAINE,))
        try:
            cur.execute(sql, {"v2run": v2run})
            rows = cur.fetchall()
        except Exception as e:  # noqa: BLE001 — une classe qui casse est un résultat
            conn.rollback()
            print(f"  ! classe {classe} : {e}")
            continue
        n = 0
        for row in rows:
            ajouter(row[0], row[1], "piege", classe)
            n += 1
        print(f"  {classe}: {n} tirées ({len(rows)} candidates)")
    for classe, motif in VIDES_DOCUMENTEES.items():
        lignes.append({"idu": "", "commune": "", "bloc": "piege",
                       "classe": classe, "detail": f"CLASSE VIDE au tirage CHASSE-1 — {motif} "
                                                   "(re-vérifiée par CHASSE-2 invariants2)"})

    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    with open(SORTIE, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["idu", "commune", "bloc", "classe", "detail"])
        w.writeheader()
        w.writerows(lignes)
    reels = [l for l in lignes if l["idu"]]
    par_bloc = {}
    for l in reels:
        par_bloc[l["bloc"]] = par_bloc.get(l["bloc"], 0) + 1
    print(f"\n{len(reels)} parcelles ({len(set(l['idu'] for l in reels))} uniques, "
          f"{par_bloc}) → {SORTIE}")
    conn.close()


if __name__ == "__main__":
    main()
