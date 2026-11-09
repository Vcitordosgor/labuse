"""BILAN-1 Lot 5 / BILAN-2 — le PDF du Bilan.

Même couverture/en-tête/pied que les autres documents (marque LABUSE, cartouche
@page lu par le rendu). En tête : le bloc de ratios & données du programme (ordre
de l'Excel) et le calendrier prévisionnel. Puis UN seul tableau aligné — Libellé ·
Assiette · Taux · HT · TVA · TTC — avec un sous-total « TOTAL (n) » par bloc, et la
synthèse (dépenses, CA, TVA résiduelle, résultat net, marge, cash flow).

BILAN-2 : le document se génère À TOUT MOMENT (calcul en continu, case vide = 0).
Une ligne vide ne porte pas de montant (elle compte pour 0 dans les totaux) ; les
états sont une simple pastille (Sourcé / Saisi / Repère pris / Mes ratios / Sans
objet), jamais « À renseigner ». Les nombres sont CEUX du moteur : écran = PDF.
"""

from __future__ import annotations

from datetime import date

from ..exports import numeros
from ..exports.rendu import Cartouche, esc, page_html, render_pdf
from ..tz import today_reunion   # FIX-ORFEVRE-1 pt 3 (ORF-17/D-13) — jour Réunion, pas process
from .catalogue import Catalogue, assiette_unite, charger_catalogue
from .moteur import ResultatBilan

# G7 — mêmes libellés d'état que l'écran (pastilles) : Sourcé / Repère / Saisi / À renseigner.
_ETAT_LABEL = {
    "source": "Sourcé",
    "saisi": "Saisi",
    "repere": "Repère",
    "ratios": "Mes ratios",
    "sans_objet": "Sans objet",
    "a_renseigner": "À renseigner",
}

# Les 4 blocs sont numérotés comme dans le modèle : TOTAL (1) … TOTAL (4).
_NUM_BLOC = {"T": 1, "C": 2, "G": 3, "V": 4}

_CSS = """
.bilan h2{font-size:13px;margin:16px 0 6px;color:#2F4F3E}
.bilan table{width:100%;border-collapse:collapse;font-size:11px;table-layout:fixed}
.bilan th{text-align:left;color:#6b7a72;border-bottom:1px solid #cdd6d0;padding:4px 6px}
.bilan td{padding:4px 6px;border-bottom:1px solid #e6ece8;vertical-align:top;overflow-wrap:anywhere}
.bilan .num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.bilan tr.tot td{font-weight:700;background:#eaf2ec}
.bilan .bloc{page-break-inside:avoid;margin-bottom:10px}
.bilan .synth{page-break-before:always}
.bilan .badge{font-size:10.5px;border:1px solid #9bb0a4;border-radius:9px;padding:1px 6px;color:#44584c;white-space:nowrap}
.bilan .res{font-size:16px;font-weight:700;color:#0a6b38}
.bilan .tete2{font-size:11px;margin:4px 0 8px}
.bilan .tete2 td{border:0;padding:2px 8px}
.bilan .tete2 .k{color:#6b7a72}
.bilan .tete2 .cal{padding-left:26px}
.bilan .tete2 .v{text-align:right;font-variant-numeric:tabular-nums;font-weight:600}
.bilan .vides{color:#6b7a72;font-size:10.5px;margin:2px 0 8px}
.bilan .tete-doc{color:#6b7a72;font-size:11px;margin:-2px 0 6px}
/* DOCS-DA-1 (V10) — aucune taille sous 10,5 px : les sous-libellés `<small>` au plancher. */
.bilan small{font-size:10.5px}
"""

# Colonne « Libellé · Assiette · Taux · HT · TVA · TTC · État » — largeurs fixes
# (en-tête et lignes partagent la même grille, chiffres calés à droite).
# DOCS-COHERENCE-1 (recette Vic) — colonne « État » élargie pour « À renseigner » sur UNE ligne.
_COLGROUP = (
    "<colgroup>"
    "<col style='width:24%'><col style='width:13%'><col style='width:12%'>"
    "<col style='width:13%'><col style='width:12%'><col style='width:14%'>"
    "<col style='width:12%'></colgroup>"
)


def _eur(x: float | None) -> str:
    if x is None:
        return "—"
    return f"{round(x):,}".replace(",", " ") + " €"


def _eur_nz(x: float | None) -> str:
    """DOCS-1 (décision Vic) — un montant NUL (total d'un bloc vide, TVA de taxes…) s'écrit « — »,
    jamais « 0 € » : on ne fait pas croire à un coût/produit renseigné à zéro."""
    return "—" if not x else _eur(x)


def _pct(x: float | None) -> str:
    return "—" if x is None else f"{x * 100:.1f} %".replace(".", ",")


def _assiette(ln, poste) -> str:
    """Assiette affichée avec l'unité de sa nature (m² · lots · €) — jamais en €
    par défaut. Un forfait n'a pas d'assiette ; une assiette vide → « — »."""
    v = ln.assiette_valeur
    if not v:
        return "forfait" if poste.mode == "forfait" else "—"
    u = assiette_unite(poste.assiette)
    if u in (None, "€"):
        return _eur(v)
    return f"{round(v):,}".replace(",", " ") + f" {u}"


def _taux(ln, poste) -> str:
    v = ln.taux_ou_montant
    if ln.etat == "sans_objet":
        return "—"
    if v is None:  # ligne vide (BILAN-2) : rien à afficher, compte pour 0
        return ""
    if poste.mode == "pct":
        return f"{v:.2f} %".replace(".", ",")
    if poste.mode == "unit":
        return f"{round(v):,}".replace(",", " ") + f" {poste.unite or ''}".rstrip()
    return _eur(v)


def _tete(
    r: ResultatBilan, programme: dict | None, calendrier: dict | None, cat: Catalogue
) -> str:
    """Le bloc de tête : ratios & données du programme (ordre de l'Excel) + le
    calendrier prévisionnel. Valeurs issues du moteur (ratios) et des saisies."""
    programme = programme or {}
    ratios = {k: v for k, v in r.ratios}
    pt = r.produits_totaux

    # DOCS-COHERENCE-1 (recette Vic) — « nothing entered » = « — », JAMAIS « 0 m² » / « 0 € »
    # (un zéro inventé). Quand rien n'est saisi, SUV et CA TTC valent 0 → on affiche « — ».
    def m2(x):
        return "—" if not x else f"{round(float(x)):,}".replace(",", " ") + " m²"

    def eur0(x):
        return "—" if not x else _eur(x)

    # DOCS-1 (décision Vic) — un ratio NON SAISISSABLE (coût de construction absent → 0) s'écrit « — »,
    # jamais « 0 € » : on ne fait pas croire à un coût de zéro.
    def _ratio(k):
        v = str(ratios.get(k, "—") or "—").strip()
        return "—" if v.replace(" ", " ").replace(" ", "") in ("0€", "0,0€", "0,00€", "") else v
    # Ordre du modèle (A4, A9, A10, A11, A14, A15, A16, A18, A21, A22).
    lignes_g = [
        ("Terrain", m2(programme.get("terrain"))),
        ("Surface de plancher", m2(programme.get("sdp"))),
        ("Surface taxable", m2(programme.get("surface_taxable"))),
        ("Surface vendable", m2(pt.get("suv"))),
        ("Coût const. m² de surface vendable HT", _ratio("Coût const. m² de surface vendable HT")),
        ("Prix moyen m² de surface vendable HT", _ratio("Prix moyen au m² de surface vendable HT")),
        ("Net promoteur m² de surface vendable TTC", _ratio("Net promoteur m² de surface vendable TTC")),
        ("CA TTC programme", eur0(r.ca_ttc)),
        ("Renta nette / CA HT", _pct(r.marge_pct) if r.ca_ttc else "—"),
        ("Nombre de lots", str(round(pt.get("lots") or 0)) if pt.get("lots") else "—"),
    ]
    cal = calendrier or {}
    lignes_c = []
    for etape in cat.calendrier:
        off = cal.get(etape["id"], etape.get("defaut"))
        txt = "—" if off is None else (f"J + {off} mois" if off else "J")
        lignes_c.append((etape["libelle"], txt))

    # DOCS-COHERENCE-1 (recette Vic) — UNE SEULE table à 4 colonnes (ratios | calendrier) : la
    # disposition flex de deux tables se repliait sous WeasyPrint et faisait « fuir » les valeurs
    # des ratios (« 0 m² », « 0 € ») dans la colonne du calendrier. Grille déterministe ici.
    n = max(len(lignes_g), len(lignes_c))
    rows = []
    for i in range(n):
        gk, gv = lignes_g[i] if i < len(lignes_g) else ("", "")
        ck, cv = lignes_c[i] if i < len(lignes_c) else ("", "")
        rows.append(
            f"<tr><td class='k'>{esc(gk)}</td><td class='v'>{esc(str(gv))}</td>"
            f"<td class='k cal'>{esc(ck)}</td><td class='v'>{esc(str(cv))}</td></tr>"
        )
    return (
        "<table class='tete2'><thead><tr><th colspan='2'>Ratios &amp; programme</th>"
        "<th colspan='2'>Calendrier prévisionnel</th></tr></thead><tbody>"
        + "".join(rows) + "</tbody></table>"
    )


def construire_html(
    r: ResultatBilan,
    *,
    idu: str,
    adresse: str = "",
    commune: str = "",
    programme: dict | None = None,
    calendrier: dict | None = None,
    cat: Catalogue | None = None,
    jour: date | None = None,
    etude_reliee: str | None = None,
    prix_demande: float | None = None,
    donnees_au: str | None = None,
    map_html: str = "",
) -> tuple[str, Cartouche]:
    cat = cat or charger_catalogue()
    j = jour or today_reunion()
    numero = numeros.numero_rapport("bilan", idu, j)

    # DOCS-COHERENCE-1 (recette Vic, G6) — en-tête COMPLET : adresse + Étude reliée + prix demandé,
    # comme à l'écran. « — » honnête quand une donnée n'est pas servie (jamais un zéro inventé).
    _etude = etude_reliee or "aucune Étude reliée"
    _prix = (f"{round(prix_demande):,}".replace(",", " ") + " €") if prix_demande else "non renseigné"
    # DOCS-1 (décision Vic) — RÉSUMÉ de couverture : chiffre d'affaires et résultat net du programme.
    _eur = lambda x: (f"{round(x):,}".replace(",", " ") + " €") if isinstance(x, (int, float)) else "—"  # noqa: E731
    # DOCS-1 (décision Vic) — pas de bénéfice annoncé en couverture tant qu'aucun coût n'est saisi.
    _res_txt = esc(_eur(r.resultat_net)) if r.resultat_net is not None else "non calculable — saisissez vos coûts"
    _resume = (f'<p class="tete-doc">CA TTC : {esc(_eur(r.ca_ttc))} · '
               f'Résultat net : {_res_txt}</p>')
    tete = (
        f'<div class="brand"><span class="wordmark">LABUSE</span>'
        f'<span class="kind">Bilan</span></div>'
        f'<h1>Bilan</h1>'
        f'<p class="idu">{esc(idu)}'
        + (f" · {esc(adresse)}" if adresse else "")
        + f" · {esc(numero)} · {j:%d/%m/%Y}</p>"
        f'<p class="tete-doc">Programme : {esc(_etude)} · Prix demandé : {esc(_prix)}</p>'
        + _resume
        + (map_html or "")   # carte de situation sur la couverture (DOCS-1)
    )

    corps = ['<div class="bilan">', tete]
    corps.append(_tete(r, programme, calendrier, cat))
    if r.lignes_vides:
        # DOCS-COHERENCE-1 (G4) — plus aucune mention de l'Excel côté client.
        corps.append(
            f"<p class='vides'>{r.lignes_vides} ligne(s) non renseignée(s) — comptées pour 0.</p>"
        )
    postes = {p.id: p for p in cat.postes()}
    lignes = {ln.id: ln for ln in r.lignes}
    for b in cat.blocs:
        tot = next(x for x in r.blocs if x.id == b.id)
        n = _NUM_BLOC.get(b.id)
        corps.append('<div class="bloc">')
        # G7 — mêmes libellés que l'écran : « n · Titre ».
        corps.append(f"<h2>{f'{n} · ' if n else ''}{esc(b.titre)}</h2>")
        corps.append(
            "<table>" + _COLGROUP + "<thead><tr><th>Libellé</th><th>Assiette</th>"
            "<th class='num'>Taux ou montant</th><th class='num'>HT</th><th class='num'>TVA</th>"
            "<th class='num'>TTC</th><th>État</th></tr></thead><tbody>"
        )
        for poste in b.postes:
            ln = lignes[poste.id]
            lib = esc(poste.libelle) + (f" <small>{esc(poste.sub)}</small>" if poste.sub else "")
            # Une ligne vide ne porte pas de montant (elle vaut 0 dans le total).
            vide = ln.manquant
            etat = _ETAT_LABEL.get(ln.etat, ln.etat)
            corps.append(
                f"<tr><td>{lib}</td>"
                f"<td class='num'>{_assiette(ln, poste)}</td>"
                f"<td class='num'>{_taux(ln, poste)}</td>"
                f"<td class='num'>{'' if vide else _eur(ln.ht)}</td>"
                # DOCS-1 (décision Vic) — une TVA nulle (taxes : 0 % de TVA) s'écrit « — », jamais « 0 € ».
                f"<td class='num'>{'' if vide else (_eur(ln.tva) if ln.tva else '—')}</td>"
                f"<td class='num'>{'' if vide else _eur(ln.ttc)}</td>"
                f"<td>{f'<span class=badge>{esc(etat)}</span>' if etat else ''}</td></tr>"
            )
        lib_tot = f"Total {n} · {esc(b.titre)}" if n else f"Total — {esc(b.titre)}"
        corps.append(
            f"<tr class='tot'><td colspan='3'>{lib_tot}</td>"
            f"<td class='num'>{_eur_nz(tot.ht)}</td>"
            f"<td class='num'>{_eur_nz(tot.tva)}</td>"
            f"<td class='num'>{_eur_nz(tot.ttc)}</td><td></td></tr>"
        )
        corps.append("</tbody></table></div>")

    # Synthèse
    corps.append('<div class="synth"><h2>Synthèse</h2><table><tbody>')
    corps.append(
        f"<tr><td>Dépenses totales</td><td class='num'>{_eur_nz(r.depenses_ht)}</td>"
        f"<td class='num'>{_eur_nz(r.depenses_tva)}</td><td class='num'>{_eur_nz(r.depenses_ttc)}</td></tr>"
    )
    corps.append(
        f"<tr><td>Chiffre d'affaires</td><td class='num'>{_eur_nz(r.ca_ht)}</td>"
        f"<td class='num'>{_eur_nz(r.ca_tva)}</td><td class='num'>{_eur_nz(r.ca_ttc)}</td></tr>"
    )
    corps.append(
        f"<tr><td>TVA résiduelle</td><td></td><td></td><td class='num'>{_eur_nz(r.tva_residuelle)}</td></tr>"
    )
    # DOCS-1 (décision Vic) — tant qu'aucun coût majeur n'est saisi, le moteur laisse résultat/marge/
    # cash-flow à None : on écrit « non calculable — saisissez vos coûts », JAMAIS un bénéfice (= tout
    # le CA) trompeur.
    if r.resultat_net is None:
        corps.append(
            "<tr class='tot'><td>Résultat net</td><td colspan='3' class='num'>"
            "non calculable — saisissez vos coûts</td></tr>"
        )
        corps.append(
            "<tr><td>Cash flow</td><td colspan='3' class='num'>"
            "non calculable — saisissez vos coûts</td></tr>"
        )
    else:
        corps.append(
            f"<tr class='tot'><td>Résultat net</td><td class='num res'>{_eur(r.resultat_net)}</td>"
            f"<td colspan='2' class='num'>{_pct(r.marge_pct)} du CA HT</td></tr>"
        )
        corps.append(
            f"<tr><td>Cash flow</td><td class='num'>{_eur(r.cash_flow)}</td><td colspan='2'></td></tr>"
        )
    corps.append("</tbody></table>")
    corps.append('<p style="color:#6b7a72;font-size:10.5px">Document non contractuel.</p>')
    corps.append("</div></div>")

    # DOCS-COHERENCE-1 (recette Vic) — pied « Données LABUSE au <date du RUN servi> » (comme les 7
    # autres documents : 21/10/2026), pas la date de génération du jour.
    au = donnees_au or f"{j:%d/%m/%Y}"
    cart = Cartouche(
        doc_title=f"LABUSE — Bilan" + (f" · {adresse}" if adresse else ""),
        doc_ref=f"{idu} · {numero}",
        doc_foot="Document d'information LABUSE.",
    )
    html = page_html("Bilan", cart, f"<style>{_CSS}</style>" + "".join(corps))
    return html, cart


def construire_pdf(r: ResultatBilan, **kw) -> bytes:
    html, _ = construire_html(r, **kw)
    return render_pdf(html)
