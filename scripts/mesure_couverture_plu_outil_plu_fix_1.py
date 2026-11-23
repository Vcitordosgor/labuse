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
-- OUTIL-PLU-FIX-4 (critère 3) — part indexée À L'ARTICLE vs AU CHAPITRE (gros bloc), et drapeau
-- « règlement peu structuré » (il reste des blocs > 10 pages sans niveau plus fin).
ALTER TABLE plu_couverture ADD COLUMN IF NOT EXISTS pct_article int;
ALTER TABLE plu_couverture ADD COLUMN IF NOT EXISTS pct_chapitre int;
ALTER TABLE plu_couverture ADD COLUMN IF NOT EXISTS peu_structure boolean;
ALTER TABLE plu_couverture ADD COLUMN IF NOT EXISTS gros_blocs text;
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
        # OUTIL-PLU-FIX-2 (C4) — « page de texte » = page avec un CORPS réel APRÈS retrait du chrome
        # (en-têtes/pieds courants). Une page qui ne porte que le bandeau répété (ex. La Possession
        # p.110-164, ~70 c. d'en-tête, zéro corps) n'est PAS du texte à indexer : ne pas la compter au
        # dénominateur (sinon couverture faussement basse).
        clean, _zb = P._clean_pages(P._pages(str(cands[-1])))
        txt = [i + 1 for i in range(n) if len(clean[i].strip()) > 40]
        img = [i + 1 for i in range(n)
               if len(clean[i].strip()) <= 40 and len(d[i].get_images()) > 0]
        # OUTIL-PLU-FIX-3 (C4) — l'article étant l'unité (multi-pages), une page est « indexée » si elle
        # figure dans le page_map d'un article (toutes les pages que l'article traverse), pas seulement
        # sa page de début. Métrique honnête : pages réellement couvertes par un extrait servi.
        idx = {int(r[0]) for r in s.execute(text(
            "SELECT DISTINCT (e->>1)::int FROM plu_reglement_extrait, "
            "jsonb_array_elements(page_map) e WHERE insee=:i AND page_map IS NOT NULL"), {"i": insee})}
        # pages couvertes À L'ARTICLE (extraits de < 6 pages) vs seulement par un gros bloc (≥ 6 pages).
        art = {int(r[0]) for r in s.execute(text(
            "SELECT DISTINCT (e->>1)::int FROM plu_reglement_extrait, jsonb_array_elements(page_map) e "
            "WHERE insee=:i AND page_map IS NOT NULL AND coalesce(page_fin-page_debut,0) < 6"), {"i": insee})}
        txt_idx = sorted(set(txt) & idx)
        art_idx = sorted(set(txt) & art)
        absentes = [p for p in txt if p not in idx]
        pct = round(100 * len(txt_idx) / len(txt)) if txt else 0
        pct_art = round(100 * len(art_idx) / len(txt)) if txt else 0
        pct_chap = max(0, pct - pct_art)
        gros = s.execute(text(
            "SELECT article_ref, page_debut, page_fin FROM plu_reglement_extrait "
            "WHERE insee=:i AND page_fin-page_debut >= 10 ORDER BY page_fin-page_debut DESC"), {"i": insee}).all()
        peu = len(gros) > 0
        gros_txt = "; ".join(f"{(gr[0] or '?')[:32]} p.{gr[1]}-{gr[2]}" for gr in gros[:12])
        lab, nul = s.execute(text(
            "SELECT count(*) FILTER (WHERE zone IS NOT NULL), count(*) FILTER (WHERE zone IS NULL) "
            "FROM plu_reglement_extrait WHERE insee=:i"), {"i": insee}).first()
        tot_lab += lab; tot += lab + nul
        s.execute(text("""
            INSERT INTO plu_couverture (insee,pages_total,pages_texte,pages_image,pages_indexees,
                pct_indexe,pct_article,pct_chapitre,peu_structure,gros_blocs,pages_absentes,mesure_le)
            VALUES (:i,:pt,:px,:pim,:pidx,:pct,:pa,:pc,:peu,:gros,:abs,:now)
            ON CONFLICT (insee) DO UPDATE SET pages_total=:pt,pages_texte=:px,pages_image=:pim,
                pages_indexees=:pidx,pct_indexe=:pct,pct_article=:pa,pct_chapitre=:pc,
                peu_structure=:peu,gros_blocs=:gros,pages_absentes=:abs,mesure_le=:now
        """), {"i": insee, "pt": n, "px": len(txt), "pim": len(img), "pidx": len(txt_idx),
               "pct": pct, "pa": pct_art, "pc": pct_chap, "peu": peu, "gros": gros_txt,
               "abs": _ranges(absentes), "now": now})
        print(f"{insee:5} {mil[insee]['commune'][:20]:20} {n:4} {len(txt):4} {len(img):3} "
              f"{pct:3}% art{pct_art:3}%{' PEU-STRUCT' if peu else ''}  {lab}/{lab+nul}  {gros_txt[:40]}")
    s.commit()
    print(f"\nTOTAL étiquetés {tot_lab}/{tot} ({round(100*tot_lab/tot)}%)")
    s.close()
    print("COUVERTURE_DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
