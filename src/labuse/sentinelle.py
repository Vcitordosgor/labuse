"""SENTINELLE-1 — l'agent de veille des sources amont, généralisé à toutes les sources.

DOCTRINE (à ne pas transgresser) : la sentinelle **surveille et prévient**. Elle ne télécharge rien,
n'ingère rien, ne remplace aucune donnée, n'écrit JAMAIS dans `data_sources`. Vic décide de chaque mise
à jour. Elle ne visite JAMAIS un portail d'annonces — uniquement les fournisseurs de données publiques
(IGN, DGFiP, INSEE, Sitadel, BAN, DHUP…). Détection 100 % mécanique : dates, motifs, en-têtes ; zéro LLM.

QUATRE MÉTHODES (W2 + SENTINELLE-3 Y3), chacune déclarée par la source dans `source_veille.methode` :
  · `api`    — le fournisseur expose un JSON de versions. `selecteur` = chemin JSON (`a.b.0.c`).
  · `page`   — page HTML, `selecteur` = regex de millésime (ex. `20\\d{2}-S[12]`) ; on garde le PLUS récent.
  · `entete` — pas de millésime lisible : on compare `Last-Modified`/`ETag` au dernier vu (`dernier_entete`).
  · `temoin` — (SENTINELLE-3) API de REQUÊTE sans notion de version : on fige une requête témoin et on
               compare une EMPREINTE stable de la réponse (`selecteur` = chemin JSON vers un agrégat
               stable — un compte, une liste courte — ou None pour la réponse entière) au dernier passage.
               Elle ne nomme AUCUNE version : elle dit « la donnée amont a changé ». L'empreinte est
               mémorisée dans `dernier_entete` (même colonne que `entete` : un marqueur opaque).

`api`/`page` détectent une VERSION (millésime comparable) ; `entete`/`temoin` détectent un CHANGEMENT
(sans nommer de version). Une 5e valeur, `rappel` (Y4), n'est PAS une sonde : c'est un rappel de
rafraîchissement posé sur une source MANUELLE (aucun amont public) — jamais interrogé (cf. `_lignes_a_sonder`).

Une source injoignable/illisible n'est PAS une source en erreur : c'est la SENTINELLE qui a échoué,
pas la donnée (W3.5 — les deux états restent distincts partout).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import ssl
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import text

import logging

log = logging.getLogger("labuse.sentinelle")

#: User-Agent identifiant LABUSE (W3.2) — un serveur public sait qui l'interroge.
USER_AGENT = "LABUSE-sentinelle/1.0 (+exploitation ; contact via data.gouv)"
#: appel one-shot, timeout COURT, aucun retry en boucle (W3.2).
TIMEOUT_S = 12.0
#: délai entre deux sources interrogées séquentiellement — on ne martèle pas un serveur public (W3.2).
DELAI_ENTRE_SOURCES_S = 2.0

STATUTS = ("ok", "nouvelle_version", "injoignable", "illisible")


@dataclass
class Sonde:
    """Résultat d'un passage sur UNE source. `vu` = millésime/en-tête constaté amont (jamais servi tel
    quel). `entete` = valeur d'en-tête à mémoriser (methode entete seulement)."""
    statut: str                    # ok | nouvelle_version | injoignable | illisible
    vu: str | None = None
    message: str | None = None
    entete: str | None = None


# ─────────────────────────────── la couche HTTP (injectable) ───────────────────────────────
# UN SEUL point de sortie réseau — les tests le monkeypatchent, jamais d'appel réel en CI.

#: CIRCUIT-P4 (lot 0) — LE FAISCEAU DE CA EXPLICITE. Sur macOS avec le Python de Homebrew, le
#: contexte TLS par défaut d'`urllib` ne connaît AUCUNE autorité de certification (le trousseau
#: système n'est pas branché sur OpenSSL) : les 84 sondes tombaient toutes en
#: `CERTIFICATE_VERIFY_FAILED` et la page mentait — « producteur injoignable » partout en local.
#: On fournit un faisceau explicite : `SSL_CERT_FILE` (posé dans `.env` si Vic veut) sinon le
#: bundle `certifi` (toujours packagé). En prod Linux, le contexte par défaut marche déjà ; ce
#: faisceau ne fait que le rendre déterministe. Cf. docs/CIRCUIT/VERROUS.md.
_SSL_CONTEXT: "ssl.SSLContext | None" = None


def _ssl_context() -> "ssl.SSLContext":
    """Contexte TLS avec un faisceau de CA garanti (SSL_CERT_FILE, sinon certifi)."""
    global _SSL_CONTEXT  # noqa: PLW0603 — cache module, construit une fois
    if _SSL_CONTEXT is None:
        cafile = os.environ.get("SSL_CERT_FILE") or None
        if not cafile:
            try:
                import certifi
                cafile = certifi.where()
            except Exception:  # noqa: BLE001 — certifi absent : contexte par défaut, DIT au log
                log.warning("certifi introuvable et SSL_CERT_FILE non posé — TLS sur le trousseau système")
                cafile = None
        _SSL_CONTEXT = ssl.create_default_context(cafile=cafile)
    return _SSL_CONTEXT


def _http(url: str, *, methode_http: str = "GET") -> tuple[int, dict, str]:
    """Requête HTTP one-shot, timeout court, User-Agent LABUSE. Retourne (status, en-têtes, corps).
    Lève sur échec réseau (capté par l'appelant → `injoignable`). Aucun retry ici (doctrine W3.2).
    Le contexte TLS porte un faisceau de CA explicite (lot 0) ; ignoré pour un URL `http://`."""
    req = urllib.request.Request(url, method=methode_http, headers={"User-Agent": USER_AGENT})
    ctx = _ssl_context() if url.lower().startswith("https:") else None
    with urllib.request.urlopen(req, timeout=TIMEOUT_S, context=ctx) as resp:  # noqa: S310 — URL du catalogue, jamais client
        entetes = {k.lower(): v for k, v in resp.headers.items()}
        corps = "" if methode_http == "HEAD" else resp.read(1_000_000).decode("utf-8", "replace")
        return resp.status, entetes, corps


# ─────────────────────────────── les trois méthodes de détection ───────────────────────────────

def _json_pointe(obj, selecteur: str):
    """Descend `obj` selon un chemin pointé `a.b.0.c` (clé de dict ou index de liste). None si absent."""
    cur = obj
    for seg in selecteur.split("."):
        if isinstance(cur, list):
            try:
                cur = cur[int(seg)]
            except (ValueError, IndexError):
                return None
        elif isinstance(cur, dict):
            cur = cur.get(seg)
        else:
            return None
        if cur is None:
            return None
    return cur


def sonder_api(url: str, selecteur: str | None) -> Sonde:
    """`api` — GET JSON, extraction du millésime au chemin `selecteur`. `selecteur` absent → on rend
    le corps entier stringifié tronqué (rare ; mieux vaut un chemin)."""
    status, _, corps = _http(url)
    if status >= 400:
        return Sonde("injoignable", message=f"HTTP {status}")
    try:
        data = json.loads(corps)
    except ValueError:
        # SILENCE-1 (point 5) — une réponse NON-JSON d'une API JSON est quasi toujours un hoquet SERVEUR
        # (page d'erreur/maintenance HTML, 429/Cloudflare rendu en 200, coupure) : c'est la SOURCE qui a
        # bronché, pas notre lecteur. On classe donc « injoignable » (transitoire, couvert par la grâce
        # `circuit_etats` < 7 j) et non « illisible » (= notre contrat est faux, en panne dès 3). C'est ce
        # qui faisait « tomber » BODACC un matin sur un simple hoquet opendatasoft (3 non-JSON d'affilée).
        # Un chemin JSON introuvable DANS un corps JSON valide reste « illisible » (vrai contrat cassé).
        return Sonde("injoignable", message="réponse non-JSON (hoquet serveur)")
    val = _json_pointe(data, selecteur) if selecteur else data
    if val is None:
        return Sonde("illisible", message=f"chemin JSON introuvable : {selecteur}")
    return Sonde("ok", vu=str(val).strip())


def sonder_page(url: str, selecteur: str | None) -> Sonde:
    """`page` — GET HTML, `selecteur` = regex de millésime ; on garde le PLUS récent trouvé (jamais le
    premier venu). Aucun motif → illisible (la page a peut-être changé de forme)."""
    if not selecteur:
        return Sonde("illisible", message="aucun sélecteur (regex) fourni")
    status, _, corps = _http(url)
    if status >= 400:
        return Sonde("injoignable", message=f"HTTP {status}")
    try:
        trouves = re.findall(selecteur, corps)
    except re.error as exc:
        return Sonde("illisible", message=f"regex invalide : {exc}")
    if not trouves:
        return Sonde("illisible", message="motif de millésime absent de la page")
    # findall peut rendre des tuples si le motif a des groupes — on aplatit sur la correspondance complète.
    plats = [t if isinstance(t, str) else "".join(t) for t in trouves]
    return Sonde("ok", vu=max(plats).strip())   # plus récent = max lexical (formats normés triables)


def sonder_entete(url: str, dernier_entete: str | None) -> Sonde:
    """`entete` — HEAD (repli GET) ; compare `Last-Modified`/`ETag` au dernier vu. Ne nomme aucune
    version : signale seulement « le fichier amont a changé ». Premier passage = baseline (ok, mémorise)."""
    try:
        status, entetes, _ = _http(url, methode_http="HEAD")
    except Exception:  # noqa: BLE001 — certains serveurs refusent HEAD : repli GET
        status, entetes, _ = _http(url, methode_http="GET")
    if status >= 400:
        return Sonde("injoignable", message=f"HTTP {status}")
    val = (entetes.get("etag") or entetes.get("last-modified") or "").strip()
    if not val:
        # TABLEAU-1 (point 3) — certains serveurs de téléchargement (ex. dossier SIS de la préfecture)
        # n'exposent NI ETag NI Last-Modified utile (header vide) mais TOUJOURS un Content-Length : un
        # dossier mis à jour change de taille. On s'en sert comme empreinte de version (signal de veille,
        # pas une garantie à l'octet près). Dernier repli seulement.
        cl = (entetes.get("content-length") or "").strip()
        if cl:
            val = f"taille:{cl}"
    if not val:
        return Sonde("illisible", message="ni ETag ni Last-Modified ni Content-Length sur l'en-tête amont")
    val = val.strip()
    if dernier_entete and val != dernier_entete:
        return Sonde("nouvelle_version", vu=val, entete=val,
                     message="le fichier amont a changé (ETag/Last-Modified) depuis le dernier passage")
    return Sonde("ok", vu=val, entete=val)


def _empreinte(val) -> str:
    """Empreinte STABLE et COMPACTE d'une valeur témoin (Y3). Scalaire (compte, date) → sa chaîne ;
    liste/dict → longueur + hachage court. On ne stocke JAMAIS la réponse entière, juste de quoi
    constater qu'elle a changé — et jamais un horodatage volatil (le témoin doit porter sur un agrégat
    stable, cf. doctrine Y3 : sinon l'empreinte n'a aucun sens et il faut écarter la source)."""
    if isinstance(val, (str, int, float, bool)):
        return str(val).strip()
    canon = json.dumps(val, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    h = hashlib.sha256(canon.encode("utf-8")).hexdigest()[:16]
    n = len(val) if isinstance(val, (list, dict)) else 0
    return f"{n}:{h}"


#: TABLEAU-1 (point 3) — miroirs Overpass (l'endpoint public overpass-api.de est régulièrement saturé :
#: 502/timeout). On réessaie la MÊME requête sur un miroir avant de conclure « injoignable ». Best-effort.
_OVERPASS_MIROIRS = ("overpass.kumi.systems", "overpass.private.coffee")


def _http_temoin(url: str) -> tuple[int, dict, str]:
    """GET d'un témoin, avec REPLI SUR MIROIR pour Overpass (amont public souvent en 502/timeout). On
    tente l'URL d'origine ; si c'est un endpoint Overpass et qu'il échoue (réseau ou HTTP), on rejoue la
    même requête sur un miroir connu (hôte différent). Hors Overpass : aucun repli (comportement W3.2)."""
    try:
        return _http(url)
    except Exception:  # noqa: BLE001
        if "overpass" not in url.lower():
            raise
        for host in _OVERPASS_MIROIRS:
            miroir = re.sub(r"https?://[^/]+/", f"https://{host}/", url, count=1)
            try:
                return _http(miroir)
            except Exception:  # noqa: BLE001 — miroir aussi en panne : on essaie le suivant
                continue
        raise


def _lire_temoin(url: str, selecteur: str | None):
    """Lit UN témoin : (valeur extraite, None) si OK, sinon (None, Sonde d'échec). Facteur commun aux
    témoins mono- et bi-commune (S4.2)."""
    status, _, corps = _http_temoin(url)
    if status >= 400:
        return None, Sonde("injoignable", message=f"HTTP {status}")
    # TABLEAU-1 (point 3) — témoin sur réponse NON-JSON (atom/xml/texte) : un sélecteur « re:<motif> »
    # extrait la valeur témoin par regex sur le corps BRUT (ex. OCS GE : le <updated> du flux atom amont).
    # Pas de json.loads — c'est ainsi qu'on lit un amont qui ne sert pas du JSON.
    if selecteur and selecteur.startswith("re:"):
        try:
            trouves = re.findall(selecteur[3:], corps)
        except re.error as exc:
            return None, Sonde("illisible", message=f"regex témoin invalide : {exc}")
        if not trouves:
            return None, Sonde("illisible", message=f"motif témoin introuvable : {selecteur[3:]}")
        plats = [t if isinstance(t, str) else "".join(t) for t in trouves]
        return max(plats).strip(), None
    try:
        data = json.loads(corps)
    except ValueError:
        return None, Sonde("illisible", message="réponse non-JSON")
    val = _json_pointe(data, selecteur) if selecteur else data
    if val is None:
        # TABLEAU-1 (point 3) — JSON valide mais FeatureCollection VIDE : c'est un creux amont MOMENTANÉ
        # (ex. WFS geopf qui renvoie 0 feature pour le bbox sous charge), pas notre lecteur qui est cassé
        # → injoignable (transitoire, couvert par le grace < 7 j), jamais illisible.
        if isinstance(data, dict) and isinstance(data.get("features"), list) and not data["features"]:
            return None, Sonde("injoignable", message="réponse sans feature (amont momentané)")
        return None, Sonde("illisible", message=f"chemin JSON introuvable : {selecteur}")
    return val, None


def sonder_temoin(url: str, selecteur: str | None, empreinte_prec: str | None,
                  url2: str | None = None) -> Sonde:
    """`temoin` (SENTINELLE-3 Y3) — requête TÉMOIN figée sur une API sans notion de version : on lit une
    EMPREINTE stable de la réponse (`selecteur` = chemin JSON vers un agrégat stable, ou None = réponse
    entière) et on la compare au dernier passage. Ne nomme AUCUNE version : signale « la donnée amont a
    changé ». Premier passage = baseline (ok, mémorise l'empreinte dans `dernier_entete`, marqueur opaque).

    SUITE-1 S4.2 — si `url2` (seconde commune témoin, Saint-Benoît) est fourni, l'empreinte combine les
    DEUX chef-lieux : un changement de L'UN OU L'AUTRE change l'empreinte → « la donnée amont a changé ».
    Les deux appels restent légers et espacés (une passe par jour, délai entre sources déjà appliqué)."""
    val, echec = _lire_temoin(url, selecteur)
    if echec is not None:
        return echec
    if url2:
        val2, echec2 = _lire_temoin(url2, selecteur)
        if echec2 is not None:
            return echec2
        emp = _empreinte([val, val2])   # combinée : l'un OU l'autre change → l'empreinte change
    else:
        emp = _empreinte(val)
    if empreinte_prec and emp != empreinte_prec:
        return Sonde("nouvelle_version", vu=emp, entete=emp,
                     message="la donnée amont a changé (empreinte de requête témoin) depuis le dernier passage")
    return Sonde("ok", vu=emp, entete=emp)


# ─────────────────────────────── comparaison au millésime SERVI ───────────────────────────────

def _plus_recent(vu: str, servi: str) -> bool:
    """`vu` (amont) est-il postérieur à `servi` (base) ? Comparaison lexicale — les millésimes normés
    (2026, 2026-S1, 2026-04) se trient correctement. Prudence : jamais « nouvelle version » si égal."""
    return vu.strip() > servi.strip()


def evaluer(sonde: Sonde, servi: str | None) -> Sonde:
    """Applique la comparaison au millésime réellement servi (W3.3, `data_sources.source_millesime`).
    `entete` a déjà tranché (nouvelle_version vs ok) sans notion de « servi ». Pour `api`/`page` : une
    lecture `ok` devient `nouvelle_version` SI le millésime amont est postérieur au servi."""
    if sonde.statut != "ok" or not sonde.vu:
        return sonde
    if servi and _plus_recent(sonde.vu, servi):
        return Sonde("nouvelle_version", vu=sonde.vu, entete=sonde.entete,
                     message=f"amont {sonde.vu} postérieur au servi {servi}")
    return sonde


# ─── VERIF-FIX-1 (Q3) — `ortho` : détection d'une Ortho Express plus récente POUR LA RÉUNION ───
# Spécifique à l'ortho basemap servie en direct (WMTS IGN), que l'`api` data.gouv ne sait pas juger
# par île : l'IGN publie un millésime pour la métropole AVANT La Réunion, et a RENOMMÉ la famille
# (`ORTHO-EXPRESS.*` → `RVB-EXPRESS.*`) à partir de 2026. On lit le GetCapabilities (tous les millésimes
# publiés, ancien ET nouveau nommage), on prend le plus récent, et on CONFIRME qu'il couvre bien l'île
# par une tuile témoin à Saint-Denis (une 404 = publié métropole mais pas encore Réunion → on ne crie pas).
_ORTHO_LAYER_RE = re.compile(r"ORTHOIMAGERY\.ORTHOPHOTOS\.(?:ORTHO-EXPRESS|RVB-EXPRESS)\.\d{4}")
_ORTHO_TUILE_974 = (16, 42863, 36657)   # z/col/row — tuile Saint-Denis (témoin de couverture La Réunion)
_ORTHO_TUILE_URL = ("https://data.geopf.fr/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&STYLE=normal"
                    "&TILEMATRIXSET=PM&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&LAYER={layer}&FORMAT=image/jpeg")


def _ortho_couvre_974(layer: str) -> bool:
    """La couche sert-elle une tuile RÉELLE à Saint-Denis ? (404 = pas encore La Réunion.)"""
    z, x, y = _ORTHO_TUILE_974
    try:
        status, _, _ = _http(_ORTHO_TUILE_URL.format(layer=layer, z=z, x=x, y=y))
    except urllib.error.HTTPError as exc:
        status = exc.code
    return bool(status) and status < 400


def sonder_ortho(url: str, servi: str | None) -> Sonde:
    """`ortho` — GetCapabilities WMTS IGN : le millésime Ortho Express/RVB Express le plus récent qui
    COUVRE La Réunion, comparé au servi. `nouvelle_version` seulement si plus récent ET présent sur l'île."""
    status, _, corps = _http(url)
    if status >= 400:
        return Sonde("injoignable", message=f"HTTP {status} (GetCapabilities)")
    par_annee = {int(lid[-4:]): lid for lid in _ORTHO_LAYER_RE.findall(corps)}
    if not par_annee:
        return Sonde("illisible", message="aucune couche ORTHO-EXPRESS/RVB-EXPRESS au GetCapabilities")
    servi_an = max([int(a) for a in re.findall(r"20\d{2}", servi or "")] or [0])
    recent = max(par_annee)
    if recent > servi_an and _ortho_couvre_974(par_annee[recent]):
        return Sonde("nouvelle_version", vu=f"{par_annee[recent]} (couvre La Réunion)")
    msg = (f"{recent} publiée mais hors Réunion (servi {servi_an})"
           if recent > servi_an else f"servi {servi_an} — rien de plus récent pour La Réunion")
    return Sonde("ok", vu=f"Ortho Express {servi_an}", message=msg)


def sonder_dvf(url: str | None, servi: str | None) -> Sonde:
    """FRAICHEUR-FIX-1 (point 1/6) — DVF géo-DVF au FORMAT ETALAB ACTUEL : lit la LISTE DES RESSOURCES
    du jeu data.gouv (`full-AAAA[-sN]`) et rend le DERNIER MILLÉSIME PUBLIÉ comme `dernier_vu`
    (ex. « 2026-S1 »). Fini la lecture du Last-Modified de l'arborescence legacy FIGÉE (FRAICHEUR-1
    §4.1). Le VERDICT « en retard » n'est PAS tranché ici (le sonde ne connaît pas l'horizon ingéré) :
    il l'est à la lecture, par `etats_sources` qui compare ce `dernier_vu` au millésime réellement
    ingéré (table servie) — c'est le cœur du mandat (point 6)."""
    from .ingestion import dvf_etalab
    ressources, _ = dvf_etalab.lister_ressources()
    dernier = dvf_etalab.dernier_millesime(ressources)
    if not dernier:
        return Sonde("illisible", message="aucune ressource full-AAAA-sN au jeu data.gouv DVF")
    return Sonde("ok", vu=dernier, message=f"dernier fichier publié : full-{dernier.lower()}")


def sonder_ligne(row: dict, servi: str | None, *, http=None) -> Sonde:
    """Sonde UNE ligne `source_veille` (dict : methode, url_version, selecteur, dernier_entete) et rend
    le verdict évalué. `http` : injection de la couche réseau pour les tests (défaut = `_http` réel)."""
    global _http  # noqa: PLW0603 — point d'injection réseau unique
    if http is not None:
        _prev, _http = _http, http
    try:
        methode = (row.get("methode") or "").strip()
        url = row.get("url_version")
        if not methode or not url:
            return Sonde("illisible", message="ligne incomplète (methode/url manquante)")
        try:
            if methode == "api":
                s = sonder_api(url, row.get("selecteur"))
            elif methode == "page":
                s = sonder_page(url, row.get("selecteur"))
            elif methode == "entete":
                s = sonder_entete(url, row.get("dernier_entete"))
            elif methode == "temoin":
                s = sonder_temoin(url, row.get("selecteur"), row.get("dernier_entete"),
                                  url2=row.get("url_temoin_2"))
            elif methode == "ortho":
                s = sonder_ortho(url, servi)   # VERIF-FIX-1 (Q3) — tranche seule (couverture Réunion)
            elif methode == "dvf":
                s = sonder_dvf(url, servi)     # FRAICHEUR-FIX-1 — dernier fichier full-AAAA-sN publié
            else:
                return Sonde("illisible", message=f"méthode inconnue : {methode}")
        except Exception as exc:  # noqa: BLE001 — tout échec réseau/parse = la SENTINELLE a échoué, pas la donnée
            return Sonde("injoignable", message=f"{type(exc).__name__}: {str(exc)[:200]}")
        # `entete`/`temoin`/`ortho` ont déjà tranché (aucune comparaison lexicale au « servi » à appliquer) :
        # seules les méthodes À VERSION (api/page) passent par `evaluer`.
        return evaluer(s, servi) if methode in ("api", "page") else s
    finally:
        if http is not None:
            _http = _prev


# ─────────────────────────────── le passage (orchestration W3) ───────────────────────────────

def _lignes_a_sonder(db, *, source_ids=None, forcer: bool) -> list[dict]:
    """Lignes `actif=true` dont la cadence est ÉCHUE (ou toutes si `forcer`, ou celles ciblées). On
    joint `data_sources` pour lire le millésime SERVI (source_millesime) et le nom (message/notif)."""
    # SENTINELLE-3 (Y4) — on ne sonde QUE les vraies méthodes de surveillance ; une ligne `rappel`
    # (source manuelle, rafraîchissement attendu) n'est jamais interrogée sur le réseau.
    where = ["v.actif = true", "v.methode IN ('api', 'page', 'entete', 'temoin', 'ortho', 'dvf')"]
    params: dict = {}
    if source_ids:
        where.append("v.source_id = ANY(:ids)")
        params["ids"] = list(source_ids)
    if not forcer and not source_ids:
        # cadence échue : jamais passé, ou passage plus vieux que cadence_heures.
        where.append("(v.dernier_passage_at IS NULL OR "
                     "v.dernier_passage_at <= now() - make_interval(hours => v.cadence_heures))")
    sql = ("SELECT v.id, v.source_id, v.url_version, v.url_temoin_2, v.methode, v.selecteur, v.cadence_heures,"
           "       v.dernier_entete, v.dernier_vu, v.dernier_notifie_vu, v.echecs_consecutifs, v.mail_alerte,"
           "       d.name AS source_nom, d.source_millesime AS servi"
           " FROM source_veille v JOIN data_sources d ON d.id = v.source_id"
           " WHERE " + " AND ".join(where) + " ORDER BY d.name")
    return [dict(r) for r in db.execute(text(sql), params).mappings()]


#: X5.2 — nombre de sondes en échec CONSÉCUTIVES avant de prévenir Vic (un serveur public tombe, ça se
#: relève ; on ne notifie ni au 1er ni au 2e échec, seulement quand le 3e le confirme).
SEUIL_ECHECS_NOTIF = 3


def passer(db, *, source_ids=None, forcer: bool = False, http=None, notifier: bool = True,
           delai_s: float | None = None) -> dict:
    """UN passage de la sentinelle (W3). Parcourt les lignes échues, sonde SÉQUENTIELLEMENT avec un
    délai, écrit le résultat dans `source_veille` (JAMAIS dans `data_sources`). À la fin du passage,
    dépose AU PLUS UNE notification admin — le RÉSUMÉ du jour (X5.1) — agrégeant :
      · les sources dont l'amont a une nouvelle version JAMAIS encore annoncée (dédup par
        `dernier_notifie_vu` : on ne ré-annonce pas un millésime déjà vu par Vic → pas de rappel quotidien) ;
      · les sondes qui viennent d'atteindre 3 échecs consécutifs (X5.2 : ni au 1er ni au 2e passage).
    Une seule cloche « N sources ont du nouveau », dépliable — jamais N notifications (X5.1).

    Retourne {sondees, nouvelles, injoignables, illisibles, notifs, details:[…]}. `notifs` ∈ {0,1} =
    le digest a-t-il été émis. `http`/`delai_s` sont des points d'injection pour les tests."""
    lignes = _lignes_a_sonder(db, source_ids=source_ids, forcer=forcer)
    delai = DELAI_ENTRE_SOURCES_S if delai_s is None else delai_s
    recap = {"sondees": 0, "nouvelles": 0, "injoignables": 0, "illisibles": 0, "notifs": 0, "details": []}
    digest_neuf: list[dict] = []   # sources à annoncer (nouvelle version jamais vue)
    digest_echec: list[dict] = []  # sondes qui atteignent le seuil d'échecs consécutifs À CE PASSAGE
    for i, row in enumerate(lignes):
        if i and delai:
            time.sleep(delai)   # on n'enchaîne pas les appels sans respirer (serveur public)
        s = sonder_ligne(row, row.get("servi"), http=http)
        recap["sondees"] += 1
        # entete : on ne mémorise l'en-tête que quand on en a un (baseline ou changement).
        nouvel_entete = s.entete if s.entete is not None else row.get("dernier_entete")
        echoue = s.statut in ("injoignable", "illisible")
        echecs = (int(row.get("echecs_consecutifs") or 0) + 1) if echoue else 0
        # dernier_notifie_vu : conservé tel quel, mis à jour SEULEMENT quand on annonce (plus bas).
        db.execute(text(
            "UPDATE source_veille SET dernier_passage_at = now(), dernier_vu = :vu,"
            "  dernier_statut = :st, dernier_message = :msg, dernier_entete = :ent,"
            "  echecs_consecutifs = :ec, updated_at = now() WHERE id = :id"),
            {"vu": s.vu, "st": s.statut, "msg": s.message, "ent": nouvel_entete,
             "ec": echecs, "id": row["id"]})
        if s.statut == "nouvelle_version":
            recap["nouvelles"] += 1
            deja = row.get("dernier_notifie_vu")
            if s.vu and s.vu != deja:      # jamais encore annoncé ce millésime → au digest
                digest_neuf.append({"row": row, "sonde": s})
                db.execute(text("UPDATE source_veille SET dernier_notifie_vu = :v WHERE id = :id"),
                           {"v": s.vu, "id": row["id"]})
        elif s.statut == "injoignable":
            recap["injoignables"] += 1
        elif s.statut == "illisible":
            recap["illisibles"] += 1
        if echoue and echecs == SEUIL_ECHECS_NOTIF:   # PILE au 3e (une seule fois par épisode)
            digest_echec.append({"row": row, "sonde": s})
        recap["details"].append({"source": row["source_nom"], "statut": s.statut, "vu": s.vu,
                                 "servi": row.get("servi"), "message": s.message, "echecs": echecs})
    if notifier and (digest_neuf or digest_echec) and _emettre_digest(db, digest_neuf, digest_echec):
        recap["notifs"] = 1
    return recap


def acquitter_apres_injection(db, nom: str) -> dict:
    """SILENCE-1 (point 1) — APRÈS UNE INJECTION RÉUSSIE d'une source (appelée par la chaîne détachée
    `ingest && filtre && source-acquitter`, donc UNIQUEMENT si ingestion + filtre ont réussi), on ACQUITTE
    la veille ET on met à jour la VERSION SERVIE pour que la carte « nouvelle version » DISPARAISSE.

    POURQUOI c'était bloqué : rien ne remettait la veille à « ok » après injection. L'injection ne posait
    que `injection_lancee_at`/`injection_vu` à l'amorçage ; `data_sources.source_millesime` (le servi)
    n'était jamais avancé, et `source_veille.dernier_statut` restait « nouvelle_version ». Les témoins
    (annuaire DILA, OFB) le ré-affichaient à chaque passage ; la source par agent (Population INSEE) n'est
    même PLUS sondée (`passer` n'interroge que api/page/entete/temoin) → le latch ne tombait jamais.

    On remet donc, idempotemment :
      · `dernier_statut = 'ok'`, `dernier_notifie_vu = injection_vu = dernier_vu` (plus ré-annoncé) ;
      · `echecs_consecutifs = 0`, `injection_lancee_at = now()` ;
      · méthode `temoin` : `dernier_entete = dernier_vu` (baseline → le prochain passage compare la MÊME
        valeur, reste « ok ») ;
      · méthodes À VERSION (`api`/`page`) : `data_sources.source_millesime = dernier_vu` (le servi suit
        l'amont injecté, sinon `evaluer()` re-déclencherait « nouvelle_version »). `agent`/`entete`
        n'utilisent pas `source_millesime` comme version → on n'y touche pas.
    Retourne {nom, trouve, statut_avant, vu, servi_maj}."""
    row = db.execute(text(
        "SELECT v.id, v.source_id, v.methode, v.dernier_vu, v.dernier_statut "
        "FROM source_veille v JOIN data_sources d ON d.id = v.source_id WHERE d.name = :n"),
        {"n": nom}).mappings().first()
    if not row:
        return {"nom": nom, "trouve": False}
    vu = row["dernier_vu"]
    methode = (row["methode"] or "").strip()
    # CAST(:vu AS varchar) partout : le même paramètre réutilisé sans cast fait inférer à psycopg des
    # types incohérents (varchar vs text) → AmbiguousParameter (même piège qu'OPS-NUIT-2 sur :n).
    set_entete = ", dernier_entete = CAST(:vu AS varchar)" if methode == "temoin" else ""
    db.execute(text(
        "UPDATE source_veille SET dernier_statut = 'ok', dernier_notifie_vu = CAST(:vu AS varchar), "
        "injection_vu = CAST(:vu AS varchar), injection_lancee_at = now(), echecs_consecutifs = 0, "
        "updated_at = now()" + set_entete + " WHERE id = :id"), {"vu": vu, "id": row["id"]})
    servi_maj = False
    if methode in ("api", "page") and vu:
        db.execute(text("UPDATE data_sources SET source_millesime = CAST(:vu AS varchar) WHERE id = :sid"),
                   {"vu": vu, "sid": row["source_id"]})
        servi_maj = True
    return {"nom": nom, "trouve": True, "statut_avant": row["dernier_statut"], "vu": vu,
            "servi_maj": servi_maj}


# ─────────────────────────────── W5 · peuplement de la table ───────────────────────────────
# Une entrée = (nom EXACT de la source en base) → méthode + URL amont RÉELLE (déjà portée par
# data_sources, jamais inventée) + sélecteur. Choix conservateur (W5.3 : une URL non vérifiée est
# pire qu'une absence). On privilégie `entete` (aucun sélecteur à deviner) pour les fichiers versionnés,
# `page` pour l'index DVF (cas phare du mandat), `api` seulement quand le champ de date est un contrat
# documenté et stable. Les sources absentes d'ici restent NON surveillées (état normal) — cf. compte-rendu.
#: SENTINELLE-2 (X1-X3) — chaque entrée a été APPELÉE POUR DE VRAI et sa réponse LUE avant d'être
#: inscrite (règle qui commande le mandat : jamais une URL supposée ; une sonde `illisible`/`injoignable`
#: au semis n'est pas inscrite). Verdict de vérification = `ok` sur les 35 (probe réel 2026-09-01, via la
#: couche `_http` de production, UA LABUSE). Familles débloquées d'un coup :
#:   · data.gouv.fr `/api/1/datasets/{slug}` → `last_update` (le mandat l'endosse explicitement pour
#:     « toute la famille ») : couvre les produits IGN servis en WFS (BD TOPO, BD ORTHO, RGE ALTI, BD
#:     CARTO, LiDAR MNH, RPG, PCI, Contours IRIS), les jeux INSEE (BPE, Filosofi, RP2022), et d'autres.
#:   · Opendatasoft v2.1 `/catalog/datasets/{ds}` → `metas.default.modified` (Région Réunion + DILA).
#:   · `entete` (ETag/Last-Modified) pour les téléchargements directs stables (cadastre, DGFiP-PM, érosion).
#:   · cas isolés : DPE ADEME (data-fair `dataUpdatedAt`), SITADEL (Dido `last_update`), classement
#:     sonore Cerema (FeatureServer ArcGIS, compteur témoin `count` — requête sans notion de version, X2).
#: Les DOUBLONS amont (Cadastre Etalab bulk ≡ PCI, RGE ALTI 5 m ≡ RGE ALTI) ne sont PAS re-semés : ils
#: sont couverts par la veille de leur canonique (l'alerte vaut pour les deux). Cf. SENTINELLE-INVENTAIRE.md.
SEED: list[dict] = [
    # ── SOURCES-3 lot 2 — sentinelles data.gouv APPELÉES POUR DE VRAI le 2026-09-14 (last_update lu,
    #    `ok`) : RNIC (Anah, actualisation quotidienne — vu 2026-09-12) et RPLS (SDES, millésime 2023,
    #    dépôt 2025-08-24). Famille `/api/1/datasets/{slug}/` → `last_update`, endossée par le mandat.
    {"name": "RNIC — registre national des copropriétés (Anah)", "methode": "api",
     "url": "https://www.data.gouv.fr/api/1/datasets/registre-national-dimmatriculation-des-coproprietes/",
     "selecteur": "last_update"},
    {"name": "RPLS — répertoire des logements locatifs sociaux (SDES)", "methode": "api",
     "url": "https://www.data.gouv.fr/api/1/datasets/repertoire-des-logements-locatifs-des-bailleurs-sociaux/",
     "selecteur": "last_update"},
    # ── RETOURS-13 R4/R5 — réseaux et TCSP. EDF : le portail Koumoul n'expose pas de JSON de
    #    version simple → en-tête du fichier data-fair (change quand EDF republie). Réunion
    #    Express : la carte des hypothèses de tracé (landweb3d) — un changement d'en-tête dit
    #    « la Région a mis à jour la carte » (le tracé bougera après le débat, clôture 26/11/2026).
    {"name": "EDF Réunion — lignes moyenne tension HTA (open data)", "methode": "entete",
     "url": ("https://opendata-reunion.edf.fr/data-fair/api/v1/datasets/"
             "lihub-72mnuv47c249qzvlhv/data-files/lignes-haute-tension-hta-aerien.csv")},
    {"name": "Réunion Express — hypothèses de tracé (débat public CNDP)", "methode": "entete",
     "url": "https://client.landweb3d.com/cr-reunion/Reunion-Express_PC/index_jaune.html"},
    # ── Famille IGN Géoplateforme : jeu data.gouv officiel du produit → `last_update` (même amont IGN
    #    que les couches servies en WFS). Débloque 8 sources d'un coup (X2, gisement principal). ──
    {"name": "Cadastre (API Carto PCI)", "methode": "api",
     "url": "https://www.data.gouv.fr/api/1/datasets/parcellaire-express-pci/", "selecteur": "last_update"},
    {"name": "BD TOPO IGN", "methode": "api",
     "url": "https://www.data.gouv.fr/api/1/datasets/bd-topo-r/", "selecteur": "last_update"},
    {"name": "Forêts publiques (ONF)", "methode": "api",   # BDTOPO_V3:foret_publique → même jeu bd-topo-r
     "url": "https://www.data.gouv.fr/api/1/datasets/bd-topo-r/", "selecteur": "last_update"},
    # VERIF-FIX-1 (Q3) — l'ortho « Actuelle » servie en direct (WMTS) : la sonde `api` data.gouv ne
    # savait pas juger la couverture PAR ÎLE. On passe à la méthode `ortho` qui lit le GetCapabilities
    # WMTS IGN (tous millésimes, ancien ET nouveau nommage RVB-EXPRESS) et confirme la présence sur La
    # Réunion par une tuile témoin → signale « nouvelle version » dans la page Données quand l'île l'a.
    {"name": "BD ORTHO 20 cm (IGN)", "methode": "ortho",
     "url": "https://data.geopf.fr/wmts?SERVICE=WMTS&REQUEST=GetCapabilities&VERSION=1.0.0", "selecteur": None},
    {"name": "BD ORTHO IRC (IGN)", "methode": "api",       # dérivée IRC de la BD ORTHO → même jeu bd-ortho-r
     "url": "https://www.data.gouv.fr/api/1/datasets/bd-ortho-r/", "selecteur": "last_update"},
    {"name": "RGE ALTI (altimétrie)", "methode": "api",
     "url": "https://www.data.gouv.fr/api/1/datasets/rge-alti-r/", "selecteur": "last_update"},
    {"name": "IGN BD CARTO V5 — occupation du sol", "methode": "api",
     "url": "https://www.data.gouv.fr/api/1/datasets/bd-carto-r-1/", "selecteur": "last_update"},
    # RECETTE-11 A5 — le data.gouv `mnh-lidar-hd` (last_update) est NATIONAL : il bouge pour n'importe
    # quelle republication en France, pas pour « le 974 ». On surveille le CANAL RÉELLEMENT INGÉRÉ (la
    # grille de dalles LiDAR HD, WFS metadata IGN) BORNÉ à l'emprise Réunion : témoin sur la DERNIÈRE
    # ÉDITION des dalles 974 (COUNT=1, SORTBY date_edition D) — une nouvelle campagne ou re-diffusion sur
    # l'île bouge cette date → « la donnée amont a changé ». URL réellement appelée (probe 2026-09-10).
    {"name": "LiDAR HD — MNH 50 cm (IGN)", "methode": "temoin",
     "url": ("https://data.geopf.fr/wfs/ows?SERVICE=WFS&REQUEST=GetFeature&VERSION=2.0.0"
             "&TYPENAMES=IGNF_LIDAR-HD_METADONNEE:metadata&SRSNAME=EPSG:4326&COUNT=1"
             "&OUTPUTFORMAT=application/json&SORTBY=date_edition%20D"
             "&PROPERTYNAME=date_edition,code_mission&BBOX=-21.40,55.20,-20.80,55.85"),
     "selecteur": "features.0.properties.date_edition"},
    # REPARATIONS-1 lot 4 — RNB : flux CONTINU sans millésime nommé. Le canal incrémental réel
    # est GET /buildings/diff/?since= (CSV national — lu par ingestion.rnb.version_diff) ; la
    # sonde fige DEUX bâtiments témoins 974 (Saint-Denis + Entre-Deux) : toute modification RNB
    # sur l'un d'eux change l'empreinte → « la donnée amont a changé » (jamais un faux signal
    # national). URLs réellement appelées (probe 13/09/2026).
    # REPARATIONS-1 lot 5 + TABLEAU-1 (point 3) — OCS GE : le catalogue de téléchargement IGN sert
    # désormais un flux ATOM (application/atom+xml), PAS du JSON — d'où l'ancien « réponse non-JSON ».
    # La date <updated> du flux porte la publication du produit D974 : une nouvelle livraison (millésime
    # ou correctif) la change. On lit donc le témoin par REGEX sur le corps atom (selecteur « re:… »),
    # sur les DEUX produits (OCS-GE + artificialisation). Probe 03/11/2026 : <updated>2025-04-10…</updated>.
    {"name": "OCS GE (IGN) — occupation du sol et artificialisation", "methode": "temoin",
     "url": "https://data.geopf.fr/telechargement/resource/OCSGE/OCS-GE_2-0__GPKG_RGR92UTM40S_D974_2022-01-01",
     "url2": "https://data.geopf.fr/telechargement/resource/OCSGE-ARTIFICIALISATION/OCS-GE-ARTIFICIALISATION_2-0_DIFF-2017-2022_GPKG_RGR92UTM40S_D974_2025-09-16",
     "selecteur": "re:<updated>([^<]+)</updated>"},
    {"name": "RNB — Référentiel National des Bâtiments", "methode": "temoin",
     "url": "https://rnb-api.beta.gouv.fr/api/alpha/buildings/B74TG4FPXST4/",
     "url2": "https://rnb-api.beta.gouv.fr/api/alpha/buildings/1126R7BCDWR1/",
     "selecteur": None},
    # GEOPF-3 — GéoMCE (mesures compensatoires) : WFS sans millésime nommé. Témoin = la mesure 974
    # la plus récente (tri date_decision) — une nouvelle mesure change l'empreinte (date la plus récente).
    {"name": "GéoMCE — mesures compensatoires", "methode": "temoin",
     "url": ("https://data.geopf.fr/wfs/ows?SERVICE=WFS&REQUEST=GetFeature&VERSION=2.0.0"
             "&TYPENAMES=MESURES_COMPENSATOIRES:emprises_polygones&SRSNAME=EPSG:4326&COUNT=1"
             "&OUTPUTFORMAT=application/json&SORTBY=date_decision%20D"
             "&BBOX=55.20,-21.42,55.90,-20.85,EPSG:4326"),
     "selecteur": "features.0.properties.date_decision"},
    # GEOPF-3 + TABLEAU-1 (point 3) — SCOT (GPU) : WFS sans millésime nommé. L'ancienne URL triait par
    # `SORTBY=gpu_timestamp D` + COUNT=1 : geopf renvoyait un ordre NON DÉTERMINISTE (parfois un SCOT au
    # gpu_timestamp null en tête) → « chemin JSON introuvable ». On ne trie plus : on demande les
    # gpu_timestamp de TOUS les SCOT du 974 (PROPERTYNAME → réponse ~0,4 ko, sans géométrie) et on garde
    # le PLUS RÉCENT par regex (témoin « re: », robuste à l'ordre et aux nulls). Une nouvelle publication
    # GPU change le max → l'empreinte change. (Une FeatureCollection vide → injoignable transitoire.)
    {"name": "SCOT (GPU)", "methode": "temoin",
     "url": ("https://data.geopf.fr/wfs/ows?SERVICE=WFS&REQUEST=GetFeature&VERSION=2.0.0"
             "&TYPENAMES=wfs_scot:scot&SRSNAME=EPSG:4326&COUNT=50&PROPERTYNAME=gpu_timestamp"
             "&OUTPUTFORMAT=application/json&BBOX=55.20,-21.42,55.90,-20.85,EPSG:4326"),
     "selecteur": "re:\"gpu_timestamp\":\"([^\"]+)\""},
    # GEOPF-3 — zones exclues EnR sauf toiture (OFB/APER) : WFS sans millésime nommé. Témoin = empreinte
    # de la 1re zone 974 (une révision du zonage APER change la réponse).
    {"name": "Zones exclues EnR sauf toiture (OFB/APER)", "methode": "temoin",
     "url": ("https://data.geopf.fr/wfs/ows?SERVICE=WFS&REQUEST=GetFeature&VERSION=2.0.0"
             "&TYPENAMES=OFB_ZONES.EXCLUES.SAUF.TOITURE:zones_exclues_aires_acceleration_sauf_toiture"
             "&SRSNAME=EPSG:4326&COUNT=1&OUTPUTFORMAT=application/json"
             "&BBOX=55.20,-21.42,55.90,-20.85,EPSG:4326"),
     "selecteur": None},
    # GEOPF-3 — BD NYME (lieux-dits) : même jeu amont que la BD TOPO (bd-topo-r), sonde data.gouv.
    {"name": "BD NYME — lieux-dits (IGN)", "methode": "api",
     "url": "https://www.data.gouv.fr/api/1/datasets/bd-topo-r/", "selecteur": "last_update"},
    {"name": "Contours IRIS (IGN/INSEE)", "methode": "api",
     "url": "https://www.data.gouv.fr/api/1/datasets/contours-iris/", "selecteur": "last_update"},
    {"name": "RPG — déclarations agricoles (IGN/ASP)", "methode": "api",
     "url": "https://www.data.gouv.fr/api/1/datasets/rpg/", "selecteur": "last_update"},
    # ── Famille INSEE (jeu national data.gouv → `last_update` ; l'URL fichier .zip INSEE n'expose ni
    #    ETag ni Last-Modified sur HEAD — vérifié, `entete` y renvoie illisible, donc écarté). ──
    {"name": "BPE INSEE", "methode": "api",
     "url": "https://www.data.gouv.fr/api/1/datasets/base-permanente-des-equipements-3/", "selecteur": "last_update"},
    {"name": "Filosofi INSEE (carreaux 200 m)", "methode": "api",
     "url": "https://www.data.gouv.fr/api/1/datasets/donnees-carroyees-a-200-m-sur-la-population/", "selecteur": "last_update"},
    {"name": "INSEE RP2022 — fichier détail Logements (EGOUL)", "methode": "api",
     "url": "https://www.data.gouv.fr/api/1/datasets/recensement-de-la-population-fichiers-detail-logements-ordinaires/", "selecteur": "last_update"},
    # ── Autres jeux data.gouv (last_update) ──
    # DVF — cas phare du mandat FRAICHEUR-FIX-1. L'ancienne sonde `page` lisait l'index legacy
    # `/geo-dvf/latest/csv/` qui ne liste QUE 2021–2025 (figé depuis mai 2026, supprimé au 31/11/2026) :
    # elle rendait toujours « 2025 » = servi → « à jour » faussement alors que l'amont publie S1 2026
    # (nouveau format `full-AAAA-sN`). La méthode `dvf` lit la LISTE DES RESSOURCES du jeu data.gouv et
    # rend le dernier fichier publié (« 2026-S1 ») ; le verdict « en retard » est tranché à la lecture.
    {"name": "DVF / valeurs foncières", "methode": "dvf",
     "url": "https://www.data.gouv.fr/api/1/datasets/demandes-de-valeurs-foncieres-geolocalisees/",
     "selecteur": None},
    {"name": "QPV 2024 (ANCT)", "methode": "api",   # SENTINELLE-1 sondait le .zip horodaté (périt à chaque
     # génération → deviendrait injoignable) ; le jeu data.gouv `last_update` est stable et suit les gén.
     "url": "https://www.data.gouv.fr/api/1/datasets/quartiers-prioritaires-de-la-politique-de-la-ville-qpv/", "selecteur": "last_update"},
    {"name": "Cartofriches (Cerema)", "methode": "api",
     "url": "https://www.data.gouv.fr/api/1/datasets/cartofriches/", "selecteur": "last_update"},
    # SCORING-3 (L3) — BDNB (CSTB) : jeu data.gouv officiel, `last_update` (sondé 03/09/2026 :
    # 2026-05-22, millésime 2026-02-a). La sentinelle PRÉVIENT ; l'ingestion (39 Go streamés,
    # filtre 974) reste le CRON trimestriel `ingest-bdnb` — jamais auto-injectée.
    {"name": "BDNB", "methode": "api",
     "url": "https://www.data.gouv.fr/api/1/datasets/base-de-donnees-nationale-des-batiments/",
     "selecteur": "last_update"},
    {"name": "ZNIEFF (INPN/MNHN)", "methode": "api",
     "url": "https://www.data.gouv.fr/api/1/datasets/inventaire-des-zones-naturelles-dinteret-ecologique-faunistique-et-floristique-znieff/", "selecteur": "last_update"},
    {"name": "ABF / Monuments historiques", "methode": "api",   # remplace l'endpoint ODS culture décommissionné
     "url": "https://www.data.gouv.fr/api/1/datasets/immeubles-proteges-au-titre-des-monuments-historiques-2/", "selecteur": "last_update"},
    {"name": "Géorisques", "methode": "api",   # base gaspar (amont de l'API Géorisques live)
     "url": "https://www.data.gouv.fr/api/1/datasets/base-nationale-de-gestion-assistee-des-procedures-administratives-relatives-aux-risques-gaspar/", "selecteur": "last_update"},
    {"name": "Géorisques — ICPE", "methode": "api",   # base ICPE BRGM (amont de /installations_classees)
     "url": "https://www.data.gouv.fr/api/1/datasets/installations-classees-pour-la-protection-de-lenvironnement-icpe-france-metropolitaine-et-drom-3/", "selecteur": "last_update"},
    {"name": "Base Adresse Nationale", "methode": "api",
     "url": "https://www.data.gouv.fr/api/1/datasets/base-adresse-nationale/", "selecteur": "last_update"},
    {"name": "SIRENE", "methode": "api",
     "url": "https://www.data.gouv.fr/api/1/datasets/base-sirene-des-entreprises-et-de-leurs-etablissements-siren-siret/", "selecteur": "last_update"},
    {"name": "SIRENE établissements géolocalisés", "methode": "api",
     "url": "https://www.data.gouv.fr/api/1/datasets/geolocalisation-des-etablissements-du-repertoire-sirene-pour-les-etudes-statistiques/", "selecteur": "last_update"},
    {"name": "Transport public — GTFS (PAN, 7 réseaux)", "methode": "api",   # canari Citalis (PAN, cf. seed)
     "url": "https://www.data.gouv.fr/api/1/datasets/horaire-du-reseau-citalis/", "selecteur": "last_update"},
    {"name": "CoSIA (couverture du sol IA, IGN)", "methode": "api",   # le .7z Géoplateforme n'a pas d'en-tête
     "url": "https://www.data.gouv.fr/api/1/datasets/cosia/", "selecteur": "last_update"},
    # ── Famille Opendatasoft v2.1 → `metas.default.modified` (Région Réunion + DILA). ──
    # SILENCE-1 (point 5) — on lit la FRAÎCHEUR RÉELLE (dernière date de parution des annonces), pas la
    # date de modification du dataset (`metas.default.modified` restait figée à 2021 → aucune fraîcheur) :
    # l'endpoint `records` trié par `dateparution desc` rend la dernière parution (contrat JSON stable,
    # `results.0.dateparution`). Même source, millésime qui bouge vraiment chaque jour.
    {"name": "BODACC (procédures collectives)", "methode": "api",
     "url": ("https://bodacc-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/"
             "annonces-commerciales/records?select=dateparution&order_by=dateparution%20desc&limit=1"),
     "selecteur": "results.0.dateparution"},
    {"name": "Parc National de La Réunion (INPN)", "methode": "api",
     "url": "https://data.regionreunion.com/api/explore/v2.1/catalog/datasets/pnrun_2021", "selecteur": "metas.default.modified"},
    {"name": "data.regionreunion.com — Potentiel foncier", "methode": "api",
     "url": "https://data.regionreunion.com/api/explore/v2.1/catalog/datasets/potentiel-foncier", "selecteur": "metas.default.modified"},
    {"name": "Potentiel foncier Région (Région ODS)", "methode": "api",   # même jeu ODS potentiel-foncier (SAR proxy)
     "url": "https://data.regionreunion.com/api/explore/v2.1/catalog/datasets/potentiel-foncier", "selecteur": "metas.default.modified"},
    {"name": "Trafic RN (Région Réunion — SIR)", "methode": "api",
     "url": "https://data.regionreunion.com/api/explore/v2.1/catalog/datasets/trafic-mja-rn-lareunion", "selecteur": "metas.default.modified"},
    # ── Téléchargements directs stables → `entete` (détection GENUINE du changement d'octets, sans servi). ──
    {"name": "DGFiP — parcelles des personnes morales", "methode": "entete",
     "url": "https://data.economie.gouv.fr/api/v2/catalog/datasets/fichiers-des-locaux-et-des-parcelles-des-personnes-morales/attachments/fichier_des_parcelles_situation_2025_dpts_57_a_976_zip",
     "selecteur": None},
    {"name": "Cerema / GéoLittoral — indicateur d'érosion côtière", "methode": "entete",
     "url": "https://geolittoral.din.developpement-durable.gouv.fr/telechargement/couches_sig/N_evolution_trait_cote_S_reunion_epsg2975_062018_shape.zip",
     "selecteur": None},
    # SOURCES-2 lot 2 — GPU : témoin sur l'APPARITION du document de Saint-Leu (le PLU révisé,
    # enquête publique 01/09–09/10/2026, doit être publié au GPU à l'approbation ; aujourd'hui
    # 0 document à la partition DU_97413, vérifié 13/09/2026). `/document?partition=` est LÉGER
    # (métadonnées seules) et remplace l'ancienne raison « pas de millésime global » : le module
    # procedure n'existe pas à l'API Carto (404 vérifié), l'apparition du document EST le signal.
    {"name": "Urbanisme PLU/GPU (API Carto)", "methode": "temoin",
     "url": "https://apicarto.ign.fr/api/gpu/document?partition=DU_97413",
     "selecteur": "totalFeatures"},
    # SOURCES-2 lot 2 — SIS : les DÉFINITIFS passent par le canal SSP (témoin bi-commune déjà
    # en place sur « sites et sols pollués ») ; on surveille EN PLUS le dossier des PROJETS
    # Nord-Est/Sud à la préfecture (ZIP officiel, détection d'octets) — une republication du
    # dossier (nouvel arrêté, création des SIS) change l'empreinte.
    {"name": "Géorisques — secteurs d'information sur les sols (SIS)", "methode": "entete",
     "url": ("https://www.reunion.gouv.fr/contenu/telechargement/51477/389074/file/"
             "dossier%20SIS%20actualis%C3%A9.zip"),
     "selecteur": None},
    # SOURCES-2 lot 3 — BAN PLUS : métadonnée `last_update` du jeu data.gouv (IGN).
    {"name": "BAN PLUS — lien adresse ↔ bâtiment (IGN)", "methode": "api",
     "url": "https://www.data.gouv.fr/api/1/datasets/ban-plus/", "selecteur": "last_update"},
    # ── Cas isolés vérifiés ──
    # DPE ADEME — data-fair `dataUpdatedAt` (métadonnée documentée stable du dataset).
    # SOURCES-2 lot 0 : l'ingestion couvre les TROIS jeux (dpe03existant + dpe02neuf +
    # dpe01tertiaire) ; mesuré 13/09/2026, les trois publient dans le MÊME train mensuel
    # (dataUpdatedAt 09/09 tous les trois) → le jeu principal suffit comme signal de version.
    {"name": "DPE ADEME (logements existants)", "methode": "api",
     "url": "https://data.ademe.fr/data-fair/api/v1/datasets/dpe03existant", "selecteur": "dataUpdatedAt"},
    # SITADEL — Dido (SDES). FRAICHEUR-FIX-1 (point 2/6) : l'ancien sélecteur `last_update` lisait la
    # date de MODIFICATION du dataset (30/10), PAS le dernier mois de DONNÉES — or la base détail retarde
    # structurellement de ~1,5-2 mois sur la note, donc `last_update` était toujours « en avance » sur
    # l'ingéré (faux signal, FRAICHEUR-1 §3.1). On lit `temporal_coverage.end` = le DERNIER MOIS COUVERT
    # (ex. 2026-09-30) → comparable au mois réellement ingéré (max(date) sitadel_permits).
    {"name": "SITADEL (autorisations d'urbanisme)", "methode": "api",
     "url": "https://data.statistiques.developpement-durable.gouv.fr/dido/api/v1/datasets/6513f0189d7d312c80ec5b5b",
     "selecteur": "temporal_coverage.end"},
    # Classement sonore ITT — endpoint de REQUÊTE ArcGIS sans notion de version : requête témoin
    # `returnCountOnly` → compteur stable `count` (X2, cas particulier assumé ; un changement du nombre
    # de tronçons signale une republication).
    {"name": "Classement sonore ITT (Cerema)", "methode": "api",
     "url": "https://cartagene.cerema.fr/server/rest/services/Hosted/Routes_classement_sonore_La_Reunion_V2/FeatureServer/0/query?where=1%3D1&returnCountOnly=true&f=json",
     "selecteur": "count"},
    # ══════════════════════ SENTINELLE-3 — second passage sur les non surveillées ══════════════════════
    # Chacune APPELÉE POUR DE VRAI et sa réponse LUE avant inscription (probe réel 2026-09-01, couche
    # `_http`, UA LABUSE). Détail des pistes essayées : SENTINELLE-INVENTAIRE.md.
    # ── Y1 · les récupérables ──
    # DEAL — PPR : le WFS Lizmap DEAL (deal974.lizmap.com, de nouveau joignable) n'expose pas de projet
    # « risques » ni de date lisible. L'amont RÉEL des PPR est la base GASPAR (Géorisques), qui porte une
    # `dateModification` par PPR. Requête TÉMOIN figée sur la commune chef-lieu (Saint-Denis 97411) →
    # empreinte du PPR (déterministe, vérifié) ; une révision DEAL/Géorisques change l'empreinte. PPR = à
    # fort enjeu (le risque figure dans les fiches parcelles), donc surveillé même par témoin de commune.
    # S4.2 — second chef-lieu témoin : Saint-Benoît (97410). Alerte si l'un des deux PPR change.
    {"name": "DEAL Réunion — PPR / aléas", "methode": "temoin",
     "url": "https://georisques.gouv.fr/api/v1/gaspar/pprn?codeInsee=97411&page=1&page_size=50",
     "url2": "https://georisques.gouv.fr/api/v1/gaspar/pprn?codeInsee=97410&page=1&page_size=50",
     "selecteur": "content"},
    # (DEAL WMS/WFS resté non surveillé : le seul jeu data.gouv « NPNRU » est DÉPARTEMENTAL — Bouches-du-
    #  Rhône, pas la Réunion ; pas d'URL amont honnête. Cf. RAISONS_NON_SURVEILLEES.)
    # ── Y2 · le hub qui expose un catalogue ──
    # Région ODS : portail (283 jeux), pas un jeu unique — mais l'API catalogue Opendatasoft v2.1 rend
    # `total_count`. Témoin sur le NOMBRE de jeux : quand une couche apparaît/disparaît, le catalogue a
    # évolué (c'est ainsi qu'on apprend qu'un nouveau jeu exploitable existe). `limit=0` = requête ultra-légère.
    {"name": "Région Réunion Open Data (Opendatasoft)", "methode": "temoin",
     "url": "https://data.regionreunion.com/api/explore/v2.1/catalog/datasets?limit=0", "selecteur": "total_count"},
    # ── Y3 · les API de requête → requête témoin (empreinte d'un agrégat stable) ──
    # Géorisques live (cavités, mouvements de terrain, sites & sols pollués) : pas de millésime, mais un
    # COMPTE stable par commune. Témoin figé sur Saint-Denis 97411 (commune à risques, déterministe vérifié) ;
    # une republication BRGM change le compte/empreinte → « la donnée amont a changé ».
    # S4.2 — chacune sondée sur DEUX chef-lieux (Saint-Denis 97411 + Saint-Benoît 97410) : empreinte
    # combinée, alerte si l'un des deux change. Appels toujours légers (page_size=1) et espacés.
    {"name": "Géorisques — cavités souterraines", "methode": "temoin",
     "url": "https://www.georisques.gouv.fr/api/v1/cavites?code_insee=97411&page=1&page_size=1",
     "url2": "https://www.georisques.gouv.fr/api/v1/cavites?code_insee=97410&page=1&page_size=1", "selecteur": "results"},
    {"name": "Géorisques — mouvements de terrain", "methode": "temoin",
     "url": "https://www.georisques.gouv.fr/api/v1/mvt?code_insee=97411&page=1&page_size=1",
     "url2": "https://www.georisques.gouv.fr/api/v1/mvt?code_insee=97410&page=1&page_size=1", "selecteur": "results"},
    # ssp : la réponse groupe casias/instructions/conclusions (pas de compte unique) → empreinte de la
    # réponse ENTIÈRE (déterministe vérifié, aucun horodatage volatil au sommet).
    {"name": "Géorisques — sites et sols pollués", "methode": "temoin",
     "url": "https://www.georisques.gouv.fr/api/v1/ssp?code_insee=97411&page=1&page_size=200",
     "url2": "https://www.georisques.gouv.fr/api/v1/ssp?code_insee=97410&page=1&page_size=200", "selecteur": None},
    # ── SOURCES-1 lot 1 — la SONDE CATÉGORIELLE des SUP 974 : l'API JSON du service de
    # téléchargement du GPU (le même service que le flux Atom, qui n'est pas filtrable par
    # territoire) rend les documents SUP du département — catégorie, gestionnaire, millésime
    # AAAAMMJJ, statut. Une publication (ex. AS1 captages, absente au 06/09/2026), un retrait
    # ou un nouveau millésime change l'empreinte → « la donnée amont a changé ».
    {"name": "SUP — assiettes GPU (API Carto)", "methode": "temoin",
     "url": "https://www.geoportail-urbanisme.gouv.fr/api/document?documentType%5B%5D=SUP&grid=974",
     "selecteur": None},
    # ══════════════════════ SOURCES-3b lot 2 — sonde des « jamais vérifié » ══════════════════════
    # Chacune APPELÉE POUR DE VRAI (couche _http, UA LABUSE) — jamais une URL supposée ; une sonde
    # illisible/injoignable au semis n'est PAS conservée ici (retirée, raison écrite au rapport).
    # ── data.gouv (famille api → last_update) ──
    {"name": "Sudocuh (procédures d'urbanisme)", "methode": "api",
     "url": ("https://www.data.gouv.fr/api/1/datasets/planification-nationale-des-documents-durbanisme-"
             "plu-plui-cc-rnu-donnees-sudocuh-dernier-etat-des-lieux-annuel-au-31-decembre-2024/"),
     "selecteur": "last_update"},
    # ── Géorisques (témoin bi-commune, empreinte figée — même famille que cavités/mvt/ssp) ──
    {"name": "CatNat (arrêtés GASPAR / Géorisques)", "methode": "temoin",
     "url": "https://www.georisques.gouv.fr/api/v1/gaspar/catnat?code_insee=97411&page=1&page_size=200",
     "url2": "https://www.georisques.gouv.fr/api/v1/gaspar/catnat?code_insee=97410&page=1&page_size=200",
     "selecteur": None},
    {"name": "Géorisques — CASIAS (anciens sites industriels)", "methode": "temoin",
     "url": "https://www.georisques.gouv.fr/api/v1/ssp?code_insee=97411&page=1&page_size=200",
     "url2": "https://www.georisques.gouv.fr/api/v1/ssp?code_insee=97410&page=1&page_size=200",
     "selecteur": None},
    # ── Opendatasoft (portails data.economie / service-public) : témoin sur total_count (requête ultra-
    #    légère limit=0 ; une republication change le nombre d'enregistrements → « la donnée a changé »). ──
    {"name": "Taxe d'aménagement — taux communaux (délibérations)", "methode": "temoin",
     "url": ("https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/"
             "delta_deliberation_tam_17_01_23/records?limit=0"), "selecteur": "total_count"},
    {"name": "Annuaire de l'administration (service-public.fr / DILA)", "methode": "temoin",
     "url": ("https://api-lannuaire.service-public.fr/api/explore/v2.1/catalog/datasets/"
             "api-lannuaire-administration/records?limit=0"), "selecteur": "total_count"},
    # ── data.gouv : Cadastre Etalab (dataset « cadastre », last_update 2026-09-08 vérifié). ──
    {"name": "Cadastre d'époque (Etalab / PCI vecteur DGFiP)", "methode": "api",
     "url": "https://www.data.gouv.fr/api/1/datasets/cadastre/", "selecteur": "last_update"},
    # SOURCES-3b lot 6 — le slug data.gouv du CONSOENAF (Cerema) retrouvé via la table ingérée
    # (source_url) : last_update 2025-05-12 vérifié. Sort la Conso NAF des « jamais vérifié ».
    {"name": "Consommation d'espaces NAF (Cerema — portail de l'artificialisation)", "methode": "api",
     "url": "https://www.data.gouv.fr/api/1/datasets/consommation-despaces-naturels-agricoles-et-forestiers-du-1er-janvier-2009-au-1er-janvier-2024/",
     "selecteur": "last_update"},
    # ── recherche-entreprises (DINUM + INPI RNE) : témoin sur total_results d'une requête 974 figée —
    #    une republication INSEE/INPI change le nombre. DINUM reste servie (retrait différé q_v15) et
    #    doit garder une veille ; l'INPI RNE (dirigeants) est exposé par le MÊME service. ──
    {"name": "Recherche d'entreprises (DINUM)", "methode": "temoin",
     "url": "https://recherche-entreprises.api.gouv.fr/search?q=mairie&departement=974&page=1&per_page=1",
     "selecteur": "total_results"},
    # ── OSM / Overpass (parkings APER, pôles d'échange, TCSP) — FRAICHEUR-FIX-1 (point 5) : la sonde
    #    `temoin` live a été RETIRÉE. Diagnostic mesuré depuis le VPS (10/11/2026) : overpass-api.de est
    #    en 502 « at capacity » de façon persistante (≠ panne réseau → les 16-18 « injoignable » de
    #    FRAICHEUR-1 §4.5), les miroirs kumi.systems/private.coffee NE RÉSOLVENT PAS depuis le VPS
    #    (HTTP 000), et overpass.osm.ch répond (200) mais est une instance RÉGIONALE sans le planet
    #    complet (compte 974 = 0, faux). Aucun Overpass fiable depuis le VPS → une sonde live ne peut que
    #    (a) crier injoignable en boucle, ou (b) projeter « à jour » sans rien vérifier (fraîcheur inerte).
    #    On REMPLACE donc par un RAPPEL de fraîcheur sur le SNAPSHOT ingéré (cf. RAPPELS_MANUELS) : honnête
    #    (« snapshot OSM non rafraîchi depuis N jours »), jamais un faux vert ni une fausse alerte amont.
    # ── GPU API Carto (prescriptions/info-surf servies DANS les documents PLU ; le seul endpoint
    #    versionnable est `document?partition=DU_<insee>` → totalFeatures — une republication du PLU
    #    de la commune témoin qui porte la couche change l'empreinte. Communes témoins choisies là où
    #    la couche EXISTE (SOURCES-2) : assainissement→Étang-Salé, DPU→Saint-Denis, PEB→Saint-Pierre). ──
    {"name": "GPU — zonages d'assainissement", "methode": "temoin",
     "url": "https://apicarto.ign.fr/api/gpu/document?partition=DU_97404", "selecteur": "totalFeatures"},
    {"name": "GPU — emplacements réservés (prescriptions CNIG)", "methode": "temoin",
     "url": "https://apicarto.ign.fr/api/gpu/document?partition=DU_97411", "selecteur": "totalFeatures"},
    {"name": "GPU — espaces boisés classés (prescriptions CNIG)", "methode": "temoin",
     "url": "https://apicarto.ign.fr/api/gpu/document?partition=DU_97415", "selecteur": "totalFeatures"},
    {"name": "GPU — droit de préemption urbain (info-surf)", "methode": "temoin",
     "url": "https://apicarto.ign.fr/api/gpu/document?partition=DU_97411", "selecteur": "totalFeatures"},
    {"name": "PEB — plans d'exposition au bruit (DGAC via annexes GPU)", "methode": "temoin",
     "url": "https://apicarto.ign.fr/api/gpu/document?partition=DU_97416", "selecteur": "totalFeatures"},
    # ── DEAL Lizmap : le WFS GetCapabilities porte un ETag stable (entete). Un changement des couches
    #    publiées du projet change l'ETag → « la donnée amont a changé ». Le projet 00cartogenerale porte
    #    50 pas / ravines / zones humides / espaces protégés ; 02sprinr/03digues porte l'endiguement. ──
    {"name": "50 pas géométriques — limite haute (DEAL)", "methode": "entete",
     "url": "https://deal974.lizmap.com/cartes/index.php/lizmap/service?repository=00cartogenerale&project=deal_reunion&SERVICE=WFS&REQUEST=GetCapabilities"},
    {"name": "Ravines — domaine public fluvial (DEAL Carmen)", "methode": "entete",
     "url": "https://deal974.lizmap.com/cartes/index.php/lizmap/service?repository=00cartogenerale&project=deal_reunion&SERVICE=WFS&REQUEST=GetCapabilities"},
    {"name": "Zones humides — inventaires DEAL (Carmen)", "methode": "entete",
     "url": "https://deal974.lizmap.com/cartes/index.php/lizmap/service?repository=00cartogenerale&project=deal_reunion&SERVICE=WFS&REQUEST=GetCapabilities"},
    {"name": "Espaces protégés complémentaires — Ramsar, sites classés/inscrits (DEAL Carmen)", "methode": "entete",
     "url": "https://deal974.lizmap.com/cartes/index.php/lizmap/service?repository=00cartogenerale&project=deal_reunion&SERVICE=WFS&REQUEST=GetCapabilities"},
    {"name": "Systèmes d'endiguement et zones protégées (DEAL Lizmap)", "methode": "entete",
     "url": "https://deal974.lizmap.com/cartes/index.php/lizmap/service?repository=02sprinr&project=03digues&SERVICE=WFS&REQUEST=GetCapabilities"},
    # ── SOURCES-1 lot 1 — zonage ABC : jeu data.gouv DHUP (arrêté national) → last_update.
    {"name": "Zonage ABC des communes (DHUP)", "methode": "api",
     "url": "https://www.data.gouv.fr/api/1/datasets/liste-des-communes-selon-le-zonage-abc/",
     "selecteur": "last_update"},
    # ── SOURCES-1 lot 2 — AZI/TRI : même famille que les témoins Géorisques (deux chef-lieux).
    {"name": "AZI / TRI — inondation (Géorisques GASPAR)", "methode": "temoin",
     "url": "https://www.georisques.gouv.fr/api/v1/gaspar/azi?code_insee=97411&page=1&page_size=100",
     "url2": "https://www.georisques.gouv.fr/api/v1/gaspar/azi?code_insee=97410&page=1&page_size=100",
     "selecteur": None},
    # ── SOURCES-1 lot 5 — la valeur : jeux data.gouv à last_update (famille api). ──
    {"name": "Fibre Arcep — Ma connexion internet (immeuble)", "methode": "api",
     "url": "https://www.data.gouv.fr/api/1/datasets/ma-connexion-internet/",
     "selecteur": "last_update"},
    {"name": "Taux de taxe foncière — fichier REI (DGFiP)", "methode": "api",
     "url": "https://www.data.gouv.fr/api/1/datasets/impots-locaux-fichier-de-recensement-des-elements-dimposition-a-la-fiscalite-directe-locale-rei-4/",
     "selecteur": "last_update"},
    {"name": "ACV / PVD / ORT (DGALN — liste des communes)", "methode": "api",
     "url": "https://www.data.gouv.fr/api/1/datasets/liste-des-communes-couvertes-par-des-operations-de-revitalisation-de-territoire/",
     "selecteur": "last_update"},
    # OLL : le JSON api/1 du jeu (520 ressources) dépasse la coupe de lecture de la sonde
    # (« réponse non-JSON » mesuré) → api/2, payload léger (3,9 ko), même last_update.
    {"name": "Loyers OLL — ADIL Réunion / AGORAH (réseau des observatoires)", "methode": "api",
     "url": "https://www.data.gouv.fr/api/2/datasets/56fd90e8c751df174ac485cb/",
     "selecteur": "last_update"},
    # SOURCES-3 lot 3 — repointée sur l'édition 2025 (le millésime servi ; sondé 2026-09-14,
    # last_update 2025-12-11). L'édition 2024 renvoyait explicitement vers la 2025 (ANIL).
    {"name": "Loyers DHUP — carte des loyers (annonces)", "methode": "api",
     "url": "https://www.data.gouv.fr/api/1/datasets/carte-des-loyers-indicateurs-de-loyers-dannonce-par-commune-en-2025/",
     "selecteur": "last_update"},
    # ── SOURCES-1 lot 6 — le foncier et les gens ──
    {"name": "DFI — documents de filiation informatisés (DGFiP)", "methode": "api",
     "url": "https://www.data.gouv.fr/api/1/datasets/agregation-des-fichiers-de-documents-de-filiation-informatises-dfi-des-parcelles/",
     "selecteur": "last_update"},
    # INSEE : les bases IRIS ne sont pas sur data.gouv — la page du sommaire insee.fr porte le
    # millésime (« Logement en 2022 ») : un nouveau millésime publie une nouvelle page-titre.
    {"name": "INSEE RP2022 — bases IRIS (logement, population)", "methode": "page",
     "url": "https://www.insee.fr/fr/statistiques/8647012",
     "selecteur": r"Logement en (20\d{2})"},
    # CRON-1 lot 1 — SRU (DHUP) SORT des rappels : le jeu data.gouv « communes-et-inventaire-sru » porte
    # un `last_update` (appelé pour de vrai le 18/09 : HTTP 200, last_update 2026-08-11). Le CSV a une URL
    # datée (donc instable), mais l'API du DATASET donne, elle, une date stable et lisible → vraie sonde.
    {"name": "Inventaire SRU (DHUP)", "methode": "api",
     "url": "https://www.data.gouv.fr/api/1/datasets/communes-et-inventaire-sru/", "selecteur": "last_update"},
]

#: SENTINELLE-2 (X3.3) — les sources NON surveillées gardent un état EXPLICITE au panneau admin
#: (« non surveillée » + raison en infobulle), jamais un blanc ni une fausse erreur. Raison par nom
#: EXACT ; défaut générique sinon. Ce que chaque famille a coûté est détaillé dans SENTINELLE-INVENTAIRE.md.
#: SENTINELLE-3 (Y5.3) — chaque raison DIT ce qui a été essayé au second passage (2026-09-01, appels
#: réels). Les 6 sources récupérées (DEAL PPR/WMS, Région ODS, Géorisques cavités/mvt/ssp) sont passées
#: au SEED et retirées d'ici.
RAISONS_NON_SURVEILLEES: dict[str, str] = {
    # GEOPF-3 — couches RASTER servies en WMTS (overlay/fond) : millésime figé (carte 1950/1980) ou
    # zonage réglementaire sans en-tête de version machine amont ; aucun flux vecteur ni date à sonder.
    "Contraintes EnR près des habitations (Géoplateforme)": "Couche RASTER WMTS (ENR.PERIMETRE.HABITATION) — zonage réglementaire APER servi en tuiles image, sans millésime machine amont à sonder ; re-contrôlé à la demande.",
    "SCAN 50 historique 1950 (IGN)": "Carte historique FIGÉE (SCAN 50 de 1950) servie en WMTS image — millésime immuable (document d'archive), aucun flux amont à surveiller.",
    "EduGéo Réunion 1980 (IGN)": "Carte historique FIGÉE (EduGéo Réunion 1980) servie en WMTS image — millésime immuable, aucun flux amont à surveiller.",
    # COUCHES-REGISTRE-2 lot 1 — le seed des contours communaux est un référentiel STATIQUE embarqué
    # (fichier communes974.geojson d'IGN ADMIN EXPRESS, matérialisé en mvt_communes) : aucun flux ni
    # millésime machine amont à sonder. Contours administratifs quasi immuables (fusions rarissimes).
    "Communes La Réunion — contours (IGN ADMIN EXPRESS via geo.api.gouv, seed)": "Seed statique embarqué (contours des 24 communes, IGN ADMIN EXPRESS via geo.api.gouv) — aucun flux amont à surveiller ; découpage administratif quasi immuable.",
    # SOURCES-3b lot 2 — 17 sources sorties d'ici : une sentinelle producteur RÉELLE a été
    # trouvée et probée (SEED) — elles ne sont plus « non surveillées ». Le reste garde sa raison.
    "GPU — zonages d'assainissement (info-surf typeinf 19)": "Doublon du GPU assainissement (canal info-surf) — même amont, non re-surveillé.",
    # SOURCES-3b lot 2 — chantier SOURCES-2 jamais classé : WMS IMAGE seule (couche courbes de niveau
    # refusée en WFS, vérifié 13/09), aucun vecteur ni date amont à sonder ; demande de vecteur DEAL en cours.
    "Carte hypsométrique du littoral (DEAL Lizmap)": "CHANTIER (SOURCES-2 lot 3) — le producteur ne sert la carte hypsométrique qu'en WMS image (couche des courbes de niveau REFUSÉE en WFS) ; aucun vecteur ni millésime machine à sonder. Vecteur demandé à la DEAL (courrier lot 5). La submersion est servie à la place par l'aléa PPRL vecteur.",
    "DEAL — cartes de bruit stratégiques (CBS)": "WFS Carmen sans en-tête de version (même service que les couches DEAL lot 2, vérifié 07/09/2026) ; CBS = échéance quinquennale (directive 2002/49/CE) — réingéré à la demande (`labuse ingest-bruit-cartes`), fraîcheur au Circuit.",
    "ZPPA — zones de présomption de prescription archéologique (Atlas des patrimoines)": "Atlas des patrimoines INJOIGNABLE au test du 06/09/2026 (timeout) et aucun jeu national/974 sur data.gouv ; page DAC de La Réunion sans millésime exploitable — rappel périodique posé (RAPPELS_MANUELS) pour re-tester l'Atlas.",
    "Coût de construction (EPTB SDES + choix LABUSE)": "L'EPTB est une PUBLICATION annuelle (pages DREAL/SDES sans millésime machine exploitable — vérifié 07/09/2026) ; rappel annuel de relecture posé (RAPPELS_MANUELS), la table cout_construction_ref est mise à jour à la main après lecture.",
    "SAR — schéma d'aménagement régional (Région/DEAL)": "Couche SIG officielle NON diffusée (Carmen 29, Lizmap DEAL, Sextant — WMS image seule —, ODS Région : 0 vecteur au 07/09/2026) ; demandée à la Région (lot 7). Rappel périodique 180 j (RAPPELS_MANUELS) : re-chercher la couche + suivre la révision SAR 2050.",
    "DVF Réunion (Région, data.regionreunion.com)": "Jeu FIGÉ chez le producteur (2014→mi-2021, vérifié 07/09/2026) servant d'échantillon producteur du filtre DVF — le hub ODS Région est déjà surveillé par la sonde témoin de son catalogue (total_count) ; une republication du jeu s'y verrait.",
    "Zonages d'assainissement SIG complets (EPCI / régies)": "CHANTIER — en attente de la remise par les 5 EPCI/régies (aucun flux à sonder) ; la demande formelle est prête (DEMANDE-REGION-EPCI.md). Le canal GPU existant (4/24) garde sa propre surveillance.",
    "Inventaires ZAE (EPCI — loi Climat et résilience)": "CHANTIER — en attente de la remise par les 5 EPCI (publication non centralisée, aucun flux à sonder) ; demande prête (DEMANDE-REGION-EPCI.md).",
    "Périmètres de ZAC (EPCI / communes / EPF Réunion)": "CHANTIER — en attente de la remise (pas d'open data 974 fiable, jeu CNIG ZAC sans le 974 — rapport fiche 17) ; demande prête (DEMANDE-REGION-EPCI.md).",
    "OPAH / PIG (Anah / EPCI)": "CHANTIER — en attente des conventions EPCI/Anah (la carto Anah localise sans polygone, aucun flux à sonder) ; demande prête (DEMANDE-REGION-EPCI.md).",
    "Périmètres ORT infra-communaux (EPCI)": "CHANTIER — en attente des annexes de conventions ORT (EPCI) ; l'éligibilité COMMUNALE est servie et surveillée par la sonde anct_ort (lot 5) ; demande prête (DEMANDE-REGION-EPCI.md).",
    "ENS du Département (Conseil départemental)": "CHANTIER — en attente de la remise par le Conseil départemental (non diffusés en open data, aucun flux à sonder) ; demande prête (DEMANDE-REGION-EPCI.md).",
    "Micro-données OLL (ADIL / AGORAH)": "CHANTIER — micro-données conventionnées (jamais en flux ouvert) ; les agrégats par zone sont servis et surveillés (loyers_oll, lot 5) ; demande prête (DEMANDE-REGION-EPCI.md).",
    "LOVAC (logements vacants)": "SOUS CONVENTION — détail réservé aux collectivités et à leurs prestataires (fiche 19) ; rien à sonder sans accès. Relecture à la convention ; en attendant, la vacance INSEE RP par IRIS est servie (lot 6).",
    "DV3F (Cerema)": "SOUS CONVENTION — même demande que les Fichiers fonciers (une convention pour les trois) ; rien à sonder sans accès. En attendant : DVF ouvert + échantillon producteur Région (lot 4).",
    "INPI RNE (dirigeants)": "API AUTHENTIFIÉE par SIREN (aucun millésime public à sonder) — FRAICHEUR-FIX-1 : ingérée par le poste mensuel `ingest-inpi-rne` et surveillée par un RAPPEL de cadence (fraîcheur réelle de pm_dirigeants), plus par le contrôle de nuit.",
    "OpenStreetMap / Overpass": "Y3 : témoin de comptage testé (Overpass `out count`) → stable localement mais OSM est un flux continu (planet) et LABUSE l'interroge EN DIRECT (aucun snapshot ingéré) ; un compte sur zone stable ne représente pas l'île et n'est pas actionnable.",
    # FRAICHEUR-FIX-1 (point 5) — les 3 couches OSM : sonde live Overpass RETIRÉE (aucun endpoint fiable
    # depuis le VPS : overpass-api.de en 502 persistant, miroirs non résolus, osm.ch sans le planet 974).
    # Surveillance par RAPPEL de fraîcheur du snapshot ingéré (RAPPELS_MANUELS, cadence 180 j).
    "Parkings OSM (loi APER)": "FRAICHEUR-FIX-1 : Overpass injoignable de façon fiable depuis le VPS (502 persistant / miroirs HS) — sonde live retirée, remplacée par un rappel de fraîcheur sur le snapshot ingéré (cadence 180 j).",
    "OSM — transport (pôles d'échange & téléphérique)": "FRAICHEUR-FIX-1 : idem parkings OSM — sonde live Overpass retirée, rappel de fraîcheur sur le snapshot (180 j).",
    "TCSP — voies bus en site propre (OSM)": "FRAICHEUR-FIX-1 : idem parkings OSM — sonde live Overpass retirée, rappel de fraîcheur sur le snapshot (180 j).",
    "INPN / patrinat — espaces protégés": "Couches patrinat servies en WFS Géoplateforme ; pas de jeu data.gouv national « espaces protégés » à millésime trouvé, ni de requête témoin à agrégat stable.",
    "PEIGEO (hub régional)": "Y2 : peigeo.re répond désormais (200) mais c'est un site WordPress — plus de GeoNetwork/CSW ni d'API de catalogue à sonder (les chemins /geonetwork renvoient 404). Pas un jeu unique.",
    "DEAL Réunion (WMS/WFS)": "Y1 : hôte carto DEAL (deal974.lizmap.com) de nouveau joignable mais sans URL amont datée ; le seul jeu data.gouv « NPNRU » est DÉPARTEMENTAL (Bouches-du-Rhône), pas Réunion → inscrire son `last_update` serait une fausse veille. La couche QP génération 2024 servie ici est, elle, déjà couverte par « QPV 2024 (ANCT) ».",
    "Géoplateforme IGN": "Y2 : GetCapabilities WFS `data.geopf.fr` répond (200) mais SANS attribut `updateSequence` ni date, et le catalogue n'est pas exposé en JSON. Hub — les produits IGN servis sont surveillés individuellement (data.gouv `last_update`).",
    "ZFANG — zone franche d'activité nouvelle génération (Légifrance)": "Y1 : 0 jeu data.gouv (ZFANG/zone franche outre-mer) ; la page JORF n'a ni ETag ni Last-Modified (Cache-Control no-store → `entete` illisible) et son HTML n'est pas déterministe (jetons dynamiques) → `page` non fiable ; un texte modifié reçoit un nouvel identifiant JORFTEXT.",
    "FRR ex-ZRR — zone spéciale d'action rurale (Légifrance)": "Y1 : les jeux data.gouv « FRR » trouvés sont DÉPARTEMENTAUX (Charente, Corrèze, Nièvre), aucun national ni Réunion ; la page JORF n'a ni ETag ni Last-Modified et son HTML n'est pas déterministe → ni `entete` ni `page` fiable.",
    "Radar (pige d'annonces)": "Collecte 100 % humaine — non surveillable par nature (aucun amont public). Y4 : rappel de rafraîchissement posé (cadence attendue).",
    "VRD / assainissement (SPANC)": "Champ manuel EPCI — aucune donnée ouverte fine, pas d'URL amont. Y4 : rappel de rafraîchissement posé.",
    "Fichiers fonciers (Cerema)": "Sous convention, non ingérée en libre — aucune URL amont publique. Y4 : rappel de rafraîchissement posé (échéance de convention à porter si connue).",
    "MOBPRO (mobilités domicile-travail, INSEE)": "Import CSV manuel ABANDONNÉ pour l'étude de zone — pas d'URL de version stable, et pas de rafraîchissement attendu (aucun rappel Y4).",
    "Office de l'eau Réunion — Chroniques de l'eau": "Seed CSV extrait à la main d'un PDF (chronique numérotée) — chaque édition = nouvelle URL, non surveillable proprement. Y4 : rappel de rafraîchissement posé.",
    "PVGIS (Commission européenne)": "API de CALCUL (v5.3 dans l'URL) — pas de jeu à millésime, le service ne versionne pas de données à comparer ; aucune requête témoin actionnable (réponse dérivée d'un modèle, pas d'une donnée ingérée).",
    # TESTS-1 + SOURCES-3b (14/09, convergents) — Annuaire DILA, Sudocuh, RNIC, RPLS et Consommation
    # NAF (Cerema) sorties d'ici : sous sonde RÉELLE (SEED SOURCES-3b) désormais ; une source ne peut
    # pas être à la fois surveillée et déclarée non surveillable (test_sentinelle).
    "INSEE RP Logement 2023": "Millésime ANNUEL du recensement (publication INSEE sans endpoint de version stable pour les tableaux communaux) — rappel par cadence, le millésime suivant s'ingère à la main (RP 2024 attendu fin 2026).",
    # COHERENCE-FIX-1 lot E — populations légales en vigueur : geo.api.gouv renvoie la valeur courante
    # SANS en-tête de version machine à comparer ; l'INSEE actualise les populations légales une fois
    # l'an (en vigueur au 1er janvier). Même traitement que « INSEE RP Logement 2023 » : millésime
    # annuel re-ingéré par `labuse population-legale-sync`, pas de fausse veille amont.
    "Population légale (INSEE via geo.api.gouv)": "Populations légales INSEE en vigueur (geo.api.gouv) — millésime ANNUEL (en vigueur au 1er janvier), sans en-tête de version machine amont à sonder ; re-ingérées à la demande (`labuse population-legale-sync`), fraîcheur au Circuit.",
    "NPNRU (DEAL Réunion / ANCT)": "Liste ANCT FIGÉE (génération 2024) — pas de flux de version ; les quartiers NPNRU ne changent qu'à une nouvelle génération (geste manuel).",
    "PLH des 5 EPCI (extraction documentaire)": "Extraction DOCUMENTAIRE manuelle (dépôt) — la version vit dans les documents des EPCI, pas dans un flux ; rappel par cadence.",
    "RTAA DOM (textes réglementaires)": "Règles portées par le code (config/rtaa_dom.yaml), vérifiées sur Légifrance À LA MAIN aux versions consolidées « en vigueur » — pas d'API de version Légifrance exploitable pour ces articles.",
}

#: SENTINELLE-3 (Y4) — les sources MANUELLES (alimentées par Vic, aucun amont public) reçoivent un RAPPEL
#: de rafraîchissement : au-delà de `cadence_jours` sans nouvelle ingestion (data_sources.last_sync_at),
#: le panneau/le job signale « donnée manuelle non rafraîchie depuis N jours » (une fois par dépassement).
#: Ce n'est PAS une sonde amont (methode='rappel', jamais interrogée). `convention_echeance` (date ISO) si
#: connue — jamais inventée (Fichiers fonciers : la date de convention n'est pas connue ici → None). MOBPRO
#: est exclu (abandonné, aucun rafraîchissement attendu).
RAPPELS_MANUELS: list[dict] = [
    # FRAICHEUR-FIX-1 (point 3) — INPI RNE dirigeants : flux quotidien AUTHENTIFIÉ (pas de millésime
    # public à sonder), désormais ingéré par le poste MENSUEL `ingest-inpi-rne`. La SENTINELLE est un
    # rappel de cadence (40 j = mensuel + marge) sur la fraîcheur RÉELLE (data_sources.last_sync_at posé
    # par le job depuis max(ingested_at)) : si le rafraîchissement décroche, le panneau/le contrôle de
    # nuit le signalent — fin du « ni job ni sentinelle » (FRAICHEUR-1 §3.3).
    {"name": "INPI RNE (dirigeants)", "cadence_jours": 40, "convention_echeance": None},
    # FRAICHEUR-FIX-1 (point 5) — les 3 couches OSM : sonde live Overpass retirée (aucun endpoint fiable
    # depuis le VPS, cf. SEED). Surveillance = RAPPEL de fraîcheur sur le snapshot ingéré (transport/
    # stationnement = couches LENTES → cadence 180 j ; un snapshot plus vieux ⇒ « à rafraîchir »).
    {"name": "Parkings OSM (loi APER)", "cadence_jours": 180, "convention_echeance": None},
    {"name": "OSM — transport (pôles d'échange & téléphérique)", "cadence_jours": 180, "convention_echeance": None},
    {"name": "TCSP — voies bus en site propre (OSM)", "cadence_jours": 180, "convention_echeance": None},
    {"name": "Radar (pige d'annonces)", "cadence_jours": 7, "convention_echeance": None},
    # SILENCE-1 (point 7) — rappel TRIMESTRIEL (une manuelle en attente de fichier : gentil rappel, pas d'alerte).
    {"name": "VRD / assainissement (SPANC)", "cadence_jours": 91, "convention_echeance": None},
    {"name": "Fichiers fonciers (Cerema)", "cadence_jours": 365, "convention_echeance": None},
    {"name": "Office de l'eau Réunion — Chroniques de l'eau", "cadence_jours": 365, "convention_echeance": None},
    # SOURCES-1 lot 1 — re-tester l'Atlas des patrimoines (ZPPA 974) : injoignable au 06/09/2026.
    {"name": "ZPPA — zones de présomption de prescription archéologique (Atlas des patrimoines)",
     "cadence_jours": 180, "convention_echeance": None},
    # SOURCES-1 lot 4 — SAR : re-chercher la couche SIG officielle (demandée à la Région) et
    # suivre la révision SAR 2050 (engagée — fiche 3 du rapport ; page DEAL sans millésime
    # exploitable pour une sonde page, vérifié 07/09/2026).
    {"name": "SAR — schéma d'aménagement régional (Région/DEAL)",
     "cadence_jours": 180, "convention_echeance": None},
    # SOURCES-1 lot 5 — coût de construction : l'EPTB est une PUBLICATION annuelle (pages
    # DREAL/SDES sans millésime machine exploitable) → rappel annuel de relecture.
    {"name": "Coût de construction (EPTB SDES + choix LABUSE)",
     "cadence_jours": 365, "convention_echeance": None},
    # SOURCES-3b lot 2 — sources one_shot/manuelles ingérées SANS producteur sondable (URL de
    # version absente, texte légal figé, liste ANCT figée, API de calcul) : leur fraîcheur se suit
    # par cadence de relecture (rappel Y4), jamais par une fausse veille. Elles gardent leur raison
    # écrite (RAISONS_NON_SURVEILLEES / notes) — le rappel dit « ingérée le X, re-contrôle attendu ».
    {"name": "NPNRU (DEAL Réunion / ANCT)", "cadence_jours": 365, "convention_echeance": None},
    {"name": "INSEE RP Logement 2023", "cadence_jours": 365, "convention_echeance": None},
    {"name": "PLH des 5 EPCI (extraction documentaire)", "cadence_jours": 365, "convention_echeance": None},
    {"name": "RTAA DOM (textes réglementaires)", "cadence_jours": 365, "convention_echeance": None},
    {"name": "PVGIS (Commission européenne)", "cadence_jours": 365, "convention_echeance": None},
]


def nature(methode: str | None) -> str:
    """Y5.4 — la NATURE de surveillance, pour la distinguer VISUELLEMENT au panneau admin :
      · `version`         — version détectable (api / page) ;
      · `changement`      — changement détectable sans version nommée (entete / temoin) ;
      · `rappel`          — rappel de rafraîchissement d'une source manuelle (Y4) ;
      · `non_surveillable`— aucune sonde (état normal, raison précise en infobulle)."""
    if methode in ("api", "page"):
        return "version"
    if methode in ("entete", "temoin"):
        return "changement"
    if methode == "rappel":
        return "rappel"
    return "non_surveillable"


def raison_non_surveillee(name: str) -> str:
    """X3.3 — raison affichable pour une source non surveillée (infobulle admin). Défaut honnête si le
    nom n'est pas au dictionnaire (ne jamais laisser un blanc)."""
    return RAISONS_NON_SURVEILLEES.get(
        name, "Pas d'URL amont à millésime stable identifiée (endpoint de requête, import manuel ou hub).")


def ensemencer(db) -> int:
    """W5 — peuple `source_veille` depuis SEED, en rattachant chaque entrée à `data_sources` par nom
    EXACT. IDEMPOTENT et non destructif : rafraîchit url/methode/selecteur d'une ligne existante mais
    NE TOUCHE JAMAIS `actif` (une source désactivée par Vic le reste). Une entrée sans source en base
    est ignorée (pas de ligne orpheline). Retourne le nombre de lignes créées."""
    crees = 0
    for e in SEED:
        sid = db.execute(text("SELECT id FROM data_sources WHERE name = :n"), {"n": e["name"]}).scalar()
        if not sid:
            continue
        existe = db.execute(text("SELECT 1 FROM source_veille WHERE source_id = :s"), {"s": sid}).scalar()
        if existe:
            db.execute(text("UPDATE source_veille SET url_version = :u, url_temoin_2 = :u2, methode = :m,"
                            " selecteur = :sel, updated_at = now() WHERE source_id = :s"),
                       {"u": e["url"], "u2": e.get("url2"), "m": e["methode"],
                        "sel": e.get("selecteur"), "s": sid})
        else:
            db.execute(text("INSERT INTO source_veille (source_id, url_version, url_temoin_2, methode, selecteur,"
                            " cadence_heures, actif) VALUES (:s, :u, :u2, :m, :sel, 24, true)"),
                       {"s": sid, "u": e["url"], "u2": e.get("url2"), "m": e["methode"],
                        "sel": e.get("selecteur")})
            crees += 1
    return crees


def ensemencer_rappels(db) -> int:
    """Y4 — pose (non destructivement) une ligne de RAPPEL (methode='rappel', AUCUNE sonde amont) sur les
    sources manuelles à fraîcheur attendue : `cadence_attendue_jours` (+ `convention_echeance` si connue).
    Une ligne 'rappel' n'est JAMAIS interrogée (cf. `_lignes_a_sonder`) — c'est un rappel de
    rafraîchissement, pas une surveillance. IDEMPOTENT, préserve `actif`. Rattachement par nom EXACT ;
    une entrée sans source en base est ignorée (pas de ligne orpheline). Retourne le nombre créé."""
    crees = 0
    for e in RAPPELS_MANUELS:
        sid = db.execute(text("SELECT id FROM data_sources WHERE name = :n"), {"n": e["name"]}).scalar()
        if not sid:
            continue
        existe = db.execute(text("SELECT 1 FROM source_veille WHERE source_id = :s"), {"s": sid}).scalar()
        if existe:
            db.execute(text("UPDATE source_veille SET methode = 'rappel', cadence_attendue_jours = :c,"
                            " convention_echeance = :ce, updated_at = now() WHERE source_id = :s"),
                       {"c": e["cadence_jours"], "ce": e.get("convention_echeance"), "s": sid})
        else:
            db.execute(text("INSERT INTO source_veille (source_id, methode, cadence_attendue_jours,"
                            " convention_echeance, cadence_heures, actif)"
                            " VALUES (:s, 'rappel', :c, :ce, 24, true)"),
                       {"s": sid, "c": e["cadence_jours"], "ce": e.get("convention_echeance")})
            crees += 1
    return crees


# ─────────────────────────────── Y4 · le rappel des sources manuelles ───────────────────────────────

def passer_rappels(db, *, source_ids=None, notifier: bool = True) -> dict:
    """Y4 — le RAPPEL de rafraîchissement des sources MANUELLES (ce n'est PAS une sonde amont : aucun
    appel réseau). Pour chaque ligne 'rappel' active, compare l'âge de la dernière ingestion
    (`data_sources.last_sync_at`) à `cadence_attendue_jours` ; au-delà, dépose UN rappel admin « donnée
    manuelle non rafraîchie depuis N jours » — UNE SEULE FOIS par dépassement (dédup sur la date de
    dernière ingestion : un rafraîchissement rouvre un épisode neuf). Porte l'échéance de convention si
    connue. N'écrit RIEN dans data_sources, n'ingère rien. Retourne {rappels, retards, notifs}."""
    where = ["v.methode = 'rappel'", "v.actif = true", "v.cadence_attendue_jours IS NOT NULL"]
    params: dict = {}
    if source_ids:
        where.append("v.source_id = ANY(:ids)")
        params["ids"] = list(source_ids)
    rows = [dict(r) for r in db.execute(text(
        "SELECT v.source_id, v.cadence_attendue_jours AS cad, v.convention_echeance AS echeance,"
        "       d.name AS nom, d.last_sync_at AS lsa"
        " FROM source_veille v JOIN data_sources d ON d.id = v.source_id"
        " WHERE " + " AND ".join(where)), params).mappings()]
    recap = {"rappels": 0, "retards": 0, "notifs": 0}
    now = datetime.now(tz=timezone.utc)
    for r in rows:
        recap["rappels"] += 1
        lsa = r["lsa"]
        if lsa is None:            # aucune date d'ingestion → rien à mesurer (honnête, pas de faux rappel)
            continue
        jours = (now - lsa).days
        if jours <= r["cad"]:
            continue
        recap["retards"] += 1
        if notifier and _emettre_rappel(db, r["nom"], jours, r["cad"], r.get("echeance"), lsa):
            recap["notifs"] += 1
    return recap


def _emettre_rappel(db, nom: str, jours: int, cadence: int, echeance, lsa) -> bool:
    """Y4 — dépose UN rappel admin (feed systeme, permanent) pour une donnée manuelle en retard. Dédup sur
    (source, date de dernière ingestion) : une seule cloche par dépassement ; un rafraîchissement (nouveau
    last_sync_at) rouvre un épisode. Ce n'est PAS une alerte « amont » : c'est un rappel de saisie."""
    from .api.events import creer_notification
    detail = (f"« {nom} » est une donnée saisie à la main (aucun amont public à surveiller). Cadence de "
              f"rafraîchissement attendue : {cadence} j — dernière ingestion il y a {jours} j. À rafraîchir. "
              f"La sentinelle ne sonde PAS cette source : ceci est un rappel, pas une alerte amont.")
    if echeance:
        detail += f" Échéance de convention : {echeance}."
    return bool(creer_notification(
        db, kind="systeme", compte_id=None, source="Veille sources",
        titre=f"Donnée manuelle non rafraîchie : {nom} (depuis {jours} j)",
        detail=detail, lien="/sources",
        dedup=f"sentinelle-rappel:{nom}:{lsa:%Y-%m-%d}", permanent=True))


def _ligne_neuf(row: dict, s: Sonde) -> str:
    """Une ligne du détail du digest pour une NOUVELLE version (formulation SENTINELLE-1 conservée)."""
    nom, servi, vu = row["source_nom"], row.get("servi"), (s.vu or "?")
    if row.get("methode") in ("entete", "temoin"):   # pas de millésime lisible : « la donnée a changé »
        return f"• {nom} : la donnée amont a changé — à vérifier."
    return f"• {nom} : {vu} est publié" + (f" — vous servez {servi}." if servi else ".")


def _emettre_digest(db, neuf: list[dict], echec: list[dict]) -> bool:
    """X5.1 — dépose UN SEUL résumé quotidien en cloche admin (feed systeme, compte_id NULL) agrégeant
    toutes les sources qui ont du nouveau (nouvelles versions) et toutes les sondes qui viennent
    d'atteindre 3 échecs consécutifs. Dédup PERMANENTE sur le contenu (les sources annoncées) → un rejeu
    du même passage n'empile rien ; `dernier_notifie_vu` empêche déjà de ré-annoncer un millésime connu.
    Formulation dépliable : titre = compte, detail = liste à puces. Retourne True si une notif est créée."""
    from .api.events import creer_notification
    n_neuf, n_echec = len(neuf), len(echec)
    parts_titre = []
    if n_neuf:
        parts_titre.append("1 source a une nouvelle version" if n_neuf == 1
                           else f"{n_neuf} sources ont une nouvelle version")
    if n_echec:
        parts_titre.append("1 sonde échoue depuis 3 passages" if n_echec == 1
                           else f"{n_echec} sondes échouent depuis 3 passages")
    titre = " · ".join(parts_titre)
    lignes = [_ligne_neuf(d["row"], d["sonde"]) for d in neuf]
    if n_echec:
        lignes.append("Sondes en échec persistant (la sentinelle a échoué, PAS la donnée) :")
        lignes += [f"• {d['row']['source_nom']} : {d['sonde'].message or d['sonde'].statut}" for d in echec]
    if n_neuf:
        lignes.append("Geste supervisé : ouvrez la page Sources et cliquez « Injecter cette version » sur "
                      "la source voulue — rien n'entre sans ce clic (la sentinelle n'ingère jamais).")
    # clé de dédup = l'ensemble ANNONCÉ (sids neufs + sids en échec) → stable, un même passage ne double pas.
    sig = "n:" + ",".join(str(d["row"]["source_id"]) + ":" + str(d["sonde"].vu) for d in neuf) \
        + "|e:" + ",".join(str(d["row"]["source_id"]) for d in echec)
    # TESTS-1 lot 1 — BORNER la clé : event_log.dedup est varchar(96) ; avec beaucoup de sondes en
    # échec persistant (mesuré : 88 → ~350 caractères) l'INSERT plantait en StringDataRightTruncation
    # et le passage de veille CRASHAIT — précisément la nuit où tout va mal. Au-delà de la place
    # disponible, la signature est remplacée par son empreinte sha1 (même stabilité, taille fixe).
    if len("sentinelle-digest:" + sig) > 96:
        import hashlib
        sig = "sha1:" + hashlib.sha1(sig.encode(), usedforsecurity=False).hexdigest()
    cree = bool(creer_notification(
        db, kind="systeme", compte_id=None, source="Veille sources",
        titre=titre, detail="\n".join(lignes), lien="/sources",
        dedup="sentinelle-digest:" + sig, permanent=True))
    # SUITE-1 S4.1 — alerte mail OPTIONNELLE, seulement pour les sources dont la veille porte le drapeau
    # `mail_alerte` (défaut off). Une seule notif in-app agrégée (ci-dessus) ; le mail ne part que si la
    # notif est neuve (pas de rejeu) ET qu'au moins une source annoncée est abonnée au mail.
    if cree:
        _alerter_mail(neuf)
    return cree


def _alerter_mail(neuf: list[dict]) -> None:
    """S4.1 — envoie UN mail (façade `mail.py` unique) listant les sources abonnées (`mail_alerte`)
    dont l'amont vient de changer. Non bloquant ; silencieux si aucune source abonnée ou pas de
    destinataire configuré (l'alerte in-app reste, elle, toujours déposée)."""
    abonnees = [d for d in neuf if d["row"].get("mail_alerte")]
    if not abonnees:
        return
    from .config import get_settings
    from .mail import send_email_async
    dest = get_settings().admin_email or get_settings().contact_email
    if not dest:
        return
    corps = ("La veille des sources a détecté une nouvelle version amont sur des sources que vous "
             "suivez par mail :\n\n"
             + "\n".join(f"• {d['row']['source_nom']} — {d['sonde'].message or 'nouvelle version'}"
                         for d in abonnees)
             + "\n\nRien n'est ingéré automatiquement : ouvrez la page Données › Catalogue et cliquez "
               "« Injecter » sur la source voulue.")
    send_email_async(dest, "[LABUSE] veille sources — nouvelle version amont", corps)


# ─────────────────────────────── Y5.2 · l'inventaire RÉGÉNÉRÉ depuis le catalogue ───────────────────────────────
#: Doublons amont : la veille de la canonique vaut pour les deux (une seule sonde).
DOUBLONS_COUVERTS: dict[str, str] = {
    "Cadastre Etalab (bulk DGFiP/Etalab)": "amont identique à « Cadastre (API Carto PCI) » (une seule veille, l'alerte vaut pour les deux)",
    "RGE ALTI 5 m (IGN)": "amont identique à « RGE ALTI (altimétrie) » (une seule veille, l'alerte vaut pour les deux)",
}

_LIB_METHODE = {"api": "`api`", "page": "`page`", "entete": "`entete`", "temoin": "`temoin`",
                "ortho": "`ortho`",   # VERIF-FIX-1 (Q3) — contrôle d'ortho plus récente (La Réunion)
                "dvf": "`dvf`"}       # FRAICHEUR-FIX-1 — ressources data.gouv full-AAAA-sN


def _famille(provider: str | None) -> str:
    """Regroupement fournisseur pour l'inventaire : on garde le premier segment du `provider` catalogue
    (avant «/» ou «—»), sinon « Autres »."""
    if not provider:
        return "Autres"
    return re.split(r"\s*[/—]\s*", provider.strip())[0] or "Autres"


def inventaire_markdown(millesimes: dict[str, str] | None = None) -> str:
    """Y5.2 — RÉGÉNÈRE l'inventaire des 64 sources DEPUIS LE CATALOGUE (`seed_sources.SOURCES`) croisé avec
    SEED / RAPPELS / RAISONS / DOUBLONS. Jamais écrit à la main : ce qui est ici EST l'état du code. Le
    millésime servi vient du catalogue (`source_millesime`), enrichi par `millesimes` (source→millésime
    servi lu en base) quand fourni. Retourne le Markdown complet."""
    from .ingestion.seed_sources import SOURCES
    millesimes = millesimes or {}
    seed_by = {e["name"]: e for e in SEED}
    rappel_by = {e["name"]: e for e in RAPPELS_MANUELS}

    def etat_veille(name: str) -> tuple[str, str, str]:
        """(nature_libellé, colonne_état, colonne_veille/raison) pour une source."""
        if name in seed_by:
            e = seed_by[name]
            nat = "version détectable" if e["methode"] in ("api", "page") else "changement détectable"
            veille = e["url"] + (f"  (sél. `{e['selecteur']}`)" if e.get("selecteur") else "")
            return nat, f"SURVEILLÉE · {_LIB_METHODE[e['methode']]}", veille
        if name in DOUBLONS_COUVERTS:
            return "doublon", "DOUBLON couvert", DOUBLONS_COUVERTS[name]
        if name in rappel_by:
            r = rappel_by[name]
            ech = f" · échéance convention {r['convention_echeance']}" if r.get("convention_echeance") else ""
            return ("rappel manuel", f"rappel manuel · cadence {r['cadence_jours']} j",
                    f"Rappel de rafraîchissement — cadence attendue {r['cadence_jours']} j{ech} (aucune "
                    f"sonde amont : source saisie à la main). {raison_non_surveillee(name)}")
        return "non surveillable", "non surveillée", raison_non_surveillee(name)

    # ventilations
    par_methode: dict[str, int] = {}
    for e in SEED:
        par_methode[e["methode"]] = par_methode.get(e["methode"], 0) + 1
    familles: dict[str, dict[str, int]] = {}
    for src in SOURCES:
        fam = _famille(src.get("provider"))
        d = familles.setdefault(fam, {"surv": 0, "rappel": 0, "non": 0, "doublon": 0})
        n = src["name"]
        if n in seed_by:
            d["surv"] += 1
        elif n in DOUBLONS_COUVERTS:
            d["doublon"] += 1
        elif n in rappel_by:
            d["rappel"] += 1
        else:
            d["non"] += 1

    n_surv, n_doub, n_rappel = len(seed_by), len(DOUBLONS_COUVERTS), len(rappel_by)
    n_total = len(SOURCES)
    n_non = n_total - n_surv - n_doub

    out: list[str] = []
    A = out.append
    A("# SENTINELLE-INVENTAIRE — les 64 sources, une par une (SENTINELLE-3)")
    A("")
    A("> **Fichier GÉNÉRÉ** — ne pas éditer à la main. Régénéré depuis le catalogue (`seed_sources.SOURCES`) "
      "croisé avec `sentinelle.SEED` / `RAPPELS_MANUELS` / `RAISONS_NON_SURVEILLEES` / `DOUBLONS_COUVERTS` "
      "par `labuse sentinelle-inventaire`. Ce qui est ici EST l'état du code.")
    A("")
    A("**Vérification réelle** : chaque URL de veille ci-dessous a été APPELÉE POUR DE VRAI (couche `_http` "
      "de production, UA `LABUSE-sentinelle/1.0`), sa réponse LUE, et la sonde a renvoyé **`ok`** — le "
      "2026-09-01. Aucune URL supposée. Une candidate qui échouait au semis n'est pas inscrite (elle figure "
      "en « non surveillée » avec ce qui a été essayé, cf. `RAISONS_NON_SURVEILLEES`).")
    A("")
    A(f"**Bilan** : **{n_surv} surveillées** · {n_rappel} rappels manuels (Y4) · {n_doub} doublons couverts "
      f"par leur canonique · {n_non} non surveillées = **{n_total}**.")
    A("")
    A("## Ventilation des surveillées par méthode")
    A("")
    A("| Méthode | N | Nature |")
    A("|---|---|---|")
    _nat_m = {"api": "version détectable", "page": "version détectable",
              "entete": "changement détectable", "temoin": "changement détectable (requête témoin)"}
    for m in ("api", "page", "entete", "temoin"):
        if par_methode.get(m):
            A(f"| `{m}` | {par_methode[m]} | {_nat_m[m]} |")
    A(f"| **Total** | **{n_surv}** | |")
    A("")
    A("## Ventilation par fournisseur")
    A("")
    A("| Fournisseur | Surveillées | Rappel manuel | Non surveillées | Doublons |")
    A("|---|---|---|---|---|")
    for fam in sorted(familles):
        d = familles[fam]
        A(f"| {fam} | {d['surv']} | {d['rappel']} | {d['non']} | {d['doublon']} |")
    A("")
    A("## Les quatre natures (Y5.4)")
    A("")
    A("- **version détectable** (`api`, `page`) — on lit un millésime comparable ; l'alerte le nomme.")
    A("- **changement détectable** (`entete`, `temoin`) — pas de version lisible ; l'alerte dit « la donnée "
      "amont a changé » (en-tête de fichier, ou empreinte d'une requête témoin figée).")
    A("- **rappel manuel** (Y4) — source saisie à la main, aucun amont ; rappel de rafraîchissement au-delà "
      "de la cadence attendue (ce n'est pas une sonde).")
    A("- **non surveillable** — aucune sonde possible ; la raison précise ce qui a été essayé.")
    A("")
    A("## Inventaire complet — par fournisseur")
    A("")
    for fam in sorted(familles):
        srcs = [s for s in SOURCES if _famille(s.get("provider")) == fam]
        A(f"### {fam}")
        A("")
        A("| Source | Millésime servi | État | Veille / raison |")
        A("|---|---|---|---|")
        for src in sorted(srcs, key=lambda s: s["name"].lower()):
            name = src["name"]
            _, col_etat, col_veille = etat_veille(name)
            mil = millesimes.get(name) or src.get("source_millesime") or "—"
            mil = str(mil).replace("|", "\\|").replace("\n", " ").strip()[:80]
            col_veille = str(col_veille).replace("|", "\\|").replace("\n", " ")
            A(f"| {name} | {mil} | {col_etat} | {col_veille} |")
        A("")
    return "\n".join(out).rstrip() + "\n"
