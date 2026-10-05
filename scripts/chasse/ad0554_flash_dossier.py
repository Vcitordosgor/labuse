"""CHASSE-2 — cas AD0554 : reproduire le « Flash ≠ Dossier » transitoire vu par VERROUS-FIX-1.

Le contrôle de la recette exports (scripts/recette_exports1.py) rend le MÊME document deux fois
(« flash » est remappé sur « dossier » par builder.construire) et exige des pdftotext identiques.
VERROUS-FIX-1 a vu UNE divergence sur 97401000AD0554 (circuit_ecarts id=8, soldée au passage
suivant) — transitoire, « reproductible seulement API lancée ».

Hypothèses instrumentées ici (les deux seuls points non déterministes du rendu) :
  H1 plan de situation — _plan_situation_html est best-effort : échec réseau IGN (ortho WMTS)
     → texte « fond cartographique momentanément indisponible » DANS le pdftotext ;
  H2 exposition — _c_exposition recalcule à CHAQUE rendu (WMS RGE ALTI + gdaldem, aucun cache)
     → échec → tuile omise du document.

Protocole : N paires (dossier, flash) rendues en-process comme la recette, phase A sans charge,
phase B avec une charge concurrente sur l'API lancée (port LABUSE_CHASSE2_API, défaut 8755) qui
génère des Dossiers d'autres parcelles (mêmes appels IGN → contention/rate-limit partagés).
Chaque paire : pdftotext -layout, diff ; on consigne la section divergente.

    python -m scripts.chasse.ad0554_flash_dossier
      → docs/audit-2026-10/CHASSE-2/raw/ad0554_repro.txt

Lecture seule : aucune écriture hors /tmp et docs/audit-2026-10/CHASSE-2/.
"""
from __future__ import annotations

import concurrent.futures as cf
import difflib
import os
import pathlib
import subprocess
import tempfile
import threading
import time
from datetime import date

IDU = "97401000AD0554"
API = os.environ.get("LABUSE_CHASSE2_API", "http://127.0.0.1:8755")
RACINE = pathlib.Path(__file__).resolve().parents[2]
SORTIE = RACINE / "docs" / "audit-2026-10" / "CHASSE-2" / "raw" / "ad0554_repro.txt"
N_PAIRES = int(os.environ.get("CHASSE2_AD0554_N", "6"))
# parcelles « charge » : les autres témoins exports (mêmes appels ortho IGN + exposition).
CHARGE = ["97415000BO0852", "97416000DY0106", "97411000AV0110"]

lignes_rapport: list[str] = []


def dire(msg: str) -> None:
    print(msg, flush=True)
    lignes_rapport.append(msg)


def _pdftotext(pdf: bytes, d: pathlib.Path, nom: str) -> str:
    p = d / f"{nom}.pdf"
    p.write_bytes(pdf)
    subprocess.run(["pdftotext", "-layout", str(p), str(p.with_suffix(".txt"))],
                   check=True, capture_output=True)
    return p.with_suffix(".txt").read_text(encoding="utf-8", errors="replace")


def _paire(fiche: dict, d: pathlib.Path, tag: str) -> tuple[bool, str]:
    """Rend (dossier, flash) comme la recette (mêmes arguments, même jour figé) ; rend
    (identiques?, diff unifié tronqué)."""
    from labuse.db import session_scope
    from labuse.exports import builder
    textes = {}
    for doc in ("dossier", "flash"):
        with session_scope() as s:
            pdf, _res = builder.generer_pdf(s, IDU, doc, fiche=fiche, jour=date(2026, 9, 5))
        textes[doc] = _pdftotext(pdf, d, f"{tag}-{doc}")
    if textes["dossier"] == textes["flash"]:
        return True, ""
    diff = "\n".join(difflib.unified_diff(
        textes["dossier"].splitlines(), textes["flash"].splitlines(),
        "dossier", "flash", lineterm="", n=1))
    return False, diff[:4000]


def _charge_api(stop: threading.Event) -> dict:
    """Charge concurrente : Dossiers PDF d'autres parcelles via l'API lancée (ortho IGN +
    exposition recalculés côté serveur → contention IGN partagée avec le rendu en-process)."""
    import httpx
    compte = {"ok": 0, "ko": 0}
    i = 0
    with httpx.Client(timeout=120.0) as c:
        while not stop.is_set():
            idu = CHARGE[i % len(CHARGE)]
            i += 1
            try:
                r = c.get(f"{API}/dossier/{idu}.pdf")
                compte["ok" if r.status_code == 200 else "ko"] += 1
            except Exception:  # noqa: BLE001
                compte["ko"] += 1
    return compte


def _marqueurs(txt_dossier: str, txt_flash: str) -> str:
    """Quel(s) des deux points non déterministes portent la divergence ?"""
    PH = "fond cartographique momentanément indisponible"
    marque = []
    if (PH in txt_dossier) != (PH in txt_flash):
        marque.append("H1 plan de situation (placeholder d'un seul côté)")
    if ("Exposition" in txt_dossier) != ("Exposition" in txt_flash):
        marque.append("H2 exposition (tuile d'un seul côté)")
    return " · ".join(marque) or "autre section (voir diff)"


def main() -> None:
    import httpx
    dire(f"CHASSE-2 AD0554 — {N_PAIRES} paires/phase, API charge = {API}")
    fiche = httpx.get(f"{API}/parcels/{IDU}", timeout=120.0).json()
    dire(f"fiche chargée : commune={fiche.get('commune')} surface={fiche.get('surface_m2')}")
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="chasse2-ad0554-"))
    bilan = {}
    for phase, avec_charge in (("A-sans-charge", False), ("B-avec-charge", True)):
        stop = threading.Event()
        fut = None
        ex = cf.ThreadPoolExecutor(max_workers=4)
        if avec_charge:
            fut = [ex.submit(_charge_api, stop) for _ in range(4)]
            time.sleep(2)  # la charge s'établit avant la première paire
        div = 0
        for k in range(N_PAIRES):
            t0 = time.time()
            memes, diff = _paire(fiche, tmp, f"{phase}-{k}")
            dt = time.time() - t0
            if memes:
                dire(f"  {phase} paire {k}: identiques ({dt:.0f}s)")
            else:
                div += 1
                td = (tmp / f"{phase}-{k}-dossier.txt").read_text()
                tf = (tmp / f"{phase}-{k}-flash.txt").read_text()
                dire(f"  {phase} paire {k}: DIVERGENCE ({dt:.0f}s) — {_marqueurs(td, tf)}")
                dire("    diff:\n" + "\n".join("    " + ligne for ligne in diff.splitlines()[:40]))
        stop.set()
        if fut:
            tot = [f.result() for f in fut]
            charge = {"ok": sum(c["ok"] for c in tot), "ko": sum(c["ko"] for c in tot)}
            dire(f"  charge API : {charge}")
        ex.shutdown(wait=False)
        bilan[phase] = div
    dire(f"bilan : {bilan} (artefacts : {tmp})")
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    SORTIE.write_text("\n".join(lignes_rapport) + "\n")


if __name__ == "__main__":
    main()
