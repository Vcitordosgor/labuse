"""SCORING-9 lot C — re-caler les 30 témoins sur le résiduel run 13 servi, remplacer les 3
témoins périmés, rejouer les invariants, et décider si le barème peut être GRAVÉ.

Les 3 périmés (constat EXPLIQUE-RUN13 / mandat SCORING-9) :
  · 97404000AX0047 (bonne, L'Étang-Salé) — touche du PPR rouge → assiette déduite → SDP effondrée.
  · 97409000AY0786 (bonne, Saint-André)  — 2243→0 m² (terrain_exigu, enveloppe PPR).
  · 97411000CP0427 (mauvaise, Saint-Denis) — SDP recalculée (LiDAR) → 21→45 (> 25).

Invariants (SCORING-7 §1, décisions Vic) : bonnes ≥ 80 (sauf cas d'école AB0798, lame bâtie
64), mauvaises ≤ 25, pas d'inversion (pire bonne ≥ meilleure mauvaise), aucune NC à 0.

Modes :
  diag                     : score les 30 témoins canoniques sur le run servi, flag les cassés.
  candidats                : liste des remplaçants candidats (scorés run 13), par catégorie.
  check <temoins.csv>      : rejoue les invariants sur un jeu de témoins donné (défaut : le
                             jeu SCORING-9 reports/scoring-9/TEMOINS.csv s'il existe).

Usage : DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib PYTHONPATH=<worktree>/src \
        python scripts/audit/scoring/scoring9_temoins.py diag
"""
from __future__ import annotations

import csv
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

CASCADE = os.environ.get("S9_CASCADE", "q_v13_sources1")
TEMOINS_CANON = ROOT / "reports" / "scoring-5" / "TEMOINS.csv"
TEMOINS_S9 = ROOT / "reports" / "scoring-9" / "TEMOINS.csv"
AB0798 = "97411000AB0798"            # cas d'école exempté du seuil 80
PERIMES = {"97404000AX0047", "97409000AY0786", "97411000CP0427"}


def _load_temoins(path: Path) -> dict[str, dict]:
    return {r["idu"]: r for r in csv.DictReader(path.open())}


def _score_idus(s, idus):
    from sqlalchemy import text

    from labuse.scoring.score_labuse import score_batch
    ids = {r[1]: r[0] for r in s.execute(
        text("SELECT id, idu FROM parcels WHERE idu = ANY(:i)"), {"i": list(idus)})}
    scores = {sc.idu: sc for sc in score_batch(
        s, [ids[i] for i in idus if i in ids], "scoring9_temoins", cascade_label=CASCADE)}
    return scores


def _invariants(cat: dict[str, str], scores) -> list[str]:
    anomalies, par_cat = [], {"bonne": [], "mauvaise": []}
    for idu, c in cat.items():
        sc = scores.get(idu)
        if sc is None:
            anomalies.append(f"{idu} : absente de la base")
            continue
        if sc.non_calculable:
            if sc.score == 0:
                anomalies.append(f"{idu} : NC à 0 (interdit)")
            continue
        if c in par_cat:
            par_cat[c].append(sc.score)
        if c == "bonne" and idu != AB0798 and sc.score < 80:
            anomalies.append(f"{idu} : bonne mais {sc.score} < 80")
        if c == "mauvaise" and sc.score > 25:
            anomalies.append(f"{idu} : mauvaise mais {sc.score} > 25")
    m = par_cat["mauvaise"]
    # inversion : exclure le cas d'école AB0798 (64) de la « pire bonne »
    bonnes_hors_ecole = [v for idu, v in
                         ((i, scores[i].score) for i in cat
                          if cat[i] == "bonne" and i in scores and not scores[i].non_calculable)
                         if idu != AB0798]
    if bonnes_hors_ecole and m and min(bonnes_hors_ecole) < max(m):
        anomalies.append(f"inversion : pire bonne {min(bonnes_hors_ecole)} < meilleure mauvaise {max(m)}")
    return anomalies


def mode_diag(s) -> int:
    cat = {i: r["categorie"] for i, r in _load_temoins(TEMOINS_CANON).items()}
    scores = _score_idus(s, list(cat))
    print(f"{'IDU':<16}{'cat':<9}{'score':>6} {'bande':<5} {'cause':<22} note")
    for idu, c in cat.items():
        sc = scores.get(idu)
        if sc is None:
            print(f"{idu:<16}{c:<9}  (absente)"); continue
        note = ""
        if idu in PERIMES:
            note = "← périmé (à remplacer)"
        print(f"{idu:<16}{c:<9}{str(sc.score):>6} {sc.bande:<5} {str(sc.cause or '')[:22]:<22} {note}")
    anomalies = _invariants(cat, scores)
    print("\n=== INVARIANTS (jeu canonique sur run 13) ===")
    for a in anomalies:
        print(f"  ⛔ {a}")
    print(f"  → {len(anomalies)} anomalie(s) (attendu : les 3 périmés).")
    return 0


def mode_candidats(s) -> int:
    from sqlalchemy import text
    print("Recherche de remplaçants (scorés sur le run 13 servi)…\n")
    # 2 « bonnes » : U quasi nue, grande SDP, cause calculée (donc PAS écrasée par PPR), emprise basse,
    #                pente douce → score ≥ 80 garanti. On vise les mêmes communes que les périmés.
    for commune, insee in (("L'Étang-Salé", "97404"), ("Saint-André", "97409")):
        rows = s.execute(text("""
            SELECT p.idu, r.sdp_residuelle_m2 AS sdp, r.taux_emprise_pct AS emp, r.cause,
                   tr.pente_moy_deg AS pente
            FROM parcels p
            JOIN parcel_residuel r ON r.parcel_id = p.id
            LEFT JOIN LATERAL (SELECT max(t0.pente_moy_deg) pente_moy_deg
                               FROM parcel_terrain t0 WHERE t0.idu = p.idu) tr ON TRUE
            WHERE substring(p.idu for 5) = :insee
              AND coalesce(r.cause,'') = ''
              AND r.sdp_residuelle_m2 >= 2000
              AND coalesce(r.taux_emprise_pct,0) <= 15
              AND coalesce(tr.pente_moy_deg,0) <= 9
            ORDER BY r.sdp_residuelle_m2 DESC
            LIMIT 6"""), {"insee": insee}).all()
        print(f"— BONNE candidate · {commune} ({insee}) —")
        for r in rows:
            print(f"    {r.idu}  SDP={int(r.sdp)}  emp={r.emp}  pente={r.pente}")
        # score des candidats
        cand = {r.idu: "bonne" for r in rows}
        sc = _score_idus(s, list(cand))
        for idu in cand:
            x = sc.get(idu)
            if x:
                print(f"       → {idu} score={x.score} bande={x.bande} "
                      f"coef={x.details.get('coef')} f_bati={x.details.get('f_bati')}")
        print()
    # 1 « mauvaise » : petite SDP sur forte pente à Saint-Denis, score ≤ 25 (profil CP0427 d'origine).
    rows = s.execute(text("""
        SELECT p.idu, r.sdp_residuelle_m2 AS sdp, r.taux_emprise_pct AS emp, r.cause,
               tr.pente_moy_deg AS pente
        FROM parcels p
        JOIN parcel_residuel r ON r.parcel_id = p.id
        LEFT JOIN LATERAL (SELECT max(t0.pente_moy_deg) pente_moy_deg
                           FROM parcel_terrain t0 WHERE t0.idu = p.idu) tr ON TRUE
        WHERE substring(p.idu for 5) = '97411'
          AND coalesce(r.cause,'') = ''
          AND r.sdp_residuelle_m2 > 0 AND r.sdp_residuelle_m2 <= 120
          AND tr.pente_moy_deg >= 38
        ORDER BY tr.pente_moy_deg DESC
        LIMIT 10"""), {}).all()
    print("— MAUVAISE candidate · Saint-Denis (97411), SDP ≤ 120 m² sur pente ≥ 38° —")
    cand = {r.idu: "mauvaise" for r in rows}
    sc = _score_idus(s, list(cand))
    for r in rows:
        x = sc.get(r.idu)
        print(f"    {r.idu}  SDP={int(r.sdp)}  pente={round(r.pente,1)}°  "
              f"→ score={x.score if x else '?'} bande={x.bande if x else '?'}")
    return 0


def mode_check(s, path: Path) -> int:
    if not path.exists():
        print(f"⛔ jeu de témoins absent : {path}")
        return 1
    cat = {i: r["categorie"] for i, r in _load_temoins(path).items()}
    scores = _score_idus(s, list(cat))
    print(f"Jeu : {path.name} ({len(cat)} témoins) sur run 13 servi\n")
    print(f"{'IDU':<16}{'cat':<9}{'score':>6} {'bande':<5} {'cause':<24}")
    for idu, c in cat.items():
        sc = scores.get(idu)
        if sc is None:
            print(f"{idu:<16}{c:<9}  (absente)"); continue
        print(f"{idu:<16}{c:<9}{str(sc.score):>6} {sc.bande:<5} {str(sc.cause or '')[:24]:<24}")
    anomalies = _invariants(cat, scores)
    print("\n=== INVARIANTS ===")
    if anomalies:
        for a in anomalies:
            print(f"  ⛔ {a}")
        print("→ NE RIEN GRAVER. Expliquer la cause.")
        return 1
    print("  ✓ bonnes ≥ 80 (sauf AB0798), mauvaises ≤ 25, pas d'inversion, aucune NC à 0.")
    print("  → GRAVURE du barème autorisée (geste manuel, run 13 servi).")
    return 0


def main() -> None:
    os.environ.setdefault(
        "LABUSE_DATABASE_URL", "postgresql+psycopg://openclaw@localhost:5432/labuse")
    from labuse.db import session_scope
    mode = sys.argv[1] if len(sys.argv) > 1 else "diag"
    with session_scope() as s:
        if mode == "diag":
            rc = mode_diag(s)
        elif mode == "candidats":
            rc = mode_candidats(s)
        elif mode == "check":
            path = Path(sys.argv[2]) if len(sys.argv) > 2 else TEMOINS_S9
            rc = mode_check(s, path)
        else:
            print(f"mode inconnu : {mode}"); rc = 1
    sys.exit(rc)


if __name__ == "__main__":
    main()
