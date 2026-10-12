"""DEPLOIEMENT-Q18 — build-intersections CIBLÉ (servitudes) sur les parcelles au cadastre MODIFIÉ.

Pourquoi : `labuse build-intersections` fait un REBUILD complet île (staging + RENAME) → plusieurs
jours (>1 h / 4 000 parcelles). Or, pour `parcel_couche_intersection`, les seules couches intersectées
sont les SERVITUDES de la fiche — `dpu`, `peb`, `sup`, `plu_gpu_prescription` (subtype 01/05) — et
AUCUNE de ces couches n'a changé depuis le 03/10 (dernières versions : dpu/peb/sup 09-13/14,
prescription 06-29 ; les couches qui ont bougé — transport, safer, ligne_ht, vefa… — ne sont PAS dans
cette table). La table n'est donc périmée QUE par le différentiel CADASTRE (son empreinte inclut
`count(parcels)||max(id)`). Il suffit de recalculer les intersections des parcelles cadastralement
modifiées : **2 919 nouvelles + 1 501 géométries = 4 420** (lues dans `_cad_sm1_nouvelles` /
`_cad_sm1_geommodif`). Les 1 353 disparues gardent leurs lignes (géométrie INCHANGÉE — marquées, pas
modifiées) ; les parcelles intactes ne sont pas touchées.

Garanties :
 · La table VIVANTE n'est modifiée QUE pour ces parcelles : `DELETE WHERE parcel_id = ANY(ids)` (retire
   les lignes périmées des géom-modifiées ; no-op pour les nouvelles) + `INSERT` recalculé, par lots
   courts (verrou bref sur la table partagée). Aucun DROP/RENAME, aucune autre ligne touchée.
 · EXPRESSION IDENTIQUE à couche_intersection.build (ordre fiche `ST_Intersection(parcelle, couche)`,
   géométrie brute, même filtre de kinds) → résultat bit-à-bit égal à un rebuild complet.
 · `--update-meta` (île entière seulement) repose `serv_version` = empreinte courante → la fiche relit
   la table (fraiche()=True). Refusé si `--commune` (jeu partiel : la table resterait au calcul au vol,
   ce qui est CORRECT tant que tout n'est pas recalculé).

Usage (venv dépôt principal) :
  DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib PYTHONPATH=src .venv/bin/python \
    scripts/audit/intersections/build_intersections_cible.py [--commune 97419] [--apply] [--update-meta]
Défaut = DRY-RUN (compte la cible, n'écrit rien).
"""
from __future__ import annotations

import argparse
import os
import time

from sqlalchemy import text

# Filtre servitudes — COPIE EXACTE de labuse.couche_intersection._FILTER_SERV (source unique du sens).
_FILTER_SERV = ("(sl.kind IN ('dpu','peb','sup') "
                "OR (sl.kind = 'plu_gpu_prescription' AND sl.subtype IN ('01','05')))")
TABLE = "parcel_couche_intersection"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--commune", default=None, help="INSEE (préfixe idu) pour restreindre — TEST.")
    ap.add_argument("--apply", action="store_true", help="Écrit (sinon DRY-RUN : compte seulement).")
    ap.add_argument("--update-meta", action="store_true",
                    help="Repose serv_version (île ENTIÈRE uniquement — refusé avec --commune).")
    ap.add_argument("--chunk", type=int, default=500, help="Parcelles par transaction (verrou bref).")
    args = ap.parse_args()
    if args.update_meta and args.commune:
        raise SystemExit("⛔ --update-meta interdit avec --commune (jeu partiel → empreinte mentirait).")

    os.environ.setdefault("LABUSE_DATABASE_URL",
                          "postgresql+psycopg://openclaw@localhost:5432/labuse")
    from labuse.db import session_scope
    from labuse import couche_intersection as ci

    where_commune = "AND left(u.idu, 5) = :insee" if args.commune else ""
    params = {"insee": args.commune} if args.commune else {}

    with session_scope() as s:
        # Jeu CIBLE = nouvelles ∪ géom-modifiées, mappées sur parcels.id (disparues EXCLUES : inchangées).
        ids = [r[0] for r in s.execute(text(f"""
            SELECT p.id
            FROM (SELECT idu FROM _cad_sm1_nouvelles
                  UNION SELECT idu FROM _cad_sm1_geommodif) u
            JOIN parcels p ON p.idu = u.idu
            WHERE p.cadastre_disparue_le IS NULL {where_commune}
            ORDER BY p.id
        """), params).fetchall()]
        cible = f"commune {args.commune}" if args.commune else "île (4 420 attendues)"
        print(f"[cible] {len(ids)} parcelle(s) à recalculer — {cible}.", flush=True)
        if not ids:
            print("rien à faire.", flush=True); return
        if not args.apply:
            print("DRY-RUN : aucune écriture. Relancer avec --apply.", flush=True); return

        t0 = time.time()
        total_ins = 0
        for i in range(0, len(ids), args.chunk):
            lot = ids[i:i + args.chunk]
            s.execute(text("SET lock_timeout = '5s'"))
            # Remplacement ATOMIQUE des lignes de CE lot : DELETE puis INSERT dans la même transaction.
            s.execute(text(f"DELETE FROM {TABLE} WHERE parcel_id = ANY(:ids)"), {"ids": lot})
            n = s.execute(text(f"""
                INSERT INTO {TABLE} (parcel_id, layer_id, kind, subtype, area_m2, geom_2975)
                SELECT p.id, sl.id, sl.kind, sl.subtype,
                       ST_Area(ST_Intersection(p.geom_2975, sl.geom_2975)),
                       ST_Intersection(p.geom_2975, sl.geom_2975)
                FROM parcels p
                JOIN spatial_layers sl
                  ON ST_Intersects(p.geom_2975, sl.geom_2975) AND {_FILTER_SERV}
                WHERE p.id = ANY(:ids)
            """), {"ids": lot}).rowcount
            s.commit()
            total_ins += n or 0
            print(f"  lot {i//args.chunk + 1}: {len(lot)} parcelles → +{n} lignes "
                  f"(cumul {total_ins}, {time.time()-t0:.0f}s)", flush=True)

        if args.update_meta:
            # Île complète : l'empreinte courante doit déjà matcher (aucune couche servitude n'a bougé,
            # seul le cadastre a changé et il est maintenant entièrement représenté).
            v = ci.serv_version(s)
            s.execute(text(f"""
                INSERT INTO {ci._META} (key, value, updated_at) VALUES (:k, :v, now())
                ON CONFLICT (key) DO UPDATE SET value = excluded.value, updated_at = now()
            """), {"k": ci._KEY_SERV, "v": v})
            s.commit()
            print(f"[meta] serv_version reposé = {v} → la fiche relit la table (fraiche()=True).",
                  flush=True)
        else:
            print("[meta] NON reposé (jeu partiel) — la fiche reste au calcul au vol jusqu'à l'île "
                  "complète. Normal pour un test commune.", flush=True)

        print(f"✓ ciblé terminé : {len(ids)} parcelles, {total_ins} lignes, {time.time()-t0:.0f}s. "
              f"Table vivante modifiée UNIQUEMENT pour ces parcelles.", flush=True)


if __name__ == "__main__":
    main()
