"""Témoin OUTIL-PERMIS-FIX-1 (LOT 2) — DORMANT = définition UNIQUE mesurée : PC autorisé (code ≠ 4
annulé, ≠ 5 commencé, ≠ 6 achevé), sans DAACT, de plus de 3 ans (ancré sur dmax = fin des données),
ET aucune parcelle bâtie (emprise de bâti mesurée ≥ 10 m² dans `parcel_bati_emprise`). Recompte
indépendant sur lignes seedées — vérifie notamment que les ANNULÉS et les TRAVAUX COMMENCÉS sortent
(constat du relecteur : 28/30 dormants avaient du bâti, et le filtre acceptait les annulés)."""
from __future__ import annotations

import json

import pytest
from sqlalchemy import text


@pytest.mark.db
def test_point_mort_temoin(engine):
    from labuse.registre.moteurs.commune import permis_point_mort
    with engine.begin() as c:
        c.execute(text("CREATE TABLE IF NOT EXISTS parcel_bati_emprise "
                       "(idu VARCHAR(14) PRIMARY KEY, bati_m2 DOUBLE PRECISION NOT NULL)"))
        c.execute(text("DELETE FROM parcels WHERE commune = 'TemoinPM-C4'"))
        c.execute(text("DELETE FROM sitadel_permits WHERE commune = 'TemoinPM-C4'"))
        c.execute(text("DELETE FROM parcel_bati_emprise WHERE idu LIKE 'C4PM%'"))
        # 2 parcelles : P0 NUE (0 m² de bâti), P1 BÂTIE (50 m² ≥ seuil 10)
        for i, bati in ((0, 0.0), (1, 50.0)):
            idu = f"C4PM000000{i}"
            c.execute(text(
                "INSERT INTO parcels (idu, commune, surface_m2, geom) VALUES "
                "(:i, 'TemoinPM-C4', 100, ST_GeomFromText('POINT(55.5 -21.1)', 4326))"), {"i": idu})
            c.execute(text("INSERT INTO parcel_bati_emprise (idu, bati_m2) VALUES (:i, :b)"),
                      {"i": idu, "b": bati})
        # dmax explicite = aujourd'hui ; fenêtre « > 36 mois » → un permis vieux de 48 mois qualifie.
        dmax = c.execute(text("SELECT now()")).scalar()
        # 6 permis PC vieux de 48 mois (idu_codes, raw) :
        #   [P0 nue], autorisé (2), sans DAACT                 → DORMANT ✓
        #   [P1 bâtie], autorisé (2), sans DAACT               → bâti détecté → NON
        #   [P0 nue], avec DAACT                               → achevé → NON
        #   [P0 nue], ANNULÉ (4)                               → NON (sort des dormants)
        #   [P0 nue], TRAVAUX COMMENCÉS (5)                    → NON (sort des dormants)
        #   OUTIL-PERMIS-FIX-2 (Défaut C) :
        #   [P0 nue, PARCELLE ABSENTE du cadastre], autorisé   → NON (mesure incomplète, pas « toutes »)
        cas = ((["C4PM0000000"], {"etat": "2"}), (["C4PM0000001"], {"etat": "2"}),
               (["C4PM0000000"], {"etat": "2", "daact": "2021-01-01"}),
               (["C4PM0000000"], {"etat": "4"}), (["C4PM0000000"], {"etat": "5"}),
               (["C4PM0000000", "C4PMABSENTE00"], {"etat": "2"}))
        for idus, raw in cas:
            c.execute(text(
                "INSERT INTO sitadel_permits (commune, type, date, idu_codes, raw) VALUES"
                " ('TemoinPM-C4', 'PC', now() - interval '48 months', :idus, :raw)"),
                {"idus": json.dumps(idus), "raw": json.dumps(raw)})
        n = permis_point_mort(c, "TemoinPM-C4", months=36, dmax=dmax)
        c.execute(text("DELETE FROM parcels WHERE commune = 'TemoinPM-C4'"))
        c.execute(text("DELETE FROM sitadel_permits WHERE commune = 'TemoinPM-C4'"))
        c.execute(text("DELETE FROM parcel_bati_emprise WHERE idu LIKE 'C4PM%'"))
    # seul le PC autorisé sans DAACT sur la parcelle NON bâtie compte → 1
    assert n == 1
