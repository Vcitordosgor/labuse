"""PLU-CALIBRAGE-3 — AUDIT DE PÉREMPTION (lecture seule, LIVE contre le GPU).

Une commune qui calcule sur un règlement ABROGÉ donne des chiffres FAUX en production. Pour
chacune des 23 communes dotées d'un PLU, on compare la date du document CALIBRÉ
(`plu_destinations/<insee>_*.yaml` meta.document_gpu / millesime) à la date du document COURANT
servi par le GPU en direct (api/gpu/document?partition=DU_<insee>). Si le GPU sert plus récent
que le calibrage → PÉRIMÉE (le calibrage est sur une version abrogée).

Usage : PYTHONPATH=src .venv/bin/python qa/plu_calibrage3_peremption.py
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import yaml  # noqa: E402

DEST = Path(__file__).resolve().parents[1] / "config" / "plu_destinations"
SORTIE = Path(__file__).resolve().parents[1] / "captures" / "plu-calibrage3" / "PEREMPTION.md"


def _date(s: str) -> str:
    m = re.search(r"(\d{8})", str(s or "").replace("-", ""))
    return m.group(1) if m else ""


def _gpu_courant(insee: str):
    """(idurba courant, date) servi par le GPU en direct, ou (None, '') si injoignable/RNU."""
    try:
        out = subprocess.run(["curl", "-sS", "-m", "40",
                              f"https://apicarto.ign.fr/api/gpu/document?partition=DU_{insee}"],
                             capture_output=True, text=True, timeout=45).stdout
        d = json.loads(out)
        feats = d.get("features", []) if isinstance(d, dict) else (d or [])
        idurbas = []
        for f in feats:
            p = f.get("properties", f) if isinstance(f, dict) else {}
            nm = p.get("name") or p.get("idurba") or ""
            if _date(nm):
                idurbas.append((nm, _date(nm)))
        if not idurbas:
            return None, ""
        idurbas.sort(key=lambda x: x[1])
        return idurbas[-1]                # le plus récent servi
    except Exception:
        return None, ""


def main() -> int:
    lignes = ["# PLU-CALIBRAGE-3 — audit de péremption (LIVE contre le GPU)\n"]
    table = ["| insee | commune | calibré (document_gpu) | GPU courant | verdict |",
             "| --- | --- | --- | --- | --- |"]
    perimees = []
    injoignables = []
    n = 0
    for p in sorted(DEST.glob("974??_*.yaml")):
        insee = p.name[:5]
        meta = (yaml.safe_load(p.read_text(encoding="utf-8")) or {}).get("meta") or {}
        cal_idurba = meta.get("document_gpu") or ""
        cal_date = _date(cal_idurba) or _date(meta.get("millesime"))
        commune = meta.get("commune") or p.stem[6:]
        gpu_idurba, gpu_date = _gpu_courant(insee)
        n += 1
        if not gpu_date:
            verdict = "GPU injoignable / RNU"
            injoignables.append(insee)
        elif not cal_date:
            verdict = "calibrage sans date"
        elif gpu_date > cal_date:
            verdict = f"**PÉRIMÉE** (GPU {gpu_date} > calibré {cal_date})"
            perimees.append((insee, commune, cal_idurba, gpu_idurba))
        elif gpu_date < cal_date:
            verdict = "calibré plus récent que GPU (catalogue en retard)"
        else:
            verdict = "à jour"
        table.append(f"| {insee} | {commune} | {cal_idurba or '—'} | {gpu_idurba or '—'} | {verdict} |")

    lignes.append(f"**{len(perimees)} commune(s) PÉRIMÉE(S)** sur {n} "
                  f"({len(injoignables)} GPU injoignable/RNU).\n")
    if perimees:
        lignes.append("Communes PÉRIMÉES (calcul sur un règlement abrogé → chiffres faux en prod) :")
        for insee, commune, cal, gpu in perimees:
            lignes.append(f"- **{insee} {commune}** : calibré `{cal}` → GPU sert `{gpu}`")
        lignes.append("")
    lignes += table
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    SORTIE.write_text("\n".join(lignes) + "\n", encoding="utf-8")
    print(f"{len(perimees)} périmée(s) sur {n} · {len(injoignables)} injoignable/RNU")
    for insee, commune, cal, gpu in perimees:
        print(f"  PÉRIMÉE {insee} {commune}: calibré {cal} → GPU {gpu}")
    print(f"→ {SORTIE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
