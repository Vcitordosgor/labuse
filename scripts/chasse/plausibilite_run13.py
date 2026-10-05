"""CHASSE-2 angle 3 — plausibilité du run 13 face au terrain (20 montées 0→A + 50 bâties
dont la SDP résiduelle a le plus augmenté).

    python -m scripts.chasse.plausibilite_run13
      → docs/audit-2026-10/CHASSE-2/PLAUSIBILITE-RUN13.csv
      → docs/audit-2026-10/CHASSE-2/raw/ortho/<idu>.png (crop ortho IGN + contour, pour l'œil)

Pour chaque parcelle : les faits mesurables (surface, emprise bâtie servie, taux, étages
servis, hauteurs LiDAR égout/faîtage → niveaux implicites à 2,8 m/niveau, SDP run 10 → 13,
zone PLU) + des drapeaux de plausibilité PROMOTEUR :

  · sat_emprise   — emprise/surface > 85 % : parcelle quasi saturée au sol ; une bande A
                    (= « excellente ») dessus demande une SDP en étages, à regarder ;
  · niveaux_incoherents — étages servis (parcel_filtre_bati.etage) vs niveaux implicites
                    LiDAR (égout/2,8 + 1) : écart > 1 niveau = mesure douteuse ;
  · sdp_sup_enveloppe — SDP résiduelle 13 > surface × 4 niveaux (enveloppe large toutes
                    zones U de l'île) : au-delà, le chiffre dépasse ce qu'un gabarit
                    courant permet — à justifier par la règle de zone, sinon FAUX.

L'ortho est le juge final : les PNG sont produits ici (plan_ortho, le MÊME composant que
les documents servis), l'inspection est consignée au rapport. Lecture seule.
"""
from __future__ import annotations

import csv
import pathlib

RACINE = pathlib.Path(__file__).resolve().parents[2]
ECHANTILLON = RACINE / "docs" / "audit-2026-10" / "CHASSE-2" / "ECHANTILLON.csv"
SORTIE = RACINE / "docs" / "audit-2026-10" / "CHASSE-2" / "PLAUSIBILITE-RUN13.csv"
ORTHO_DIR = RACINE / "docs" / "audit-2026-10" / "CHASSE-2" / "raw" / "ortho"
DSN = "postgresql://openclaw@localhost:5432/labuse"
H_NIVEAU_M = 2.8


def main() -> None:
    import psycopg

    with open(ECHANTILLON, newline="") as f:
        ech = [r for r in csv.DictReader(f) if r["idu"]
               and r["classe"] in ("montee_0A", "sdp_hausse_batie")]
    conn = psycopg.connect(DSN, options="-c statement_timeout=120000")
    cur = conn.cursor()
    lignes = []
    for r in ech:
        cur.execute("""
            SELECT p.surface_m2::int,
                   fb.emprise_max_m2::int, fb.etage, fb.ratio_pct::int,
                   bh.egout_m, bh.faitage_m, bh.hauteur_bdtopo_m,
                   r10.sdp_residuelle_m2, r13.sdp_residuelle_m2,
                   zp.zone_fam, zp.zone_lib,
                   sl.bande, sl.score
            FROM parcels p
            LEFT JOIN parcel_filtre_bati fb ON fb.parcel_id = p.id
            LEFT JOIN batiment_hauteur_lidar bh ON bh.idu = p.idu
            LEFT JOIN parcel_residuel_runs r10 ON r10.parcel_id = p.id AND r10.run_seq = 10
            LEFT JOIN parcel_residuel_runs r13 ON r13.parcel_id = p.id AND r13.run_seq = 13
            LEFT JOIN parcel_zone_plu zp ON zp.idu = p.idu
            LEFT JOIN score_labuse sl ON sl.parcel_id = p.id AND sl.run_label = 'q_v16'
            WHERE p.idu = %s""", (r["idu"],))
        row = cur.fetchone()
        if not row:
            continue
        (surf, emprise, etages, ratio, egout, faitage, h_bdtopo,
         sdp10, sdp13, zfam, zlib, bande, score) = row
        niv_lidar = round(egout / H_NIVEAU_M) + 1 if egout else None
        sat = (emprise or 0) and surf and (emprise / surf) > 0.85
        niv_ko = (niv_lidar is not None and etages is not None
                  and abs(niv_lidar - etages) > 1)
        sdp_ko = (sdp13 or 0) > (surf or 0) * 4
        lignes.append({
            "idu": r["idu"], "commune": r["commune"], "classe": r["classe"],
            "zone": zlib or zfam or "", "bande": bande or "", "score": score,
            "surface_m2": surf, "emprise_m2": emprise, "taux_pct": ratio,
            "etages_servis": etages,
            "egout_m": egout, "faitage_m": faitage, "h_bdtopo_m": h_bdtopo,
            "niveaux_lidar": niv_lidar,
            "sdp_run10": sdp10, "sdp_run13": sdp13,
            "flag_sat_emprise": "X" if sat else "",
            "flag_niveaux_incoherents": "X" if niv_ko else "",
            "flag_sdp_sup_enveloppe": "X" if sdp_ko else "",
        })
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    with open(SORTIE, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(lignes[0].keys()))
        w.writeheader()
        w.writerows(lignes)
    n_flags = sum(1 for l in lignes if l["flag_sat_emprise"] or
                  l["flag_niveaux_incoherents"] or l["flag_sdp_sup_enveloppe"])
    print(f"{len(lignes)} parcelles, {n_flags} avec ≥1 drapeau → {SORTIE}")

    # crops ortho (contour mint) — même composant que les documents (plan_ortho).
    ORTHO_DIR.mkdir(parents=True, exist_ok=True)
    import base64 as _b64

    from sqlalchemy import text as _text

    from labuse.api.plan_situation import plan_ortho
    from labuse.db import session_scope
    from labuse.flash.report import storage_dir
    faits = 0
    with session_scope() as s:
        for l in lignes:
            cible = ORTHO_DIR / f"{l['idu']}.png"
            if cible.exists():
                faits += 1
                continue
            gj = s.execute(_text("SELECT ST_AsGeoJSON(geom) FROM parcels WHERE idu = :i"),
                           {"i": l["idu"]}).scalar()
            res = plan_ortho(gj, cache_dir=storage_dir() / "tiles", zoom_max=19)
            if res.get("ok"):
                cible.write_bytes(_b64.b64decode(res["jpeg"].split(",", 1)[1])
                                  if isinstance(res.get("jpeg"), str) and res["jpeg"].startswith("data:")
                                  else res["jpeg"])
                faits += 1
            else:
                print(f"  ! ortho {l['idu']}: {res.get('echec')}")
    print(f"orthos : {faits}/{len(lignes)} → {ORTHO_DIR}")


if __name__ == "__main__":
    main()
