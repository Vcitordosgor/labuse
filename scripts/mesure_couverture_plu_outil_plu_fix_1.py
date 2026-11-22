"""OUTIL-PLU-FIX-1 (LOT 3+4) — mesure la COUVERTURE d'indexation par commune et peuple plu_couverture.

Pour chaque commune servie : pages totales du PDF, pages de TEXTE (> 40 c. non blancs), pages IMAGE
seules (texte trivial + images → scan/plan, « non indexé (image) »), pages réellement indexées (au
moins un extrait), % indexé = pages_indexees / pages_texte, et la liste compacte des pages de texte
ABSENTES. Écrit tout dans plu_couverture (lu par l'API /plu-annuaire/communes → part indexée à l'écran).
Émet aussi le tableau couverture + le décompte d'étiquettes (justes / absentes) pour le compte-rendu.
"""
from __future__ import annotations

import datetime as _dt
import os
import pathlib
import sys

import fitz
import yaml
from sqlalchemy import text

sys.path.insert(0, "src")
from labuse.db import session_factory            # noqa: E402
from labuse.ingestion import plu_ingest as P     # noqa: E402


def _pages_couvertes(path: str) -> set[int]:
    """Pages PDF réellement couvertes par un extrait — par SPAN (de la page de début à la page de fin
    du segment), pas seulement la page de début : un article sur 4 pages couvre ses 4 pages."""
    pages = P._pages(path)
    clean, _zb = P._clean_pages(pages)
    starts, pos = [], 0
    for i, t in enumerate(clean):
        starts.append((pos, i + 1)); pos += len(t)
    flat = "".join(clean)

    def page_of(off: int) -> int:
        pg = 1
        for o, p in starts:
            if o <= off:
                pg = p
            else:
                break
        return pg

    heads = list(P._HEADER.finditer(flat))
    cov: set[int] = set()
    for i, m in enumerate(heads):
        ref = P._norm(m.group(1))
        end = heads[i + 1].start() if i + 1 < len(heads) else len(flat)
        body_net = len(P.re.sub(r'\s', '', flat[m.start():end]))
        if ref.upper().startswith("ZONE") and body_net < 60:
            continue
        for p in range(page_of(m.start()), page_of(max(m.start(), end - 1)) + 1):
            cov.add(p)
    return cov

ROOT = pathlib.Path(__file__).resolve().parents[1]
PDFDIR = pathlib.Path(os.path.expanduser(
    os.environ.get("LABUSE_PLU_PDF_DIR", "~/Desktop/labuse/data/plu_reglements")))

_DDL = """
CREATE TABLE IF NOT EXISTS plu_couverture (
    insee          varchar(5) PRIMARY KEY,
    pages_total    int, pages_texte int, pages_image int,
    pages_indexees int, pct_indexe int,
    pages_absentes text, mesure_le timestamptz
);
"""


def _ranges(nums: list[int]) -> str:
    nums = sorted(nums)
    out, i = [], 0
    while i < len(nums):
        j = i
        while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
            j += 1
        out.append(str(nums[i]) if i == j else f"{nums[i]}-{nums[j]}")
        i = j + 1
    return ", ".join(out)


def main() -> int:
    mil = yaml.safe_load((ROOT / "config" / "plu_millesimes.yaml").read_text())["communes"]
    s = session_factory()()
    for stmt in _DDL.strip().split(";"):
        if stmt.strip():
            s.execute(text(stmt))
    s.commit()
    now = _dt.datetime.now(_dt.timezone.utc)

    docs = {r[0]: r[1] for r in s.execute(text(
        "SELECT insee, string_agg(DISTINCT document, ',') FROM plu_reglement_extrait GROUP BY insee"))}
    print(f"{'insee':5} {'commune':22} {'pg':>4} {'txt':>4} {'img':>4} {'idx':>4} {'%':>4}  "
          f"{'étiq':>9}  absentes")
    tot_lab = tot = 0
    for insee in sorted(docs):
        # PDF : on prend le règlement sur disque (le document actif peut n'exister que logiquement)
        cands = sorted(PDFDIR.glob(f"{insee}_[Rr]eglement_*.pdf"))
        if not cands:
            continue
        d = fitz.open(str(cands[-1]))
        n = d.page_count
        txt = [i + 1 for i in range(n) if len(d[i].get_text().strip()) > 40]
        img = [i + 1 for i in range(n)
               if len(d[i].get_text().strip()) <= 40 and len(d[i].get_images()) > 0]
        idx = _pages_couvertes(str(cands[-1]))      # pages couvertes par SPAN d'extrait
        txt_idx = sorted(set(txt) & idx)
        absentes = [p for p in txt if p not in idx]
        pct = round(100 * len(txt_idx) / len(txt)) if txt else 0
        lab, nul = s.execute(text(
            "SELECT count(*) FILTER (WHERE zone IS NOT NULL), count(*) FILTER (WHERE zone IS NULL) "
            "FROM plu_reglement_extrait WHERE insee=:i"), {"i": insee}).first()
        tot_lab += lab; tot += lab + nul
        s.execute(text("""
            INSERT INTO plu_couverture (insee,pages_total,pages_texte,pages_image,pages_indexees,
                pct_indexe,pages_absentes,mesure_le)
            VALUES (:i,:pt,:px,:pim,:pidx,:pct,:abs,:now)
            ON CONFLICT (insee) DO UPDATE SET pages_total=:pt,pages_texte=:px,pages_image=:pim,
                pages_indexees=:pidx,pct_indexe=:pct,pages_absentes=:abs,mesure_le=:now
        """), {"i": insee, "pt": n, "px": len(txt), "pim": len(img), "pidx": len(txt_idx),
               "pct": pct, "abs": _ranges(absentes), "now": now})
        print(f"{insee:5} {mil[insee]['commune'][:22]:22} {n:4} {len(txt):4} {len(img):4} "
              f"{len(txt_idx):4} {pct:3}%  {lab:4}/{lab+nul:<4}  {_ranges(absentes)[:48]}")
    s.commit()
    print(f"\nTOTAL étiquetés {tot_lab}/{tot} ({round(100*tot_lab/tot)}%)")
    s.close()
    print("COUVERTURE_DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
