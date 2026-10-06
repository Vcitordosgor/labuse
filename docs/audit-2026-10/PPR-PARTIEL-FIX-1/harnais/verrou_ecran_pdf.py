"""PPR-PARTIEL-FIX-1 (étape B) — VERROU écran = PDF : le chiffre du badge « partie hors zone rouge »
servi à la fiche est LE MÊME que celui imprimé au Dossier PDF (source unique db.surface_hors_ppr_rouge,
portée par potentiel_transformation.hors_ppr_rouge → verdict_potentiel au §potentiel + note au §risques).

  LABUSE_DATABASE_URL=postgresql+psycopg://openclaw@localhost:5432/labuse \
  PYTHONPATH=src ~/Desktop/labuse/.venv/bin/python docs/.../harnais/verrou_ecran_pdf.py
"""
from __future__ import annotations

import re
import sys



from labuse import runs
from labuse.api.app import _q_v2_fiche
from labuse.db import session_factory
from labuse.exports.builder import construire

TEMOINS = ["97409000AY0786", "97415000HL0001"]


def main() -> None:
    session = session_factory()()
    ok = True
    try:
        for idu in TEMOINS:
            # ÉCRAN : la valeur servie à la fiche (exactement ce que l'UI lit).
            fiche = _q_v2_fiche(session, idu, run_label=runs.current())
            hr = (fiche.get("potentiel_transformation") or {}).get("hors_ppr_rouge")
            assert hr, f"{idu} : pas de badge hors_ppr_rouge (témoin attendu)"
            ecran_m2 = f"{hr['hors_rouge_m2']:,}".replace(",", " ")
            # PDF : le MÊME fiche passé au builder (comme l'endpoint Dossier réel).
            res = construire(session, idu, "dossier", fiche=fiche)
            html = res.html
            # le chiffre « X m² » doit figurer au Dossier (§potentiel ET §risques)
            present = (f"{ecran_m2} m²" in html)
            # compter les occurrences du chiffre hors-rouge dans le PDF (≥ 2 : §potentiel + §risques)
            occ = len(re.findall(re.escape(f"{ecran_m2} m²"), html))
            print(f"{idu}  écran={ecran_m2} m² ({hr['pct']} %)  "
                  f"→ PDF contient le chiffre : {present}  (occurrences : {occ})")
            ok = ok and present and occ >= 2
        print("VERROU écran = PDF :", "OK" if ok else "ÉCHEC")
        sys.exit(0 if ok else 1)
    finally:
        session.rollback()
        session.close()


if __name__ == "__main__":
    main()
