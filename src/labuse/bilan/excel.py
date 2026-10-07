"""BILAN-1 Lot 5 / BILAN-2 — export Excel VIVANT du bilan.

Pas de valeurs figées : les colonnes HT / TVA / TTC et les totaux sont des
FORMULES qui recalculent à partir des saisies (taux, assiettes, programme). Une
seule feuille, colonnes Libellé · Assiette · Taux · HT · TVA · TTC. En haut, comme
dans le modèle de la promotrice, le bloc de ratios & données du programme (ordre de
l'Excel) et le calendrier prévisionnel. Ouvert dans un tableur, le fichier se
recalcule tout seul ; ses totaux sont identiques au moteur (recette « écran = PDF =
Excel »).

BILAN-2 : le classeur se génère à TOUT MOMENT (calcul en continu, case vide = 0).

On n'utilise QUE un vocabulaire de formules simple (références de cellules,
`+ - * /`, parenthèses, `SUM(plage)`) : le test évalue ce graphe sans tableur.
"""

from __future__ import annotations

from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from .catalogue import Catalogue, charger_catalogue
from .moteur import EntreesBilan

_EUR = '#,##0 €'
_PCT = '0.00 %'
_GRAS = Font(bold=True)
_ENTETE = Font(bold=True, color="FFFFFF")
_FOND = PatternFill("solid", fgColor="2F4F3E")
_FOND_TOT = PatternFill("solid", fgColor="EAF2EC")
_FIN = Side(style="thin", color="D5DDD7")
_BORD = Border(bottom=_FIN)


def classeur_bilan(
    entrees: EntreesBilan, catalogue: Catalogue | None = None, titre: str = "Bilan"
) -> Workbook:
    cat = catalogue or charger_catalogue()
    tva_dom = float(cat.tva_legales["dom_standard"])
    wb = Workbook()
    ws = wb.active
    ws.title = "Bilan"
    widths = {"A": 34, "B": 16, "C": 12, "D": 15, "E": 13, "F": 15, "G": 2}
    for col, w in widths.items():
        ws.column_dimensions[col].width = w

    ws.cell(1, 1, titre).font = Font(bold=True, size=14)
    # BILAN-2 : le haut de feuille (lignes 3..24) reçoit le bloc de ratios &
    # programme + le calendrier (comme le modèle). Il est REMPLI à la fin, une fois
    # connues les adresses des cellules du corps ; le corps démarre donc plus bas.
    _HEAD_FIN = 25
    r = _HEAD_FIN + 1

    def entete(label):
        nonlocal r
        ws.cell(r, 1, label).font = _GRAS
        r += 1

    # ---- Programme (cellules d'entrée référencées par les assiettes) ----
    entete("Programme")
    cell_terrain = f"B{r}"
    ws.cell(r, 1, "Terrain (m²)")
    ws.cell(r, 2, entrees.programme.terrain)
    r += 1
    cell_sdp = f"B{r}"
    ws.cell(r, 1, "Surface de plancher (m²)")
    ws.cell(r, 2, entrees.programme.sdp)
    r += 1
    cell_stax = f"B{r}"
    ws.cell(r, 1, "Surface taxable (m²)")
    ws.cell(r, 2, entrees.programme.surface_taxable)
    r += 1
    cell_loyer = f"B{r}"
    ws.cell(r, 1, "Loyer (€/m² SUV)")
    ws.cell(r, 2, entrees.programme.loyer)
    r += 2

    # ---- Produits ----
    entete("Produits")
    hdr = ["Produit", "Lots", "SUV m²", "Prix TTC/m²", "TVA", "CA TTC", "CA HT"]
    for i, h in enumerate(hdr, start=1):
        c = ws.cell(r, i, h)
        c.font = _ENTETE
        c.fill = _FOND
    r += 1
    prod_ca_ttc_cells: list[str] = []
    prod_first = r
    for p in entrees.produits:
        ws.cell(r, 1, p.libelle)
        ws.cell(r, 2, p.lots)
        ws.cell(r, 3, p.suv)
        ws.cell(r, 4, p.prix_ttc_m2_suv)
        ws.cell(r, 5, p.tva).number_format = _PCT
        ws.cell(r, 6, f"=C{r}*D{r}").number_format = _EUR  # CA TTC = SUV × prix
        ws.cell(r, 7, f"=F{r}/(1+E{r})").number_format = _EUR  # CA HT
        prod_ca_ttc_cells.append(f"F{r}")
        r += 1
    prod_last = r - 1
    # Totaux produits
    ws.cell(r, 1, "Total produits").font = _GRAS
    cell_lots = f"B{r}"
    cell_suv = f"C{r}"
    cell_ca_ttc = f"F{r}"
    cell_ca_ht = f"G{r}"
    ws.cell(r, 2, f"=SUM(B{prod_first}:B{prod_last})")
    ws.cell(r, 3, f"=SUM(C{prod_first}:C{prod_last})")
    ws.cell(r, 6, f"=SUM(F{prod_first}:F{prod_last})").number_format = _EUR
    ws.cell(r, 7, f"=SUM(G{prod_first}:G{prod_last})").number_format = _EUR
    for cc in range(1, 8):
        ws.cell(r, cc).fill = _FOND_TOT
    r += 2

    # ---- Bilan : une ligne par poste, HT/TVA/TTC en formules ----
    hdr = ["Libellé", "Assiette", "Taux", "HT", "TVA", "TTC"]
    for i, h in enumerate(hdr, start=1):
        c = ws.cell(r, i, h)
        c.font = _ENTETE
        c.fill = _FOND
    r += 1

    # placeholders résolus en deux passes (achat/constr référencés par d'autres)
    ligne_poste: dict[str, int] = {}
    bloc_ht_cells: dict[str, tuple[int, int]] = {}

    def assiette_ref(poste, saisie) -> str | None:
        a = poste.assiette
        m = {
            "terrain": cell_terrain,
            "surface_taxable": cell_stax,
            "suv": cell_suv,
            "lots": cell_lots,
            "ca_ttc": cell_ca_ttc,
        }
        if a in m:
            return f"={m[a]}"
        if a == "prix_terrain":
            return f"=D{ligne_poste['achat']}"
        if a == "construction":
            return f"=D{ligne_poste['constr']}"
        if a == "demi_construction_ttc":
            return f"=D{ligne_poste['constr']}*(1+{tva_dom})/2"
        if a == "ca_produit_1":
            return f"={prod_ca_ttc_cells[0]}" if prod_ca_ttc_cells else None
        if a == "ca_produit_2":
            return f"={prod_ca_ttc_cells[1]}" if len(prod_ca_ttc_cells) > 1 else None
        if a == "loyers_annuels":
            return f"={cell_loyer}*{cell_suv}"
        if a in ("pret", "valeur_ajoutee"):
            return None  # valeur littérale posée en B (saisie)
        if a == "total2_ht":
            lo, hi = bloc_ht_cells["C"]
            return f"=SUM(D{lo}:D{hi})"
        if a == "total2_ttc":
            lo, hi = bloc_ht_cells["C"]
            return f"=SUM(F{lo}:F{hi})"
        # assiettes d'assurances composées comme le tableur : total(2) + sol − imprévus
        if a == "total2_ht_sol_imprevus":
            lo, hi = bloc_ht_cells["C"]
            return f"=SUM(D{lo}:D{hi})+D{ligne_poste['sol']}-D{ligne_poste['aleaC']}"
        if a == "total2_ttc_sol_imprevus":
            lo, hi = bloc_ht_cells["C"]
            return f"=SUM(F{lo}:F{hi})+F{ligne_poste['sol']}-F{ligne_poste['aleaC']}"
        return None

    # première passe : réserver les lignes, poser libellé/taux/assiette-littérale
    bloc_rows: dict[str, tuple[int, int]] = {}
    for bloc in cat.blocs:
        start = r
        for poste in bloc.postes:
            ligne_poste[poste.id] = r
            r += 1
        bloc_rows[bloc.id] = (start, r - 1)
        bloc_ht_cells[bloc.id] = (start, r - 1)
        r += 1  # ligne de total du bloc
    # on connaît maintenant toutes les lignes → deuxième passe (écriture)
    r = list(bloc_rows.values())[0][0]  # retour au début du tableau des postes

    def taux_tva(poste, saisie):
        if saisie.etat == "sans_objet":
            return 0.0
        if isinstance(poste.tva, (int, float)):
            return float(poste.tva)
        return saisie.tva  # a_saisir

    for bloc in cat.blocs:
        start, end = bloc_rows[bloc.id]
        for poste in bloc.postes:
            rr = ligne_poste[poste.id]
            s = entrees.saisie(poste.id)
            ws.cell(rr, 1, poste.libelle + (f" — {poste.sub}" if poste.sub else ""))
            # Assiette (B)
            aref = assiette_ref(poste, s)
            if poste.assiette in ("pret", "valeur_ajoutee"):
                ws.cell(rr, 2, s.assiette_valeur)
            elif aref:
                ws.cell(rr, 2, aref).number_format = _EUR if poste.mode != "unit" else '#,##0.00'
            # Taux / montant (C)
            val = 0.0 if s.etat == "sans_objet" else (s.valeur if s.valeur is not None else None)
            cC = ws.cell(rr, 3, val)
            cC.number_format = _PCT if poste.mode == "pct" else _EUR
            tva = taux_tva(poste, s)
            # HT (D)
            if poste.mode == "forfait":
                brut = f"C{rr}"
            elif poste.mode == "pct":
                brut = f"(B{rr}*C{rr}/100)"
            else:  # unit
                brut = f"(B{rr}*C{rr})"
            if poste.base == "ttc" and tva:
                ht = f"={brut}/(1+{tva})"
                tvaf = f"={brut}-D{rr}"
                ttc = f"={brut}"
            else:
                ht = f"={brut}"
                tvaf = f"=D{rr}*{tva}" if tva else "=0"
                ttc = f"=D{rr}+E{rr}"
            ws.cell(rr, 4, ht).number_format = _EUR
            ws.cell(rr, 5, tvaf).number_format = _EUR
            ws.cell(rr, 6, ttc).number_format = _EUR
            for cc in range(1, 7):
                ws.cell(rr, cc).border = _BORD
        # total du bloc
        tr = end + 1
        ws.cell(tr, 1, f"Total — {bloc.titre}").font = _GRAS
        ws.cell(tr, 4, f"=SUM(D{start}:D{end})").number_format = _EUR
        ws.cell(tr, 5, f"=SUM(E{start}:E{end})").number_format = _EUR
        ws.cell(tr, 6, f"=SUM(F{start}:F{end})").number_format = _EUR
        for cc in range(1, 7):
            ws.cell(tr, cc).fill = _FOND_TOT
        bloc_rows[bloc.id] = (start, end, tr)  # type: ignore[assignment]

    r = max(v[2] for v in bloc_rows.values()) + 2  # après le dernier total de bloc

    # ---- Synthèse : dépenses, CA, TVA résiduelle, résultat, marge ----
    tot_cells = {b: bloc_rows[b][2] for b in ("T", "C", "G", "V")}
    dep_ht = "+".join(f"D{tot_cells[b]}" for b in ("T", "C", "G", "V"))
    dep_tva = "+".join(f"E{tot_cells[b]}" for b in ("T", "C", "G", "V"))

    def ligne(label, d=None, e=None, f=None, fmt=_EUR, gras=False):
        nonlocal r
        ws.cell(r, 1, label).font = _GRAS if gras else Font()
        for col, frm in ((4, d), (5, e), (6, f)):
            if frm is not None:
                c = ws.cell(r, col, frm)
                c.number_format = fmt
                if gras:
                    c.font = _GRAS
        r += 1

    ligne("Dépenses totales", d=f"={dep_ht}", e=f"={dep_tva}", f=f"=D{r}+E{r}", gras=True)
    row_dep = r - 1
    ligne("Chiffre d'affaires", d=f"={cell_ca_ht}", e=f"={cell_ca_ttc}-{cell_ca_ht}", f=f"={cell_ca_ttc}", gras=True)
    ligne("TVA résiduelle", f=f"=(E{row_dep + 1}) - E{row_dep}")  # (CA TTC-HT) - dépenses TVA
    row_res = r
    ligne("Résultat net", d=f"=D{row_dep + 1}-D{row_dep}", gras=True)  # CA HT - dépenses HT
    ws.cell(row_res, 5, f"=D{row_res}/D{row_dep + 1}").number_format = _PCT  # marge % du CA HT
    ws.cell(row_res, 5).font = _GRAS
    mod_row = ligne_poste["mod"]
    ligne("Cash flow", d=f"=D{row_res}+D{mod_row}")

    # ---- Haut de feuille : ratios & programme (ordre du modèle) + calendrier ----
    # Rempli ici car il référence des cellules du corps, maintenant connues.
    d = {k: ligne_poste.get(k) for k in ("constr", "aleaC", "acte", "pack", "proc")}
    _M2 = '#,##0 "m²"'
    ratios_tete = [
        ("Terrain", f"={cell_terrain}", _M2),
        ("Surface de plancher", f"={cell_sdp}", _M2),
        ("Surface taxable", f"={cell_stax}", _M2),
        ("SUV", f"={cell_suv}", _M2),
        ("Coût const. m² SUV HT", f"=(D{d['constr']}+D{d['aleaC']})/{cell_suv}", _EUR),
        ("Prix moyen m² SUV HT", f"={cell_ca_ht}/{cell_suv}", _EUR),
        (
            "Net promoteur m² SUV TTC",
            f"=(({cell_ca_ht}-D{d['acte']}-D{d['pack']}-D{d['proc']})/{cell_suv})*(1+{tva_dom})",
            _EUR,
        ),
        ("CA TTC programme", f"={cell_ca_ttc}", _EUR),
        ("Renta nette / CA HT", f"=D{row_res}/{cell_ca_ht}", _PCT),
        ("Nombre de lots", f"={cell_lots}", '#,##0'),
    ]
    ws.cell(3, 1, "Ratios & programme").font = _GRAS
    for i, (lib, frm, fmt) in enumerate(ratios_tete):
        rr = 4 + i
        ws.cell(rr, 1, lib)
        ws.cell(rr, 5, frm).number_format = fmt

    ws.cell(15, 1, "Calendrier prévisionnel").font = _GRAS
    for i, etape in enumerate(cat.calendrier):
        rr = 16 + i
        off = entrees.calendrier.get(etape["id"], etape.get("defaut"))
        txt = "" if off is None else (f"J+{off}" if off else "J")
        ws.cell(rr, 1, etape["libelle"])
        ws.cell(rr, 5, txt)

    return wb


def classeur_bilan_bytes(entrees: EntreesBilan, **kw: Any) -> bytes:
    import io

    wb = classeur_bilan(entrees, **kw)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
