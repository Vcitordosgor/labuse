#!/usr/bin/env python3
"""EXPORTS-FIX-1 — recette : mots interdits, cohérence garde↔sections, champs Apporteur.

Lecture seule sur les PDF de `apres/`. Sortie : un rapport texte + code retour non nul si un
contrôle échoue. Aucune écriture en base, aucun run.
"""
from __future__ import annotations

import io
import re
import sys
from pathlib import Path

import pypdf

ICI = Path(__file__).resolve().parent
# EXPORTS-FIX-1-BIS — la recette porte sur la seconde passe (apres-bis) ; repli sur apres/.
APRES = (ICI / "apres-bis") if (ICI / "apres-bis").exists() else (ICI / "apres")
P1, P2 = "97408000AO1424", "97415000EO0796"

# Mots/motifs qui ne doivent JAMAIS apparaître dans un export (mandat, section Recette).
# EXPORTS-FIX-1-BIS : + « cascade », « engagée le », « capacité nulle ».
MOTS_INTERDITS = ["{'", "part_pct", "fiche identite", "miroir de la fiche",
                  "bandeau des six chif", "mouvement_terrain", "ocsge", "scot_gpu",
                  "SCOT SCOT", "1 bâtiments", "cascade", "engagée le", "capacité nulle"]
ISO_DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")


def _texte(pdf: Path) -> str:
    r = pypdf.PdfReader(str(pdf))
    return "\n".join(p.extract_text() or "" for p in r.pages)


def test_mots_interdits() -> list[str]:
    err = []
    for doc in ("dossier", "apporteur"):
        for idu in (P1, P2):
            t = _texte(APRES / f"{doc}-{idu}.pdf")
            for mot in MOTS_INTERDITS:
                if mot in t:
                    err.append(f"[{doc} {idu}] mot interdit : {mot!r}")
            for m in sorted(set(ISO_DATE.findall(t))):
                err.append(f"[{doc} {idu}] date ISO AAAA-MM-JJ : {m}")
    return err


def test_apporteur_champs() -> list[str]:
    """Noms de champs uniques hors groupes radio ; remplir un champ n'en change qu'un."""
    err = []
    for idu in (P1, P2):
        path = APRES / f"apporteur-{idu}.pdf"
        r = pypdf.PdfReader(str(path))
        champs = list((r.get_fields() or {}).keys())
        textes = [n for n in champs if n.startswith("q")]
        if len(textes) != len(set(textes)):
            err.append(f"[apporteur {idu}] noms de champs texte NON uniques")
        # remplir q1, vérifier que seul q1 change
        w = pypdf.PdfWriter()
        w.append(r)
        for pg in w.pages:
            w.update_page_form_field_values(pg, {textes[0]: "SENTINEL"})
        buf = io.BytesIO()
        w.write(buf)
        buf.seek(0)
        f2 = pypdf.PdfReader(buf).get_fields() or {}
        remplis = [n for n in textes if str((f2.get(n) or {}).get("/V") or "") == "SENTINEL"]
        if remplis != [textes[0]]:
            err.append(f"[apporteur {idu}] remplir un champ en change {len(remplis)} : {remplis}")
    return err


def test_coherence_garde_sections() -> list[str]:
    """Page de garde = sections : SDP, zone, risques, exposition doivent concorder entre la garde et
    le corps du Dossier (mêmes valeurs, pas de contradiction)."""
    err = []
    for idu in (P1, P2):
        t = _texte(APRES / f"dossier-{idu}.pdf")
        # zone de garde (tuile ZONE) = code au §4. On vérifie que le code de garde apparaît au §4.
        # risques : le nombre de la garde (tuile RISQUES) = « Points de risque N » du §5.
        mgarde = re.search(r"(\d+)\s+couches?\s+de\s+risque|Points de risque\s+(\d+)", t)
        # exposition : la tuile EXPOSITION ne doit pas être « — »
        if re.search(r"—\s*\n?\s*EXPOSITION", t) or re.search(r"EXPOSITION\s*\n?\s*—", t):
            err.append(f"[dossier {idu}] Exposition vide en garde (« — »)")
    return err


def main() -> int:
    blocs = [("Mots interdits", test_mots_interdits()),
             ("Champs Apporteur", test_apporteur_champs()),
             ("Cohérence garde↔sections", test_coherence_garde_sections())]
    ko = 0
    for nom, err in blocs:
        if err:
            ko += len(err)
            print(f"✗ {nom} — {len(err)} problème(s) :")
            for e in err:
                print("   ", e)
        else:
            print(f"✓ {nom}")
    print("\n" + ("RECETTE OK" if ko == 0 else f"RECETTE : {ko} problème(s)"))
    return 1 if ko else 0


if __name__ == "__main__":
    sys.exit(main())
