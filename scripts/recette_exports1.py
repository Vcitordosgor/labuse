#!/usr/bin/env python
"""EXPORTS-1 — test doré de la recette (mandat, § Recette).

Génère les 6 exports + fiche.json des 4 témoins par les VRAIES routes (TestClient, base
réelle), extrait les grandeurs nommées des PDF (pdftotext -layout) et les confronte à la
référence écran. Divergence = échec du lot (exit 1).

Lancement (env audit, hors venv cassé) :
  DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib \
  PYTHONPATH=/Users/openclaw/Desktop/labuse-merge/src \
  /Users/openclaw/miniforge3/envs/labusedb/bin/python scripts/recette_exports1.py [--dir SORTIE]

Points de recette couverts : 1 (génération), 2 (grandeurs vs fiche.json), 3 (mots interdits),
4 (zéros sans couverture — contrôles ciblés). Le point 5 (requêtes de l'annexe) se rejoue à part.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TEMOINS = ["97415000BO0852", "97401000AD0554", "97416000DY0106", "97411000AV0110"]


def _mots_interdits() -> list[str]:
    """0-bis — la liste VERSIONNÉE (config/mots_interdits.yaml) ; repli embarqué si absente.
    « Non ICPE » toléré dans le tableau ICPE seul — contrôle spécifique plus bas."""
    p = Path(__file__).resolve().parents[1] / "config" / "mots_interdits.yaml"
    if p.exists():
        try:
            import yaml
            return list(yaml.safe_load(p.read_text())["mots"])
        except Exception:  # noqa: BLE001 — repli embarqué, jamais un contrôle muet
            pass
    return ["run m1", "EPSG", "ST_Buffer", "à_vérifier", "deja_bati", "reglt",
            " pt)", "scoring", "fiabilité suivie", "doctrine", "page corrigée",
            "L'IA", "fiche commune", "parcours Flash", "MOBPRO", "n 11"]


MOTS_INTERDITS = _mots_interdits()

ERREURS: list[str] = []
MOTS_TROUVES: list[str] = []    # 0-bis — contrôle distinct (sonde) : les hits « mots interdits »


def ko(msg: str) -> None:
    ERREURS.append(msg)
    print(f"  ✗ {msg}")


def ok(msg: str) -> None:
    print(f"  ✓ {msg}")


def generer(idu: str, outdir: Path) -> dict:
    """Les 6 exports + fiche.json par les vraies routes (même chemin que l'audit)."""
    from fastapi.testclient import TestClient
    from labuse.api.app import app
    from labuse.flash.report import generate_flash_report
    c = TestClient(app)
    d = outdir / idu
    d.mkdir(parents=True, exist_ok=True)
    fiche = c.get(f"/parcels/{idu}").json()
    (d / "fiche.json").write_text(json.dumps(fiche, ensure_ascii=False, indent=1))
    for name, url in (("fiche.pdf", f"/parcels/{idu}/export.pdf"),
                      ("dossier.pdf", f"/dossier/{idu}.pdf"),
                      ("banquier.pdf", f"/dossier-banquier/{idu}.pdf"),
                      ("argumentaire.pdf", f"/argumentaire/{idu}.pdf")):
        r = c.get(url)
        if r.status_code != 200:
            ko(f"{idu}/{name} : HTTP {r.status_code}")
            continue
        (d / name).write_bytes(r.content)
    try:
        p = generate_flash_report(idu, order_ref=f"RECETTE-{idu[-6:]}", force=True)
        shutil.copy(p, d / "flash.pdf")
    except Exception as exc:  # noqa: BLE001
        ko(f"{idu}/flash.pdf : {exc}")
    for f in d.glob("*.pdf"):
        subprocess.run(["pdftotext", "-layout", str(f), str(f.with_suffix(".txt"))], check=True)
    return fiche


def _num(s: str) -> int:
    return int(s.replace(" ", "").replace(" ", ""))


def verifier_temoin(idu: str, d: Path, fiche: dict) -> None:
    txts = {f.stem: f.read_text(encoding="utf-8", errors="replace") for f in d.glob("*.txt")}
    tout = "\n".join(txts.values())

    # ── pt 3 : mots interdits (liste versionnée — contrôle DISTINCT pour la sonde, 0-bis) ──
    for mot in MOTS_INTERDITS:
        for doc, t in txts.items():
            if mot in t:
                MOTS_TROUVES.append(f"{idu}/{doc} : « {mot} »")
                ko(f"{idu}/{doc} : mot interdit « {mot} »")
    # « Non ICPE » : toléré UNIQUEMENT dans le tableau ICPE (ligne portant une distance en m)
    for doc, t in txts.items():
        for line in t.splitlines():
            if "Non ICPE" in line and not re.search(r"\d+\s*m\b", line):
                ko(f"{idu}/{doc} : « Non ICPE » hors tableau : {line.strip()[:80]}")

    # ── pt 2 : grandeurs nommées vs fiche.json ──
    # surface (l'écran fait foi)
    surf = fiche.get("surface_m2")
    if surf:
        attendu = f"{_num(f'{round(surf):,}'.replace(',', ' ')):,}".replace(",", " ")
        if f"{attendu} m²" not in tout and f"{round(surf)} m²" not in tout:
            ko(f"{idu} : surface écran {round(surf)} m² introuvable dans les PDF")
        else:
            ok(f"surface {round(surf)} m² cohérente")
    # prix ancien : LA phrase unique (marche_synthese) — même valeur partout, pas d'autre
    ms = fiche.get("marche_synthese") or ""
    m = re.search(r"Prix ancien médian (\d[\d ]*) €/m²", ms)
    if m:
        val = m.group(1).strip()
        deviants = set()
        for doc, t in txts.items():
            for hit in re.findall(r"Prix ancien médian (\d[\d ]*) €/m²", t):
                if hit.strip() != val:
                    deviants.add((doc, hit.strip()))
        if deviants:
            ko(f"{idu} : prix ancien divergent {deviants} (écran : {val})")
        else:
            ok(f"prix ancien unique {val} €/m² (écran = PDF)")
    # un seul « neuf » : « Neuf VEFA » a quitté la fiche (Q3)
    if "Neuf VEFA" in txts.get("fiche", ""):
        ko(f"{idu}/fiche : « Neuf VEFA » encore servi (Q3)")
    # médiane locale : jamais annoncée sans valeur (1.5)
    for doc, t in txts.items():
        if re.search(r"Médiane €/m² observée,", t):
            ko(f"{idu}/{doc} : médiane locale annoncée sans sa valeur (1.5)")

    # ── lot 3 : potentiel — la table orpheline ne fuit plus, écran = Dossier ──
    if idu == "97415000BO0852":
        for doc, t in txts.items():
            if re.search(r"\b127(\.\d)?\s*m²", t):
                ko(f"{idu}/{doc} : « 127 m² » (table orpheline parcel_residuel_bati) encore servi")
    pt = fiche.get("potentiel_transformation") or {}
    sdp_ecran = pt.get("sdp_residuelle_m2")
    m3 = re.search(r"Au sol \(SDP résiduelle du run servi\)\s+(\d[\d ]*) m²", txts.get("dossier", ""))
    if sdp_ecran is not None and m3:
        if abs(_num(m3.group(1)) - round(float(sdp_ecran))) > 1:
            ko(f"{idu} : SDP résiduelle écran {sdp_ecran} ≠ Dossier {m3.group(1)}")
        else:
            ok(f"SDP résiduelle écran = Dossier ({m3.group(1)} m²)")
    if idu == "97416000DY0106":
        if sdp_ecran not in (0, 0.0, None):
            ko(f"{idu} : SDP écran devrait être 0 par garde (zone N), servie {sdp_ecran}")
        if "zone_non_constructible" not in json.dumps(fiche, ensure_ascii=False) and \
           "zone_non_constructible" not in txts.get("dossier", ""):
            ko(f"{idu} : cause zone_non_constructible absente (T3)")

    # ── lot 2 : plus jamais un « appartement » à surface d'immeuble dans un tableau ──
    for doc, t in txts.items():
        for line in t.splitlines():
            m2 = re.search(r"Appartement\s+(\d[\d ]*) m²", line)
            if m2 and _num(m2.group(1)) > 200:
                ko(f"{idu}/{doc} : « Appartement {m2.group(1)} m² » servi (agrégat multi-lots, 2.2/2.3)")

    # ── pt 4 : zéros ciblés ──
    # la ligne « Secteur — X : médiane — » doit porter l'étiquette secondaire à proximité
    if re.search(r"Secteur — .* : médiane — €/m²", txts.get("fiche", "")) and \
            "secteur cadastral" not in txts.get("fiche", ""):
        ko(f"{idu}/fiche : médiane secteur « — » sans étiquette de couverture")


def main() -> int:
    outdir = Path(sys.argv[sys.argv.index("--dir") + 1]) if "--dir" in sys.argv \
        else Path(tempfile.mkdtemp(prefix="recette-exports1-"))
    print(f"Recette EXPORTS-1 → {outdir}")
    for idu in TEMOINS:
        print(f"== {idu}")
        fiche = generer(idu, outdir)
        verifier_temoin(idu, outdir / idu, fiche)
    print(f"\n{'ÉCHEC — ' + str(len(ERREURS)) + ' divergence(s)' if ERREURS else 'RECETTE VERTE'}")
    # 0-bis — sortie machine pour la sonde (cas nocturne coherence-robinets) : divergences et
    # mots interdits SÉPARÉS (deux contrôles distincts du verdict).
    if "--json" in sys.argv:
        Path(sys.argv[sys.argv.index("--json") + 1]).write_text(json.dumps(
            {"temoins": TEMOINS, "erreurs": ERREURS, "mots_interdits": MOTS_TROUVES,
             "n_erreurs_hors_mots": len([e for e in ERREURS if "mot interdit" not in e]),
             "n_mots_interdits": len(MOTS_TROUVES)}, ensure_ascii=False, indent=1))
    return 1 if ERREURS else 0


if __name__ == "__main__":
    sys.exit(main())
