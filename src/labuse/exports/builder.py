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
    "financier": ("Dossier financier", ""),   # RECETTE-5 (V17) — ex « Bilan de l'opération »
    "apporteur": ("Brief apporteur", ""),
}


def titre_document(document: str) -> str:
    """RECETTE-5 (V17) — le titre humain d'un document (page de garde) — point unique, réutilisé
    pour le nom de fichier téléchargé (« Dossier financier — FI-….pdf »)."""
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
    prefill = qf.prefill(fiche)
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
    except Exception:  # noqa: BLE001 — colonne/table absente (base de test) : émetteur non servi
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
        # EXPORTS-FIX-1 F3 — le plan se CALE sur la parcelle : zoom auto (plus de « −1 » qui la
        # rétrécissait) et plafond relevé à 19 (max ortho IGN) pour qu'une petite parcelle (479 m²)
        # ne reste pas un point. Même appel pour le Dossier (§1) et l'Apporteur.
        res = plan_ortho(gj, cache_dir=storage_dir() / "tiles", extra_geojson=extra,
                         zoom_delta=0, zoom_max=19)
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
    _aleas = (fiche.get("aleas") or {}).get("liste") or []
    obs_eau = (_releve("ravine") or _releve("zone_humide") or _releve("tri_zone") or _releve("dpf")
               or any(isinstance(a, dict) and any(k in (a.get("nature") or a.get("libelle") or "").lower()
                      for k in ("inond", "submers", "ravine", "humide")) for a in _aleas))
    obs_pollution = industriel or _releve("sol_pollue") or _releve("casias")
    return {
        "idu": idu, "adresse": fiche.get("adresse") or "", "emetteur": _emetteur(db, compte_id),
        "emission": f"{jour:%d/%m/%Y}", "validite": f"{jour + timedelta(days=90):%d/%m/%Y}",
        "is_bati": bool(lb.get("nb_batiments") or lb.get("emprise_batie_m2")),
        "is_pm": isinstance(pm, dict) and bool(pm),
        "industriel_proche": industriel,
        # §6 — questions d'observation conditionnelles (imprimées si la couche touche). La ligne
        # HTA/HTB (< 50 m) n'a pas de couche fiable dans le socle → question omise tant qu'elle manque.
        "obs_eau": obs_eau, "obs_pollution": obs_pollution, "obs_ligne_ht": False,
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
    j = jour or date.today()
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
        au = f.get("donnees_labuse_au") or f"{j:%d/%m/%Y}"
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
    return ResultatDoc(html=html, valeurs=valeurs, numero=numero, cartouche=cart,
                       contexte={**(ctx or {}), "adresse": adresse})


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
