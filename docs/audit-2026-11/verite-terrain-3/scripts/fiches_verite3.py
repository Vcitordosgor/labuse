"""VERITE-TERRAIN-3 — 30 cas illustrés pour le relecteur (~/Desktop/verite-3/).

Chaque cas = un fichier Markdown autoportant : la ligne du permis (Sit@del), la fiche LABUSE
reconstruite (zone, verdict moteur avec ses étapes, classement servi, SDP), et le classement
de relecture avec sa preuve. Entrée : CAS-30.csv (permit_id;idu;source;classement;preuve)
préparé par l'orchestrateur depuis les relectures.

    PYTHONPATH=src python docs/audit-2026-11/verite-terrain-3/scripts/fiches_verite3.py
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

RACINE = Path(__file__).resolve().parents[4]
DOSSIER = RACINE / "docs" / "audit-2026-11" / "verite-terrain-3"
CACHE = DOSSIER / "cache" / "capacite"
DEST = Path.home() / "Desktop" / "verite-3"


def main() -> None:
    import psycopg
    from labuse.verite_terrain import _dsn

    DEST.mkdir(exist_ok=True)
    conn = psycopg.connect(_dsn())
    conn.read_only = True
    cas = list(csv.DictReader(open(DOSSIER / "CAS-30.csv", newline=""), delimiter=";"))
    for i, c in enumerate(cas, 1):
        idu = c["idu"]
        cap = {}
        p = CACHE / f"{idu}.json"
        if p.exists():
            cap = json.loads(p.read_text())
        with conn.cursor() as cur:
            cur.execute("SELECT permit_id, type, date::date, date_depot, commune, raw "
                        "FROM sitadel_permits WHERE permit_id=%s", (c["permit_id"],))
            prow = cur.fetchone()
            cur.execute("SELECT s.score, s.bande, s.cause FROM score_labuse s "
                        "WHERE s.run_label='q_v20' AND s.idu=%s", (idu,))
            srow = cur.fetchone()
            cur.execute("SELECT zone_lib, zone_fam FROM parcel_zone_plu WHERE idu=%s", (idu,))
            zrow = cur.fetchone()
            cur.execute("SELECT surface_m2 FROM parcels WHERE idu=%s", (idu,))
            parc = cur.fetchone()
        raw = prow[5] if prow else {}
        lignes = [
            f"# Cas {i:02d} — {c['permit_id']} / parcelle {idu}",
            "",
            f"**Source de l'audit** : {c['source']} · **Classement relecture** : {c['classement']}",
            "",
            "## La ligne du permis (Sit@del, vérité mairie)",
            "",
            f"- Numéro : `{prow[0] if prow else c['permit_id']}` ({prow[1] if prow else '?'}) — commune {prow[4] if prow else '?'}",
            f"- Autorisé le : {prow[2] if prow else '?'} (dépôt {prow[3] if prow else '?'})",
            f"- État Sit@del : {raw.get('etat')} (2=autorisé, 5=commencé, 6=achevé) · DAACT : {raw.get('daact') or '—'}",
            f"- Logements créés : {raw.get('nb_lgt')} · surface habitable créée : {raw.get('surf_hab')} m²",
            f"- Demandeur : {raw.get('petitioner_name') or '—'} (SIREN {raw.get('petitioner_siren') or '—'})",
            "",
            "## La fiche LABUSE (moteur de main, état du jour)",
            "",
            f"- Parcelle : {idu} — {parc[0]:.0f} m²" if parc else f"- Parcelle : {idu} (absente du cadastre servi)",
            f"- Zone PLU : {(zrow[0] if zrow else cap.get('zone')) or '?'} (famille {(zrow[1] if zrow else cap.get('zone_fam')) or '?'})",
            f"- Verdict moteur : {'CONSTRUCTIBLE' if cap.get('constructible') else 'NON CONSTRUCTIBLE'}"
            f" — {cap.get('verdict') or cap.get('cause') or '—'}",
            f"- Estimation rapide : {cap.get('sdp_max_m2') or 0:.0f} m² de plancher · emprise constructible "
            f"{cap.get('emprise_constructible_m2') or '—'} m² · niveaux max {cap.get('niveaux_max') or '—'}",
            f"- Classement servi (q_v20) : bande {srow[1] if srow else '—'} (score {srow[0] if srow else '—'}"
            f"{', ' + srow[2] if srow and srow[2] else ''})",
            "",
            "## Relecture",
            "",
            c["preuve"],
            "",
        ]
        (DEST / f"cas-{i:02d}-{c['permit_id']}.md").write_text("\n".join(lignes))
    conn.close()
    print(f"→ {DEST} ({len(cas)} fiches)")


if __name__ == "__main__":
    main()
