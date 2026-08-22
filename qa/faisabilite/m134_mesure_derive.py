"""M134 Phase C-échantillon — mesure READ-ONLY de la dérive de parcel_residuel.

Recalcule `compute_residuel()` (fonction PURE, aucune écriture) en direct sur un
échantillon et compare au cache servi. AUCUNE écriture, AUCUNE bascule. Chronométré
pour extrapoler le coût île entière (inconnue de A.2).

Échantillon : 7 ancres + toutes les zones M131 (Us + 2AUa-e) + 500/lot d'écriture
(29/07·05/08·19/08) stratifié par commune + 300 du vivier scoring servi.
"""
from __future__ import annotations

import os
import time
from collections import defaultdict
from statistics import median

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from labuse.faisabilite.residuel import compute_residuel

RUN = "q_v10_m129"
ANCHORS = ["97416000EP1044", "97422000BI1097", "97415000CW1056", "97422000BV2471",
           "97422000EL0368", "97422000CN1677", "97422000BT0960"]
eng = create_engine(os.environ["LABUSE_DATABASE_URL"])


def _after_sdp(d: dict):
    """SDP que le batch ÉCRIRAIT (mêmes règles que compute_residuel_batch)."""
    if d.get("disponible"):
        return d.get("sdp_residuelle_m2"), (d.get("capacite_estimee")), None
    return d.get("sdp_ecrite"), None, d.get("cause")


def collect_sample(c) -> dict:
    """→ {parcel_id: (idu, commune, strate, lot)}. Un parcel_id peut couvrir plusieurs strates :
    on garde la 1ʳᵉ (priorité ancre > M131 > lot > conso)."""
    sample: dict = {}

    def add(pid, idu, commune, strate, lot):
        if pid not in sample:
            sample[pid] = (idu, commune, strate, lot)

    lot_of = dict(c.execute(text(
        "SELECT parcel_id, computed_at::date::text FROM parcel_residuel")).all())

    for idu in ANCHORS:
        r = c.execute(text("SELECT p.id, p.commune FROM parcels p WHERE p.idu=:i"), {"i": idu}).first()
        if r:
            add(r[0], idu, r[1], "ancre", lot_of.get(r[0]))

    # zones M131 : Us (Saint-Pierre) + 2AUa-e (Le Tampon), toutes
    for pid, idu, com in c.execute(text("""
            SELECT p.id, p.idu, p.commune FROM parcel_zone_plu z JOIN parcels p ON p.idu=z.idu
            WHERE (z.zone_lib='Us' AND p.commune ILIKE '%Pierre%')
               OR (z.zone_lib LIKE '2AU%' AND p.commune ILIKE '%Tampon%')""")).all():
        add(pid, idu, com, "m131", lot_of.get(pid))

    # lot × commune : 500/lot réparti au prorata commune (plancher 3), spread déterministe md5
    for lot in ("2026-07-29", "2026-08-05", "2026-08-19"):
        tot = c.execute(text("SELECT count(*) FROM parcel_residuel WHERE computed_at::date=:l"),
                        {"l": lot}).scalar()
        rows = c.execute(text("""
            SELECT p.commune, count(*) n FROM parcel_residuel r JOIN parcels p ON p.id=r.parcel_id
            WHERE r.computed_at::date=:l GROUP BY p.commune"""), {"l": lot}).all()
        for commune, n in rows:
            k = max(3, round(500 * n / tot))
            for pid, idu in c.execute(text("""
                    SELECT p.id, p.idu FROM parcel_residuel r JOIN parcels p ON p.id=r.parcel_id
                    WHERE r.computed_at::date=:l AND p.commune=:c
                    ORDER BY md5(p.id::text) LIMIT :k"""), {"l": lot, "c": commune, "k": k}).all():
                add(pid, idu, commune, f"lot:{lot}", lot)

    # consommateurs sensibles : 300 du vivier scoring servi (tier admis + résiduel>0)
    for pid, idu, com in c.execute(text("""
            SELECT p.id, p.idu, p.commune FROM parcels p
            JOIN parcel_residuel r ON r.parcel_id=p.id AND r.sdp_residuelle_m2>0
            JOIN parcel_p_score_v2 s2 ON s2.parcelle_id=p.idu AND s2.run_id=:run
              AND s2.tier IN ('brulante','chaude','reserve_fonciere','a_creuser')
            ORDER BY md5(p.id::text) LIMIT 300"""), {"run": RUN}).all():
        add(pid, idu, com, "conso", lot_of.get(pid))
    return sample


def main():
    with Session(eng) as db:
        sample = collect_sample(db)
        before = {pid: (r.sdp_residuelle_m2, r.cause, r.capacite_estimee)
                  for pid, r in [(pid, db.execute(text(
                      "SELECT sdp_residuelle_m2, cause, capacite_estimee FROM parcel_residuel WHERE parcel_id=:p"),
                      {"p": pid}).first()) for pid in sample]}
        by_strate = defaultdict(lambda: {"n": 0, "changed": 0, "deltas": [], "motifs": defaultdict(int)})
        t_constr, t_nonconstr = [], []
        anchors_out = []
        conso_changed = 0
        for pid, (idu, commune, strate, lot) in sample.items():
            b_sdp, b_cause, b_est = before[pid]
            t0 = time.perf_counter()
            d = compute_residuel(db, pid)
            dt = time.perf_counter() - t0
            a_sdp, a_est, a_cause = _after_sdp(d)
            (t_constr if d.get("disponible") else t_nonconstr).append(dt)
            s = by_strate[strate.split(":")[0] if strate.startswith("lot") else strate]
            # regroupe les 3 lots sous 'lot' ET garde le détail par lot
            for key in ({strate} | ({f"lot:{lot}"} if lot and strate == "conso" else set())):
                pass
            st = by_strate[strate]
            st["n"] += 1
            changed = (b_sdp != a_sdp) or (b_cause != a_cause)
            if changed:
                st["changed"] += 1
                if b_sdp is not None and a_sdp is not None:
                    st["deltas"].append(a_sdp - b_sdp)
                motif = f"{'sdp' if b_sdp != a_sdp else ''}{'+cause' if b_cause != a_cause else ''}"
                st["motifs"][motif or "autre"] += 1
                if strate == "conso":
                    conso_changed += 1
            if strate == "ancre":
                anchors_out.append((idu, commune, lot, b_sdp, a_sdp, b_cause, a_cause, b_est, a_est,
                                    d.get("disponible")))

    def stats(xs):
        if not xs:
            return "—"
        xs = sorted(xs)
        p90 = xs[min(len(xs) - 1, int(0.9 * len(xs)))]
        return f"med={median(xs):+.0f} p90={p90:+.0f} max={max(xs, key=abs):+.0f} (n={len(xs)})"

    print("===== DÉRIVE PAR STRATE =====")
    for strate in sorted(by_strate):
        s = by_strate[strate]
        pct = 100 * s["changed"] / s["n"] if s["n"] else 0
        top = sorted(s["motifs"].items(), key=lambda x: -x[1])[:3]
        print(f"  {strate:16} n={s['n']:5} changées={s['changed']:5} ({pct:5.1f}%)  Δsdp {stats(s['deltas'])}  motifs {dict(top)}")

    print("\n===== ANCRES (une à une) =====")
    for idu, com, lot, bs, as_, bc, ac, be, ae, dispo in anchors_out:
        flag = "≠" if (bs != as_ or bc != ac) else "="
        print(f"  {idu} {com:13} lot {lot} : sdp {bs}→{as_} {flag} cause {bc!r}→{ac!r} estimee {be}→{ae} dispo={dispo}")

    print("\n===== CONSOMMATEURS (vivier scoring) =====")
    cs = by_strate.get("conso", {})
    print(f"  {cs.get('n',0)} parcelles, {conso_changed} verraient leur résiduel/feature bouger "
          f"({100*conso_changed/max(1,cs.get('n',0)):.1f}%)")

    print("\n===== TIMING (extrapolation coût île) =====")
    for lab, xs in (("constructible", t_constr), ("non-constructible", t_nonconstr)):
        if xs:
            print(f"  {lab:18} n={len(xs)} médiane={1000*median(xs):.1f} ms/parcelle")
    # île : 431663 dont ~130k disponibles (constructible) + ~300k non
    if t_constr and t_nonconstr:
        est = 130370 * median(t_constr) + (431663 - 130370) * median(t_nonconstr)
        print(f"  → extrapolation île entière ≈ {est/60:.0f} min (séquentiel, 1 process)")


if __name__ == "__main__":
    main()
