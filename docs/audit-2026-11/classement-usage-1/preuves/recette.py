"""CLASSEMENT-USAGE-1 — recette rejouable. Rejoue les 100 premières parcelles du lot D (q_v20)
sous les deux tris, vérifie le gate « potentiel à bâtir » et le cas AX1253.

Usage : PYTHONPATH=src ~/Desktop/labuse/.venv/bin/python docs/audit-2026-11/classement-usage-1/preuves/recette.py
"""
from __future__ import annotations

import sys

from sqlalchemy import text

from labuse.db import session_scope
from labuse import runs
from labuse.faisabilite.potentiel_batir import potentiel_batir_batch
from labuse.api.app import _q_v2_list, FiltreCriteres, _q_v2_stats

RUN = "q_v20"
echecs: list[str] = []


def check(cond: bool, label: str) -> None:
    print(("  OK  " if cond else " ÉCHEC ") + label)
    if not cond:
        echecs.append(label)


def top100_idus(db) -> list[str]:
    return [r[0] for r in db.execute(text(
        "SELECT parcelle_id FROM parcel_p_score_v2 WHERE run_id=:r AND rang IS NOT NULL "
        "ORDER BY rang ASC LIMIT 100"), {"r": RUN}).all()]


def main() -> int:
    with session_scope() as db:
        print("runs.current() =", runs.current())
        top = top100_idus(db)

        # 1) gate potentiel à bâtir sur le top-100
        pot = potentiel_batir_batch(db, top)
        a_construire = [i for i in top if not pot[i]["rien_a_batir"] and pot[i]["zone_ouverte"]]
        fermees = [i for i in top if not pot[i]["zone_ouverte"]]
        rien = [i for i in top if pot[i]["zone_ouverte"] and pot[i]["rien_a_batir"]]
        print(f"\n[1] Top-100 lot D — à construire={len(a_construire)}, "
              f"zone fermée={len(fermees)}, rien à bâtir={len(rien)}")
        check(len(a_construire) == 66, "66 parcelles réellement à bâtir (= 66 plausibles NU4-D)")

        # 2) cas AX1253
        ax = pot.get("97422000AX1253") or potentiel_batir_batch(db, ["97422000AX1253"])["97422000AX1253"]
        print(f"\n[2] 97422000AX1253 : {ax}")
        check(ax["sdp_restante_m2"] == 0, "AX1253 — SDP restante servie = 0 (était 25 426)")
        check(ax["zone_ouverte"] is False and ax["rien_a_batir"] is True,
              "AX1253 — zone fermée, rien à bâtir")

        # 3) tri « À construire » (île entière, 150 têtes) : 0 fermée / 0 rien à bâtir en tête
        fc = FiltreCriteres(source=RUN, a_construire=True)
        extra, xp = fc.where()
        page_ac = _q_v2_list(db, None, 150, 0, run_label=RUN, extra_where=extra,
                             extra_params=xp, sort="rang")
        idus_ac = [r["idu"] for r in page_ac]
        pot_ac = potentiel_batir_batch(db, idus_ac)
        mauvais = [i for i in idus_ac if pot_ac[i]["rien_a_batir"] or not pot_ac[i]["zone_ouverte"]]
        print(f"\n[3] Tri « À construire » (tête de {len(idus_ac)}) — intrus (rien/fermée) = {len(mauvais)}")
        check(len(mauvais) == 0, "À construire — 0 parcelle sans rien à bâtir ni en zone fermée en tête")
        rangs = [r["rang_v2"] for r in page_ac if r["rang_v2"] is not None]
        check(rangs == sorted(rangs), "À construire — classé par probabilité de vente (rang croissant)")

        # 4) tri « Va se vendre » (défaut) = classement actuel servi, à l'identique. La référence
        # réplique le PÉRIMÈTRE servi (hors étage 0 du run de cascade + hors slivers < 2 m²), jamais
        # un rang nu — sinon on comparerait à un univers plus large que la liste n'a jamais servi.
        from labuse.api.app import _cascade_run, MIN_DISPLAY_SURFACE_M2
        casc = _cascade_run(db, RUN)
        page_vv = _q_v2_list(db, None, 200, 0, run_label=RUN, sort="rang")
        ref = [r[0] for r in db.execute(text(
            "SELECT s.parcelle_id FROM parcel_p_score_v2 s "
            "JOIN parcels p ON p.idu=s.parcelle_id "
            "JOIN dryrun_parcel_evaluations d ON d.parcel_id=p.id AND d.run_label=:casc "
            "WHERE s.run_id=:r AND s.rang IS NOT NULL "
            "  AND NOT (d.status IN ('exclue','faux_positif_probable')) "
            "  AND (p.surface_m2 IS NULL OR p.surface_m2 >= :ms) "
            "ORDER BY s.rang ASC LIMIT 200"),
            {"r": RUN, "casc": casc, "ms": MIN_DISPLAY_SURFACE_M2}).all()]
        got = [r["idu"] for r in page_vv][:200]
        print(f"\n[4] Tri « Va se vendre » — {len(got)} têtes comparées au classement servi")
        check(got == ref, "Va se vendre — classement identique au servi d'aujourd'hui (q_v20)")

        # 5) le compteur suit le filtre (carte = liste)
        stats_vv = _q_v2_stats(db, None, run_label=RUN)
        stats_ac = _q_v2_stats(db, None, run_label=RUN, extra_where=extra, extra_params=xp)
        print(f"\n[5] Compteur — va se vendre={stats_vv['total']} · à construire={stats_ac['total']}")
        check(0 < stats_ac["total"] < stats_vv["total"],
              "À construire — compteur strictement plus petit que l'univers (filtre actif)")

    print("\n" + ("TOUT VERT" if not echecs else f"{len(echecs)} ÉCHEC(S) : " + " | ".join(echecs)))
    return 1 if echecs else 0


if __name__ == "__main__":
    sys.exit(main())
