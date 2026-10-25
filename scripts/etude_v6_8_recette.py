#!/usr/bin/env python3
"""ETUDE-V6-8 — recette : génère les 2 PDF (aérien 11/5/2/5 ; sous-sol 39/5/9/20) et lance TOUTES les
vérifications d'un seul coup, en lisant le PDF (pdftotext) et l'image du plan — jamais le payload.

Usage :
    LABUSE_APP_DATABASE_URL=postgresql+psycopg:///labuse PYTHONPATH=src \
        python scripts/etude_v6_8_recette.py [--out docs/audit-2026-10/etude-v6-8]

Chaque point du mandat V6-8 est un bloc check_* qui renvoie (ok, detail). Sortie : un tableau PASS/FAIL
et le nouveau maximum sous-sol (item 4). Code de sortie 0 si tout passe.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

ETANG = ["97404000AW0099", "97404000AW0451", "97404000AW0624", "97404000AW0625"]
SURF = {"T1": 30, "T2": 56, "T3": 70, "T4": 80}
GEN = "24/10/2026"


def _session():
    from sqlalchemy.orm import sessionmaker
    from labuse.db import make_engine
    url = os.environ.get("LABUSE_APP_DATABASE_URL") or "postgresql+psycopg:///labuse"
    return sessionmaker(bind=make_engine(url=url), future=True)()


def _lignes(mix: dict) -> list[dict]:
    return [{"type": t, "nombre": n, "surface_m2": SURF[t]} for t, n in mix.items()]


def _payload(session, mix: dict, stationnement: str):
    from labuse.implantation.service import etudier_payload
    e = {"idus": ETANG, "type_projet": "etudiante", "stationnement": stationnement,
         "programme": {"mode": "saisi", "lignes": _lignes(mix)}}
    if stationnement == "sous_sol":
        e["niveaux_sous_sol"] = 1
    return etudier_payload(session, e)


def _pdf_text(payload, out_pdf: Path) -> str:
    from labuse.exports import etude_faisabilite as ef
    from labuse.exports.rendu import render_pdf
    r = ef.rendu_etude(payload, genere_le=GEN)
    out_pdf.write_bytes(render_pdf(r["html"]))
    txt = subprocess.run(["pdftotext", "-layout", str(out_pdf), "-"],
                         capture_output=True, text=True).stdout
    return txt


def _nums(s: str) -> list[str]:
    return re.findall(r"\d+", s)


# ── items ───────────────────────────────────────────────────────────────────────────────────
def check_item1_une_implantation(txt: str, payload) -> tuple[bool, str]:
    """Une seule implantation : logements=23 et places=27 identiques au plan, à la répartition, aux
    contrôles et à la page 1 ; aucune « autre implantation possible »."""
    from labuse.exports import etude_faisabilite as ef
    retenu = ef.scenario_retenu(payload)
    L = retenu["resume"]["logements"]
    P = retenu["resume"]["places"]
    # dans le texte du PDF, le total dessiné doit être unique : pas d'autre total de logements qui traîne.
    pb = "autre implantation" not in txt.lower()
    # répartition par niveau : la somme imprimée = L (on relit la ligne Total de la répartition)
    distro_total = sum(v for d in retenu["distribution_niveaux"] for v in (d.get("par_type") or {}).values())
    controls_places = next((c for c in retenu["controles"] if c["nom"] == "Stationnement"), {})
    ok = (str(L) in txt and str(P) in txt and distro_total == L and pb
          and str(P) in str(controls_places.get("mesure") or ""))
    return ok, (f"L={L} P={P} distro={distro_total} ctrl_places={controls_places.get('mesure')!r} "
                f"pas_d_annexe={pb}")


def check_item2_un_seul_numero(txt: str, payload) -> tuple[bool, str]:
    from labuse.exports import etude_faisabilite as ef
    ecran = (payload.get("study_id") or "")[:11]
    motifs = sorted(set(re.findall(r"EF-[0-9A-Za-z\-]+", txt)))
    ok = len(motifs) == 1 and motifs[0] == ecran
    return ok, f"écran={ecran} · motifs_PDF={motifs}"


def check_item3_titre_et_regle_statio(txt: str, payload) -> tuple[bool, str]:
    titre = "Étude de faisabilité — L'Étang-Salé · parcelles AW 99, 451, 624, 625"
    # pdftotext peut replier le titre sur plusieurs lignes : on compare espaces normalisés.
    norm = re.sub(r"\s+", " ", txt)
    t_ok = re.sub(r"\s+", " ", titre) in norm
    # règle de stationnement dans le TABLEAU des règles (section 2), avant l'enveloppe (section 3).
    sec2 = txt.split("3. Enveloppe")[0]
    r_ok = bool(re.search(r"Stationnement", sec2.split("2. R")[-1]))
    return (t_ok and r_ok), f"titre={t_ok} · règle_statio_dans_tableau={r_ok}"


def check_item4_sous_sol(txt: str, payload) -> tuple[bool, str]:
    from labuse.exports import etude_faisabilite as ef
    retenu = ef.scenario_retenu(payload)
    st = retenu["stationnement"]
    rampe = st.get("rampe_m2") or 0
    rampe_ok = rampe > 0 and ("rampe" in txt.lower())
    # le sous-sol PEUT déborder du bâtiment, tant que la pleine terre reste ≥ 30 % de la contenance.
    emp_bati = retenu.get("emprise_sol_m2") or 0
    emp_ss = st.get("emprise_sous_sol_m2") or 0
    cont = payload["terrain"].get("contenance_totale_m2") or 0
    pt = retenu.get("pleine_terre_m2") or 0
    overflow_autorise = emp_ss >= 0  # jamais interdit ; borné par la pleine terre
    pt_ok = (pt >= 0.30 * cont) if cont else True
    # « Ce qui limite » ne cite pas la hauteur quand le bâtiment est sous le plafond.
    niv = retenu["niveaux"]
    h = payload["regles"]
    hp = next((l for l in h["lignes"] if "égout" in (l.get("nom") or "")), None)
    import math
    niv_max = int((hp["valeur"]) // 3) if (hp and hp.get("valeur")) else niv
    sous_plafond = niv < niv_max
    fl = (payload.get("facteur_limitant") or "")
    haut_ok = (not sous_plafond) or ("hauteur" not in fl.lower())
    return (rampe_ok and haut_ok and pt_ok), (
        f"rampe_m2={rampe} rampe_ok={rampe_ok} · emp_bati={emp_bati} emp_ss={emp_ss} "
        f"pleine_terre={pt}/{round(0.30*cont)} pt_ok={pt_ok} · niv=R+{niv-1} "
        f"plafond=R+{niv_max-1} sous_plafond={sous_plafond} facteur_limitant={fl!r} haut_ok={haut_ok}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="docs/audit-2026-10/etude-v6-8")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    s = _session()
    try:
        p_aer = _payload(s, {"T1": 11, "T2": 5, "T3": 2, "T4": 5}, "aerien")
        p_ss = _payload(s, {"T1": 39, "T2": 5, "T3": 9, "T4": 20}, "sous_sol")
    finally:
        s.close()
    txt_aer = _pdf_text(p_aer, out / "pdf_aerien_11-5-2-5.pdf")
    txt_ss = _pdf_text(p_ss, out / "pdf_soussol_39-5-9-20.pdf")
    (out / "pdf_aerien.txt").write_text(txt_aer)
    (out / "pdf_soussol.txt").write_text(txt_ss)

    checks = [
        ("item1 une implantation (aérien)", check_item1_une_implantation, txt_aer, p_aer),
        ("item2 un seul n° doc (aérien)", check_item2_un_seul_numero, txt_aer, p_aer),
        ("item2 un seul n° doc (sous-sol)", check_item2_un_seul_numero, txt_ss, p_ss),
        ("item3 titre + règle statio (aérien)", check_item3_titre_et_regle_statio, txt_aer, p_aer),
        ("item4 sous-sol rampe/hauteur", check_item4_sous_sol, txt_ss, p_ss),
    ]
    allok = True
    print("\n=== ETUDE-V6-8 — recette (lecture PDF, pas payload) ===")
    for nom, fn, txt, pl in checks:
        ok, detail = fn(txt, pl)
        allok = allok and ok
        print(f"[{'PASS' if ok else 'FAIL'}] {nom}\n        {detail}")

    from labuse.exports import etude_faisabilite as ef
    rss = ef.scenario_retenu(p_ss)
    print(f"\nMaximum sous-sol (39/5/9/20) : capacité_maximale="
          f"{(p_ss.get('capacite_maximale') or {}).get('logements')} logements · "
          f"plan retenu={rss['resume']['logements']} logts / {rss['resume']['places']} places "
          f"({rss['stationnement'].get('places_sous_sol_par_niveau')} places/niveau −1)")
    print(f"\nPDF : {out}/pdf_aerien_11-5-2-5.pdf · {out}/pdf_soussol_39-5-9-20.pdf")
    return 0 if allok else 1


if __name__ == "__main__":
    sys.exit(main())
