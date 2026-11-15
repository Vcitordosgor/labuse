"""ETUDE-STATIONNEMENT-FIX-1 (relecture 3) — remplace la citation de chaque zone ingérée par le TEXTE
VERBATIM de la norme d'habitation lu sur SA page du PDF officiel, jusqu'à 0 échec du contrôle
(citation mot pour mot sur la page + chaque chiffre appliqué dans la citation).

Extraction : le bloc « habitation » de la page (de l'en-tête habitation jusqu'à la destination suivante)
+ toute ligne portant un chiffre appliqué par le barème. Verbatim, retours à la ligne réels.
"""
import glob
import os
import re

import fitz

PDFDIR = os.path.expanduser("~/Desktop/labuse/data/plu_reglements/")

_START = ("destination d'habitation", "destinations d'habitation", "habitation", "habitat individuel",
          "habitat collectif", "logement", "logements", "constructions à usage d'habitation")
_STOP = ("commerce", "bureau", "activités artisanales", "activité de service", "activités de service",
         "hébergement hôtelier", "équipement", "industri", "entrepôt", "artisanat", "restauration",
         "secteur primaire", "exploitation agricole", "constructions à destination de commerces",
         "services publics", "intérêt collectif", "2 roues", "deux roues")


def pdf_for(insee):
    hits = sorted(glob.glob(PDFDIR + f"{insee}_[rR]eglement_*.pdf"))
    return hits[0] if hits else None


def _lines(doc, page_pdf):
    """Lignes (texte) de la page + voisines, dans l'ordre, avec un index stable."""
    out = []
    for j in (page_pdf - 2, page_pdf - 1, page_pdf):
        if 0 <= j < doc.page_count:
            for ln in doc[j].get_text().split("\n"):
                out.append((j, ln.rstrip()))
    return out


_CTX = ("place de stationnement", "place par logement", "places par logement", "place/logt", "par logement",
        "par tranche de", "pièce", "aidé", "logement social", "logement locatif", "lotissement",
        "habitat individuel", "habitat collectif", "studio", "chambre", "par hébergement", "minimum par logement")
# contextes NON stationnement (hauteur, façades, plantations…) : excluent une ligne même si un chiffre y figure.
_EXCL = ("mètre", "hauteur", "égout", "faîtage", "faitage", "soutènement", "pente", "façade", "clôture",
         "plantation", "arbre", "biotope", "perméab", "imperméab", "acrotère", "niveau", "r+", "voie",
         "limite séparative", "recul", "emprise au sol", "haie", "palmier", "mur")


def verbatim(doc, page_pdf, fig_tokens):
    """Texte VERBATIM de la norme d'habitation : fenêtre serrée autour des LIGNES qui portent un chiffre
    appliqué en contexte de stationnement d'habitation (exclut le bruit « logement » des articles hauteur/
    façades). Renvoie le texte (retours à la ligne réels) ou None si rien de probant."""
    lines = _lines(doc, page_pdf)
    low = [ln.lower() for _p, ln in lines]
    # lignes « norme de stationnement d'habitation » : contexte parking/habitation, chiffre appliqué, ET
    # AUCUN contexte hauteur/façade/plantation (le bruit qui porte aussi des « 1 »/« 1,5 »).
    norme = [i for i, l in enumerate(low)
             if lines[i][1].strip()
             and any(t and _norm(t) in _norm(l) for t in fig_tokens)
             and any(c in l for c in _CTX)
             and not any(x in l for x in _EXCL)]
    if not norme:
        return None
    keep = set(norme)
    # rattache les lignes d'EN-TÊTE de catégorie contiguës (sans chiffre : « Habitat collectif », « Autres
    # logements », « Logement », « Habitation »…) juste au-dessus/à côté des lignes-norme.
    heads = ("habitat individuel", "habitat collectif", "autres logements", "logements aidés",
             "logements privés", "logement locatif", "habitation", "logement", "destination d'habitation")
    for i in list(norme):
        for j in (i - 1, i - 2, i + 1):
            if 0 <= j < len(low) and lines[j][1].strip() and any(h in low[j] for h in heads) \
                    and not any(x in low[j] for x in _EXCL):
                keep.add(j)
    idx = sorted(keep)
    txt = "\n".join(lines[i][1].strip() for i in idx)
    return re.sub(r'\n{2,}', '\n', txt).strip() or None


def _norm(s):
    return re.sub(r'\s+', '', (s or "").lower().replace("’", "'").replace("œ", "oe"))


if __name__ == "__main__":
    # test rapide sur quelques zones
    import sys
    sys.path.insert(0, "src")
    sys.path.insert(0, "scripts")
    from labuse.implantation import regles as R
    from stationnement_controle_pages import figures  # type: ignore
    for insee, z in [("97422", "Ud"), ("97424", "Ua"), ("97416", "Ud"), ("97412", "U3"), ("97407", "Ua")]:
        b = R.charger(insee, z).stationnement
        doc = fitz.open(pdf_for(insee))
        v = verbatim(doc, b.page_pdf, figures(b))
        doc.close()
        figs = figures(b)
        manque = [f for f in figs if _norm(f) not in _norm(v or "")]
        print(f"\n=== {insee} {z} p{b.page_pdf} — chiffres {sorted(figs)} — manquants {manque} ===")
        print((v or "(rien)")[:400])
