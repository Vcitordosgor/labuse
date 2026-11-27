"""OUTIL-PERMIS-FIX-14 (LOT 1) — mesure de l'avertissement §Bâti « permis postérieur au survol ».

Combien de parcelles changent de TEXTE quand l'avertissement lit la SOURCE `sitadel_permits.date`
(via `permis_classe.permis_autorise_apres`) au lieu de la table périmée `p_model_permits` ?
LECTURE SEULE de la base (SELECT uniquement). Usage :

    PYTHONPATH=src LABUSE_DATABASE_URL=…/labuse python scripts/outil_permis_fix8/fix14_mesure_caveat.py
"""
from __future__ import annotations

import os

from sqlalchemy import create_engine, text

URL = os.environ["LABUSE_DATABASE_URL"]
eng = create_engine(URL)

# Caveat = max(date d'autorisation de permis sur la parcelle) STRICTEMENT après la fin du survol LiDAR.
# AVANT (périmé) : p_model_permits.date_autorisation. APRÈS (source) : sitadel_permits.date via idu_codes.
SQL = """
WITH lid AS (
  SELECT idu, date_fin_survol FROM batiment_hauteur_lidar WHERE date_fin_survol IS NOT NULL
),
avant AS (
  SELECT l.idu, max(p.date_autorisation) AS d
  FROM lid l JOIN p_model_permits p ON p.idu = l.idu AND p.date_autorisation > l.date_fin_survol
  GROUP BY l.idu
),
apres AS (
  SELECT l.idu, max(sp.date::date) AS d
  FROM lid l
  JOIN sitadel_permits sp ON true
  JOIN LATERAL jsonb_array_elements_text(sp.idu_codes) j(idu) ON j.idu = l.idu
  WHERE sp.date::date > l.date_fin_survol
  GROUP BY l.idu
)
SELECT l.idu, l.date_fin_survol, avant.d AS caveat_avant, apres.d AS caveat_apres
FROM lid l
LEFT JOIN avant ON avant.idu = l.idu
LEFT JOIN apres ON apres.idu = l.idu
WHERE avant.d IS DISTINCT FROM apres.d
ORDER BY l.idu
"""


def _fmt(d):
    return d.strftime("%d/%m/%Y") if d else "— (aucun caveat)"


with eng.connect() as c:
    rows = c.execute(text(SQL)).mappings().all()
    print(f"parcelles dont le TEXTE de l'avertissement §Bâti change : {len(rows)}")
    # ventilation
    disparait = sum(1 for r in rows if r["caveat_apres"] is None)
    change_date = sum(1 for r in rows if r["caveat_apres"] is not None)
    print(f"  · l'avertissement DISPARAÎT (plus de permis postérieur réel) : {disparait}")
    print(f"  · la DATE de l'avertissement change                          : {change_date}")

    # 10 à vérifier à la main : on ré-expose les permis source de la parcelle
    print("\n10 parcelles vérifiées à la main (permis source sur la parcelle, date de survol) :")
    for r in rows[:10]:
        permits = c.execute(text(
            "SELECT sp.permit_id, sp.date::date AS d FROM sitadel_permits sp "
            "JOIN LATERAL jsonb_array_elements_text(sp.idu_codes) j(idu) ON j.idu = :i "
            "ORDER BY sp.date"), {"i": r["idu"]}).all()
        pstr = ", ".join(f"{pid}:{d}" for pid, d in permits)
        print(f"  {r['idu']}  survol fin {r['date_fin_survol']}  "
              f"AVANT(périmé)={_fmt(r['caveat_avant'])}  APRÈS(source)={_fmt(r['caveat_apres'])}")
        print(f"      permis source : {pstr}")
