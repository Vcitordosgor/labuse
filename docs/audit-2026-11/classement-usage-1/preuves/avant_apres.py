"""CLASSEMENT-USAGE-1 — capture AVANT/APRÈS (texte, rejouable) des trois défauts + du tri par usage.

AVANT = valeur BRUTE telle que le run servi la stocke (ce que l'app servait avant le fix).
APRÈS = valeur SERVIE par la nouvelle lecture unique `potentiel_batir` / verdict_servi / tri.

Usage : PYTHONPATH=src ~/Desktop/labuse/.venv/bin/python docs/audit-2026-11/classement-usage-1/preuves/avant_apres.py
"""
from __future__ import annotations

from sqlalchemy import text

from labuse.db import session_scope
from labuse import verdict_servi
from labuse.faisabilite.potentiel_batir import potentiel_batir_batch
from labuse.api.app import FiltreCriteres, _q_v2_stats

RUN = "q_v20"


def main() -> None:
    with session_scope() as db:
        print("=" * 78)
        print("CLASSEMENT-USAGE-1 — AVANT / APRÈS (run servi", RUN + ")")
        print("=" * 78)

        # — Défaut 1 : SDP sur zone fermée (97422000AX1253, 2AUe) ——————————————
        idu = "97422000AX1253"
        brut = db.execute(text(
            "SELECT r.sdp_residuelle_m2 FROM parcel_residuel r JOIN parcels p ON p.id=r.parcel_id "
            "WHERE p.idu=:i"), {"i": idu}).scalar()
        pab = potentiel_batir_batch(db, [idu])[idu]
        print(f"\n[Défaut 1] SDP en zone fermée — {idu} (2AUe)")
        print(f"   AVANT  : SDP résiduelle servie = {brut} m²  (stockée sans cause au run)")
        print(f"   APRÈS  : SDP restante servie   = {pab['sdp_restante_m2']} m²  · "
              f"{pab['libelle']}")

        # — Défaut 3 : avertissement sur une « À suivre » non constructible —————
        print("\n[Défaut 3] Avertissement sur parcelle servable non constructible")
        for t in (idu, "97415000HL0033"):
            v = verdict_servi.verdict_servi(db, t)
            print(f"   {t} : palier={v['label']!r}")
            print(f"      AVANT  : aucun avertissement (piège silencieux NU4-D §2.2)")
            print(f"      APRÈS  : {v['avertissement']}")

        # — Tri par usage : AVANT (va se vendre) vs APRÈS (à construire) ————————
        print("\n[Tri par usage] Têtes de classement (île entière)")
        vv = _q_v2_stats(db, None, run_label=RUN)
        fc = FiltreCriteres(source=RUN, a_construire=True)
        extra, xp = fc.where()
        ac = _q_v2_stats(db, None, run_label=RUN, extra_where=extra, extra_params=xp)
        print(f"   « Va se vendre » (défaut, classement actuel) : {vv['total']:,} parcelles"
              .replace(",", " "))
        print(f"   « À construire » (zone ouverte + SDP > 0)    : {ac['total']:,} parcelles"
              .replace(",", " "))

        # — Top-100 lot D : combien de fausses affaires sortent de la tête ————————
        top = [r[0] for r in db.execute(text(
            "SELECT parcelle_id FROM parcel_p_score_v2 WHERE run_id=:r AND rang IS NOT NULL "
            "ORDER BY rang ASC LIMIT 100"), {"r": RUN}).all()]
        pots = potentiel_batir_batch(db, top)
        a_construire = sum(1 for i in top if not pots[i]["rien_a_batir"] and pots[i]["zone_ouverte"])
        print(f"\n[Top-100 lot D] en tri « À construire » :")
        print(f"   AVANT  : 100 têtes dont 34 fausses affaires (NU4-D : 22 zone fermée + 12 rien à bâtir)")
        print(f"   APRÈS  : {a_construire} têtes, toutes réellement constructibles "
              f"(0 zone fermée, 0 rien à bâtir)")


if __name__ == "__main__":
    main()
