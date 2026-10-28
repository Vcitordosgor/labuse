"""EXPORTS-2 lot 1 — LE BUILDER UNIQUE : un document = une suite de blocs du catalogue. Le
builder réunit les ids de tous les blocs, appelle la collecte UNE fois, passe les Valeur aux
blocs (purs), assemble le HTML avec le cartouche @page, rend le PDF (WeasyPrint) et archive les
Valeur lues à côté du PDF. Les cinq documents (lots 2-7) ne sont que des listes de blocs ici.

Le lot 1 câble le Dossier partiel (page de garde + section 1) pour prouver la chaîne de bout en
bout sur les quatre témoins ; les lots 2-7 ajoutent les blocs.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date

from ..registre.valeur import Valeur
from ..tz import today_reunion   # FIX-ORFEVRE-1 pt 3 (ORF-17/D-13) — « généré le » au jour Réunion
from . import archive, numeros

# ORF-19 (FIX-ORFEVRE-1) — les best-effort du builder restent (jamais un 500 sur un document client),
# mais un échec N'EST PLUS MUET : chaque repli se dit en warning (un bug de code ne doit pas être
# indistinguable d'une vraie absence de donnée).
log = logging.getLogger("labuse.exports.builder")


def _donnees_labuse_au() -> str | None:
    """CHASSE-DONNEES-FIX-1 (suite 2c, C-36) — « Données LABUSE au » = date de la DONNÉE servie (la
    dernière bascule du run servi, config/served_manifest.json `promoted_at`), PAS la date de
    génération du PDF. None si le manifeste est illisible (le builder retombe alors sur la date du
    jour, comportement historique)."""
    try:
        import json
        import pathlib
        racine = pathlib.Path(__file__).resolve().parents[3]   # src/labuse/exports/builder.py → racine
        m = json.loads((racine / "config" / "served_manifest.json").read_text())
        p = (m.get("promoted_at") or "")[:10]   # 'YYYY-MM-DD'
        if len(p) == 10:
            a, mo, d = p.split("-")
            return f"{d}/{mo}/{a}"
    except Exception as exc:  # noqa: BLE001 — jamais bloquant, mais DIT (ORF-19)
        import logging
        logging.getLogger("labuse.exports.builder").warning(
            "served_manifest.json illisible (%s) — « Données LABUSE au » retombe sur la date du jour", exc)
        return None
    return None
# EXPORTS-REBRANCHEMENT-1 lot 1 — le Dossier miroir ne consomme plus les anciens blocs de
# section ; restent les blocs-documents (financier, apporteur) et la clôture (sources).
from .blocs import apporteur, financier
from .registre_fmt import fmt_m2
from .rendu import Cartouche, esc, esc_noms, page_html, render_pdf

MODELE_VERSION = "3.0"   # EXPORTS-REBRANCHEMENT — le Dossier miroir de la fiche (v4)


class DocumentNonEtablissable(Exception):
    """RECETTE-5 (V18b) — levée quand un document ne peut PAS être établi faute d'éléments
    indispensables (ex. le Financier sans prix de sortie / régime de TVA / programme constructible).
    Le document ne se génère PAS ; la route la traduit en 422 + la liste des manques, et l'écran dit
    lesquels manquent — plutôt que d'imprimer trois pages de tableau « non chiffré »."""
    def __init__(self, manques: list[dict]):
        self.manques = manques
        super().__init__("document non établissable : " + ", ".join(m["libelle"] for m in manques))

#: libellé et sous-titre de chaque document (page de garde).
_LABEL = {
    "dossier": ("Dossier parcelle", "Ce que cette parcelle est, ce qu'elle porte, ce que le règlement y permet."),
    "flash": ("Rapport Flash", "Ce que cette parcelle est, ce qu'elle porte, ce que le règlement y permet."),
    # DOCS-1 §4 (décision Vic) — le document s'appelle « Bilan » côté client (ex « Dossier financier »,
    # RECETTE-5 V17). La clé interne reste « financier » (route, builder, questionnaire) ; seul le
    # LIBELLÉ humain change (titre de garde + nom de fichier). Moteur/ratios/Excel → BILAN-1.
    "financier": ("Bilan", ""),
    "apporteur": ("Brief apporteur", ""),
    # DOCS-1 (Lot C) — les 3 nouveaux documents (miroirs des outils Gabarit, Comparer, Étude de zone).
    "gabarit": ("Gabarit", "L'enveloppe réglementaire de la parcelle : zone d'implantation, plafond d'emprise, hauteur."),
    "comparatif": ("Comparatif", "Deux à trois parcelles côte à côte, sur les lignes de Comparer."),
    "etude-zone": ("Étude de zone", "Le territoire autour de la parcelle, dans le rayon choisi."),
  # ANNONCE-3 — miroir de l'outil « Analyser une annonce » : une adresse (rapport parcelle) ou un lien
  # d'annonce (rapport commune). Même source que l'écran ; aucun moteur neuf.
  "analyse-annonce": ("Analyse d'annonce", "Une adresse ou un lien d'annonce, croisés au marché et au foncier."),
}


def titre_document(document: str) -> str:
    """RECETTE-5 (V17) — le titre humain d'un document (page de garde) — point unique, réutilisé
    pour le nom de fichier téléchargé (« Bilan — FI-….pdf »)."""
    return _LABEL.get(document, (document, ""))[0]

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
    # DOCS-1 (Lot C)
    "gabarit": ("Gabarit réglementaire 2D, pré-faisabilité sur règlement public. Ne remplace ni un "
                "certificat d'urbanisme, ni une étude de faisabilité réglementaire. Données LABUSE au {au}."),
    "comparatif": ("Comparatif indicatif de parcelles établi sur des données publiques. Ni un prix, "
                   "ni un conseil. Données LABUSE au {au}."),
    "etude-zone": ("Agrégats de données publiques dans le périmètre indiqué. Les mailles « à l'échelle "
                   "de la commune » portent sur toute la commune. Données LABUSE au {au}."),
    # ANNONCE-3 — l'estimation est COMPARATIVE (prix observés au m², DVF), jamais un avis de valeur.
    "analyse-annonce": ("Estimation comparative établie sur des données publiques (prix observés au m², "
                        "DVF) — ce n'est pas un avis de valeur. Sources : DVF · Radar LABUSE. "
                        "Données LABUSE au {au}."),
}

#: composition de chaque document. EXPORTS-REBRANCHEMENT-1 lot 1 : le Dossier n'est PLUS une
#: suite de blocs — il est le MIROIR des déclarations de la fiche (exports/miroir.py, 11
#: sections de declarations/fiche/sections.yaml) + la clôture Sources/limites. Le Flash EST le
#: Dossier (un nom commercial, pas un document : rendu identique, même numéro DP).
#: RECETTE-3 (T2, décision Vic) — le document Résumé est SUPPRIMÉ (route, builder, bloc, bouton).
_MIROIR = "miroir"
DOCUMENTS: dict[str, object] = {
    "dossier": _MIROIR,
    "flash": _MIROIR,
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
    #: RECETTE-7 lot 0 (Z5) — le contexte Financier/Apporteur (bilan dérivé, voisines, adresse)
    #: est porté ici pour que le crible de provenance rattache aussi SES nombres au registre.
    contexte: dict | None = None


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
    # RECETTE-8 W21 — l'en-tête compact du Financier mettait l'adresse dans un h1 à 24 pt : elle
    # cassait au milieu, entre le code postal et la commune (« …97417 / Saint-Denis »). On la sert
    # dans une classe DÉDIÉE plus petite (16 pt) ET on LIE le code postal à la commune par une
    # espace insécable U+00A0 (qui s'extrait proprement en espace, contrairement à U+2011 — F2) :
    # « 97417 Saint-Denis » ne se scinde plus (E7 gardant déjà « Saint-Denis » insécable).
    import re as _re
    adr = _re.sub(r"(\b\d{5})\s+", lambda m: m.group(1) + " ", esc_noms(adresse or label))
    return (f'<div class="brand"><span class="wordmark">LABUSE</span>'
            f'<span class="kind">{esc(label)}</span></div>'
            f'<h1 class="addr-compacte">{adr}</h1>'
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
        + (f'<p class="address">{esc_noms(adresse)}</p>' if adresse else "")   # E7 (Saint-Denis)
        + f'<p class="idu">{esc(idu)}{(" · " + esc_noms(commune)) if commune else ""}</p>'
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
    # PRIX-SORTIE-1 (Vic 05/10/2026) — pré-remplissage du prix de sortie = prix NEUF servi
    # (source unique), identique à la fiche/calculette ; None si non calculable → non pré-rempli.
    prefill = qf.prefill(fiche, qf.prix_sortie_neuf_servi(db, idu))
    resolved = qf.resoudre(etat["reponses"], prefill)
    rv = lambda fid: (resolved.get(fid) or {}).get("valeur")  # noqa: E731
    # RECETTE-8 W13bis (C3) — le parcours « Revente en l'état » : calcul de marge SIMPLE (pas de
    # bilan à rebours, pas de programme constructible). On dispatche AVANT tout le calcul construction.
    if qf.usage_choisi(etat["reponses"]) == "revente":
        hyp_rev = {"prix_achat": rv("prix_achat_revente_saisi_eur"),
                   "prix_revente": rv("prix_revente_saisi_eur"),
                   "frais_acq_pct": rv("frais_acquisition_saisi_pct"),
                   "travaux": rv("travaux_revente_saisi_eur"),
                   "duree_portage": rv("duree_portage_saisi_mois"),
                   "taux_apport": rv("taux_apport_saisi_pct")}
        return {"usage": "revente", "revente": fb.calculer_revente(hyp_rev),
                "resolved": resolved, "prefill": prefill, "complet": etat["complet"],
                "existe": etat["existe"], "bilan": None, "program": None,
                "tfpb": None, "zonage_abc": None,
                "manques": qf.manques_revente(resolved)}
    hyp = {
        "prix_sortie": rv("prix_sortie_saisi_eur_m2"), "prix_bailleur": rv("prix_vente_bailleur_saisi_eur_m2"),
        "cout": rv("cout_construction_saisi_eur_m2"), "honoraires_pct": rv("honoraires_techniques_saisi_pct"),
        "vrd_m2": rv("vrd_saisi_eur_m2"), "cout_place": rv("cout_place_stationnement_saisi_eur"),
        "aleas_pct": rv("aleas_saisi_pct"), "marge_pct": rv("marge_visee_saisi_pct"),
        "frais_acq_pct": rv("frais_acquisition_saisi_pct"), "prix_demande": rv("prix_demande_saisi_eur"),
        "demolition": rv("bilan_demolition_eur"), "depollution": rv("bilan_depollution_eur"),
        "taxe": rv("taxe_amenagement_saisi_eur"), "duree_portage": rv("duree_portage_saisi_mois"),
        "taux_apport": rv("taux_apport_saisi_pct"), "part_sociale_pct": rv("part_sociale_saisi_pct") or 0,
        "rap": None,   # TAXE-FIX-1 point 2 — RAP (0,40 % assiette), chiffrée ci-dessous par calculer()
    }
    pot = fiche.get("potentiel_transformation") or {}
    # LOGEMENTS-SOURCE-UNIQUE — le programme ne tire PLUS un nombre de logements de l'ancien calcul
    # de capacité (A-05-1 prenait la borne haute de `logements_au_sol`) : seule la SAISIE du porteur
    # (logements_vises_saisi) porte un nombre ; sinon le Financier imprime le renvoi de la fiche
    # (« voir l'Étude de faisabilité » — moteur d'implantation, seul à compter des logements).
    program = {
        # CONTENANCE-1 (Lot B) : surface de terrain = contenance si présente, sinon dessin.
        "surface_terrain": fiche.get("surface_terrain_m2") or fiche.get("surface_m2"),
        "logements": rv("logements_vises_saisi"),
        "surface_vendable": pot.get("surface_vendable_m2"),
        "surface_plancher": pot.get("surface_plancher_m2"),
    }
    if not program["surface_vendable"] and program["logements"]:
        typo = str(rv("typologie_moyenne_saisi") or "T3").upper().strip()
        surf = _TYPOLOGIE_SURFACE.get(typo, 60)
        program["surface_vendable"] = program["logements"] * surf
        program["surface_plancher"] = program["surface_vendable"] / 0.8
    # RECETTE-8 W2 — la taxe d'aménagement du bilan porte sur la SDP du PROJET (`program`), au taux
    # communal public. On ne la pré-calcule que si le porteur ne l'a NI saisie NI explicitement vidée
    # (règle 2 : un champ vidé reste vide) et que le projet a une SDP. C'est le SEUL endroit où la
    # taxe est chiffrée : sur une SDP de projet, jamais sur un scénario de fiche (W1/W2).
    if program.get("surface_plancher"):
        from .. import taxe_amenagement as _tax
        # TAXE-FIX-1 point 3 — résolution PAR PARCELLE (secteur à taux majoré prioritaire).
        _pub = _tax.taux_parcelle(db, idu) if idu else None
        _res = _tax.calculer(
            surface_taxable_m2=float(program["surface_plancher"]),
            taux_communal_public_pct=(_pub["part_communale_pct"] if _pub else None),
            taux_communal_public_source=(_pub["source"] if _pub else None),
            taux_communal_public_millesime=(_pub["millesime"] if _pub else None),
            taux_communal_public_delib_date=(_pub["delib_date"] if _pub else None),
            taux_communal_public_perime=(_pub["perime"] if _pub else None),
            taux_communal_secteur_majore=bool(_pub and _pub.get("secteur_majore")))
        # TAXE-FIX-1 point 2 — la RAP (0,40 % de l'assiette TA) accompagne la taxe : toujours chiffrée
        # dès qu'il y a une SDP, MÊME quand le porteur a saisi la taxe d'aménagement à la main.
        hyp["rap"] = _res["rap_eur"]
        # La taxe d'aménagement n'est pré-remplie que si le porteur ne l'a NI saisie NI vidée (W2).
        if ("taxe_amenagement_saisi_eur" not in etat["reponses"]
                and hyp["taxe"] is None and _res["total_eur"] is not None):
            hyp["taxe"] = _res["total_eur"]
            resolved["taxe_amenagement_saisi_eur"] = {
                "valeur": round(float(_res["total_eur"])), "origine": "prefill",
                # TAXE-FIX-1 point 4 — la taxe porte sur la SURFACE TAXABLE (close et couverte,
                # garages et annexes inclus, CGI 1635 quater H) ; on l'approche ici par la SDP du
                # projet (garages/annexes non modélisés → estimation plutôt basse).
                "source": (f"taxe d'aménagement sur la surface taxable "
                           f"(≈ SDP du projet {round(float(program['surface_plancher']))} m², "
                           "garages/annexes non modélisés) au taux communal — config datée, "
                           "service-public.gouv.fr")}
    # RECETTE-4 U1/U2 — la fiscalité locale de la commune (taux TFPB, REI DGFiP) et sa zone A/B/C
    # (DHUP) entrent au Financier : la taxe foncière pèse sur les charges de portage et la zone
    # commande le régime applicable (TVA accession, PTZ, prix bailleur). Passe-plats sourcés + datés ;
    # None si non ingérés (jamais devinés). L'insee vient de l'IDU.
    insee = (idu or "")[:5]
    tfpb = zonage = None
    try:
        from ..ingestion.rei import rei_commune
        tfpb = rei_commune(db, insee)
    except Exception:  # noqa: BLE001 — table absente = source non ingérée, jamais un 500
        db.rollback()
    try:
        from ..ingestion.zonage_abc import zonage_commune
        zonage = zonage_commune(db, insee)
    except Exception:  # noqa: BLE001
        db.rollback()
    bilan = fb.calculer(program, hyp)
    manques = qf.manques(resolved, program)
    # RECETTE-11 B2 — DÉFENSE : une hypothèse hors marché ne produit PLUS un PDF « bilan non établi ».
    # Le questionnaire la bloque en amont (valider_hors_marche) ; si malgré tout la génération est
    # atteinte (saisie ancienne, URL directe), le document est REFUSÉ (422) — jamais imprimé sur le ton
    # d'un bilan. Le garde reste le point de vérité unique (`_hors_marche`).
    hm = bilan.get("hors_marche") if isinstance(bilan, dict) else None
    if hm:
        manques = [{"libelle": f"Hypothèse hors marché : {hm['champ']}",
                    "raison": hm.get("raison", "valeur hors bornes de vraisemblance")}] + manques
    return {"bilan": bilan, "resolved": resolved, "prefill": prefill,
            "complet": etat["complet"], "existe": etat["existe"], "program": program,
            "tfpb": tfpb, "zonage_abc": zonage,
            # RECETTE-5 (V18b) — les éléments indispensables manquants pour établir le bilan (vide ⇒ OK).
            "manques": manques}


def _emetteur(db, compte_id: int | None) -> dict | None:
    """RECETTE-12 E1 — l'émetteur du brief = le compte de l'utilisateur (NON anonyme : refus Vic
    05/09). Nom (marque.raison_sociale sinon comptes.nom) + coordonnées (marque.coordonnees, qui porte
    le téléphone) + e-mail (utilisateurs). Best-effort : rien de servable → None."""
    if not compte_id:
        return None
    import json

    from sqlalchemy import text
    try:
        row = db.execute(text("SELECT nom, marque FROM comptes WHERE id = :i"),
                         {"i": compte_id}).mappings().first()
    except Exception as exc:  # noqa: BLE001 — colonne/table absente (base de test) : émetteur non servi
        log.warning("émetteur du brief non servi (compte %s) : %s — bloc émetteur omis (ORF-19)",
                    compte_id, exc)
        return None
    if not row:
        return None
    marque = row.get("marque") or {}
    if isinstance(marque, str):
        try:
            marque = json.loads(marque)
        except Exception:  # noqa: BLE001
            marque = {}
    nom = (marque.get("raison_sociale") or row.get("nom") or "").strip() or None
    coord = (marque.get("coordonnees") or "").strip() or None
    email = None
    try:
        email = db.execute(text("SELECT email FROM utilisateurs WHERE compte_id = :i ORDER BY id LIMIT 1"),
                           {"i": compte_id}).scalar()
    except Exception:  # noqa: BLE001
        email = None
    if not (nom or coord or email):
        return None
    return {"nom": nom, "coordonnees": coord, "email": email}


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
            # CONTENANCE-1 (Lot B) : surface des voisines du bloc = terrain (contenance si présente,
            # sinon le dessin stocké sur le membre). Jointure parcels pour la contenance.
            """WITH b AS (SELECT bloc_id FROM parcel_bloc_membres WHERE idu = :idu LIMIT 1)
               SELECT m.idu, COALESCE(p.contenance_m2, m.surface_m2) AS surface_m2
               FROM parcel_bloc_membres m JOIN b ON b.bloc_id = m.bloc_id
               LEFT JOIN parcels p ON p.idu = m.idu
               WHERE m.idu <> :idu ORDER BY COALESCE(p.contenance_m2, m.surface_m2) DESC NULLS LAST, m.idu"""),
            {"idu": idu}).mappings().all()
    except Exception as exc:  # noqa: BLE001 — table absente / base de test : pas de voisines, jamais d'erreur
        log.warning("voisines du bloc non servies (%s) : %s — document rendu sans voisines (ORF-19)",
                    idu, exc)
        return {"n": 0, "membres": [], "surface_totale_m2": None}
    membres = [{"idu": r["idu"], "ref": _ref_courte(r["idu"]),
                "surface_m2": round(r["surface_m2"]) if r["surface_m2"] else None} for r in rows]
    total = sum(m["surface_m2"] or 0 for m in membres) or None
    return {"n": len(membres), "membres": membres, "surface_totale_m2": total}


def _plan_situation_html(db, idu: str) -> str:
    """EXPORTS-REBRANCHEMENT-2 lot 1 — le plan de situation en fragment HTML `.plan`, MÊME composant
    que l'Apporteur (ortho IGN + contour + voisines du même propriétaire). Utilisé par le §1 du
    Dossier. Best-effort : réseau/géométrie absents → cadre neutre légendé (jamais d'erreur)."""
    from .rendu import esc
    try:
        voisines = _apporteur_voisines(db, idu)
        plan = _apporteur_plan(db, idu, voisines)
    except Exception:  # noqa: BLE001 — le plan est un plus, jamais un bloqueur du Dossier
        plan = None
    if plan and plan.get("img"):
        cap = esc(plan.get("attribution") or "")
        legende = ("Plan de situation — la parcelle (contour) et ses voisines"
                   + (f" · {cap}" if cap else ""))
        return (f'<div class="plan" data-quoi="parcelle_geometrie">'
                f'<img src="{plan["img"]}" alt="Plan de situation">'
                f'<div class="cap">{legende}</div></div>')
    return ('<div class="plan" data-quoi="parcelle_geometrie"><div class="ph">'
            'Plan de situation — la parcelle et ses voisines '
            '(fond cartographique momentanément indisponible)</div></div>')


def _apporteur_plan(db, idu: str, voisines: dict) -> dict | None:
    """RECETTE-3 (T1) — plan de situation : ortho IGN + contour de la parcelle (mint) et overlay des
    voisines du même propriétaire. Réutilise `plan_ortho` (point d'appel unique des tuiles). Réseau
    indisponible / parcelle sans géométrie → None (le brief imprime un cadre neutre, jamais d'erreur)."""
    from sqlalchemy import text
    try:
        gj = db.execute(text("SELECT ST_AsGeoJSON(geom) FROM parcels WHERE idu = :idu"), {"idu": idu}).scalar()
    except Exception as exc:  # noqa: BLE001
        log.warning("géométrie de %s illisible pour le plan de situation : %s — cadre neutre (ORF-19)",
                    idu, exc)
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
        # EXPORTS-FIX-1 F3 — le plan se CALE sur la parcelle : zoom auto (plus de « −1 » qui la
        # rétrécissait) et plafond relevé à 19 (max ortho IGN) pour qu'une petite parcelle (479 m²)
        # ne reste pas un point. Même appel pour le Dossier (§1) et l'Apporteur.
        res = plan_ortho(gj, cache_dir=storage_dir() / "tiles", extra_geojson=extra,
                         zoom_delta=0, zoom_max=19)
    except Exception as exc:  # noqa: BLE001 — la carte est un plus, jamais un bloqueur du document
        log.warning("plan de situation de %s non rendu : %s — cadre neutre (ORF-19)", idu, exc)
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
    # RECETTE-11 D7 — l'ICPE proche vient du MÊME MOTEUR que le Dossier (la cascade `lines`), pas d'un
    # « ICPE » trouvé dans le JSON (qui fuyait le seul NOM de la source du catalogue : faux positif).
    # Signalée seulement si la cascade la RELÈVE (result ≠ PASS), avec sa description/distance.
    _icpe = next((l for l in (fiche.get("lines") or [])
                  if isinstance(l, dict) and l.get("layer") == "icpe"), None)
    industriel = bool(_icpe and _icpe.get("result") not in (None, "PASS"))
    icpe_detail = _icpe.get("detail") if industriel else None
    voisines = _apporteur_voisines(db, idu)
    # EXPORTS-REBRANCHEMENT-2 lot 3 — les DRAPEAUX D'OBSERVATION du §6 « Le terrain, vu sur place » :
    # une question n'est imprimée que si la couche TOUCHE la parcelle (même moteur que le Dossier, la
    # cascade `lines` + les aléas). L'apporteur observe ce que le foncier signale, jamais une liste vide.
    _lines = [l for l in (fiche.get("lines") or []) if isinstance(l, dict)]
    def _releve(layer: str) -> bool:
        return any(l.get("layer") == layer and l.get("result") not in (None, "PASS") for l in _lines)
    # DOCS-COHERENCE-1 (C2) — un SOFT_FLAG (ex. TRI : territoire de GESTION du risque inondation, large
    # périmètre) n'est PAS un aléa d'eau à la parcelle : il ne doit pas, à lui seul, déclencher la
    # question « Traces d'eau » (BY0083 : TRI SOFT_FLAG, aucun aléa d'eau → question retirée).
    def _releve_ferme(layer: str) -> bool:
        return any(l.get("layer") == layer and l.get("result") not in (None, "PASS", "SOFT_FLAG") for l in _lines)
    _aleas = (fiche.get("aleas") or {}).get("liste") or []
    # EXPORTS-FIX-1 E3 — on regarde la nature ET le libellé (l'ancien « nature or libelle » s'arrêtait
    # à la nature « PPR — zone bleue » et manquait « …inondation… » du libellé → P1, qui a un PPR
    # inondation, n'avait pas la question d'eau et se retrouvait identique à P2).
    obs_eau = (_releve_ferme("ravine") or _releve_ferme("zone_humide") or _releve_ferme("tri_zone")
               or _releve_ferme("dpf")
               or any(isinstance(a, dict) and any(
                      k in ((a.get("nature") or "") + " " + (a.get("libelle") or "")).lower()
                      for k in ("inond", "submers", "ravine", "humide")) for a in _aleas))
    obs_pollution = industriel or _releve("sol_pollue") or _releve("casias")
    # DOCS-COHERENCE-1 (C2) — question « Mouvements de sol » quand un aléa de mouvement de terrain est
    # relevé (au lieu de la question d'eau, qui ne concerne que inondation/ravine/zone humide).
    obs_mouvement = (_releve("mouvement_terrain") or any(
        isinstance(a, dict) and any(k in ((a.get("nature") or "") + " " + (a.get("libelle") or "")).lower()
                                    for k in ("mouvement", "glissement", "retrait", "gonflement", "argile"))
        for a in _aleas))
    return {
        "idu": idu, "adresse": fiche.get("adresse") or "", "emetteur": _emetteur(db, compte_id),
        "emission": f"{jour:%d/%m/%Y}", "validite": f"{jour + timedelta(days=90):%d/%m/%Y}",
        "is_bati": bool(lb.get("nb_batiments") or lb.get("emprise_batie_m2")),
        "is_pm": isinstance(pm, dict) and bool(pm),
        "industriel_proche": industriel,
        # §6 — questions d'observation conditionnelles (imprimées si la couche touche). La ligne
        # HTA/HTB (< 50 m) n'a pas de couche fiable dans le socle → question omise tant qu'elle manque.
        "obs_eau": obs_eau, "obs_mouvement": obs_mouvement, "obs_pollution": obs_pollution, "obs_ligne_ht": False,
        "icpe_detail": icpe_detail,   # RECETTE-11 D7 — description/distance de l'ICPE relevée
        "voisines": voisines,
        "plan": _apporteur_plan(db, idu, voisines),
    }


def construire(db, idu: str, document: str = "dossier", *, fiche: dict | None = None,
               jour: date | None = None, compte_id: int | None = None) -> ResultatDoc:
    """Assemble le HTML complet d'un document et les Valeur lues (pour l'archive). Pour le Financier,
    `compte_id` sert à charger le questionnaire persisté du porteur."""
    from .robinet_fiche import EXTRACTEURS, collecte
    if document not in DOCUMENTS:
        raise ValueError(f"document inconnu : {document!r} (câblé : {sorted(DOCUMENTS)})")
    j = jour or today_reunion()
    f = fiche or {}
    # EXPORTS-REBRANCHEMENT-1 lot 1 — Flash = Dossier (nom commercial) : rendu, libellé et
    # NUMÉRO identiques (preuve : pdftotext diff vide). L'entrée « flash » reste acceptée
    # (facturation _flash_fulfill), le document rendu est LE Dossier.
    document = "dossier" if document == "flash" else document
    numero = numeros.numero_rapport(document, idu, j)
    if DOCUMENTS[document] == _MIROIR:
        from . import miroir
        ids = sorted(ids_m for ids_m in miroir.ids_declares() | {"run_label_servi"}
                     if ids_m in EXTRACTEURS)
        valeurs = collecte(db, idu, ids, fiche=f)
        label, _st = _LABEL["dossier"]
        adresse = f.get("adresse") or ""
        au = f.get("donnees_labuse_au") or _donnees_labuse_au() or f"{j:%d/%m/%Y}"
        cart = Cartouche(
            doc_title=f"LABUSE — {label}" + (f" · {adresse}" if adresse else ""),
            doc_ref=f"{idu} · {numero}",
            doc_foot=_FOOT["dossier"].format(au=au))
        # EXPORTS-REBRANCHEMENT-2 lot 1 — le plan de situation de §1 = le MÊME composant que
        # l'Apporteur (ortho IGN + contour + voisines du même propriétaire). Best-effort : réseau
        # indisponible / parcelle sans géométrie → cadre neutre, jamais une erreur.
        plan_html = _plan_situation_html(db, idu)
        corps = (miroir.cover_dossier(idu, f, numero, j, valeurs, MODELE_VERSION)
                 + miroir.rendu_sections(valeurs, f, plan_html=plan_html))
        html = page_html(label, cart, corps)
        return ResultatDoc(html=html, valeurs=valeurs, numero=numero, cartouche=cart,
                           contexte={"adresse": adresse})
    blocs = DOCUMENTS[document]
    ids = sorted({cid for b in blocs for cid in b.IDS})
    valeurs = collecte(db, idu, ids, fiche=f)
    ctx = None
    if document == "financier":
        ctx = _financier_contexte(db, idu, f, compte_id)
        # RECETTE-5 (V18b) — tant qu'un élément indispensable manque, le Financier NE SE GÉNÈRE PAS
        # (l'écran dira lesquels). Fini les trois pages de tableau « non chiffré » sous un document qui
        # annonce lui-même qu'il ne peut pas être établi.
        if ctx.get("manques"):
            raise DocumentNonEtablissable(ctx["manques"])
    elif document == "apporteur":
        ctx = _apporteur_contexte(db, idu, f, j, compte_id)
    label, _ = _LABEL.get(document, (document, ""))
    adresse = f.get("adresse") or ""
    au = f.get("donnees_labuse_au") or _donnees_labuse_au() or f"{j:%d/%m/%Y}"
    cart = Cartouche(
        doc_title=f"LABUSE — {label}" + (f" · {adresse}" if adresse else ""),
        doc_ref=f"{idu} · {numero}",
        doc_foot=_FOOT.get(document, "Document d'information LABUSE. Données au {au}.").format(au=au),
    )
    corps = _cover(document, idu, f, numero, j, valeurs)
    for b in blocs:
        corps += b.rendu(valeurs, ctx) if document in _AVEC_CONTEXTE else b.rendu(valeurs)
    html = page_html(label, cart, corps)
    return ResultatDoc(html=html, valeurs=valeurs, numero=numero, cartouche=cart,
                       contexte={**(ctx or {}), "adresse": adresse})


# ── DOCS-1 (Lot C) — les 3 nouveaux documents : miroirs des outils, même builder/couverture/pied. ──
_GABARIT_INCALCULABLE = "Gabarit non calculable sur cette parcelle : donnée réglementaire manquante"


def _entete_doc(document: str, ref_ligne: str, numero: str, jour: date) -> str:
    """En-tête compact commun aux 3 nouveaux documents (même marque/typo que l'en-tête Financier) :
    marque + titre + sous-titre + ligne d'identité (référence · n° de rapport · date)."""
    label, sous = _LABEL.get(document, (document, ""))
    return (f'<div class="brand"><span class="wordmark">LABUSE</span>'
            f'<span class="kind">{esc(label)}</span></div>'
            f'<h1>{esc(label)}</h1>'
            + (f'<p class="subtitle">{esc(sous)}</p>' if sous else "")
            + f'<p class="idu">{esc(ref_ligne)} · {esc(numero)} · {jour:%d/%m/%Y}</p>')


def _cart(document: str, titre_suffixe: str, idu_ref: str, numero: str, jour: date) -> Cartouche:
    label, _ = _LABEL.get(document, (document, ""))
    # CHASSE-DONNEES-FIX-1 (suite 2c, C-36) — « Données au » = date de la DONNÉE servie (run servi),
    # plus la date de GÉNÉRATION du PDF (gabarit/comparatif/étude-zone).
    au = _donnees_labuse_au() or f"{jour:%d/%m/%Y}"
    return Cartouche(
        doc_title=f"LABUSE — {label}" + (f" · {titre_suffixe}" if titre_suffixe else ""),
        doc_ref=f"{idu_ref} · {numero}",
        doc_foot=_FOOT.get(document, "Document d'information LABUSE. Données au {au}.").format(au=au))


def construire_gabarit(db, idu: str, *, jour: date | None = None) -> ResultatDoc:
    """Le Gabarit, miroir de l'outil /outils/gabarit : plan 2D + zone d'implantation + plafond
    d'emprise + hauteur + règles appliquées / non intégrées. ABSENT si « Calcul incomplet » :
    on lève DocumentNonEtablissable (la route rend 422 + le message, la porte le dit avant génération).
    On lit le MÊME moteur que l'écran (build_gabarit_input + compute_gabarit)."""
    from ..gabarit.builder import build_gabarit_input
    from ..gabarit.engine import compute_gabarit
    from .blocs import gabarit as bloc_gabarit
    from .robinet_fiche import collecte
    j = jour or today_reunion()
    build = build_gabarit_input(db, idu)
    if build is None or build.blocking:
        raise DocumentNonEtablissable([{"libelle": _GABARIT_INCALCULABLE}])
    gr = compute_gabarit(build.input)
    if gr.status != "ok":
        raise DocumentNonEtablissable([{"libelle": _GABARIT_INCALCULABLE}])
    # RECETTE-OUTILS-2 (R16) — le bâti EXISTANT n'est peuplé que par l'endpoint outil ; on l'attache
    # ici aussi (best-effort) pour que la vue 3D du PDF montre le MÊME contexte bâti que l'écran.
    try:
        from ..api.gabarit import _bati_existant
        if gr.batiExistantGeoJSON is None:
            gr.batiExistantGeoJSON = _bati_existant(db, idu)
    except Exception:  # noqa: BLE001 — le bâti de contexte n'est jamais un bloqueur du document
        pass
    # RECETTE-OUTILS-3 (S7/S10) — MÊME déduction/découpe que l'app : la zone d'implantation du PDF (p1
    # schéma, p3 3D) déduit le bâti et le bâti est découpé au contour. Référence géométrique UNIQUE.
    try:
        from ..gabarit.builder import deduire_bati_de_zone, rescale_zone_contenance
        rescale_zone_contenance(db, idu, gr)   # U4 — même aire AVANT que l'endpoint (contenance), sinon déduit 46≠40
        deduire_bati_de_zone(gr)
    except Exception:  # noqa: BLE001
        pass
    valeurs = collecte(db, idu, sorted(bloc_gabarit.IDS), fiche={})
    numero = numeros.numero_rapport("gabarit", idu, j)
    cart = _cart("gabarit", idu, idu, numero, j)
    corps = _entete_doc("gabarit", idu, numero, j) + bloc_gabarit.rendu(valeurs, {"gabarit": gr})
    html = page_html(_LABEL["gabarit"][0], cart, corps)
    # le contexte porte le résultat gabarit (pour que le crible de provenance rattache SES nombres).
    return ResultatDoc(html=html, valeurs=valeurs, numero=numero, cartouche=cart,
                       contexte={"gabarit": gr.model_dump() if hasattr(gr, "model_dump") else dict(gr)})


def construire_comparatif(idus: list[str], rows: list[dict], *, jour: date | None = None) -> ResultatDoc:
    """Le Comparatif, miroir de l'outil Comparer (/compare) : 2-3 parcelles en colonnes sur les lignes
    de Comparer, EN PAGE PAYSAGE. `rows` sont les CompareRow servis (aucun recalcul ici)."""
    from .blocs import comparatif as bloc_comparatif
    j = jour or today_reunion()
    ids = [i.strip() for i in idus if i and i.strip()][:3]
    ref0 = ids[0] if ids else ""
    numero = numeros.numero_rapport("comparatif", ref0, j)
    suffixe = f"{len(rows)} parcelles"
    cart = _cart("comparatif", suffixe, " · ".join(ids), numero, j)
    corps = _entete_doc("comparatif", suffixe, numero, j) + bloc_comparatif.rendu(rows)
    html = page_html(_LABEL["comparatif"][0], cart, corps, paysage=True)
    return ResultatDoc(html=html, valeurs={}, numero=numero, cartouche=cart,
                       contexte={"comparatif": rows})


def construire_etude_zone(idu: str, rayon_km, zone: dict, map_html: str, *,
                          jour: date | None = None) -> ResultatDoc:
    """L'Étude de zone, miroir de l'outil /outils/etude-zone en mode rayon : page 1 carte du périmètre
    + « Rayon N km autour de <IDU> », puis les 7 sections. `zone` est le résultat servi (aucun recalcul)."""
    from .blocs import etude_zone as bloc_zone
    j = jour or today_reunion()
    numero = numeros.numero_rapport("etude-zone", idu, j)
    # CHASSE-DONNEES-FIX-1 (Lot 7, E-69) — le titre dit le périmètre RÉELLEMENT calculé (lu de `zone`),
    # plus le rayon DEMANDÉ (un rayon hors whitelist retombe sur l'isochrone).
    from .blocs import etude_zone as bloc_zone
    suffixe = bloc_zone._echelle_label(zone or {}, idu, rayon_km)
    cart = _cart("etude-zone", suffixe, idu, numero, j)
    corps = (_entete_doc("etude-zone", suffixe, numero, j)
             + bloc_zone.rendu(zone, map_html=map_html, idu=idu, rayon_km=rayon_km))
    html = page_html(_LABEL["etude-zone"][0], cart, corps)
    return ResultatDoc(html=html, valeurs={}, numero=numero, cartouche=cart,
                       contexte={"zone": zone})


# ── ANNONCE-3 — « Analyse d'annonce » : deux variantes, miroir de l'outil Analyser une annonce. ──
def construire_analyse_annonce_parc(db, idu: str, *, request=None, jour: date | None = None) -> ResultatDoc:
    """Variante PARCELLE (entrée adresse) : en-tête (adresse · IDU · date) + plan de situation (contour
    parcelle, MÊME composant que le Dossier) + les 6 tuiles + « Estimation du prix » + « Le foncier ».
    Aucun recalcul : on LIT les MÊMES endpoints que l'écran — `parcel_fiche` (prix_ancien, zone PLU,
    SDP, aléas, surface), `parcel_exposition` (orientation), `radar_annonce_classement` (bande du run
    SERVI + vocabulaire gravé). Le PDF sorti de l'outil et celui sorti de Docs sont IDENTIQUES (même route)."""
    from .blocs import annonce as bloc_annonce
    from ..api.app import parcel_exposition, parcel_fiche
    j = jour or today_reunion()
    fiche = parcel_fiche(idu, db=db, request=request)
    try:
        expo = parcel_exposition(idu, db=db)
    except Exception as exc:  # noqa: BLE001 — l'exposition est un plus, jamais un bloqueur (ORF-19)
        log.warning("analyse-annonce %s : exposition indisponible (%s)", idu, exc)
        expo = None
    try:
        from ..pige.api import radar_annonce_classement
        classement = radar_annonce_classement(idu)
    except Exception as exc:  # noqa: BLE001 — le classement est un plus ; sa tuile sera simplement omise
        log.warning("analyse-annonce %s : classement indisponible (%s)", idu, exc)
        classement = None
    numero = numeros.numero_rapport("analyse-annonce", idu, j)
    adresse = fiche.get("adresse") or ""
    ref = " · ".join(x for x in (adresse, idu) if x)
    cart = _cart("analyse-annonce", adresse or idu, idu, numero, j)
    corps = (_entete_doc("analyse-annonce", ref, numero, j)
             + _plan_situation_html(db, idu)
             + bloc_annonce.rendu_parcelle(fiche, expo, classement))
    html = page_html(_LABEL["analyse-annonce"][0], cart, corps)
    return ResultatDoc(html=html, valeurs={}, numero=numero, cartouche=cart,
                       contexte={"idu": idu, "adresse": adresse})


def construire_analyse_annonce_lien(annonce: dict, marche: dict | None, contexte: dict | None, *,
                                    jour: date | None = None) -> ResultatDoc:
    """Variante COMMUNE (entrée lien) : en-tête (type · commune · « Annonce Leboncoin · relevée le … »)
    + « Ce que dit l'annonce » + « Prix face au marché » + « La commune ». `annonce`/`marche` sont les
    sorties EXACTES de `radar_annonce_analyser` (Radar d'abord, sinon fetch) et `contexte` celle de
    `commune_contexte` — aucun recalcul ici (le PDF outil == PDF Docs, même route)."""
    from .blocs import annonce as bloc_annonce
    j = jour or today_reunion()
    a = annonce or {}
    commune = a.get("commune") or ""
    typ = a.get("type")
    pieces = a.get("pieces")
    titre = ((typ[0].upper() + typ[1:]) if typ else "Annonce")
    if isinstance(pieces, int):
        titre += f" {pieces} pièces"
    if commune:
        titre += f" · {commune}"
    # le suffixe du numéro = l'identifiant d'annonce (list_id, chiffres de l'URL) — ASCII et STABLE ;
    # jamais le nom de commune tronqué mi-mot (« …-noît » pour Saint-Benoît, qui cassait aussi l'en-tête
    # Content-Disposition en octets non-ASCII). Repli « annonce » si l'URL ne porte aucun identifiant.
    import re as _re
    _ids = _re.findall(r"\d{6,}", a.get("url") or "")
    numero = numeros.numero_rapport("analyse-annonce", _ids[-1] if _ids else "annonce", j)
    # « relevée le … » = la date de relevé portée par le rapport (capture Radar, ou jour du fetch).
    releve = a.get("releve_le")
    # miroir de l'écran : « 2026-10-27 » → « 27/10/2026 » (split('-').reverse().join('/')).
    releve_fr = "/".join(reversed(releve.split("-"))) if isinstance(releve, str) and "-" in releve else None
    emis = (f'<p class="emis">Annonce Leboncoin'
            + (f' · relevée le {esc(releve_fr)}' if releve_fr else "") + "</p>")
    cart = _cart("analyse-annonce", titre, commune or "annonce", numero, j)
    corps = (_entete_doc("analyse-annonce", titre, numero, j) + emis
             + bloc_annonce.rendu_commune(a, marche, contexte))
    html = page_html(_LABEL["analyse-annonce"][0], cart, corps)
    return ResultatDoc(html=html, valeurs={}, numero=numero, cartouche=cart,
                       contexte={"annonce": a})


def generer_pdf(db, idu: str, document: str = "dossier", *, fiche: dict | None = None,
                jour: date | None = None, chemin_pdf=None, compte_id: int | None = None):
    """Rend le PDF d'un document et, si `chemin_pdf` est donné, écrit le PDF + son archive JSON
    (reproductibilité — lot 1.6). Rend (bytes_pdf, ResultatDoc)."""
    res = construire(db, idu, document, fiche=fiche, jour=jour, compte_id=compte_id)
    pdf = render_pdf(res.html, forms=(document == "apporteur"))
    if chemin_pdf is not None:
        from pathlib import Path
        Path(chemin_pdf).write_bytes(pdf)
        j = (jour or today_reunion()).isoformat()
        archive.ecrire_archive(chemin_pdf, archive.payload_archive(
            document, idu, res.numero, res.valeurs, genere_le=j))
    return pdf, res
