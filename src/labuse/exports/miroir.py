"""EXPORTS-REBRANCHEMENT-1 lot 1 — LE MIROIR : le Dossier EST la fiche parcelle.

Le Dossier ne compose plus ses propres sections : il rend les DÉCLARATIONS de la fiche
(`declarations/fiche/` — sections.yaml pour l'ordre et les noms, chaque surface pour ses
lignes). Mêmes 11 sections, mêmes noms, même ordre, mêmes lignes que l'écran ; chaque valeur
vient du robinet unique (`robinet_fiche`, le payload `/parcels/{idu}`) et porte sa nature du
registre. Une ligne qui n'est pas déclarée n'existe pas au PDF (verrou V5d étendu) ; chaque
ligne rendue porte `data-quoi="<id>"` — c'est la preuve mécanique que le verrou lit.

Les lignes déclarées SANS valeur sur la parcelle sont dites sous « Vérifié, sans objet »
(en petit — le PDF n'a pas de clic pour déplier) avec leur phrase d'absence DÉCLARÉE.
Les lignes déclarées sans extracteur câblé sont OMISES et listées par `non_cables()` —
jamais un silence : le test de couverture les compte.

Cas particuliers assumés :
  · `simulation` (§11) = un encart de renvoi au document Financier, rien d'autre (lot 2) ;
  · la clôture « Sources, limites et mentions » suit les 11 sections (noms de sources seuls,
    aucun millésime — doctrine PAGE-SOURCES-1 du 18/09, lot 2).
"""
from __future__ import annotations

from typing import Any

from ..registre import declarations as DEC
from ..registre.valeur import Valeur
from .nature import chip
from .pieds import sources_lues
from .registre_fmt import fmt_eur, fmt_eur_m2, fmt_m, fmt_m2, fmt_pct, groupe
from .rendu import aside, esc, esc_noms, note, section, tuiles, verdict
from .verdicts import rendu_verdict, verdict_potentiel, verdict_reseaux, verdict_zonage

# ── la structure : sections + lignes, depuis les déclarations ────────────────────────────────


def structure() -> list[dict]:
    """Les sections de la fiche (ordre de sections.yaml), chacune avec ses lignes déclarées.
    Ordre des lignes dans une section : en_tete avant replie, puis (surface, rang)."""
    surfaces = [s for s in DEC.charger()[0] if s.categorie == "fiche"]
    par_section: dict[str, list] = {}
    for s in surfaces:
        for l in s.donnees:
            cle = l.fiche_section or s.fiche_section
            if cle:
                par_section.setdefault(cle, []).append((s, l))
    out = []
    for sec in DEC.sections_fiche():
        lignes = sorted(par_section.get(sec["id"], []),
                        key=lambda t: (t[1].etat != "en_tete", t[0].surface, t[1].rang))
        out.append({**sec, "lignes": lignes})
    return out


def ids_declares() -> set[str]:
    return {l.quoi for s in DEC.charger()[0] if s.categorie == "fiche" for l in s.donnees}


def non_cables() -> list[str]:
    """Les ids déclarés sur la fiche SANS extracteur au robinet — omis du rendu, comptés ici."""
    from .robinet_fiche import EXTRACTEURS
    return sorted(cid for cid in ids_declares() if cid not in EXTRACTEURS)


# ── formats scalaires (comment.format du FORMAT.md) ──────────────────────────────────────────

def _fmt_scalaire(fmt: str | None, v: Any) -> str:
    try:
        if fmt == "entier_m2":
            return fmt_m2(v)
        if fmt == "euro":
            return fmt_eur(v)
        if fmt == "euro_m2":
            return fmt_eur_m2(v)
        if fmt == "pourcent":
            return fmt_pct(v)
        if fmt == "metre":
            return fmt_m(v)
        if fmt == "degre":
            return f"{str(v).replace('.', ',')}°"
        if fmt == "entier":
            return groupe(round(float(v)))
    except (TypeError, ValueError):
        pass
    return esc(v)


# ── rendeurs par id (valeurs structurées) — la phrase de l'écran, jamais un dump ─────────────

def _r_prix_achat(v):
    d = f"{fmt_eur(v['valeur'])}" if v.get("valeur") else ""
    quand = (v.get("date_mutation") or "")[:4]
    nat = v.get("nature") or ""
    bits = [b for b in (d, nat.lower() if nat else "", quand) if b]
    return " — ".join(bits[:1] + [", ".join(bits[1:])] if len(bits) > 1 else bits)


def _r_copros(v):
    n = len(v) if isinstance(v, list) else 1
    return f"{n} copropriété{'s' if n > 1 else ''} enregistrée{'s' if n > 1 else ''} (RNIC)"


def _r_timeline(v):
    if not isinstance(v, list) or not v:
        return ""
    d = v[0].get("denomination") or ""
    ans = [str(x.get("millesime")) for x in v if x.get("millesime")]
    per = f"{ans[0]}–{ans[-1]}" if len(ans) > 1 else (ans[0] if ans else "")
    return esc(f"{d} ({per})" if d else per)


def _r_permis_liste(v):
    n = len(v) if isinstance(v, list) else 0
    return f"{n} permis sur la parcelle (Sitadel)" if n else ""


def _r_er_ebc(v):
    if isinstance(v, dict):
        lib = v.get("libelle") or v.get("detail") or "parcelle concernée"
        part = v.get("part_pct")
        return esc(f"{lib} ({groupe(part, 1)} % de la parcelle)" if part else lib)
    return esc(v)


def _r_dpu(v):
    return esc(v.get("detail") or v.get("libelle") or "Droit de préemption urbain institué")


def _r_peb(v):
    z = v.get("zone")
    return esc(f"Zone {z} du plan d'exposition au bruit" + (f" — {v['detail']}" if v.get("detail") else ""))


def _r_sup(v):
    if isinstance(v, list):
        cats = [str(x.get("categorie") or x.get("libelle") or x) for x in v if x]
        return esc(f"{len(v)} servitude{'s' if len(v) > 1 else ''} — " + " · ".join(cats[:6]))
    return esc(v)


def _r_statut_plu(v):
    return esc(v.get("libelle") or "")


def _r_aleas(v, val: Valeur):
    rows = []
    for a in v:
        nat = esc(a.get("nature") or "Aléa")
        lib = esc(a.get("libelle") or "")
        niv = a.get("niveau")
        if niv:
            lib += esc(f" — aléa de niveau {niv}") if "niveau" not in (a.get("libelle") or "") else ""
        rows.append(f'<tr data-quoi="aleas_parcelle_liste"><td class="k">{nat}</td>'
                    f'<td>{lib}</td><td class="n">{chip(val)}</td></tr>')
    return '<table class="kv">' + "".join(rows) + "</table>"


def _r_sols(v):
    bits = []
    if v.get("sis") or v.get("sis_classe"):
        bits.append(f"SIS : {v.get('sis') or v.get('sis_classe')}")
    if v.get("casias") or v.get("casias_statut"):
        bits.append(f"CASIAS : {v.get('casias') or v.get('casias_statut')}")
    return esc(" · ".join(bits))


def _r_viab(v):
    lib = v.get("libelle") or v.get("verdict") or ""
    ind = v.get("indices") or []
    if ind:
        lib += " — indices : " + " · ".join(str(i) for i in ind[:4])
    return esc(lib)


def _r_proximites(v):
    bits = []
    a = v.get("arret")
    if isinstance(a, dict) and a.get("distance_m") is not None:
        res = f" ({a['reseau']})" if a.get("reseau") else ""
        bits.append(f"Arrêt {a.get('nom', '')}{res} à {groupe(a['distance_m'])} m")
    p = v.get("pole")
    if isinstance(p, dict) and p.get("distance_m") is not None:
        bits.append(f"{p.get('nom', 'Pôle')} à {groupe(p['distance_m'])} m")
    ax = v.get("axe")
    if isinstance(ax, dict) and ax.get("distance_m") is not None:
        bits.append(f"{ax.get('nom', 'Axe')} à {groupe(ax['distance_m'])} m")
    return esc(" · ".join(bits))


def _r_tcsp(v):
    d = v.get("distance_m")
    lib = "Station de transport en site propre"
    if d is not None:
        lib += f" à {groupe(d)} m"
    if v.get("sous_800m"):
        lib += " — stationnement allégé possible (L151-36, < 800 m)"
    return esc(lib)


def _r_anc(v):
    return esc(v.get("phrase") or v.get("libelle") or "")


def _r_fibre(v):
    e = v.get("etat")
    return esc({"servi": "Immeuble raccordable (Arcep)"}.get(e, v.get("libelle") or str(e)))


def _r_prix_ancien(v):
    lib = fmt_eur_m2(v["median"])
    n = v.get("n")
    typ = v.get("type_bien") or "ancien"
    if n:
        lib += f" — {typ}, {groupe(n)} ventes à moins de 500 m"
    return esc(lib)


def _r_terrain_nu(v):
    lib = fmt_eur_m2(v["prix_m2"])
    if v.get("n"):
        lib += f" — terrain nu, {groupe(v['n'])} ventes"
    return esc(lib)


def _r_n(v):
    return esc(groupe(v["n"])) if isinstance(v, dict) and v.get("n") is not None else esc(v)


def _r_dvf_liste(v, val: Valeur):
    rows = []
    for r in v[:6]:
        tb = esc(str(r.get("type_bien") or "").capitalize())
        px = fmt_eur_m2(r["mediane_prix_m2"]) if r.get("mediane_prix_m2") else \
            (fmt_eur(r["mediane_valeur"]) if r.get("mediane_valeur") else "")
        det = f"{px} — {groupe(r['n_ventes'])} ventes" if r.get("n_ventes") else px
        if r.get("fenetre"):
            det += f", {r['fenetre']}"
        rows.append(f'<tr data-quoi="dvf_parcelle_liste"><td class="k">{tb}</td>'
                    f'<td>{esc(det)}</td><td class="n">{chip(val)}</td></tr>')
    return '<table class="kv">' + "".join(rows) + "</table>"


def _r_radar(v):
    n = len(v) if isinstance(v, list) else 0
    return f"{n} annonce{'s' if n > 1 else ''} active{'s' if n > 1 else ''} repérée{'s' if n > 1 else ''}" if n else ""


def _r_voisinage(v):
    bits = []
    if v.get("ventes_dvf") is not None:
        bits.append(f"{groupe(v['ventes_dvf'])} vente{'s' if v['ventes_dvf'] > 1 else ''} DVF")
    if v.get("prix_median_eur"):
        bits.append(f"médiane {fmt_eur(v['prix_median_eur'])}")
    elif v.get("prix_note"):
        bits.append(str(v["prix_note"]))
    if v.get("permis") is not None:
        bits.append(f"{groupe(v['permis'])} permis")
    r, fen = v.get("rayon_m"), v.get("fenetre_mois")
    suff = f" (< {r} m, {fen} mois)" if r and fen else ""
    return esc(" · ".join(bits) + suff)


def _r_iris(v, val: Valeur):
    t = tuiles([(groupe(v["habitants"]), f"habitants, {groupe(v.get('menages') or 0)} ménages"),
                (fmt_pct(v["part_60_plus_pct"]), "de 60 ans et plus")
                if v.get("part_60_plus_pct") is not None else ("", ""),
                (fmt_pct(v["part_locataires_pct"]), "de locataires")
                if v.get("part_locataires_pct") is not None else ("", "")])
    lignes = ""
    if v.get("logements") is not None:
        det = f"{groupe(v['logements'])} logements"
        if v.get("vacance_pct") is not None:
            det += f", {fmt_pct(v['vacance_pct'])} de vacance"
        lignes = (f'<table class="kv"><tr data-quoi="iris_quartier">'
                  f'<td class="k">Parc de logements du quartier</td><td>{esc(det)}</td>'
                  f'<td class="n">{chip(val)}</td></tr></table>')
    return f'<div data-quoi="iris_quartier">{t}</div>' + lignes


def _r_equipements(v):
    # même accord singulier/pluriel que l'écran et l'ancien bloc (RECETTE-8 W14) — point unique.
    from collections import Counter

    from .blocs.autour import _accord
    c = Counter(str(it.get("cat") or "") for it in v if isinstance(it, dict))
    bits = [_accord(cat, n) for cat, n in c.items() if cat]
    return esc(", ".join(bits))


def _r_potentiel(v):
    # ZONE-1 — sous une CAUSE (zone non constructible…), le libellé brut de sous-densité ne
    # s'imprime JAMAIS (faux constructible) : le bandeau verdict_potentiel dit déjà la cause.
    if v.get("cause"):
        return ""
    niv = v.get("libelle") or v.get("niveau") or ""
    return esc(niv)


def _r_dpe(v):
    et, an = v.get("etiquette"), v.get("annee")
    return esc(f"DPE {et}" + (f" ({an})" if an else "")) if et else esc(v.get("libelle") or "")


def _r_rnb(v):
    n = len(v) if isinstance(v, list) else 0
    return f"{n} identifiant{'s' if n > 1 else ''} RNB" if n else ""


def _r_tfpb(v):
    bits = [f"part communale {fmt_pct(v['tfpb_commune_pct'], 2)}"]
    if v.get("tfpb_epci_pct") is not None:
        bits.append(f"EPCI {fmt_pct(v['tfpb_epci_pct'], 2)}")
    if v.get("teom_pct") is not None:
        bits.append(f"TEOM {fmt_pct(v['teom_pct'], 2)}")
    return esc("Taxe foncière (TFPB) : " + " · ".join(bits))


def _r_taxe(v):
    taux = v.get("taux_communal_pct")
    if taux is None:
        return ""
    lib = f"Taux communal {fmt_pct(taux)}"
    if v.get("taux_communal_millesime"):
        lib += f" — {v['taux_communal_millesime']}"
    lib += (". Se calcule sur la surface de plancher créée par le projet — "
            "montant chiffré au Dossier financier.")
    return esc(lib)


def _r_territoire(v, val: Valeur):
    rows = []

    def _row(cle, lib):
        rows.append(f'<tr data-quoi="perimetres_dispositifs_liste"><td class="k">{esc(cle)}</td>'
                    f'<td>{esc(lib)}</td><td class="n">{chip(val)}</td></tr>')
    dom = (v.get("dispositifs_dom") or [{}])[0]
    if dom.get("libelle"):
        _row("Zonage du logement", dom["libelle"])
    if (v.get("zfang") or {}).get("libelle"):
        _row("ZFANG", v["zfang"]["libelle"])
    if (v.get("frr") or {}).get("libelle"):
        _row("FRR (ex-ZRR)", v["frr"]["libelle"])
    for per in (v.get("perimetres") or []):
        if per.get("libelle"):
            _row("Périmètre", per["libelle"])
    return '<table class="kv">' + "".join(rows) + "</table>" if rows else ""


def _r_rang(v):
    if v.get("total"):
        return esc(f"{groupe(v['rang'])} sur {groupe(v['total'])}")
    return esc(groupe(v["rang"]))


def _r_filiation(v):
    if isinstance(v, list):
        return esc(f"{len(v)} événement{'s' if len(v) > 1 else ''} cadastral(aux) (DFI)")
    return esc(v.get("libelle") or "Filiation cadastrale disponible")


#: id → rendeur. `bloc` = fragment pleine largeur (tableau propre) ; sinon cellule valeur.
_RENDEURS: dict[str, Any] = {
    "prix_achat_historique_eur": _r_prix_achat, "coproprietes_liste": _r_copros,
    "proprietaire_timeline_liste": _r_timeline, "historique_permis_liste": _r_permis_liste,
    "er_emplacement_reserve": _r_er_ebc, "ebc_classe": _r_er_ebc, "dpu_perimetre": _r_dpu,
    "peb_zone": _r_peb, "dispositifs_parcelle": _r_sup, "statut_plu": _r_statut_plu,
    "sols_parcelle": _r_sols, "viabilisation_verdict": _r_viab, "distance_arret_m": _r_proximites,
    "tcsp_stationnement_allege": _r_tcsp, "part_logements_egout_pct": _r_anc,
    "fibre_parcelle": _r_fibre, "prix_sortie_bati_eur_m2": _r_prix_ancien,
    "prix_terrain_secteur_eur_m2": _r_terrain_nu, "ventes_retenues_n": _r_n,
    "ventes_ecartees_n": _r_n, "n_permis_proximite": _r_n, "radar_annonces_liste": _r_radar,
    "ventes_100m_n": _r_voisinage, "voisinage_100m_liste": _r_voisinage,
    "equipements_proximite_liste": _r_equipements, "potentiel_verdict": _r_potentiel,
    "dpe_connu": _r_dpe, "rnb_batiments_liste": _r_rnb, "tfpb_taux_pct": _r_tfpb,
    "taxe_amenagement_estimee_eur": _r_taxe, "rang_tier": _r_rang,
    "filiation_parcelle": _r_filiation,
}
_RENDEURS_BLOC: dict[str, Any] = {
    "aleas_parcelle_liste": _r_aleas, "dvf_parcelle_liste": _r_dvf_liste,
    "iris_quartier": _r_iris, "perimetres_dispositifs_liste": _r_territoire,
}
#: le règlement PLU (extraits) garde son rendu de bloc historique (blocs/zonage._regles) — réutilisé.
#: `simulation` : lignes remplacées par l'encart de renvoi (lot 2) — dit dans le rendu.
_IGNORES_SIMULATION = True


def _valeur_html(cid: str, l, brute, val: Valeur) -> str:
    r = _RENDEURS.get(cid)
    if r is not None:
        return r(brute)
    return _fmt_scalaire((l.comment or {}).get("format"), brute)


# ── le rendu ─────────────────────────────────────────────────────────────────────────────────

def _pied_noms(vals: list[Valeur]) -> str:
    """Le pied de section : les NOMS des sources lues — aucun millésime, aucune date
    (doctrine PAGE-SOURCES-1 du 18/09)."""
    noms = [nom for nom, _mill in sources_lues(vals)]
    return note("Sources : " + " · ".join(noms)) if noms else ""


def _ligne_tr(cid: str, cle: str, valeur_html: str, chip_html: str) -> str:
    return (f'<tr data-quoi="{esc(cid)}"><td class="k">{esc(cle)}</td><td>{valeur_html}</td>'
            f'<td class="n">{chip_html}</td></tr>')


#: valeur COURTE d'une tuile pour les ids structurés de l'en-tête (jamais un dict imprimé).
_TUILE_FMT = {
    "tfpb_taux_pct": lambda v: fmt_pct(v["tfpb_commune_pct"], 2) if isinstance(v, dict) else fmt_pct(v, 2),
    "rang_tier": lambda v: f"{groupe(v['rang'])} / {groupe(v['total'])}" if v.get("total") else groupe(v["rang"]),
}


def _entete_tuiles(sec: dict, valeurs: dict[str, Valeur]) -> str:
    items, quois = [], []
    for s, l in sec["lignes"]:
        v = valeurs.get(l.quoi)
        if v is None:
            continue
        f = _TUILE_FMT.get(l.quoi)
        if f is not None:
            try:
                court = f(v.valeur)
            except (KeyError, TypeError, ValueError):
                continue
        elif isinstance(v.valeur, (dict, list)):
            continue                                # pas de forme courte : la tuile n'invente pas
        else:
            court = _fmt_scalaire((l.comment or {}).get("format"), v.valeur)
        items.append((court, (l.comment or {}).get("libelle") or l.quoi))
        quois.append(l.quoi)
    if not items:
        return ""
    cells = "".join(f'<div class="tile" data-quoi="{esc(q)}"><div class="v">{v}</div>'
                    f'<div class="l">{esc(lb)}</div></div>' for q, (v, lb) in zip(quois, items))
    return f'<div class="tiles">{cells}</div>'


def _v(valeurs, cid):
    x = valeurs.get(cid)
    return x.valeur if x else None


def _verdict_factuel(sec_id: str, valeurs: dict[str, Valeur]) -> tuple[str, str, str] | None:
    """EXPORTS-REBRANCHEMENT-2 lot 1 — le verdict-phrase FACTUEL des sections « gris » (le maquette
    v4 en veut un en tête de CHAQUE section). Assemblé DÉTERMINISTIQUEMENT de valeurs servies —
    jamais une prose inventée : chaque nombre est ancré au registre (crible de provenance). Rend
    (texte, ton, chiffre_id_tampon) ou None si rien de servi (pas de bandeau vide)."""
    if sec_id == "identite":
        pm = _v(valeurs, "type_proprietaire")
        tl = _v(valeurs, "proprietaire_timeline_liste")
        if not pm:
            return None
        bout = ""
        if isinstance(tl, list) and tl:
            ans = [str(x.get("millesime")) for x in tl if x.get("millesime")]
            if ans:
                bout = f" — au fichier depuis {ans[0]}" if len(set(ans)) == 1 else f" — au fichier {ans[0]}–{ans[-1]}"
        return (esc(str(pm).split(" (SIREN")[0]) + esc(bout) + ".", "neutral", "type_proprietaire")
    if sec_id == "terrain":
        p = _v(valeurs, "pente_deg")
        libre = _v(valeurs, "surface_libre_sol_m2")
        bits = []
        if p is not None:
            bits.append(f"pente {str(p).replace('.', ',')}°")
        if libre is not None:
            bits.append(f"{fmt_m2(libre)} de sol libre")
        return (esc(" · ".join(bits).capitalize()) + ".", "neutral", "pente_deg") if bits else None
    if sec_id == "bati":
        n = _v(valeurs, "n_batiments")
        emp = _v(valeurs, "emprise_batie_m2")
        if not n:
            return ("Parcelle non bâtie (aucun bâtiment cartographié).", "neutral", "n_batiments")
        t = f"{groupe(n)} bâtiment{'s' if n > 1 else ''}"
        if emp is not None:
            t += f", {fmt_m2(emp)} au sol"
        return (esc(t) + ".", "neutral", "n_batiments")
    if sec_id == "fiscalite":
        tf = _v(valeurs, "perimetres_dispositifs_liste")
        if isinstance(tf, dict):
            dom = (tf.get("dispositifs_dom") or [{}])[0]
            z = dom.get("libelle") or ""
            n_disp = sum(1 for k in ("zfang", "frr") if (tf.get(k) or {}).get("libelle")) \
                + len(tf.get("perimetres") or [])
            t = esc(z) if z else "Régime fiscal de droit commun"
            if n_disp:
                t += f" · {n_disp} dispositif{'s' if n_disp > 1 else ''} territ{'oriaux' if n_disp > 1 else 'orial'}"
            return (t + ".", "neutral", "perimetres_dispositifs_liste")
        return None
    if sec_id == "marche":
        pa = _v(valeurs, "prix_sortie_bati_eur_m2")
        if isinstance(pa, dict) and pa.get("median") is not None:
            t = f"Prix ancien médian {fmt_eur_m2(pa['median'])}"
            if pa.get("n"):
                t += f" ({groupe(pa['n'])} ventes à moins de 500 m)"
            return (esc(t) + ".", "neutral", "prix_sortie_bati_eur_m2")
        return None
    if sec_id == "quartier":
        iq = _v(valeurs, "iris_quartier")
        if isinstance(iq, dict) and iq.get("habitants") is not None:
            nom = iq.get("nom") or "le quartier IRIS"
            return (esc(f"{nom} — {groupe(iq['habitants'])} habitants") + ".", "neutral", "iris_quartier")
        return None
    return None


def _bandeau(sec_id: str, valeurs: dict[str, Valeur]) -> str:
    """Le verdict-phrase de tête de section. Moteurs réels quand ils existent (urbanisme, potentiel,
    réseaux, risques) ; sinon une synthèse FACTUELLE déterministe (identité, terrain, bâti, fiscalité,
    marché, quartier). Rien pour §10 si la fiche ne sert pas de potentiel (pas de bandeau vide)."""
    if sec_id == "urbanisme":
        v = verdict_zonage(valeurs)
        return f'<div data-quoi="zone_plu_famille">{rendu_verdict(v)}</div>' if v else ""
    if sec_id == "potentiel":
        v = verdict_potentiel(valeurs)
        return f'<div data-quoi="potentiel_verdict">{rendu_verdict(v)}</div>' if v else ""
    if sec_id == "reseaux":
        v = verdict_reseaux(valeurs)
        return f'<div data-quoi="viabilisation_verdict">{rendu_verdict(v)}</div>' if v else ""
    if sec_id == "risques":
        av = valeurs.get("aleas_parcelle_liste")
        rouges = [a for a in ((av.valeur if av else None) or [])
                  if isinstance(a, dict) and a.get("redhibitoire")]
        if rouges:
            return (f'<div data-quoi="aleas_parcelle_liste">'
                    f'{verdict(esc(rouges[0].get("libelle") or ""), ton="warn")}</div>')
        if av is not None:
            return f'<div data-quoi="aleas_parcelle_liste">{verdict("Aléas relevés — aucun rédhibitoire.", ton="neutral")}</div>'
        return ""
    fx = _verdict_factuel(sec_id, valeurs)
    if fx:
        texte, ton, cid = fx
        return f'<div data-quoi="{esc(cid)}">{verdict(texte, ton=ton)}</div>'
    return ""


def _renvoi_financier() -> str:
    return aside(
        '<div class="t">Renseignez votre opération pour obtenir le bilan</div>'
        "<p>Le bilan dépend de chiffres que vous seul connaissez : prix demandé par le vendeur, "
        "coût de construction, marge visée. LABUSE ne les suppose pas à votre place. "
        "Le document <strong>Financier</strong> les recueille et imprime le chiffre d'affaires, "
        "la charge foncière supportable, l'écart au prix demandé et la sensibilité au coût de "
        "construction.</p>", variante="projet")


def _bloc_reglement(valeurs: dict[str, Valeur]) -> str:
    """Les extraits du règlement (règles calibrées + destinations + drapeau Q12 + renvoi GPU) —
    le rendu historique du bloc zonage, réutilisé tel quel (mêmes gardes de mots interdits)."""
    from .blocs.zonage import _destinations, _regles
    v = valeurs.get("reglement_plu_bloc")
    z = (v.valeur if v else None) or {}
    corps = _regles(z) + _destinations(z)
    if isinstance(z, dict) and z.get("_prescriptions_verifiables") is False:
        motif = z.get("_prescriptions_motif") or "aucun document de prescriptions publié pour cette commune"
        corps += aside(f"<strong>Prescriptions non vérifiables sur cette commune</strong> — {esc(motif)}. "
                       "Un emplacement réservé ou une servitude peut exister sans être publié : "
                       "à vérifier en mairie.", "rose")
    if z.get("idurba"):
        corps += note(f"Règlement complet : {z['idurba']} sur le Géoportail de l'urbanisme. "
                      "Les valeurs ci-dessus sont une aide à la lecture ; le règlement fait foi.")
    return corps


#: EXPORTS-REBRANCHEMENT-2 lot 1 — les SIX chiffres du bandeau de garde (maquette v4), dans
#: l'ordre : Surface · Zone · Pente · Exposition · Risques · SDP restante. Le SCORE n'y est pas.
_COVER_TUILES = [
    ("surface_parcelle_m2", "Surface", lambda v: fmt_m2(v)),
    ("zone_plu_famille", "Zone", lambda v: esc(v)),
    ("pente_deg", "Pente", lambda v: esc(f"{str(v).replace('.', ',')}°")),
    ("exposition_versant", "Exposition", lambda v: esc(v)),
    ("n_vigilances", "Risques", lambda v: esc(f"{groupe(v)} relevé{'s' if v and v > 1 else ''}")),
    ("sdp_residuelle_m2", "SDP restante", lambda v: fmt_m2(v)),
]


def cover_dossier(idu: str, fiche: dict, numero: str, jour, valeurs: dict[str, Valeur],
                  modele: str) -> str:
    """La page de garde du Dossier (maquette v4) : cartouche 4 champs + bandeau des SIX chiffres
    de la fiche en 3 colonnes + sommaire des sections + légende. Chaque tuile porte data-quoi
    (verrou V5d) ; une valeur absente s'affiche « — » (jamais un zéro inventé)."""
    adresse = fiche.get("adresse") or ""
    commune = fiche.get("commune") or ""
    tuiles_html = []
    for cid, lib, fmt in _COVER_TUILES:
        v = valeurs.get(cid)
        try:
            aff = fmt(v.valeur) if v is not None and v.valeur is not None else '<span class="none">—</span>'
        except (TypeError, ValueError, KeyError):
            aff = '<span class="none">—</span>'
        tuiles_html.append(f'<div class="tile" data-quoi="{esc(cid)}"><div class="v">{aff}</div>'
                           f'<div class="l">{esc(lib)}</div></div>')
    toc = []
    n = 0
    for sec in structure():
        if sec["id"] == "entete":
            continue
        n += 1
        toc.append(f'<li>{n}. {esc(sec["titre"])}<span>fiche {esc(sec["id"])}</span></li>')
    toc.append(f'<li>{n + 1}. Limites et sources<span>annexe</span></li>')
    legende = (
        '<div class="legend">'
        '<span class="chip s">sourcé</span> lu dans la source · '
        '<span class="chip d">dérivé</span> calculé · '
        '<span class="chip e">estimé</span> hypothèse dite · '
        '<span class="chip p">projet</span> saisi par vous</div>')
    return (
        '<div class="cover">'
        '<div class="kicker">Dossier parcelle</div>'
        f'<h1>{esc(idu)}</h1>'
        + (f'<p class="address">{esc_noms(adresse)}</p>' if adresse else "")
        + f'<p class="idu">{esc(commune)}</p>'
        '<div class="gm-meta">'
        f'<div><b>{esc(numero)}</b>n° de rapport</div>'
        f'<div><b>{jour:%d/%m/%Y}</b>généré le</div>'
        f'<div><b>{fmt_m2(valeurs["surface_parcelle_m2"].valeur) if valeurs.get("surface_parcelle_m2") else "—"}</b>contenance</div>'
        f'<div><b>Modèle {esc(modele)}</b>miroir de la fiche</div>'
        '</div>'
        f'<div class="cover-tiles">{"".join(tuiles_html)}</div>'
        '<p class="note">Le bandeau des six chiffres de la fiche.</p>'
        f'<ul class="toc">{"".join(toc)}</ul>'
        + legende +
        '</div>')


def rendu_sections(valeurs: dict[str, Valeur], fiche: dict, *, plan_html: str = "") -> str:
    """Le corps du Dossier : les 11 sections de la fiche, depuis les déclarations. L'en-tête de
    tuiles vit désormais dans la page de garde (cover_dossier) ; la clôture §12 (limites + sources)
    est ajoutée ici. `plan_html` : le plan de situation injecté en §1 (même composant que l'Apporteur)."""
    corps = []
    numero = 0
    for sec in structure():
        if sec["id"] == "entete":
            continue                                   # rendu dans la page de garde (cover_dossier)
        numero += 1
        titre = f"{numero}. {sec['titre']}" if sec.get("numerote", True) else sec["titre"]
        if sec["id"] == "simulation":
            corps.append(section(titre, _renvoi_financier()))
            continue
        frags: list[str] = []
        frags.append(_bandeau(sec["id"], valeurs))
        blocs_pleins: list[str] = []
        groupes: dict[str, list[str]] = {}           # libellé de groupe → lignes kv (ordre 1re vue)
        absents: list[tuple[str, str]] = []          # (quoi, phrase d'absence déclarée)
        vals_lus: list[Valeur] = []
        from .robinet_fiche import EXTRACTEURS
        for s, l in sec["lignes"]:
            v = valeurs.get(l.quoi)
            if v is None:
                # DONNEES-1 lot 2 — `masquer_si_absent` : la ligne disparaît, aucune phrase d'absence.
                if l.quoi in EXTRACTEURS and l.absence and not l.masquer_si_absent:
                    absents.append((l.quoi, l.absence))
                continue                              # sans extracteur : omis (non_cables le compte)
            vals_lus.append(v)
            if l.quoi == "reglement_plu_bloc":
                blocs_pleins.append(f'<div data-quoi="reglement_plu_bloc">{_bloc_reglement(valeurs)}</div>')
                continue
            if l.quoi in _RENDEURS_BLOC:
                blocs_pleins.append(_RENDEURS_BLOC[l.quoi](v.valeur, v))
                continue
            html = _valeur_html(l.quoi, l, v.valeur, v)
            if not html:
                continue
            lib = (l.comment or {}).get("libelle") or l.quoi
            grp = l.section if (l.section and l.section != sec["titre"]) else ""
            groupes.setdefault(grp, []).append(_ligne_tr(l.quoi, lib, html, chip(v)))
        rows: list[str] = []
        for grp, lignes_grp in groupes.items():      # un en-tête de groupe UNE fois, jamais vide
            if grp:
                rows.append(f'<tr class="grp"><td colspan="3"><strong>{esc(grp)}</strong></td></tr>')
            rows += lignes_grp
        if rows:
            frags.append('<table class="kv">' + "".join(rows) + "</table>")
        frags += blocs_pleins
        # §1 — le plan de situation (ortho IGN, contour, voisines du même propriétaire), le MÊME
        # composant que l'Apporteur, injecté par le builder (qui a la base).
        if sec["id"] == "identite" and plan_html:
            frags.append(plan_html)
        if absents:
            lis = "".join(f'<li data-quoi="{esc(q)}">{esc(ph)}</li>' for q, ph in absents)
            frags.append(f'<div class="sansobjet"><div class="t">Vérifié, sans objet</div>'
                         f'<ul>{lis}</ul></div>')
        if vals_lus:
            frags.append(_pied_noms(vals_lus))
        corps.append(section(titre, "".join(x for x in frags if x)))
    # §12 — ce que ce document ne peut pas dire + les NOMS des sources (bloc dédié, sans millésime).
    from .blocs import sources as bloc_sources
    corps.append(section(f"{numero + 1}. Limites et sources", bloc_sources.corps_sources(valeurs)))
    return "".join(corps)
