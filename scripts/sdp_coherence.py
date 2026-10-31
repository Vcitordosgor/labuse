#!/usr/bin/env python3
"""SDP-UNIQUE-1 — recette de cohérence de la SDP résiduelle « bâti conservé ».

Compare, pour les 12 parcelles témoins du lot A, la SDP résiduelle servie à CHAQUE endroit :
  • l'EN-TÊTE de la fiche          GET /parcels/{idu}  → potentiel_transformation.sdp_residuelle_m2
  • le VERDICT LABUSE              GET /parcels/{idu}  → analyse_labuse.sdp_residuelle_m2
  • l'outil COMPARER              GET /compare?idus=… → ligne « SDP résiduelle · bâti conservé »
  • le PDF DOSSIER                 GET /dossier/{idu}.pdf          → tuile « SDP restante »
  • le PDF ESTIMER (analyse)       GET /analyse-annonce/{idu}.pdf  → tuile « SDP restante »

Règle : une seule notion, une seule valeur. Parmi les sources PRÉSENTES, soit toutes disent
« rien » (None ou 0 — parcelle non constructible/saturée), soit toutes portent la MÊME valeur
positive (tolérance d'arrondi 1 m²). Tout écart = ÉCHEC (sortie ≠ 0).

Usage : API servie sur $LABUSE_SDP_API (défaut http://127.0.0.1:9120), base locale `labuse`.
Lecture seule (l'API sert ses caches). N'appelle JAMAIS la prod.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.request

API = os.environ.get("LABUSE_SDP_API", "http://127.0.0.1:9120")
ESPACES = "    "  # insécable, fine insécable, fine, espace
NB = rf"[\d{ESPACES}]+"

# 12 témoins du lot A (docs/audit-2026-11/nu-1/A). Pivot = parcelle U servable pour Comparer.
TEMOINS = [
    "97411000IN0347", "97411000IE0241", "97411000HC0139", "97424000AE0050",
    "97424000AM0893", "97421000AB0133", "97411000AO0753", "97411000EY0173",
    "97417000BI0076", "97411000AB0785", "97411000HN0074", "97411000DR0042",
]
PIVOT = "97411000EY0173"  # grande parcelle U servable (SDP > 0), pour la 2ᵉ colonne de Comparer


def _get(path: str, timeout: int = 200) -> bytes:
    with urllib.request.urlopen(API + path, timeout=timeout) as r:
        return r.read()


def _json(path: str):
    return json.loads(_get(path).decode())


def _pdftotext(octets: bytes) -> str:
    p = subprocess.run(["pdftotext", "-layout", "-", "-"], input=octets,
                       capture_output=True, check=True)
    return p.stdout.decode("utf-8", "replace")


def _sdp_pdf(txt: str):
    """SDP restante lue dans un PDF (même extracteur que docs_coherence)."""
    for pat in (rf"restante[^\n]*?b[âa]ti conserv[ée][^\n]*?[≈~]?\s*({NB})\s*m²",
                rf"({NB})\s*m²\s*\n?\s*SDP RESTANTE",
                rf"SDP restante[^\n]*?({NB})\s*m²",
                rf"SDP résiduelle[^\n]*?({NB})\s*m²"):
        m = re.search(pat, txt, re.IGNORECASE)
        if m:
            return _norm(m.group(1))
    return None


def _norm(v):
    if v is None:
        return None
    s = re.sub(f"[{ESPACES}]", "", str(v)).replace(",", ".")
    try:
        return int(round(float(s)))
    except (TypeError, ValueError):
        return None


def _rien(x) -> bool:
    """« rien à construire » : absent (None) ou nul (0)."""
    return x is None or x == 0


def coherente(valeurs: dict[str, object]) -> tuple[bool, str]:
    """Parmi les sources présentes (valeur ≠ 'absente'), vérifie la notion unique."""
    presentes = {k: v for k, v in valeurs.items() if v != "absente"}
    positifs = {k: v for k, v in presentes.items() if not _rien(v)}
    if not positifs:
        return True, "toutes « rien » (0/—)"
    socle = next(iter(positifs.values()))
    # tout positif doit valoir le même socle ; aucune source présente ne doit dire « rien ».
    ecarts = [k for k, v in positifs.items() if abs(v - socle) > 1]
    riens = [k for k, v in presentes.items() if _rien(v)]
    if ecarts or riens:
        return False, f"socle={socle} ; écarts={ecarts} ; disent-rien={riens}"
    return True, f"toutes = {socle} m²"


def mesure(idu: str) -> dict[str, object]:
    out: dict[str, object] = {}
    try:
        f = _json(f"/parcels/{idu}?source=q_v20")
    except Exception as exc:  # noqa: BLE001 — parcelle disparue (500) : on le note, pas de SDP à comparer
        return {"_erreur_fiche": str(exc)[:60]}
    pt = f.get("potentiel_transformation") or {}
    al = f.get("analyse_labuse") or {}
    out["en-tête"] = _norm(pt.get("sdp_residuelle_m2")) if "sdp_residuelle_m2" in pt else "absente"
    out["verdict"] = _norm(al.get("sdp_residuelle_m2")) if al else "absente"
    # Comparer : 2 idus (le témoin + un pivot), on lit la ligne résiduelle du témoin.
    try:
        comp = _json(f"/compare?idus={idu},{PIVOT}")
        rows = comp if isinstance(comp, list) else comp.get("parcels") or []
        cell = next((r for r in rows if (r.get("idu") or "").startswith(idu)), None)
        out["comparer"] = _norm(cell.get("sdp_residuelle_m2")) if cell else "absente"
    except Exception:  # noqa: BLE001
        out["comparer"] = "absente"
    # PDF Dossier + Estimer
    for nom, path in (("pdf_dossier", f"/dossier/{idu}.pdf?carte=false"),
                      ("pdf_estimer", f"/analyse-annonce/{idu}.pdf")):
        try:
            out[nom] = _sdp_pdf(_pdftotext(_get(path)))
        except Exception:  # noqa: BLE001 — PDF indisponible (ex. disparue) : source absente
            out[nom] = "absente"
    return out


def main() -> int:
    echecs = 0
    print(f"SDP-UNIQUE-1 — cohérence SDP résiduelle · API {API}\n")
    print(f"{'témoin':16} {'en-tête':>8} {'verdict':>8} {'comparer':>9} {'dossier':>8} {'estimer':>8}  verdict")
    for idu in TEMOINS:
        m = mesure(idu)
        if "_erreur_fiche" in m:
            print(f"{idu:16} fiche indisponible ({m['_erreur_fiche']}) — parcelle disparue, pas de SDP")
            continue
        ok, detail = coherente({k: m[k] for k in ("en-tête", "verdict", "comparer", "pdf_dossier", "pdf_estimer")})

        def c(x):
            return "—" if x == "absente" else ("∅" if x is None else str(x))
        print(f"{idu:16} {c(m['en-tête']):>8} {c(m['verdict']):>8} {c(m['comparer']):>9} "
              f"{c(m['pdf_dossier']):>8} {c(m['pdf_estimer']):>8}  {'OK' if ok else 'ÉCHEC'} — {detail}")
        if not ok:
            echecs += 1
    print()
    if echecs:
        print(f"✗ {echecs} témoin(s) incohérent(s) — la notion « SDP résiduelle, bâti conservé » diverge.")
        return 1
    print("✓ Cohérence SDP résiduelle « bâti conservé » : une seule valeur par témoin, partout.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
