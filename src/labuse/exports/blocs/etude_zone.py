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
        lignes.append(_kv("Revenu médian", f"{_i(p.get('revenu_median_eur'))} €{suff}"))
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
    if m.get("ventes_12m") is not None:
        lignes.append(_kv("Ventes (12 mois)", f"{_i(m.get('ventes_12m'))}"))
    if m.get("prix_m2_median_bati") is not None:
        lignes.append(_kv("Prix médian du bâti", f"{_i(m.get('prix_m2_median_bati'))} €/m²"))
    if m.get("annonces_actives") is not None:
        lignes.append(_kv("Annonces actives", f"{_i(m.get('annonces_actives'))}"))
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
    # RECETTE-OUTILS-3 (S3) — activité choisie : le menu « Activité » MODIFIE la lecture (verdict de la
    # sous-destination par zone PLU), le PDF l'affiche comme l'outil (autorisé / sous condition / …).
    dest = z.get("destinations") or {}
    if dest.get("sous_destination"):
        if dest.get("erreur"):
            lignes.append(_kv("Activité étudiée", esc(dest.get("erreur"))))
        else:
            lignes.append(_kv("Activité étudiée",
                              f'<b>{esc(dest.get("libelle") or dest["sous_destination"])}</b>'))
            for zn in (dest.get("zones") or []):
                etat = zn.get("etat") or zn.get("statut") or ""
                z_lbl = esc(zn.get("zone") or "") + (f" · {esc(zn.get('commune'))}" if zn.get("commune") else "")
                val = _ETAT_LABEL.get(etat, esc(etat))
                if zn.get("condition"):
                    val += f' <span class="muted">— {esc(zn.get("condition"))}</span>'
                lignes.append(_kv(z_lbl, val))
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
    lignes = []
    for d in doms:
        n = int(d.get("n") or 0)
        label = d.get("label") or d.get("domaine") or "Équipements"
        # en-tête de catégorie : libellé + compte
        lignes.append(_kv(label, f'<b>{n} établissement{"s" if n > 1 else ""}</b>'))
        for x in (d.get("liste") or []):
            nom = x.get("nom") or "Établissement (nom non renseigné)"
            typ = x.get("type") or ""
            # une ligne par établissement : nom · type (type en gris discret)
            lignes.append(_kv("", f'{esc(nom)} <span class="muted">· {esc(typ)}</span>'))
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


def rendu(zone, *, map_html: str, idu: str, rayon_km) -> str:
    z = zone or {}
    corps = map_html
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
    # CHASSE-DOCS-FIX-1 (E-14) — la note servie finit déjà par « . » ; on la débarrasse de sa ponctuation
    # finale avant d'ajouter « . » + le rappel, sinon « …chiffre d'affaires.. Les mailles ».
    _note_servie = (z.get("note") or "").strip().rstrip(".")
    _rappel = ("Les mailles « " + ECHELLE_COMMUNE + " » portent sur toute la commune, pas sur le seul rayon.")
    corps += note((f"Sources : {_note_servie}. {_rappel}" if _note_servie
                   else "Agrégats de sources publiques dans le périmètre. " + _rappel))
    return section("Étude de zone", corps)
