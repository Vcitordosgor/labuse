"""CHASSE-3 angle 5 — l'écran et le papier : 40 parcelles tirées au sort, chaque
chiffre-clef de la FICHE (écran) confronté aux PDF servis par le build.

Documents parcellaires RÉELS : dossier, financier, apporteur, gabarit
(argumentaire / dossier-banquier / export sont des ALIAS 308 vers financier/dossier —
mesuré, noté au rapport). Comparatif et Étude de zone : joués sur 3 témoins à part.

Pour chaque figure : si le LIBELLÉ est présent dans le PDF, le nombre qui le suit doit
être le chiffre de la fiche (format FR « 1 889 », décimales « 8,2 » tolérés) — y compris
arrondi. Libellé absent = non applicable (jamais un écart silencieux : compté `absents`).
Un PDF non-PDF ou tronqué = écart. Le gabarit a le droit de REFUSER (422 explicite).

Tirage : déterministe (md5 'chasse3-a5'), stratifié — 20 SDP chiffrée > 0, 10 cause
certaine, 5 cause d'ignorance, 5 sans cause SDP 0.

Sorties : docs/audit-2026-10/CHASSE-3/ECRAN_PAPIER.csv (une ligne par comparaison).
Rejouable : LABUSE_CHASSE3_API=http://127.0.0.1:6015 python -m scripts.chasse.ecran_papier3
"""
from __future__ import annotations

import csv
import json
import os
import re
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import psycopg

BASE = os.environ.get("LABUSE_CHASSE3_API", "http://127.0.0.1:6015")
DSN = os.environ.get("LABUSE_DSN", "dbname=labuse")
OUT = Path(__file__).resolve().parents[2] / "docs" / "audit-2026-10" / "CHASSE-3"
OUT.mkdir(parents=True, exist_ok=True)

STRATES = (  # (étiquette, WHERE, n)
    ("sdp_chiffree", "r.cause IS NULL AND r.sdp_residuelle_m2 > 0", 20),
    ("cause_certaine", "split_part(r.cause,':',1) IN ('zone_non_constructible',"
     "'terrain_exigu','habitat_interdit','redhibitoire','capacite_nulle')", 10),
    ("cause_ignorance", "r.cause IS NOT NULL AND split_part(r.cause,':',1) NOT IN "
     "('zone_non_constructible','terrain_exigu','habitat_interdit','redhibitoire',"
     "'capacite_nulle')", 5),
    ("zero_sans_cause", "r.cause IS NULL AND r.sdp_residuelle_m2 = 0", 5),
)


def _api(path: str):
    url = BASE + urllib.parse.quote(path, safe="/?&=")
    with urllib.request.urlopen(url, timeout=300) as r:
        return json.loads(r.read())


def _pdf(path: str) -> tuple[int, str]:
    """(statut, texte extrait). 422 = refus explicite (texte = détail JSON)."""
    url = BASE + urllib.parse.quote(path, safe="/?&=")
    try:
        with urllib.request.urlopen(url, timeout=300) as r:
            corps = r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:300]
    if not corps.startswith(b"%PDF") or b"%%EOF" not in corps[-2048:]:
        return -1, "NON-PDF ou tronqué"
    with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
        f.write(corps)
        f.flush()
        return 200, subprocess.run(["pdftotext", "-layout", f.name, "-"],
                                   capture_output=True, text=True).stdout


def _nombre_apres(texte: str, motif: str) -> float | None:
    """Premier nombre FR qui suit `motif` (1 889 / 8,2 / 75)."""
    m = re.search(motif + r"[^\d\n]{0,60}(\d[\d  ]*(?:,\d+)?)", texte)
    if not m:
        return None
    brut = m.group(1).replace(" ", "").replace(" ", "").replace(",", ".")
    return float(brut)


def _egal(a: float | None, b: float | None) -> bool:
    if a is None or b is None:
        return False
    return abs(a - b) <= max(0.5, abs(b) * 0.001)  # arrondi d'impression toléré


def chemin(d: dict, *cles):
    for c in cles:
        d = d.get(c) if isinstance(d, dict) else None
        if d is None:
            return None
    return d


def figures_fiche(fiche: dict, fais: dict, gabarit: dict) -> dict[str, float | None]:
    """Les chiffres-clefs que l'ÉCRAN affiche (fiche + outils faisabilité/gabarit).
    NB : potentiel_transformation.hauteur_regle_m (égout, entrée de calcul) n'est PAS
    affiché au front — l'écran montre hauteurReglementaireM du Gabarit (faîtage)."""
    pa = fiche.get("prix_ancien") or {}
    return {
        "surface_m2": fiche.get("surface_m2"),
        # l'« Emprise bâtie » du Dossier = BD TOPO clippé SERVI (fiche: emprise_batie_m2) ;
        # mode_b.…emprise_bati_m2 est la notion « révélée » = max(BD TOPO, CoSIA), NOMMÉE
        # par sa source_emprise (COHERENCE-FIX-2) — deux notions, pas comparables.
        "emprise_bati_m2": fiche.get("emprise_batie_m2")
        or chemin(fiche, "le_bien", "emprise_batie_m2"),
        "hauteur_bati_m": chemin(fiche, "le_bien", "hauteur_bati_m"),
        "hauteur_regle_m": gabarit.get("hauteurReglementaireM")
        if isinstance(gabarit, dict) else None,
        "prix_ancien_median": pa.get("median"),
        "prix_ancien_n": pa.get("n"),
        "prix_sortie": chemin(fais, "prix_sortie", "prix"),
    }


# figure → (libellé PDF, documents où le libellé fait foi)
MAPPING = {
    "surface_m2": (r"Surface\b", ("apporteur",)),
    "emprise_bati_m2": (r"Emprise bâtie", ("dossier",)),
    "hauteur_bati_m": (r"Hauteur du bâti", ("dossier",)),
    "hauteur_regle_m": (r"Hauteur réglementaire", ("dossier",)),
    "prix_ancien_median": (r"Ancien bâti — secteur", ("dossier",)),
    "prix_ancien_n": (r"Ancien bâti — secteur[^\n]*?ancien,", ("dossier",)),
    "prix_sortie": (r"Prix de vente prévu", ("financier",)),
}

def _fr(n: float) -> str:
    """1625 → « 1 625 » (espace fine insécable du rendu PDF tolérée via classe)."""
    e = f"{int(round(n)):,}".replace(",", " ")
    return e


def main() -> None:
    conn = psycopg.connect(DSN)
    cur = conn.cursor()
    parcelles: list[tuple[str, str]] = []
    for strate, where, n in STRATES:
        cur.execute(f"""
            SELECT p.idu FROM parcel_residuel r JOIN parcels p ON p.id = r.parcel_id
            WHERE {where} ORDER BY md5('chasse3-a5' || p.idu) LIMIT {n}""")
        parcelles += [(strate, r[0]) for r in cur.fetchall()]
    conn.close()

    lignes: list[list] = []
    ecarts = 0
    for strate, idu in parcelles:
        try:
            fiche = _api(f"/parcels/{idu}")
            fais = _api(f"/modules/faisabilite/{idu}")
            try:
                gabarit = _api(f"/outils/gabarit/{idu}")
            except Exception:
                gabarit = {}
        except Exception as e:
            lignes.append([idu, strate, "(écran)", "", "FICHE INJOUABLE", str(e)[:120]])
            ecarts += 1
            continue
        figs = figures_fiche(fiche, fais, gabarit)
        textes: dict[str, tuple[int, str]] = {}
        for doc, path in (("dossier", f"/dossier/{idu}.pdf"),
                          ("financier", f"/financier/{idu}.pdf"),
                          ("apporteur", f"/apporteur/{idu}.pdf"),
                          ("gabarit", f"/gabarit/{idu}.pdf")):
            textes[doc] = _pdf(path)
            code = textes[doc][0]
            if code not in (200, 422):
                lignes.append([idu, strate, doc, "", f"HTTP {code}", textes[doc][1][:120]])
                ecarts += 1
        # surface au DOSSIER : l'en-tête l'imprime SANS libellé → présence du nombre
        # formaté FR dans les 60 premières lignes (table d'identité).
        if figs.get("surface_m2") and textes["dossier"][0] == 200:
            tete = "\n".join(textes["dossier"][1].splitlines()[:60])
            attendu_fr = _fr(figs["surface_m2"])
            present = re.search(re.escape(attendu_fr).replace(r"\ ", r"[  ]") + r"[  ]*m²", tete)
            lignes.append([idu, strate, "dossier", "surface_m2",
                           "OK" if present else "ECART",
                           f"écran={figs['surface_m2']} ({attendu_fr} m² en tête: {bool(present)})"])
            if not present:
                ecarts += 1
        for fig, (motif, docs) in MAPPING.items():
            attendu = figs.get(fig)
            if attendu is None:
                continue
            for doc in docs:
                code, texte = textes[doc]
                if code != 200:
                    continue  # refus 422 du gabarit = légitime, déjà tracé si autre code
                vu = _nombre_apres(texte, motif)
                if vu is None:
                    lignes.append([idu, strate, doc, fig, "absent", f"écran={attendu}"])
                    continue
                ok = _egal(vu, float(attendu))
                lignes.append([idu, strate, doc, fig, "OK" if ok else "ECART",
                               f"écran={attendu} papier={vu}"])
                if not ok:
                    ecarts += 1
        print(f"{idu} ({strate}) joué")

    with (OUT / "ECRAN_PAPIER.csv").open("w", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["idu", "strate", "document", "figure", "verdict", "detail"])
        w.writerows(lignes)
    n_ok = sum(1 for l in lignes if l[4] == "OK")
    print(f"\n{len(parcelles)} parcelles · {n_ok} comparaisons OK · {ecarts} écart(s) "
          f"→ {OUT}/ECRAN_PAPIER.csv")


if __name__ == "__main__":
    main()
