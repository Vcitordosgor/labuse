"""OUTIL-PLU-FIX-1 (LOT 2+3) — réingestion des 21 règlements servis dans plu_reglement_extrait.

Aligné sur la VÉRITÉ config (config/plu_millesimes.yaml : idurba actif, date d'approbation) et sur les
PDF réellement présents sur disque (config/plu_destinations/<insee>.yaml : document + url PDF direct).
Le pack intégral (.zip) est résolu EN DIRECT sur le GPU (EN_VIGUEUR) → jamais un dépôt archivé ;
GARDE-FOU : on compare l'idurba servi par le GPU à l'idurba de plu_millesimes (identifiant, pas nom de
fichier) et on refuse d'ingérer en cas d'écart.

Cas La Possession (97408) : le PDF sur disque est l'édition 20251217 ; la version ACTIVE est
97408_PLU_20260625 (modification simplifiée n°2, texte identique — confirmé par le relecteur externe).
On extrait depuis le PDF sur disque mais on ESTAMPILLE la version active (idurba/millésime/document/liens).

Usage :
  LABUSE_DATABASE_URL=postgresql+psycopg://<user>@localhost:5432/<db> \
  LABUSE_PLU_PDF_DIR=~/Desktop/labuse/data/plu_reglements \
  PYTHONPATH=src python scripts/reingest_plu_outil_plu_fix_1.py [--dry-run] [--insee 97415]
"""
from __future__ import annotations

import argparse
import datetime as _dt
import os
import pathlib
import sys

import requests
import yaml
from sqlalchemy import text

sys.path.insert(0, "src")
from labuse.db import session_factory            # noqa: E402
from labuse.ingestion import plu_ingest          # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
PDFDIR = pathlib.Path(os.path.expanduser(
    os.environ.get("LABUSE_PLU_PDF_DIR", "~/Desktop/labuse/data/plu_reglements")))
SERVABLES = {"a_jour", "annule_partiel"}          # statuts dont le règlement est servi à la recherche


def _active_pack(insee: str) -> dict | None:
    """Pack .zip EN_VIGUEUR résolu en direct sur le GPU (même logique que l'endpoint /plu-annuaire/pack)."""
    import re
    r = requests.get("https://www.geoportail-urbanisme.gouv.fr/api/document",
                     params={"grid": insee}, headers={"User-Agent": "labuse/1.0"}, timeout=20)
    r.raise_for_status()
    docs = [d for d in r.json() if (d.get("documentType") or d.get("type")) in ("PLU", "POS", "PLUI")]
    if not docs:
        return None
    docs.sort(key=lambda d: (((d.get("effectiveStatus") or d.get("status")) == "EN_VIGUEUR"),
                             str(d.get("originalName") or "")), reverse=True)
    d = docs[0]
    idurba = str(d.get("originalName") or "")
    return {"idurba": idurba, "statut": d.get("effectiveStatus") or d.get("status"),
            "url": f"https://www.geoportail-urbanisme.gouv.fr/api/document/{d.get('id')}/download/{idurba}.zip"}


def _dest_meta(insee: str) -> dict:
    for f in (ROOT / "config" / "plu_destinations").glob(f"{insee}_*.yaml"):
        return yaml.safe_load(f.read_text()).get("meta", {}) or {}
    return {}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--insee", default=None)
    args = ap.parse_args()

    mil = yaml.safe_load((ROOT / "config" / "plu_millesimes.yaml").read_text())["communes"]
    now = _dt.datetime.now(_dt.timezone.utc).isoformat()
    s = session_factory()()
    plu_ingest.ensure_ddl(s)
    s.commit()

    total = 0
    ecarts: list[str] = []
    done: list[str] = []
    for insee, c in sorted(mil.items()):
        if args.insee and insee != args.insee:
            continue
        if c.get("statut") not in SERVABLES:
            continue
        meta = _dest_meta(insee)
        document = meta.get("document")                     # nom du règlement écrit (version active)
        pdf_url = meta.get("url")                            # lien direct .pdf
        idurba = c["idurba"]
        # PDF à extraire : d'abord le document actif s'il est sur disque, sinon le règlement de la commune.
        cand = PDFDIR / (document or "")
        if not cand.exists():
            alt = sorted(PDFDIR.glob(f"{insee}_[Rr]eglement_*.pdf"))
            if not alt:
                ecarts.append(f"{insee} : aucun PDF sur disque"); continue
            cand = alt[-1]                                   # le plus récent (La Possession → 20251217)
        # Garde-fou idurba GPU vs config (identifiant, pas nom de fichier).
        src_url = None
        try:
            pack = _active_pack(insee)
            if pack:
                src_url = pack["url"]
                if pack["idurba"].upper() != idurba.upper():
                    ecarts.append(f"{insee} : idurba GPU {pack['idurba']} ≠ config {idurba} — NON servi")
                    continue
        except Exception as e:  # noqa: BLE001
            ecarts.append(f"{insee} : GPU injoignable ({e}) — pack non résolu, repli manifest")
        if not src_url:
            src_url = f"https://www.geoportail-urbanisme.gouv.fr/ (pack {idurba})"
        if args.dry_run:
            print(f"DRY {insee} {c['commune']} idurba={idurba} doc={document} pdf={cand.name} "
                  f"pack={'ok' if src_url.endswith('.zip') else src_url}")
            done.append(insee); continue
        r = plu_ingest.ingest_commune_reglements(
            s, insee=insee, commune=c["commune"], idurba=idurba,
            millesime=c.get("date_mairie"),
            documents=[{"name": document or cand.name, "path": str(cand)}],
            source_url=src_url, pdf_url=pdf_url, fetched_at=now, commit=True, log=print)
        total += r["extraits"]; done.append(insee)

    n = s.execute(text("SELECT count(DISTINCT insee) FROM plu_reglement_extrait")).scalar()
    print(f"\n=== {len(done)} communes traitées · {total} extraits · {n} communes en base")
    if ecarts:
        print("ÉCARTS / garde-fou :")
        for x in ecarts:
            print("  -", x)
    s.close()
    print("REINGEST_DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
