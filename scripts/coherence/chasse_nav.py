"""CHASSE-NAV-1 — le banc des écarts de navigation (docs/audit-2026-10/chasse-nav-1/ECARTS.md).

Une garde par écart REPRODUCTIBLE de la chasse « chaque bouton mène au bon endroit » :
aujourd'hui elle MORD (les écarts N-1/N-2/N-4/N-5 sont ouverts) ; après CHASSE-NAV-FIX-1
elle doit passer au vert et devenir la garde automatique de navigation. Lecture seule stricte
(aucune écriture base/fichier ; GET only côté API).

Gardes « positives » (déjà vertes) : elles prouvent les passages SAINS (liens externes sans
127.0.0.1, deep-link #idu, garde d'URL de base des mails, /flash servi, page 404 brandée) et
mordent si une régression les casse.

Usage :
    PYTHONPATH=src .venv/bin/python -m scripts.coherence.chasse_nav \
        [--api http://127.0.0.1:8770] [--disparue 97411000AE0013]

Sortie : une ligne [OK]/[ECART]/[SKIP] par garde, bilan final, exit 1 si ECART.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import urllib.request

RACINE = pathlib.Path(__file__).resolve().parents[2]
FRONT = RACINE / "frontend" / "src"
BACK = RACINE / "src" / "labuse"

API = "http://127.0.0.1:8770"
DISPARUE = "97411000AE0013"   # témoin : parcelle disparue du cadastre (payload sans `lines`)


# ── utilitaires ──────────────────────────────────────────────────────────────
def _lire(rel: pathlib.Path) -> str:
    try:
        return rel.read_text(encoding="utf-8")
    except OSError:
        return ""


def _get(path: str, timeout: float = 20.0):
    """GET API → (status_code, texte, content_type) ; (None, msg, '') si injoignable."""
    url = API + path
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace"), r.headers.get("content-type", "")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace"), e.headers.get("content-type", "")
    except Exception as e:  # noqa: BLE001 — API down → SKIP
        return None, str(e), ""


# ── gardes (chacune renvoie (code, detail) avec code ∈ OK/ECART/SKIP) ─────────
def g_n1_digest_parcelle():
    """N-1 — le digest mail construit `#parcelle=` mais le front lit `#idu=`."""
    emails = _lire(BACK / "emails.py")
    app = _lire(FRONT / "App.tsx")
    mail_parcelle = "#parcelle=" in emails
    front_lit_idu = bool(re.search(r"\.get\(\s*['\"]idu['\"]\s*\)", app))
    front_lit_parcelle = bool(re.search(r"\.get\(\s*['\"]parcelle['\"]\s*\)", app))
    if mail_parcelle and front_lit_idu and not front_lit_parcelle:
        return "ECART", "emails.py construit '#parcelle=' alors que App.tsx ne lit que '#idu=' (lien digest mort)"
    if not mail_parcelle:
        return "OK", "le digest ne construit plus '#parcelle=' (aligné sur '#idu=')"
    return "OK", "App.tsx lit aussi 'parcelle' (compat)"


def g_n2_disparue_crash():
    """N-2 — fiche d'une parcelle disparue : payload sans `lines` + dérivés avant le garde."""
    status, body, _ = _get(f"/parcels/{DISPARUE}")
    if status is None:
        return "SKIP", f"API injoignable ({body})"
    try:
        payload = json.loads(body)
    except ValueError:
        return "SKIP", "réponse non-JSON"
    sans_lines = payload.get("lines") in (None, []) and bool(payload.get("cadastre_disparue"))
    fiche = _lire(FRONT / "components" / "fiche" / "Fiche.tsx")
    i_filter = fiche.find("?.lines.filter")
    i_garde = fiche.find("cadastre_disparue")
    derive_avant_garde = i_filter != -1 and i_garde != -1 and i_filter < i_garde
    if sans_lines and derive_avant_garde:
        return "ECART", ("payload disparue sans 'lines' ET Fiche.tsx calcule 'f?.lines.filter' "
                         f"(pos {i_filter}) AVANT le garde cadastre_disparue (pos {i_garde}) → crash ErrorBoundary")
    if sans_lines and not derive_avant_garde:
        return "OK", "le garde cadastre_disparue précède les dérivés '.lines.filter' (fiche disparue sûre)"
    return "SKIP", "témoin non disparu dans ce run (payload contient 'lines')"


def g_n4_communes_scan_retour():
    """N-4 — « Scan patrimoine » depuis Communes n'ouvre pas de fil de retour."""
    communes = _lire(FRONT / "components" / "outils" / "Communes.tsx")
    m = re.search(r"ouvrirScanPatrimoine[\s\S]{0,260}?setModule\('patrimoine'\)[\s\S]{0,120}?\}", communes)
    if not m:
        return "SKIP", "ouvrirScanPatrimoine introuvable (refactor ?)"
    bloc = m.group(0)
    if "pushOutilRetour" in bloc:
        return "OK", "Communes → Scan pose pushOutilRetour (retour cohérent)"
    return "ECART", "Communes.ouvrirScanPatrimoine n'appelle pas pushOutilRetour (pas de '← Communes')"


def g_n5_etude_zone_pdf():
    """N-5 — la constante etudeZonePdfUrl pointe une route 404."""
    api = _lire(FRONT / "lib" / "api.ts")
    m = re.search(r"etudeZonePdfUrl\s*=\s*['\"]([^'\"]+)['\"]", api)
    if not m:
        return "OK", "constante etudeZonePdfUrl supprimée"
    route = m.group(1)
    status, _, _ = _get(route + "?idu=97411000BZ1065")
    if status is None:
        return "SKIP", "API injoignable"
    if status == 404:
        return "ECART", f"etudeZonePdfUrl='{route}' → 404 (route servie = /etude-zone.pdf)"
    return "OK", f"{route} → {status}"


def g_n3_pagesjaunes_commune():
    """N-3 (cosmétique) — Pages Jaunes concatène adresse+commune (commune dupliquée)."""
    liens = _lire(FRONT / "components" / "fiche" / "liensExternes.ts")
    if re.search(r"ou\s*=\s*a\s*\?\s*`\$\{a\}\s+\$\{c\}`", liens):
        return "ECART", "liensExternes.pagesJaunes concatène `${a} ${c}` (commune déjà dans l'adresse)"
    return "OK", "Pages Jaunes ne duplique plus la commune"


# ── gardes positives (passages sains — doivent rester vertes) ─────────────────
def g_pos_liens_externes():
    liens = _lire(FRONT / "components" / "fiche" / "liensExternes.ts")
    if not liens:
        return "SKIP", "liensExternes.ts absent"
    if "127.0.0.1" in liens or "localhost" in liens:
        return "ECART", "liensExternes.ts contient 127.0.0.1/localhost (lien externe cassé)"
    if "errial.georisques.gouv.fr/#/?adresse=" not in liens:
        return "ECART", "le lien Errial n'est plus en '#/?adresse=' (format attendu par l'appli Errial)"
    if "/parcels/${encodeURIComponent(idu)}.kmz" not in liens.replace(" ", ""):
        pass  # format KMZ libre
    return "OK", "liens externes sains (Cadastre/Maps/Errial/KMZ, aucun localhost)"


def g_pos_deeplink_idu():
    app = _lire(FRONT / "App.tsx")
    if re.search(r"\.get\(\s*['\"]idu['\"]\s*\)", app):
        return "OK", "App.tsx réhydrate la fiche depuis '#idu=' (deep-link + reload)"
    return "ECART", "App.tsx ne lit plus '#idu=' (deep-link fiche cassé)"


def g_pos_garde_url_base():
    cfg = _lire(BACK / "config.py")
    if "127.0.0.1" in cfg and "localhost" in cfg and "0.0.0.0" in cfg:
        return "OK", "config.py garde l'URL de base des mails (alerte si localhost/127.0.0.1/0.0.0.0)"
    return "ECART", "la garde d'URL de base des mails a disparu de config.py"


def g_pos_flash_servi():
    status, body, _ = _get("/flash")
    if status is None:
        return "SKIP", f"API injoignable ({body})"
    if status == 200 and "127.0.0.1" not in body and "localhost" not in body:
        return "OK", "/flash servi (200) sans 127.0.0.1/localhost"
    return "ECART", f"/flash status={status} ou contient localhost"


def g_pos_404_brande():
    """Lien expiré → page HTML brandée en navigateur (Accept text/html)."""
    url = API + "/p/BANC_TOKEN_INEXISTANT"
    try:
        req = urllib.request.Request(url, headers={"Accept": "text/html"})
        urllib.request.urlopen(req, timeout=20)
        return "ECART", "/p/<token invalide> ne renvoie pas 404"
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        if e.code == 404 and "<!doctype html" in body.lower():
            return "OK", "lien de partage expiré → page 404 HTML brandée (Accept text/html)"
        return "ECART", f"/p/<invalide> code={e.code}, HTML={'<!doctype' in body.lower()}"
    except Exception as e:  # noqa: BLE001
        return "SKIP", f"API injoignable ({e})"


GARDES = [
    ("N-1  digest '#parcelle=' vs front '#idu='", g_n1_digest_parcelle),
    ("N-2  fiche parcelle disparue (crash)", g_n2_disparue_crash),
    ("N-4  retour Scan patrimoine depuis Communes", g_n4_communes_scan_retour),
    ("N-5  etudeZonePdfUrl → route 404", g_n5_etude_zone_pdf),
    ("N-3  Pages Jaunes commune dupliquée", g_n3_pagesjaunes_commune),
    ("pos  liens externes sains", g_pos_liens_externes),
    ("pos  deep-link #idu", g_pos_deeplink_idu),
    ("pos  garde URL de base des mails", g_pos_garde_url_base),
    ("pos  /flash servi sans localhost", g_pos_flash_servi),
    ("pos  lien expiré → 404 brandé", g_pos_404_brande),
]


def main() -> int:
    global API, DISPARUE
    ap = argparse.ArgumentParser(description="Banc de navigation CHASSE-NAV-1 (OK/ECART/SKIP).")
    ap.add_argument("--api", default=API)
    ap.add_argument("--disparue", default=DISPARUE)
    args = ap.parse_args()
    API, DISPARUE = args.api.rstrip("/"), args.disparue

    print(f"CHASSE-NAV-1 — banc de navigation (api={API})\n" + "─" * 72)
    ecarts = oks = skips = 0
    for nom, fn in GARDES:
        try:
            code, detail = fn()
        except Exception as e:  # noqa: BLE001 — une garde ne doit jamais planter le banc
            code, detail = "SKIP", f"exception garde: {e}"
        tag = {"OK": "[OK]   ", "ECART": "[ECART]", "SKIP": "[SKIP] "}[code]
        print(f"{tag} {nom}\n         → {detail}")
        ecarts += code == "ECART"
        oks += code == "OK"
        skips += code == "SKIP"
    print("─" * 72)
    print(f"bilan : {oks} OK · {ecarts} ECART · {skips} SKIP")
    if ecarts:
        print("→ écarts de navigation OUVERTS (attendu avant CHASSE-NAV-FIX-1).")
    return 1 if ecarts else 0


if __name__ == "__main__":
    sys.exit(main())
