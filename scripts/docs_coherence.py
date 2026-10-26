"""DOCS-COHERENCE-1 (Lot 0) — les 8 documents de Docs disent la même chose.

Génère les 8 documents de la page Docs sur UNE parcelle, en extrait le texte
(pdftotext) et CONFRONTE les valeurs partagées entre documents : surface, emprise
bâtie, bâtiments, zone d'implantation (terrain libéré / bâti déduit), pente, hauteur
(égout / faîtage), reculs, stationnement, pleine terre, contraintes, prix (bâti /
terrain / neuf), SDP (résiduelle / max réglementaire / scénario), propriétaire (type),
date des données. La règle de LABUSE : rien de faux — un chiffre, une source, un
libellé, dans tous les documents. À la fin du mandat : ZÉRO écart.

    PYTHONPATH=…/labuse-docs2/src .venv/bin/python -m scripts.docs_coherence <IDU>
    LABUSE_DOCS_API=http://127.0.0.1:8830 (défaut)
    LABUSE_DOCS_SORTIE=/chemin/ecarts.csv (optionnel)

Les 7 documents « PDF via HTTP » sont tirés de l'API locale ; le Bilan est rendu
EN PROCESS par le MÊME chemin que la route (`labuse.bilan.pdf.construire_pdf`), car
sa route d'écriture exige une session compte (indisponible en mode local). Aucune
écriture en base.
"""
from __future__ import annotations

import io
import json
import os
import re
import subprocess
import sys
import urllib.request
import zipfile

API = os.environ.get("LABUSE_DOCS_API", "http://127.0.0.1:8830").rstrip("/")

#: Comparatif = BY0083 + deux voisines ; second témoin de clôture = BL0020.
COMPARATIF = {
    "97415000BY0083": ["97415000BY0083", "97415000BY0361", "97415000BY0272"],
    "97408000BL0020": ["97408000BL0020"],
}
#: Programme fixé de l'Étude de faisabilité (mandat) — résidence 24 T1 aérien.
PROGRAMME = {"mode": "saisi", "lignes": [{"type": "T1", "nombre": 24, "surface_m2": 30}]}

ESPACES = "    "   # insécable, fine insécable, fine, espace


# ── récupération des documents ────────────────────────────────────────────────
def _get(path: str, timeout: int = 200) -> bytes:
    with urllib.request.urlopen(API + path, timeout=timeout) as r:
        return r.read()


def _post(path: str, body: dict, timeout: int = 120) -> bytes:
    req = urllib.request.Request(API + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _pdftotext(octets: bytes, layout: bool = True) -> str:
    cmd = ["pdftotext"] + (["-layout"] if layout else []) + ["-", "-"]
    p = subprocess.run(cmd, input=octets, capture_output=True, timeout=120)
    return p.stdout.decode("utf-8", errors="replace")


def _bilan_pdf(idu: str) -> bytes:
    """Le Bilan rendu en process (même chemin que la route) avec le MÊME pré-remplissage Sourcé que
    la route (`bilan.reperes.sources_parcelle` : terrain = contenance cadastrale, comme la fiche)."""
    from sqlalchemy import text
    from labuse.bilan import reperes
    from labuse.bilan.moteur import EntreesBilan, Moteur, Programme
    from labuse.bilan.pdf import construire_pdf
    from labuse.db import session_scope
    with session_scope() as s:
        commune = s.execute(text("SELECT commune FROM parcels WHERE idu=:i"), {"i": idu}).scalar() or ""
        terrain = (reperes.sources_parcelle(s, idu) or {}).get("terrain")
    e = EntreesBilan(programme=Programme(terrain=float(terrain) if terrain else None))
    r = Moteur().calculer(e)
    return construire_pdf(r, idu=idu, commune=str(commune), programme={}, calendrier={})


def documents(idu: str) -> dict[str, str]:
    """Rend {nom_document: texte}. Best-effort : un document en échec garde son message."""
    textes: dict[str, str] = {}

    def essaie(nom, fn):
        try:
            textes[nom] = fn()
        except Exception as exc:  # noqa: BLE001
            textes[nom] = f"__ERREUR__ {exc}"
            print(f"  ! {nom} : {exc}", file=sys.stderr)

    essaie("Dossier", lambda: _pdftotext(_get(f"/dossier/{idu}.pdf?carte=false")))
    essaie("Apporteur", lambda: _pdftotext(_get(f"/apporteur/{idu}.pdf")))
    essaie("Étude de zone", lambda: _pdftotext(_get(f"/etude-zone.pdf?idu={idu}&rayon_km=1.0")))
    essaie("Gabarit", lambda: _pdftotext(_get(f"/gabarit/{idu}.pdf")))
    ids = COMPARATIF.get(idu)
    if ids and len(ids) >= 2:
        essaie("Comparatif", lambda: _pdftotext(_get(f"/comparatif.pdf?idus={','.join(ids)}")))
    essaie("Étude de faisabilité", lambda: _pdftotext(_post(
        "/modules/etude/pdf", {"idus": [idu], "type_projet": "collectif", "objectif": "equilibre",
                               "stationnement": "aerien", "terrain": "libere", "programme": PROGRAMME})))
    essaie("Pré-dossier PC", lambda: _cerfa_texte(_get(f"/pre-dossier/{idu}.zip")))
    essaie("Bilan", lambda: _pdftotext(_bilan_pdf(idu)))
    return textes


def _cerfa_texte(zip_octets: bytes) -> str:
    out = []
    with zipfile.ZipFile(io.BytesIO(zip_octets)) as z:
        for nom in z.namelist():
            if nom.lower().endswith(".pdf"):
                out.append(f"### {nom}\n" + _pdftotext(z.read(nom)))
    return "\n".join(out)


# ── normalisation ───────────────────────────────────────────────────────────
def _norm_nb(txt: str) -> str:
    """« 2 458 m² » → « 2458 ». Espaces (dont insécables) ôtés, virgule décimale normalisée ;
    les zéros DÉCIMAUX de queue tombent (9,0 → 9) sans toucher aux zéros ENTIERS (900 reste 900)."""
    s = re.sub(f"[{ESPACES}]", "", txt).replace(",", ".")
    try:
        f = float(s)
        return str(int(f)) if f == int(f) else f"{f:g}"
    except ValueError:
        return s


def _n(v):
    return _norm_nb(v) if v else None


def _plat(v):
    """Texte aplati (une ligne, espaces normalisés) pour comparer des libellés."""
    return re.sub(r"\s+", " ", v).strip() if v else None


def _cherche(txt, *patterns):
    for p in patterns:
        m = re.search(p, txt, re.IGNORECASE)
        if m:
            return m.group(1)
    return None


NB = rf"[\d{ESPACES}]+"   # un nombre avec séparateurs de milliers


# ── extracteurs : chaque donnée lue dans TOUS les documents qui la portent ────
def _surface(t):
    # surface CADASTRALE du terrain (contenance) ; jamais une « surface réelle ~ » géométrique d'un
    # plan de masse (approximative, autre donnée) : le gap des patterns ne franchit ni « ; » ni « ~ ».
    return _n(_cherche(t, rf"({NB})\s*m²\s*\n?\s*SURFACE",
                       rf"[Ss]urface(?:\s*\(plan\))?\s+({NB})\s*m²",
                       rf"Contenance(?:\s*cadastrale)?[^\n;~]*?({NB})\s*m²",
                       # « Terrain (contenance) » / « Assiette fusionnée » — PAS « terrain libéré » (= zone).
                       rf"(?:Terrain\s*\(contenance\)|Assiette fusionn[ée]e?)[^\n;~]*?({NB})\s*m²"))


def _emprise(t):
    # emprise du bâti EXISTANT (pas celle d'un scénario projeté, suffixée « · NN % ») :
    return _n(_cherche(t, rf"[Ee]mprise bâtie\s+({NB})\s*m²(?!\s*·)",
                       rf"bâtiments?\s*existants?[^\n]*?({NB})\s*m²\s*au sol"))


def _batiments(t):
    return _n(_cherche(t, rf"[Bb]âtiments?\s+(\d+)\s*\n", r"(\d+)\s*bâtiments?,"))


def _pente(t):
    v = _cherche(t, r"[Pp]ente\s+(\d+[.,]?\d*\s*°(?:\s*\(\s*\d+[.,]?\d*\s*%\s*\))?)",
                 r"[Pp]ente(?:\s*moyenne)?\s+(\d+[.,]?\d*\s*%)",
                 r"(\d+[.,]?\d*\s*°)\s*·")
    return _plat(v)


def _hauteur(t):
    """Représentation normalisée faîtage/égout : « 9/6 » quand les deux sont dits, sinon ce qui l'est."""
    fait = _cherche(t, r"(\d+[.,]?\d*)\s*m\s*au faîtage", r"hauteur au faîtage\s+(\d+[.,]?\d*)\s*m",
                    r"[Hh]auteur\s*(?:max|réglementaire)\w*\s+(\d+[.,]?\d*)\s*m")
    egout = _cherche(t, r"(\d+[.,]?\d*)\s*m à l['’]égout", r"hauteur à l['’]égout\s+(\d+[.,]?\d*)\s*m")
    if not (fait or egout):
        return None
    return f"{_norm_nb(fait) if fait else '?'}/{_norm_nb(egout) if egout else '?'}"


def _recul_voie(t):
    return _n(_cherche(t, rf"[Rr]ecul\s*(?:sur\s*)?voie(?:\s*\(emprise publique\))?\s*[:\-]?\s*({NB}[.,]?\d*)\s*m"))


def _stationnement(t):
    v = _cherche(t, r"[Ss]tationnement[^\n]*?[:·]\s*([^\n]{2,45})", r"[Ss]tationnement\s+([^\n]{2,45})")
    v = _plat(v)
    return v.lower().rstrip(". ") if v else None


def _pleine_terre(t):
    return _n(_cherche(t, rf"[Pp]leine terre[^\n]*?({NB}[.,]?\d*)\s*%"))


def _prix_bati(t):
    return _n(_cherche(t, rf"Prix (?:ancien )?médian(?: du bâti)?\s+({NB})\s*€/m²",
                       rf"Prix (?:du )?bâti[^\n]*?({NB})\s*€/m²",
                       rf"Ancien bâti[^\n]*?({NB})\s*€/m²",
                       rf"({NB})\s*€/m²\s*[—\-][^\n]*ancien"))


def _prix_terrain(t):
    return _n(_cherche(t, rf"Prix (?:du )?terrain[^\n]*?({NB})\s*€/m²",
                       rf"[Tt]errain\s+({NB})\s*€/m²"))


def _prix_neuf(t):
    return _n(_cherche(t, rf"(?:Neuf VEFA|VEFA)[^\n]*?({NB})\s*€/m²",
                       rf"({NB})\s*€/m²[^\n]*VEFA"))


def _sdp_residuelle(t):
    return _n(_cherche(t, rf"({NB})\s*m²\s*\n?\s*SDP RESTANTE",
                       rf"SDP résiduelle[^\n]*?({NB})\s*m²"))


def _sdp_max(t):
    return _n(_cherche(t, rf"SDP maximale réglementaire[^\n]*?({NB})\s*m²"))


def _zone_libere(t):
    return _n(_cherche(t, rf"Zone d'implantation(?:\s*réglementaire)?\s+({NB})\s*m²",
                       rf"terrain libéré\s*[:\-]?\s*({NB})\s*m²"))


def _zone_deduite(t):
    return _n(_cherche(t, rf"bâti existant déduit\s+({NB})\s*m²"))


def _proprietaire(t):
    # ancré sur le libellé « propriétaire » du document (le « particulier » du CERFA = la case
    # DEMANDEUR d'un formulaire vierge, pas le propriétaire de la parcelle — jamais comparé ici).
    v = _cherche(t, r"Type de propriétaire\s+([^\n]{3,45})",
                 r"Propriétaire\s+(?:sourcé\s+)?(Particulier|Personne morale|Succession|Indivision)",
                 r"\b(Succession|Indivision|Personne morale|Particulier)\s*—")
    v = _plat(v)
    return v.split("—")[0].strip().lower() if v else None


def _date(t):
    # le pied du Dossier passe à la ligne entre « Données » et « LABUSE au … » → on ancre sur « LABUSE au ».
    return _cherche(t, r"LABUSE au (\d{2}/\d{2}/\d{4})",
                    r"Généré via LABUSE le (\d{2}/\d{2}/\d{4})")


def _contraintes(t):
    """« oui » si le document relève au moins une contrainte, « aucune » s'il l'affirme explicitement."""
    bas = t.lower()
    if re.search(r"aucune contrainte|aucun aléa|rien à signaler.*contrainte", bas):
        return "aucune"
    if re.search(r"aléa|mouvement de terrain|dpu|droit de préemption|parc national|servitude|ppr|inondation", bas):
        return "oui"
    return None


DONNEES = [
    ("surface terrain (m²)", _surface),
    ("emprise bâtie (m²)", _emprise),
    ("nombre de bâtiments", _batiments),
    ("zone impl. libérée (m²)", _zone_libere),
    ("zone impl. déduite (m²)", _zone_deduite),
    ("pente", _pente),
    ("hauteur faît./égout", _hauteur),
    ("recul voie (m)", _recul_voie),
    ("stationnement", _stationnement),
    ("pleine terre (%)", _pleine_terre),
    ("prix bâti (€/m²)", _prix_bati),
    ("prix terrain (€/m²)", _prix_terrain),
    ("prix neuf VEFA (€/m²)", _prix_neuf),
    ("SDP résiduelle (m²)", _sdp_residuelle),
    ("SDP max régl. (m²)", _sdp_max),
    ("contraintes relevées", _contraintes),
    ("propriétaire (type)", _proprietaire),
    ("date des données", _date),
]

ORDRE_DOCS = ["Dossier", "Apporteur", "Pré-dossier PC", "Étude de zone", "Gabarit",
              "Comparatif", "Étude de faisabilité", "Bilan"]


def comparer(textes):
    lignes = []
    for libelle, fn in DONNEES:
        cells = {}
        for doc in ORDRE_DOCS:
            t = textes.get(doc)
            cells[doc] = (fn(t) if t and not t.startswith("__ERREUR__") else None)
        presentes = {v for v in cells.values() if v is not None}
        lignes.append({"donnee": libelle, "cells": cells, "ecart": len(presentes) > 1,
                       "valeurs": sorted(presentes)})
    return lignes


def rendu(idu, lignes):
    out = [f"# docs_coherence — {idu}  (API {API})", ""]
    n_ecart = sum(1 for l in lignes if l["ecart"])
    out.append(f"**{n_ecart} écart(s)** sur {len(lignes)} données partagées.\n")
    larg = 26
    entete = "donnée".ljust(larg) + "".join(d[:14].ljust(16) for d in ORDRE_DOCS)
    out.append(entete)
    out.append("-" * len(entete))
    for l in lignes:
        marque = "/!\\ " if l["ecart"] else "    "
        ligne = marque + l["donnee"][:larg - 4].ljust(larg - 4)
        for d in ORDRE_DOCS:
            v = l["cells"][d]
            ligne += ((v or "—")[:15]).ljust(16)
        out.append(ligne)
    return "\n".join(out)


def _csv(idu, lignes, chemin):
    import csv
    with open(chemin, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["idu", "donnee", "ecart"] + ORDRE_DOCS)
        for l in lignes:
            w.writerow([idu, l["donnee"], "ECART" if l["ecart"] else ""]
                       + [l["cells"][d] or "" for d in ORDRE_DOCS])


def main(argv):
    if not argv:
        print("usage: python -m scripts.docs_coherence <IDU> [IDU...]", file=sys.stderr)
        return 2
    rc = 0
    for idu in argv:
        print(f"-> {idu} : génération des 8 documents…", file=sys.stderr)
        textes = documents(idu)
        lignes = comparer(textes)
        print(rendu(idu, lignes))
        sortie = os.environ.get("LABUSE_DOCS_SORTIE")
        if sortie:
            _csv(idu, lignes, sortie.replace("{idu}", idu))
        if any(l["ecart"] for l in lignes):
            rc = 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
