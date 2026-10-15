"""F2 — Le registre : cohérence des VALEURS d'un même chiffre à TRAVERS les surfaces.

Généralisation de la « chasse aux données » de la vague-1 à TOUS les nombres d'un coup :
pour chaque chiffre servi sur plusieurs surfaces (liste `/parcels`, fiche `/parcels/{idu}`,
`/filtre`, export, carte/tuiles, base), la MÊME VALEUR doit apparaître partout.

Trois AXES de croisement (au-delà du registre nu, trop maigre à 19 règles) :

  AXIS 1 — liste `/parcels` vs SOURCE DE VÉRITÉ EN BASE (île, pas cher, haute valeur).
    La route liste rend, par parcelle, ~35 scalaires. Chacun a une table/colonne maîtresse
    (lue DANS le code du handler `_q_v2_list`, app.py:3624 — pas devinée). On pagine
    `/parcels?source=q_v18&commune=<C>&limit=1000` sur plusieurs communes (plusieurs milliers
    de parcelles), on joint chaque idu à sa source en base, on exige l'égalité. 1 règle/chiffre.

  AXIS 2 — liste `/parcels` vs fiche `/parcels/{idu}` (DEUX chemins de code distincts, échantillon).
    Pour chaque chiffre partagé, la valeur liste == la valeur fiche au chemin donné. Échantillon
    borné (≤ ~120 fiches distinctes, réutilisées via cache, sous le quota 300/j). 1 règle/chiffre.

  AXIS 3 — `/filtre.page` vs liste, et export `/parcels/{idu}/export` vs fiche.
    `/filtre.page` est bâti par LE MÊME `_q_v2_list` → identité stricte (invariant de parité).
    L'export est en MARKDOWN : on en extrait les rares scalaires robustes (surface, commune),
    on écarte le reste (pas un JSON scalaire).

Discipline : une règle qu'on ne peut pas câbler (surface ne porte pas le chiffre, définition
DIFFÉRENTE, cache commune vide) → `Ecartee` AVANT de tourner. Tolérance d'arrondi (≤1 m², ≤0,1
ratio). Un pur arrondi n'est PAS une violation. Lecture seule stricte, GET uniquement.

Mappings de source (lus dans app.py:3624 `_q_v2_list` et app.py:3398 geojson, VÉRIFIÉS) :
  surface_m2          → round(parcels.surface_m2)
  contenance_m2       → parcels.contenance_m2
  surface_terrain_m2  → round(COALESCE(parcels.contenance_m2, parcels.surface_m2))  (surface.py)
  bande/signal_niveau/cause/non_calculable → score_labuse (run q_v18)
  sdp_residuelle_m2   → score_labuse.sdp_residuelle_m2 (NULL si cause présente — convention liste)
  tier_v2/rang_v2/mult_v2 → parcel_p_score_v2 (run_id q_v18)
  v_band/v_score/owner_type → parcel_v_score (1 ligne/parcelle, sans run)
  zone_lib/zone_fam   → parcel_zone_plu
  completeness_score  → dryrun_parcel_evaluations (run cascade = q_v18_sources)
"""
from __future__ import annotations

import re
import time
import urllib.error
import urllib.request
from collections import defaultdict

from scripts.coherence.invariants2.noyau import (
    Ecartee,
    RuleSpec,
    api_json,
    bilan,
    connexion,
    echantillon_stratifie,
    registre_chiffres,
    registre_robinets,
    run_specs,
)

# ─────────────────────────────────────────────────────────────────────────────────────────────
# Rythme API : ~1 appel/s pour rester SOUS 60/min (protection.py). Échantillon fiche capé pour
# rester SOUS 300 fiches/jour. Les règles BASE (SQL) et liste-paginée ignorent ce cap de fiches.
# ─────────────────────────────────────────────────────────────────────────────────────────────
PAUSE_S = 1.15
N_API = 120          # fiches DISTINCTES réutilisées à travers TOUTES les règles API (< 300/jour)
TOL = 1.0            # tolérance d'arrondi (m² entiers)
TOL_RATIO = 0.1      # tolérance pour les ratios (mult_v2)
RUN = "q_v18"
RUN_CASCADE = "q_v18_sources"   # _cascade_run(q_v18) — cascade dont provient dryrun_parcel_evaluations

# Communes couvertes par l'AXE 1 (liste vs base) : un panel large mais borné (≈ 40 k parcelles
# cumulées sur ~6 communes — chaque /parcels sert jusqu'à 1000 lignes, donc on couvre le HAUT du
# classement rang de chaque commune, échantillon non trivial par chiffre). Petites+moyennes+1 grande.
COMMUNES_AXE1 = ["Bras-Panon", "Entre-Deux", "Salazie", "Cilaos",
                 "Sainte-Rose", "La Plaine-des-Palmistes", "Saint-Philippe", "Saint-Paul",
                 "L'Étang-Salé", "Les Trois-Bassins"]

_CACHE_FICHE: dict = {}
_CACHE_LISTE: dict = {}          # commune -> list[item]  (réutilisé par AXE 1, AXE 2, AXE 3)


def _get(base, path, timeout=40):
    st, p = api_json(base, path, timeout=timeout)
    time.sleep(PAUSE_S)
    return st, p


def _get_text(base, path, timeout=40):
    """Récupère une réponse TEXTE (markdown export) — api_json planterait sur le json.loads."""
    try:
        with urllib.request.urlopen(base + path, timeout=timeout) as r:
            body = r.read().decode("utf-8", "replace")
            time.sleep(PAUSE_S)
            return r.status, body
    except urllib.error.HTTPError as e:
        time.sleep(PAUSE_S)
        return e.code, None
    except Exception:
        time.sleep(PAUSE_S)
        return "ERR", None


def _fiche(base, idu):
    if idu not in _CACHE_FICHE:
        _CACHE_FICHE[idu] = _get(base, f"/parcels/{idu}?source={RUN}")
    return _CACHE_FICHE[idu]


def _liste_commune(base, commune):
    """Liste paginée d'une commune (jusqu'à 1000), mise en cache (réutilisée par tous les axes)."""
    if commune not in _CACHE_LISTE:
        st, p = _get(base, f"/parcels?source={RUN}&commune={commune}&limit=1000")
        _CACHE_LISTE[commune] = p if (st == 200 and isinstance(p, list)) else []
    return _CACHE_LISTE[commune]


def _echantillon_api(cx):
    return echantillon_stratifie(cx, 2000)[:N_API]


def _d(o, *path):
    for k in path:
        if not isinstance(o, dict):
            return None
        o = o.get(k)
    return o


def _egal(a, b, tol=TOL):
    """Égalité tolérante : numérique à `tol` près, sinon stricte en texte. None≠valeur géré amont."""
    try:
        return abs(float(a) - float(b)) <= tol
    except (TypeError, ValueError):
        return str(a) == str(b)


# ═══════════════════════════════════════════════════════════════════════════════════════════════
#  AXE 1 — liste `/parcels` vs base (île, par commune). Un seul round-trip SQL par (règle, commune) :
#  on charge la colonne maîtresse pour tous les idu de la commune d'un coup, puis compare en mémoire.
# ═══════════════════════════════════════════════════════════════════════════════════════════════
def _mk_liste_vs_base(chiffre, libelle, liste_key, sql_map, gravite="FAUX-CLIENT",
                      tol=TOL, texte=False):
    """La valeur de la LISTE (`liste_key`) == la valeur maîtresse en base pour le même idu.

    `sql_map(commune)` rend un SQL qui SELECTe (idu, valeur) pour toute la commune (1 round-trip).
    On ne compare QUE les idu où les deux côtés sont non-null (un None d'un côté = non comparable,
    PAS une violation — la liste peut masquer légitimement, cf. sdp gated-cause).
    """
    def check(cx, api):
        if not api:
            return "SKIP", "API absente"
        teste = comparables = 0
        premier_ecart = None
        ecarts = []
        for commune in COMMUNES_AXE1:
            items = _liste_commune(api, commune)
            if not items:
                continue
            # 1 round-trip : (idu -> valeur base) pour tous les idu servis de la commune
            idus = [it["idu"] for it in items if it.get("idu")]
            if not idus:
                continue
            base = {}
            try:
                with cx.conn.cursor() as cur:
                    cur.execute(sql_map(idus), (idus,))
                    for row in cur.fetchall():
                        base[row[0]] = row[1]
            except Exception as e:  # noqa: BLE001
                cx.rollback()
                return "SKIP", f"{chiffre} base indisponible : {type(e).__name__}: {e}"
            for it in items:
                idu = it.get("idu")
                vl = it.get(liste_key)
                vb = base.get(idu)
                teste += 1
                if vl is None or vb is None:
                    continue
                comparables += 1
                ok = (str(vl) == str(vb)) if texte else _egal(vl, vb, tol)
                if not ok:
                    if premier_ecart is None:
                        premier_ecart = (idu, vl, vb)
                    if len(ecarts) < 3:
                        ecarts.append({"idu": idu, "liste": vl, "base": vb})
        if premier_ecart:
            idu, vl, vb = premier_ecart
            return "ECART", (f"{idu} : liste {liste_key}={vl!r} ≠ base={vb!r} "
                             f"(comparées {comparables}/{teste}) | exemples={ecarts}")
        return "OK", f"{comparables}/{teste} parcelles comparées (liste↔base) — toutes égales"
    return RuleSpec(
        id=f"F2.liste_vs_base.{chiffre}", famille="F2",
        source=f"chiffre {chiffre} — liste /parcels vs base (source de vérité)",
        libelle=f"{libelle} : liste /parcels == base", gravite=gravite,
        attendu="valeur liste == valeur base", check=check)


# ═══════════════════════════════════════════════════════════════════════════════════════════════
#  AXE 2 — liste `/parcels` vs fiche `/parcels/{idu}` (deux chemins de code), échantillon borné.
# ═══════════════════════════════════════════════════════════════════════════════════════════════
def _mk_liste_vs_fiche(chiffre, libelle, liste_key, fiche_extr, gravite="INCOHERENT",
                       tol=TOL, texte=False):
    """La valeur de la LISTE == la valeur de la FICHE pour le même idu (deux builders distincts)."""
    def check(cx, api):
        if not api:
            return "SKIP", "API absente"
        # on part de l'échantillon stratifié ; pour chaque idu on a besoin de sa ligne de liste.
        # Les listes de commune sont déjà en cache (AXE 1) ; on y pioche par idu, et on lit la fiche.
        par_idu = {}
        for commune in COMMUNES_AXE1:
            for it in _liste_commune(api, commune):
                if it.get("idu"):
                    par_idu[it["idu"]] = it
        if not par_idu:
            return "SKIP", "aucune ligne de liste en cache"
        # On échantillonne DANS les lignes réellement servies par la liste (ordre md5 déterministe,
        # capé à N_API) — garantit que chaque idu testé a bien une ligne de liste ET une fiche
        # (sinon, un idu du tirage global tombait souvent hors du top-1000 servi → 0 comparaison).
        import hashlib as _h
        idus = sorted(par_idu, key=lambda i: _h.md5(i.encode()).hexdigest())[:N_API]
        teste = comparables = 0
        premier_ecart = None
        ecarts = []
        for idu in idus:
            it = par_idu.get(idu)
            if it is None:
                continue                      # pas dans les communes de l'AXE 1 → on saute (borné)
            st, p = _fiche(api, idu)
            if st != 200 or not isinstance(p, dict):
                continue
            teste += 1
            vl = it.get(liste_key)
            vf = fiche_extr(p)
            if vl is None or vf is None:
                continue
            comparables += 1
            ok = (str(vl) == str(vf)) if texte else _egal(vl, vf, tol)
            if not ok:
                if premier_ecart is None:
                    premier_ecart = (idu, vl, vf)
                if len(ecarts) < 3:
                    ecarts.append({"idu": idu, "liste": vl, "fiche": vf})
        if premier_ecart:
            idu, vl, vf = premier_ecart
            return "ECART", (f"{idu} : liste {liste_key}={vl!r} ≠ fiche={vf!r} "
                             f"(comparées {comparables}/{teste}) | exemples={ecarts}")
        return "OK", f"{comparables}/{teste} parcelles comparées (liste↔fiche) — toutes égales"
    return RuleSpec(
        id=f"F2.liste_vs_fiche.{chiffre}", famille="F2",
        source=f"chiffre {chiffre} — liste /parcels vs fiche /parcels/{{idu}}",
        libelle=f"{libelle} : liste == fiche", gravite=gravite,
        attendu="valeurs identiques", check=check)


# ═══════════════════════════════════════════════════════════════════════════════════════════════
#  AXE 3a — `/filtre.page` vs liste `/parcels` (même builder _q_v2_list → identité attendue).
# ═══════════════════════════════════════════════════════════════════════════════════════════════
def _mk_filtre_vs_liste(chiffre, liste_key, gravite="INCOHERENT", tol=TOL, texte=False):
    def check(cx, api):
        if not api:
            return "SKIP", "API absente"
        comparables = premier = 0
        ecart = None
        exemples = []
        for commune in COMMUNES_AXE1[:3]:          # 3 communes : /filtre est plus lourd
            liste = {it["idu"]: it for it in _liste_commune(api, commune) if it.get("idu")}
            if not liste:
                continue
            # /filtre plafonne limit à 200 (Query le=200) ; sa page est bâtie par le MÊME
            # _q_v2_list que la liste, triée par rang → les 200 premières lignes de la commune
            # recoupent le haut de la liste /parcels (limit 1000). On compare l'intersection.
            st, p = _get(api, f"/filtre?source={RUN}&commune={commune}&limit=200")
            page = (p or {}).get("page") if isinstance(p, dict) else None
            if not isinstance(page, list):
                continue
            for it in page:
                idu = it.get("idu")
                if idu not in liste:
                    continue
                vf, vl = it.get(liste_key), liste[idu].get(liste_key)
                if vf is None or vl is None:
                    continue
                comparables += 1
                ok = (str(vf) == str(vl)) if texte else _egal(vf, vl, tol)
                if not ok:
                    if ecart is None:
                        ecart = (idu, vf, vl)
                    if len(exemples) < 3:
                        exemples.append({"idu": idu, "filtre": vf, "liste": vl})
        if ecart:
            idu, vf, vl = ecart
            return "ECART", f"{idu} : /filtre {liste_key}={vf!r} ≠ liste={vl!r} | {exemples}"
        if comparables == 0:
            return "SKIP", "aucune parcelle commune /filtre↔liste"
        return "OK", f"{comparables} parcelles /filtre↔liste — toutes égales"
    return RuleSpec(
        id=f"F2.filtre_vs_liste.{chiffre}", famille="F2",
        source=f"chiffre {chiffre} — /filtre.page vs liste /parcels",
        libelle=f"{chiffre} : /filtre.page == liste (même builder)", gravite=gravite,
        attendu="valeurs identiques", check=check)


# ═══════════════════════════════════════════════════════════════════════════════════════════════
#  AXE 3b — export `/parcels/{idu}/export` (MARKDOWN) vs fiche : seuls les scalaires robustes.
# ═══════════════════════════════════════════════════════════════════════════════════════════════
def _mk_export_vs_fiche(chiffre, libelle, fiche_extr, md_extr, gravite="FAUX-CLIENT",
                        tol=TOL, texte=False, n=30):
    def check(cx, api):
        if not api:
            return "SKIP", "API absente"
        idus = _echantillon_api(cx)[:n]
        comparables = 0
        ecart = None
        exemples = []
        for idu in idus:
            stf, pf = _fiche(api, idu)
            if stf != 200 or not isinstance(pf, dict):
                continue
            ste, md = _get_text(api, f"/parcels/{idu}/export?source={RUN}")
            if ste != 200 or not isinstance(md, str):
                continue
            vf = fiche_extr(pf)
            ve = md_extr(md)
            if vf is None or ve is None:
                continue
            comparables += 1
            ok = (str(vf) == str(ve)) if texte else _egal(vf, ve, tol)
            if not ok:
                if ecart is None:
                    ecart = (idu, ve, vf)
                if len(exemples) < 3:
                    exemples.append({"idu": idu, "export": ve, "fiche": vf})
        if ecart:
            idu, ve, vf = ecart
            return "ECART", f"{idu} : export={ve!r} ≠ fiche={vf!r} | {exemples}"
        if comparables == 0:
            return "SKIP", "export ne porte pas ce scalaire de façon lisible"
        return "OK", f"{comparables} exports comparés à la fiche — tous égaux"
    return RuleSpec(
        id=f"F2.export_vs_fiche.{chiffre}", famille="F2",
        source=f"chiffre {chiffre} — export markdown vs fiche",
        libelle=f"{libelle} : export == fiche", gravite=gravite,
        attendu="valeurs identiques", check=check)


# ─── extracteurs markdown export (robustes, sinon None) ──────────────────────────────────────
_RE_SURF_CAD = re.compile(r"Surface cadastrale\s*:\s*([\d   ]+)\s*m²")
_RE_SURF_PLAN = re.compile(r"Surface\s*:\s*([\d   ]+)\s*m²")
_RE_COMMUNE = re.compile(r"\*\*Commune\s*:\*\*\s*([^·\n]+?)\s*(?:·|$)", re.MULTILINE)


def _md_surface(md):
    m = _RE_SURF_CAD.search(md) or _RE_SURF_PLAN.search(md)
    if not m:
        return None
    try:
        return int(re.sub(r"[   ]", "", m.group(1)))
    except ValueError:
        return None


def _md_commune(md):
    m = _RE_COMMUNE.search(md)
    return m.group(1).strip() if m else None


# ═══════════════════════════════════════════════════════════════════════════════════════════════
#  Carte d'EXTRACTION fiche (list key → fiche path), vérifiée par l'orchestrateur + relue à la main.
# ═══════════════════════════════════════════════════════════════════════════════════════════════
_FICHE = {
    "bande":              lambda p: _d(p, "analyse_labuse", "bande"),
    "sdp_residuelle_m2":  lambda p: _d(p, "analyse_labuse", "sdp_residuelle_m2"),
    "surface_m2":         lambda p: p.get("surface_m2"),
    "contenance_m2":      lambda p: p.get("contenance_m2"),
    "tier_v2":            lambda p: _d(p, "score_v2", "tier"),
    "rang_v2":            lambda p: _d(p, "score_v2", "rang"),
    "mult_v2":            lambda p: _d(p, "score_v2", "mult_base"),
    "v_band":             lambda p: _d(p, "score_v", "v_band"),
    "v_score":            lambda p: _d(p, "score_v", "v_score"),
    "owner_type":         lambda p: _d(p, "score_v", "owner_type"),
    "zone_lib":           lambda p: (_d(p, "reglement_plu", "zones") or [{}])[0].get("zone")
                                    if _d(p, "reglement_plu", "zones") else None,
    "zone_fam":           lambda p: _d(p, "reglement_plu", "zone_famille"),
    "signal_niveau":      lambda p: _d(p, "analyse_labuse", "signal_niveau"),
    "completeness_score": lambda p: p.get("completeness_score"),
}


# ───────────────────────────── SQL maîtres (AXE 1) ──────────────────────────────────────────
def _sql_parcels(col_expr):
    return lambda idus: f"SELECT idu, {col_expr} FROM parcels WHERE idu = ANY(%s)"


def _sql_score(col):
    return lambda idus: (f"SELECT idu, {col} FROM score_labuse "
                         f"WHERE run_label='{RUN}' AND idu = ANY(%s)")


def _sql_v2(col):
    return lambda idus: (f"SELECT parcelle_id, {col} FROM parcel_p_score_v2 "
                         f"WHERE run_id='{RUN}' AND parcelle_id = ANY(%s)")


def _sql_vscore(col):
    return lambda idus: f"SELECT parcelle_id, {col} FROM parcel_v_score WHERE parcelle_id = ANY(%s)"


def _sql_zone(col):
    return lambda idus: f"SELECT idu, {col} FROM parcel_zone_plu WHERE idu = ANY(%s)"


def _sql_completeness():
    # dryrun_parcel_evaluations (run cascade) joint à parcels par parcel_id=p.id
    return lambda idus: (f"SELECT p.idu, d.completeness_score FROM dryrun_parcel_evaluations d "
                         f"JOIN parcels p ON p.id=d.parcel_id "
                         f"WHERE d.run_label='{RUN_CASCADE}' AND p.idu = ANY(%s)")


# ═══════════════════════════════════════════════════════════════════════════════════════════════
#  Générateur
# ═══════════════════════════════════════════════════════════════════════════════════════════════
def generer(cx):
    specs: list = []
    ecartees: list = []

    chiffres = {c["id"]: c for c in registre_chiffres(cx)}
    robinets = registre_robinets(cx)

    served = defaultdict(list)
    for r in robinets:
        for cid in (r["chiffres"] or []):
            served[cid].append(r)

    # ── (1) Discipline du registre (CONSERVÉE à l'identique) : 0/1 robinet → écartés d'office ───
    for cid, c in chiffres.items():
        rs = served.get(cid, [])
        if len(rs) == 0:
            ecartees.append(Ecartee(f"F2.{cid}", "F2", f"chiffre {cid}",
                                    "aucun robinet ne le sert — hors périmètre de croisement"))
        elif len(rs) == 1:
            ecartees.append(Ecartee(f"F2.{cid}", "F2", f"chiffre {cid}",
                                    "servi par un seul robinet, pas de croisement possible"))

    multi = {cid: rs for cid, rs in served.items() if len(rs) >= 2}
    NON_APPELABLE_CAT = {"pdf", "copilote", "notification", "admin", "couche", "fond", "crm",
                         "veille", "projets"}
    for cid in sorted(multi):
        c = chiffres.get(cid, {})
        niveau = c.get("niveau")
        cats = {r["categorie"] for r in multi[cid]}
        if niveau == "commune":
            ecartees.append(Ecartee(
                f"F2.{cid}.croisement_api", "F2", f"chiffre {cid}",
                "chiffre commune : /communes/{c}/contexte sert via commune_contexte_cache VIDE "
                "dans ce worktree (sru/prix/marche/foncier=null) → surfaces non comparables en API ; "
                "testé en BASE si deux tables servies le portent"))
            continue
        if niveau in ("proprietaire", "zone") or cats <= NON_APPELABLE_CAT:
            ecartees.append(Ecartee(
                f"F2.{cid}.surfaces", "F2", f"chiffre {cid}",
                f"surfaces servantes non appelables en GET JSON scalaire ({sorted(cats)})"))
            continue

    # ═══════════════════════════════════════════════════════════════════════════════════════════
    #  AXE 1 — liste /parcels vs base (source de vérité). 1 règle/chiffre. Île (par communes panel).
    # ═══════════════════════════════════════════════════════════════════════════════════════════
    specs.append(_mk_liste_vs_base("surface_m2", "Surface (dessin)", "surface_m2",
                                   _sql_parcels("round(surface_m2)::int")))
    specs.append(_mk_liste_vs_base("contenance_m2", "Contenance cadastrale", "contenance_m2",
                                   _sql_parcels("contenance_m2")))
    specs.append(_mk_liste_vs_base(
        "surface_terrain_m2", "Surface de terrain", "surface_terrain_m2",
        _sql_parcels("round(COALESCE(contenance_m2, surface_m2))::int")))
    specs.append(_mk_liste_vs_base("bande", "Bande de score", "bande",
                                   _sql_score("bande"), texte=True))
    specs.append(_mk_liste_vs_base("signal_niveau", "Signal de mutation", "signal_niveau",
                                   _sql_score("signal_niveau"), gravite="INCOHERENT", texte=True))
    specs.append(_mk_liste_vs_base("cause", "Cause de non-retenue", "cause",
                                   _sql_score("cause"), gravite="INCOHERENT", texte=True))
    specs.append(_mk_liste_vs_base("non_calculable", "Non calculable", "non_calculable",
                                   _sql_score("non_calculable"), gravite="INCOHERENT", texte=True))
    # sdp : liste sert NULL si cause présente (convention) → on compare uniquement les non-null des
    # deux côtés ; la base rend sdp_residuelle_m2 (qui peut être non-null même sous cause), mais la
    # paire (liste null, base val) est écartée par le garde None≠comparable. Reste testé : égalité
    # quand la liste expose une valeur (= cause NULL). On mappe donc la base au MÊME gate.
    specs.append(_mk_liste_vs_base(
        "sdp_residuelle_m2", "SDP résiduelle", "sdp_residuelle_m2",
        _sql_score("CASE WHEN cause IS NULL THEN sdp_residuelle_m2 END")))
    specs.append(_mk_liste_vs_base("tier_v2", "Verdict (tier v2)", "tier_v2",
                                   _sql_v2("tier"), texte=True))
    specs.append(_mk_liste_vs_base("rang_v2", "Rang v2", "rang_v2", _sql_v2("rang")))
    specs.append(_mk_liste_vs_base("mult_v2", "Multiplicateur v2", "mult_v2",
                                   _sql_v2("mult_base"), tol=TOL_RATIO))
    specs.append(_mk_liste_vs_base("v_band", "Bande V (vendabilité)", "v_band",
                                   _sql_vscore("v_band"), gravite="INCOHERENT", texte=True))
    specs.append(_mk_liste_vs_base("v_score", "Score V (vendabilité)", "v_score",
                                   _sql_vscore("v_score"), gravite="INCOHERENT"))
    specs.append(_mk_liste_vs_base("owner_type", "Type de propriétaire", "owner_type",
                                   _sql_vscore("owner_type"), gravite="INCOHERENT", texte=True))
    specs.append(_mk_liste_vs_base("zone_lib", "Zone PLU (libellé)", "zone_lib",
                                   _sql_zone("zone_lib"), texte=True))
    specs.append(_mk_liste_vs_base("zone_fam", "Zone PLU (famille)", "zone_fam",
                                   _sql_zone("zone_fam"), texte=True))
    specs.append(_mk_liste_vs_base("completeness_score", "Score de complétude", "completeness_score",
                                   _sql_completeness(), gravite="INCOHERENT"))

    # ═══════════════════════════════════════════════════════════════════════════════════════════
    #  AXE 2 — liste /parcels vs fiche /parcels/{idu} (deux chemins de code). 1 règle/chiffre.
    # ═══════════════════════════════════════════════════════════════════════════════════════════
    GRAV_FICHE = {"bande": "FAUX-CLIENT", "sdp_residuelle_m2": "FAUX-CLIENT",
                  "surface_m2": "FAUX-CLIENT", "contenance_m2": "FAUX-CLIENT",
                  "tier_v2": "FAUX-CLIENT"}
    TOL_FICHE = {"mult_v2": TOL_RATIO}
    TEXTE_FICHE = {"bande", "tier_v2", "v_band", "owner_type", "zone_lib", "zone_fam",
                   "signal_niveau"}
    LIB_FICHE = {
        "bande": "Bande de score", "sdp_residuelle_m2": "SDP résiduelle",
        "surface_m2": "Surface (dessin)", "contenance_m2": "Contenance cadastrale",
        "tier_v2": "Verdict (tier v2)", "rang_v2": "Rang v2", "mult_v2": "Multiplicateur v2",
        "v_band": "Bande V", "v_score": "Score V", "owner_type": "Type de propriétaire",
        "zone_lib": "Zone PLU (libellé)", "zone_fam": "Zone PLU (famille)",
        "signal_niveau": "Signal de mutation", "completeness_score": "Score de complétude",
    }
    for cid, extr in _FICHE.items():
        specs.append(_mk_liste_vs_fiche(
            cid, LIB_FICHE.get(cid, cid), cid, extr,
            gravite=GRAV_FICHE.get(cid, "INCOHERENT"),
            tol=TOL_FICHE.get(cid, TOL), texte=(cid in TEXTE_FICHE)))

    # ═══════════════════════════════════════════════════════════════════════════════════════════
    #  AXE 3a — /filtre.page vs liste (même builder _q_v2_list → identité). Quelques chiffres clés.
    # ═══════════════════════════════════════════════════════════════════════════════════════════
    for cid, texte in [("bande", True), ("tier_v2", True), ("sdp_residuelle_m2", False),
                       ("surface_terrain_m2", False), ("rang_v2", False), ("zone_lib", True),
                       ("signal_niveau", True)]:
        specs.append(_mk_filtre_vs_liste(cid, cid, texte=texte,
                                         tol=(TOL_RATIO if cid == "mult_v2" else TOL)))

    # ═══════════════════════════════════════════════════════════════════════════════════════════
    #  AXE 3b — export markdown vs fiche : scalaires robustes (surface, commune). Reste écarté.
    # ═══════════════════════════════════════════════════════════════════════════════════════════
    specs.append(_mk_export_vs_fiche(
        "surface_terrain_m2", "Surface de terrain",
        lambda p: p.get("surface_terrain_m2"), _md_surface, gravite="FAUX-CLIENT"))
    specs.append(_mk_export_vs_fiche(
        "commune", "Commune",
        lambda p: p.get("commune"), _md_commune, gravite="FAUX-CLIENT", texte=True))
    ecartees.append(Ecartee(
        "F2.export_vs_fiche.autres", "F2", "export /parcels/{idu}/export",
        "l'export est du MARKDOWN prosé (pas un JSON scalaire) : seules surface et commune s'en "
        "extraient de façon robuste ; bande/tier/sdp y sont noyés dans des phrases (libellés "
        "clients) → pas un scalaire comparable sans parser fragile"))

    # ═══════════════════════════════════════════════════════════════════════════════════════════
    #  Les 19 règles de la PREMIÈRE passe, CONSERVÉES à l'identique (fiche dual-key, fiche↔base,
    #  global, base SQL île). Elles restent valides et vertes.
    # ═══════════════════════════════════════════════════════════════════════════════════════════
    # fiche dual-key
    specs.append(_mk_fiche_dualkey(
        "sdp_residuelle_m2", "SDP résiduelle",
        "analyse_labuse.sdp_residuelle_m2", "potentiel_transformation.sdp_residuelle_m2",
        lambda p: _d(p, "analyse_labuse", "sdp_residuelle_m2"),
        lambda p: _d(p, "potentiel_transformation", "sdp_residuelle_m2"),
        gravite="FAUX-CLIENT"))
    ecartees.append(Ecartee(
        "F2.sdp_residuelle_m2.fiche_vs_faisabilite", "F2", "chiffre sdp_residuelle_m2",
        "fiche sert la SDP RÉSIDUELLE ; /modules/faisabilite sert surface_plancher_m2 (GABARIT "
        "théorique) — même id de registre mais DÉFINITIONS différentes, pas une égalité"))
    specs.append(_mk_fiche_vs_db(
        "sdp_residuelle_m2", "SDP résiduelle",
        "analyse_labuse.sdp_residuelle_m2",
        lambda p: _d(p, "analyse_labuse", "sdp_residuelle_m2"),
        "SELECT round(sdp_residuelle_m2)::int FROM score_labuse WHERE run_label='q_v18' AND idu=%s"))
    specs.append(_mk_fiche_dualkey(
        "surface_parcelle_m2", "Surface parcelle",
        "surface_m2", "le_bien.surface_parcelle_m2",
        lambda p: p.get("surface_m2"),
        lambda p: _d(p, "le_bien", "surface_parcelle_m2"),
        gravite="FAUX-CLIENT"))
    specs.append(_mk_fiche_dualkey(
        "contenance_m2", "Contenance cadastrale",
        "contenance_m2", "surface_terrain_m2",
        lambda p: p.get("contenance_m2"),
        lambda p: p.get("surface_terrain_m2"),
        gravite="FAUX-CLIENT"))
    specs.append(_mk_fiche_vs_db(
        "tier_opportunite", "Verdict · classement servi",
        "score_v2.tier",
        lambda p: _d(p, "score_v2", "tier"),
        "SELECT tier FROM parcel_p_score_v2 WHERE parcelle_id=%s AND run_id='q_v18' LIMIT 1",
        gravite="FAUX-CLIENT"))
    ecartees.append(Ecartee(
        "F2.tier_opportunite.surfaces_couche_pdf", "F2", "chiffre tier_opportunite",
        "autres surfaces (couche_verdict=tuiles MVT, pdf_dossier_expert/pdf_flash, "
        "outil_etudier_bien=/modules/scoreur-adresse POST) non appelables en GET JSON scalaire"))
    specs.append(_mk_fiche_vs_db(
        "bande_score", "Bande de score (A..0/NC)",
        "analyse_labuse.bande",
        lambda p: _d(p, "analyse_labuse", "bande"),
        "SELECT bande FROM score_labuse WHERE run_label='q_v18' AND idu=%s",
        gravite="FAUX-CLIENT"))
    specs.append(_mk_fiche_vs_db(
        "surface_parcelle_m2", "Surface parcelle (= surface_m2)",
        "surface_m2", lambda p: p.get("surface_m2"),
        "SELECT round(surface_m2)::int FROM parcels WHERE idu=%s"))
    specs.append(_mk_fiche_vs_db(
        "contenance_m2", "Contenance cadastrale",
        "contenance_m2", lambda p: p.get("contenance_m2"),
        "SELECT round(contenance_m2)::int FROM parcels WHERE idu=%s"))
    specs.append(_mk_fiche_vs_db(
        "commune", "Commune de la parcelle",
        "commune", lambda p: p.get("commune"),
        "SELECT commune FROM parcels WHERE idu=%s"))
    specs.append(_mk_fiche_vs_db(
        "signal_niveau", "Signal (niveau)",
        "analyse_labuse.signal_niveau", lambda p: _d(p, "analyse_labuse", "signal_niveau"),
        "SELECT signal_niveau FROM score_labuse WHERE run_label='q_v18' AND idu=%s"))
    specs.append(_mk_fiche_vs_db(
        "sdp_residuelle_m2", "SDP résiduelle (bloc potentiel)",
        "potentiel_transformation.sdp_residuelle_m2",
        lambda p: _d(p, "potentiel_transformation", "sdp_residuelle_m2"),
        "SELECT round(r.sdp_residuelle_m2)::int FROM parcel_residuel r "
        "JOIN parcels p ON p.id=r.parcel_id WHERE p.idu=%s", suffixe=".potentiel"))

    # globaux
    specs.append(_mk_global_pair(
        "run_label_servi", "Run servi",
        "/config/run", lambda p: p.get("run"),
        "/accueil/chiffres", lambda p: p.get("run_label"), numerique=False))
    specs.append(_mk_global_pair(
        "n_sources", "Sources",
        "/accueil/chiffres", lambda p: p.get("sources"),
        "/sources", lambda p: (len(p) if isinstance(p, list) else None)))
    specs.append(_mk_global_pair(
        "parcelles_total", "Parcelles vivantes (île)",
        "/accueil/chiffres", lambda p: p.get("parcelles"),
        "/communes", lambda p: (sum(c.get("parcelles", 0) for c in p) if isinstance(p, list) else None)))
    specs.append(_mk_global_pair(
        "n_communes", "Communes",
        "/accueil/chiffres", lambda p: p.get("communes"),
        "/communes", lambda p: (len(p) if isinstance(p, list) else None)))

    # base SQL île
    specs.append(RuleSpec(
        id="F2.base.sdp_residuelle_m2.residuel_vs_score", famille="F2",
        source="chiffre sdp_residuelle_m2 — parcel_residuel vs score_labuse(q_v18)",
        libelle="SDP résiduelle identique entre parcel_residuel et score_labuse (run servi)",
        gravite="INCOHERENT", attendu="0 ligne divergente",
        sql_violations="""
            SELECT count(*) FROM parcel_residuel r
              JOIN score_labuse s ON s.parcel_id=r.parcel_id AND s.run_label='q_v18'
            WHERE round(coalesce(r.sdp_residuelle_m2,0))::int
                  <> round(coalesce(s.sdp_residuelle_m2,0))::int""",
        exemples_sql="""
            SELECT s.idu, r.sdp_residuelle_m2 AS residuel, s.sdp_residuelle_m2 AS score
            FROM parcel_residuel r
              JOIN score_labuse s ON s.parcel_id=r.parcel_id AND s.run_label='q_v18'
            WHERE round(coalesce(r.sdp_residuelle_m2,0))::int
                  <> round(coalesce(s.sdp_residuelle_m2,0))::int LIMIT 3"""))
    specs.append(RuleSpec(
        id="F2.base.commune.parcels_vs_score", famille="F2",
        source="chiffre commune — parcels vs score_labuse(q_v18)",
        libelle="Commune d'une parcelle identique entre parcels et score_labuse (run servi)",
        gravite="FAUX-CLIENT", attendu="0 ligne divergente",
        sql_violations="""
            SELECT count(*) FROM score_labuse s JOIN parcels p ON p.idu=s.idu
            WHERE s.run_label='q_v18' AND s.commune IS DISTINCT FROM p.commune""",
        exemples_sql="""
            SELECT s.idu, p.commune AS parcels, s.commune AS score
            FROM score_labuse s JOIN parcels p ON p.idu=s.idu
            WHERE s.run_label='q_v18' AND s.commune IS DISTINCT FROM p.commune LIMIT 3"""))
    specs.append(RuleSpec(
        id="F2.base.dvf.valeur_fonciere.mutations_vs_parcelle", famille="F2",
        source="chiffre valeur_fonciere — dvf_mutations vs dvf_mutations_parcelle",
        libelle="Valeur foncière d'une mutation identique entre dvf_mutations et dvf_mutations_parcelle",
        gravite="INCOHERENT", attendu="0 ligne divergente",
        sql_violations="""
            SELECT count(*) FROM dvf_mutations m
              JOIN dvf_mutations_parcelle mp ON m.mutation_id = mp.id_mutation
            WHERE round(coalesce(m.valeur_fonciere,0))::bigint
                  <> round(coalesce(mp.valeur_fonciere,0))::bigint""",
        exemples_sql="""
            SELECT m.mutation_id, m.valeur_fonciere AS v_mut, mp.valeur_fonciere AS v_parc
            FROM dvf_mutations m
              JOIN dvf_mutations_parcelle mp ON m.mutation_id = mp.id_mutation
            WHERE round(coalesce(m.valeur_fonciere,0))::bigint
                  <> round(coalesce(mp.valeur_fonciere,0))::bigint LIMIT 3"""))
    ecartees.append(Ecartee(
        "F2.base.dvf.surface_terrain", "F2", "chiffre surface_terrain",
        "dvf_mutations porte la surface AGRÉGÉE de la mutation, dvf_mutations_parcelle la surface "
        "par PARCELLE (join 1→N) — granularités différentes, pas une égalité (faux positif écarté)"))
    ecartees.append(Ecartee(
        "F2.base.dvf.surface_bati", "F2", "chiffre surface_reelle_bati",
        "idem surface_terrain : agrégat mutation vs composante parcelle — pas une égalité de valeur"))
    specs.append(RuleSpec(
        id="F2.base.commune.sitadel_vs_parcels", famille="F2",
        source="chiffre commune — sitadel_permits vs parcels (via idu_codes)",
        libelle="Commune d'un permis SITADEL cohérente avec la commune des parcelles qu'il cite",
        gravite="INCOHERENT", attendu="0 ligne divergente",
        sql_violations="""
            SELECT count(*) FROM sitadel_permits sp
              JOIN LATERAL jsonb_array_elements_text(sp.idu_codes) AS u(idu) ON true
              JOIN parcels p ON p.idu = u.idu
            WHERE sp.commune IS NOT NULL AND p.commune IS NOT NULL
              AND sp.commune IS DISTINCT FROM p.commune""",
        exemples_sql="""
            SELECT sp.permit_id, u.idu, sp.commune AS permis, p.commune AS parcelle
            FROM sitadel_permits sp
              JOIN LATERAL jsonb_array_elements_text(sp.idu_codes) AS u(idu) ON true
              JOIN parcels p ON p.idu = u.idu
            WHERE sp.commune IS NOT NULL AND p.commune IS NOT NULL
              AND sp.commune IS DISTINCT FROM p.commune LIMIT 3"""))

    return specs, ecartees


# ─── règles de la 1re passe (callables), reprises telles quelles ────────────────────────────────
def _mk_fiche_dualkey(chiffre, libelle, ex_a, ex_b, extr_a, extr_b, gravite="INCOHERENT"):
    def check(cx, api):
        if not api:
            return "SKIP", "API absente"
        idus = _echantillon_api(cx)
        teste = both = 0
        for idu in idus:
            st, p = _fiche(api, idu)
            if st != 200 or not isinstance(p, dict):
                continue
            teste += 1
            va, vb = extr_a(p), extr_b(p)
            if va is None or vb is None:
                continue
            both += 1
            try:
                if abs(float(va) - float(vb)) > TOL:
                    return "ECART", (f"{idu} : {ex_a}={va} ≠ {ex_b}={vb} "
                                     f"(testées {teste}, deux clés présentes {both})")
            except (TypeError, ValueError):
                if str(va) != str(vb):
                    return "ECART", f"{idu} : {ex_a}={va!r} ≠ {ex_b}={vb!r}"
        return "OK", f"{both}/{teste} fiches avec les deux clés — toutes égales"
    return RuleSpec(
        id=f"F2.fiche_dualkey.{chiffre}", famille="F2",
        source=f"chiffre {chiffre} — fiche parcelle ({ex_a} vs {ex_b})",
        libelle=f"{libelle} : {ex_a} == {ex_b} sur la même fiche", gravite=gravite,
        attendu="valeurs identiques", check=check)


def _mk_fiche_vs_db(chiffre, libelle, ex_cle, extr, sql_db, gravite="FAUX-CLIENT", suffixe=""):
    def check(cx, api):
        if not api:
            return "SKIP", "API absente"
        idus = _echantillon_api(cx)
        teste = both = 0
        for idu in idus:
            st, p = _fiche(api, idu)
            if st != 200 or not isinstance(p, dict):
                continue
            teste += 1
            vf = extr(p)
            vdb = cx.scalar(sql_db, (idu,))
            if vf is None or vdb is None:
                continue
            both += 1
            try:
                if abs(float(vf) - float(vdb)) > TOL:
                    return "ECART", (f"{idu} : fiche {ex_cle}={vf} ≠ base={vdb} "
                                     f"(testées {teste}, comparables {both})")
            except (TypeError, ValueError):
                if str(vf) != str(vdb):
                    return "ECART", f"{idu} : fiche {ex_cle}={vf!r} ≠ base={vdb!r}"
        return "OK", f"{both}/{teste} fiches comparées à la base — toutes égales"
    return RuleSpec(
        id=f"F2.fiche_vs_base.{chiffre}{suffixe}", famille="F2",
        source=f"chiffre {chiffre} — fiche ({ex_cle}) vs base",
        libelle=f"{libelle} : fiche {ex_cle} == base", gravite=gravite,
        attendu="valeur fiche == valeur base", check=check)


def _mk_global_pair(chiffre, libelle, route_a, extr_a, route_b, extr_b, numerique=True):
    def check(cx, api):
        if not api:
            return "SKIP", "API absente"
        sa, pa = _get(api, route_a)
        sb, pb = _get(api, route_b)
        if sa != 200 or sb != 200:
            return "SKIP", f"{route_a}={sa} / {route_b}={sb}"
        va, vb = extr_a(pa), extr_b(pb)
        if va is None or vb is None:
            return "SKIP", f"valeur absente ({route_a}:{va} / {route_b}:{vb})"
        if numerique:
            try:
                ok = abs(float(va) - float(vb)) <= TOL
            except (TypeError, ValueError):
                ok = str(va) == str(vb)
        else:
            ok = str(va) == str(vb)
        if ok:
            return "OK", f"{route_a}={va} == {route_b}={vb}"
        return "ECART", f"{route_a}={va} ≠ {route_b}={vb}"
    return RuleSpec(
        id=f"F2.global.{chiffre}", famille="F2",
        source=f"chiffre {chiffre} — {route_a} vs {route_b}",
        libelle=f"{libelle} : {route_a} == {route_b}", gravite="INCOHERENT",
        attendu="valeurs identiques", check=check)


# ═══════════════════════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import sys
    API = "http://127.0.0.1:8793"
    cx = connexion()
    specs, ecartees = generer(cx)
    print("# F2 — le registre (étendu : axes liste/fiche/filtre/export)")
    print(f"générées (retenues) : {len(specs)}")
    print(f"écartées             : {len(ecartees)}")

    raisons = defaultdict(int)
    for e in ecartees:
        raisons[e.raison] += 1
    print("\n## raisons d'écart")
    for r, n in sorted(raisons.items(), key=lambda kv: -kv[1]):
        print(f"  {n:4}  {r[:110]}")

    only = sys.argv[1] if len(sys.argv) > 1 else None
    a_jouer = [s for s in specs if (only is None or only in s.id)]
    print(f"\n## exécution de {len(a_jouer)} règle(s)" + (f" filtrées sur « {only} »" if only else ""))
    res = run_specs(cx, a_jouer, api=API)
    b = bilan(res)
    print(f"\n## bilan : OK={b['OK']} ECART={b['ECART']} SKIP={b['SKIP']}")
    for r in res:
        if r.statut != "OK":
            print(f"\n[{r.statut}] {r.spec.id}\n   {r.message}")
            for ex in r.exemples[:3]:
                print(f"     · {ex}")
