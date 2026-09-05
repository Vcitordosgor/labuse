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
import re
import time
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import text

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

def _http(url: str, *, methode_http: str = "GET") -> tuple[int, dict, str]:
    """Requête HTTP one-shot, timeout court, User-Agent LABUSE. Retourne (status, en-têtes, corps).
    Lève sur échec réseau (capté par l'appelant → `injoignable`). Aucun retry ici (doctrine W3.2)."""
    req = urllib.request.Request(url, method=methode_http, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:  # noqa: S310 — URL du catalogue, jamais client
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
        return Sonde("illisible", message="réponse non-JSON")
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
    val = entetes.get("etag") or entetes.get("last-modified")
    if not val:
        return Sonde("illisible", message="ni ETag ni Last-Modified sur l'en-tête amont")
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


def _lire_temoin(url: str, selecteur: str | None):
    """Lit UN témoin : (valeur extraite, None) si OK, sinon (None, Sonde d'échec). Facteur commun aux
    témoins mono- et bi-commune (S4.2)."""
    status, _, corps = _http(url)
    if status >= 400:
        return None, Sonde("injoignable", message=f"HTTP {status}")
    try:
        data = json.loads(corps)
    except ValueError:
        return None, Sonde("illisible", message="réponse non-JSON")
    val = _json_pointe(data, selecteur) if selecteur else data
    if val is None:
        return None, Sonde("illisible", message=f"chemin JSON introuvable : {selecteur}")
    return val, None


def sonder_temoin(url: str, selecteur: str | None, empreinte_prec: str | None,
                  url2: str | None = None) -> Sonde:
    """`temoin` (SENTINELLE-3 Y3) — requête TÉMOIN figée sur une API sans notion de version : on lit une
    EMPREINTE stable de la réponse (`selecteur` = chemin JSON vers un agrégat stable, ou None = réponse
    entière) et on la compare au dernier passage. Ne nomme AUCUNE version : signale « la donnée amont a
    changé ». Premier passage = baseline (ok, mémorise l'empreinte dans `dernier_entete`, marqueur opaque).

    SUITE-1 S4.2 — si `url2` (seconde commune témoin, Saint-Pierre) est fourni, l'empreinte combine les
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
            else:
                return Sonde("illisible", message=f"méthode inconnue : {methode}")
        except Exception as exc:  # noqa: BLE001 — tout échec réseau/parse = la SENTINELLE a échoué, pas la donnée
            return Sonde("injoignable", message=f"{type(exc).__name__}: {str(exc)[:200]}")
        # `entete`/`temoin` ont déjà tranché (marqueur opaque, aucune notion de « servi ») : on n'applique
        # la comparaison au millésime servi qu'aux méthodes À VERSION (api/page).
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
    where = ["v.actif = true", "v.methode IN ('api', 'page', 'entete', 'temoin')"]
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
    {"name": "BD ORTHO 20 cm (IGN)", "methode": "api",
     "url": "https://www.data.gouv.fr/api/1/datasets/bd-ortho-r/", "selecteur": "last_update"},
    {"name": "BD ORTHO IRC (IGN)", "methode": "api",       # dérivée IRC de la BD ORTHO → même jeu bd-ortho-r
     "url": "https://www.data.gouv.fr/api/1/datasets/bd-ortho-r/", "selecteur": "last_update"},
    {"name": "RGE ALTI (altimétrie)", "methode": "api",
     "url": "https://www.data.gouv.fr/api/1/datasets/rge-alti-r/", "selecteur": "last_update"},
    {"name": "IGN BD CARTO V5 — occupation du sol", "methode": "api",
     "url": "https://www.data.gouv.fr/api/1/datasets/bd-carto-r-1/", "selecteur": "last_update"},
    {"name": "LiDAR HD — MNH 50 cm (IGN)", "methode": "api",
     "url": "https://www.data.gouv.fr/api/1/datasets/mnh-lidar-hd/", "selecteur": "last_update"},
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
    # DVF — cas phare : on GARDE `page` (l'index géo-DVF liste les millésimes annuels, on garde le plus
    # récent, motif lisible « 2025 » comparable au servi ; supérieur à un last_update opaque). Reprise
    # de sentinelle-dvf-cadastre (moitié DVF).
    {"name": "DVF / valeurs foncières", "methode": "page",
     "url": "https://files.data.gouv.fr/geo-dvf/latest/csv/", "selecteur": r"20\d{2}"},
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
    {"name": "BODACC (procédures collectives)", "methode": "api",   # CORRIGE le chemin JSON de SENTINELLE-1
     "url": "https://bodacc-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/annonces-commerciales",
     "selecteur": "metas.default.modified"},
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
    # ── Cas isolés vérifiés ──
    # DPE ADEME — data-fair `dataUpdatedAt` (métadonnée documentée stable du dataset).
    {"name": "DPE ADEME (logements existants)", "methode": "api",
     "url": "https://data.ademe.fr/data-fair/api/v1/datasets/dpe03existant", "selecteur": "dataUpdatedAt"},
    # SITADEL — Dido (SDES) : métadonnée `last_update` du dataset national.
    {"name": "SITADEL (autorisations d'urbanisme)", "methode": "api",
     "url": "https://data.statistiques.developpement-durable.gouv.fr/dido/api/v1/datasets/6513f0189d7d312c80ec5b5b",
     "selecteur": "last_update"},
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
    # S4.2 — second chef-lieu témoin : Saint-Pierre (97410). Alerte si l'un des deux PPR change.
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
    # S4.2 — chacune sondée sur DEUX chef-lieux (Saint-Denis 97411 + Saint-Pierre 97410) : empreinte
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
]

#: SENTINELLE-2 (X3.3) — les sources NON surveillées gardent un état EXPLICITE au panneau admin
#: (« non surveillée » + raison en infobulle), jamais un blanc ni une fausse erreur. Raison par nom
#: EXACT ; défaut générique sinon. Ce que chaque famille a coûté est détaillé dans SENTINELLE-INVENTAIRE.md.
#: SENTINELLE-3 (Y5.3) — chaque raison DIT ce qui a été essayé au second passage (2026-09-01, appels
#: réels). Les 6 sources récupérées (DEAL PPR/WMS, Région ODS, Géorisques cavités/mvt/ssp) sont passées
#: au SEED et retirées d'ici.
RAISONS_NON_SURVEILLEES: dict[str, str] = {
    # API Carto GPU (Géoportail de l'urbanisme) — interrogée PAR GÉOMÉTRIE à l'usage, aucun millésime global.
    "Urbanisme PLU/GPU (API Carto)": "API Carto GPU interrogée par géométrie à l'usage. Y3 : le point d'entrée `/municipality` ne porte aucun millésime (gid/insee/is_rnu seulement), `/document` exige une géométrie, aucun jeu data.gouv « documents GPU » à `last_update` ; un témoin par parcelle détecterait un changement de PLU commune par commune, mais LABUSE interroge le GPU EN DIRECT (aucun snapshot ingéré à réinjecter).",
    "GPU — zonages d'assainissement": "API Carto GPU par géométrie (mêmes limites que « Urbanisme PLU/GPU » : pas de millésime global, interrogé en direct sans snapshot ingéré).",
    "GPU — zonages d'assainissement (info-surf typeinf 19)": "Doublon du GPU assainissement (canal info-surf) — même amont, non re-surveillé.",
    "SUP — assiettes GPU (API Carto)": "API Carto GPU (assiette-sup-s) par géométrie — pas de millésime global lisible ; interrogé en direct.",
    "Recherche d'entreprises (DINUM)": "Y3 : requête témoin `?departement=974` testée → `total_results` plafonné à 10000 (non exploitable) ; agrégat Sirene/RNE en direct, déjà couvert par la veille SIRENE (data.gouv).",
    "INPI RNE (dirigeants)": "API AUTHENTIFIÉE interrogée par SIREN (pas de requête témoin publique possible) — aucun millésime global à comparer.",
    "OpenStreetMap / Overpass": "Y3 : témoin de comptage testé (Overpass `out count`) → stable localement mais OSM est un flux continu (planet) et LABUSE l'interroge EN DIRECT (aucun snapshot ingéré) ; un compte sur zone stable ne représente pas l'île et n'est pas actionnable.",
    "Parkings OSM (loi APER)": "OSM en flux continu, interrogé en direct (cf. « OpenStreetMap / Overpass ») — témoin de comptage non représentatif ni actionnable.",
    "OSM — transport (pôles d'échange & téléphérique)": "OSM en flux continu, interrogé en direct (cf. « OpenStreetMap / Overpass ») — témoin de comptage non représentatif ni actionnable.",
    # RETOURS-13 R5 — même famille OSM (extraction Overpass à la demande, CLI `labuse tcsp`).
    "TCSP — voies bus en site propre (OSM)": "OSM en flux continu, interrogé en direct (cf. « OpenStreetMap / Overpass ») — témoin de comptage non représentatif ni actionnable.",
    "INPN / patrinat — espaces protégés": "Couches patrinat servies en WFS Géoplateforme ; pas de jeu data.gouv national « espaces protégés » à millésime trouvé, ni de requête témoin à agrégat stable.",
    # Portails / hubs
    "PEIGEO (hub régional)": "Y2 : peigeo.re répond désormais (200) mais c'est un site WordPress — plus de GeoNetwork/CSW ni d'API de catalogue à sonder (les chemins /geonetwork renvoient 404). Pas un jeu unique.",
    "DEAL Réunion (WMS/WFS)": "Y1 : hôte carto DEAL (deal974.lizmap.com) de nouveau joignable mais sans URL amont datée ; le seul jeu data.gouv « NPNRU » est DÉPARTEMENTAL (Bouches-du-Rhône), pas Réunion → inscrire son `last_update` serait une fausse veille. La couche QP génération 2024 servie ici est, elle, déjà couverte par « QPV 2024 (ANCT) ».",
    "50 pas géométriques — limite haute (DEAL)": "Y1 : WFS Lizmap DEAL de nouveau joignable mais sans projet/date lisible ; 0 jeu data.gouv (« 50 pas », « pas géométriques »). Limite domaniale dérivée du cadastre 1877 géoréférencé — donnée quasi statique, aucun millésime ni empreinte amont.",
    "Géoplateforme IGN": "Y2 : GetCapabilities WFS `data.geopf.fr` répond (200) mais SANS attribut `updateSequence` ni date, et le catalogue n'est pas exposé en JSON. Hub — les produits IGN servis sont surveillés individuellement (data.gouv `last_update`).",
    # Réglementaire Légifrance — pistes Y1.2 épuisées
    "ZFANG — zone franche d'activité nouvelle génération (Légifrance)": "Y1 : 0 jeu data.gouv (ZFANG/zone franche outre-mer) ; la page JORF n'a ni ETag ni Last-Modified (Cache-Control no-store → `entete` illisible) et son HTML n'est pas déterministe (jetons dynamiques) → `page` non fiable ; un texte modifié reçoit un nouvel identifiant JORFTEXT.",
    "FRR ex-ZRR — zone spéciale d'action rurale (Légifrance)": "Y1 : les jeux data.gouv « FRR » trouvés sont DÉPARTEMENTAUX (Charente, Corrèze, Nièvre), aucun national ni Réunion ; la page JORF n'a ni ETag ni Last-Modified et son HTML n'est pas déterministe → ni `entete` ni `page` fiable.",
    # Alimentées à la main — non surveillables PAR NATURE. Y4 : rappel de rafraîchissement (cadence_attendue_jours).
    "Radar (pige d'annonces)": "Collecte 100 % humaine — non surveillable par nature (aucun amont public). Y4 : rappel de rafraîchissement posé (cadence attendue).",
    "VRD / assainissement (SPANC)": "Champ manuel EPCI — aucune donnée ouverte fine, pas d'URL amont. Y4 : rappel de rafraîchissement posé.",
    "Fichiers fonciers (Cerema)": "Sous convention, non ingérée en libre — aucune URL amont publique. Y4 : rappel de rafraîchissement posé (échéance de convention à porter si connue).",
    "MOBPRO (mobilités domicile-travail, INSEE)": "Import CSV manuel ABANDONNÉ pour l'étude de zone — pas d'URL de version stable, et pas de rafraîchissement attendu (aucun rappel Y4).",
    "Office de l'eau Réunion — Chroniques de l'eau": "Seed CSV extrait à la main d'un PDF (chronique numérotée) — chaque édition = nouvelle URL, non surveillable proprement. Y4 : rappel de rafraîchissement posé.",
    # Autre
    "PVGIS (Commission européenne)": "API de CALCUL (v5.3 dans l'URL) — pas de jeu à millésime, le service ne versionne pas de données à comparer ; aucune requête témoin actionnable (réponse dérivée d'un modèle, pas d'une donnée ingérée).",
}

#: SENTINELLE-3 (Y4) — les sources MANUELLES (alimentées par Vic, aucun amont public) reçoivent un RAPPEL
#: de rafraîchissement : au-delà de `cadence_jours` sans nouvelle ingestion (data_sources.last_sync_at),
#: le panneau/le job signale « donnée manuelle non rafraîchie depuis N jours » (une fois par dépassement).
#: Ce n'est PAS une sonde amont (methode='rappel', jamais interrogée). `convention_echeance` (date ISO) si
#: connue — jamais inventée (Fichiers fonciers : la date de convention n'est pas connue ici → None). MOBPRO
#: est exclu (abandonné, aucun rafraîchissement attendu).
RAPPELS_MANUELS: list[dict] = [
    {"name": "Radar (pige d'annonces)", "cadence_jours": 7, "convention_echeance": None},
    {"name": "VRD / assainissement (SPANC)", "cadence_jours": 365, "convention_echeance": None},
    {"name": "Fichiers fonciers (Cerema)", "cadence_jours": 365, "convention_echeance": None},
    {"name": "Office de l'eau Réunion — Chroniques de l'eau", "cadence_jours": 365, "convention_echeance": None},
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

_LIB_METHODE = {"api": "`api`", "page": "`page`", "entete": "`entete`", "temoin": "`temoin`"}


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
