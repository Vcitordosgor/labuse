"""F3 — Relations MÉTAMORPHIQUES (chasse-invariants-2).

On ne vérifie pas une valeur absolue, on vérifie une DIRECTION : quand UN input bouge (les autres
tenus égaux), la sortie du moteur doit bouger dans le bon sens. Chaque règle est « vraie par
construction » — on l'écarte AVANT de tourner si le moteur ne la garantit pas (pas de faux mordant).

Les moteurs sont appelés DIRECTEMENT, en calcul à blanc, JAMAIS via l'API ni par écriture base :
  · `faisabilite.engine.estimate_capacity(rules, surface, contraintes, hyp)` — PUR (modèle carré si
    pas d'`emprise_geo`). surface↑⇒SDP/emprise≥ ; hé↑⇒niveaux/SDP≥ ; recul↑⇒emprise≤ ; CES↑⇒emprise≥ ;
    pleine terre↑⇒emprise≤ ; ajout contrainte (PPR/pente/littoral)⇒capacité≤ ; emprise×niveaux=SDP.
  · `exports.financier_bilan.calculer / calculer_revente` — PUR. prix d'achat↑⇒marge≤ ; revente↑⇒
    marge≥ ; travaux↑⇒marge≤ ; coût↑⇒charge foncière≤ ; prix de sortie↑⇒CA/charge≥ ; marge_pct↑⇒
    charge≤ ; prix demandé↑⇒marge résiduelle/écart≤.
  · `taxe_amenagement.calculer` — PUR (config datée). surface taxable↑⇒assiette/total≥ ; taux↑⇒
    total≥ ; forfaits (piscine/PV/stationnement/éolienne)↑⇒assiette≥ ; abattement RP⇒assiette≤ ;
    exonération⇒total≤.

Les bases de règles (ZoneRules) sont tirées de VRAIES parcelles servies (zone+commune réelles,
résolues par `resolve_zone`), de façon déterministe (échantillon md5 du noyau). Les perturbations
numériques (surface, prix, taux…) sont synthétiques et bornées au domaine réaliste.

Forme callable (noyau) : chaque `check(cx, api)` boucle sur les cas échantillonnés, renvoie
("ECART", …) au PREMIER cas qui viole (cas montré), sinon ("OK", N cas), ou ("SKIP", raison).
"""
from __future__ import annotations

import dataclasses
import sys
import pathlib

_ICI = pathlib.Path(__file__).resolve()
sys.path.insert(0, str(_ICI.parents[2]))  # scripts/
from coherence.invariants2.noyau import (  # noqa: E402
    Ecartee,
    RuleSpec,
    bilan,
    connexion,
    echantillon_stratifie,
    run_specs,
)

# ── import des moteurs (purs) ─────────────────────────────────────────────────────────────────
from labuse.faisabilite.engine import (  # noqa: E402
    Contraintes,
    Hypotheses,
    estimate_capacity,
)
from labuse.faisabilite.zonage import ZoneRules, resolve_zone  # noqa: E402
from labuse.exports import financier_bilan as FBILAN  # noqa: E402
from labuse import taxe_amenagement as TAXE  # noqa: E402

EPS = 1e-6  # tolérance d'égalité flottante (une direction « ≥ » accepte l'égalité à EPS près)


# ════════════════════════════════════════════════════════════════════════════════════════════
#  1) bases ZoneRules RÉELLES (zone+commune de vraies parcelles servies, résolues par le moteur)
# ════════════════════════════════════════════════════════════════════════════════════════════
_BASES_CACHE: list[tuple[str, ZoneRules]] | None = None


def _bases_zonerules(cx, n: int = 400) -> list[tuple[str, ZoneRules]]:
    """ZoneRules CONSTRUCTIBLES distinctes (code zone) tirées de vraies parcelles. On déduplique par
    (commune, code) pour couvrir des règles variées sans rejouer 400× la même zone. Déterministe."""
    global _BASES_CACHE
    if _BASES_CACHE is not None:
        return _BASES_CACHE
    idus = echantillon_stratifie(cx, n=n)
    out: dict[tuple, ZoneRules] = {}
    with cx.conn.cursor() as cur:
        # (zone, commune) servis pour l'échantillon — parcel_zone_plu est la table servie (clé idu,
        # code de zone = zone_lib).
        cur.execute(
            "SELECT p.commune, z.zone_lib FROM parcels p "
            "JOIN parcel_zone_plu z ON z.idu = p.idu "
            "WHERE p.idu = ANY(%s) AND z.zone_lib IS NOT NULL",
            (idus,))
        couples = cur.fetchall()
    for commune, zone in couples:
        if not zone:
            continue
        key = (commune, zone)
        if key in out:
            continue
        try:
            r = resolve_zone(zone, commune)
        except Exception:  # noqa: BLE001 — une zone non résoluble ne casse pas la génération
            continue
        if r is None or not r.constructible_neuf or r.habitat == "interdit" or r.regle_non_validee:
            continue
        # garde : le moteur exige hé OU hf OU prospect pour calculer des niveaux
        if not (r.hauteur_mode == "prospect" or isinstance(r.he_m, (int, float))
                or isinstance(r.hf_m, (int, float)) or r.niveaux_max is not None
                or r.hauteur_plage):
            continue
        out[key] = r
    _BASES_CACHE = list(out.items())
    return _BASES_CACHE


def _sdp(f) -> float:
    return float((f.fourchette or {}).get("surface_plancher_m2") or 0.0)


def _emprise(f) -> float:
    return float((f.fourchette or {}).get("emprise_constructible_m2") or 0.0)


def _niveaux(f) -> int:
    return int((f.fourchette or {}).get("niveaux_max") or 0)


def _logts_hi(f) -> int:
    fr = f.fourchette or {}
    return max((fr.get("logements_au_sol") or (0, 0))[1],
               (fr.get("logements_sous_sol") or (0, 0))[1])


# ────────────────────────── relations sur estimate_capacity ────────────────────────────────────
_SURFACES = [400.0, 1000.0, 3000.0]      # m² terrain tenus comme point de départ


def _mk_check_surface(sortie_fn, nom):
    """surface terrain ↑ (règles tenues égales) ⇒ `sortie_fn` ≥ (non décroissante)."""
    def check(cx, api):
        bases = _bases_zonerules(cx)
        if not bases:
            return "SKIP", "aucune base ZoneRules constructible échantillonnée"
        n = 0
        for (commune, _code), rules in bases:
            for s in _SURFACES:
                f_lo = estimate_capacity(rules, s)
                f_hi = estimate_capacity(rules, s * 1.5)
                n += 1
                if not (f_lo.constructible and f_hi.constructible):
                    continue
                v_lo, v_hi = sortie_fn(f_lo), sortie_fn(f_hi)
                if v_hi < v_lo - EPS:
                    return ("ECART",
                            f"{commune}/{rules.code} surface {s:g}→{s*1.5:g} : {nom} {v_lo:g}→{v_hi:g} "
                            f"(devrait être ≥)")
        return "OK", f"{nom} non décroissante en surface ({n} cas, {len(bases)} zones)"
    return check


def _mk_check_hauteur(sortie_fn, nom):
    """hauteur hé ↑ ⇒ `sortie_fn` ≥. On ne teste QUE les zones à hé numérique (sinon la hauteur
    n'est pas le levier : plage/niveaux_max/prospect ignoreraient la perturbation → non concluant)."""
    def check(cx, api):
        bases = [(k, r) for k, r in _bases_zonerules(cx)
                 if isinstance(r.he_m, (int, float)) and r.niveaux_max is None and not r.hauteur_plage]
        if not bases:
            return "SKIP", "aucune zone à hé numérique (hauteur = levier) échantillonnée"
        n = 0
        for (commune, _code), rules in bases:
            r_hi = dataclasses.replace(rules, he_m=float(rules.he_m) + 3.0)  # +1 niveau
            for s in _SURFACES:
                f_lo = estimate_capacity(rules, s)
                f_hi = estimate_capacity(r_hi, s)
                n += 1
                if not (f_lo.constructible and f_hi.constructible):
                    continue
                v_lo, v_hi = sortie_fn(f_lo), sortie_fn(f_hi)
                if v_hi < v_lo - EPS:
                    return ("ECART",
                            f"{commune}/{rules.code} hé {rules.he_m:g}→{rules.he_m+3:g} : {nom} "
                            f"{v_lo:g}→{v_hi:g} (devrait être ≥)")
        return "OK", f"{nom} non décroissante en hauteur hé ({n} cas, {len(bases)} zones)"
    return check


def _mk_check_hf(sortie_fn, nom):
    """hauteur FAÎTAGE hf ↑ ⇒ sortie ≥ — chemin DISTINCT de hé (niveaux = (hf−étage)÷étage). On ne
    teste QUE les zones à hf numérique SANS hé (sinon hé prime : hf n'est pas le levier)."""
    def check(cx, api):
        bases = [(k, r) for k, r in _bases_zonerules(cx)
                 if isinstance(r.hf_m, (int, float)) and not isinstance(r.he_m, (int, float))
                 and r.niveaux_max is None and not r.hauteur_plage]
        if not bases:
            return "SKIP", "aucune zone à hf numérique sans hé (faîtage = levier)"
        n = 0
        for (commune, _code), rules in bases:
            r_hi = dataclasses.replace(rules, hf_m=float(rules.hf_m) + 3.0)
            for s in _SURFACES:
                f_lo = estimate_capacity(rules, s)
                f_hi = estimate_capacity(r_hi, s)
                n += 1
                if not (f_lo.constructible and f_hi.constructible):
                    continue
                if sortie_fn(f_hi) < sortie_fn(f_lo) - EPS:
                    return ("ECART", f"{commune}/{rules.code} hf {rules.hf_m:g}→{rules.hf_m+3:g} : "
                            f"{nom} {sortie_fn(f_lo):g}→{sortie_fn(f_hi):g} (devrait ≥)")
        return "OK", f"{nom} non décroissant quand hf (faîtage) ↑ ({n} cas, {len(bases)} zones)"
    return check


def _mk_check_niveaux_max(sortie_fn, nom):
    """R+n imposé (niveaux_max) ↑ ⇒ niveaux/SDP ≥ (feuille `niveaux` validée, chemin distinct)."""
    def check(cx, api):
        bases = _bases_zonerules(cx)
        if not bases:
            return "SKIP", "aucune base ZoneRules"
        n = 0
        for (commune, _code), rules in bases:
            r_lo = dataclasses.replace(rules, niveaux_max=2, hauteur_plage=None)
            r_hi = dataclasses.replace(rules, niveaux_max=5, hauteur_plage=None)
            for s in _SURFACES:
                f_lo = estimate_capacity(r_lo, s)
                f_hi = estimate_capacity(r_hi, s)
                n += 1
                if not (f_lo.constructible and f_hi.constructible):
                    continue
                if sortie_fn(f_hi) < sortie_fn(f_lo) - EPS:
                    return ("ECART", f"{commune}/{rules.code} R+2→R+5 : {nom} "
                            f"{sortie_fn(f_lo):g}→{sortie_fn(f_hi):g} (devrait ≥)")
        return "OK", f"{nom} non décroissant quand R+n imposé ↑ ({n} cas, {len(bases)} zones)"
    return check


def _mk_check_hyp_coef(champ, pct, sens, nom, sortie_fn, sortie_nom):
    """hypothèse de modélisation (coef_occupation / coef_rendement) perturbée ⇒ sortie monotone.
    coef_occupation ↑ ⇒ emprise bâtie/SDP ≥ ; coef_rendement ↑ ⇒ surface habitable vendable ≥."""
    def check(cx, api):
        bases = _bases_zonerules(cx)
        if not bases:
            return "SKIP", "aucune base ZoneRules"
        h_lo, h_hi = Hypotheses(), Hypotheses()
        setattr(h_hi, champ, float(getattr(h_lo, champ)) * pct)
        n = 0
        for (commune, _code), rules in bases:
            for s in _SURFACES:
                f_lo = estimate_capacity(rules, s, hyp=h_lo)
                f_hi = estimate_capacity(rules, s, hyp=h_hi)
                n += 1
                if not (f_lo.constructible and f_hi.constructible):
                    continue
                v_lo, v_hi = sortie_fn(f_lo), sortie_fn(f_hi)
                ok = (v_hi >= v_lo - EPS) if sens > 0 else (v_hi <= v_lo + EPS)
                if not ok:
                    return ("ECART", f"{commune}/{rules.code} {nom} ×{pct:g}, terrain {s:g} : "
                            f"{sortie_nom} {v_lo:g}→{v_hi:g} (devrait {'≥' if sens > 0 else '≤'})")
        return "OK", (f"{sortie_nom} {'croît' if sens > 0 else 'décroît'} quand {nom} ↑ "
                      f"({n} cas, {len(bases)} zones)")
    return check


def _shab_vendable(f) -> float:
    return float((f.fourchette or {}).get("shab_vendable_m2") or 0.0)


def _emprise_batie(f) -> float:
    return float((f.fourchette or {}).get("emprise_batie_max_m2") or 0.0)


def _mk_check_logement_m2():
    """surface moyenne / logement ↓ (logements plus petits) ⇒ nombre de logements ≥ (habitable fixe).
    On DIMINUE logement_m2 (×0,7) et on attend logements ≥."""
    def check(cx, api):
        bases = _bases_zonerules(cx)
        if not bases:
            return "SKIP", "aucune base ZoneRules"
        h_gros, h_petit = Hypotheses(), Hypotheses()
        h_petit.logement_m2_bas = Hypotheses().logement_m2_bas * 0.7
        h_petit.logement_m2_haut = Hypotheses().logement_m2_haut * 0.7
        n = 0
        for (commune, _code), rules in bases:
            for s in (3000.0, 8000.0):   # grand terrain : la densité (ex-COS) ne masque pas l'effet
                f_gros = estimate_capacity(rules, s, hyp=h_gros)
                f_petit = estimate_capacity(rules, s, hyp=h_petit)
                n += 1
                if not (f_gros.constructible and f_petit.constructible):
                    continue
                if _logts_hi(f_petit) < _logts_hi(f_gros) - EPS:
                    return ("ECART", f"{commune}/{rules.code} logement ×0,7 (plus petits), terrain {s:g} : "
                            f"logements {_logts_hi(f_gros)}→{_logts_hi(f_petit)} (devrait ≥)")
        return "OK", f"logements non décroissant quand la surface/logement ↓ ({n} cas, {len(bases)} zones)"
    return check


def _mk_check_recul(champ, nom_recul):
    """recul ↑ (voie OU limites) ⇒ emprise constructible ≤. On ne teste QUE les zones SANS CES %
    (sinon le CES borne l'emprise et masque l'effet des reculs) et modèle carré (reculs = levier
    géométrique direct). Surfaces assez grandes pour ne pas vider l'assiette (0 des deux côtés)."""
    def check(cx, api):
        bases = [(k, r) for k, r in _bases_zonerules(cx) if not isinstance(r.emprise_sol_pct, (int, float))
                 and not r.emprise_plage]
        if not bases:
            return "SKIP", "aucune zone sans CES % (recul = levier) échantillonnée"
        n = 0
        for (commune, _code), rules in bases:
            base_v = getattr(rules, champ)
            base_v = float(base_v) if isinstance(base_v, (int, float)) else 3.0
            r_hi = dataclasses.replace(rules, **{champ: base_v + 6.0})
            for s in (2000.0, 5000.0):   # grandes parcelles : l'assiette ne se vide pas
                f_lo = estimate_capacity(rules, s)
                f_hi = estimate_capacity(r_hi, s)
                n += 1
                if not f_lo.constructible:
                    continue
                e_lo = _emprise(f_lo)
                e_hi = _emprise(f_hi) if f_hi.constructible else 0.0
                if e_hi > e_lo + EPS:
                    return ("ECART",
                            f"{commune}/{rules.code} {nom_recul} {base_v:g}→{base_v+6:g} m, terrain {s:g} : "
                            f"emprise {e_lo:g}→{e_hi:g} (devrait être ≤)")
        return "OK", f"emprise non croissante quand {nom_recul} ↑ ({n} cas, {len(bases)} zones)"
    return check


def _mk_check_ces(sortie_fn, nom):
    """CES (emprise_sol_pct) ↑ ⇒ emprise / SDP ≥. Le CES PLAFONNE l'emprise (min(reculs, cap)) ;
    relâcher le plafond ne peut pas diminuer. On part d'un CES BAS pour que le plafond morde."""
    def check(cx, api):
        bases = _bases_zonerules(cx)
        if not bases:
            return "SKIP", "aucune base ZoneRules"
        n = 0
        for (commune, _code), rules in bases:
            r_lo = dataclasses.replace(rules, emprise_sol_pct=20.0, emprise_plage=None)
            r_hi = dataclasses.replace(rules, emprise_sol_pct=60.0, emprise_plage=None)
            for s in (1000.0, 3000.0):
                f_lo = estimate_capacity(r_lo, s)
                f_hi = estimate_capacity(r_hi, s)
                n += 1
                if not (f_lo.constructible and f_hi.constructible):
                    continue
                v_lo, v_hi = sortie_fn(f_lo), sortie_fn(f_hi)
                if v_hi < v_lo - EPS:
                    return ("ECART",
                            f"{commune}/{rules.code} CES 20→60 %, terrain {s:g} : {nom} "
                            f"{v_lo:g}→{v_hi:g} (devrait être ≥)")
        return "OK", f"{nom} non décroissante quand le CES ↑ ({n} cas, {len(bases)} zones)"
    return check


def _mk_check_pleine_terre():
    """pleine terre % ↑ ⇒ emprise constructible ≤ (cap_pt = surface×(1−pt%) borne l'emprise)."""
    def check(cx, api):
        bases = _bases_zonerules(cx)
        if not bases:
            return "SKIP", "aucune base ZoneRules"
        n = 0
        for (commune, _code), rules in bases:
            r_lo = dataclasses.replace(rules, pleine_terre_pct=10.0, pleine_terre_compose=None)
            r_hi = dataclasses.replace(rules, pleine_terre_pct=60.0, pleine_terre_compose=None)
            for s in (1000.0, 3000.0):
                f_lo = estimate_capacity(r_lo, s)
                f_hi = estimate_capacity(r_hi, s)
                n += 1
                if not f_lo.constructible:
                    continue
                e_lo = _emprise(f_lo)
                e_hi = _emprise(f_hi) if f_hi.constructible else 0.0
                if e_hi > e_lo + EPS:
                    return ("ECART",
                            f"{commune}/{rules.code} pleine terre 10→60 %, terrain {s:g} : emprise "
                            f"{e_lo:g}→{e_hi:g} (devrait être ≤)")
        return "OK", f"emprise non croissante quand la pleine terre ↑ ({n} cas, {len(bases)} zones)"
    return check


def _mk_check_contrainte(champ, valeur, nom, sortie_fn, sortie_nom):
    """ajout d'une contrainte rédhibitoire / dégradante ⇒ capacité (SDP ou logements) ≤. Le facteur
    de modulation ∈ [0,1] ne peut qu'abaisser. `champ`/`valeur` = l'input de Contraintes à poser."""
    def check(cx, api):
        bases = _bases_zonerules(cx)
        if not bases:
            return "SKIP", "aucune base ZoneRules"
        n = 0
        for (commune, _code), rules in bases:
            c = Contraintes(**{champ: valeur})
            for s in (1000.0, 3000.0):
                f_sans = estimate_capacity(rules, s)
                f_avec = estimate_capacity(rules, s, contraintes=c)
                n += 1
                if not f_sans.constructible:
                    continue
                v_sans = sortie_fn(f_sans)
                v_avec = sortie_fn(f_avec) if f_avec.constructible else 0.0
                if v_avec > v_sans + EPS:
                    return ("ECART",
                            f"{commune}/{rules.code} +{nom}, terrain {s:g} : {sortie_nom} "
                            f"{v_sans:g}→{v_avec:g} (devrait être ≤)")
        return "OK", f"{sortie_nom} non croissante quand +{nom} ({n} cas, {len(bases)} zones)"
    return check


def _mk_check_sdp_identite():
    """identité par construction : SDP = emprise_bâtie × niveaux (footprint × niveaux). On la vérifie
    comme relation : SDP / (emprise_constructible × coef_occ × niveaux) ≈ 1 quand niveaux>0."""
    def check(cx, api):
        bases = _bases_zonerules(cx)
        if not bases:
            return "SKIP", "aucune base ZoneRules"
        hyp = Hypotheses()
        n = 0
        for (commune, _code), rules in bases:
            for s in _SURFACES:
                f = estimate_capacity(rules, s, hyp=hyp)
                if not f.constructible:
                    continue
                niv = _niveaux(f)
                emp_bat = float((f.fourchette or {}).get("emprise_batie_max_m2") or 0.0)
                sdp = _sdp(f)
                n += 1
                attendu = emp_bat * niv
                if abs(sdp - attendu) > max(2.0, 0.01 * attendu):
                    return ("ECART",
                            f"{commune}/{rules.code} terrain {s:g} : SDP {sdp:g} ≠ emprise_bâtie "
                            f"{emp_bat:g} × niveaux {niv} = {attendu:g}")
        return "OK", f"SDP = emprise_bâtie × niveaux (identité, {n} cas)"
    return check


def _mk_check_niveaux_sdp_coherence():
    """niveaux ≥ 1 dès que constructible et SDP > 0 ; niveaux croît avec hé (déjà couvert), ici :
    une SDP > 0 ⇒ emprise_constructible > 0 (pas de SDP sans emprise). Invariant de signe."""
    def check(cx, api):
        bases = _bases_zonerules(cx)
        if not bases:
            return "SKIP", "aucune base ZoneRules"
        n = 0
        for (commune, _code), rules in bases:
            for s in _SURFACES:
                f = estimate_capacity(rules, s)
                if not f.constructible:
                    continue
                n += 1
                if _sdp(f) > 0 and _emprise(f) <= 0:
                    return ("ECART",
                            f"{commune}/{rules.code} terrain {s:g} : SDP {_sdp(f):g}>0 mais emprise "
                            f"{_emprise(f):g} ≤ 0 (SDP sans emprise)")
                if _sdp(f) > 0 and _niveaux(f) < 1:
                    return ("ECART",
                            f"{commune}/{rules.code} terrain {s:g} : SDP>0 mais niveaux {_niveaux(f)}<1")
        return "OK", f"pas de SDP sans emprise ni niveaux ({n} cas)"
    return check


# ════════════════════════════════════════════════════════════════════════════════════════════
#  2) bilan de REVENTE (financier_bilan.calculer_revente) — PUR, synthétique
# ════════════════════════════════════════════════════════════════════════════════════════════
_REVENTE_BASE = dict(prix_achat=250_000.0, prix_revente=500_000.0, frais_acq_pct=7.0,
                     travaux=80_000.0, duree_portage=18.0, taux_apport=5.0)
# plusieurs points de départ pour varier (achat, revente, travaux)
_REVENTE_CAS = [
    dict(_REVENTE_BASE),
    dict(_REVENTE_BASE, prix_achat=120_000.0, prix_revente=300_000.0, travaux=40_000.0),
    dict(_REVENTE_BASE, prix_achat=600_000.0, prix_revente=1_200_000.0, travaux=200_000.0),
    dict(_REVENTE_BASE, prix_achat=90_000.0, prix_revente=180_000.0, travaux=10_000.0, duree_portage=6.0),
]


def _mk_check_revente(champ, sens, nom):
    """perturbe `champ` de +20 % (tenant le reste) ; `sens`=+1 ⇒ marge ≥, -1 ⇒ marge ≤."""
    def check(cx, api):
        n = 0
        for base in _REVENTE_CAS:
            r0 = FBILAN.calculer_revente(base)
            h = dict(base)
            h[champ] = float(base[champ]) * 1.2
            r1 = FBILAN.calculer_revente(h)
            n += 1
            if not (r0.get("etablissable") and r1.get("etablissable")):
                continue
            m0, m1 = r0["marge"], r1["marge"]
            ok = (m1 >= m0 - EPS) if sens > 0 else (m1 <= m0 + EPS)
            if not ok:
                return ("ECART",
                        f"revente {nom} {base[champ]:g}→{h[champ]:g} : marge {m0:g}→{m1:g} "
                        f"(devrait {'≥' if sens > 0 else '≤'})")
        return "OK", f"marge de revente {'croît' if sens > 0 else 'décroît'} avec {nom} ({n} cas)"
    return check


def _mk_check_revente_taux_marge(champ, sens, nom):
    """taux de marge (%) = marge/revente — même sens que la marge pour achat/travaux/frais (revente
    fixe) ; pour la revente c'est non trivial (num ET dénom bougent) → on ne teste PAS la revente."""
    def check(cx, api):
        n = 0
        for base in _REVENTE_CAS:
            r0 = FBILAN.calculer_revente(base)
            h = dict(base)
            h[champ] = float(base[champ]) * 1.2
            r1 = FBILAN.calculer_revente(h)
            n += 1
            if r0.get("taux_marge_pct") is None or r1.get("taux_marge_pct") is None:
                continue
            t0, t1 = r0["taux_marge_pct"], r1["taux_marge_pct"]
            ok = (t1 >= t0 - 1e-3) if sens > 0 else (t1 <= t0 + 1e-3)
            if not ok:
                return ("ECART",
                        f"revente {nom} ×1,2 : taux de marge {t0:g}→{t1:g}% "
                        f"(devrait {'≥' if sens > 0 else '≤'})")
        return "OK", f"taux de marge {'croît' if sens > 0 else 'décroît'} avec {nom} ({n} cas)"
    return check


# ════════════════════════════════════════════════════════════════════════════════════════════
#  3) bilan à rebours (financier_bilan.calculer) — PUR, synthétique
# ════════════════════════════════════════════════════════════════════════════════════════════
_PROG = dict(surface_vendable=800.0, surface_plancher=1000.0, surface_terrain=1500.0, logements=10)
_HYP_BASE = dict(cout=2500.0, prix_sortie=4000.0, marge_pct=9.0, honoraires_pct=12.0,
                 aleas_pct=4.0, vrd_m2=90.0, cout_place=15_000.0, frais_acq_pct=7.0,
                 prix_demande=300_000.0, duree_portage=18.0, taux_apport=5.0)
_PROG_CAS = [
    (dict(_PROG), dict(_HYP_BASE)),
    (dict(_PROG, surface_vendable=1500.0, surface_plancher=1900.0, surface_terrain=3000.0, logements=20),
     dict(_HYP_BASE, prix_sortie=3500.0, cout=2800.0)),
    (dict(_PROG, surface_vendable=400.0, surface_plancher=500.0, surface_terrain=600.0, logements=5),
     dict(_HYP_BASE, prix_sortie=5000.0, cout=2300.0, prix_demande=150_000.0)),
]


def _charge_centrale(prog, hyp):
    r = FBILAN.calculer(prog, hyp)
    return (r.get("charge") or {}).get("centrale")


def _mk_check_bilan_charge(champ, pct, sens, nom, cle="hyp"):
    """perturbe un champ hyp (ou prog) ; `sens`=+1 ⇒ charge foncière centrale ≥, -1 ⇒ ≤."""
    def check(cx, api):
        n = 0
        for prog0, hyp0 in _PROG_CAS:
            src = hyp0 if cle == "hyp" else prog0
            if src.get(champ) in (None, 0):
                continue
            prog1, hyp1 = dict(prog0), dict(hyp0)
            (hyp1 if cle == "hyp" else prog1)[champ] = float(src[champ]) * pct
            c0 = _charge_centrale(prog0, hyp0)
            c1 = _charge_centrale(prog1, hyp1)
            n += 1
            if c0 is None or c1 is None:
                continue
            ok = (c1 >= c0 - 1.0) if sens > 0 else (c1 <= c0 + 1.0)
            if not ok:
                return ("ECART",
                        f"bilan {nom} ×{pct:g} : charge centrale {c0:.0f}→{c1:.0f} "
                        f"(devrait {'≥' if sens > 0 else '≤'})")
        return "OK", f"charge foncière {'croît' if sens > 0 else 'décroît'} avec {nom} ({n} cas)"
    return check


def _mk_check_bilan_ca():
    """prix de sortie ↑ ⇒ CA HT ≥ ; surface vendable ↑ ⇒ CA HT ≥."""
    def check(cx, api):
        n = 0
        for prog0, hyp0 in _PROG_CAS:
            # prix de sortie
            r0 = FBILAN.calculer(prog0, hyp0)
            r1 = FBILAN.calculer(prog0, dict(hyp0, prix_sortie=hyp0["prix_sortie"] * 1.3))
            n += 1
            if r0["ca_ht"] is not None and r1["ca_ht"] is not None and r1["ca_ht"] < r0["ca_ht"] - 1.0:
                return ("ECART", f"prix sortie ×1,3 : CA {r0['ca_ht']:.0f}→{r1['ca_ht']:.0f} (devrait ≥)")
            # surface vendable
            r2 = FBILAN.calculer(dict(prog0, surface_vendable=prog0["surface_vendable"] * 1.3), hyp0)
            n += 1
            if r0["ca_ht"] is not None and r2["ca_ht"] is not None and r2["ca_ht"] < r0["ca_ht"] - 1.0:
                return ("ECART", f"vendable ×1,3 : CA {r0['ca_ht']:.0f}→{r2['ca_ht']:.0f} (devrait ≥)")
        return "OK", f"CA HT croît avec prix de sortie ET surface vendable ({n} cas)"
    return check


def _mk_check_bilan_prix_revient():
    """prix demandé ↑ ⇒ prix de revient €/m² ≥ (foncier retenu = prix demandé entre au numérateur).
    coût de construction ↑ ⇒ prix de revient ≥ (postes croissent)."""
    def check(cx, api):
        n = 0
        for prog0, hyp0 in _PROG_CAS:
            r0 = FBILAN.calculer(prog0, hyp0)
            r1 = FBILAN.calculer(prog0, dict(hyp0, prix_demande=hyp0["prix_demande"] * 1.5))
            n += 1
            if (r0.get("prix_revient") is not None and r1.get("prix_revient") is not None
                    and r1["prix_revient"] < r0["prix_revient"] - EPS):
                return ("ECART", f"prix demandé ×1,5 : prix de revient "
                        f"{r0['prix_revient']:.0f}→{r1['prix_revient']:.0f} (devrait ≥)")
            r2 = FBILAN.calculer(prog0, dict(hyp0, cout=hyp0["cout"] * 1.3))
            n += 1
            if (r0.get("prix_revient") is not None and r2.get("prix_revient") is not None
                    and r2["prix_revient"] < r0["prix_revient"] - EPS):
                return ("ECART", f"coût ×1,3 : prix de revient "
                        f"{r0['prix_revient']:.0f}→{r2['prix_revient']:.0f} (devrait ≥)")
        return "OK", f"prix de revient croît avec prix demandé ET coût de construction ({n} cas)"
    return check


def _mk_check_bilan_portage():
    """durée de portage ↑ et taux d'apport ↑ ⇒ poste portage ↑ ⇒ charge foncière ≤."""
    def check(cx, api):
        n = 0
        for champ, nom in (("duree_portage", "durée de portage"), ("taux_apport", "taux d'apport")):
            for prog0, hyp0 in _PROG_CAS:
                if hyp0.get(champ) in (None, 0):
                    continue
                c0 = _charge_centrale(prog0, hyp0)
                c1 = _charge_centrale(prog0, dict(hyp0, **{champ: hyp0[champ] * 1.5}))
                n += 1
                if c0 is None or c1 is None:
                    continue
                if c1 > c0 + 1.0:
                    return ("ECART", f"bilan {nom} ×1,5 : charge centrale {c0:.0f}→{c1:.0f} (devrait ≤)")
        return "OK", f"charge foncière décroît avec durée et taux de portage ({n} cas)"
    return check


def _mk_check_bilan_marge_residuelle():
    """prix demandé ↑ ⇒ marge résiduelle % ≤ et écart au prix demandé ≤ (on paie plus cher le foncier)."""
    def check(cx, api):
        n = 0
        for prog0, hyp0 in _PROG_CAS:
            r0 = FBILAN.calculer(prog0, hyp0)
            r1 = FBILAN.calculer(prog0, dict(hyp0, prix_demande=hyp0["prix_demande"] * 1.5))
            n += 1
            if (r0.get("marge_residuelle_pct") is not None
                    and r1.get("marge_residuelle_pct") is not None
                    and r1["marge_residuelle_pct"] > r0["marge_residuelle_pct"] + 1e-3):
                return ("ECART", f"prix demandé ×1,5 : marge résiduelle "
                        f"{r0['marge_residuelle_pct']:.1f}→{r1['marge_residuelle_pct']:.1f}% (devrait ≤)")
            if (r0.get("ecart_prix_demande") is not None and r1.get("ecart_prix_demande") is not None
                    and r1["ecart_prix_demande"] > r0["ecart_prix_demande"] + 1.0):
                return ("ECART", f"prix demandé ×1,5 : écart charge−demandé "
                        f"{r0['ecart_prix_demande']:.0f}→{r1['ecart_prix_demande']:.0f} (devrait ≤)")
        return "OK", f"marge résiduelle % et écart décroissent avec le prix demandé ({n} cas)"
    return check


# ════════════════════════════════════════════════════════════════════════════════════════════
#  4) taxe d'aménagement (taxe_amenagement.calculer) — PUR (config datée)
# ════════════════════════════════════════════════════════════════════════════════════════════
_TAXE_SURF = [50.0, 150.0, 400.0]
_TAXE_TAUX = [2.0, 5.0]


def _mk_check_taxe_surface(cle_sortie, nom):
    """surface taxable ↑ ⇒ assiette (et total) ≥ (hors résidence principale, qui a un abattement
    plafonné — on la traite ailleurs). Construction simple, aucune exonération."""
    def check(cx, api):
        n = 0
        for s in _TAXE_SURF:
            for t in _TAXE_TAUX:
                r0 = TAXE.calculer(surface_taxable_m2=s, taux_communal_pct=t)
                r1 = TAXE.calculer(surface_taxable_m2=s * 1.5, taux_communal_pct=t)
                n += 1
                v0, v1 = r0.get(cle_sortie), r1.get(cle_sortie)
                if v0 is None or v1 is None:
                    continue
                if v1 < v0 - EPS:
                    return ("ECART",
                            f"taxe surface {s:g}→{s*1.5:g} m², taux {t:g}% : {nom} {v0:g}→{v1:g} "
                            f"(devrait ≥)")
        return "OK", f"{nom} croît avec la surface taxable ({n} cas)"
    return check


def _mk_check_taxe_taux():
    """taux communal ↑ ⇒ part communale et total ≥ (assiette fixe)."""
    def check(cx, api):
        n = 0
        for s in _TAXE_SURF:
            r0 = TAXE.calculer(surface_taxable_m2=s, taux_communal_pct=2.0)
            r1 = TAXE.calculer(surface_taxable_m2=s, taux_communal_pct=5.0)
            n += 1
            for cle in ("part_communale_eur", "total_eur"):
                v0, v1 = r0.get(cle), r1.get(cle)
                if v0 is None or v1 is None:
                    continue
                if v1 < v0 - EPS:
                    return ("ECART", f"taxe taux 2→5 %, surface {s:g} : {cle} {v0:g}→{v1:g} (devrait ≥)")
        return "OK", f"part communale et total croissent avec le taux ({n} cas)"
    return check


def _mk_check_taxe_forfait(champ, valeur_bas, valeur_haut, nom):
    """un forfait d'installation (piscine m² / PV sol m² / stationnement ext. / éoliennes) ↑ ⇒
    assiette ≥ (chaque forfait ajoute une assiette propre positive)."""
    def check(cx, api):
        n = 0
        for s in (0.0, 100.0):
            r0 = TAXE.calculer(surface_taxable_m2=s, taux_communal_pct=5.0, **{champ: valeur_bas})
            r1 = TAXE.calculer(surface_taxable_m2=s, taux_communal_pct=5.0, **{champ: valeur_haut})
            n += 1
            a0, a1 = r0["assiette_eur"], r1["assiette_eur"]
            if a1 < a0 - EPS:
                return ("ECART",
                        f"taxe forfait {nom} {valeur_bas:g}→{valeur_haut:g} : assiette {a0:g}→{a1:g} "
                        f"(devrait ≥)")
        return "OK", f"assiette croît avec le forfait {nom} ({n} cas)"
    return check


def _mk_check_taxe_taux_dep():
    """taux départemental ↑ ⇒ part départementale et total ≥ (assiette fixe)."""
    def check(cx, api):
        n = 0
        for s in _TAXE_SURF:
            r0 = TAXE.calculer(surface_taxable_m2=s, taux_communal_pct=5.0, taux_departemental_pct=1.0)
            r1 = TAXE.calculer(surface_taxable_m2=s, taux_communal_pct=5.0, taux_departemental_pct=2.5)
            n += 1
            for cle in ("part_departementale_eur", "total_eur"):
                v0, v1 = r0.get(cle), r1.get(cle)
                if v0 is None or v1 is None:
                    continue
                if v1 < v0 - EPS:
                    return ("ECART", f"taxe taux dép. 1→2,5 %, surface {s:g} : {cle} {v0:g}→{v1:g} (devrait ≥)")
        return "OK", f"part départementale et total croissent avec le taux départemental ({n} cas)"
    return check


def _mk_check_taxe_logement_aide():
    """logement aidé (abattement −50 % sur TOUTE la surface) ⇒ assiette ≤ construction pleine."""
    def check(cx, api):
        n = 0
        for s in (100.0, 300.0):
            r_plein = TAXE.calculer(surface_taxable_m2=s, taux_communal_pct=5.0)
            r_aide = TAXE.calculer(surface_taxable_m2=s, taux_communal_pct=5.0, logement_aide=True)
            n += 1
            if r_aide["assiette_eur"] > r_plein["assiette_eur"] + EPS:
                return ("ECART", f"taxe logement aidé surface {s:g} : assiette aidé {r_aide['assiette_eur']:g} "
                        f"> plein {r_plein['assiette_eur']:g} (abattement devrait réduire)")
        return "OK", f"assiette logement aidé ≤ assiette pleine ({n} cas)"
    return check


def _mk_check_taxe_abattement_rp():
    """abattement résidence principale ⇒ assiette ≤ (−50 % sur les 100 premiers m² / logement).
    À surface, taux, logements égaux : assiette(RP) ≤ assiette(ni RP ni aidé)."""
    def check(cx, api):
        n = 0
        for s in (80.0, 100.0, 250.0):
            r_plein = TAXE.calculer(surface_taxable_m2=s, taux_communal_pct=5.0)
            r_rp = TAXE.calculer(surface_taxable_m2=s, taux_communal_pct=5.0,
                                 residence_principale=True, nb_logements=1)
            n += 1
            if r_rp["assiette_eur"] > r_plein["assiette_eur"] + EPS:
                return ("ECART", f"taxe RP surface {s:g} : assiette RP {r_rp['assiette_eur']:g} > plein "
                        f"{r_plein['assiette_eur']:g} (abattement devrait réduire)")
        return "OK", f"assiette RP ≤ assiette pleine (abattement, {n} cas)"
    return check


def _mk_check_taxe_abattement_logements():
    """à surface RP égale, plus de logements ⇒ abattement plus large ⇒ assiette ≤ (plafond
    d'abattement = 100 m² × nb_logements : il croît, donc l'assiette décroît ou reste égale)."""
    def check(cx, api):
        n = 0
        for s in (250.0, 500.0):
            r1 = TAXE.calculer(surface_taxable_m2=s, taux_communal_pct=5.0,
                               residence_principale=True, nb_logements=1)
            r3 = TAXE.calculer(surface_taxable_m2=s, taux_communal_pct=5.0,
                               residence_principale=True, nb_logements=3)
            n += 1
            if r3["assiette_eur"] > r1["assiette_eur"] + EPS:
                return ("ECART", f"taxe RP surface {s:g} : assiette nb_log=3 {r3['assiette_eur']:g} > "
                        f"nb_log=1 {r1['assiette_eur']:g} (plus de logements → abattement plus large)")
        return "OK", f"assiette RP décroît quand le nombre de logements croît ({n} cas)"
    return check


def _mk_check_taxe_exoneration():
    """surface exonérée de plein droit ⇒ 0 € d'assiette pour cette surface : total(exo) ≤ total(même
    surface imposée). On compare 100 m² exonérés (agricole) vs 100 m² taxables, reste égal."""
    def check(cx, api):
        n = 0
        for s_exo in (100.0, 300.0):
            r_exo = TAXE.calculer(surface_taxable_m2=0.0, surface_exoneree_m2=s_exo,
                                  motif_exoneration="agricole", taux_communal_pct=5.0)
            r_tax = TAXE.calculer(surface_taxable_m2=s_exo, taux_communal_pct=5.0)
            n += 1
            if (r_exo["total_eur"] or 0) > (r_tax["total_eur"] or 0) + EPS:
                return ("ECART", f"taxe exonération {s_exo:g} m² : total exonéré {r_exo['total_eur']} > "
                        f"total taxé {r_tax['total_eur']} (exonération devrait ≤)")
        return "OK", f"total exonéré ≤ total taxé à surface égale ({n} cas)"
    return check


def _mk_check_taxe_rap():
    """la redevance d'archéologie préventive (0,40 % de l'assiette) croît avec l'assiette : surface
    taxable ↑ ⇒ rap_eur ≥. Relation interne (rap = assiette × 0,4 %)."""
    def check(cx, api):
        n = 0
        for s in _TAXE_SURF:
            r0 = TAXE.calculer(surface_taxable_m2=s, taux_communal_pct=5.0)
            r1 = TAXE.calculer(surface_taxable_m2=s * 2, taux_communal_pct=5.0)
            n += 1
            if r1["rap_eur"] < r0["rap_eur"] - EPS:
                return ("ECART", f"taxe RAP surface {s:g}→{s*2:g} : rap {r0['rap_eur']:g}→"
                        f"{r1['rap_eur']:g} (devrait ≥)")
        return "OK", f"redevance archéologie croît avec l'assiette ({n} cas)"
    return check


# ════════════════════════════════════════════════════════════════════════════════════════════
#  GÉNÉRATEUR
# ════════════════════════════════════════════════════════════════════════════════════════════
def generer(cx) -> tuple[list[RuleSpec], list[Ecartee]]:
    specs: list[RuleSpec] = []
    ecartees: list[Ecartee] = []

    def add(id_, source, libelle, gravite, attendu, check):
        specs.append(RuleSpec(id=id_, famille="F3", source=source, libelle=libelle,
                              gravite=gravite, attendu=attendu, check=check))

    # ── 1) estimate_capacity : surface ↑ ⇒ sorties ≥ ──────────────────────────────────────────
    for sortie_fn, nom in ((_sdp, "sdp"), (_emprise, "emprise"), (_niveaux, "niveaux"),
                           (_logts_hi, "logements")):
        # niveaux ne dépend PAS de la surface (hauteur seule) → la relation est « ≥ » triviale mais
        # vraie (non décroissante) ; on la garde (couple input=surface/output=niveaux, monotone ≥).
        add(f"F3.engine.surface_up.{nom}_ge", "faisabilite.engine.estimate_capacity",
            f"surface terrain ↑ (règles égales) ⇒ {nom} non décroissant",
            "INCOHERENT", f"{nom} ≥", _mk_check_surface(sortie_fn, nom))

    # ── 1) hauteur hé ↑ ⇒ niveaux/SDP/logements ≥ ─────────────────────────────────────────────
    for sortie_fn, nom in ((_niveaux, "niveaux"), (_sdp, "sdp"), (_logts_hi, "logements")):
        add(f"F3.engine.hauteur_up.{nom}_ge", "faisabilite.engine.estimate_capacity",
            f"hauteur hé ↑ ⇒ {nom} non décroissant",
            "INCOHERENT", f"{nom} ≥", _mk_check_hauteur(sortie_fn, nom))
    # emprise NE dépend PAS de la hauteur (bornée au sol) → écartée : relation sans effet, non informative
    ecartees.append(Ecartee("F3.engine.hauteur_up.emprise_ge", "F3",
                            "faisabilite.engine.estimate_capacity",
                            "l'emprise au sol est indépendante de la hauteur (bornée par reculs/CES/"
                            "pleine terre) : la relation hauteur→emprise n'a aucun effet — non informative"))

    # ── 1) hauteur FAÎTAGE hf ↑ ⇒ niveaux/SDP ≥ (chemin distinct de hé) ────────────────────────
    for sortie_fn, nom in ((_niveaux, "niveaux"), (_sdp, "sdp")):
        add(f"F3.engine.faitage_up.{nom}_ge", "faisabilite.engine.estimate_capacity",
            f"hauteur faîtage hf ↑ (sans hé) ⇒ {nom} non décroissant", "INCOHERENT", f"{nom} ≥",
            _mk_check_hf(sortie_fn, nom))

    # ── 1) R+n imposé (niveaux_max) ↑ ⇒ niveaux/SDP ≥ ─────────────────────────────────────────
    for sortie_fn, nom in ((_niveaux, "niveaux"), (_sdp, "sdp")):
        add(f"F3.engine.niveaux_max_up.{nom}_ge", "faisabilite.engine.estimate_capacity",
            f"R+n imposé au règlement ↑ ⇒ {nom} non décroissant", "INCOHERENT", f"{nom} ≥",
            _mk_check_niveaux_max(sortie_fn, nom))

    # ── 1) hypothèses de modélisation : occupation / rendement / surface par logement ─────────
    add("F3.engine.coef_occupation_up.emprise_batie_ge", "faisabilite.engine.estimate_capacity",
        "coefficient d'occupation du gabarit ↑ ⇒ emprise bâtie ≥", "INCOHERENT", "emprise bâtie ≥",
        _mk_check_hyp_coef("coef_occupation", 1.5, +1, "occupation du gabarit", _emprise_batie, "emprise bâtie"))
    add("F3.engine.coef_occupation_up.sdp_ge", "faisabilite.engine.estimate_capacity",
        "coefficient d'occupation du gabarit ↑ ⇒ SDP ≥", "INCOHERENT", "sdp ≥",
        _mk_check_hyp_coef("coef_occupation", 1.5, +1, "occupation du gabarit", _sdp, "sdp"))
    add("F3.engine.coef_rendement_up.shab_vendable_ge", "faisabilite.engine.estimate_capacity",
        "coefficient de rendement SDP→habitable ↑ ⇒ surface habitable vendable ≥", "INCOHERENT",
        "shab vendable ≥",
        _mk_check_hyp_coef("coef_rendement", 1.2, +1, "rendement SDP→habitable", _shab_vendable, "shab vendable"))
    add("F3.engine.logement_m2_down.logements_ge", "faisabilite.engine.estimate_capacity",
        "surface moyenne par logement ↓ (logements plus petits) ⇒ nombre de logements ≥", "INCOHERENT",
        "logements ≥", _mk_check_logement_m2())

    # ── 1) recul ↑ ⇒ emprise ≤ ────────────────────────────────────────────────────────────────
    add("F3.engine.recul_voirie_up.emprise_le", "faisabilite.engine.estimate_capacity",
        "recul sur voie ↑ ⇒ emprise constructible ≤", "INCOHERENT", "emprise ≤",
        _mk_check_recul("recul_voirie_m", "recul voie"))
    add("F3.engine.recul_limites_up.emprise_le", "faisabilite.engine.estimate_capacity",
        "recul limites séparatives ↑ ⇒ emprise constructible ≤", "INCOHERENT", "emprise ≤",
        _mk_check_recul("recul_limites_sep_m", "recul limites"))

    # ── 1) CES ↑ ⇒ emprise/SDP ≥ ; pleine terre ↑ ⇒ emprise ≤ ─────────────────────────────────
    add("F3.engine.ces_up.emprise_ge", "faisabilite.engine.estimate_capacity",
        "CES (emprise au sol %) ↑ ⇒ emprise constructible ≥", "INCOHERENT", "emprise ≥",
        _mk_check_ces(_emprise, "emprise"))
    add("F3.engine.ces_up.sdp_ge", "faisabilite.engine.estimate_capacity",
        "CES (emprise au sol %) ↑ ⇒ SDP ≥", "INCOHERENT", "sdp ≥",
        _mk_check_ces(_sdp, "sdp"))
    add("F3.engine.pleine_terre_up.emprise_le", "faisabilite.engine.estimate_capacity",
        "pleine terre % ↑ ⇒ emprise constructible ≤", "INCOHERENT", "emprise ≤",
        _mk_check_pleine_terre())

    # ── 1) ajout d'une contrainte (zone rouge / aléa / littoral / pente) ⇒ capacité ≤ ──────────
    _CONTRAINTES = [
        ("alea_ppr", "fort", "aléa PPR fort"),
        ("alea_ppr", "moyen", "aléa PPR moyen"),
        ("alea_ppr", "faible", "aléa PPR faible"),
        ("bande_littorale", True, "bande littorale"),
        ("agricole_sar", True, "agricole SAR"),
        ("pente_pct", 35.0, "pente 35 %"),
        ("pente_pct", 20.0, "pente 20 %"),
    ]
    for champ, valeur, nom in _CONTRAINTES:
        for sortie_fn, sortie_nom in ((_sdp, "sdp"), (_logts_hi, "logements")):
            cid = f"F3.engine.contrainte.{champ}_{str(valeur).replace('.', '_')}.{sortie_nom}_le"
            add(cid, "faisabilite.engine.estimate_capacity",
                f"ajout de « {nom} » (zone/contrainte restrictive) ⇒ {sortie_nom} ≤",
                "INCOHERENT", f"{sortie_nom} ≤",
                _mk_check_contrainte(champ, valeur, nom, sortie_fn, sortie_nom))

    # ── 1) identités / invariants de signe ─────────────────────────────────────────────────────
    add("F3.engine.identite.sdp_eq_emprise_niveaux", "faisabilite.engine.estimate_capacity",
        "SDP = emprise bâtie × niveaux (identité de construction)", "INCOHERENT",
        "SDP = emp×niv", _mk_check_sdp_identite())
    add("F3.engine.signe.sdp_implique_emprise_niveaux", "faisabilite.engine.estimate_capacity",
        "SDP > 0 ⇒ emprise > 0 et niveaux ≥ 1 (pas de SDP sans support)", "INCOHERENT",
        "cohérence de signe", _mk_check_niveaux_sdp_coherence())

    # ── 2) bilan de revente : marge décroît en achat/travaux/frais, croît en revente ──────────
    for champ, sens, nom in (("prix_achat", -1, "prix d'achat"), ("travaux", -1, "travaux"),
                             ("frais_acq_pct", -1, "frais d'acquisition %"),
                             ("taux_apport", -1, "taux de portage"),
                             ("duree_portage", -1, "durée de portage"),
                             ("prix_revente", +1, "prix de revente")):
        add(f"F3.revente.{champ}.marge_{'ge' if sens > 0 else 'le'}",
            "exports.financier_bilan.calculer_revente",
            f"{nom} ↑ ⇒ marge de revente {'≥' if sens > 0 else '≤'}", "INCOHERENT",
            f"marge {'≥' if sens > 0 else '≤'}", _mk_check_revente(champ, sens, nom))
    # taux de marge % : même sens pour les postes de COÛT (revente fixe), pas pour la revente
    for champ, sens, nom in (("prix_achat", -1, "prix d'achat"), ("travaux", -1, "travaux"),
                             ("frais_acq_pct", -1, "frais d'acquisition %")):
        add(f"F3.revente.{champ}.taux_marge_le", "exports.financier_bilan.calculer_revente",
            f"{nom} ↑ ⇒ taux de marge % ≤", "INCOHERENT", "taux de marge ≤",
            _mk_check_revente_taux_marge(champ, sens, nom))
    ecartees.append(Ecartee("F3.revente.prix_revente.taux_marge_ge", "F3",
                            "exports.financier_bilan.calculer_revente",
                            "taux de marge = marge/revente : revente ↑ fait croître num ET dénom — "
                            "le sens n'est PAS garanti par construction (dépend du coût total) → écartée"))

    # ── 3) bilan à rebours : charge foncière ───────────────────────────────────────────────────
    for champ, pct, sens, nom, cle in (
            ("prix_sortie", 1.3, +1, "prix de sortie", "hyp"),
            ("cout", 1.3, -1, "coût de construction", "hyp"),
            ("marge_pct", 1.5, -1, "marge visée %", "hyp"),
            ("honoraires_pct", 1.5, -1, "honoraires %", "hyp"),
            ("aleas_pct", 1.5, -1, "aléas %", "hyp"),
            ("vrd_m2", 1.5, -1, "VRD €/m²", "hyp"),
            ("cout_place", 1.5, -1, "coût par place", "hyp"),
            ("surface_vendable", 1.3, +1, "surface vendable", "prog")):
        add(f"F3.bilan.{champ}.charge_{'ge' if sens > 0 else 'le'}",
            "exports.financier_bilan.calculer",
            f"{nom} ↑ ⇒ charge foncière supportable {'≥' if sens > 0 else '≤'}", "INCOHERENT",
            f"charge {'≥' if sens > 0 else '≤'}", _mk_check_bilan_charge(champ, pct, sens, nom, cle))
    add("F3.bilan.ca_monotone", "exports.financier_bilan.calculer",
        "prix de sortie ↑ et surface vendable ↑ ⇒ CA HT ≥", "INCOHERENT", "CA ≥",
        _mk_check_bilan_ca())
    add("F3.bilan.prix_demande.marge_residuelle_le", "exports.financier_bilan.calculer",
        "prix demandé ↑ ⇒ marge résiduelle % ≤ et écart (charge−demandé) ≤", "INCOHERENT",
        "marge résiduelle / écart ≤", _mk_check_bilan_marge_residuelle())
    add("F3.bilan.prix_revient_monotone", "exports.financier_bilan.calculer",
        "prix demandé ↑ et coût de construction ↑ ⇒ prix de revient €/m² ≥", "INCOHERENT",
        "prix de revient ≥", _mk_check_bilan_prix_revient())
    add("F3.bilan.portage.charge_le", "exports.financier_bilan.calculer",
        "durée et taux de portage ↑ ⇒ poste portage ↑ ⇒ charge foncière ≤", "INCOHERENT",
        "charge ≤", _mk_check_bilan_portage())

    # ── 4) taxe d'aménagement ──────────────────────────────────────────────────────────────────
    for cle, nom in (("assiette_eur", "assiette"), ("total_eur", "total"),
                     ("part_communale_eur", "part communale"), ("rap_eur", "redevance archéo")):
        add(f"F3.taxe.surface_up.{cle}_ge", "taxe_amenagement.calculer",
            f"surface taxable ↑ ⇒ {nom} ≥", "FAUX-CLIENT", f"{nom} ≥",
            _mk_check_taxe_surface(cle, nom))
    add("F3.taxe.taux_up.part_total_ge", "taxe_amenagement.calculer",
        "taux communal ↑ ⇒ part communale et total ≥ (assiette fixe)", "FAUX-CLIENT",
        "part/total ≥", _mk_check_taxe_taux())
    add("F3.taxe.taux_dep_up.part_total_ge", "taxe_amenagement.calculer",
        "taux départemental ↑ ⇒ part départementale et total ≥ (assiette fixe)", "FAUX-CLIENT",
        "part dép./total ≥", _mk_check_taxe_taux_dep())
    add("F3.taxe.logement_aide.assiette_le", "taxe_amenagement.calculer",
        "logement aidé (abattement −50 % sur toute la surface) ⇒ assiette ≤ construction pleine",
        "FAUX-CLIENT", "assiette aidé ≤", _mk_check_taxe_logement_aide())
    for champ, vb, vh, nom in (("piscine_m2", 0.0, 50.0, "piscine"),
                               ("pv_sol_m2", 0.0, 100.0, "PV au sol"),
                               ("stationnement_ext_places", 0, 5, "stationnement ext."),
                               ("eoliennes_mats", 0, 2, "éoliennes")):
        add(f"F3.taxe.forfait.{champ}.assiette_ge", "taxe_amenagement.calculer",
            f"forfait {nom} ↑ ⇒ assiette ≥", "FAUX-CLIENT", "assiette ≥",
            _mk_check_taxe_forfait(champ, vb, vh, nom))
    add("F3.taxe.rp.abattement_assiette_le", "taxe_amenagement.calculer",
        "résidence principale (abattement −50 %) ⇒ assiette ≤ construction pleine", "FAUX-CLIENT",
        "assiette RP ≤", _mk_check_taxe_abattement_rp())
    add("F3.taxe.rp.logements_up.assiette_le", "taxe_amenagement.calculer",
        "nombre de logements RP ↑ ⇒ assiette ≤ (plafond d'abattement 100 m²/logement plus large)",
        "FAUX-CLIENT", "assiette ≤", _mk_check_taxe_abattement_logements())
    add("F3.taxe.exoneration.total_le", "taxe_amenagement.calculer",
        "surface exonérée de plein droit ⇒ total ≤ même surface taxée", "FAUX-CLIENT",
        "total exonéré ≤", _mk_check_taxe_exoneration())
    add("F3.taxe.rap.assiette_up.ge", "taxe_amenagement.calculer",
        "assiette ↑ ⇒ redevance archéologie (0,40 %) ≥", "INCOHERENT", "rap ≥",
        _mk_check_taxe_rap())

    return specs, ecartees


# ════════════════════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    cx = connexion()
    specs, ecartees = generer(cx)
    print(f"F3 — métamorphiques : {len(specs)} règles générées, {len(ecartees)} écartées avant de tourner")
    for e in ecartees:
        print(f"  · écartée {e.id} — {e.raison}")
    resultats = run_specs(cx, specs, None)
    b = bilan(resultats)
    print(f"\nBILAN : OK={b['OK']}  ECART={b['ECART']}  SKIP={b['SKIP']}  (sur {len(specs)})")
    for r in resultats:
        if r.statut != "OK":
            print(f"  [{r.statut}] {r.spec.id} :: {r.message}")
    # détail OK compact (famille → compte)
    print("\n— aperçu OK —")
    for r in resultats:
        if r.statut == "OK":
            print(f"  OK {r.spec.id} :: {r.message}")
