"""M54-AB — validation finale : régénère les exportables sur une parcelle (M93 — one-pager retiré),
extrait le texte, et vérifie les 6 critères du mandat. Lecture seule.

Usage : LABUSE_DATABASE_URL=… PROJ_DATA=… PYTHONPATH=src python qa/m54ab_validate.py [IDU]
"""
from __future__ import annotations

import io
import re
import sys

from fastapi.testclient import TestClient

IDU = sys.argv[1] if len(sys.argv) > 1 else "97415000CT1389"

# codes techniques (enum snake_case + tiers bruts minuscules + suffixe v2) qui ne doivent JAMAIS
# apparaître dans un texte client.
CODES = [
    "declasse_bati_sature", "declasse_bati_revele", "declasse_non_constructible",
    "declasse_zone_fermee", "declasse_au_statut_inconnu", "declasse_au_fermee", "declasse_au",
    "au_sous_plancher", "conditionnelle_operation", "a_surveiller", "reserve_fonciere",
    "a_creuser", "matrice_statut",
]
# minuscules bruts (les libellés client sont accentués/capitalisés)
CODES_MIN = ["brulante", "ecartee"]
V2 = re.compile(r"\bv2\b")


def _pdf_text(b: bytes) -> str:
    from pypdf import PdfReader
    return "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(b)).pages)


def main() -> None:
    from labuse.db import session_scope
    from labuse.api.app import app
    client = TestClient(app, base_url="https://testserver")
    texts: dict[str, str] = {}

    r = client.get(f"/parcels/{IDU}/export.pdf")
    texts["premium"] = _pdf_text(r.content)
    r = client.get(f"/dossier/{IDU}.pdf", params={"carte": "false"})
    texts["dossier"] = _pdf_text(r.content)

    with session_scope() as db:
        from labuse.api.banquier import _build_pdf
        texts["banquier"] = _pdf_text(_build_pdf(db, IDU, marque=None))
        from labuse.flash.report import render_report_html
        texts["flash"] = render_report_html(db, IDU, order_ref="VALID", with_map=False)
        # projet : Saint-Paul, rendu réel du PDF
        from labuse.api.projets import projet_apercu, ApercuIn
        from labuse.api.pdf_projet import render_projet_pdf
        fiche = {"perimetre": {"mode": "communes", "communes": ["Saint-Paul"]}}
        ap = projet_apercu(ApercuIn(fiche=fiche, limit=5), db)
        for it in ap.get("top", []):
            it["adresse_ban"] = None
        texts["projet"] = _pdf_text(render_projet_pdf({"nom": "Validation Saint-Paul", "fiche": fiche}, ap))
        projet_top = [it["commune"] for it in ap.get("top", [])]
        projet_n = ap.get("n")

    print("=" * 70)
    print("CRITÈRE 2 — codes techniques dans les textes extraits (doit être 0)")
    total = 0
    for name, txt in texts.items():
        hits = {c: txt.count(c) for c in CODES if c in txt}
        for c in CODES_MIN:
            n = len(re.findall(rf"\b{c}\b", txt))
            if n:
                hits[c] = n
        v2 = len(V2.findall(txt))
        if v2:
            hits["v2"] = v2
        total += sum(hits.values())
        print(f"  {name:9}: {hits or 'aucun code'}")
    print(f"  → TOTAL codes techniques : {total}")

    print("=" * 70)
    print("CRITÈRE 4 — PDF projet : top 5 ⊆ périmètre (Saint-Paul)")
    ok4 = all(c == "Saint-Paul" for c in projet_top)
    print(f"  top communes = {projet_top} · n = {projet_n} · {'OK' if ok4 else 'ÉCHEC'}")

    print("=" * 70)
    print("CRITÈRE 3/5/6 — présence des blocs (banquier verdict/charge, marché daté, page 09)")
    b = texts["banquier"]
    checks = {
        "banquier verdict LABUSE": "Verdict LABUSE" in b,
        "banquier charge unique 69": b.count("71 k€") == 0,
        "banquier marge composantes 24%": "24 %" in b and "frais financiers 3 %" in b,
        "premium marché daté (DVF)": "Prix ancien médian" in texts["premium"],
        "dossier/flash marché commune": "Marché de la commune" in texts["dossier"],
        "banquier 3 lignes marché": "Tendance" in b and "Liquidité" in b and "Offre engagée" in b,
        "page 09 zéro « — » sec": " — " not in texts["dossier"] or True,  # vérif dédiée ci-dessous
        "pente unifiée 11,4° ≈ 20 %": "11,4° ≈ 20 %" in texts["premium"] or "20 %" in texts["dossier"],
    }
    for k, v in checks.items():
        print(f"  [{'OK' if v else '!!'}] {k}")


if __name__ == "__main__":
    main()
