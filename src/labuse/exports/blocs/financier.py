"""Bloc « Financier » (document « Financier », gabarit maquette-financier.html corrigé par la
RELECTURE). Consomme le questionnaire (résolu) + le moteur de bilan HT. Verdict en tête, hypothèses
du porteur en ambre, programme, bilan à rebours HT (chaque poste HT/TTC + nature, « non chiffré »
si vide), sensibilité double 3×3, charge foncière 3 bornes, face au prix demandé, calendrier,
marché en regard, « ce que ce document n'établit pas ». Un poste non chiffré → mention « maximum »."""
from __future__ import annotations

from ..lignes import val
from ..nature import CLASSE, LIBELLE
from ..registre_fmt import fmt_eur, fmt_eur_m2, fmt_pct, groupe
from ..rendu import aside, chip_span, esc, ligne_kv, note, section, table_kv, tuiles, verdict

# ids fiche lus (programme + marché) — pour la collecte, le pied et l'archive.
IDS = ("surface_vendable_m2", "surface_plancher_m2", "capacite_logements", "surface_parcelle_m2",
       "prix_sortie_bati_eur_m2", "prix_terrain_secteur_eur_m2", "mixite_clause",
       # EXPORTS-REBRANCHEMENT-2 lot 2 — le prix d'achat historique (DVF) entre au §6 « Face au prix
       # demandé » À TITRE D'INFORMATION, hors calcul (maquette v4).
       "prix_achat_historique_eur")

_POSTE_LABEL = {
    "construction": "Coût de construction", "honoraires_techniques": "Honoraires techniques",
    "vrd": "VRD et viabilisation", "stationnement": "Stationnement", "demolition": "Démolition",
    "depollution": "Dépollution et étude de sol", "aleas": "Aléas",
    "taxe_amenagement": "Taxe d'aménagement",
    "redevance_archeologie": "Redevance d'archéologie préventive (0,40 %)",
    "portage": "Portage financier", "frais_acquisition": "Frais d'acquisition",
}
_POSTE_ORDRE = ("construction", "honoraires_techniques", "vrd", "stationnement", "demolition",
                "depollution", "aleas", "taxe_amenagement", "redevance_archeologie", "portage",
                "frais_acquisition")
_REGIME_LABEL = {"assujetti_recuperation": "assujetti avec récupération de la TVA",
                 "tva_marge": "TVA sur marge", "autre": "autre régime"}
#: hypothèses clés montrées dans l'encart « hypothèses du porteur » (id questionnaire → libellé).
#: RECETTE-10 T2b (recette) — « Scénario » RETIRÉ : le bilan chiffre toujours une reconstruction (W3),
#: la ligne n'apportait rien et perpétuait un champ retiré de la saisie. Plus imprimée au document.
#: RECETTE-11 B3 — l'encart liste TOUS les champs qui entrent dans le bilan, y compris ceux repliés
#: sous « Affiner » (rien de caché : ce que le porteur a pu toucher est imprimé, sourcé ou projet).
_HYP_CLES = (("prix_sortie_saisi_eur_m2", "Prix de vente prévu"),
             ("prix_vente_bailleur_saisi_eur_m2", "Prix de vente au bailleur social"),
             ("part_sociale_saisi_pct", "Part de logement social"),
             ("regime_tva_saisi", "Régime de TVA"),
             ("logements_vises_saisi", "Nombre de logements visés"),
             ("typologie_moyenne_saisi", "Typologie moyenne"),
             ("cout_construction_saisi_eur_m2", "Coût de construction"),
             ("honoraires_techniques_saisi_pct", "Honoraires techniques"),
             ("vrd_saisi_eur_m2", "VRD et raccordements"),
             ("cout_place_stationnement_saisi_eur", "Coût par place de stationnement"),
             ("aleas_saisi_pct", "Provision pour aléas"),
             ("taxe_amenagement_saisi_eur", "Taxe d'aménagement"),
             ("marge_visee_saisi_pct", "Marge visée"),
             ("frais_acquisition_saisi_pct", "Frais d'acquisition"),
             ("prix_demande_saisi_eur", "Prix demandé pour le terrain"),
             ("bilan_demolition_eur", "Coût de démolition"),
             ("bilan_depollution_eur", "Dépollution / étude de sol"),
             ("duree_portage_saisi_mois", "Durée de portage"),
             ("taux_apport_saisi_pct", "Taux d'emprunt"))
#: RECETTE-6 (E3) — l'UNITÉ de chaque hypothèse : « 700000 »/« 9 » sans unité était illisible. On formate
#: en € / €/m² / % / mois (mêmes formateurs que le reste du document — un seul format monétaire, cf. E3).
_HYP_UNITE = {"prix_demande_saisi_eur": "eur", "cout_construction_saisi_eur_m2": "eur_m2",
              "marge_visee_saisi_pct": "pct", "prix_sortie_saisi_eur_m2": "eur_m2",
              "bilan_demolition_eur": "eur", "prix_vente_bailleur_saisi_eur_m2": "eur_m2",
              "part_sociale_saisi_pct": "pct", "honoraires_techniques_saisi_pct": "pct",
              "vrd_saisi_eur_m2": "eur_m2", "cout_place_stationnement_saisi_eur": "eur",
              "aleas_saisi_pct": "pct", "taxe_amenagement_saisi_eur": "eur",
              "frais_acquisition_saisi_pct": "pct", "bilan_depollution_eur": "eur",
              "duree_portage_saisi_mois": "mois", "taux_apport_saisi_pct": "pct"}


def _fmt_hyp(fid: str, valeur) -> str:
    """RECETTE-6 (E3) — une hypothèse formatée AVEC son unité (jamais un nombre nu)."""
    # RECETTE-8 W18 — le scénario est CITÉ par son libellé humain, jamais par l'identifiant
    # technique (« surelevation » sans accent ni majuscule s'imprimait au client). Point unique.
    if fid == "scenario_saisi":
        from ...scenarios import libelle_scenario
        return esc(libelle_scenario(valeur) or str(valeur))
    if fid == "regime_tva_saisi":   # RECETTE-11 B3 — libellé humain, jamais la clé technique
        return esc(_REGIME_LABEL.get(valeur, str(valeur)))
    u = _HYP_UNITE.get(fid)
    try:
        if u == "eur":
            return fmt_eur(valeur)
        if u == "eur_m2":
            return fmt_eur_m2(valeur)
        if u == "pct":
            fv = float(valeur)
            return f"{groupe(round(fv)) if fv == int(fv) else groupe(fv)} %"
        if u == "mois":
            return f"{groupe(round(float(valeur)))} mois"
    except (TypeError, ValueError):
        pass
    return esc(str(valeur))

_NON_CHIFFRE = '<span class="none">non chiffré</span>'


def _keur(v) -> str:
    # RECETTE-6 (E3) — jamais un « 0 k€ » trompeur pour un montant non nul mais sous le millier
    # (ex. Redevance d'archéologie ~0,68 €/m²) : on écrit « < 1 k€ », un montant honnête, jamais un zéro.
    if v is None:
        return _NON_CHIFFRE
    k = round(v / 1000)
    if k == 0 and abs(v) >= 1:
        return "< 1 k€"
    return f"{groupe(k)} k€"


def _chip_nat(nat: str) -> str:
    return chip_span(CLASSE.get(nat, "e"), LIBELLE.get(nat, "estimé"))


def _ce_qui_nest_pas_etabli() -> str:
    """RECETTE-6 (E2/E3) — le rappel « Ce que ce document n'établit pas » (point unique, réutilisé par
    le chemin normal ET le chemin hors-marché)."""
    return ("<h3>Ce que ce document n'établit pas</h3>"
            + table_kv([ligne_kv("Plan de financement, apport, taux", "Établissement prêteur", ""),
                        ligne_kv("Valeur vénale", "Avis de valeur — notaire, expert", ""),
                        ligne_kv("Coûts de démolition et de dépollution réels", "Devis d'entreprise", ""),
                        ligne_kv("Constructibilité définitive", "Certificat d'urbanisme", "")]))


def _verdict(bilan: dict, prix_demande, regime_label: str) -> str:
    charge = bilan["charge"]["centrale"]
    # RECETTE-6 (E3) — « Régime retenu » n'apparaît plus ICI : il était imprimé trois fois (verdict +
    # encart ambre + …). Une seule mention désormais, dans l'encart ambre (aside) plus bas.
    petit = ""
    if bilan["maximum"]:
        petit += "Bilan en maximum : des postes ne sont pas chiffrés — ils ne peuvent que réduire ce résultat."
    if charge is None:
        return verdict("Le bilan ne peut pas être établi ici : le programme (surface vendable) ou "
                       "le prix de sortie manquent. Renseignez le questionnaire.", "neutral", petit)
    # RECETTE-10 T4 — une charge foncière NÉGATIVE ne se dit pas en euros négatifs (« supporte au mieux
    # -141 788 € » ne veut rien dire). On dit ce qu'elle signifie : l'opération ne peut porter AUCUN
    # achat de terrain, et il lui manque {|charge|} pour seulement atteindre l'équilibre à terrain nul.
    if charge < 0:
        manque = -charge
        tete = ("Dans ces hypothèses, l'opération ne peut supporter <strong>aucun achat de terrain</strong> : "
                f"il lui manque {fmt_eur(manque)} pour seulement atteindre l'équilibre à un prix de "
                "terrain nul.")
        if prix_demande is not None:
            tete = f"Au prix demandé de {fmt_eur(prix_demande)}, l'opération ne tient pas. " + tete
        return verdict(tete, "warn", petit)
    if prix_demande is not None:
        if charge >= prix_demande:
            return verdict(f"Au prix demandé de {fmt_eur(prix_demande)}, l'opération tient : elle "
                           f"supporte {fmt_eur(charge)} de charge foncière.", "", petit)
        return verdict(f"Au prix demandé de {fmt_eur(prix_demande)}, cette opération ne tient pas : "
                       f"elle supporte au mieux {fmt_eur(charge)} de charge foncière.", "warn", petit)
    return verdict(f"Cette opération supporte au mieux {fmt_eur(charge)} de charge foncière "
                   f"(bilan à rebours).", "neutral", petit)


def _hypotheses(resolved: dict) -> str:
    lignes = []
    for fid, lib in _HYP_CLES:
        r = resolved.get(fid) or {}
        o = r.get("origine")
        if o == "saisi":
            lignes.append(ligne_kv(lib, _fmt_hyp(fid, r["valeur"]), chip_span("p", "projet")))
        elif o == "prefill":
            # RECETTE-6 (E3) unité formatée · (E4) un pré-remplissage PORTE SA SOURCE → « sourcé »,
            # pas « estimé » (tant que le porteur ne l'a pas modifié).
            src = f' <span class="note" style="display:inline">— {esc(r.get("source", ""))}</span>'
            lignes.append(ligne_kv(lib, _fmt_hyp(fid, r["valeur"]) + src, chip_span("s", "sourcé")))
        else:
            lignes.append(ligne_kv(lib, _NON_CHIFFRE, ""))
    return ('<div class="projet keep"><div class="t">Hypothèses du porteur</div>'
            + table_kv(lignes) + '</div>')


def _programme(prog: dict, valeurs) -> str:
    lignes = []
    if prog.get("surface_plancher"):
        lignes.append(ligne_kv("Surface de plancher", esc(f"~{groupe(round(prog['surface_plancher']))} m²"), chip_span("e", "estimé")))
    if prog.get("surface_vendable"):
        lignes.append(ligne_kv("Surface habitable vendable", esc(f"~{groupe(round(prog['surface_vendable']))} m²"), chip_span("e", "estimé")))
    if prog.get("logements"):
        lignes.append(ligne_kv("Logements", esc(str(prog["logements"])), chip_span("e", "estimé")))
    mx = val(valeurs, "mixite_clause")
    if mx:
        lignes.append(ligne_kv("Mixité sociale", esc(str(mx)), chip_span("s", "sourcé")))
    return ("<h2>Le programme</h2>" + table_kv(lignes)) if lignes else ""


def _bilan_rebours(bilan: dict, resolved: dict | None = None) -> str:
    resolved = resolved or {}
    lignes = ['<tr><th>Poste</th><th style="text-align:right">Montant</th><th></th></tr>']
    ca = bilan["ca_ht"]
    # RECETTE-6 (E4) — le CA HT DÉRIVE d'une saisie du porteur (prix de sortie × surface) : « dérivé »,
    # pas « estimé » (qui laisserait croire à un calcul LABUSE autonome).
    lignes.append(ligne_kv("Chiffre d'affaires HT", f'<span class="num">{_keur(ca)}</span>', _chip_nat("derive")))
    # RECETTE-10 T3 — la nature imprimée EST celle du MONTANT (ce que la ligne affiche), pas celle de
    # son entrée. Le coût de construction est un produit (plancher × €/m²) → toujours ƒ DÉRIVÉ, même
    # quand le €/m² est un pré-remplissage sourcé (le taux est sourcé, le montant ne l'est pas ; le
    # taux sourcé apparaît dans l'encart « Hypothèses du porteur »). L'ancien code (E4) rendait le
    # MONTANT « sourcé » dès que le taux l'était → le -717 k€ / -14 k€ portait une pastille sourcé
    # mensongère. Seule exception : la taxe d'aménagement SAISIE au forfait par le porteur → `projet`.
    _POSTE_PROJET_SI_SAISI = {"taxe_amenagement": "taxe_amenagement_saisi_eur"}
    for k in _POSTE_ORDRE:
        p = bilan["postes"][k]
        # RECETTE-6 (E3) — un poste NUL non nul (ex. Redevance d'archéologie) s'écrit « < 1 k€ » via _keur,
        # jamais « 0 k€ » ; un poste None reste « non chiffré ».
        montant = None if p["montant"] is None else -p["montant"]
        nat = p["nature"]
        fid = _POSTE_PROJET_SI_SAISI.get(k)
        if fid and (resolved.get(fid) or {}).get("origine") == "saisi":
            nat = "projet"      # le porteur a saisi ce montant forfaitaire lui-même
        v = f'<span class="num">{_keur(montant)}</span>' + (f' <span class="note" style="display:inline">{p["ht_ttc"]}</span>')
        lignes.append(ligne_kv(_POSTE_LABEL[k], v, _chip_nat(nat)))
    # RECETTE-6 (E3) — la TAXE FONCIÈRE DE PORTAGE, expliquée en fin de document, entre au bilan comme
    # poste « non chiffré » (comme le stationnement) : LABUSE n'invente pas la valeur locative cadastrale.
    lignes.append(ligne_kv("Taxe foncière (portage)", f'<span class="num">{_NON_CHIFFRE}</span>', _chip_nat("derive")))
    if bilan["marge"] is not None:
        # RECETTE-10 T3 — le MONTANT de marge est un produit (marge % × CA HT) → ƒ dérivé. Le TAUX
        # visé (projet) est montré dans l'encart « Hypothèses du porteur », pas ici sur le montant.
        lignes.append(ligne_kv("Marge visée", f'<span class="num">{_keur(-bilan["marge"])}</span>', _chip_nat("derive")))
    charge = bilan["charge"]["centrale"]
    # RECETTE-5 (V18a) — la clé est ÉCHAPPÉE par ligne_kv (esc) : y mettre « <strong>…</strong> »
    # imprimait les balises en toutes lettres. La ligne est déjà mise en avant par le montant en gras
    # (valeur, HTML non échappé) ; la clé redevient du texte simple.
    lignes.append(ligne_kv("Charge foncière supportable",
                  f'<span class="num"><strong>{_keur(charge)}</strong></span>', _chip_nat("derive")))
    return "<h2>Le bilan à rebours (HT)</h2>" + table_kv(lignes)


def _sensibilite(bilan: dict) -> str:
    grille = bilan["sensibilite"]
    if not grille or all(c["charge"] is None for row in grille for c in row):
        return ""
    entete = '<tr><th>Coût \\ Prix de sortie</th><th>bas</th><th>retenu</th><th>haut</th></tr>'
    lignes = [entete]
    for row in grille:
        cells = "".join(f'<td class="num">{_keur(c["charge"])}</td>' for c in row)
        lignes.append(f'<tr><td class="k">{row[0]["cout"]}</td>{cells}</tr>')
    return ("<h3>Sensibilité double — charge foncière selon coût et prix de sortie</h3>"
            + f'<table class="kv">{"".join(lignes)}</table>'
            + note("Coût de construction en lignes (bas/retenu/haut de la fourchette EPTB), prix de "
                   "sortie en colonnes (±5 %). La charge foncière varie sur les deux axes."))


def _face_prix(bilan: dict, prix_demande, valeurs) -> str:
    lignes = []
    if prix_demande is not None:
        lignes.append(ligne_kv("Prix demandé", f'<span class="num">{fmt_eur(prix_demande)}</span>', chip_span("p", "projet")))
    charge = bilan["charge"]["centrale"]
    if charge is not None:
        # RECETTE-10 T3 — la charge foncière supportable est déduite (CA − Σ postes − marge) → ƒ dérivé,
        # jamais « estimé » (elle n'est pas un moteur de calcul LABUSE mais une soustraction affichée).
        # T4 — négative : dite en clair, jamais un euro négatif.
        if charge < 0:
            v_ch = esc(f"aucune — manque {fmt_eur(-charge)} pour l'équilibre à terrain nul")
        else:
            v_ch = f'<span class="num">{fmt_eur(charge)}</span>'
        lignes.append(ligne_kv("Ce que l'opération supporte", v_ch, _chip_nat("derive")))
    if bilan["ecart_prix_demande"] is not None:
        lignes.append(ligne_kv("Écart", f'<span class="num"><strong>{fmt_eur(bilan["ecart_prix_demande"])}</strong></span>', _chip_nat("derive")))
    if bilan["marge_residuelle_pct"] is not None:
        # RECETTE-10 T4 — une marge résiduelle négative se dit en clair (perte), pas en « -X % » sec.
        mr = bilan["marge_residuelle_pct"]
        if mr < 0:
            v_mr = esc(f"négative ({groupe(mr, 1)} %) — au prix demandé, l'opération perd de l'argent")
        else:
            v_mr = esc(f"{groupe(mr, 1)} % du chiffre d'affaires")
        lignes.append(ligne_kv("Marge résiduelle au prix demandé", v_mr, _chip_nat("derive")))
    if bilan["seuil_rentabilite"] is not None:
        # RECETTE-10 T4 — un seuil de rentabilité négatif = aucun prix d'achat ne dégage la marge visée
        # (il faudrait un terrain « payé » à l'opération). On le dit, on ne montre pas un euro négatif.
        sr = bilan["seuil_rentabilite"]
        if sr < 0:
            v_sr = esc(f"aucun prix d'achat viable — il manque {fmt_eur(-sr)} même à un terrain nul")
        else:
            v_sr = f'<span class="num">{fmt_eur(sr)}</span>'
        lignes.append(ligne_kv("Seuil de rentabilité (prix d'achat)", v_sr, _chip_nat("derive")))
    if bilan["prix_revient"] is not None:
        lignes.append(ligne_kv("Prix de revient", esc(f"{groupe(round(bilan['prix_revient']))} €/m² vendable"), _chip_nat("derive")))
    tn = val(valeurs, "prix_terrain_secteur_eur_m2")
    if isinstance(tn, dict) and tn.get("valeur_eur"):
        lignes.append(ligne_kv("Terrain nu au prix du marché", f'<span class="num">{fmt_eur(tn["valeur_eur"])}</span>', chip_span("d", "dérivé")))
    # EXPORTS-REBRANCHEMENT-2 lot 2 — le prix d'achat HISTORIQUE de la parcelle (DVF, dernière
    # mutation) : information de contexte, HORS calcul (il n'entre dans aucun poste). Absent si la
    # parcelle n'a jamais muté seule (fréquent). Sourcé (DVF).
    ph = val(valeurs, "prix_achat_historique_eur")
    if isinstance(ph, dict) and ph.get("valeur"):
        quand = (ph.get("date_mutation") or "")[:4]
        lib = fmt_eur(ph["valeur"]) + (f" (dernière mutation {quand})" if quand else " (dernière mutation)")
        lignes.append(ligne_kv("Prix d'achat historique — information, hors calcul",
                               f'<span class="num">{esc(lib)}</span>', chip_span("s", "sourcé")))
    return ("<h2>Face au prix demandé</h2>" + table_kv(lignes)) if lignes else ""


def _pct(v) -> str:
    return _NON_CHIFFRE if v is None else f"{groupe(v, 2)} %"


def _fiscalite_locale(tfpb: dict | None, zonage: dict | None, resolved: dict) -> str:
    """RECETTE-4 U1/U2 — la fiscalité locale de la commune au Financier : le taux de taxe foncière
    (REI DGFiP, sourcé + daté) qui pèse sur le portage, et la zone A/B/C (DHUP) qui commande le
    régime applicable. Aucun euro n'est chiffré ici sans base : la taxe foncière de portage se
    calcule sur la valeur locative cadastrale du bien — on DIT le taux et ce qu'il manque, on
    n'invente jamais une valeur locative (doctrine « dite et sourcée, jamais devinée en silence »)."""
    if not tfpb and not zonage:
        return ""
    lignes = []
    if tfpb:
        lignes.append(ligne_kv("Taxe foncière (TFPB) — part communale",
                               f'<span class="num">{_pct(tfpb.get("tfpb_commune_pct"))}</span>',
                               chip_span("s", "sourcé")))
        if tfpb.get("tfpb_epci_pct") is not None:
            lignes.append(ligne_kv("Part intercommunale (EPCI)",
                                   f'<span class="num">{_pct(tfpb.get("tfpb_epci_pct"))}</span>',
                                   chip_span("s", "sourcé")))
        if tfpb.get("teom_pct") is not None:
            lignes.append(ligne_kv("Ordures ménagères (TEOM, taux plein)",
                                   f'<span class="num">{_pct(tfpb.get("teom_pct"))}</span>',
                                   chip_span("s", "sourcé")))
    if zonage:
        # RECETTE-9 T4 — la clé dit déjà « Zone … » : la valeur porte le seul code ABC (« B2 »),
        # plus de « zone B2 » redondant (même famille que le doublon « Zone Zone Um » de l'Apporteur).
        lignes.append(ligne_kv("Zone d'investissement (A/B/C)",
                               esc(str(zonage.get("zone"))), chip_span("s", "sourcé")))
    corps = "<h2>Fiscalité locale et régime applicable</h2>" + table_kv(lignes)
    # la taxe foncière de portage : dite, jamais chiffrée sans la valeur locative cadastrale.
    r = resolved.get("duree_portage_saisi_mois") or {}
    duree = r.get("valeur")
    if tfpb and tfpb.get("tfpb_commune_pct") is not None:
        combien = f"les {int(duree)} mois de portage" if duree not in (None, "") else "la durée de portage"
        corps += note(
            f"Pendant {combien}, le porteur acquitte la taxe foncière sur le bien. Elle se calcule "
            f"sur la valeur locative cadastrale du bien × le taux communal "
            f"({_pct(tfpb['tfpb_commune_pct'])}, part départementale et TEOM en sus). LABUSE n'invente "
            "pas de valeur locative : reportez-la de l'avis de taxe foncière du bien pour la chiffrer.")
    if zonage:
        corps += note(
            f"Zone {zonage.get('zone')} (DHUP) : elle fixe l'éligibilité au PTZ dans le neuf, les "
            "plafonds de loyer et de ressources des dispositifs, et le prix de vente au bailleur "
            "social. À La Réunion, la TVA du logement neuf est de 8,5 % (2,1 % en locatif social).")
    # EXPORTS-REBRANCHEMENT-1 lot 2 — noms de sources seuls, aucun millésime côté client.
    src = []
    if tfpb:
        src.append("DGFiP — fichier REI")
    if zonage:
        src.append("DHUP — zonage A/B/C")
    if src:
        corps += note("Sources : " + " · ".join(src) + ".")
    return corps


def _calendrier(resolved: dict) -> str:
    r = resolved.get("duree_portage_saisi_mois") or {}
    if r.get("valeur") in (None, ""):
        return ""
    duree = int(r["valeur"])
    etudes, chantier = 9, max(1, duree - 9)
    return ("<h3>Calendrier sommaire</h3>"
            + note(f"Acquisition → études et instruction (~{etudes} mois) → chantier (~{chantier} "
                   f"mois) → livraison. Durée de portage retenue : {duree} mois."))


#: RECETTE-8 W13bis (C3) — les postes du calcul de revente, dans l'ordre du raisonnement.
_REVENTE_POSTES = (("prix_achat", "Prix d'achat"), ("frais_acquisition", "Frais d'acquisition"),
                   ("travaux", "Travaux éventuels"), ("portage", "Coût de portage"))


def _revente(rev: dict, resolved: dict) -> str:
    """RECETTE-8 W13bis (C3) — le rendu du parcours « Revente en l'état » : marge et taux de marge
    en tête, puis les postes du calcul (achat → frais → travaux → portage → revente). Aucun bilan à
    rebours. Sous garde de vraisemblance simple : marge NÉGATIVE → verdict prudent (« perte »)."""
    postes = rev.get("postes") or {}
    marge, taux = rev.get("marge"), rev.get("taux_marge_pct")
    maxi = rev.get("maximum")
    signe = "" if (marge is None or marge < 0) else "+"
    tete = (f"Marge estimée <strong>{signe}{fmt_eur(marge)}</strong>"
            + (f" — taux de marge {fmt_pct(taux)}" if taux is not None else "")
            + (". Coût de portage non chiffré : marge <strong>maximum</strong>." if maxi else "."))
    ton = "warn" if (marge is not None and marge < 0) else ""
    corps = verdict(tete, ton, "")
    lignes = []
    for k, lib in _REVENTE_POSTES:
        v = postes.get(k)
        lignes.append(ligne_kv(lib, fmt_eur(v) if v is not None else '<span class="none">non chiffré</span>',
                               chip_span("p", "projet")))
    lignes.append(ligne_kv("Coût total de revient", fmt_eur(rev.get("cout_total")), chip_span("d", "dérivé")))
    lignes.append(ligne_kv("Prix de revente visé", fmt_eur(postes.get("prix_revente")), chip_span("p", "projet")))
    corps += table_kv(lignes)
    corps += note("Calcul simple de marge (revente en l'état) : marge = prix de revente − prix "
                  "d'achat − frais d'acquisition − travaux − coût de portage. Aucun bilan à rebours, "
                  "aucune construction. Les montants en bleu sont vos saisies (projet).")
    return corps


def rendu(valeurs, ctx=None) -> str:
    ctx = ctx or {}
    # RECETTE-8 W13bis (C3) — parcours « Revente en l'état » : rendu dédié, jamais le bilan à rebours.
    if ctx.get("usage") == "revente":
        rev = ctx.get("revente") or {}
        from ..lignes import pied
        if not rev.get("etablissable"):
            corps = verdict("La marge de revente n'est pas établie : renseignez le prix d'achat et le "
                            "prix de revente visé.", "warn", "")
            return section("Bilan de l'opération — revente en l'état", corps) + pied(valeurs, IDS)
        return section("Bilan de l'opération — revente en l'état",
                       _revente(rev, ctx.get("resolved") or {})) + pied(valeurs, IDS)
    bilan, resolved, prog = ctx.get("bilan") or {}, ctx.get("resolved") or {}, ctx.get("program") or {}
    if not ctx.get("existe"):
        # aucun questionnaire → l'encart de renvoi (le document sort quand même, en « maximum »)
        pass
    pd = (resolved.get("prix_demande_saisi_eur") or {}).get("valeur")
    regime = (resolved.get("regime_tva_saisi") or {}).get("valeur")
    regime_label = _REGIME_LABEL.get(regime, "à préciser au questionnaire")
    # RECETTE-6 (E2, BLOQUANT) — HYPOTHÈSE HORS MARCHÉ : le document ne publie AUCUN verdict de charge
    # foncière ; il dit que l'hypothèse est hors marché, NOMME le champ, montre les hypothèses saisies et
    # renvoie à la correction. Jamais un bilan absurde imprimé sur le ton de l'évidence (« l'opération tient »).
    hm = bilan.get("hors_marche") if isinstance(bilan, dict) else None
    if hm:
        # RECETTE-10 T5 — le conseil de correction dépend du garde qui a mordu (prix total vs prix
        # bailleur > libre) : chaque garde porte sa propre phrase `correction`.
        correction = hm.get("correction", "Corrigez ce champ (un prix AU M², pas un prix total), "
                                          "puis régénérez le document.")
        corps = verdict(
            f"Hypothèse hors marché — le bilan n'est pas établi. Le champ « {esc(hm['champ'])} » vaut "
            f"{fmt_eur_m2(hm['valeur'])} : {esc(hm['raison'])} {esc(correction)}", "warn", "")
        corps += _hypotheses(resolved)
        corps += _ce_qui_nest_pas_etabli()
        from ..lignes import pied
        return section("Bilan de l'opération", corps) + pied(valeurs, IDS)
    corps = _verdict(bilan, pd, regime_label)
    cc = bilan.get("charge", {}).get("centrale")
    if cc is not None:
        # RECETTE-10 T4 — charge centrale négative : la tuile hero ne montre pas « -142 k€ » (illisible)
        # mais « aucune » + le déficit à terrain nul.
        tuile_charge = ((f"aucune", f"charge foncière — manque {_keur(-cc)} à terrain nul") if cc < 0
                        else (_keur(cc), "charge foncière supportable"))
        corps += tuiles([tuile_charge,
                         (f'{_keur(bilan["charge"]["basse"])} → {_keur(bilan["charge"]["haute"])}',
                          "plancher et plafond (coût × prix de sortie)"),
                         (_keur(bilan["ecart_prix_demande"]) if bilan.get("ecart_prix_demande") is not None else "—",
                          "écart au prix demandé")])
    corps += _hypotheses(resolved)
    corps += aside(f"<strong>Régime de TVA retenu : {esc(regime_label)}.</strong> "
                   "Le bilan travaille HT (prix de sortie ramené HT au taux du régime). À confirmer "
                   "avec votre expert-comptable.", "")
    corps += _programme(prog, valeurs)
    corps += _bilan_rebours(bilan, resolved)
    corps += _sensibilite(bilan)
    corps += _face_prix(bilan, pd, valeurs)
    corps += _fiscalite_locale(ctx.get("tfpb"), ctx.get("zonage_abc"), resolved)
    corps += _calendrier(resolved)
    corps += _ce_qui_nest_pas_etabli()
    corps += note("Bilan indicatif : données publiques (cadastre, DVF, Sitadel, PLU) et hypothèses "
                  "saisies par le porteur. Il ne remplace ni un bilan promoteur professionnel, ni une "
                  "étude de faisabilité, ni une expertise.")
    from ..lignes import pied
    return section("Bilan de l'opération", corps) + pied(valeurs, IDS)
