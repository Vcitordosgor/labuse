"""RESIDUEL-1 — simulation PROD EN LECTURE SEULE sur les parcelles cause='redhibitoire'.

Ne CALCULE rien de nouveau dans la base : pour chaque parcelle fermée « rédhibitoire » par le run
servi, rejoue `compute_residuel(assiette_clippee=True)` = le NOUVEAU chemin unique de RESIDUEL-1
(identique, parcelle par parcelle, à `compute_residuel(pid)` du code fix/residuel-1), et compare au
stocké. N'écrit RIEN : transaction forcée READ ONLY (tout UPSERT accidentel échouerait).

Sortie : des lignes `CSV|...` (IDU, commune, zone, part rouge %, SDP avant, SDP après, verdict) +
un bloc `SUMMARY|...`. L'appelant redirige la sortie vers un fichier LOCAL.
"""
from __future__ import annotations

import time

from sqlalchemy import text

from labuse.db import session_scope
from labuse.faisabilite.residuel import compute_residuel

# Aire du ROUGE SEUL dans la parcelle (même découpage que le gabarit) → part rouge pour le CSV.
_ROUGE = text(
    "SELECT ST_Area(p.geom_2975) AS parcelle_m2, "
    "  ST_Area(ST_Intersection(ST_Union(ST_MakeValid(ST_ClipByBox2D(sl.geom_2975, p.geom_2975))), "
    "          p.geom_2975)) AS rouge_m2 "
    "FROM spatial_layers sl, parcels p "
    "WHERE p.id = :pid AND sl.kind='ppr' AND labuse_ppr_couleur(sl.subtype, sl.attrs) <> 'bleu' "
    "  AND ST_Intersects(sl.geom_2975, p.geom_2975) GROUP BY p.geom_2975")


def main() -> None:
    with session_scope() as s:
        # Filet de sécurité : AUCUNE écriture possible dans cette session.
        s.execute(text("SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY"))
        s.execute(text("SET statement_timeout = '120s'"))

        served = s.execute(text("SELECT run_seq, label FROM residuel_runs WHERE is_served")).first()
        univers = s.execute(text("SELECT count(*) FROM parcel_residuel")).scalar()
        print(f"META|served_run={served.run_seq}|label={served.label}|univers={univers}")

        rows = s.execute(text(
            "SELECT pr.parcel_id AS pid, p.idu AS idu, p.commune AS commune, "
            "       pr.sdp_residuelle_m2 AS sdp_avant "
            "FROM parcel_residuel pr JOIN parcels p ON p.id = pr.parcel_id "
            "WHERE pr.cause = 'redhibitoire' ORDER BY p.commune, p.idu")).mappings().all()
        print(f"META|n_redhibitoire={len(rows)}")

        flips = 0
        restent = 0
        erreurs = 0
        t0 = time.time()
        for r in rows:
            pid = r["pid"]
            # part rouge (CSV) — tolérant : géométrie pathologique → part inconnue.
            part_rouge = ""
            zone = ""
            try:
                with s.begin_nested():
                    g = s.execute(_ROUGE, {"pid": pid}).first()
                if g and g.parcelle_m2 and float(g.parcelle_m2) > 0:
                    part_rouge = f"{100.0 * float(g.rouge_m2 or 0) / float(g.parcelle_m2):.1f}"
            except Exception:  # noqa: BLE001
                part_rouge = "?"
            # nouveau chemin unique (= compute_residuel(pid) du fix).
            try:
                fresh = compute_residuel(s, pid, assiette_clippee=True)
            except Exception as exc:  # noqa: BLE001
                erreurs += 1
                print(f"ERR|{r['idu']}|{type(exc).__name__}: {str(exc)[:80]}")
                continue
            zone = (fresh.get("zone") or "") if isinstance(fresh, dict) else ""
            # la zone n'est pas toujours dans le dict résiduel → lire parcel_zone_plu.
            if not zone:
                zone = s.execute(text("SELECT zone_lib FROM parcel_zone_plu WHERE idu=:i"),
                                 {"i": r["idu"]}).scalar() or ""
            dispo = bool(fresh.get("disponible"))
            cause = fresh.get("cause")
            sdp_apres = fresh.get("sdp_residuelle_m2") if dispo else (fresh.get("sdp_ecrite") or 0)
            if dispo and cause is None:
                verdict = "CONSTRUCTIBLE"
                flips += 1
            else:
                verdict = f"ferme:{cause or 'indispo'}"
                restent += 1
            print(f"CSV|{r['idu']}|{r['commune']}|{zone}|{part_rouge}|"
                  f"{r['sdp_avant'] if r['sdp_avant'] is not None else 0}|{sdp_apres}|{verdict}")
        dt = time.time() - t0

        n = len(rows) - erreurs
        rate = (n / dt) if dt > 0 else 0.0
        print(f"SUMMARY|n={len(rows)}|flips={flips}|restent={restent}|erreurs={erreurs}"
              f"|secondes={dt:.1f}|parcelles_par_s={rate:.1f}|univers={univers}"
              f"|estim_ile_s={(univers / rate) if rate else 0:.0f}")

        # Ancrage : durées des runs résiduels historiques (clippés) pour borner l'estimation île.
        hist = s.execute(text(
            "SELECT label, duree_s FROM residuel_runs WHERE duree_s IS NOT NULL "
            "ORDER BY run_seq DESC LIMIT 6")).mappings().all()
        for h in hist:
            print(f"HIST|{h['label']}|duree_s={h['duree_s']}")


if __name__ == "__main__":
    main()
