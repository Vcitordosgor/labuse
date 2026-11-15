"""VERITE-TERRAIN-3 — rejeu du comparateur VT-2 (volet D) sur l'état d'AUJOURD'HUI.

Réutilise `labuse.verite_terrain_capacite` (module VT-2, dans main) en remplaçant :
  · les chemins de sortie → docs/audit-2026-11/verite-terrain-3/ (cache propre, état du jour) ;
  · la lecture de cause résiduelle : run_seq SERVI lu dans config/served_manifest.json (17 = q_v20),
    plus le 16 (q_v19) câblé en dur en octobre ;
  · le cache par parcelle est ENRICHI (fourchette du moteur : emprise constructible, niveaux,
    SDP estimée, verdict) — il sert aussi aux tests 1 et 2 du mandat (aucun recalcul).

LECTURE SEULE identique à VT-2 : psycopg read_only, moteur en lecture, aucun écrit en base.

    PYTHONPATH=src python docs/audit-2026-11/verite-terrain-3/scripts/rejouer_capacite_vt3.py run [n] [insee]
    PYTHONPATH=src python docs/audit-2026-11/verite-terrain-3/scripts/rejouer_capacite_vt3.py rapport
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import labuse.verite_terrain_capacite as vt

RACINE = Path(__file__).resolve().parents[4]
SORTIE = RACINE / "docs" / "audit-2026-11" / "verite-terrain-3"
RUN_SEQ_SERVI = json.loads((RACINE / "config" / "served_manifest.json").read_text())["residuel_run_seq"]

# chemins VT-3 (le module VT-2 écrit chez VT-2 par défaut — on détourne TOUT avant usage)
vt.SORTIE = SORTIE
vt.CACHE = SORTIE / "cache" / "capacite"
vt.PERMIS_CSV = SORTIE / "PERMIS-VS-CAPACITE-NOV.csv"
vt.NOTES_MD = SORTIE / "PERMIS-VS-CAPACITE-NOV-NOTES.md"
vt.PARTIEL_CSV = SORTIE / "_capacite_partiel.csv"


def capacite_labuse_vt3(conn, idu: str) -> dict:
    """Copie de vt.capacite_labuse avec (1) run_seq servi du jour, (2) fourchette enrichie."""
    hit = vt._cache_cap(idu)
    if hit is not None:
        return hit
    out = {"idu": idu, "existe": False, "servie": False, "constructible": None,
           "sdp_max_m2": 0.0, "logements": 0, "zone": None, "zone_fam": None, "cause": None,
           # enrichissement VT-3 (tests 1/2) :
           "emprise_constructible_m2": None, "niveaux_max": None, "verdict": None,
           "run_seq_servi": RUN_SEQ_SERVI}
    with conn.cursor() as cur:
        cur.execute("SELECT id, cadastre_disparue_le FROM parcels WHERE idu=%s", (idu,))
        row = cur.fetchone()
        if not row:
            out["cause"] = "parcelle absente du cadastre servi (disparue/redécoupée)"
            vt._ecrire_cap(idu, out)
            return out
        pid, disparue = row
        out["existe"] = True
        out["servie"] = disparue is None
        cur.execute("SELECT zone_lib, zone_fam FROM parcel_zone_plu WHERE idu=%s", (idu,))
        z = cur.fetchone()
        if z:
            out["zone"], out["zone_fam"] = z[0], z[1]
        cur.execute("SELECT cause FROM parcel_residuel_runs WHERE run_seq=%s AND parcel_id=%s",
                    (RUN_SEQ_SERVI, pid))
        rc = cur.fetchone()
        res_cause = rc[0] if rc else None
    try:
        from labuse.faisabilite.db import parcel_faisabilite
        res = parcel_faisabilite(vt._session(), pid)
    except Exception as e:  # noqa: BLE001
        out["constructible"] = None
        out["cause"] = f"moteur a levé : {str(e)[:70]}"
        vt._ecrire_cap(idu, out)
        return out
    if res is None:
        out["constructible"] = False
        out["cause"] = res_cause or "hors PLU outillé — capacité non calculable"
        vt._ecrire_cap(idu, out)
        return out
    ctx, f = res
    out["constructible"] = bool(f.constructible)
    out["verdict"] = (f.verdict or "")[:160]
    out["cause_moteur"] = f.cause
    if out["zone"] is None:
        out["zone"] = getattr(ctx, "zone", None)
    fr = f.fourchette or {}
    out["emprise_constructible_m2"] = fr.get("emprise_constructible_m2")
    out["niveaux_max"] = fr.get("niveaux_max")
    if not f.constructible:
        out["cause"] = res_cause or f.cause or "non constructible (moteur)"
        vt._ecrire_cap(idu, out)
        return out
    # MOTEUR-VERITE-FIX-4 LOT 5 — « capacité à vérifier » (SDP ∅) reste INCONNUE dans les
    # fichiers de preuve : sdp None + cause, jamais 0 (AS0256/CY1293 sérialisés à 0 avant).
    if "surface_plancher_m2" not in fr:
        out["sdp_max_m2"] = None
        out["cause"] = out.get("cause") or "capacite_a_verifier"
        vt._ecrire_cap(idu, out)
        return out
    out["sdp_max_m2"] = float(fr.get("surface_plancher_m2") or 0.0)
    las = fr.get("logements_au_sol") or (0, 0)
    lss = fr.get("logements_sous_sol") or (0, 0)
    out["logements"] = int(max(las[1] if len(las) > 1 else 0, lss[1] if len(lss) > 1 else 0))
    vt._ecrire_cap(idu, out)
    return out


vt.capacite_labuse = capacite_labuse_vt3

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    insee = sys.argv[3] if len(sys.argv) > 3 else None
    print(f"run_seq servi = {RUN_SEQ_SERVI} ; sortie = {SORTIE}", flush=True)
    if cmd == "run":
        vt._run(n, insee)
    elif cmd == "rapport":
        vt._finaliser()
    else:
        raise SystemExit(f"commande inconnue : {cmd}")
