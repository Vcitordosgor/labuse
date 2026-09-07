"""Bloc « Financier » (document « Financier », gabarit maquette-financier.html corrigé par la
RELECTURE). Consomme le questionnaire (résolu) + le moteur de bilan HT. Verdict en tête, hypothèses
du porteur en ambre, programme, bilan à rebours HT (chaque poste HT/TTC + nature, « non chiffré »
si vide), sensibilité double 3×3, charge foncière 3 bornes, face au prix demandé, calendrier,
marché en regard, « ce que ce document n'établit pas ». Un poste non chiffré → mention « maximum »."""
from __future__ import annotations

from ..lignes import val
from ..nature import CLASSE, LIBELLE
from ..registre_fmt import fmt_eur, fmt_eur_m2, groupe
from ..rendu import aside, chip_span, esc, ligne_kv, note, section, table_kv, tuiles, verdict

# ids fiche lus (programme + marché) — pour la collecte, le pied et l'archive.
IDS = ("surface_vendable_m2", "surface_plancher_m2", "capacite_logements", "surface_parcelle_m2",
       "prix_sortie_bati_eur_m2", "prix_terrain_secteur_eur_m2", "mixite_clause")

_POSTE_LABEL = {
    "construction": "Coût de construction", "honoraires_techniques": "Honoraires techniques",
    "vrd": "VRD et viabilisation", "stationnement": "Stationnement", "demolition": "Démolition",
    "depollution": "Dépollution et étude de sol", "aleas": "Aléas",
    "taxe_amenagement": "Taxe d'aménagement", "redevance_archeologie": "Redevance d'archéologie",
    "portage": "Portage financier", "frais_acquisition": "Frais d'acquisition",
}
_POSTE_ORDRE = ("construction", "honoraires_techniques", "vrd", "stationnement", "demolition",
                "depollution", "aleas", "taxe_amenagement", "redevance_archeologie", "portage",
                "frais_acquisition")
_REGIME_LABEL = {"assujetti_recuperation": "assujetti avec récupération de la TVA",
                 "tva_marge": "TVA sur marge", "autre": "autre régime"}
#: hypothèses clés montrées dans l'encart « hypothèses du porteur » (id questionnaire → libellé).
_HYP_CLES = (("scenario_saisi", "Scénario"), ("prix_demande_saisi_eur", "Prix demandé"),
             ("cout_construction_saisi_eur_m2", "Coût de construction"),
             ("marge_visee_saisi_pct", "Marge visée"), ("prix_sortie_saisi_eur_m2", "Prix de sortie"),
             ("bilan_demolition_eur", "Démolition"))

_NON_CHIFFRE = '<span class="none">non chiffré</span>'


def _keur(v) -> str:
    return _NON_CHIFFRE if v is None else f"{groupe(round(v / 1000))} k€"


def _chip_nat(nat: str) -> str:
    return chip_span(CLASSE.get(nat, "e"), LIBELLE.get(nat, "estimé"))


def _verdict(bilan: dict, prix_demande, regime_label: str) -> str:
    charge = bilan["charge"]["centrale"]
    petit = f"Régime retenu : {esc(regime_label)}." if regime_label else ""
    if bilan["maximum"]:
        petit += " Bilan en maximum : des postes ne sont pas chiffrés — ils ne peuvent que réduire ce résultat."
    if charge is None:
        return verdict("Le bilan ne peut pas être établi ici : le programme (surface vendable) ou "
                       "le prix de sortie manquent. Renseignez le questionnaire.", "neutral", petit)
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
            lignes.append(ligne_kv(lib, esc(str(r["valeur"])), chip_span("p", "projet")))
        elif o == "prefill":
            src = f' <span class="note" style="display:inline">— {esc(r.get("source", ""))}</span>'
            lignes.append(ligne_kv(lib, esc(str(r["valeur"])) + src, chip_span("e", "estimé")))
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


def _bilan_rebours(bilan: dict) -> str:
    lignes = ['<tr><th>Poste</th><th style="text-align:right">Montant</th><th></th></tr>']
    ca = bilan["ca_ht"]
    lignes.append(ligne_kv("Chiffre d'affaires HT", f'<span class="num">{_keur(ca)}</span>', _chip_nat("estime")))
    for k in _POSTE_ORDRE:
        p = bilan["postes"][k]
        montant = None if p["montant"] is None else -p["montant"]
        v = f'<span class="num">{_keur(montant)}</span>' + (f' <span class="note" style="display:inline">{p["ht_ttc"]}</span>')
        lignes.append(ligne_kv(_POSTE_LABEL[k], v, _chip_nat(p["nature"])))
    if bilan["marge"] is not None:
        lignes.append(ligne_kv("Marge visée", f'<span class="num">{_keur(-bilan["marge"])}</span>', _chip_nat("projet")))
    charge = bilan["charge"]["centrale"]
    lignes.append(ligne_kv("<strong>Charge foncière supportable</strong>",
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
        lignes.append(ligne_kv("Ce que l'opération supporte", f'<span class="num">{fmt_eur(charge)}</span>', _chip_nat("estime")))
    if bilan["ecart_prix_demande"] is not None:
        lignes.append(ligne_kv("Écart", f'<span class="num"><strong>{fmt_eur(bilan["ecart_prix_demande"])}</strong></span>', _chip_nat("derive")))
    if bilan["marge_residuelle_pct"] is not None:
        lignes.append(ligne_kv("Marge résiduelle au prix demandé", esc(f"{groupe(bilan['marge_residuelle_pct'], 1)} % du chiffre d'affaires"), _chip_nat("derive")))
    if bilan["seuil_rentabilite"] is not None:
        lignes.append(ligne_kv("Seuil de rentabilité (prix d'achat)", f'<span class="num">{fmt_eur(bilan["seuil_rentabilite"])}</span>', _chip_nat("derive")))
    if bilan["prix_revient"] is not None:
        lignes.append(ligne_kv("Prix de revient", esc(f"{groupe(round(bilan['prix_revient']))} €/m² vendable"), _chip_nat("derive")))
    tn = val(valeurs, "prix_terrain_secteur_eur_m2")
    if isinstance(tn, dict) and tn.get("valeur_eur"):
        lignes.append(ligne_kv("Terrain nu au prix du marché", f'<span class="num">{fmt_eur(tn["valeur_eur"])}</span>', chip_span("d", "dérivé")))
    return ("<h2>Face au prix demandé</h2>" + table_kv(lignes)) if lignes else ""


def _calendrier(resolved: dict) -> str:
    r = resolved.get("duree_portage_saisi_mois") or {}
    if r.get("valeur") in (None, ""):
        return ""
    duree = int(r["valeur"])
    etudes, chantier = 9, max(1, duree - 9)
    return ("<h3>Calendrier sommaire</h3>"
            + note(f"Acquisition → études et instruction (~{etudes} mois) → chantier (~{chantier} "
                   f"mois) → livraison. Durée de portage retenue : {duree} mois."))


def rendu(valeurs, ctx=None) -> str:
    ctx = ctx or {}
    bilan, resolved, prog = ctx.get("bilan") or {}, ctx.get("resolved") or {}, ctx.get("program") or {}
    if not ctx.get("existe"):
        # aucun questionnaire → l'encart de renvoi (le document sort quand même, en « maximum »)
        pass
    pd = (resolved.get("prix_demande_saisi_eur") or {}).get("valeur")
    regime = (resolved.get("regime_tva_saisi") or {}).get("valeur")
    regime_label = _REGIME_LABEL.get(regime, "à préciser au questionnaire")
    corps = _verdict(bilan, pd, regime_label)
    if bilan.get("charge", {}).get("centrale") is not None:
        corps += tuiles([(_keur(bilan["charge"]["centrale"]), "charge foncière supportable"),
                         (f'{_keur(bilan["charge"]["basse"])} → {_keur(bilan["charge"]["haute"])}',
                          "plancher et plafond (coût × prix de sortie)"),
                         (_keur(bilan["ecart_prix_demande"]) if bilan.get("ecart_prix_demande") is not None else "—",
                          "écart au prix demandé")])
    corps += _hypotheses(resolved)
    corps += aside(f"<strong>Régime de TVA retenu : {esc(regime_label)}.</strong> "
                   "Le bilan travaille HT (prix de sortie ramené HT au taux du régime). À confirmer "
                   "avec votre expert-comptable.", "")
    corps += _programme(prog, valeurs)
    corps += _bilan_rebours(bilan)
    corps += _sensibilite(bilan)
    corps += _face_prix(bilan, pd, valeurs)
    corps += _calendrier(resolved)
    corps += ("<h3>Ce que ce document n'établit pas</h3>"
              + table_kv([ligne_kv("Plan de financement, apport, taux", "Établissement prêteur", ""),
                          ligne_kv("Valeur vénale", "Avis de valeur — notaire, expert", ""),
                          ligne_kv("Coûts de démolition et de dépollution réels", "Devis d'entreprise", ""),
                          ligne_kv("Constructibilité définitive", "Certificat d'urbanisme", "")]))
    corps += note("Bilan indicatif : données publiques (cadastre, DVF, Sitadel, PLU) et hypothèses "
                  "saisies par le porteur. Il ne remplace ni un bilan promoteur professionnel, ni une "
                  "étude de faisabilité, ni une expertise.")
    from ..lignes import pied
    return section("Bilan de l'opération", corps) + pied(valeurs, IDS)
