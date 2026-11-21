"""ETUDE-STATIONNEMENT-FIX-1 (relecture 4) — remplace la CITATION de chaque règle d'habitation ingérée par
le TEXTE VERBATIM de sa page (habitation : logement, hébergement, visiteurs, aidé), en préservant tout le
reste (valeurs, exceptions). Piloté par le contrôle jusqu'à 0 échec.

    PYTHONPATH=src:scripts python scripts/apply_verbatim_citations.py <insee_slug ...>
"""
import glob
import os
import re
import sys

import fitz
import yaml

sys.path.insert(0, "src")
sys.path.insert(0, "scripts")
from labuse.implantation import regles as R  # noqa: E402
from stationnement_citation_verbatim import pdf_for, verbatim  # noqa: E402
from stationnement_controle_pages import figures  # noqa: E402

CFG = "config/plu_destinations/"


def _is_c(z):
    return re.match(r'^\d*(U|AU)', z, re.I) is not None


def dump_block(mapping, indent):
    raw = yaml.safe_dump({"stationnement": mapping}, allow_unicode=True, sort_keys=False,
                         default_flow_style=False, width=100000)
    return [(indent + ln if ln.strip() else "") for ln in raw.rstrip("\n").split("\n")]


def apply_commune(slug):
    insee = slug[:5]
    path = CFG + slug + ".yaml"
    doc = fitz.open(pdf_for(insee)) if pdf_for(insee) else None
    if doc is None:
        print(f"{slug}: pas de PDF — ignoré")
        return 0, 0
    lines = open(path, encoding="utf-8").read().split("\n")
    zones = yaml.safe_load("\n".join(lines))["zones"]
    out, i, cur = [], 0, None
    changed = non_couvert = 0
    while i < len(lines):
        ln = lines[i]
        mz = re.match(r'^  ([A-Za-z0-9_]+):\s*$', ln)
        if mz and mz.group(1) in zones:
            cur = mz.group(1)
        ms = re.match(r'^(\s+)stationnement:\s*$', ln)
        if ms and cur and _is_c(cur):
            indent = ms.group(1)
            j = i + 1
            block = [ln]
            while j < len(lines) and (lines[j].strip() == "" or
                                      (len(lines[j]) - len(lines[j].lstrip())) > len(indent)):
                block.append(lines[j]); j += 1
            sub = "\n".join(b[len(indent):] if b.startswith(indent) else b for b in block)
            st = (yaml.safe_load(sub) or {}).get("stationnement") or {}
            b = R.charger(insee, cur).stationnement
            form = next((f for f in ("par_logement", "par_m2_sdp", "par_typologie") if st.get(f)), None)
            if b.validee and form and b.page_pdf is not None:
                v = verbatim(doc, b.page_pdf, figures(b))
                # le verbatim doit porter TOUS les chiffres appliqués, sinon on ne remplace pas (on garde la
                # citation existante et on le signale, pour ne jamais citer un texte qui ne prouve pas la valeur).
                figs = figures(b)
                def _n(s):
                    return re.sub(r'\s+', '', (s or "").lower().replace("’", "'").replace("œ", "oe"))
                if v and all(_n(f) in _n(v) for f in figs):
                    st[form]["citation"] = v
                    out.extend(dump_block(st, indent)); changed += 1
                else:
                    non_couvert += 1
                    out.extend(block)
            else:
                out.extend(block)
            i = j
            continue
        out.append(ln); i += 1
    open(path, "w", encoding="utf-8").write("\n".join(out))
    doc.close()
    print(f"{slug}: {changed} citations verbatim posées, {non_couvert} non couvertes (verbatim incomplet)")
    return changed, non_couvert


if __name__ == "__main__":
    communes = sys.argv[1:] or [os.path.basename(p)[:-5] for p in sorted(glob.glob(CFG + "974??_*.yaml"))]
    tot_c = tot_n = 0
    for slug in communes:
        if False:  # Saint-Denis confirme en vigueur (autre session), on le traite
            continue
        c, n = apply_commune(slug)
        tot_c += c; tot_n += n
    print(f"\nTOTAL : {tot_c} citations verbatim · {tot_n} non couvertes")
