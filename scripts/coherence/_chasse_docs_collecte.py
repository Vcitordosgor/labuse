#!/usr/bin/env python3
"""CHASSE-DOCS-1 — harnais de COLLECTE (lecture seule, hors banc).

Pour chaque IDU : tire la fiche + les documents Docs + les outils parcelle (JSON),
télécharge les PDF/ZIP et en produit le pdftotext, range tout sous
docs/audit-2026-10/chasse-docs/<idu>/.

Ce script NE JUGE RIEN : il archive. L'analyse et les gardes vivent dans chasse_docs.py.
"""
from __future__ import annotations

import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8830"
RACINE = Path("docs/audit-2026-10/chasse-docs")


def _req(method: str, path: str, body: dict | None = None, timeout: int = 180):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"} if body is not None else {}
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        return resp.status, resp.read(), resp.headers.get("Content-Type", "")


def get_json(path: str):
    try:
        st, raw, _ = _req("GET", path)
        return st, json.loads(raw)
    except urllib.error.HTTPError as e:
        return e.code, {"_http_error": e.read().decode(errors="replace")[:2000]}
    except Exception as e:  # noqa: BLE001
        return 0, {"_error": repr(e)}


def post_json(path: str, body: dict):
    try:
        st, raw, _ = _req("POST", path, body)
        return st, json.loads(raw)
    except urllib.error.HTTPError as e:
        return e.code, {"_http_error": e.read().decode(errors="replace")[:2000]}
    except Exception as e:  # noqa: BLE001
        return 0, {"_error": repr(e)}


def fetch_bin(method: str, path: str, dest: Path, body: dict | None = None) -> str:
    try:
        st, raw, ctype = _req(method, path, body)
        dest.write_bytes(raw)
        return f"{st} {ctype} {len(raw)}o"
    except urllib.error.HTTPError as e:
        dest.with_suffix(dest.suffix + ".err").write_text(
            f"HTTP {e.code}\n" + e.read().decode(errors="replace")[:2000])
        return f"HTTP {e.code}"
    except Exception as e:  # noqa: BLE001
        return f"ERR {e!r}"


def pdftotext(pdf: Path) -> str:
    out = pdf.with_suffix(".pdf.txt")
    try:
        subprocess.run(["pdftotext", "-layout", str(pdf), str(out)], check=True,
                       capture_output=True, timeout=120)
        return f"ok {out.stat().st_size}o"
    except Exception as e:  # noqa: BLE001
        return f"ERR {e!r}"


def save(d: Path, name: str, st: int, obj) -> None:
    (d / f"{name}.json").write_text(json.dumps({"_status": st, "data": obj},
                                               ensure_ascii=False, indent=1))


def collecte(idu: str, voisin: str | None) -> dict:
    d = RACINE / idu
    d.mkdir(parents=True, exist_ok=True)
    rap: dict[str, str] = {}

    # 1. Fiche (référence écran)
    st, fiche = get_json(f"/parcels/{idu}")
    save(d, "fiche", st, fiche)
    rap["fiche"] = f"{st}"

    # --- Outils parcelle (JSON) ---
    jobs_get = {
        "zone_plu": f"/parcels/{idu}/zone",
        "exposition": f"/parcels/{idu}/exposition",
        "prospection_solaire": f"/modules/prospection-solaire/parcelle/{idu}",
        "gabarit_outil": f"/outils/gabarit/{idu}",
        "taxe_prefill": f"/outils/taxe-amenagement/prefill?idu={idu}",
        "permis": f"/modules/parcelle-permis?idu={idu}",
        "pieges_risques": f"/servitudes-invisibles/{idu}",
        "compare_seule": f"/compare?idus={idu}",
        "faisabilite": f"/modules/faisabilite/{idu}",
        "bilan_modele": f"/bilan/{idu}/modele",
        "verif_procedure": f"/modules/verif-procedure/{idu}",
    }
    for name, path in jobs_get.items():
        st, obj = get_json(path)
        save(d, name, st, obj)
        rap[name] = f"{st}"

    # Courrier aperçu (POST, sans envoi)
    st, obj = post_json("/courrier/composer", {"idu": idu})
    save(d, "courrier_apercu", st, obj)
    rap["courrier_apercu"] = f"{st}"

    # Étude de faisabilité — payload écran (scénario par défaut)
    st, obj = post_json("/modules/etude", {"idus": [idu]})
    save(d, "etude_faisabilite", st, obj)
    rap["etude_faisabilite"] = f"{st}"

    # --- PDF / ZIP documents ---
    pdfs = {
        "dossier": ("GET", f"/dossier/{idu}.pdf", None),
        "apporteur": ("GET", f"/apporteur/{idu}.pdf", None),
        "gabarit_doc": ("GET", f"/gabarit/{idu}.pdf", None),
        "etude_zone": ("GET", f"/etude-zone.pdf?idu={idu}", None),
        "etude_faisabilite_doc": ("POST", "/modules/etude/pdf", {"idus": [idu]}),
    }
    if voisin:
        pdfs["comparatif"] = ("GET", f"/comparatif.pdf?idus={idu},{voisin}", None)
    for name, (method, path, body) in pdfs.items():
        dest = d / f"{name}.pdf"
        rap[name + "_pdf"] = fetch_bin(method, path, dest, body)
        if dest.exists() and dest.stat().st_size > 1000:
            rap[name + "_txt"] = pdftotext(dest)

    # Pré-dossier ZIP
    dest = d / "pre_dossier.zip"
    rap["pre_dossier_zip"] = fetch_bin("GET", f"/pre-dossier/{idu}.zip", dest)

    (d / "_collecte.json").write_text(json.dumps(rap, ensure_ascii=False, indent=1))
    return rap


if __name__ == "__main__":
    pairs = [a.split(":") for a in sys.argv[1:]]
    for p in pairs:
        idu = p[0]
        voisin = p[1] if len(p) > 1 else None
        print(f"=== {idu} ===")
        rap = collecte(idu, voisin)
        for k, v in rap.items():
            print(f"  {k}: {v}")
