"""Point 1 de l'ARBITRAGE RE-RUN (Vic 30/07) — URGENT : restaurer l'avertissement AU des communes
NON encore calibrées en AU-OUVERTURE affiné.

Le re-run a purgé les ~6 636 marques expérimentales île-entière de `parcel_au_statut` puis n'a
re-peuplé que les 4 communes calibrées (Saint-Paul, La Possession, Saint-Leu, Trois-Bassins). Les
parcelles AU des ~19 autres communes se sont retrouvées SANS aucun avertissement, alors qu'elles
restent au statut d'ouverture non vérifié. « Une parcelle ne doit jamais perdre un avertissement
parce qu'on a amélioré le mécanisme ailleurs. » (Vic)

Ce script RESTAURE la marque LEGACY (générique / dimensions_seules, via `build_au_statut_batch` →
`resolve_zone`, motifs d'origine inchangés) pour les seules parcelles AU HORS des 4 communes
calibrées. Les 4 communes gardent leurs motifs affinés (plus vrais). Idempotent, réversible.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
from sqlalchemy import text
from labuse.db import session_scope
from labuse.faisabilite.au_statut import build_au_statut_batch

CALIBREES = ["97415", "97408", "97413", "97423"]  # 4 communes AU-OUVERTURE affinées

def main():
    with session_scope() as s:
        idus = [r[0] for r in s.execute(text("""
            SELECT DISTINCT p.idu FROM parcels p JOIN parcel_zone_plu z ON z.idu = p.idu
            WHERE (z.zone_fam = 'AU' OR z.zone_lib ~ '^[0-9]?AU')
              AND substring(p.idu from 1 for 5) <> ALL(:cal)"""), {"cal": CALIBREES}).all()]
    print(f"parcelles AU hors 4 communes calibrées : {len(idus)}")
    total = 0
    for k in range(0, len(idus), 500):
        with session_scope() as s:
            total += build_au_statut_batch(s, idus[k:k + 500])
    print(f"marquées (générique + dimensions_seules) : {total}")
    with session_scope() as s:
        for classe, n in s.execute(text(
                "SELECT classe, count(*) FROM parcel_au_statut GROUP BY 1 ORDER BY 2 DESC")).all():
            print(f"   {classe:28s} {n}")

if __name__ == "__main__":
    main()
