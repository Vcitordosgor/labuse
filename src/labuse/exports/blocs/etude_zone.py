"""DOCS-1 (Lot C) — bloc « Étude de zone » : page 1 = carte du périmètre (parcelle + cercle du rayon)
+ « Rayon N km autour de <IDU> », puis les 7 sections dans l'ordre de l'outil (Population · Économie ·
Immobilier · Foncier · Contraintes · Équipements · Dynamique). Aucun recalcul : on rend le résultat
servi par /outils/etude-zone en mode rayon. Les mailles commune sont libellées « à l'échelle de la
commune » comme à l'écran."""
from __future__ import annotations

from ..registre_fmt import groupe
from ..rendu import esc, note, section, table_kv

ECHELLE_COMMUNE = "à l'échelle de la commune"


def _i(v):
    return groupe(round(v)) if isinstance(v, (int, float)) else None


def _kv(cle, valeur_html):
    return f'<tr><td class="k">{esc(cle)}</td><td>{valeur_html}</td><td class="n"></td></tr>'


def _sec(titre: str, lignes: list[str]) -> str:
    lignes = [x for x in lignes if x]
    if not lignes:
        return ""
    return f"<h3>{esc(titre)}</h3>" + table_kv(lignes)


def _population(z) -> str:
    p = z.get("population") or {}
    if p.get("inhabitee"):
        return _sec("Population", [_kv("Population", "zone inhabitée (aucun carreau peuplé)")])
    lignes = []
    if _i(p.get("habitants")):
        lignes.append(_kv("Habitants", f"{_i(p.get('habitants'))}"))
    if _i(p.get("menages")):
        lignes.append(_kv("Ménages", f"{_i(p.get('menages'))}"))
    if p.get("revenu_median_eur") is not None:
        suff = " (estimé)" if p.get("revenu_estime") else ""
        # NU-C-002 — le chiffre est sum(ind_snv)/sum(ind) = niveau de vie MOYEN par individu, ni
        # médian ni un revenu. Le libellé PDF s'aligne sur l'écran (EtudeZone.tsx:243).
        lignes.append(_kv("Niveau de vie moyen / an", f"{_i(p.get('revenu_median_eur'))} €{suff}"))
    if p.get("pct_moins_25") is not None:
        lignes.append(_kv("Moins de 25 ans", f"{_i(p.get('pct_moins_25'))} %"))
    if p.get("taux_pauvrete_pct") is not None:
        lignes.append(_kv("Taux de pauvreté", f"{_i(p.get('taux_pauvrete_pct'))} %"))
    return _sec("Population", lignes)


def _economie(z) -> str:
    e = z.get("emplois") or {}
    lignes = []
    # CHASSE-DOCS-FIX-1 (E-10) — la FOURCHETTE d'abord : `libelle` (toujours posé par zone.py, sans
    # le nombre) ne doit pas court-circuiter `postes_min/max` ; il n'en est que le SUFFIXE (comme le Flash).
    if e.get("postes_min") is not None:
        val = f"{_i(e.get('postes_min'))} à {_i(e.get('postes_max'))}"
        if e.get("libelle"):
            val += " " + esc(e["libelle"])
        lignes.append(_kv("Emplois salariés", val))
    elif e.get("libelle"):
        lignes.append(_kv("Emplois salariés", esc(e.get("libelle"))))
    if _i(e.get("n_etablissements")):
        lignes.append(_kv("Établissements", f"{_i(e.get('n_etablissements'))}"))
    conc = z.get("concurrents") or {}
    if conc.get("n") is not None and conc.get("couverture") == "servie":
        lignes.append(_kv("Concurrents (NAF)", f"{_i(conc.get('n'))}"))
    return _sec("Économie", lignes)


def _immobilier(z) -> str:
    m = z.get("marche") or {}
    lignes = []
    # OUTILS-P0-2 (P3, revue Astra) — « Prix médian du bâti dans le cercle » = le prix calculé DANS LE
    # PÉRIMÈTRE DESSINÉ (`prix_m2_median_bati`), avec son effectif et sa période. Le prix du secteur de
    # la fiche (`prix_secteur_fiche`) est un AUTRE périmètre : servi À PART, avec son rayon réel. Même
    # périmètre, même prix, même effectif que l'écran.
    if m.get("prix_m2_median_bati") is not None:
        # OUTILS-P0-2 (recette) — la période du cercle est la FENÊTRE DEMANDÉE (36 mois), pas les dates
        # extrêmes des ventes trouvées.
        n, fen = m.get("prix_m2_median_n"), m.get("prix_m2_median_fenetre_mois")
        bouts = []
        if n:
            bouts.append(f"{_i(n)} ventes")
        if fen:
            bouts.append(f"{_i(fen)} mois")
        suff = f" — {', '.join(bouts)}" if bouts else ""
        lignes.append(_kv("Prix médian du bâti dans le cercle", f"{_i(m['prix_m2_median_bati'])} €/m²{suff}"))
    if m.get("ventes_12m") is not None:
        lignes.append(_kv("Ventes (12 mois)", f"{_i(m.get('ventes_12m'))}"))
    # OUTILS-P0-2 (recette) — le SECTEUR de la fiche DIT ce qu'il mesure : type + fenêtre (années) +
    # effectif ; AUTRE périmètre (rayon adaptatif de la fiche), affiché à part.
    pa = m.get("prix_secteur_fiche") or {}
    if pa.get("median"):
        n, r = pa.get("n"), pa.get("radius_m")
        tp = pa.get("type_prix")
        type_lbl = ("maisons" if tp == "maison" else "appartements" if tp == "appartement"
                    else "maisons et appartements" if (tp or "").startswith("mixte") else None)
        per = pa.get("periode")
        annees = (f"{per[0]}–{per[1]}" if (isinstance(per, (list, tuple)) and len(per) == 2 and per[0] and per[1] != per[0])
                  else (f"{per[0]}" if (isinstance(per, (list, tuple)) and per and per[0]) else None))
        cle = ", ".join(x for x in ("Secteur de la fiche", type_lbl, annees) if x)
        if pa.get("commune_fallback"):
            suff = f" — {_i(n)} ventes (commune entière)" if n else " (commune entière)"
        else:
            suff = (f" — {_i(n)} ventes à moins de {_i(r)} m" if n and r
                    else (f" — {_i(n)} ventes" if n else ""))
        lignes.append(_kv(cle, f"{_i(pa['median'])} €/m²{suff}"))
    if m.get("annonces_actives") is not None:
        lignes.append(_kv("Annonces suivies par LABUSE", f"{_i(m.get('annonces_actives'))}"))
    if m.get("permis_36m") is not None:
        lignes.append(_kv("Permis (36 mois)", f"{_i(m.get('permis_36m'))}"))
    return _sec("Immobilier", lignes)


def _foncier(z) -> str:
    pm = z.get("proprietaires_pm") or {}
    lignes = []
    # CHASSE-FIX-1 (C39) — le producteur sert `proprietaires` (zone.py:709) : les clés
    # top/items ne s'imprimaient JAMAIS (section morte depuis DOCS-1).
    top = pm.get("proprietaires") or pm.get("top") or pm.get("items") or []
    for o in (top[:5] if isinstance(top, list) else []):
        nom = o.get("denomination") or o.get("nom")
        surf = _i(o.get("surface_m2"))
        if nom:
            # DOCS-COHERENCE-1 (E1) — `_kv` échappe déjà sa clé ; pré-échapper ici double l'échappement
            # (« D'AMENAGEMENT » → « D&#x27;AMENAGEMENT » affiché littéralement). On passe le nom BRUT.
            lignes.append(_kv(nom, f"{surf} m²" if surf else ""))
    zd = z.get("zone_demain") or {}
    if zd.get("logements_autorises_36m") is not None:
        lignes.append(_kv("Logements autorisés (36 mois)", f"{_i(zd.get('logements_autorises_36m'))}"))
    if zd.get("au_zones_ha") is not None:
        lignes.append(_kv("Zones AU", f"{_i(zd.get('au_zones_n'))} · {_i(zd.get('au_zones_ha'))} ha"))
    return _sec("Foncier", lignes)


_ETAT_LABEL = {"autorise": "autorisé", "sous_condition": "sous condition", "interdit": "interdit",
               "en_cours_de_calibration": "en calibration", "non_lu": "en calibration"}


def _contraintes(z) -> str:
    lignes = []
    cp = z.get("contraintes_plu") or {}
    for zn in (cp.get("zones") or [])[:8]:
        zone = zn.get("zone")
        part = _i(zn.get("part_pct"))
        commune = zn.get("commune")
        if zone:
            val = f"{part} %" if part is not None else ""
            lignes.append(_kv(f"{zone}" + (f" · {commune}" if commune else ""), val))   # E1 — _kv échappe déjà
    # RECETTE-4 — le menu « Activité (destination) » est retiré de l'Étude de zone : plus de bloc
    # « Activité étudiée » (verdict de sous-destination par zone PLU) dans le PDF.
    risq = z.get("risques") or {}
    if risq.get("libelle"):
        lignes.append(_kv("Risques", esc(risq.get("libelle"))))
    assa = z.get("assainissement") or {}
    if assa.get("libelle"):
        lignes.append(_kv("Assainissement", esc(assa.get("libelle"))))
    return _sec("Zonage PLU dans le rayon", lignes)   # DOCS-COHERENCE-1 (E4) — ce bloc liste le zonage PLU, pas des contraintes


def _equipements(z) -> str:
    # RECETTE-OUTILS-3 (S2) — pour CHAQUE catégorie BPE : le NOMBRE d'établissements dans le rayon,
    # puis la LISTE COMPLÈTE (nom · type), plus seulement le plus proche. La table se répartit sur
    # plusieurs pages si besoin (WeasyPrint). On lit `bpe.domaines` (compte + liste), pas le flat
    # `equipements` (un par domaine) qui ne servait qu'au mini-aperçu.
    doms = (z.get("bpe") or {}).get("domaines") or []
    if not doms:
        return ""
    # NU5-FIX-1 (B-F5) — la liste nominative de TOUS les établissements d'une commune dense rendait
    # 36 pages (chaque commerce nommé). On BORNE chaque catégorie aux plus proches (top-N) et on
    # ANNONCE le reste (« + N autres »), au lieu d'une énumération exhaustive peu exploitable.
    _MAX_PAR_CAT = 8
    lignes = []
    for d in doms:
        n = int(d.get("n") or 0)
        label = d.get("label") or d.get("domaine") or "Équipements"
        # en-tête de catégorie : libellé + compte
        lignes.append(_kv(label, f'<b>{n} établissement{"s" if n > 1 else ""}</b>'))
        liste = d.get("liste") or []
        for x in liste[:_MAX_PAR_CAT]:
            nom = x.get("nom") or "Établissement (nom non renseigné)"
            typ = x.get("type") or ""
            # une ligne par établissement : nom · type (type en gris discret)
            lignes.append(_kv("", f'{esc(nom)} <span class="muted">· {esc(typ)}</span>'))
        if len(liste) > _MAX_PAR_CAT:
            # NU5-FIX-1 (B-F5) — on NE RÉIMPRIME PAS de nombre ici (le total est déjà la ligne
            # d'en-tête de la catégorie, seul chiffre sourcé) : « verrou écran=PDF » refuse tout
            # nombre imprimé hors registre. On dit seulement que la liste est bornée aux plus proches.
            lignes.append(_kv("", f'<span class="muted">seuls les {_MAX_PAR_CAT} plus proches sont '
                                  f'listés (total ci-dessus)</span>'))
    return _sec("Équipements", lignes)


def _dynamique(z) -> str:
    lignes = []
    acq = z.get("acquisitions_pm") or {}
    # CHASSE-FIX-1 (C39) — la clé servie est n_parcelles (zone.py:878), `n` ne s'imprimait jamais.
    _n_acq = acq.get("n_parcelles") if acq.get("n_parcelles") is not None else acq.get("n")
    if _n_acq is not None:
        lignes.append(_kv("Acquisitions récentes (personnes morales)", f"{_i(_n_acq)}"))
    cc = z.get("commune_contexte") or {}
    # maille commune : libellée « à l'échelle de la commune » comme à l'écran.
    if cc.get("loyer_median_eur_m2") is not None:
        lignes.append(_kv(f"Loyer médian ({ECHELLE_COMMUNE})", f"{_i(cc.get('loyer_median_eur_m2'))} €/m²"))
    tr = z.get("trafic") or {}
    for ax in (tr.get("axes") or [])[:3]:
        if ax.get("tmja") is not None:
            lignes.append(_kv(f"Trafic {esc(ax.get('route') or '')}", f"{_i(ax.get('tmja'))} véh./j"))
    return _sec("Dynamique", lignes)


def _echelle_label(z: dict, idu: str, rayon_km) -> str:
    """CHASSE-DONNEES-FIX-1 (Lot 7, E-69) — le périmètre IMPRIMÉ = celui RÉELLEMENT calculé (lu de
    `zone`), plus le rayon DEMANDÉ : un rayon hors {0,5 ; 1 ; 2 ; 5} km retombe sur l'isochrone 10
    min voiture, et le document affichait quand même « Rayon 10 km »."""
    if z.get("entree") == "rayon" and z.get("rayon_km"):
        return f"Rayon {esc(str(z['rayon_km']))} km autour de {esc(idu)}"
    mins, mode = z.get("isochrone_minutes"), z.get("isochrone_mode")
    if mins:
        return f"Isochrone {esc(str(mins))} min ({esc(str(mode or 'voiture'))}) autour de {esc(idu)}"
    if z.get("entree") == "polygone":
        return f"Périmètre dessiné autour de {esc(idu)}"
    # repli : le rayon demandé s'il a été retenu, sinon libellé neutre (jamais un rayon non calculé)
    return (f"Rayon {esc(str(rayon_km))} km autour de {esc(idu)}" if rayon_km
            else f"Périmètre autour de {esc(idu)}")


def _tuiles(z, rayon_km) -> str:
    """DOCS-1 (décision Vic) — la RANGÉE DE TUILES de tête de l'Étude de zone (comme le Dossier et
    Estimer), qui manquait : périmètre, habitants, revenu médian, prix médian bâti, ventes 12 mois."""
    t: list[str] = []

    def tile(v, lib):
        if v:
            t.append(f'<div class="tile"><div class="v">{v}</div><div class="l">{esc(lib)}</div></div>')

    sa = z.get("surface_ha")
    tile(f"{_i(sa)} ha" if sa else (f"{_i(rayon_km)} km" if rayon_km else None), "Périmètre")
    p = z.get("population") or {}
    tile(_i(p.get("habitants")), "Habitants")
    rm = p.get("revenu_median_eur")
    tile(f"{_i(rm)} €" if rm is not None else None, "Revenu médian / an")
    m = z.get("marche") or {}
    pa = (m.get("prix_ancien") or {}).get("median") or m.get("prix_m2_median_bati")
    tile(f"{_i(pa)} €/m²" if pa else None, "Prix médian bâti")
    v12 = m.get("ventes_12m")
    tile(_i(v12) if v12 is not None else None, "Ventes 12 mois")
    return f'<div class="tiles">{"".join(t[:5])}</div>' if t else ""


def rendu(zone, *, map_html: str, idu: str, rayon_km) -> str:
    z = zone or {}
    corps = map_html
    corps += _tuiles(z, rayon_km)
    corps += f'<p class="zone-echelle">{_echelle_label(z, idu, rayon_km)}'
    sa = z.get("surface_ha")
    if sa:
        corps += f" · {_i(sa)} ha"
    corps += "</p>"
    corps += (_population(z) + _economie(z) + _immobilier(z) + _foncier(z)
              + _contraintes(z) + _equipements(z) + _dynamique(z))
    # CHASSE-DONNEES-FIX-1 (suite 2d, C-42) — la note RELAIE les sources DATÉES servies (zone['note'] :
    # « INSEE Filosofi 2021 · SIRENE · BPE 2025 · DVF · isochrones IGN · Arcep… »), plus une note
    # statique muette : les millésimes calculés côté outil s'impriment enfin dans le PDF.
    # DOCS-DA-1 (V10) — plus de ligne « Sources : » sous la section (comme le Dossier) ; on garde la
    # seule mise en garde d'ÉCHELLE (les mailles communales ne portent pas sur le seul rayon).
    _rappel = ("Les mailles « " + ECHELLE_COMMUNE + " » portent sur toute la commune, pas sur le seul rayon.")
    corps += note(_rappel)
    return section("Étude de zone", corps)
