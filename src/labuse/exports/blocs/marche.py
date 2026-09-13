"""Bloc « 5. Marché et prix ». Prix du secteur (point d'appel unique), nuage des ventes retenues
+ écartées, médianes du secteur cadastral (indicateur secondaire étiqueté). Un seul prix ancien,
pas de VEFA à l'acte en fiche (Q3) ; étiquette immeuble jamais confondue avec appartement (Q8)."""
from __future__ import annotations

from ..lignes import a, pied, val
from ..nature import chip
from ..registre_fmt import fmt_eur, fmt_eur_m2, groupe
from ..rendu import chip_span, esc, ligne_kv, note, section, table_kv, tuiles

IDS = ("prix_sortie_bati_eur_m2", "prix_terrain_secteur_eur_m2", "ventes_retenues_n",
       "ventes_ecartees_n", "dvf_parcelle_liste", "n_permis_proximite")


def _tuiles(valeurs) -> str:
    items = []
    pa = val(valeurs, "prix_sortie_bati_eur_m2")
    if isinstance(pa, dict) and pa.get("median"):
        n, r = pa.get("n"), pa.get("radius_m")
        lib = f"ancien, {pa.get('type_prix') or 'bâti'}"
        if n:
            lib += f" — {n} ventes"
        if r:
            lib += f" à moins de {int(r)} m"
        items.append((fmt_eur_m2(pa["median"]), lib))
    tn = val(valeurs, "prix_terrain_secteur_eur_m2")
    if isinstance(tn, dict) and tn.get("prix_m2"):
        items.append((fmt_eur_m2(tn["prix_m2"]), tn.get("libelle") or "terrain nu — secteur"))
    return tuiles(items) if items else ""


def _nuage(pa: dict) -> str:
    pts = pa.get("prix_points") or []
    med, lo, hi = pa.get("median"), pa.get("min"), pa.get("max")
    if not pts or lo is None or hi is None or hi <= lo:
        return ""
    pos = lambda v: max(0, min(100, round((v - lo) / (hi - lo) * 100, 1)))  # noqa: E731
    dots = "".join(f'<div class="dot" style="left:{pos(v)}%"></div>' for v in pts if lo <= v <= hi)
    medh = f'<div class="med" style="left:{pos(med)}%"></div>' if med else ""
    # RECETTE-7 (E6) — les trois valeurs PORTENT leur libellé (min / médiane / max) : on annonçait
    # « les ventes retenues » et on n'imprimait que trois nombres nus.
    lab = (f'<div class="lab"><span>min {fmt_eur_m2(lo)}</span>'
           f'<span>médiane {fmt_eur_m2(med)}</span><span>max {fmt_eur_m2(hi)}</span></div>')
    n, nex = pa.get("n"), pa.get("n_exclus")
    leg = (f'<p class="legend">{n or "?"} ventes retenues'
           + (f", {nex} écartées" if nex else "") + '. Aucune vente n\'est fabriquée ni lissée.</p>')
    return f'<div class="cloud"><div class="axis">{dots}{medh}</div>{lab}{leg}</div>'


def _secteur(valeurs) -> str:
    liste = val(valeurs, "dvf_parcelle_liste") or []
    lignes = []
    for r in liste:
        if not isinstance(r, dict) or not r.get("mediane_prix_m2"):
            continue
        lignes.append(ligne_kv(
            (r.get("type_bien") or "bien").capitalize(),
            esc(f"{groupe(r['mediane_prix_m2'])} €/m² — {r.get('n_ventes', '?')} ventes, "
                f"{r.get('fenetre', 'secteur cadastral')}"),
            chip_span("s", "sourcé")))
    if not lignes:
        return ""
    return ("<h3>Médianes du secteur cadastral (indicateur secondaire)</h3>" + table_kv(lignes))


def rendu(valeurs) -> str:
    data = _tuiles(valeurs)
    pa = val(valeurs, "prix_sortie_bati_eur_m2")
    lignes = []
    tn = val(valeurs, "prix_terrain_secteur_eur_m2")
    if isinstance(tn, dict) and tn.get("valeur_eur"):
        lignes.append(ligne_kv("Terrain nu au prix du secteur",
                               esc(f"{fmt_eur(tn['valeur_eur'])} ({groupe(tn['prix_m2'])} €/m² × "
                                   f"{tn.get('surface_m2', '?')} m²)"), chip_span("d", "dérivé")))
    if isinstance(pa, dict) and pa.get("tendance_pct") is not None:
        sens = pa.get("tendance") or ""
        # RECETTE-11 D6 — la période était rendue en repr de liste Python (« [2022, 2025] ») ; on
        # l'écrit « 2022–2025 » (jamais un [ ] au client).
        per = pa.get("periode", "")
        if isinstance(per, (list, tuple)) and len(per) == 2:
            per = f"{per[0]}–{per[1]}"
        lignes.append(ligne_kv("Tendance du secteur",
                               esc(f"{'+' if sens == 'hausse' else ''}{pa['tendance_pct']} % "
                                   f"({sens}) sur la période {per}"),
                               chip_span("s", "sourcé")))
    if a(valeurs, "n_permis_proximite"):
        nc = valeurs["n_permis_proximite"].valeur
        n = nc.get("n") if isinstance(nc, dict) else nc
        # RECETTE-12 D1 — la définition arbitrée (Q7, 05/09) : RAYON 500 m · fenêtre 24 mois, RAYON et
        # FENÊTRE écrits (avant : « section cadastrale, 36 mois »). Repli « section cadastrale » si un
        # ancien profil sans rayon est servi.
        rayon = nc.get("rayon_m") if isinstance(nc, dict) else None
        maille = (nc.get("maille") if isinstance(nc, dict) else None) or "section cadastrale"
        fen = nc.get("fenetre_mois") if isinstance(nc, dict) else None
        ou = f"dans un rayon de {int(rayon)} m" if rayon else f"sur la {esc(maille)}"
        detail = f"{n} permis autorisés {ou}" + (f", sur les {int(fen)} derniers mois" if fen else "")
        lignes.append(ligne_kv("Activité de dépôt (permis, secteur)", detail,
                               chip(valeurs["n_permis_proximite"])))
    if lignes:
        data += table_kv(lignes)
    if isinstance(pa, dict):
        nu = _nuage(pa)
        if nu:
            # RECETTE-8 W17 — titre HONNÊTE : on n'imprime pas la liste ligne à ligne des ventes,
            # on montre leur DISTRIBUTION (un point par vente, min/médiane/max repérés). « une à une »
            # annonçait une liste qui n'existe pas.
            data += "<h3>Les ventes retenues — distribution des prix au m² (un point par vente)</h3>" + nu
    data += _secteur(valeurs)
    if not data.strip():
        return ""      # aucun prix/vente servi → section omise
    note_txt = ("Ventes publiées (DVF), anonymisées ; les ventes récentes mettent un à "
                "trois ans à apparaître.")
    # RECETTE-11 D2 — dire POURQUOI le prix « ancien {type} » : c'est le comparable de revente
    # DOMINANT du secteur pour ce type (segment retenu par le rayon adaptatif), servi comme prix de
    # sortie du programme reconstruit — jamais une estimation du bâti actuellement sur la parcelle
    # (un terrain de trois maisons se reconstruit en collectif → l'appartement est le comparable).
    if isinstance(pa, dict) and pa.get("type_prix"):
        note_txt += (f" Le prix « ancien {esc(pa['type_prix'])} » est la référence de revente du "
                     "secteur pour ce type de bien (segment le plus représenté à proximité), utilisée "
                     "comme prix de sortie du programme reconstruit — pas une estimation du bâti existant.")
    corps = data + note(note_txt) + pied(valeurs, IDS)
    return section("5. Marché et prix", corps)
