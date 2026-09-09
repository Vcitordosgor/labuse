"""Bloc « 8. Contexte communal ». Dispositifs fiscaux (ZFANG, FRR, zonage A/B/C, bande QPV),
parc social, taxe d'aménagement (taux communal « non renseigné » dit honnêtement, jamais un ◌),
fraîcheur du PLU."""
from __future__ import annotations

from ..lignes import a, pied, val
from ..nature import chip
from ..registre_fmt import fmt_pct, groupe
from ..rendu import chip_span, esc, ligne_kv, section, table_kv

IDS = ("perimetres_dispositifs_liste", "parc_social_rpls_logements",
       "taxe_amenagement_estimee_eur", "statut_plu")


def _taxe(t: dict) -> str:
    # RECETTE-8 W2 — la taxe d'aménagement se paie sur la surface de plancher CRÉÉE par un projet
    # (art. L331 c. urb.). Le Dossier est un document AVANT projet : aucun n'est saisi, LABUSE ne
    # connaît donc pas cette surface et ne l'invente pas. On ne dit QUE sur quoi elle se calculera
    # et le taux communal — jamais un montant en euros sur un scénario que personne n'a choisi
    # (avant : « De l'ordre de 22 469 € … pour 458 m² de table rase »). Le montant chiffré est au
    # Financier, sur la SDP du projet réellement saisi.
    # RECETTE-9 T2 — le Dossier DIT EN UNE LIGNE comment obtenir le montant (jamais un trou) : il
    # renvoie au Financier ET nomme les entrées à décrire, y compris sur une parcelle SANS potentiel
    # constructible calculé (où le Financier ne s'établissait pas — cul-de-sac de T2, désormais ouvert
    # par T1 : le nombre de logements visés + la typologie y suffisent). Aucun chiffre inventé.
    base = ("Se calcule sur la surface de plancher créée par le projet (taxe due une fois un projet "
            "déposé). Pour en obtenir le montant : ouvrez le Dossier financier et décrivez le "
            "programme — le nombre de logements visés et la typologie suffisent lorsque la parcelle "
            "n'a pas de potentiel constructible calculé.")
    if t.get("taux_communal_manquant"):
        return f"{base} Taux communal non renseigné pour cette commune."
    # RECETTE-7 (E9) — le taux à la française (« 3,0 % », pas « 3.0 % »).
    taux = fmt_pct(t["taux_communal_pct"]) if t.get("taux_communal_pct") else None
    mil = t.get("taux_communal_millesime")
    src = f" — {mil}" if (t.get("taux_communal_source") == "public" and mil) else ""
    return f"Taux communal {taux}{src}. {base}" if taux else base


def rendu(valeurs) -> str:
    lignes = []
    fisc = val(valeurs, "perimetres_dispositifs_liste") or {}
    if isinstance(fisc, dict):
        dom = (fisc.get("dispositifs_dom") or [{}])[0]
        if dom.get("libelle"):
            lignes.append(ligne_kv("Zonage du logement", esc(dom["libelle"]), chip(valeurs["perimetres_dispositifs_liste"])))
        if (fisc.get("zfang") or {}).get("libelle"):
            lignes.append(ligne_kv("ZFANG", esc(fisc["zfang"]["libelle"]), chip_span("s", "sourcé")))
        if (fisc.get("frr") or {}).get("libelle"):
            lignes.append(ligne_kv("FRR (ex-ZRR)", esc(fisc["frr"]["libelle"]), chip_span("s", "sourcé")))
        per = (fisc.get("perimetres") or [{}])[0]
        if per.get("libelle"):
            lignes.append(ligne_kv("Périmètre fiscal", esc(per["libelle"]), chip_span("d", "dérivé")))
    if a(valeurs, "parc_social_rpls_logements"):
        lignes.append(ligne_kv("Parc social (commune)",
                      esc(f"{groupe(val(valeurs, 'parc_social_rpls_logements'))} logements sociaux (RPLS)"),
                      chip(valeurs["parc_social_rpls_logements"])))
    taxe = val(valeurs, "taxe_amenagement_estimee_eur")
    if isinstance(taxe, dict):
        lignes.append(ligne_kv("Taxe d'aménagement", esc(_taxe(taxe)), chip_span("e", "estimé")))
    plu = val(valeurs, "statut_plu")
    if isinstance(plu, dict) and plu.get("libelle"):
        lignes.append(ligne_kv("PLU", esc(plu["libelle"]), chip_span("s", "sourcé")))
    if not lignes:
        return ""
    commune = fisc.get("commune") if isinstance(fisc, dict) else None
    titre = f"8. Contexte communal — {commune}" if commune else "8. Contexte communal"
    return section(titre, table_kv(lignes) + pied(valeurs, IDS))
