"""CHASSE-INVARIANTS-2 — F5 : l'API à la limite (robustesse des routes GET client).

On GÉNÈRE, pour chaque route GET servie au client, un faisceau de règles de robustesse :
pour chaque classe de paramètre (valide / inconnu / malformé / injection / démesuré / combiné),
on vérifie TROIS invariants, chacun une RuleSpec `check(cx, api)` :

  · JAMAIS DE 500        — une entrée absurde/malformée doit rendre un code propre
                           (200/204/400/404/422), jamais un 500 ni une erreur non gérée.
  · JAMAIS « NaN/None/null/Infinity » LÀ OÙ UN NOMBRE/LABEL EST ATTENDU
                           — on scanne le corps JSON pour les littéraux `NaN`, `Infinity`
                           (JSON invalide, cassant un client strict), et pour `null` dans un
                           champ qui DOIT être peuplé (idu de /parcels/{idu}, run de /config/run…).
                           Un `null` légitime (ex. /parcels/at sans parcelle) n'est PAS une violation.
  · DÉTERMINISME          — deux appels successifs identiques → même code + même corps.

Lecture seule STRICTE, GET uniquement, cadencé (~1.1 s entre appels) pour respecter le
rate-limit ~60/min. Un appel transitoirement en erreur réseau est rejoué une fois.

Les routes qui exigent `source` rendent un 404 propre quand elle manque : c'est le COMPORTEMENT
CORRECT, pas une violation — on le teste comme tel (≠ 500).
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request

from scripts.coherence.invariants2 import noyau as N  # type: ignore

# ── réglages de cadence ──────────────────────────────────────────────────────────────────────
PAUSE = 1.1          # s entre deux appels (rate-limit ~60/min)
TIMEOUT = 30

# littéraux JSON interdits dans un corps censé être consommable par un client strict
_LITT_INTERDITS = ("NaN", "Infinity", "-Infinity")


# ── appel bas niveau : rend (code|'ERR', corps_texte, corps_json|None) ─────────────────────────
def _appel(base: str, path: str):
    """Un GET. Rend (status, texte_brut, json|None). Jamais d'exception ; rejoue une fois sur ERR."""
    url = base + path
    for essai in range(2):
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                raw = r.read()
                txt = raw.decode("utf-8", "replace")
                try:
                    js = json.loads(txt) if txt.strip() else None
                except Exception:
                    js = None
                return r.status, txt, js
        except urllib.error.HTTPError as e:
            try:
                raw = e.read()
                txt = raw.decode("utf-8", "replace")
            except Exception:
                txt = ""
            try:
                js = json.loads(txt) if txt.strip() else None
            except Exception:
                js = None
            return e.code, txt, js
        except Exception:
            if essai == 0:
                time.sleep(0.6)
                continue
            return "ERR", "", None
    return "ERR", "", None


def _get(base, path):
    code, txt, js = _appel(base, path)
    time.sleep(PAUSE)
    return code, txt, js


# ── les trois contrôles élémentaires ───────────────────────────────────────────────────────────
def _scan_litteraux(txt: str) -> list:
    """Cherche NaN/Infinity comme TOKENS JSON (pas sous-chaîne d'un mot). Rend les littéraux trouvés."""
    import re
    trouve = []
    for lit in _LITT_INTERDITS:
        # token JSON : précédé de [ : , espace ou début ; suivi de ] } , espace ou fin
        if re.search(r"(?<![\w\"])" + re.escape(lit) + r"(?![\w\"])", txt):
            trouve.append(lit)
    return trouve


def _controle_pas_500(base, cas: list) -> tuple:
    """cas = liste de (libelle, path). Viole si un code 5xx ou ERR (erreur non gérée)."""
    coupables = []
    for lib, path in cas:
        code, txt, _ = _get(base, path)
        if code == "ERR" or (isinstance(code, int) and code >= 500):
            coupables.append(f"{lib} :: {path} -> {code} :: {txt[:140]!r}")
    if coupables:
        return "ECART", " | ".join(coupables[:3]) + (f"  (+{len(coupables)-3})" if len(coupables) > 3 else "")
    return "OK", f"{len(cas)} entrée(s) absurde(s) : aucun 5xx (codes propres 2xx/4xx)"


def _controle_pas_nan(base, cas: list) -> tuple:
    """cas = liste de (libelle, path). Viole si le corps contient NaN/Infinity (JSON invalide côté client)."""
    coupables = []
    for lib, path in cas:
        code, txt, _ = _get(base, path)
        if code == "ERR":
            continue
        trouve = _scan_litteraux(txt)
        if trouve:
            coupables.append(f"{lib} :: {path} -> {code} :: littéraux {trouve} :: {txt[:120]!r}")
    if coupables:
        return "ECART", " | ".join(coupables[:3])
    return "OK", f"{len(cas)} corps scanné(s) : aucun NaN/Infinity"


def _controle_null_peuple(base, cas: list) -> tuple:
    """cas = liste de (libelle, path, champ). Viole si champ attendu peuplé == null/absent sur un 200.

    N'est appliqué qu'aux paths VALIDES (baseline) où le champ DOIT être présent.
    """
    coupables = []
    for lib, path, champ in cas:
        code, txt, js = _get(base, path)
        if code != 200 or not isinstance(js, dict):
            continue
        if champ not in js or js.get(champ) is None:
            coupables.append(f"{lib} :: {path} -> 200 mais {champ}={js.get(champ)!r}")
    if coupables:
        return "ECART", " | ".join(coupables[:3])
    return "OK", f"{len(cas)} champ(s) obligatoire(s) peuplé(s)"


# champs de DIAGNOSTIC légitimement volatils (latence de réponse) — à neutraliser avant comparaison
_VOLATILS = __import__("re").compile(r'"ms":\s*[0-9.]+')


def _normaliser(txt: str) -> str:
    """Neutralise les champs diagnostiques non-déterministes (latence 'ms') pour la comparaison sémantique."""
    return _VOLATILS.sub('"ms":0', txt)


def _controle_determinisme(base, cas: list) -> tuple:
    """cas = liste de (libelle, path). Viole si deux appels successifs diffèrent (code ou corps SÉMANTIQUE).

    Les champs de diagnostic volatils (latence 'ms') sont neutralisés : seule la donnée servie compte.
    """
    coupables = []
    for lib, path in cas:
        c1, t1, _ = _get(base, path)
        c2, t2, _ = _get(base, path)
        if c1 == "ERR" or c2 == "ERR":
            continue
        t1, t2 = _normaliser(t1), _normaliser(t2)
        if c1 != c2:
            coupables.append(f"{lib} :: {path} -> codes {c1} puis {c2}")
        elif t1 != t2:
            # diff textuel : montrer la première divergence
            i = next((k for k in range(min(len(t1), len(t2))) if t1[k] != t2[k]), min(len(t1), len(t2)))
            coupables.append(f"{lib} :: {path} -> corps divergent @~{i} :: A={t1[max(0,i-20):i+40]!r} B={t2[max(0,i-20):i+40]!r}")
    if coupables:
        return "ECART", " | ".join(coupables[:3])
    return "OK", f"{len(cas)} appel(s) rejoué(s) : réponse identique"


# ── fabrique de RuleSpec ─────────────────────────────────────────────────────────────────────
def _spec(rid, route, invariant, libelle, gravite, attendu, fn):
    return N.RuleSpec(
        id=f"F5.{rid}",
        famille="F5",
        source=f"route {route} ({invariant})",
        libelle=libelle,
        gravite=gravite,
        attendu=attendu,
        check=(lambda cx, api, _fn=fn: _fn(api) if api else ("SKIP", "pas d'API")),
    )


def _specs_pas_500_par_cas(rid_prefix, route, cas: list) -> list:
    """Une règle 'jamais 500' PAR cas de la liste (granularité param-classe)."""
    out = []
    for lib, path in cas:
        slug = (lib.replace(" ", "_").replace("=", "").replace("<", "lt").replace(">", "gt")
                .replace("-", "_").replace(",", "_").replace("/", "").replace(".", ""))
        out.append(_spec(
            f"{rid_prefix}.pas_500.{slug}", route, "jamais 500",
            f"[{lib}] sur {route} ne doit jamais rendre 500 : {path}",
            "ROBUSTESSE", "≠ 5xx",
            lambda api, _c=[(lib, path)]: _controle_pas_500(api, _c)))
    return out


def _enc(v: str) -> str:
    return urllib.parse.quote(v, safe="")


# ── le générateur ──────────────────────────────────────────────────────────────────────────────
def generer(cx):
    specs: list = []
    ecartees: list = []

    # échantillons réels pour les baselines & le déterminisme
    try:
        idu_ok = N.echantillon_stratifie(cx, n=4)[:3] or ["97415000AW2362"]
    except Exception:
        idu_ok = ["97415000AW2362"]
    try:
        with cx.conn.cursor() as cur:
            cur.execute("SELECT DISTINCT commune FROM parcels WHERE commune IS NOT NULL ORDER BY commune LIMIT 2")
            com_ok = [r[0] for r in cur.fetchall()] or ["Cilaos"]
    except Exception:
        com_ok = ["Cilaos"]
    idu0 = idu_ok[0]
    com0 = com_ok[0]

    SRC = "q_v18"
    # payloads d'agression réutilisés
    SQLI = "' OR 1=1--"
    LONG = "A" * 500
    UNI = "Café™日本語"
    EMOJI = "🏠🔥"
    CTRL = "a\tb\nc"

    def q(**kw):
        return "?" + urllib.parse.urlencode(kw)

    # ============ 1) /parcels/{idu} ============
    r = "/parcels/{idu}"
    mauvais_idu = [
        ("inconnu", f"/parcels/00000000XX0000"),
        ("malformé-abc", f"/parcels/abc"),
        ("sqli", f"/parcels/{_enc(SQLI)}"),
        ("très-long", f"/parcels/{_enc(LONG)}"),
        ("unicode", f"/parcels/{_enc(UNI)}"),
        ("emoji", f"/parcels/{_enc(EMOJI)}"),
        ("source-inconnue", f"/parcels/{idu0}?source=zzz_nope"),
        ("source-vide", f"/parcels/{idu0}?source="),
        ("source-sqli", f"/parcels/{idu0}?source={_enc(SQLI)}"),
    ]
    specs += _specs_pas_500_par_cas("parcels_idu", r, mauvais_idu)
    specs.append(_spec("parcels_idu.pas_nan", r, "jamais NaN",
                       "corps de /parcels/{idu} sans littéral NaN/Infinity",
                       "FAUX-CLIENT", "pas de NaN/Infinity",
                       lambda api: _controle_pas_nan(api, [("valide", f"/parcels/{i}") for i in idu_ok])))
    specs.append(_spec("parcels_idu.null_peuple", r, "null interdit",
                       "une parcelle servie (200) a toujours un idu peuplé",
                       "FAUX-CLIENT", "idu non null",
                       lambda api: _controle_null_peuple(api, [("valide", f"/parcels/{i}", "idu") for i in idu_ok])))
    specs.append(_spec("parcels_idu.determinisme", r, "déterminisme",
                       "/parcels/{idu} rend deux fois la même réponse",
                       "ROBUSTESSE", "2 appels identiques",
                       lambda api: _controle_determinisme(api, [("valide", f"/parcels/{idu0}"),
                                                                 ("inconnu", "/parcels/00000000XX0000")])))

    # ============ 2) /parcels (liste, source REQUISE) ============
    r = "/parcels"
    # D'abord : source manquante doit faire 404 PROPRE (pas 500) — on le teste
    bornes_liste = [
        ("src-manquante", f"/parcels{q(commune=com0, limit=1)}"),
        ("limit=0", f"/parcels{q(source=SRC, limit=0)}"),
        ("limit=-1", f"/parcels{q(source=SRC, limit=-1)}"),
        ("limit=99999", f"/parcels{q(source=SRC, limit=99999)}"),
        ("limit=non-int", f"/parcels{q(source=SRC, limit='abc')}"),
        ("offset=-1", f"/parcels{q(source=SRC, offset=-1)}"),
        ("offset=huge", f"/parcels{q(source=SRC, offset=999999999)}"),
        ("offset=non-int", f"/parcels{q(source=SRC, offset='x')}"),
        ("surface_min<0", f"/parcels{q(source=SRC, surface_min=-5)}"),
        ("surface_min=9e9", f"/parcels{q(source=SRC, surface_min='9000000000')}"),
        ("surface_min>max", f"/parcels{q(source=SRC, surface_min=9999, surface_max=1)}"),
        ("surface_non-num", f"/parcels{q(source=SRC, surface_min='xx')}"),
        ("sdp_min<0", f"/parcels{q(source=SRC, sdp_min=-1)}"),
        ("flags-garbage", f"/parcels{q(source=SRC, flags='zzz,%%%,1=1')}"),
        ("zonage-garbage", f"/parcels{q(source=SRC, zonage=SQLI)}"),
        ("sort-invalide", f"/parcels{q(source=SRC, sort='zzz')}"),
        ("commune-inconnue", f"/parcels{q(source=SRC, commune='ZZZZ')}"),
        ("commune-sqli", f"/parcels{q(source=SRC, commune=SQLI)}"),
        ("source-inconnue", f"/parcels{q(source='zzz_nope')}"),
        ("combiné-absurde", f"/parcels{q(source=SRC, limit=-1, offset=-1, surface_min='9e9', sort='zzz')}"),
    ]
    specs += _specs_pas_500_par_cas("parcels_liste", r, bornes_liste)
    specs.append(_spec("parcels_liste.pas_nan", r, "jamais NaN",
                       "corps de /parcels liste sans NaN/Infinity",
                       "FAUX-CLIENT", "pas de NaN/Infinity",
                       lambda api: _controle_pas_nan(api, [("valide", f"/parcels{q(source=SRC, commune=com0, limit=20)}"),
                                                           ("surface_min=0", f"/parcels{q(source=SRC, surface_min=0, limit=20)}")])))
    specs.append(_spec("parcels_liste.determinisme", r, "déterminisme",
                       "/parcels liste rend deux fois la même réponse",
                       "ROBUSTESSE", "2 appels identiques",
                       lambda api: _controle_determinisme(api, [("valide", f"/parcels{q(source=SRC, commune=com0, limit=10)}")])))

    # ============ 3) /parcels/search?q= ============
    r = "/parcels/search"
    search_cas = [
        ("q-vide", f"/parcels/search{q(q='')}"),
        ("q-1car", f"/parcels/search{q(q='a')}"),
        ("q-long", f"/parcels/search{q(q=LONG)}"),
        ("q-sqli", f"/parcels/search{q(q=SQLI)}"),
        ("q-unicode", f"/parcels/search{q(q=UNI)}"),
        ("q-emoji", f"/parcels/search{q(q=EMOJI)}"),
        ("q-ctrl", f"/parcels/search{q(q=CTRL)}"),
        ("q-ok-src", f"/parcels/search{q(q=idu0[:6], source=SRC, limit=5)}"),
        ("limit=-1", f"/parcels/search{q(q=idu0[:6], limit=-1)}"),
        ("limit=99999", f"/parcels/search{q(q=idu0[:6], limit=99999)}"),
    ]
    specs += _specs_pas_500_par_cas("parcels_search", r, search_cas)
    specs.append(_spec("parcels_search.pas_nan", r, "jamais NaN",
                       "corps de /parcels/search sans NaN/Infinity",
                       "FAUX-CLIENT", "pas de NaN/Infinity",
                       lambda api: _controle_pas_nan(api, [("ok", f"/parcels/search{q(q=com0[:4])}")])))
    specs.append(_spec("parcels_search.determinisme", r, "déterminisme",
                       "/parcels/search rend deux fois la même réponse",
                       "ROBUSTESSE", "2 appels identiques",
                       lambda api: _controle_determinisme(api, [("ok", f"/parcels/search{q(q=com0[:4])}")])))

    # ============ 4) /api/recherche/suggest?q= ============
    r = "/api/recherche/suggest"
    sugg_cas = [
        ("q-vide", f"/api/recherche/suggest{q(q='')}"),
        ("q-1car", f"/api/recherche/suggest{q(q='a')}"),
        ("q-long", f"/api/recherche/suggest{q(q=LONG)}"),
        ("q-sqli", f"/api/recherche/suggest{q(q=SQLI)}"),
        ("q-emoji-unicode-ctrl", f"/api/recherche/suggest{q(q=UNI + EMOJI + CTRL)}"),
        ("types-garbage", f"/api/recherche/suggest{q(q=com0[:4], types='zzz')}"),
    ]
    specs += _specs_pas_500_par_cas("suggest", r, sugg_cas)
    specs.append(_spec("suggest.pas_nan", r, "jamais NaN",
                       "corps de /api/recherche/suggest sans NaN/Infinity",
                       "FAUX-CLIENT", "pas de NaN/Infinity",
                       lambda api: _controle_pas_nan(api, [("ok", f"/api/recherche/suggest{q(q=com0[:4])}")])))
    specs.append(_spec("suggest.determinisme", r, "déterminisme",
                       "/api/recherche/suggest rend deux fois la même réponse",
                       "ROBUSTESSE", "2 appels identiques",
                       lambda api: _controle_determinisme(api, [("ok", f"/api/recherche/suggest{q(q=com0[:4])}")])))

    # ============ 5) /adresses/autocomplete?q= ============
    r = "/adresses/autocomplete"
    auto_cas = [
        ("q-vide", f"/adresses/autocomplete{q(q='')}"),
        ("q-1car", f"/adresses/autocomplete{q(q='a')}"),
        ("q-long", f"/adresses/autocomplete{q(q=LONG)}"),
        ("q-sqli", f"/adresses/autocomplete{q(q=SQLI)}"),
        ("q-emoji", f"/adresses/autocomplete{q(q=EMOJI)}"),
        ("limit=-1", f"/adresses/autocomplete{q(q='rue', limit=-1)}"),
        ("limit=99999", f"/adresses/autocomplete{q(q='rue', limit=99999)}"),
        ("limit=non-int", f"/adresses/autocomplete{q(q='rue', limit='x')}"),
    ]
    specs += _specs_pas_500_par_cas("autocomplete", r, auto_cas)
    specs.append(_spec("autocomplete.pas_nan", r, "jamais NaN",
                       "corps de /adresses/autocomplete sans NaN/Infinity",
                       "FAUX-CLIENT", "pas de NaN/Infinity",
                       lambda api: _controle_pas_nan(api, [("ok", f"/adresses/autocomplete{q(q='rue')}")])))
    specs.append(_spec("autocomplete.determinisme", r, "déterminisme",
                       "/adresses/autocomplete rend deux fois la même réponse",
                       "ROBUSTESSE", "2 appels identiques",
                       lambda api: _controle_determinisme(api, [("ok", f"/adresses/autocomplete{q(q='rue')}")])))

    # ============ 6) /parcels/at?lon=&lat= ============
    r = "/parcels/at"
    at_cas = [
        ("réunion", f"/parcels/at{q(lon=55.5, lat=-21.0)}"),
        ("0,0", f"/parcels/at{q(lon=0, lat=0)}"),
        ("999,999", f"/parcels/at{q(lon=999, lat=999)}"),
        ("-999,-999", f"/parcels/at{q(lon=-999, lat=-999)}"),
        ("lon-non-num", f"/parcels/at{q(lon='abc', lat=-21.0)}"),
        ("lat-non-num", f"/parcels/at{q(lon=55.5, lat='xyz')}"),
        ("lat-manquant", f"/parcels/at{q(lon=55.5)}"),
        ("lon-manquant", f"/parcels/at{q(lat=-21.0)}"),
        ("inf", f"/parcels/at{q(lon='1e999', lat='1e999')}"),
        ("tous-manquants", "/parcels/at"),
    ]
    specs += _specs_pas_500_par_cas("parcels_at", r, at_cas)
    specs.append(_spec("parcels_at.pas_nan", r, "jamais NaN",
                       "corps de /parcels/at sans NaN/Infinity",
                       "FAUX-CLIENT", "pas de NaN/Infinity",
                       lambda api: _controle_pas_nan(api, [("réunion", f"/parcels/at{q(lon=55.5, lat=-21.0)}"),
                                                           ("0,0", f"/parcels/at{q(lon=0, lat=0)}")])))
    specs.append(_spec("parcels_at.determinisme", r, "déterminisme",
                       "/parcels/at rend deux fois la même réponse",
                       "ROBUSTESSE", "2 appels identiques",
                       lambda api: _controle_determinisme(api, [("réunion", f"/parcels/at{q(lon=55.5, lat=-21.0)}")])))

    # ============ 7) /communes/{commune}/contexte & /communes ============
    r = "/communes/{commune}/contexte"
    ctx_cas = [
        ("valide", f"/communes/{_enc(com0)}/contexte"),
        ("inconnue", "/communes/ZZZZZ/contexte"),
        ("vide-enc", f"/communes/{_enc(' ')}/contexte"),
        ("sqli", f"/communes/{_enc(SQLI)}/contexte"),
        ("unicode", f"/communes/{_enc(UNI)}/contexte"),
        ("long", f"/communes/{_enc(LONG)}/contexte"),
    ]
    specs += _specs_pas_500_par_cas("commune_ctx", r, ctx_cas)
    specs.append(_spec("commune_ctx.pas_nan", r, "jamais NaN",
                       "corps de /communes/{c}/contexte sans NaN/Infinity",
                       "FAUX-CLIENT", "pas de NaN/Infinity",
                       lambda api: _controle_pas_nan(api, [("valide", f"/communes/{_enc(c)}/contexte") for c in com_ok])))
    specs.append(_spec("commune_ctx.determinisme", r, "déterminisme",
                       "/communes/{c}/contexte rend deux fois la même réponse",
                       "ROBUSTESSE", "2 appels identiques",
                       lambda api: _controle_determinisme(api, [("valide", f"/communes/{_enc(com0)}/contexte")])))
    r = "/communes"
    communes_cas = [
        ("sans-src", "/communes"),
        ("src-connue", f"/communes{q(source=SRC)}"),
        ("src-inconnue", f"/communes{q(source='zzz')}"),
        ("src-sqli", f"/communes{q(source=SQLI)}"),
    ]
    specs += _specs_pas_500_par_cas("communes", r, communes_cas)
    specs.append(_spec("communes.determinisme", r, "déterminisme",
                       "/communes rend deux fois la même réponse",
                       "ROBUSTESSE", "2 appels identiques",
                       lambda api: _controle_determinisme(api, [("src", f"/communes{q(source=SRC)}")])))

    # ============ 8) /map/tiles — E-14 régression ============
    r = "/map/tiles/{z}/{x}/{y}.pbf"
    tiles_cas = [
        ("z14-valide", "/map/tiles/14/9000/9000.pbf"),
        ("z=-1", "/map/tiles/-1/0/0.pbf"),
        ("z=0", "/map/tiles/0/5/5.pbf"),
        ("z=30", "/map/tiles/30/0/0.pbf"),
        ("z-non-int", "/map/tiles/abc/0/0.pbf"),
        ("x-hors-grille-E14", "/map/tiles/14/99999/99999.pbf"),   # E-14 vague-1 : doit être GREEN
        ("x-negatif", "/map/tiles/14/-1/-1.pbf"),
        ("x-geant", "/map/tiles/14/999999999/999999999.pbf"),
        ("y-non-int", "/map/tiles/14/9000/xyz.pbf"),
    ]
    specs += _specs_pas_500_par_cas("tiles", r, tiles_cas)
    specs.append(_spec("tiles.determinisme", r, "déterminisme",
                       "/map/tiles rend deux fois le même statut",
                       "ROBUSTESSE", "2 appels identiques",
                       lambda api: _controle_determinisme(api, [("hors-grille", "/map/tiles/14/99999/99999.pbf")])))
    # tiles par couche {kind}
    r2 = "/map/tiles/{kind}/{z}/{x}/{y}.pbf"
    tiles_kind_cas = [
        ("kind-inconnu", "/map/tiles/zzz/14/9000/9000.pbf"),
        ("kind-sqli", f"/map/tiles/{_enc(SQLI)}/14/9000/9000.pbf"),
        ("kind-hors-grille", "/map/tiles/zzz/14/99999/99999.pbf"),
        ("kind-z-non-int", "/map/tiles/zzz/abc/0/0.pbf"),
    ]
    specs += _specs_pas_500_par_cas("tiles_kind", r2, tiles_kind_cas)
    # tiles/meta
    specs.append(_spec("tiles_meta.pas_nan", "/map/tiles/meta", "jamais NaN",
                       "corps de /map/tiles/meta sans NaN/Infinity",
                       "FAUX-CLIENT", "pas de NaN/Infinity",
                       lambda api: _controle_pas_nan(api, [("meta", "/map/tiles/meta")])))
    specs.append(_spec("tiles_meta.null_peuple", "/map/tiles/meta", "null interdit",
                       "/map/tiles/meta a toujours un run_label peuplé",
                       "FAUX-CLIENT", "run_label non null",
                       lambda api: _controle_null_peuple(api, [("meta", "/map/tiles/meta", "run_label")])))
    specs.append(_spec("tiles_meta.determinisme", "/map/tiles/meta", "déterminisme",
                       "/map/tiles/meta rend deux fois la même réponse",
                       "ROBUSTESSE", "2 appels identiques",
                       lambda api: _controle_determinisme(api, [("meta", "/map/tiles/meta")])))

    # ============ 9) /filtre (source REQUISE) ============
    r = "/filtre"
    filtre_cas = [
        ("src-manquante", f"/filtre{q(limit=5)}"),
        ("src-ok", f"/filtre{q(source=SRC, limit=5)}"),
        ("limit=-1", f"/filtre{q(source=SRC, limit=-1)}"),
        ("limit=99999", f"/filtre{q(source=SRC, limit=99999)}"),
        ("offset=-1", f"/filtre{q(source=SRC, offset=-1)}"),
        ("surface_min<0", f"/filtre{q(source=SRC, surface_min=-5)}"),
        ("surface_min>max", f"/filtre{q(source=SRC, surface_min=9999, surface_max=1)}"),
        ("sort-invalide", f"/filtre{q(source=SRC, sort='zzz')}"),
        ("segment-garbage", f"/filtre{q(source=SRC, segment='zzz')}"),
        ("bande-garbage", f"/filtre{q(source=SRC, bande='999')}"),
        ("idus-garbage", f"/filtre{q(source=SRC, idus='zzz,%%%')}"),
        ("zone_plu-sqli", f"/filtre{q(source=SRC, zone_plu=SQLI)}"),
        ("capacite_min-non-num", f"/filtre{q(source=SRC, capacite_min='xx')}"),
        ("combiné-absurde", f"/filtre{q(source=SRC, limit=-1, offset=-1, surface_min='9e9', sort='zzz', bande='999')}"),
    ]
    specs += _specs_pas_500_par_cas("filtre", r, filtre_cas)
    specs.append(_spec("filtre.pas_nan", r, "jamais NaN",
                       "corps de /filtre sans NaN/Infinity",
                       "FAUX-CLIENT", "pas de NaN/Infinity",
                       lambda api: _controle_pas_nan(api, [("ok", f"/filtre{q(source=SRC, limit=20)}")])))
    specs.append(_spec("filtre.determinisme", r, "déterminisme",
                       "/filtre rend deux fois la même réponse",
                       "ROBUSTESSE", "2 appels identiques",
                       lambda api: _controle_determinisme(api, [("ok", f"/filtre{q(source=SRC, limit=10)}")])))

    # ============ 10) /stats & /stats/entonnoir (source REQUISE) ============
    r = "/stats"
    stats_cas = [
        ("src-manquante", "/stats"),
        ("src-ok", f"/stats{q(source=SRC)}"),
        ("src-inconnue", f"/stats{q(source='zzz')}"),
        ("commune-inconnue", f"/stats{q(source=SRC, commune='ZZZZ')}"),
        ("surface_min<0", f"/stats{q(source=SRC, surface_min=-5)}"),
        ("flags-garbage", f"/stats{q(source=SRC, flags='zzz')}"),
    ]
    specs += _specs_pas_500_par_cas("stats", r, stats_cas)
    specs.append(_spec("stats.pas_nan", r, "jamais NaN",
                       "corps de /stats sans NaN/Infinity",
                       "FAUX-CLIENT", "pas de NaN/Infinity",
                       lambda api: _controle_pas_nan(api, [("ok", f"/stats{q(source=SRC)}")])))
    specs.append(_spec("stats.determinisme", r, "déterminisme",
                       "/stats rend deux fois la même réponse",
                       "ROBUSTESSE", "2 appels identiques",
                       lambda api: _controle_determinisme(api, [("ok", f"/stats{q(source=SRC)}")])))
    r = "/stats/entonnoir"
    ent_cas = [
        ("src-manquante", "/stats/entonnoir"),
        ("src-ok", f"/stats/entonnoir{q(source=SRC)}"),
        ("src-inconnue", f"/stats/entonnoir{q(source='zzz')}"),
        ("commune-inconnue", f"/stats/entonnoir{q(source=SRC, commune='ZZZZ')}"),
    ]
    specs += _specs_pas_500_par_cas("entonnoir", r, ent_cas)
    specs.append(_spec("entonnoir.pas_nan", r, "jamais NaN",
                       "corps de /stats/entonnoir sans NaN/Infinity",
                       "FAUX-CLIENT", "pas de NaN/Infinity",
                       lambda api: _controle_pas_nan(api, [("ok", f"/stats/entonnoir{q(source=SRC)}")])))
    specs.append(_spec("entonnoir.null_peuple", r, "null interdit",
                       "/stats/entonnoir a toujours 'analysees' peuplé",
                       "FAUX-CLIENT", "analysees non null",
                       lambda api: _controle_null_peuple(api, [("ok", f"/stats/entonnoir{q(source=SRC)}", "analysees")])))
    specs.append(_spec("entonnoir.determinisme", r, "déterminisme",
                       "/stats/entonnoir rend deux fois la même réponse",
                       "ROBUSTESSE", "2 appels identiques",
                       lambda api: _controle_determinisme(api, [("ok", f"/stats/entonnoir{q(source=SRC)}")])))

    # ============ 11) /parcels/{idu}/zone ============
    r = "/parcels/{idu}/zone"
    zone_cas = [
        ("valide", f"/parcels/{idu0}/zone"),
        ("idu-inconnu", "/parcels/00000000XX0000/zone"),
        ("idu-malformé", "/parcels/abc/zone"),
        ("idu-sqli", f"/parcels/{_enc(SQLI)}/zone"),
        ("mode-garbage", f"/parcels/{idu0}/zone{q(mode='zzz')}"),
        ("minutes=-1", f"/parcels/{idu0}/zone{q(minutes=-1)}"),
        ("minutes=99999", f"/parcels/{idu0}/zone{q(minutes=99999)}"),
        ("minutes-non-int", f"/parcels/{idu0}/zone{q(minutes='x')}"),
    ]
    specs += _specs_pas_500_par_cas("parcels_zone", r, zone_cas)
    specs.append(_spec("parcels_zone.pas_nan", r, "jamais NaN",
                       "corps de /parcels/{idu}/zone sans NaN/Infinity",
                       "FAUX-CLIENT", "pas de NaN/Infinity",
                       lambda api: _controle_pas_nan(api, [("valide", f"/parcels/{idu0}/zone")])))
    specs.append(_spec("parcels_zone.determinisme", r, "déterminisme",
                       "/parcels/{idu}/zone rend deux fois la même réponse",
                       "ROBUSTESSE", "2 appels identiques",
                       lambda api: _controle_determinisme(api, [("inconnu", "/parcels/00000000XX0000/zone")])))

    # ============ 12) /parcels/{idu}/export ============
    r = "/parcels/{idu}/export"
    export_cas = [
        ("valide", f"/parcels/{idu0}/export"),
        ("idu-inconnu", "/parcels/00000000XX0000/export"),
        ("idu-malformé", "/parcels/abc/export"),
        ("idu-sqli", f"/parcels/{_enc(SQLI)}/export"),
    ]
    specs += _specs_pas_500_par_cas("parcels_export", r, export_cas)
    specs.append(_spec("parcels_export.determinisme", r, "déterminisme",
                       "/parcels/{idu}/export rend deux fois la même réponse",
                       "ROBUSTESSE", "2 appels identiques",
                       lambda api: _controle_determinisme(api, [("valide", f"/parcels/{idu0}/export")])))

    # ============ 13) routes sans paramètre : NaN + null + déterminisme ============
    sans_param = [
        ("config_run", "/config/run", "run"),
        ("sante_fraicheur", "/sante/fraicheur", "empreinte_attendue"),
        ("vocab_paliers", "/vocabulaire/paliers", None),
        ("vocab_scoring", "/vocabulaire/scoring-fraction", None),
    ]
    for rid, path, champ in sans_param:
        specs.append(_spec(f"{rid}.pas_nan", path, "jamais NaN",
                           f"corps de {path} sans NaN/Infinity",
                           "FAUX-CLIENT", "pas de NaN/Infinity",
                           lambda api, _p=path: _controle_pas_nan(api, [("v", _p)])))
        specs.append(_spec(f"{rid}.determinisme", path, "déterminisme",
                           f"{path} rend deux fois la même réponse",
                           "ROBUSTESSE", "2 appels identiques",
                           lambda api, _p=path: _controle_determinisme(api, [("v", _p)])))
        if champ:
            specs.append(_spec(f"{rid}.null_peuple", path, "null interdit",
                               f"{path} a toujours '{champ}' peuplé",
                               "FAUX-CLIENT", f"{champ} non null",
                               lambda api, _p=path, _c=champ: _controle_null_peuple(api, [("v", _p, _c)])))

    # ── règles écartées (traçabilité : générées ≠ retenues) ──────────────────────────────────
    ecartees.append(N.Ecartee(
        "F5.discover.pas_500", "F5", "route /discover",
        "la route /discover n'existe pas (404 constant) dans l'OpenAPI servi — pas une route client à tester"))
    ecartees.append(N.Ecartee(
        "F5.parcels_at.null_interdit", "F5", "route /parcels/at",
        "un idu null sur /parcels/at (aucune parcelle au point) est LÉGITIME, pas une violation FAUX-CLIENT ; "
        "contrôle null-peuplé non applicable à cette route"))
    ecartees.append(N.Ecartee(
        "F5.commune_ctx.null_interdit", "F5", "route /communes/{c}/contexte",
        "une commune inconnue rend un contexte à champs null (insee/epci null) de façon GRACIEUSE "
        "— le null y est attendu, contrôle null-peuplé non applicable"))

    return specs, ecartees


if __name__ == "__main__":
    API = "http://127.0.0.1:8793"
    cx = N.connexion()
    specs, ecartees = generer(cx)
    print(f"F5 — générées {len(specs)} règles, écartées {len(ecartees)}")
    if not N.api_dispo(API):
        print("API indisponible — abandon")
        raise SystemExit(1)
    resultats = N.run_specs(cx, specs, api=API)
    b = N.bilan(resultats)
    print(f"bilan : OK={b['OK']} ECART={b['ECART']} SKIP={b['SKIP']}")
    print("--- écartées ---")
    for e in ecartees:
        print(f"  {e.id} : {e.raison}")
    print("--- détail ---")
    for r in resultats:
        marque = {"OK": "  ok ", "ECART": "ECART", "SKIP": "skip "}[r.statut]
        print(f"[{marque}] {r.spec.id}")
        if r.statut in ("ECART", "SKIP"):
            print(f"         {r.message[:400]}")
