#!/usr/bin/env python
"""SOLAIRE M1 — test témoin : le builder reconstruit produit-il les MÊMES ORDRES DE GRANDEUR que la
donnée gelée (11/07/2026) sur 100 parcelles témoins ? Pas l'identique — les sources (SARAH3) ont bougé.

Compare `qa/solaire/temoins_geles.json` (snapshot AVANT reconstruction) au `parcel_solar` courant.
Règle (exigence Vic) : si une parcelle diverge FORT (> 20 % sur le productible), on la NOMME avec sa
cause probable — on ne lisse pas. Code retour 0 si la MÉDIANE des écarts ≤ 20 % (ordre de grandeur
tenu), 1 sinon. Les divergences individuelles > 20 % sont TOUJOURS listées (informatif), jamais un échec
en soi (une maille de grille peut légitimement bouger).

Usage : LABUSE_DATABASE_URL=… .venv/bin/python qa/solaire/temoin.py
"""
from __future__ import annotations

import json
import os
import statistics
import sys

from sqlalchemy import create_engine, text

SNAP = os.path.join(os.path.dirname(__file__), "temoins_geles.json")
URL = os.environ.get("LABUSE_DATABASE_URL", "postgresql+psycopg://openclaw@localhost:5432/labuse")
if URL.startswith("postgresql://"):   # forcer le driver psycopg3 (psycopg2 n'est pas installé)
    URL = URL.replace("postgresql://", "postgresql+psycopg://", 1)


def main() -> int:
    temoins = json.load(open(SNAP))
    eng = create_engine(URL)
    ecarts: list[float] = []
    diverg: list[dict] = []
    with eng.connect() as c:
        for t in temoins:
            r = c.execute(text(
                "SELECT prod_spec_kwh_kwc, flag_topo_ombrage, source_millesime "
                "FROM parcel_solar WHERE idu = :i"), {"i": t["idu"]}).mappings().first()
            if not r or r["prod_spec_kwh_kwc"] is None:
                diverg.append({**t, "cause": "absente/NULL dans le parcel_solar reconstruit"})
                continue
            gel = float(t["prod_gel"])
            fresh = float(r["prod_spec_kwh_kwc"])
            pct = 100.0 * (fresh - gel) / gel if gel else 0.0
            ecarts.append(abs(pct))
            if abs(pct) > 20.0:
                # cause probable, factuelle — jamais lissée
                cause = ("point de grille voisin différent (IDW) ; "
                         + ("ombrage topo PVGIS actif" if r["flag_topo_ombrage"]
                            else "zone sans ombrage — révision SARAH3 probable"))
                diverg.append({"idu": t["idu"], "insee": t["insee"], "prod_gel": round(gel),
                               "prod_fresh": round(fresh), "ecart_pct": round(pct, 1), "cause": cause})
    med = statistics.median(ecarts) if ecarts else 999.0
    p90 = statistics.quantiles(ecarts, n=10)[-1] if len(ecarts) >= 10 else max(ecarts, default=999.0)
    mil = "?"
    with eng.connect() as c:
        mm = c.execute(text("SELECT source_millesime FROM parcel_solar WHERE source_millesime IS NOT NULL LIMIT 1")).scalar()
        mil = mm or "?"
    print(f"Témoins : {len(temoins)} · comparés : {len(ecarts)} · millésime frais : {mil}")
    print(f"Écart |%| productible vs gelé — médiane {med:.1f} % · p90 {p90:.1f} %")
    print(f"Divergences > 20 % : {len(diverg)}")
    for d in diverg:
        print(f"  · {d['idu']} ({d['insee']}) gelé {d.get('prod_gel','?')} → frais "
              f"{d.get('prod_fresh','?')} ({d.get('ecart_pct','?')} %) — {d['cause']}")
    ok = med <= 20.0 and len(ecarts) >= 90
    print("\n" + ("✅ ordres de grandeur TENUS (médiane ≤ 20 %)" if ok
                  else "❌ ordres de grandeur NON tenus — voir divergences ci-dessus"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
