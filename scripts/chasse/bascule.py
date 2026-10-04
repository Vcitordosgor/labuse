"""CHASSE-1 angle 6 — test de bascule (BASE DE TEST labuse_chasse1 UNIQUEMENT).

    python -m scripts.chasse.bascule   # → docs/audit-2026-10/CHASSE-1/BASCULE.csv

Preuve structurelle que tous les lecteurs écoutent le même pointeur :
  1. lecture de chaque lecteur sous le run A (résiduel run_seq 1, scoring q_v11_m137) ;
  2. bascule : `is_served` → run_seq 2 (SDP +1000) en base de TEST, et
     `scoring_run` → q_v99b (tier brûlante) dans config/served_manifest.json + served_run.txt
     (fichiers du worktree, RESTAURÉS par git checkout en fin de script) ;
  3. relecture SANS redémarrer l'app : tout lecteur qui montre encore la valeur A = DISCORDANT
     structurel (pointeur figé, cache, calcul à part) ;
  4. millésime : data_sources.source_millesime (DVF) changé en base de TEST → les libellés
     de millésime doivent suivre ;
  5. remise à l'état initial (DB de test + fichiers config).

⚠ Préconditions : AUCUN autre banc en cours (le manifeste est partagé par toute app du
worktree) ; l'app est instanciée EN-PROCESS sur LABUSE_DATABASE_URL=labuse_chasse1.
"""
from __future__ import annotations

import csv
import os
import pathlib
import subprocess

RACINE = pathlib.Path(__file__).resolve().parents[2]
SORTIE = RACINE / "docs" / "audit-2026-10" / "CHASSE-1" / "BASCULE.csv"
DSN_TEST = "postgresql://openclaw@localhost:5432/labuse_chasse1"
IDU = "97415000AB0001"
MANIFESTE = RACINE / "config" / "served_manifest.json"
SERVED_TXT = RACINE / "config" / "served_run.txt"

os.environ["LABUSE_DATABASE_URL"] = "postgresql+psycopg://openclaw@localhost:5432/labuse_chasse1"
os.environ["LABUSE_RATE_LIMIT_OFF"] = "1"


def _sql(q: str) -> None:
    subprocess.run(["psql", DSN_TEST, "-c", q], check=True, capture_output=True)


def _git_restore() -> None:
    subprocess.run(["git", "-C", str(RACINE), "checkout", "--",
                    "config/served_manifest.json", "config/served_run.txt"], check=True)


def _lecteurs(fetch, client) -> dict:
    """Chaque lecteur → (valeur SDP / tier / run) sous forme comparable."""
    out = {}
    fiche = fetch(f"/parcels/{IDU}")
    pot = fiche.get("potentiel_transformation") or {}
    out["fiche.sdp_residuelle"] = pot.get("sdp_residuelle_m2")
    out["fiche.tier_v2"] = (fiche.get("score_v2") or {}).get("tier")
    cfg = fetch("/config/run")
    out["config_run"] = cfg.get("run") or cfg.get("run_label") or str(cfg)[:60]
    try:
        flt = fetch(f"/filtre?source={cfg.get('run') or 'q_v11_m137'}&limit=0")
        out["filtre.compte"] = flt.get("compte")
        out["filtre.tiers"] = str(flt.get("tiers"))[:80]
    except Exception as e:  # noqa: BLE001
        out["filtre"] = f"ERR {str(e)[:60]}"
    # lecteur résiduel robuste sur la base-squelette : le filtre capacite/sdp_min lit la vue
    # parcel_residuel → 0 parcelle si le run servi a SDP 500, 9 si 1500
    try:
        f2 = fetch(f"/filtre?source={cfg.get('run') or 'q_v11_m137'}&limit=0&sdp_min=1000")
        out["filtre.sdp_min_1000"] = f2.get("compte")
    except Exception as e:  # noqa: BLE001
        out["filtre.sdp_min_1000"] = f"ERR {str(e)[:60]}"
    try:
        srcs = fiche.get("data_sources") or []
        dvf = [s for s in srcs if "dvf" in str(s.get("name", "")).lower()]
        out["fiche.millesime_dvf"] = (dvf[0].get("source_millesime") or dvf[0].get("millesime")) if dvf else None
    except Exception:  # noqa: BLE001
        out["fiche.millesime_dvf"] = None
    return out


def main() -> None:
    from scripts.coherence.lib import client_en_process
    client, fetch = client_en_process()
    lignes = []

    avant = _lecteurs(fetch, client)
    print("AVANT :", avant)

    # — bascule résiduel (base de test) + scoring (fichiers worktree)
    # (2 UPDATE : l'index unique partiel one_served interdit le flip en un seul ordre selon
    # l'ordre physique des lignes)
    _sql("UPDATE residuel_runs SET is_served = false")
    _sql("UPDATE residuel_runs SET is_served = true WHERE run_seq = 2")
    manif = MANIFESTE.read_text()
    MANIFESTE.write_text(manif.replace('"q_v11_m137"', '"q_v99b"'))
    SERVED_TXT.write_text(SERVED_TXT.read_text().replace("q_v11_m137", "q_v99b"))
    # millésime DVF (base de test)
    _sql("UPDATE data_sources SET source_millesime='TEST-2099' WHERE name='DVF non-reg'")

    try:
        import time
        time.sleep(35.0)  # runs.current() TTL 3 s ET memo compteur /filtre 30 s — on lit après les DEUX
        apres = _lecteurs(fetch, client)
        print("APRÈS :", apres)
    finally:
        _sql("UPDATE residuel_runs SET is_served = false")
        _sql("UPDATE residuel_runs SET is_served = true WHERE run_seq = 1")
        _sql("UPDATE data_sources SET source_millesime='2025-S2' WHERE name='DVF non-reg'")
        _git_restore()
        print("état initial restauré (DB test + config git)")

    attendus = {
        "fiche.sdp_residuelle": ("500→1500", lambda a, b: a == 500 and b == 1500),
        "fiche.tier_v2": ("chaude→brulante", lambda a, b: b == "brulante"),
        "config_run": ("q_v11_m137→q_v99b", lambda a, b: "q_v99b" in str(b)),
        "fiche.millesime_dvf": ("suit TEST-2099 si affiché", lambda a, b: a is None or b != a),
    }
    for cle in sorted(set(avant) | set(apres)):
        va, vb = avant.get(cle), apres.get(cle)
        att, test = attendus.get(cle, ("doit bouger ou refléter le run B", None))
        verdict = ""
        if test is not None:
            verdict = "OK" if test(va, vb) else "DISCORDANT_STRUCTUREL"
        elif va == vb and cle.startswith(("filtre", "export")):
            verdict = "INCHANGE_A_INSTRUIRE"
        lignes.append({"lecteur": cle, "avant": str(va)[:100], "apres": str(vb)[:100],
                       "attendu": att, "verdict": verdict})

    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    with open(SORTIE, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["lecteur", "avant", "apres", "attendu", "verdict"])
        w.writeheader()
        w.writerows(lignes)
    print(f"→ {SORTIE}")
    for l in lignes:
        print(f"  {l['verdict'] or '·':24s} {l['lecteur']}: {l['avant']} → {l['apres']}")


if __name__ == "__main__":
    main()
