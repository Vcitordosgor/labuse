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

import json
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

# OPS-3 (C) — « pas d'instance sans authentification ». Les lots A, B, F (qui tapent l'app) ne
# s'appuient plus sur une instance auth-off : ils S'AUTHENTIFIENT avec un compte de RECETTE dédié.
# L'identifiant est fixe ; le mot de passe vient de l'env (jamais commité) — /etc/labuse/labuse.env.
RECETTE_EMAIL = os.environ.get("LABUSE_RECETTE_EMAIL") or "victorlaganepro+recette@gmail.com"
RECETTE_PW = os.environ.get("LABUSE_RECETTE_PASSWORD")


def _cookie_recette(base: str) -> tuple[str | None, str | None]:
    """Se connecte au compte de recette et renvoie (cookie « labuse_session=… », motif-d'échec).
    Lecture seule : un seul POST /login, aucune écriture métier. (cookie, None) si OK ;
    (None, motif) si le mot de passe manque ou si l'app refuse les identifiants."""
    if not RECETTE_PW:
        return None, "compte de recette non configuré (LABUSE_RECETTE_PASSWORD absent de l'env)"
    import http.cookiejar
    import urllib.error
    import urllib.request

    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):  # on NE suit pas le 303 : le cookie est déjà posé
            return None

    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(_NoRedirect, urllib.request.HTTPCookieProcessor(jar))
    data = json.dumps({"identifiant": RECETTE_EMAIL, "password": RECETTE_PW}).encode()
    req = urllib.request.Request(base + "/login", data=data,
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        opener.open(req, timeout=30)
    except urllib.error.HTTPError as e:
        if e.code not in (301, 302, 303, 307, 308):
            return None, f"login recette refusé (HTTP {e.code} — identifiants/compte ?)"
    except Exception as e:  # noqa: BLE001
        return None, f"login recette impossible ({type(e).__name__}: {e})"
    for c in jar:
        if c.name == "labuse_session" and c.value:
            return f"labuse_session={c.value}", None
    return None, "login recette échoué (pas de cookie de session — compte inactif ?)"


def _env_py(cookie: str | None = None) -> dict:
    e = dict(os.environ)
    e["PYTHONPATH"] = str(RACINE / "src") + os.pathsep + e.get("PYTHONPATH", "")
    if BASE:
        e["BASE"] = BASE
        e["NU5_BASE"] = BASE   # lot B lit NU5_BASE
        e.setdefault("LABUSE_SOCLE", BASE.rstrip("/") + "/socle/")   # lot F : le front servi par l'app
    if cookie:
        e["LABUSE_HARNAIS_COOKIE"] = cookie   # lu par les harnais A/B (header Cookie) et F (addCookies)
    return e


def _auth_lot(lot: str, desc: str, cmd: list, cwd, cookie: str | None, motif: str | None,
              extra_ok: bool = True, extra_motif: str = "") -> dict:
    """Construit l'entrée d'un lot AUTHENTIFIÉ (A/B/F). Sans instance → SAUTÉ ; instance mais login
    recette en échec → ROUGE (une instance existe, l'auth doit marcher : ce n'est pas un saut)."""
    if not BASE:
        return {"lot": lot, "desc": desc, "skip": "API non lancée (poser LABUSE_HARNAIS_BASE)"}
    if not extra_ok:
        return {"lot": lot, "desc": desc, "skip": extra_motif}
    if cookie is None:
        return {"lot": lot, "desc": desc, "rouge": motif or "authentification recette indisponible"}
    return {"lot": lot, "desc": desc, "cmd": cmd, "cwd": cwd, "env": _env_py(cookie)}


#: (lot, description, prérequis → raison-de-saut-ou-None, commande, cwd).
def _harnais(cookie: str | None = None, login_motif: str | None = None) -> list[dict]:
    node_chrom = bool(shutil.which("node") and CHROMIUM)
    return [
        _auth_lot("A", "16 outils × 20 parcelles-pièges",
                  [PY, str(NU5 / "A/harnais/harness.py")], RACINE, cookie, login_motif),
        _auth_lot("B", "chaque document page par page",
                  [PY, str(NU5 / "B/harnais/harnais.py")], NU5 / "B/harnais", cookie, login_motif),
        {"lot": "C", "desc": "catalogue des 21 mails (modèle MAILS-1, rendu par l'app, read-only)",
         "skip": None,   # OPS-3 — rendu EN-PROCESS par l'app : aucun prérequis réseau (ni Brevo)
         "cmd": [PY, str(NU5 / "C/harnais_mails.py")], "cwd": RACINE, "env": _env_py()},
        {"lot": "D", "desc": "Radar annonce par annonce (SQL lecture seule)",
         "skip": None if (DB_URL and shutil.which("psql")) else "DB/psql indisponible",
         "cmd": ["psql", DB_URL_PSQL or "", "-X", "-v", "ON_ERROR_STOP=1", "-f", str(NU5 / "D/harnais.sql")],
         "cwd": RACINE, "env": dict(os.environ)},
        {"lot": "E", "desc": "fiche commune 24 communes (recompute cohérence)",
         "skip": None if DB_URL else "DB indisponible (LABUSE_DATABASE_URL)",
         "cmd": [PY, str(NU5 / "E/harnais/extraire.py")], "cwd": NU5 / "E/harnais", "env": _env_py()},
        _auth_lot("F", "accessibilité (axe-core + Playwright)",
                  ["node", str(NU5 / "F/harness/audit_a11y.mjs")], NU5 / "F/harness", cookie,
                  login_motif, extra_ok=node_chrom,
                  extra_motif="node/LABUSE_CHROMIUM non disponibles"),
    ]


def run() -> dict:
    """Joue les 6 harnais. Renvoie {lots: [...], lances, verts, rouges, sautes}.

    OPS-3 — les lots A/B/F s'authentifient d'abord avec le compte de recette (une seule session,
    partagée via `LABUSE_HARNAIS_COOKIE`). Login en échec alors qu'une instance existe = ROUGE
    (pas un saut) : « pas d'instance sans authentification »."""
    cookie, login_motif = (None, None)
    if BASE:
        cookie, login_motif = _cookie_recette(BASE)
        if cookie:
            print(f"  auth recette OK ({RECETTE_EMAIL}) — session partagée aux lots A/B/F")
        else:
            print(f"  auth recette INDISPONIBLE — {login_motif}")
    resultats = []
    for h in _harnais(cookie, login_motif):
        if h.get("skip"):
            resultats.append({"lot": h["lot"], "etat": "saute", "motif": h["skip"]})
            print(f"  [{h['lot']}] SAUTÉ — {h['skip']}")
            continue
        if h.get("rouge"):
            resultats.append({"lot": h["lot"], "etat": "rouge", "motif": h["rouge"]})
            print(f"  [{h['lot']}] ROUGE — {h['rouge']}")
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
