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
from .blocs import (apporteur, autour, bilan, commune, financier, identite, marche, potentiel,
                    reseaux, risques, sources, zonage)
from .registre_fmt import fmt_m2
from .rendu import Cartouche, esc, page_html, render_pdf

MODELE_VERSION = "2.0"

#: libellé et sous-titre de chaque document (page de garde).
_LABEL = {
    "dossier": ("Dossier parcelle", "Ce que cette parcelle est, ce qu'elle porte, ce que le règlement y permet."),
    "flash": ("Rapport Flash", "Ce que cette parcelle est, ce qu'elle porte, ce que le règlement y permet."),
    "financier": ("Bilan de l'opération", ""),
    "apporteur": ("Brief apporteur", ""),
}

_FOOT_DOSSIER = ("Document d'information établi à partir de données publiques. Ne remplace ni un "
                 "certificat d'urbanisme, ni une étude de faisabilité réglementaire, ni un conseil "
                 "juridique. Données LABUSE au {au}.")
_FOOT = {
    "dossier": _FOOT_DOSSIER, "flash": _FOOT_DOSSIER,
    "financier": ("Bilan indicatif établi sur des données publiques et sur les hypothèses saisies "
                  "par le porteur (en ambre). Ni un prix, ni une promesse, ni un conseil. Il ne "
                  "remplace pas un bilan promoteur professionnel. Données LABUSE au {au}."),
    "apporteur": ("Document confidentiel remis par l'émetteur à son apporteur d'affaires. Ne pas "
                  "transmettre au propriétaire. Ne vaut pas mandat. Données publiques LABUSE au {au}."),
}

#: composition de chaque document = la suite ordonnée des blocs (catalogue EXPORTS-SOURCES).
#: Le Dossier = 10 sections ; le Flash = le Dossier SANS la section 9 (bilan), même builder.
#: RECETTE-3 (T2, décision Vic) — le document Résumé est SUPPRIMÉ (route, builder, bloc, bouton).
_DOSSIER = [identite, zonage, potentiel, risques, marche, reseaux, autour, commune, bilan, sources]
DOCUMENTS: dict[str, list] = {
    "dossier": _DOSSIER,
    "flash": [b for b in _DOSSIER if b is not bilan],
    "financier": [financier],
    "apporteur": [apporteur],
}

#: documents servis avec un contexte (au-delà des Valeur) : Financier (questionnaire+bilan),
#: Apporteur (émetteur, dates, blocs adaptatifs). Le bloc reçoit rendu(valeurs, ctx).
_AVEC_CONTEXTE = {"financier", "apporteur"}


@dataclass(frozen=True)
class ResultatDoc:
    html: str
    valeurs: dict[str, Valeur]
    numero: str
    cartouche: Cartouche


#: documents « au fil » (pas de page de garde pleine) : en-tête compact (Résumé, Financier).
#: L'Apporteur rend son propre en-tête (confidentiel + « Un terrain à sonder ») → aucun en-tête ici.
_COVER_COMPACTE = {"financier"}
_COVER_AUCUNE = {"apporteur"}


def _entete_compacte(document: str, idu: str, fiche: dict, numero: str, jour: date,
                     valeurs: dict[str, Valeur]) -> str:
    """En-tête compact (Résumé / Apporteur) : marque + adresse + une ligne d'identité. Pas de
    page de garde, pas de cartouche-tableau (l'IDU entier vit dans cette ligne et au @page)."""
    label, _ = _LABEL.get(document, (document, ""))
    adresse = fiche.get("adresse") or ""
    surf = valeurs.get("surface_parcelle_m2")
    zone = valeurs.get("zone_plu_famille")
    bits = [esc(idu)]
    if surf is not None:
        bits.append(fmt_m2(surf.valeur))
    if zone is not None:
        bits.append(f"zone {esc(zone.valeur)}")
    bits += [esc(numero), f"{jour:%d/%m/%Y}"]
    return (f'<div class="brand"><span class="wordmark">LABUSE</span>'
            f'<span class="kind">{esc(label)}</span></div>'
            f'<h1>{esc(adresse or label)}</h1>'
            f'<p class="idu">{" · ".join(bits)}</p>')


def _cover(document: str, idu: str, fiche: dict, numero: str, jour: date,
           valeurs: dict[str, Valeur]) -> str:
    if document in _COVER_AUCUNE:
        return ""      # le bloc rend son propre en-tête (Apporteur)
    if document in _COVER_COMPACTE:
        return _entete_compacte(document, idu, fiche, numero, jour, valeurs)
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


#: surface vendable moyenne par logement selon la typologie saisie (hypothèse déclarée, repli du
#: programme quand le potentiel ne chiffre pas de reconstruction — le programme reste piloté par
#: les logements visés du client).
_TYPOLOGIE_SURFACE = {"T1": 30, "T2": 45, "T3": 65, "T4": 85, "T5": 105, "STUDIO": 25}


def _financier_contexte(db, idu: str, fiche: dict, compte_id: int | None) -> dict:
    """Charge le questionnaire, résout les hypothèses (avec pré-remplissages sourcés) et calcule le
    bilan HT. Le programme vient du potentiel (reconstruction) ou, à défaut, des logements visés ×
    surface de la typologie."""
    from .. import financier_questionnaire as qf
    from . import financier_bilan as fb
    etat = qf.charger(db, idu, compte_id)
    prefill = qf.prefill(fiche)
    resolved = qf.resoudre(etat["reponses"], prefill)
    rv = lambda fid: (resolved.get(fid) or {}).get("valeur")  # noqa: E731
    hyp = {
        "prix_sortie": rv("prix_sortie_saisi_eur_m2"), "prix_bailleur": rv("prix_vente_bailleur_saisi_eur_m2"),
        "cout": rv("cout_construction_saisi_eur_m2"), "honoraires_pct": rv("honoraires_techniques_saisi_pct"),
        "vrd_m2": rv("vrd_saisi_eur_m2"), "cout_place": rv("cout_place_stationnement_saisi_eur"),
        "aleas_pct": rv("aleas_saisi_pct"), "marge_pct": rv("marge_visee_saisi_pct"),
        "frais_acq_pct": rv("frais_acquisition_saisi_pct"), "prix_demande": rv("prix_demande_saisi_eur"),
        "demolition": rv("bilan_demolition_eur"), "depollution": rv("bilan_depollution_eur"),
        "taxe": rv("taxe_amenagement_saisi_eur"), "duree_portage": rv("duree_portage_saisi_mois"),
        "taux_apport": rv("taux_apport_saisi_pct"), "part_sociale_pct": rv("part_sociale_saisi_pct") or 0,
    }
    pot = fiche.get("potentiel_transformation") or {}
    cap = pot.get("capacite_estimee")
    program = {
        "surface_terrain": fiche.get("surface_m2"),
        "logements": rv("logements_vises_saisi") or (cap if (cap and not isinstance(cap, bool)) else None),
        "surface_vendable": pot.get("surface_vendable_m2"),
        "surface_plancher": pot.get("surface_plancher_m2"),
    }
    if not program["surface_vendable"] and program["logements"]:
        typo = str(rv("typologie_moyenne_saisi") or "T3").upper().strip()
        surf = _TYPOLOGIE_SURFACE.get(typo, 60)
        program["surface_vendable"] = program["logements"] * surf
        program["surface_plancher"] = program["surface_vendable"] / 0.8
    return {"bilan": fb.calculer(program, hyp), "resolved": resolved, "prefill": prefill,
            "complet": etat["complet"], "existe": etat["existe"], "program": program}


def _emetteur(db, compte_id: int | None) -> dict | None:
    """L'émetteur du brief = le compte de l'utilisateur (non modifiable). Best-effort : si la
    colonne n'existe pas sur cette base, on rend None (l'Apporteur imprime « (votre compte) »)."""
    if not compte_id:
        return None
    from sqlalchemy import text
    try:
        row = db.execute(text("SELECT raison_sociale, email FROM comptes WHERE id = :i"),
                         {"i": compte_id}).mappings().first()
        if row:
            return {"raison": row.get("raison_sociale"), "contact": row.get("email")}
    except Exception:  # noqa: BLE001
        pass
    return None


def _ref_courte(idu: str) -> str:
    """Référence cadastrale courte lisible (« CY 0044 ») depuis l'IDU (section + numéro)."""
    return f"{idu[8:10]} {idu[10:14]}" if len(idu) >= 14 else idu


def _apporteur_voisines(db, idu: str) -> dict:
    """RECETTE-3 (T1) — parcelles voisines du MÊME propriétaire (feature Blocs fonciers) : pour la
    ligne « À côté » du coup d'œil ET l'overlay du plan de situation. Vide si la parcelle n'est
    dans aucun bloc (propriétaire non morale, parcelle isolée…)."""
    from sqlalchemy import text
    try:
        rows = db.execute(text(
            """WITH b AS (SELECT bloc_id FROM parcel_bloc_membres WHERE idu = :idu LIMIT 1)
               SELECT m.idu, m.surface_m2 FROM parcel_bloc_membres m JOIN b ON b.bloc_id = m.bloc_id
               WHERE m.idu <> :idu ORDER BY m.surface_m2 DESC NULLS LAST, m.idu"""),
            {"idu": idu}).mappings().all()
    except Exception:  # noqa: BLE001 — table absente / base de test : pas de voisines, jamais d'erreur
        return {"n": 0, "membres": [], "surface_totale_m2": None}
    membres = [{"idu": r["idu"], "ref": _ref_courte(r["idu"]),
                "surface_m2": round(r["surface_m2"]) if r["surface_m2"] else None} for r in rows]
    total = sum(m["surface_m2"] or 0 for m in membres) or None
    return {"n": len(membres), "membres": membres, "surface_totale_m2": total}


def _apporteur_plan(db, idu: str, voisines: dict) -> dict | None:
    """RECETTE-3 (T1) — plan de situation : ortho IGN + contour de la parcelle (mint) et overlay des
    voisines du même propriétaire. Réutilise `plan_ortho` (point d'appel unique des tuiles). Réseau
    indisponible / parcelle sans géométrie → None (le brief imprime un cadre neutre, jamais d'erreur)."""
    from sqlalchemy import text
    try:
        gj = db.execute(text("SELECT ST_AsGeoJSON(geom) FROM parcels WHERE idu = :idu"), {"idu": idu}).scalar()
    except Exception:  # noqa: BLE001
        return None
    if not gj:
        return None
    extra = None
    ids = [m["idu"] for m in (voisines or {}).get("membres", [])]
    if ids:
        try:
            extra = db.execute(text("SELECT ST_AsGeoJSON(ST_Collect(geom)) FROM parcels WHERE idu = ANY(:ids)"),
                               {"ids": ids}).scalar()
        except Exception:  # noqa: BLE001
            extra = None
    try:
        from ..api.plan_situation import plan_ortho
        from ..flash.report import storage_dir
        res = plan_ortho(gj, cache_dir=storage_dir() / "tiles", extra_geojson=extra, zoom_delta=-1)
    except Exception:  # noqa: BLE001 — la carte est un plus, jamais un bloqueur du document
        return None
    if not res.get("ok"):
        return None
    import base64
    return {"img": "data:image/jpeg;base64," + base64.b64encode(res["jpeg"]).decode(),
            "attribution": res.get("attribution")}


def _apporteur_contexte(db, idu: str, fiche: dict, jour: date, compte_id: int | None) -> dict:
    """Contexte de l'Apporteur : émetteur (compte), dates d'émission/validité (90 j), les drapeaux
    des blocs adaptatifs (bâti / personne morale / usage industriel proche), les voisines du même
    propriétaire et le plan de situation (RECETTE-3 T1)."""
    import json
    from datetime import timedelta
    lb = fiche.get("le_bien") or {}
    pm = fiche.get("proprietaire_moral")
    industriel = "ICPE" in json.dumps(fiche.get("lines") or [], ensure_ascii=False)
    voisines = _apporteur_voisines(db, idu)
    return {
        "idu": idu, "adresse": fiche.get("adresse") or "", "emetteur": _emetteur(db, compte_id),
        "emission": f"{jour:%d/%m/%Y}", "validite": f"{jour + timedelta(days=90):%d/%m/%Y}",
        "is_bati": bool(lb.get("nb_batiments") or lb.get("emprise_batie_m2")),
        "is_pm": isinstance(pm, dict) and bool(pm),
        "industriel_proche": industriel,
        "voisines": voisines,
        "plan": _apporteur_plan(db, idu, voisines),
    }


def construire(db, idu: str, document: str = "dossier", *, fiche: dict | None = None,
               jour: date | None = None, compte_id: int | None = None) -> ResultatDoc:
    """Assemble le HTML complet d'un document et les Valeur lues (pour l'archive). Pour le Financier,
    `compte_id` sert à charger le questionnaire persisté du porteur."""
    from .collecte import collecte
    if document not in DOCUMENTS:
        raise ValueError(f"document inconnu : {document!r} (câblé : {sorted(DOCUMENTS)})")
    j = jour or date.today()
    f = fiche or {}
    numero = numeros.numero_rapport(document, idu, j)
    blocs = DOCUMENTS[document]
    ids = sorted({cid for b in blocs for cid in b.IDS})
    valeurs = collecte(db, idu, ids, fiche=f)
    ctx = None
    if document == "financier":
        ctx = _financier_contexte(db, idu, f, compte_id)
    elif document == "apporteur":
        ctx = _apporteur_contexte(db, idu, f, j, compte_id)
    label, _ = _LABEL.get(document, (document, ""))
    adresse = f.get("adresse") or ""
    au = f.get("donnees_labuse_au") or f"{j:%d/%m/%Y}"
    cart = Cartouche(
        doc_title=f"LABUSE — {label}" + (f" · {adresse}" if adresse else ""),
        doc_ref=f"{idu} · {numero}",
        doc_foot=_FOOT.get(document, "Document d'information LABUSE. Données au {au}.").format(au=au),
    )
    corps = _cover(document, idu, f, numero, j, valeurs)
    for b in blocs:
        corps += b.rendu(valeurs, ctx) if document in _AVEC_CONTEXTE else b.rendu(valeurs)
    html = page_html(label, cart, corps)
    return ResultatDoc(html=html, valeurs=valeurs, numero=numero, cartouche=cart)


def generer_pdf(db, idu: str, document: str = "dossier", *, fiche: dict | None = None,
                jour: date | None = None, chemin_pdf=None, compte_id: int | None = None):
    """Rend le PDF d'un document et, si `chemin_pdf` est donné, écrit le PDF + son archive JSON
    (reproductibilité — lot 1.6). Rend (bytes_pdf, ResultatDoc)."""
    res = construire(db, idu, document, fiche=fiche, jour=jour, compte_id=compte_id)
    pdf = render_pdf(res.html, forms=(document == "apporteur"))
    if chemin_pdf is not None:
        from pathlib import Path
        Path(chemin_pdf).write_bytes(pdf)
        j = (jour or date.today()).isoformat()
        archive.ecrire_archive(chemin_pdf, archive.payload_archive(
            document, idu, res.numero, res.valeurs, genere_le=j))
    return pdf, res
