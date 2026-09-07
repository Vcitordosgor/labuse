"""EXPORTS-2 lot 1 — LE BUILDER UNIQUE : un document = une suite de blocs du catalogue. Le
builder réunit les ids de tous les blocs, appelle la collecte UNE fois, passe les Valeur aux
blocs (purs), assemble le HTML avec le cartouche @page, rend le PDF (WeasyPrint) et archive les
Valeur lues à côté du PDF. Les cinq documents (lots 2-7) ne sont que des listes de blocs ici.

Le lot 1 câble le Dossier partiel (page de garde + section 1) pour prouver la chaîne de bout en
bout sur les quatre témoins ; les lots 2-7 ajoutent les blocs.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from ..registre.valeur import Valeur
from . import archive, numeros
from .blocs import (autour, bilan, commune, identite, marche, potentiel, reseaux, risques,
                    sources, zonage)
from .registre_fmt import fmt_m2
from .rendu import Cartouche, esc, page_html, render_pdf

MODELE_VERSION = "2.0"

#: libellé et sous-titre de chaque document (page de garde).
_LABEL = {
    "dossier": ("Dossier parcelle", "Ce que cette parcelle est, ce qu'elle porte, ce que le règlement y permet."),
    "flash": ("Rapport Flash", "Ce que cette parcelle est, ce qu'elle porte, ce que le règlement y permet."),
    "resume": ("Fiche parcelle — résumé", ""),
    "financier": ("Bilan de l'opération", ""),
    "apporteur": ("Brief apporteur", ""),
}

_FOOT_DOSSIER = ("Document d'information établi à partir de données publiques. Ne remplace ni un "
                 "certificat d'urbanisme, ni une étude de faisabilité réglementaire, ni un conseil "
                 "juridique. Données LABUSE au {au}.")
_FOOT = {"dossier": _FOOT_DOSSIER, "flash": _FOOT_DOSSIER}

#: composition de chaque document = la suite ordonnée des blocs (catalogue EXPORTS-SOURCES).
#: Le Dossier = 10 sections ; le Flash = le Dossier SANS la section 9 (bilan), même builder.
_DOSSIER = [identite, zonage, potentiel, risques, marche, reseaux, autour, commune, bilan, sources]
DOCUMENTS: dict[str, list] = {
    "dossier": _DOSSIER,
    "flash": [b for b in _DOSSIER if b is not bilan],
}


@dataclass(frozen=True)
class ResultatDoc:
    html: str
    valeurs: dict[str, Valeur]
    numero: str
    cartouche: Cartouche


def _cover(document: str, idu: str, fiche: dict, numero: str, jour: date,
           valeurs: dict[str, Valeur]) -> str:
    label, subtitle = _LABEL.get(document, (document, ""))
    adresse = fiche.get("adresse") or ""
    commune = fiche.get("commune") or ""
    surf = valeurs.get("surface_parcelle_m2")
    contenance = fmt_m2(surf.valeur) if surf is not None else '<span class="none">non chiffré</span>'
    return (
        '<div class="cover">'
        f'<div class="brand"><span class="wordmark">LABUSE</span>'
        f'<span class="kind">{esc(label)}</span></div>'
        f'<h1>{esc(label)}</h1>'
        + (f'<p class="subtitle">{esc(subtitle)}</p>' if subtitle else "")
        + (f'<p class="address">{esc(adresse)}</p>' if adresse else "")
        + f'<p class="idu">{esc(idu)}{(" · " + esc(commune)) if commune else ""}</p>'
        + '<table class="cartouche">'
        f'<tr><td>N° de rapport</td><td>{esc(numero)}</td></tr>'
        f'<tr><td>Généré le</td><td>{jour:%d/%m/%Y}</td></tr>'
        f'<tr><td>Contenance cadastrale</td><td>{contenance}</td></tr>'
        f'<tr><td>Modèle de document</td><td>{MODELE_VERSION}</td></tr>'
        '</table>'
        '<p class="notice">Chaque donnée porte sa nature : '
        '<span class="chip s">sourcé</span> vient d\'une source publique · '
        '<span class="chip e">estimé</span> est un calcul LABUSE · '
        '<span class="chip d">dérivé</span> est déduit d\'une autre donnée · '
        '<span class="chip p">projet</span> a été saisi par vous. Une donnée absente est dite '
        'absente : ce document n\'imprime jamais un zéro pour une valeur qu\'il ne connaît pas.</p>'
        '</div>'
    )


def construire(db, idu: str, document: str = "dossier", *, fiche: dict | None = None,
               jour: date | None = None) -> ResultatDoc:
    """Assemble le HTML complet d'un document et les Valeur lues (pour l'archive)."""
    from .collecte import collecte
    if document not in DOCUMENTS:
        raise ValueError(f"document inconnu : {document!r} (câblé : {sorted(DOCUMENTS)})")
    j = jour or date.today()
    f = fiche or {}
    numero = numeros.numero_rapport(document, idu, j)
    blocs = DOCUMENTS[document]
    ids = sorted({cid for b in blocs for cid in b.IDS})
    valeurs = collecte(db, idu, ids, fiche=f)
    label, _ = _LABEL.get(document, (document, ""))
    adresse = f.get("adresse") or ""
    au = f.get("donnees_labuse_au") or f"{j:%d/%m/%Y}"
    cart = Cartouche(
        doc_title=f"LABUSE — {label}" + (f" · {adresse}" if adresse else ""),
        doc_ref=f"{idu} · {numero}",
        doc_foot=_FOOT.get(document, ("Document d'information LABUSE. Données au {au}.",))[0].format(au=au),
    )
    corps = _cover(document, idu, f, numero, j, valeurs) + "".join(b.rendu(valeurs) for b in blocs)
    html = page_html(label, cart, corps)
    return ResultatDoc(html=html, valeurs=valeurs, numero=numero, cartouche=cart)


def generer_pdf(db, idu: str, document: str = "dossier", *, fiche: dict | None = None,
                jour: date | None = None, chemin_pdf=None):
    """Rend le PDF d'un document et, si `chemin_pdf` est donné, écrit le PDF + son archive JSON
    (reproductibilité — lot 1.6). Rend (bytes_pdf, ResultatDoc)."""
    res = construire(db, idu, document, fiche=fiche, jour=jour)
    pdf = render_pdf(res.html)
    if chemin_pdf is not None:
        from pathlib import Path
        Path(chemin_pdf).write_bytes(pdf)
        j = (jour or date.today()).isoformat()
        archive.ecrire_archive(chemin_pdf, archive.payload_archive(
            document, idu, res.numero, res.valeurs, genere_le=j))
    return pdf, res
