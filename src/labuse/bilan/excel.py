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
from openpyxl.worksheet.datavalidation import DataValidation

from .catalogue import Catalogue, assiette_unite, charger_catalogue
from .moteur import EntreesBilan

# CHIRURGICAL-FIX-1 (LOT H pt1) — même texte que le PDF (bilan/pdf.py) quand un coût requis manque :
# le classeur ne doit PAS afficher un résultat (= CA), 100 % de marge et un cash-flow calculés par
# des FORMULES Excel qui recalculent « dépenses vides = 0 ». Il gèle ces lignes comme le PDF.
_NON_CALCULABLE = "non calculable — saisissez vos coûts"

def _dec_m2(x: float) -> str:
    """CHIRURGICAL-FIX-1 (LOT O 2) — surface AVEC sa décimale quand elle en a (« 595,1 »), entière sinon
    (« 595 »), virgule française : assez de décimales pour VOIR le dépassement (595,1 contre 595)."""
    s = f"{float(x):.1f}".rstrip("0").rstrip(".")
    return s.replace(".", ",")


def _xl_m2(ref: str) -> str:
    """CHIRURGICAL-FIX-1 (LOT Q / LOT R) — SOUS-EXPRESSION Excel qui formate une surface d'une CELLULE
    VIVANTE, même règle que le PDF : la valeur est ARRONDIE au centième (`ROUND(.,2)`, précision d'une
    surface), puis affichée entière si entière (« 595 »), sinon à 2 décimales au plus (« 595,01 »),
    virgule française. Le message d'alerte se construit avec elle → il suit la saisie."""
    rref = f"ROUND({ref},2)"
    return (f'IF({rref}=INT({rref}),TEXT({rref},"0"),'
            f'SUBSTITUTE(TEXT({rref},"0.##"),".",","))')


_EUR = '#,##0 €'
_PCT = '0.0 %'   # DOCS-1 : les taux (TVA, marge) s'affichent « 8,5 % », jamais « 0.085 » ni « 8,50 % »
_M2 = '#,##0.## "m²"'   # LOT P — les surfaces montrent leurs décimales (« 595,01 m² »), entières sinon
_LOTS = '#,##0 "lots"'


def _assiette_fmt(poste) -> str:
    """Format de l'assiette selon sa nature (m² · lots · €) — retour Vic BILAN-2."""
    return {"m²": _M2, "lots": _LOTS}.get(assiette_unite(poste.assiette), _EUR)
_GRAS = Font(bold=True)
_ENTETE = Font(bold=True, color="FFFFFF")
_FOND = PatternFill("solid", fgColor="2F4F3E")
_FOND_TOT = PatternFill("solid", fgColor="EAF2EC")
_FIN = Side(style="thin", color="D5DDD7")
_BORD = Border(bottom=_FIN)


def classeur_bilan(
    entrees: EntreesBilan, catalogue: Catalogue | None = None, titre: str = "Bilan",
    garde_fou: dict | None = None,
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
    # CHIRURGICAL-FIX-1 (LOT K 2b / LOT L 2) — bandeau garde-fou en tête. Les alertes STATIQUES (habitat
    # interdit, terrain libéré, démolition non chiffrée) sont du texte ; l'alerte « SDP > surface à
    # retenir » devient une FORMULE VIVANTE (ligne 3) qui réagit quand on change la surface de plancher.
    _gf = garde_fou or {}
    _sar = _gf.get("surface_a_retenir")
    # LOT L 2 / LOT N 2 — les alertes qui ont une FORMULE VIVANTE dans la feuille (surface à retenir,
    # surface vendable > surface de plancher) ne sont pas répétées en texte figé dans le bandeau A2.
    _gf_statiques = [a for a in (_gf.get("alertes") or [])
                     if "dépasse la surface à retenir" not in a
                     and "supérieure à la surface de plancher" not in a]
    if _gf_statiques:
        # CHIRURGICAL-FIX-1 (LOT M 3) — même libellé que le PDF : « Aucun programme » quand le Bilan est
        # livré sans programme (parcelle écartée), « Programme saisi » quand l'utilisateur en a saisi un.
        if _gf.get("programme_saisi", True):
            _txt = ("Programme saisi — non vérifié par LABUSE : " + " ; ".join(_gf_statiques)
                    + " Les chiffres ci-dessous découlent de cette saisie.")
        else:
            # CHIRURGICAL-FIX-1 (LOT N 3) — même texte que le PDF (reprend la distinction du Dossier).
            from .reperes import bandeau_sans_programme
            _titre, _bas = bandeau_sans_programme(_gf)
            _txt = f"{_titre} : " + (" ; ".join(_gf_statiques) + " " if _gf_statiques else "") + _bas
        c = ws.cell(2, 1, _txt)
        c.font = Font(bold=True, color="7C2D12")
        c.fill = PatternFill("solid", fgColor="FFF7ED")
        c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.merge_cells("A2:F2")
        ws.row_dimensions[2].height = 42
    # CHIRURGICAL-FIX-1 (LOT Q) — la « surface à retenir du Dossier » est posée DANS UNE CELLULE (I2) :
    # l'alerte SDP > surface à retenir se construit à partir d'ELLE (pas d'un nombre figé dans la
    # formule), donc le message suit si on modifie cette cellule ou la SDP sans régénérer.
    cell_sar = "I2"
    if isinstance(_sar, (int, float)):
        ws["H2"] = "Surface à retenir (Dossier, m²)"
        ws[cell_sar] = _sar
    # BILAN-2 : le haut de feuille (lignes 3..24) reçoit le bloc de ratios &
    # programme + le calendrier (comme le modèle). Il est REMPLI à la fin, une fois
    # connues les adresses des cellules du corps ; le corps démarre donc plus bas.
    _HEAD_FIN = 25
    r = _HEAD_FIN + 1
    # CHIRURGICAL-FIX-1 (LOT J 1c) — on collecte les cellules de SAISIE pour y poser une validation
    # Excel « ≥ 0 » : un coût négatif (ex. −250 000 € sur AD0887 → 128 % de marge) est refusé à la main.
    saisie_cells: list[str] = []
    # CHIRURGICAL-FIX-1 (LOT L 3) — cellule de VALIDITÉ unique (hors zone visible), remplie en fin de
    # feuille d'une formule sur toutes les cellules de saisie + TVA ; lue par toutes les formules de résultat.
    cell_valid = "I1"

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
    # CHIRURGICAL-FIX-1 (LOT L 2 / LOT O 2 / LOT P / LOT Q) — avertissement VIVANT à côté de la SDP :
    # compare la cellule de SDP à la surface à retenir (cellule `cell_sar`, ci-dessous), SUR LES DÉCIMALES
    # (pas d'arrondi : 595,01 > 595 alerte), MÊME seuil que le PDF. LOT Q — le message se CONSTRUIT DANS LA
    # FORMULE à partir des cellules (plus de valeurs figées à l'export) : si on modifie la SDP ou la
    # surface à retenir SANS régénérer, le texte cité suit (`_xl_m2`, même règle d'affichage que le PDF).
    if isinstance(_sar, (int, float)):
        # LOT R — comparaison AU CENTIÈME (ROUND(.,2)) : tient même sur une valeur collée à 3 décimales ;
        # un écart < 0,01 m² ne déclenche pas l'alerte (sinon « 595 contre 595 »).
        wf = (f'=IF(AND(ROUND({cell_sdp},2)>0,ROUND({cell_sdp},2)>ROUND({cell_sar},2)),'
              f'"⚠ surface de plancher ("&{_xl_m2(cell_sdp)}&" m²) dépasse la surface à retenir du '
              f'Dossier ("&{_xl_m2(cell_sar)}&" m²) — à vérifier","")')
        wc = ws.cell(r, 3, wf)
        wc.font = Font(bold=True, color="B45309")
    r += 1
    cell_stax = f"B{r}"
    ws.cell(r, 1, "Surface taxable (m²)")
    ws.cell(r, 2, entrees.programme.surface_taxable)
    r += 1
    cell_loyer = f"B{r}"
    ws.cell(r, 1, "Loyer (€/m² de surface vendable)")
    ws.cell(r, 2, entrees.programme.loyer)
    r += 2
    saisie_cells += [cell_terrain, cell_sdp, cell_stax, cell_loyer]   # LOT J 1c — saisies programme

    # ---- Produits ----
    entete("Produits")
    hdr = ["Produit", "Lots", "surface vendable (m²)", "Prix TTC/m²", "TVA", "CA TTC", "CA HT"]
    for i, h in enumerate(hdr, start=1):
        c = ws.cell(r, i, h)
        c.font = _ENTETE
        c.fill = _FOND
    r += 1
    prod_ca_ttc_cells: list[str] = []
    prod_ht_cells: list[str] = []      # LOT M 2 — cellules CA HT par produit (peuvent porter du texte)
    tva_cells: list[str] = []          # LOT K 2 — cellules de TVA (validées 0..1 à la main)
    prod_first = r
    for p in entrees.produits:
        ws.cell(r, 1, p.libelle)
        ws.cell(r, 2, p.lots)
        ws.cell(r, 3, p.suv)
        ws.cell(r, 4, p.prix_ttc_m2_suv)
        ws.cell(r, 5, p.tva).number_format = _PCT
        saisie_cells += [f"B{r}", f"C{r}", f"D{r}"]   # LOT J 1c — lots / surface vendable / prix
        tva_cells.append(f"E{r}")
        ws.cell(r, 6, f"=C{r}*D{r}").number_format = _EUR  # CA TTC = SUV × prix
        # CHIRURGICAL-FIX-1 (LOT K 2d) — une TVA de vente hors [0 %, 100 %] casse le HT (TVA = −100 %
        # → division par 0 → #DIV/0!). La formule dit « saisie invalide » au lieu de propager l'erreur ;
        # la validation Excel (plus bas) refuse déjà la saisie hors bornes.
        # CHIRURGICAL-FIX-1 (LOT M 2) — une TVA de vente VIDE n'est PAS 0 % : un produit qui VEND
        # (CA TTC > 0) avec une TVA vide a un CA HT « non calculable » (on ne divise pas par 1 + 0).
        # Hors [0 %, 100 %] → « saisie invalide ». Un produit à blanc (CA TTC = 0) reste à 0.
        ws.cell(r, 7, f'=IF(AND(ISBLANK(E{r}),F{r}>0),"non calculable",'
                      f'IF(OR(E{r}<0,E{r}>1),"saisie invalide",'
                      f'IF(F{r}=0,0,F{r}/(1+E{r}))))').number_format = _EUR  # CA HT
        prod_ht_cells.append(f"G{r}")
        prod_ca_ttc_cells.append(f"F{r}")
        r += 1
    prod_last = r - 1
    # Totaux produits
    ws.cell(r, 1, "Total produits").font = _GRAS
    cell_lots = f"B{r}"
    cell_suv = f"C{r}"
    cell_ca_ttc = f"F{r}"
    cell_ca_ht = f"G{r}"
    # CHIRURGICAL-FIX-1 (LOT J 1a) — SANS produit (AM0838), la plage de total est INVERSÉE et inclut la
    # ligne de total elle-même (`SUM(B{r}:B{r-1})` avec prod_first = r) → RÉFÉRENCE CIRCULAIRE au recalcul.
    # On écrit `=0` (FORMULE, pas un 0 littéral) quand il n'y a aucun produit (plage vide) : LOT O 1 —
    # la ligne « Total produits » (AM0838 / IS0448, 0 produit) devient ainsi une case CALCULÉE, donc
    # ENVELOPPÉE par la validité → elle affiche « saisie invalide » comme les autres après un rejet (plus
    # de quatre zéros qui résistent). Jamais une somme auto-référente (plage inversée).
    def _somme_produits(col: str):
        return f"=SUM({col}{prod_first}:{col}{prod_last})" if prod_last >= prod_first else "=0"

    # CHIRURGICAL-FIX-1 (LOT M 2) — le CA HT total propage le « non calculable » : on ADDITIONNE les
    # cellules (« + », PAS SUM — SUM IGNORE le texte et rendrait 0, le bug « CA HT à zéro »). Si un
    # produit porte « non calculable », l'addition échoue → IFERROR → « non calculable » (jamais un CA
    # HT fabriqué sur une TVA supposée nulle).
    def _somme_ca_ht():
        if not prod_ht_cells:
            return "=0"      # LOT O 1 — formule (enveloppée), pas un 0 littéral qui résisterait au rejet
        return f'=IFERROR({"+".join(prod_ht_cells)},"non calculable")'
    ws.cell(r, 2, _somme_produits("B"))
    ws.cell(r, 3, _somme_produits("C"))
    ws.cell(r, 6, _somme_produits("F")).number_format = _EUR
    ws.cell(r, 7, _somme_ca_ht()).number_format = _EUR
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
                ws.cell(rr, 2, s.assiette_valeur).number_format = _assiette_fmt(poste)
                saisie_cells.append(f"B{rr}")           # LOT J 1c — assiette saisie (prêt / valeur ajoutée)
            elif aref:
                ws.cell(rr, 2, aref).number_format = _assiette_fmt(poste)
            # Taux / montant (C) — cellule de SAISIE du coût (LOT J 1c : validée ≥ 0)
            val = 0.0 if s.etat == "sans_objet" else (s.valeur if s.valeur is not None else None)
            cC = ws.cell(rr, 3, val)
            cC.number_format = _PCT if poste.mode == "pct" else _EUR
            saisie_cells.append(f"C{rr}")
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

    # CHIRURGICAL-FIX-1 (LOT L 3 / LOT M 2) — UNE SEULE cellule de VALIDITÉ (`cell_valid`, remplie en
    # fin de feuille) : « saisie invalide » dès qu'un coût est négatif ou qu'une TVA sort de [0 %, 100 %].
    # Toutes les formules de RÉSULTAT ET les TOTAUX (dépenses, CA) la lisent + un IFERROR : l'erreur ne
    # reste JAMAIS sur une seule ligne et ne laisse JAMAIS passer un #VALUE! (texte collé dans un coût).
    _inv = f'{cell_valid}<>""'

    def _si_valide(formule_ok: str, err: str = "non calculable") -> str:
        if not formule_ok.startswith("="):
            return formule_ok
        return f'=IF({_inv},"saisie invalide",IFERROR({formule_ok[1:]},"{err}"))'

    # LOT M 2 — les TOTAUX touchés sont bloqués eux aussi (pas seulement le résultat) : une dépense
    # négative, une TVA hors bornes qui casse le CA HT, un texte dans un coût → « saisie invalide » /
    # « non calculable », jamais un chiffre faux ou un #VALUE! visible dans la synthèse.
    ligne("Dépenses totales", d=_si_valide(f"={dep_ht}", "saisie invalide"),
          e=_si_valide(f"={dep_tva}", "saisie invalide"), f=_si_valide(f"=D{r}+E{r}", "saisie invalide"),
          gras=True)
    row_dep = r - 1
    ligne("Chiffre d'affaires", d=_si_valide(f"={cell_ca_ht}"),
          e=_si_valide(f"={cell_ca_ttc}-{cell_ca_ht}"), f=f"={cell_ca_ttc}", gras=True)
    ligne("TVA résiduelle", f=_si_valide(f"=(E{row_dep + 1}) - E{row_dep}"))  # (CA TTC-HT) - dépenses TVA
    row_res = r
    mod_row = ligne_poste["mod"]
    # CHIRURGICAL-FIX-1 (LOT H pt1 + LOT I 1a/1b) — formule VIVANTE (pas un texte figé, qui ne se
    # recalculerait pas à la saisie). Tant qu'un COÛT REQUIS manque — l'achat du terrain OU la
    # construction est à 0 — la cellule AFFICHE « non calculable… » (c'est un OU : il faut les DEUX,
    # même règle que le moteur `couts_requis`). Dès que les deux sont saisis, elle CALCULE.
    _cm = f"OR(D{ligne_poste['achat']}<=0,D{ligne_poste['constr']}<=0)"   # un coût requis manque
    # 1b — la marge ne divise JAMAIS par un CA nul (ventes à zéro) : sinon #DIV/0!. On la laisse vide.
    _ca = f"D{row_dep + 1}"
    _marge_vide = f"OR({_cm},{_ca}=0)"
    ligne("Résultat net", d=_si_valide(f'=IF({_cm},"{_NON_CALCULABLE}",{_ca}-D{row_dep})'), gras=True)
    ws.cell(row_res, 5, _si_valide(f'=IF({_marge_vide},"",D{row_res}/{_ca})')).number_format = _PCT
    ws.cell(row_res, 5).font = _GRAS
    ligne("Cash flow", d=_si_valide(f'=IF({_cm},"{_NON_CALCULABLE}",D{row_res}+D{mod_row})'))

    # ---- Haut de feuille : ratios & programme (ordre du modèle) + calendrier ----
    # Rempli ici car il référence des cellules du corps, maintenant connues.
    d = {k: ligne_poste.get(k) for k in ("constr", "aleaC", "acte", "pack", "proc")}
    ratios_tete = [
        ("Terrain", f"={cell_terrain}", _M2),
        ("Surface de plancher", f"={cell_sdp}", _M2),
        ("Surface taxable", f"={cell_stax}", _M2),
        ("Surface vendable", f"={cell_suv}", _M2),
        # CHIRURGICAL-FIX-1 (LOT J 1b) — pas de #DIV/0! quand la surface vendable est nulle (0 produit) :
        # ces ratios /m² de SUV sont vides tant que SUV = 0.
        ("Coût const. m² de surface vendable HT",
         _si_valide(f'=IF({cell_suv}=0,"",(D{d["constr"]}+D{d["aleaC"]})/{cell_suv})'), _EUR),
        # CHIRURGICAL-FIX-1 (LOT M 2) — ces 3 ratios DÉPENDENT du CA HT : si la TVA de vente est vide, le
        # CA HT est « non calculable » (texte) → le ratio l'est aussi (ISTEXT), des DEUX côtés (PDF/Excel).
        ("Prix moyen m² de surface vendable HT",
         _si_valide(f'=IF({cell_suv}=0,"",IF(ISTEXT({cell_ca_ht}),"non calculable",{cell_ca_ht}/{cell_suv}))'), _EUR),
        (
            # CHIRURGICAL-FIX-1 (LOT J 1e / LOT M 2) — le « net promoteur TTC » applique la TVA RÉELLE de
            # la vente (ratio CA TTC / CA HT), PAS la TVA DOM forfaitaire de 8,5 % (comme le moteur/PDF) :
            # un programme vendu à 0 % ne doit pas être regonflé. « non calculable » si la TVA est vide.
            "Net promoteur m² de surface vendable TTC",
            _si_valide(f'=IF({cell_suv}=0,"",IF(ISTEXT({cell_ca_ht}),"non calculable",'
                       f'(({cell_ca_ht}-D{d["acte"]}-D{d["pack"]}-D{d["proc"]})/{cell_suv})*({cell_ca_ttc}/{cell_ca_ht})))'),
            _EUR,
        ),
        ("CA TTC programme", f"={cell_ca_ttc}", _EUR),
        # CHIRURGICAL-FIX-1 (LOT H pt1 + LOT I 1b + LOT M 2) — « non calculable » si CA HT inconnu (TVA
        # vide) ; sinon vide tant qu'un coût requis manque OU que le CA HT est nul (pas de #DIV/0!).
        ("Renta nette / CA HT",
         _si_valide(f'=IF(ISTEXT({cell_ca_ht}),"non calculable",IF(OR({_cm},{cell_ca_ht}=0),"",D{row_res}/{cell_ca_ht}))'), _PCT),
        ("Nombre de lots", f"={cell_lots}", '#,##0'),
    ]
    ws.cell(3, 1, "Ratios & programme").font = _GRAS
    for i, (lib, frm, fmt) in enumerate(ratios_tete):
        rr = 4 + i
        ws.cell(rr, 1, lib)
        ws.cell(rr, 5, frm).number_format = fmt
        # CHIRURGICAL-FIX-1 (LOT M 1) — alerte VIVANTE de COHÉRENCE à côté de la surface vendable : la
        # surface vendable (habitable) ne peut PAS dépasser la surface de plancher. Doubler la SUV
        # (donc le CA) sans rapport avec la SDP déclenche désormais l'avertissement (réagit à la saisie).
        if lib == "Surface vendable":
            # LOT N 2 / LOT P / LOT Q — alerte si surface vendable > surface de plancher (DÉCIMALES, sans
            # arrondi) OU si la surface vendable est positive alors que la SDP est nulle / vide. LOT Q — le
            # message se CONSTRUIT DANS LA FORMULE à partir des DEUX cellules (surface vendable + surface de
            # plancher) : il CITE les deux valeurs (plus « aucun chiffre ») et SUIT la saisie si on modifie
            # une cellule sans régénérer (`_xl_m2`, même règle d'affichage que le PDF).
            # LOT R — comparaison AU CENTIÈME (ROUND(.,2)) des deux surfaces.
            wc = ws.cell(rr, 6, f'=IF(AND(ROUND({cell_suv},2)>0,OR(ROUND({cell_sdp},2)=0,'
                                f'ISBLANK({cell_sdp}),ROUND({cell_suv},2)>ROUND({cell_sdp},2))),'
                                f'"⚠ surface vendable ("&{_xl_m2(cell_suv)}&" m²) supérieure à la surface '
                                f'de plancher ("&{_xl_m2(cell_sdp)}&" m²) — à vérifier","")')
            wc.font = Font(bold=True, color="B45309")

    ws.cell(15, 1, "Calendrier prévisionnel").font = _GRAS
    for i, etape in enumerate(cat.calendrier):
        rr = 16 + i
        off = entrees.calendrier.get(etape["id"], etape.get("defaut"))
        txt = "" if off is None else (f"J+{off}" if off else "J")
        ws.cell(rr, 1, etape["libelle"])
        ws.cell(rr, 5, txt)

    # CHIRURGICAL-FIX-1 (LOT J 1c) — validation Excel « ≥ 0 » sur TOUTES les cellules de saisie
    # (programme, produits, coûts) : un coût/montant négatif est refusé à la main dans le tableur,
    # avec un message. (Le serveur refuse déjà les coûts négatifs à la saisie — api/bilan.py.)
    if saisie_cells:
        dv = DataValidation(type="decimal", operator="greaterThanOrEqual", formula1="0",
                            allow_blank=True, showErrorMessage=True)
        dv.errorTitle = "Saisie invalide"
        dv.error = "Une valeur de saisie (surface, coût, montant) ne peut pas être négative."
        dv.promptTitle = "Valeur ≥ 0"
        dv.prompt = "Saisissez une valeur positive ou nulle."
        ws.add_data_validation(dv)
        for coord in dict.fromkeys(saisie_cells):     # dédup, ordre stable
            dv.add(coord)

    # CHIRURGICAL-FIX-1 (LOT K 2d) — la TVA de vente est une FRACTION dans [0 %, 100 %] : on la valide à
    # part (une TVA négative ou > 100 % casse le HT). Hors bornes → refus à la saisie dans le tableur.
    if tva_cells:
        dvt = DataValidation(type="decimal", operator="between", formula1="0", formula2="1",
                             allow_blank=True, showErrorMessage=True)
        dvt.errorTitle = "TVA invalide"
        dvt.error = "La TVA de vente doit être comprise entre 0 % et 100 %."
        dvt.promptTitle = "TVA entre 0 % et 100 %"
        dvt.prompt = "Saisissez un taux entre 0 % et 100 % (ex. 8,5 %)."
        ws.add_data_validation(dvt)
        for coord in dict.fromkeys(tva_cells):
            dvt.add(coord)

    # CHIRURGICAL-FIX-1 (LOT L 3 / LOT N 1 / LOT O 1) — la cellule de VALIDITÉ unique. RÈGLE : chaque case
    # de saisie doit être VIDE **ou** un NOMBRE dans ses bornes. Un TEXTE n'est pas un nombre → invalide ;
    # un coût < 0 ou une TVA hors [0, 1] → invalide. LOT O : une VALEUR D'ERREUR Excel (#N/A, #DIV/0!,
    # #VALUE!) collée dans une case est AUSSI une saisie invalide — on enveloppe CHAQUE test d'un
    # `IFERROR(…, TRUE)` pour que l'erreur ne CONTAMINE pas la cellule de validité (en vrai Excel,
    # `#N/A < 0` propage l'erreur à travers OR/AND) : une case en erreur → invalide, jamais #N/A dans I1.
    _checks = [f'IFERROR(AND(NOT(ISBLANK({c})),OR(NOT(ISNUMBER({c})),{c}<0)),TRUE)'
               for c in dict.fromkeys(saisie_cells)]
    _checks += [f'IFERROR(AND(NOT(ISBLANK({t})),OR(NOT(ISNUMBER({t})),{t}<0,{t}>1)),TRUE)'
                for t in dict.fromkeys(tva_cells)]
    ws[cell_valid] = (f'=IF(OR({",".join(_checks)}),"saisie invalide","")' if _checks else "")
    ws[cell_valid].font = Font(color="B45309")

    # CHIRURGICAL-FIX-1 (LOT N 1 / LOT O 1) — ENVELOPPE DE VALIDITÉ sur TOUTE formule de la feuille :
    # chaque case calculée (ligne, sous-total, total, CA TTC/HT, ratio, résultat ET les alertes de
    # surface) devient `=IF(validité, "saisie invalide", …)`. Excel court-circuite le IF → quand une
    # saisie est invalide, le calcul N'EST PAS tenté (jamais de #VALUE! ni de chiffre faux) ; sur une
    # saisie valide, la cellule calcule normalement. LOT O : les ALERTES de surface sont AUSSI enveloppées
    # (une alerte ne s'affiche que sur une saisie valide ; sinon « saisie invalide », pas l'alerte à
    # tort). SEULE la cellule de validité elle-même est épargnée (elle est la source de vérité).
    _gate_prefixe = f'=IF({cell_valid}<>"",'
    for row in ws.iter_rows():
        for c in row:
            v = c.value
            if not (isinstance(v, str) and v.startswith("=")):
                continue
            if c.coordinate == cell_valid:
                continue
            if v.startswith(_gate_prefixe):     # déjà enveloppée (ratios, synthèse via _si_valide)
                continue
            c.value = f'{_gate_prefixe}"saisie invalide",{v[1:]})'

    return wb


# ── CHIRURGICAL-FIX-1 (LOT I 1c) — valeurs calculées écrites EN PLUS des formules ──────────────────
# openpyxl écrit les cellules de formule « <f>…</f><v/> » (cache VIDE) : un aperçu (Finder, téléphone,
# pièce jointe) ne recalcule pas → tout apparaît blanc. On évalue le graphe (même vocabulaire que le
# test) et on injecte la valeur dans le cache `<v>` de chaque formule. Le classeur reste VIVANT
# (`fullCalcOnLoad=1`, les formules sont intactes) ; relu SANS recalcul, il montre les mêmes chiffres
# que le moteur.
import re as _re

_SUM_RE = _re.compile(r"SUM\(([A-Z]+)(\d+):([A-Z]+)(\d+)\)")
_ISBLANK_RE = _re.compile(r"ISBLANK\(([A-Z]+\d+)\)")   # LOT M 2 — cellule VIDE (≠ 0)
_REF_RE = _re.compile(r"(?<![A-Za-z_])([A-Z]{1,3})(\d+)")
_EQ_RE = _re.compile(r"(?<![<>=!])=(?!=)")


def _iferror(a, b):
    """IFERROR(a, b) — `a` est déjà évalué ici ; une valeur NaN (div/0 propagée) → `b`."""
    return b if (isinstance(a, float) and a != a) else a


_FNS = {"IF": lambda c, a, b: a if c else b, "AND": lambda *x: all(x), "OR": lambda *x: any(x),
        "IFERROR": _iferror, "ISTEXT": lambda x: isinstance(x, str), "NOT": lambda x: not x,
        "ISNUMBER": lambda x: isinstance(x, (int, float)) and not isinstance(x, bool),
        "TRUE": True, "FALSE": False}   # LOT O 1 — littéraux booléens Excel (IFERROR(…,TRUE))


def _valeurs_calculees(ws) -> dict[str, object]:
    """Évalue toutes les cellules de formule de la feuille → {coordonnée: valeur}. Vocabulaire :
    références, `+ - * /`, parenthèses, `SUM(plage)`, `IF/AND/OR`, comparateurs. Division par zéro ou
    expression non évaluable → la cellule est laissée sans cache (aperçu vide, jamais un faux chiffre)."""
    grille = {c.coordinate: c.value for row in ws.iter_rows() for c in row if c.value is not None}
    cache: dict[str, object] = {}

    def ev(coord: str):
        if coord in cache:
            return cache[coord]
        cache[coord] = 0.0  # garde-fou anti-cycle (le bilan est acyclique)
        v = grille.get(coord)
        if v is None:
            return 0.0
        if isinstance(v, (int, float)):
            cache[coord] = float(v)
            return cache[coord]
        if not isinstance(v, str) or not v.startswith("="):
            cache[coord] = v  # libellé texte (pas une formule)
            return v
        # SUM(plage) → somme des cellules ; une plage VIDE/inversée (ex. produits=[] → SUM(F5:F4))
        # vaut 0 (comme Excel), jamais « () ».
        expr = _SUM_RE.sub(
            lambda m: "(" + ("+".join(f"{m.group(1)}{r}" for r in range(int(m.group(2)), int(m.group(4)) + 1)) or "0") + ")",
            v[1:])
        # LOT M 2 — ISBLANK(ref) AVANT la substitution des références : une cellule absente de la grille
        # (valeur None → ex. TVA non saisie) est VIDE ; une cellule présente ne l'est pas.
        expr = _ISBLANK_RE.sub(lambda m: repr(grille.get(m.group(1)) in (None, "")), expr)
        expr = _REF_RE.sub(lambda m: repr(ev(f"{m.group(1)}{m.group(2)}")), expr)
        expr = expr.replace("<>", "!=")       # LOT L 3 — « différent de » Excel → Python (avant « = »→« == »)
        expr = _EQ_RE.sub("==", expr)
        try:
            raw = eval(expr, {"__builtins__": {}}, dict(_FNS))  # noqa: S307 — vocabulaire contrôlé
            val = float(raw) if isinstance(raw, (int, float, bool)) else raw
        except Exception:  # noqa: BLE001 — div/0, ref vide… → pas de cache
            val = None
        cache[coord] = val
        return val

    return {coord: ev(coord) for coord, v in grille.items() if isinstance(v, str) and v.startswith("=")}


_CELL_RE = _re.compile(
    r'(?P<open><c r="(?P<r>[A-Z]+\d+)"(?P<attrs>[^>]*)>)(?P<f><f>.*?</f>)<v\s*/>(?P<close></c>)')


def _injecter_valeurs(octets: bytes, vals: dict[str, object]) -> bytes:
    import io
    import zipfile
    from xml.sax.saxutils import escape

    def _repl(m):
        coord = m.group("r")
        val = vals.get(coord)
        if val is None or (isinstance(val, float) and (val != val or val in (float("inf"), float("-inf")))):
            return m.group(0)
        if isinstance(val, bool):
            val = 1 if val else 0
        if isinstance(val, (int, float)):
            return f'{m.group("open")}{m.group("f")}<v>{val!r}</v>{m.group("close")}'
        attrs = m.group("attrs")
        open_tag = m.group("open") if 't="' in attrs else f'<c r="{coord}"{attrs} t="str">'
        return f'{open_tag}{m.group("f")}<v>{escape(str(val))}</v>{m.group("close")}'

    zin = zipfile.ZipFile(io.BytesIO(octets))
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "xl/worksheets/sheet1.xml":
                data = _CELL_RE.sub(_repl, data.decode("utf-8")).encode("utf-8")
            zout.writestr(item, data)
    return out.getvalue()


def classeur_bilan_bytes(entrees: EntreesBilan, **kw: Any) -> bytes:
    import io

    wb = classeur_bilan(entrees, **kw)
    vals = _valeurs_calculees(wb.active)       # LOT I 1c — cache des valeurs (aperçu non vide)
    buf = io.BytesIO()
    wb.save(buf)
    return _injecter_valeurs(buf.getvalue(), vals)
