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
    if e.get("libelle"):
        lignes.append(_kv("Emplois salariés", esc(e.get("libelle"))))
    elif e.get("postes_min") is not None:
        lignes.append(_kv("Emplois salariés", f"{_i(e.get('postes_min'))} à {_i(e.get('postes_max'))}"))
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
    top = pm.get("top") or pm.get("items") or []
    for o in (top[:5] if isinstance(top, list) else []):
        nom = o.get("denomination") or o.get("nom")
        surf = _i(o.get("surface_m2"))
        if nom:
            lignes.append(_kv(esc(nom), f"{surf} m²" if surf else ""))
    zd = z.get("zone_demain") or {}
    if zd.get("logements_autorises_36m") is not None:
        lignes.append(_kv("Logements autorisés (36 mois)", f"{_i(zd.get('logements_autorises_36m'))}"))
    if zd.get("au_zones_ha") is not None:
        lignes.append(_kv("Zones AU", f"{_i(zd.get('au_zones_n'))} · {_i(zd.get('au_zones_ha'))} ha"))
    return _sec("Foncier", lignes)


def _contraintes(z) -> str:
    lignes = []
    cp = z.get("contraintes_plu") or {}
    for zn in (cp.get("zones") or [])[:8]:
        zone = zn.get("zone")
        part = _i(zn.get("part_pct"))
        commune = zn.get("commune")
        if zone:
            val = f"{part} %" if part is not None else ""
            lignes.append(_kv(f"{esc(zone)}" + (f" · {esc(commune)}" if commune else ""), val))
    risq = z.get("risques") or {}
    if risq.get("libelle"):
        lignes.append(_kv("Risques", esc(risq.get("libelle"))))
    assa = z.get("assainissement") or {}
    if assa.get("libelle"):
        lignes.append(_kv("Assainissement", esc(assa.get("libelle"))))
    return _sec("Contraintes", lignes)


def _equipements(z) -> str:
    lignes = []
    for eq in (z.get("equipements") or [])[:10]:
        nom, dom = eq.get("nom"), eq.get("domaine")
        t = eq.get("temps_min")
        if nom:
            suff = f" · {int(t)} min" if isinstance(t, (int, float)) else ""
            lignes.append(_kv(esc(dom or "Équipement"), f"{esc(nom)}{suff}"))
    return _sec("Équipements", lignes)


def _dynamique(z) -> str:
    lignes = []
    acq = z.get("acquisitions_pm") or {}
    if acq.get("n") is not None:
        lignes.append(_kv("Acquisitions récentes (personnes morales)", f"{_i(acq.get('n'))}"))
    cc = z.get("commune_contexte") or {}
    # maille commune : libellée « à l'échelle de la commune » comme à l'écran.
    if cc.get("loyer_median_eur_m2") is not None:
        lignes.append(_kv(f"Loyer médian ({ECHELLE_COMMUNE})", f"{_i(cc.get('loyer_median_eur_m2'))} €/m²"))
    tr = z.get("trafic") or {}
    for ax in (tr.get("axes") or [])[:3]:
        if ax.get("tmja") is not None:
            lignes.append(_kv(f"Trafic {esc(ax.get('route') or '')}", f"{_i(ax.get('tmja'))} véh./j"))
    return _sec("Dynamique", lignes)


def rendu(zone, *, map_html: str, idu: str, rayon_km) -> str:
    z = zone or {}
    corps = map_html
    corps += f'<p class="zone-echelle">Rayon {esc(str(rayon_km))} km autour de {esc(idu)}'
    sa = z.get("surface_ha")
    if sa:
        corps += f" · {_i(sa)} ha"
    corps += "</p>"
    corps += (_population(z) + _economie(z) + _immobilier(z) + _foncier(z)
              + _contraintes(z) + _equipements(z) + _dynamique(z))
    corps += note("Agrégats de sources publiques dans le périmètre. Les mailles « " + ECHELLE_COMMUNE
                  + " » portent sur toute la commune, pas sur le seul rayon.")
    return section("Étude de zone", corps)
