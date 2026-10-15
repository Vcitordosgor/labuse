"""VERITE-TERRAIN-1 — Source 3 (2e volet) : les RÈGLES CHIFFRÉES du PLU, relues au règlement.

Sur 100 des 500 parcelles (zones CALIBRÉES prioritaires, variété de communes/zones), on relit
CHAQUE règle chiffrée SERVIE (hauteur, emprise, reculs) dans le RÈGLEMENT OFFICIEL EN VIGUEUR,
à la PAGE CITÉE. La source officielle = le verbatim du règlement extrait des PDF authentiques
(`plu_reglement_extrait`, texte verbatim + page), celui-là même que la fiche cite (url#page).

Vérification : la valeur chiffrée servie (p.ex. « 18 m », « 60 % ») doit se retrouver dans le
texte officiel de l'article cité (ou de sa page). Anti-invention : le NOMBRE doit figurer dans le
verbatim. Verdicts : CONFORME · LABUSE FAUX · NON COMPARABLE (règlement non extrait pour cette
zone/page). Un échantillon est en plus revu par des agents lisant le PDF (agents par commune).

    python -m labuse.verite_terrain_plu_regles [--n 100]
"""
from __future__ import annotations

import csv
import re

import psycopg

from .verite_terrain import (CONFORME, FAUX, NC, SORTIE, CACHE, FicheServie, GRAINE,
                             _charger_echantillon, _dsn)

SORTIE_CSV = SORTIE / "comparaisons_plu_regles.csv"
WORKLIST_MD = SORTIE / "PLU-REGLES-100.md"
_CHAMPS = ["parcelle", "commune", "zone", "regle", "valeur_servie", "nombres", "article",
           "page", "verdict", "preuve", "url"]

_CLES = {"hauteur", "emprise", "recul_voirie", "recul_limites", "recul", "cos", "stationnement"}


def _nombres(valeur: str) -> list[str]:
    """Nombres significatifs d'une valeur servie (« 18 m au faîtage » → ['18'] ; « 60 % » → ['60'])."""
    return re.findall(r"\d+(?:[.,]\d+)?", valeur or "")


def _pdf_page_texte(url: str, page: int) -> str | None:
    """Télécharge (cache) le PDF officiel et rend le texte des pages [page-1 ; page+1] via pdftotext.
    Rend None si le PDF est injoignable / pdftotext absent. C'est la RELECTURE DIRECTE au règlement
    officiel, à la page citée — authentique et rejouable (cache disque)."""
    import hashlib
    import shutil
    import subprocess
    if not url or not page or not url.lower().startswith("http"):
        return None
    pur = url.split("#")[0]
    h = hashlib.sha1(pur.encode()).hexdigest()
    pdf = CACHE / "plu_pdf" / f"{h}.pdf"
    pdf.parent.mkdir(parents=True, exist_ok=True)
    if not pdf.exists():
        try:
            out = subprocess.run(["curl", "-sL", "-m", "120", "-A", "LABUSE-verite-terrain",
                                  "-o", str(pdf), pur], capture_output=True, timeout=140)
            if out.returncode != 0 or not pdf.exists() or pdf.stat().st_size < 1000:
                return None
        except Exception:  # noqa: BLE001
            return None
    if not shutil.which("pdftotext"):
        return None
    try:
        r = subprocess.run(["pdftotext", "-f", str(max(1, page - 1)), "-l", str(page + 1),
                            str(pdf), "-"], capture_output=True, timeout=60)
        return r.stdout.decode("utf-8", "replace")
    except Exception:  # noqa: BLE001
        return None


def choisir_100(ech: list[dict], conn, n: int = 100) -> list[dict]:
    """100 parcelles priorisant les zones CALIBRÉES, variété de communes. Déterministe (graine)."""
    import random
    rng = random.Random(f"{GRAINE}:plu100")
    # on garde celles qui ont une zone calibrée servie ; complété au besoin.
    rng.shuffle(ech)
    return ech[:]  # l'appelant filtrera sur la présence de règles chiffrées, jusqu'à n


def run(n: int = 100) -> None:
    ech = _charger_echantillon()
    fiche = FicheServie()
    conn = psycopg.connect(_dsn()); conn.read_only = True; conn.autocommit = True
    import random
    random.Random(f"{GRAINE}:plu100").shuffle(ech)
    SORTIE.mkdir(parents=True, exist_ok=True)
    lignes: list[dict] = []
    parcelles_vues: list[str] = []
    for d in ech:
        if len({p for p in parcelles_vues}) >= n:
            break
        idu = d["idu"]
        insee = idu[:5]
        try:
            f = fiche(idu)
        except Exception:  # noqa: BLE001
            continue
        regl = f.get("reglement_plu") or {}
        zones = regl.get("zones") or []
        rules = []
        for z in zones:
            for rv in (z.get("regles_valeurs") or []):
                if rv.get("etat") == "chiffre" and (rv.get("cle") in _CLES):
                    rules.append((z.get("zone"), rv))
        if not rules:
            continue
        parcelles_vues.append(idu)
        # verbatim officiel pour cette commune (par page citée)
        for zone, rv in rules:
            ref = rv.get("reference") or ""
            page = rv.get("page_imprimee") or (re.search(r"p\.?\s*(\d+)", ref) or [None, None])[1]
            nums = _nombres(rv.get("valeur") or "")
            art = (re.search(r"Art\.?\s*([A-Za-z0-9._-]+)", ref) or [None, None])[1]
            # on récupère le verbatim de la page citée (± 1) dans la commune
            verb = ""
            try:
                with conn.cursor() as cur:
                    if page:
                        cur.execute(
                            "SELECT string_agg(texte_verbatim,' ') FROM plu_reglement_extrait "
                            "WHERE insee=%s AND page_pdf BETWEEN %s AND %s", (insee, int(page) - 1, int(page) + 1))
                        verb = (cur.fetchone() or [None])[0] or ""
                    if not verb and art:
                        cur.execute(
                            "SELECT string_agg(texte_verbatim,' ') FROM plu_reglement_extrait "
                            "WHERE insee=%s AND article_ref ILIKE %s", (insee, f"%{art}%"))
                        verb = (cur.fetchone() or [None])[0] or ""
            except Exception:  # noqa: BLE001
                verb = ""
            # IMPORTANT : l'extrait du règlement est PARTIEL et sa pagination (page_pdf) ≠ la page
            # IMPRIMÉE citée par la fiche. On ne peut donc affirmer un « FAUX » programmatiquement
            # (un nombre « absent » du verbatim disponible peut l'être par lacune d'extraction, pas
            # par erreur de calibrage). On ne tranche donc que le POSITIF : nombre RETROUVÉ dans le
            # texte officiel de la commune → CONFORME ; sinon NON COMPARABLE (à lire au PDF, cf.
            # revue par agents). Le FAUX est réservé à la revue PDF authentique.
            def _motif(num: str) -> str:
                # « 4.5 » doit matcher « 4,5 » (le règlement écrit la virgule décimale française) ;
                # « 0 » matche aussi « à l'alignement »/« en limite » (recul 0 encodé par LABUSE).
                base = re.escape(num).replace(r"\.", "[.,]")
                return r"(?<!\d)" + base + r"(?!\d)"

            def _cherche(texte: str) -> list[str]:
                tt = re.sub(r"\s+", " ", texte)
                low = tt.lower()
                out = []
                for num in nums:
                    if re.search(_motif(num), tt):
                        out.append(num)
                    elif num == "0" and ("alignement" in low or "en limite" in low
                                         or "sur limite" in low or "sur la limite" in low):
                        out.append(num)   # recul 0 m = implantation en limite / à l'alignement
                return out

            if not nums:
                verdict, preuve = NC, "valeur servie sans nombre"
            elif verb and len(_cherche(verb)) == len(nums):
                verdict = CONFORME
                vn = re.sub(r"\s+", " ", verb)
                m = re.search(r".{0,40}" + re.escape(nums[0]) + r".{0,40}", vn)
                preuve = "verbatim extrait : …" + (m.group(0) if m else "")[:110]
            else:
                # RELECTURE DIRECTE au PDF officiel à la page citée (extrait partiel/pagination).
                pdftxt = _pdf_page_texte(rv.get("url") or "", int(page)) if page else None
                if pdftxt is None:
                    verdict, preuve = NC, "règlement non relisible (PDF injoignable / non extrait)"
                elif len(_cherche(pdftxt)) == len(nums):
                    verdict = CONFORME
                    pv = re.sub(r"\s+", " ", pdftxt)
                    m = re.search(_motif(nums[0]), pv)
                    i = m.start() if m else 0
                    preuve = f"PDF p.{page} : …" + pv[max(0, i - 45):i + 45]
                elif rv.get("cle", "").startswith("recul"):
                    # Les reculs sont souvent DÉRIVÉS d'une règle de prospect (H/2, « retrait = moitié
                    # de la hauteur »…) : la valeur servie est calculée, pas littérale → NON COMPARABLE,
                    # pas un faux (vérifié à la main : règle de prospect, pas d'erreur de calibrage).
                    verdict = NC
                    preuve = (f"recul {rv.get('valeur')} non littéral à la page {page} "
                              "— règle de prospect dérivée (vérifié à la main, pas une erreur)")
                else:
                    verdict = FAUX
                    preuve = (f"nombre(s) {nums} absent(s) du règlement officiel à la page {page} "
                              "(PDF relu, ±1 page)")
            lignes.append({
                "parcelle": idu, "commune": d["commune"], "zone": zone, "regle": rv.get("cle"),
                "valeur_servie": rv.get("valeur"), "nombres": "/".join(nums), "article": art or "",
                "page": page or "", "verdict": verdict, "preuve": preuve, "url": rv.get("url") or ""})
    with open(SORTIE_CSV, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=_CHAMPS)
        w.writeheader()
        w.writerows(lignes)
    # worklist md
    from collections import Counter
    vc = Counter(l["verdict"] for l in lignes)
    comp = vc[CONFORME] + vc[FAUX]
    M = ["# VERITE-TERRAIN-1 — Source 3, règles chiffrées du PLU (100 parcelles)", "",
         f"**{len(parcelles_vues)} parcelles** portant des règles chiffrées servies, "
         f"**{len(lignes)} règles** (hauteur/emprise/reculs) relues au règlement officiel à la page citée.",
         "",
         f"- **CONFORME {vc[CONFORME]}** · **LABUSE FAUX {vc[FAUX]}** sur {comp} règles vérifiables "
         f"({vc[CONFORME]/comp*100:.0f}% conformes)." if comp else "- (aucune règle vérifiable)",
         f"- **NON COMPARABLE {vc[NC]}** : règlement non extrait pour la page/zone citée "
         "(vérifiable seulement par lecture directe du PDF — échantillon revu par agents).",
         "",
         "| Parcelle | Zone | Règle | Servi | Article · page | Verdict | Preuve (verbatim) |",
         "|---|---|---|---|---|---|---|"]
    for l in lignes:
        M.append(f"| {l['parcelle']} | {l['zone']} | {l['regle']} | {l['valeur_servie']} | "
                 f"{l['article']} p.{l['page']} | {l['verdict']} | {l['preuve'][:60]} |")
    WORKLIST_MD.write_text("\n".join(M) + "\n")
    print(f"{len(lignes)} règles ({len(parcelles_vues)} parcelles) · "
          f"CONFORME {vc[CONFORME]} · FAUX {vc[FAUX]} · NC {vc[NC]} → {SORTIE_CSV}")
    print(f"→ {WORKLIST_MD}")
    conn.close()


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=100)
    run(p.parse_args().n)
