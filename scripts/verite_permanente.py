"""VÉRITÉ-PERMANENTE-1 (début) — branche les HARNAIS des six lots de NU-5 dans le banc de nuit.

Un seul runner invoque, chaque nuit, les harnais rejouables des audits NU5-A..F (déjà écrits par
les auditeurs, rangés sous `docs/audit-2026-11/nu-5/<lot>/`). But : qu'une régression sur l'un des
six axes (outils, documents, mails, Radar, fiches communes, accessibilité) devienne VISIBLE sans
ré-audit manuel.

Chaque lot déclare sa COMMANDE et ses PRÉREQUIS. Un harnais dont les prérequis manquent (API non
lancée, node/Playwright absent, Brevo non configuré) est **sauté AVEC MOTIF** (jamais un faux rouge).
Un harnais lancé qui échoue (rc ≠ 0) est **rouge**. Sortie : un résumé par lot + un code de retour
global (≠ 0 si au moins un harnais lancé a échoué) → le job `verite-permanente` l'escalade.

Appelé par le job nocturne `verite-permanente` (labuse jobs run verite-permanente) et rejouable à la
main : `python -m scripts.verite_permanente`.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
NU5 = RACINE / "docs" / "audit-2026-11" / "nu-5"
PY = sys.executable
DB_URL = os.environ.get("LABUSE_DATABASE_URL") or os.environ.get("LABUSE_TEST_DATABASE_URL")
# PROD-SUITE-1 — psql ne comprend PAS le dialecte SQLAlchemy (`postgresql+psycopg://…`) : il
# prendrait toute la chaîne pour un nom de base (« database … does not exist », lot D rouge en prod).
# Le lot D (psql -f) reçoit donc une URL libpq (`postgresql://…`), le dialecte retiré.
DB_URL_PSQL = re.sub(r"^postgresql\+\w+://", "postgresql://", DB_URL) if DB_URL else DB_URL
BASE = os.environ.get("LABUSE_HARNAIS_BASE")        # ex. http://127.0.0.1:9790 (API déjà lancée)
CHROMIUM = os.environ.get("LABUSE_CHROMIUM")        # binaire chromium pour Playwright (lot F)


def _env_py() -> dict:
    e = dict(os.environ)
    e["PYTHONPATH"] = str(RACINE / "src") + os.pathsep + e.get("PYTHONPATH", "")
    if BASE:
        e["BASE"] = BASE
    return e


#: (lot, description, prérequis → raison-de-saut-ou-None, commande, cwd).
def _harnais() -> list[dict]:
    return [
        {"lot": "A", "desc": "16 outils × 20 parcelles-pièges",
         "skip": None if BASE else "API non lancée (poser LABUSE_HARNAIS_BASE)",
         "cmd": [PY, str(NU5 / "A/harnais/harness.py")], "cwd": RACINE, "env": _env_py()},
        {"lot": "B", "desc": "chaque document page par page",
         "skip": None if BASE else "API non lancée (poser LABUSE_HARNAIS_BASE)",
         "cmd": [PY, str(NU5 / "B/harnais/harnais.py")], "cwd": NU5 / "B/harnais", "env": _env_py()},
        {"lot": "C", "desc": "catalogue des 21 mails (dry-run, read-only)",
         "skip": None if os.environ.get("BREVO_API_KEY") else "Brevo non configuré (BREVO_API_KEY)",
         "cmd": [PY, str(NU5 / "C/harnais_mails.py")], "cwd": RACINE, "env": _env_py()},
        {"lot": "D", "desc": "Radar annonce par annonce (SQL lecture seule)",
         "skip": None if (DB_URL and shutil.which("psql")) else "DB/psql indisponible",
         "cmd": ["psql", DB_URL_PSQL or "", "-X", "-v", "ON_ERROR_STOP=1", "-f", str(NU5 / "D/harnais.sql")],
         "cwd": RACINE, "env": dict(os.environ)},
        {"lot": "E", "desc": "fiche commune 24 communes (recompute cohérence)",
         "skip": None if DB_URL else "DB indisponible (LABUSE_DATABASE_URL)",
         "cmd": [PY, str(NU5 / "E/harnais/extraire.py")], "cwd": NU5 / "E/harnais", "env": _env_py()},
        {"lot": "F", "desc": "accessibilité (axe-core + Playwright)",
         "skip": (None if (shutil.which("node") and CHROMIUM and BASE)
                  else "node/LABUSE_CHROMIUM/front non disponibles"),
         "cmd": ["node", str(NU5 / "F/harness/audit_a11y.mjs")],
         "cwd": NU5 / "F/harness", "env": dict(os.environ)},
    ]


def run() -> dict:
    """Joue les 6 harnais. Renvoie {lots: [...], lances, verts, rouges, sautes}."""
    resultats = []
    for h in _harnais():
        if h["skip"]:
            resultats.append({"lot": h["lot"], "etat": "saute", "motif": h["skip"]})
            print(f"  [{h['lot']}] SAUTÉ — {h['skip']}")
            continue
        try:
            p = subprocess.run(h["cmd"], cwd=str(h["cwd"]), env=h["env"],
                               capture_output=True, text=True, timeout=1800)
            etat = "vert" if p.returncode == 0 else "rouge"
            queue = (p.stdout or p.stderr or "").strip().splitlines()[-3:]
            resultats.append({"lot": h["lot"], "etat": etat, "rc": p.returncode, "queue": queue})
            print(f"  [{h['lot']}] {etat.upper()} (rc={p.returncode}) — {h['desc']}")
        except Exception as exc:  # noqa: BLE001 — un harnais qui plante = rouge, jamais un traceback nu
            resultats.append({"lot": h["lot"], "etat": "rouge", "erreur": f"{type(exc).__name__}: {exc}"})
            print(f"  [{h['lot']}] ROUGE — {type(exc).__name__}: {exc}")
    verts = sum(1 for r in resultats if r["etat"] == "vert")
    rouges = sum(1 for r in resultats if r["etat"] == "rouge")
    sautes = sum(1 for r in resultats if r["etat"] == "saute")
    print(f"\nVÉRITÉ-PERMANENTE — {verts} vert · {rouges} rouge · {sautes} sauté "
          f"(sur 6 lots)")
    return {"lots": resultats, "lances": verts + rouges, "verts": verts,
            "rouges": rouges, "sautes": sautes}


def main() -> None:
    r = run()
    sys.exit(1 if r["rouges"] else 0)


if __name__ == "__main__":
    main()
