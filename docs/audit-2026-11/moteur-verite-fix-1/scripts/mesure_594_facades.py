"""MOTEUR-VERITE-FIX-8 LOT 4 — MESURE SANS RIEN CHANGER (dimensionnement d'un chantier ultérieur).

Décision actée : pas de chiffre de scénario bas pour les parcelles « à vérifier » sans façade
établie (le retrait minimal uniforme tient mais aucun front sur voie n'est qualifié — le moteur
classe tout le contour comme un fond). On NE MODIFIE PAS le moteur ; on MESURE seulement, sur cette
population :
  (1) combien n'ont AUCUN front qualifié sur voie, par commune ;
  (2) combien en auraient un si on considérait comme voie POSSIBLE un côté qui n'est mitoyen
      d'aucune autre parcelle cadastrée (hors cours d'eau et rivage).

Usage : PYTHONPATH=src python mesure_594_facades.py
Lit le cache-fix6-ile (rejeu de la branche) pour la population « à vérifier », relit le motif réel,
classe les limites (gabarit.limites.classify_parcel_limits) et mesure. N'écrit rien dans la base.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

FIX = Path(__file__).resolve().parents[1]


def main() -> None:
    from sqlalchemy import text
    from labuse.db import session_factory
    from labuse.faisabilite.db import parcel_faisabilite
    from labuse.gabarit.limites import classify_parcel_limits
    s = session_factory()()

    cache = FIX / "cache-fix6-ile"
    averif = [json.loads(p.read_text()) for p in cache.glob("*.json")]
    averif = [r["idu"] for r in averif if r.get("sdp") is None and r.get("constructible")]
    print(f"« à vérifier » dans le cache branche : {len(averif)}")

    # population visée : motif « retrait minimal uniforme » (scénario bas sans façade établie)
    cibles = []
    for idu in averif:
        pid = s.execute(text("select id from parcels where idu=:i"), {"i": idu}).scalar()
        if pid is None:
            continue
        try:
            _ctx, f = parcel_faisabilite(s, pid)
        except Exception:  # noqa: BLE001
            continue
        if "retrait uniforme minimal" in (f.verdict or "").lower() or "retrait minimal" in (f.verdict or "").lower():
            cibles.append((idu, pid, _ctx.commune))
    print(f"population « sans façade établie » (retrait minimal uniforme) : {len(cibles)}")

    # (2) mesure FINE sur le CONTOUR (pas par arête fusionnée). Longueur de bord LIBRE = le contour
    # moins les portions le long d'un cours d'eau/rivage (tampon 1 m) moins les portions mitoyennes :
    #   · littéral : mitoyennes de TOUTE autre parcelle cadastrée (tampon 0,5 m) ;
    #   · utile    : mitoyennes d'un voisin BÂTI seulement — un côté qui ne borde ni bâti ni eau face
    #                donc du domaine public / une voie-parcelle (le cadastre réunionnais DÉCOUPE les
    #                voies en parcelles, d'où le littéral ≈ 0 ; l'utile mesure le front de rue possible).
    # Un bord libre ≥ 3 m (seuil de desserte du moteur) = une voie POSSIBLE. Une requête par parcelle.
    _BORD_LIBRE = text("""
        WITH p AS (SELECT geom_2975 AS g, commune AS c FROM parcels WHERE id = :pid),
        eau AS (SELECT ST_Union(ST_Buffer(l.geom_2975, 1.0)) AS u FROM spatial_layers l, p
                WHERE l.commune = p.c AND l.kind IN ('ravine','trait_de_cote')
                  AND ST_DWithin(l.geom_2975, p.g, 1.1)),
        nb_all AS (SELECT ST_Union(ST_Buffer(o.geom_2975, 0.5)) AS u FROM parcels o, p
                   WHERE o.id <> :pid AND o.commune = p.c AND ST_DWithin(o.geom_2975, p.g, 0.6)),
        nb_bati AS (SELECT ST_Union(ST_Buffer(o.geom_2975, 0.5)) AS u FROM parcels o, p
                    WHERE o.id <> :pid AND o.commune = p.c AND ST_DWithin(o.geom_2975, p.g, 0.6)
                      AND EXISTS(SELECT 1 FROM spatial_layers b WHERE b.kind='batiment'
                                 AND b.commune = p.c AND ST_Intersects(b.geom_2975, o.geom_2975)))
        SELECT ST_Length(ST_Difference(ST_Difference(ST_Boundary(p.g),
                 COALESCE((SELECT u FROM nb_all), ST_GeomFromText('POLYGON EMPTY',2975))),
                 COALESCE((SELECT u FROM eau), ST_GeomFromText('POLYGON EMPTY',2975)))) AS libre_litteral,
               ST_Length(ST_Difference(ST_Difference(ST_Boundary(p.g),
                 COALESCE((SELECT u FROM nb_bati), ST_GeomFromText('POLYGON EMPTY',2975))),
                 COALESCE((SELECT u FROM eau), ST_GeomFromText('POLYGON EMPTY',2975)))) AS libre_utile
        FROM p
    """)
    sans_voie_par_commune = Counter()
    total_sans_voie = 0
    gagnent_litteral = 0   # (2) littéral : bord libre d'aucune parcelle cadastrée
    gagnent_utile = 0      # (2 bis) utile : bord ne bordant ni bâti ni eau (front de domaine public)
    for idu, pid, commune in cibles:
        try:
            lim = classify_parcel_limits(s, pid, emprises_publiques=True, voies_privees=True)
        except Exception:  # noqa: BLE001
            lim = None
        if lim is None or lim.has_voie:
            continue
        total_sans_voie += 1
        sans_voie_par_commune[commune] += 1
        try:
            r = s.execute(_BORD_LIBRE, {"pid": pid}).fetchone()
            if r is not None and r.libre_litteral is not None and float(r.libre_litteral) >= 3.0:
                gagnent_litteral += 1
            if r is not None and r.libre_utile is not None and float(r.libre_utile) >= 3.0:
                gagnent_utile += 1
        except Exception:  # noqa: BLE001
            pass

    print("\n(1) SANS AUCUN FRONT QUALIFIÉ SUR VOIE — par commune :")
    for commune, n in sans_voie_par_commune.most_common():
        print(f"    {n:5d}  {commune}")
    print(f"    TOTAL sans front sur voie : {total_sans_voie} / {len(cibles)}")
    print(f"\n(2) EN GAGNERAIENT UN si un CÔTÉ LIBRE (≥ 3 m) était traité comme voie possible :")
    print(f"    · littéral (aucune parcelle cadastrée mitoyenne, hors eau/rivage) : {gagnent_litteral} "
          f"/ {total_sans_voie}")
    print(f"      → ≈ 0 attendu : le cadastre RÉUNIONNAIS découpe les VOIES en parcelles, donc tout "
          f"front de rue est « mitoyen » d'une parcelle (la voie).")
    print(f"    · utile (côté ne bordant ni BÂTI ni eau/rivage = face à du domaine public / une voie) "
          f": {gagnent_utile} / {total_sans_voie}")


if __name__ == "__main__":
    main()
