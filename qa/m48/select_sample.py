"""M48 P0 — sélection déterministe de l'échantillon stratifié (~30 parcelles).
Lecture seule. Sort qa/m48/echantillon.csv (idu, strate, commune_insee).
Couvre : tous les tiers, cas spéciaux (mode B, locatif M44, société M43, radar M41,
dépôts M38, piscine M39, Renouvellement M47, RNU St-Philippe, sans adresse), ≥10 communes,
+ témoins récurrents (AT2542, CY0197, AL1154, EP0228, AZ0004)."""
from __future__ import annotations
import csv
from labuse.db import make_engine
from sqlalchemy import text

RUN = "q_v8_calibre"
eng = make_engine()

# Témoins récurrents (canoniques, résolus sur pièces).
WITNESSES = [
    ("97418000AT2542", "temoin_AT2542_brulante"),
    ("97419000AL1154", "temoin_AL1154_fourchette_piscine"),
    ("97422000CY0197", "temoin_CY0197_bati_marginal_divisible"),
    ("97411000EP0228", "temoin_EP0228_piscine_M39_M40"),
    ("97404000AZ0004", "temoin_AZ0004_renouvellement_rang1"),
]

sample: dict[str, str] = {}
def add(idu, strate):
    if idu and idu not in sample:
        sample[idu] = strate

for idu, s in WITNESSES:
    add(idu, s)

with eng.connect() as c:
    # 1 parcelle par tier, la plus « parlante » (rang bas si classé), commune variée.
    tiers = [r[0] for r in c.execute(text(
        "SELECT DISTINCT tier FROM parcel_p_score_v2 WHERE run_id=:r"), {"r": RUN})]
    for t in sorted(tiers):
        # pour les tiers classés (rang non nul) prendre un rang median ; sinon un idu déterministe
        row = c.execute(text("""
            SELECT parcelle_id FROM parcel_p_score_v2
            WHERE run_id=:r AND tier=:t
            ORDER BY COALESCE(rang, 999999), parcelle_id LIMIT 1"""), {"r": RUN, "t": t}).scalar()
        add(row, f"tier_{t}")
        # une 2e du même tier dans une autre commune (diversité)
        if row:
            row2 = c.execute(text("""
                SELECT parcelle_id FROM parcel_p_score_v2
                WHERE run_id=:r AND tier=:t AND left(parcelle_id,5) <> :cne
                ORDER BY COALESCE(rang,999999), parcelle_id LIMIT 1"""),
                {"r": RUN, "t": t, "cne": row[:5]}).scalar()
            if t in ("brulante", "chaude", "a_creuser", "reserve_fonciere", "declasse_bati_sature"):
                add(row2, f"tier_{t}_2")

    # Cas spéciaux
    add(c.execute(text("SELECT idu FROM score_e WHERE marge_estimee IS NOT NULL ORDER BY idu LIMIT 1")).scalar(), "special_M44_locatif_score_e")
    add(c.execute(text("SELECT idu FROM parcelle_personne_morale WHERE groupe_label IS NOT NULL ORDER BY idu LIMIT 1")).scalar(), "special_M43_societe")
    add(c.execute(text("SELECT idu FROM parcel_renouvellement WHERE run_label=:r AND renouv_score>=80 ORDER BY rang_segment LIMIT 1"), {"r": RUN}).scalar(), "special_M47_renouvellement")
    # RNU Saint-Philippe (97417)
    add(c.execute(text("SELECT parcelle_id FROM parcel_p_score_v2 WHERE run_id=:r AND parcelle_id LIKE '97417%' AND tier<>'ecartee' ORDER BY COALESCE(rang,999999),parcelle_id LIMIT 1"), {"r": RUN}).scalar(), "special_RNU_saint_philippe")
    # M38 dépôts : parcelle rattachée à un permis sitadel géolocalisé
    add(c.execute(text("SELECT p.idu FROM sitadel_permits s JOIN parcels p ON p.commune IS NOT NULL AND s.geom IS NOT NULL AND ST_Contains(p.geom, ST_Centroid(s.geom)) ORDER BY p.idu LIMIT 1")).scalar(), "special_M38_depot_permis")
    # sans adresse : parcelle non écartée sans adresse BAN
    add(c.execute(text("""
        SELECT s.parcelle_id FROM parcel_p_score_v2 s
        WHERE s.run_id=:r AND s.tier IN ('a_creuser','chaude')
          AND NOT EXISTS (SELECT 1 FROM adresses a WHERE a.idu = s.parcelle_id)
        ORDER BY s.parcelle_id LIMIT 1"""), {"r": RUN}).scalar(), "special_sans_adresse")

    # communes couvertes
    communes = sorted({idu[:5] for idu in sample})
    # commune de veille active M41 : forcer une parcelle dans une commune sous procédure
    # (Saint-Leu 97413 souvent citée) si pas déjà couverte
    add(c.execute(text("SELECT parcelle_id FROM parcel_p_score_v2 WHERE run_id=:r AND parcelle_id LIKE '97413%' AND tier<>'ecartee' ORDER BY COALESCE(rang,999999),parcelle_id LIMIT 1"), {"r": RUN}).scalar(), "special_M41_radar_commune")

# écrire
rows = [{"idu": i, "strate": s, "commune_insee": i[:5]} for i, s in sample.items()]
rows.sort(key=lambda x: (x["commune_insee"], x["idu"]))
with open("qa/m48/echantillon.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["idu", "strate", "commune_insee"])
    w.writeheader(); w.writerows(rows)

print(f"échantillon : {len(rows)} parcelles, {len({r['commune_insee'] for r in rows})} communes")
for r in rows:
    print(f"  {r['idu']}  {r['strate']}")
