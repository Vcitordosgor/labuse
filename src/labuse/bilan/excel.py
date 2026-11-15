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

from .catalogue import Catalogue, assiette_unite, charger_catalogue
from .moteur import EntreesBilan

# CHIRURGICAL-FIX-1 (LOT H pt1) — même texte que le PDF (bilan/pdf.py) quand un coût requis manque :
# le classeur ne doit PAS afficher un résultat (= CA), 100 % de marge et un cash-flow calculés par
# des FORMULES Excel qui recalculent « dépenses vides = 0 ». Il gèle ces lignes comme le PDF.
_NON_CALCULABLE = "non calculable — saisissez vos coûts"

_EUR = '#,##0 €'
_PCT = '0.0 %'   # DOCS-1 : les taux (TVA, marge) s'affichent « 8,5 % », jamais « 0.085 » ni « 8,50 % »
_M2 = '#,##0 "m²"'
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
    ws.cell(r, 1, "Loyer (€/m² de surface vendable)")
    ws.cell(r, 2, entrees.programme.loyer)
    r += 2

    # ---- Produits ----
    entete("Produits")
    hdr = ["Produit", "Lots", "surface vendable (m²)", "Prix TTC/m²", "TVA", "CA TTC", "CA HT"]
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
                ws.cell(rr, 2, s.assiette_valeur).number_format = _assiette_fmt(poste)
            elif aref:
                ws.cell(rr, 2, aref).number_format = _assiette_fmt(poste)
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
    mod_row = ligne_poste["mod"]
    # CHIRURGICAL-FIX-1 (LOT H pt1 + LOT I 1a/1b) — formule VIVANTE (pas un texte figé, qui ne se
    # recalculerait pas à la saisie). Tant qu'un COÛT REQUIS manque — l'achat du terrain OU la
    # construction est à 0 — la cellule AFFICHE « non calculable… » (c'est un OU : il faut les DEUX,
    # même règle que le moteur `couts_requis`). Dès que les deux sont saisis, elle CALCULE.
    _cm = f"OR(D{ligne_poste['achat']}<=0,D{ligne_poste['constr']}<=0)"   # un coût requis manque
    # 1b — la marge ne divise JAMAIS par un CA nul (ventes à zéro) : sinon #DIV/0!. On la laisse vide.
    _ca = f"D{row_dep + 1}"
    _marge_vide = f"OR({_cm},{_ca}=0)"
    ligne("Résultat net", d=f'=IF({_cm},"{_NON_CALCULABLE}",{_ca}-D{row_dep})', gras=True)
    ws.cell(row_res, 5, f'=IF({_marge_vide},"",D{row_res}/{_ca})').number_format = _PCT  # marge % du CA HT
    ws.cell(row_res, 5).font = _GRAS
    ligne("Cash flow", d=f'=IF({_cm},"{_NON_CALCULABLE}",D{row_res}+D{mod_row})')

    # ---- Haut de feuille : ratios & programme (ordre du modèle) + calendrier ----
    # Rempli ici car il référence des cellules du corps, maintenant connues.
    d = {k: ligne_poste.get(k) for k in ("constr", "aleaC", "acte", "pack", "proc")}
    ratios_tete = [
        ("Terrain", f"={cell_terrain}", _M2),
        ("Surface de plancher", f"={cell_sdp}", _M2),
        ("Surface taxable", f"={cell_stax}", _M2),
        ("Surface vendable", f"={cell_suv}", _M2),
        ("Coût const. m² de surface vendable HT", f"=(D{d['constr']}+D{d['aleaC']})/{cell_suv}", _EUR),
        ("Prix moyen m² de surface vendable HT", f"={cell_ca_ht}/{cell_suv}", _EUR),
        (
            "Net promoteur m² de surface vendable TTC",
            f"=(({cell_ca_ht}-D{d['acte']}-D{d['pack']}-D{d['proc']})/{cell_suv})*(1+{tva_dom})",
            _EUR,
        ),
        ("CA TTC programme", f"={cell_ca_ttc}", _EUR),
        # CHIRURGICAL-FIX-1 (LOT H pt1 + LOT I 1b) — même garde VIVANTE : vide tant qu'un coût requis
        # manque (D{row_res} porte alors le texte « non calculable ») OU quand le CA HT est nul (pas de
        # #DIV/0!), calculée dès que les deux coûts sont saisis et qu'il y a du CA.
        ("Renta nette / CA HT", f'=IF(OR({_cm},{cell_ca_ht}=0),"",D{row_res}/{cell_ca_ht})', _PCT),
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


# ── CHIRURGICAL-FIX-1 (LOT I 1c) — valeurs calculées écrites EN PLUS des formules ──────────────────
# openpyxl écrit les cellules de formule « <f>…</f><v/> » (cache VIDE) : un aperçu (Finder, téléphone,
# pièce jointe) ne recalcule pas → tout apparaît blanc. On évalue le graphe (même vocabulaire que le
# test) et on injecte la valeur dans le cache `<v>` de chaque formule. Le classeur reste VIVANT
# (`fullCalcOnLoad=1`, les formules sont intactes) ; relu SANS recalcul, il montre les mêmes chiffres
# que le moteur.
import re as _re

_SUM_RE = _re.compile(r"SUM\(([A-Z]+)(\d+):([A-Z]+)(\d+)\)")
_REF_RE = _re.compile(r"(?<![A-Za-z_])([A-Z]{1,3})(\d+)")
_EQ_RE = _re.compile(r"(?<![<>=!])=(?!=)")
_FNS = {"IF": lambda c, a, b: a if c else b, "AND": lambda *x: all(x), "OR": lambda *x: any(x)}


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
        expr = _REF_RE.sub(lambda m: repr(ev(f"{m.group(1)}{m.group(2)}")), expr)
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
