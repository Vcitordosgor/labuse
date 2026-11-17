"""MOTEUR-VERITE-FIX-1 — ARRÊT final : sondage de VINGT règles d'implantation à graine fixe sur
TOUTES les communes calibrées (lots 2+6), chacune prouvée par l'image de la ligne entière de la
page officielle. Télécharge au besoin le pack GPU de la commune tirée (règlement seul extrait,
zip supprimé). Sortie : sondage-final/SONDAGE-20.md + SONDAGE-Fnn-{bande,page}.png.

    python docs/audit-2026-11/moteur-verite-fix-1/scripts/sondage20.py
"""
from __future__ import annotations

import csv
import glob
import hashlib
import re
import subprocess
import unicodedata
from pathlib import Path
from xml.etree import ElementTree

FIX = Path(__file__).resolve().parents[1]
IMPL = FIX / "implantation"
REGL = FIX / "reglements"
OUT = FIX / "sondage-final"
GRAINE = "VT-FIX-SONDAGE-FINAL-20"


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def _pdf_commune(insee: str) -> Path | None:
    cand = [p for p in glob.glob(str(REGL / insee / "*.pdf"))
            if "graphique" not in p.lower() and "sanitaire" not in p.lower()
            and re.search(r"eglement", p, re.I)]
    if cand:
        return Path(sorted(cand, key=lambda p: len(p))[0])
    # téléchargement ciblé du pack GPU (source_url de plu_reglement_extrait)
    try:
        url = subprocess.run(
            ["psql", "-U", "openclaw", "-d", "labuse", "-Atc",
             f"select source_url from plu_reglement_extrait where insee='{insee}' limit 1;"],
            capture_output=True, text=True, timeout=30).stdout.strip()
    except Exception:  # noqa: BLE001
        url = ""
    if not url:
        return None
    dest = REGL / insee
    dest.mkdir(parents=True, exist_ok=True)
    zp = Path(f"/tmp/pack_{insee}.zip")
    print(f"  téléchargement pack {insee}…", flush=True)
    if subprocess.run(["curl", "-s", "-o", str(zp), "--max-time", "1200", url]).returncode != 0:
        return None
    subprocess.run(["unzip", "-o", "-j", str(zp), "*eglement*", "-d", str(dest)],
                   capture_output=True)
    zp.unlink(missing_ok=True)
    cand = [p for p in glob.glob(str(dest / "*.pdf"))
            if "graphique" not in p.lower() and re.search(r"eglement", p, re.I)]
    return Path(sorted(cand, key=lambda p: len(p))[0]) if cand else None


def lignes_page(pdf: Path, page: int):
    xml = subprocess.run(["pdftotext", "-bbox", "-f", str(page), "-l", str(page),
                          str(pdf), "-"], capture_output=True, text=True).stdout
    xml = re.sub(r'xmlns="[^"]+"', "", xml, count=1)
    root = ElementTree.fromstring(xml)
    mots = [(float(w.get("yMin")), float(w.get("yMax")), w.text or "")
            for w in root.iter("word")]
    lignes: dict[int, list] = {}
    for y0, y1, t in mots:
        lignes.setdefault(int(y0 // 4), []).append((y0, y1, t))
    out = [(min(g[0] for g in grp), max(g[1] for g in grp),
            _norm(" ".join(g[2] for g in grp))) for grp in lignes.values()]
    out.sort()
    return out


def main() -> None:
    OUT.mkdir(exist_ok=True)
    rows = []
    for f in sorted(IMPL.glob("974*.csv")):
        for r in csv.DictReader(open(f, newline=""), delimiter=";"):
            cit = (r.get("citation_verbatim") or "").strip()
            if cit and not cit.startswith("[YAML") and (r.get("page_pdf") or "").strip():
                rows.append(r)
    rows.sort(key=lambda r: hashlib.md5(
        f"{r['insee']}|{r['zone']}|{r['cote']}|{GRAINE}".encode()).hexdigest())
    tirage = rows[:20]
    from PIL import Image
    md = [f"# SONDAGE FINAL — 20 règles d'implantation, graine {GRAINE}",
          f"(univers : {len(rows)} règles à citation officielle, toutes communes calibrées)", ""]
    for i, r in enumerate(tirage, 1):
        pdf = _pdf_commune(r["insee"])
        statut = "PDF du règlement indisponible — citation verbatim seule"
        if pdf is not None:
            try:
                page = int(float(r["page_pdf"]))
                cles = _norm(r["citation_verbatim"])[:120].split()[:8]
                lgs = lignes_page(pdf, page)
                def score(l):
                    return sum(1 for m in cles if m in l[2])
                best = [l for l in sorted(lgs, key=lambda l: -score(l))
                        if score(l) >= max(3, len(cles) // 2)][:4]
                subprocess.run(["pdftoppm", "-f", str(page), "-l", str(page), "-r", "150",
                                "-png", str(pdf), str(OUT / f"SONDAGE-F{i:02d}-page")], check=True)
                pagepng = next(OUT.glob(f"SONDAGE-F{i:02d}-page*.png"))
                pagepng = pagepng.rename(OUT / f"SONDAGE-F{i:02d}-page.png")
                if best:
                    y0 = min(l[0] for l in best) - 6
                    y1 = max(l[1] for l in best) + 6
                    img = Image.open(pagepng)
                    k = 150 / 72.0
                    img.crop((0, max(0, int(y0 * k)), img.width,
                              min(img.height, int(y1 * k)))).save(OUT / f"SONDAGE-F{i:02d}-bande.png")
                    statut = f"bande extraite ({len(best)} ligne(s), {pdf.name} p.{page})"
                else:
                    statut = f"ligne non localisée — page entière fournie ({pdf.name} p.{page})"
            except Exception as e:  # noqa: BLE001
                statut = f"échec d'extraction : {str(e)[:60]}"
        md += [f"## F{i:02d} — {r['insee']} zone {r['zone']} ({r['cote']}) · mode `{r['mode']}`"
               + (f" · `{r['condition_modelable']}`" if (r.get('condition_modelable') or '').strip() else ""),
               f"- Article {r['article']} · page PDF {r['page_pdf']} · {statut}",
               f"- Citation : « {r['citation_verbatim'][:300]} »",
               f"- Images : `SONDAGE-F{i:02d}-bande.png` / `SONDAGE-F{i:02d}-page.png`", ""]
    (OUT / "SONDAGE-20.md").write_text("\n".join(md))
    bandes = len(list(OUT.glob("*-bande.png")))
    print(f"→ {OUT} : {bandes}/20 bandes extraites — SONDAGE-20.md")


if __name__ == "__main__":
    main()
