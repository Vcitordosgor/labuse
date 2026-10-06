"""BILAN-1 Lot 5 — le PDF du Bilan.

Même couverture/en-tête/pied que les autres documents (marque LABUSE, cartouche
@page lu par le rendu), puis une page par bloc (Libellé · Assiette · Taux · HT ·
TVA · TTC · État, avec badges d'état) et une page de synthèse (dépenses, CA, TVA
résiduelle, résultat net, marge, cash flow). Les nombres sont CEUX du moteur :
écran = PDF par construction. Généré seulement si le bilan est complet.
"""

from __future__ import annotations

from datetime import date

from ..exports import numeros
from ..exports.rendu import Cartouche, esc, page_html, render_pdf
from .catalogue import Catalogue, charger_catalogue
from .moteur import ResultatBilan

_ETAT_LABEL = {
    "source": "Sourcé",
    "saisi": "Saisi",
    "repere": "Repère pris",
    "ratios": "Mes ratios",
    "sans_objet": "Sans objet",
    "a_renseigner": "À renseigner",
}

_CSS = """
.bilan h2{font-size:13px;margin:18px 0 6px;color:#2F4F3E}
.bilan table{width:100%;border-collapse:collapse;font-size:11px}
.bilan th{text-align:left;color:#6b7a72;border-bottom:1px solid #cdd6d0;padding:4px 6px}
.bilan td{padding:4px 6px;border-bottom:1px solid #e6ece8;vertical-align:top}
.bilan .num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.bilan tr.tot td{font-weight:700;background:#eaf2ec}
.bilan .bloc{page-break-inside:avoid;margin-bottom:10px}
.bilan .synth{page-break-before:always}
.bilan .badge{font-size:10px;border:1px solid #9bb0a4;border-radius:9px;padding:1px 6px;color:#44584c}
.bilan .res{font-size:16px;font-weight:700;color:#0a6b38}
"""


def _eur(x: float | None) -> str:
    if x is None:
        return "—"
    return f"{round(x):,}".replace(",", " ") + " €"


def _pct(x: float | None) -> str:
    return "—" if x is None else f"{x * 100:.1f} %".replace(".", ",")


def _taux(ln, poste) -> str:
    v = ln.taux_ou_montant
    if ln.etat == "sans_objet" or v is None:
        return "—"
    if poste.mode == "pct":
        return f"{v:.2f} %".replace(".", ",")
    if poste.mode == "unit":
        return f"{round(v):,}".replace(",", " ") + f" {poste.unite or ''}".rstrip()
    return _eur(v)


def construire_html(
    r: ResultatBilan,
    *,
    idu: str,
    adresse: str = "",
    commune: str = "",
    cat: Catalogue | None = None,
    jour: date | None = None,
) -> tuple[str, Cartouche]:
    cat = cat or charger_catalogue()
    j = jour or date.today()
    numero = numeros.numero_rapport("bilan", idu, j)

    tete = (
        f'<div class="brand"><span class="wordmark">LABUSE</span>'
        f'<span class="kind">Bilan</span></div>'
        f'<h1>Bilan</h1>'
        f'<p class="idu">{esc(idu)}'
        + (f" · {esc(adresse)}" if adresse else "")
        + f" · {esc(numero)} · {j:%d/%m/%Y}</p>"
    )

    corps = ['<div class="bilan">', tete]
    postes = {p.id: p for p in cat.postes()}
    lignes = {ln.id: ln for ln in r.lignes}
    for b in cat.blocs:
        tot = next(x for x in r.blocs if x.id == b.id)
        corps.append('<div class="bloc">')
        corps.append(f"<h2>{esc(b.titre)}</h2>")
        corps.append(
            "<table><thead><tr><th>Libellé</th><th>Assiette</th>"
            "<th class='num'>Taux</th><th class='num'>HT</th><th class='num'>TVA</th>"
            "<th class='num'>TTC</th><th>État</th></tr></thead><tbody>"
        )
        for poste in b.postes:
            ln = lignes[poste.id]
            lib = esc(poste.libelle) + (f" <small>{esc(poste.sub)}</small>" if poste.sub else "")
            corps.append(
                f"<tr><td>{lib}</td>"
                f"<td class='num'>{_eur(ln.assiette_valeur) if ln.assiette_valeur is not None else '—'}</td>"
                f"<td class='num'>{_taux(ln, poste)}</td>"
                f"<td class='num'>{_eur(ln.ht)}</td>"
                f"<td class='num'>{_eur(ln.tva)}</td>"
                f"<td class='num'>{_eur(ln.ttc)}</td>"
                f"<td><span class='badge'>{_ETAT_LABEL.get(ln.etat, ln.etat)}</span></td></tr>"
            )
        corps.append(
            f"<tr class='tot'><td colspan='3'>Total — {esc(b.titre)}</td>"
            f"<td class='num'>{_eur(tot.ht)}</td><td class='num'>{_eur(tot.tva)}</td>"
            f"<td class='num'>{_eur(tot.ttc)}</td><td></td></tr>"
        )
        corps.append("</tbody></table></div>")

    # Synthèse
    corps.append('<div class="synth"><h2>Synthèse</h2><table><tbody>')
    corps.append(
        f"<tr><td>Dépenses totales</td><td class='num'>{_eur(r.depenses_ht)}</td>"
        f"<td class='num'>{_eur(r.depenses_tva)}</td><td class='num'>{_eur(r.depenses_ttc)}</td></tr>"
    )
    corps.append(
        f"<tr><td>Chiffre d'affaires</td><td class='num'>{_eur(r.ca_ht)}</td>"
        f"<td class='num'>{_eur(r.ca_tva)}</td><td class='num'>{_eur(r.ca_ttc)}</td></tr>"
    )
    corps.append(
        f"<tr><td>TVA résiduelle</td><td></td><td></td><td class='num'>{_eur(r.tva_residuelle)}</td></tr>"
    )
    corps.append(
        f"<tr class='tot'><td>Résultat net</td><td class='num res'>{_eur(r.resultat_net)}</td>"
        f"<td colspan='2' class='num'>{_pct(r.marge_pct)} du CA HT</td></tr>"
    )
    corps.append(
        f"<tr><td>Cash flow</td><td class='num'>{_eur(r.cash_flow)}</td><td colspan='2'></td></tr>"
    )
    corps.append("</tbody></table>")
    corps.append('<p style="color:#6b7a72;font-size:10px">Document non contractuel.</p>')
    corps.append("</div></div>")

    au = f"{j:%d/%m/%Y}"
    cart = Cartouche(
        doc_title=f"LABUSE — Bilan" + (f" · {adresse}" if adresse else ""),
        doc_ref=f"{idu} · {numero}",
        doc_foot=f"Document d'information LABUSE. Données au {au}.",
    )
    html = page_html("Bilan", cart, f"<style>{_CSS}</style>" + "".join(corps))
    return html, cart


def construire_pdf(r: ResultatBilan, **kw) -> bytes:
    html, _ = construire_html(r, **kw)
    return render_pdf(html)
