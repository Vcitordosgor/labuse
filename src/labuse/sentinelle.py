"""SENTINELLE-1 — l'agent de veille des sources amont, généralisé à toutes les sources.

DOCTRINE (à ne pas transgresser) : la sentinelle **surveille et prévient**. Elle ne télécharge rien,
n'ingère rien, ne remplace aucune donnée, n'écrit JAMAIS dans `data_sources`. Vic décide de chaque mise
à jour. Elle ne visite JAMAIS un portail d'annonces — uniquement les fournisseurs de données publiques
(IGN, DGFiP, INSEE, Sitadel, BAN, DHUP…). Détection 100 % mécanique : dates, motifs, en-têtes ; zéro LLM.

TROIS MÉTHODES, PAS PLUS (W2), chacune déclarée par la source dans `source_veille.methode` :
  · `api`    — le fournisseur expose un JSON de versions. `selecteur` = chemin JSON (`a.b.0.c`).
  · `page`   — page HTML, `selecteur` = regex de millésime (ex. `20\\d{2}-S[12]`) ; on garde le PLUS récent.
  · `entete` — pas de millésime lisible : on compare `Last-Modified`/`ETag` au dernier vu (`dernier_entete`).

Une source injoignable/illisible n'est PAS une source en erreur : c'est la SENTINELLE qui a échoué,
pas la donnée (W3.5 — les deux états restent distincts partout).
"""
from __future__ import annotations

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
            else:
                return Sonde("illisible", message=f"méthode inconnue : {methode}")
        except Exception as exc:  # noqa: BLE001 — tout échec réseau/parse = la SENTINELLE a échoué, pas la donnée
            return Sonde("injoignable", message=f"{type(exc).__name__}: {str(exc)[:200]}")
        return evaluer(s, servi)
    finally:
        if http is not None:
            _http = _prev


# ─────────────────────────────── le passage (orchestration W3) ───────────────────────────────

def _lignes_a_sonder(db, *, source_ids=None, forcer: bool) -> list[dict]:
    """Lignes `actif=true` dont la cadence est ÉCHUE (ou toutes si `forcer`, ou celles ciblées). On
    joint `data_sources` pour lire le millésime SERVI (source_millesime) et le nom (message/notif)."""
    where = ["v.actif = true"]
    params: dict = {}
    if source_ids:
        where.append("v.source_id = ANY(:ids)")
        params["ids"] = list(source_ids)
    if not forcer and not source_ids:
        # cadence échue : jamais passé, ou passage plus vieux que cadence_heures.
        where.append("(v.dernier_passage_at IS NULL OR "
                     "v.dernier_passage_at <= now() - make_interval(hours => v.cadence_heures))")
    sql = ("SELECT v.id, v.source_id, v.url_version, v.methode, v.selecteur, v.cadence_heures,"
           "       v.dernier_entete, v.dernier_vu, v.dernier_notifie_vu, v.echecs_consecutifs,"
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
]

#: SENTINELLE-2 (X3.3) — les sources NON surveillées gardent un état EXPLICITE au panneau admin
#: (« non surveillée » + raison en infobulle), jamais un blanc ni une fausse erreur. Raison par nom
#: EXACT ; défaut générique sinon. Ce que chaque famille a coûté est détaillé dans SENTINELLE-INVENTAIRE.md.
RAISONS_NON_SURVEILLEES: dict[str, str] = {
    # Endpoints de REQUÊTE sans notion de version (API interrogée à la demande, aucun millésime lisible)
    "Urbanisme PLU/GPU (API Carto)": "API Carto GPU interrogée à la demande (idurba par commune) — aucun millésime global lisible.",
    "GPU — zonages d'assainissement": "API Carto GPU interrogée à la demande — aucun millésime global lisible.",
    "GPU — zonages d'assainissement (info-surf typeinf 19)": "Doublon du GPU assainissement (canal info-surf) — même amont, non re-surveillé.",
    "SUP — assiettes GPU (API Carto)": "API Carto GPU interrogée à la demande — aucun millésime global lisible.",
    "Géorisques — sites et sols pollués": "Bases BRGM (BASIAS/BASOL/SIS) servies par l'API Géorisques live ; pas de jeu data.gouv national à millésime trouvé.",
    "Géorisques — cavités souterraines": "Base BRGM cavités servie par l'API Géorisques live ; pas de jeu data.gouv national à millésime trouvé.",
    "Géorisques — mouvements de terrain": "Base BRGM BDMvt servie par l'API Géorisques live ; pas de jeu data.gouv national à millésime trouvé.",
    "Recherche d'entreprises (DINUM)": "API de recherche live (agrégat Sirene/RNE) — pas de millésime ingéré à comparer.",
    "INPI RNE (dirigeants)": "API authentifiée interrogée par SIREN — pas de millésime global.",
    "OpenStreetMap / Overpass": "OSM en flux continu (planet) — pas de version ; requête live.",
    "Parkings OSM (loi APER)": "OSM en flux continu — pas de version ; requête live.",
    "OSM — transport (pôles d'échange & téléphérique)": "OSM en flux continu — pas de version ; requête live.",
    "INPN / patrinat — espaces protégés": "Couches patrinat servies en WFS Géoplateforme ; pas de jeu data.gouv national espaces protégés à millésime trouvé.",
    # Portails / proxys injoignables ou hubs (pas un jeu unique)
    "PEIGEO (hub régional)": "Hub AGORAH injoignable depuis l'infra (HTTP 000) — pas de jeu unique à sonder.",
    "DEAL Réunion (WMS/WFS)": "Hôte carto DEAL injoignable (servi par proxys) — aucune URL amont stable.",
    "DEAL Réunion — PPR / aléas": "WFS Lizmap DEAL (requête) — pas de millésime lisible ; hôte souvent indisponible.",
    "50 pas géométriques — limite haute (DEAL)": "WFS Lizmap DEAL (requête) — pas de millésime lisible.",
    "Région Réunion Open Data (Opendatasoft)": "Hub/catalogue ODS (275 jeux) — pas un jeu unique ; les jeux servis sont surveillés individuellement.",
    "Géoplateforme IGN": "Hub IGN (WFS/WMS) — pas un jeu unique ; les produits IGN servis sont surveillés individuellement.",
    # Réglementaire Légifrance : pages SPA sans millésime lisible, texte à identifiant figé
    "ZFANG — zone franche d'activité nouvelle génération (Légifrance)": "Page Légifrance rendue en JS (aucun millésime lisible côté serveur) ; un texte modifié reçoit un nouvel identifiant.",
    "FRR ex-ZRR — zone spéciale d'action rurale (Légifrance)": "Page Légifrance rendue en JS (aucun millésime lisible côté serveur) ; un texte modifié reçoit un nouvel identifiant.",
    # Alimentées à la main / hors automatisation (non surveillables PAR NATURE — réponse valable, X2)
    "Radar (pige d'annonces)": "Collecte 100 % humaine — non surveillable par nature.",
    "VRD / assainissement (SPANC)": "Champ manuel EPCI — aucune donnée ouverte fine, pas d'URL.",
    "Fichiers fonciers (Cerema)": "Sous convention, non ingérée — aucune URL amont publique.",
    "MOBPRO (mobilités domicile-travail, INSEE)": "Import CSV manuel (abandonné pour l'étude de zone) — pas d'URL de version stable.",
    "Office de l'eau Réunion — Chroniques de l'eau": "Seed CSV extrait à la main d'un PDF (chronique numérotée) — chaque édition = nouvelle URL, non surveillable proprement.",
    # Autre
    "PVGIS (Commission européenne)": "API de calcul (v5.3 dans l'URL) — pas de jeu à millésime ; le service ne versionne pas de données à comparer.",
}


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
            db.execute(text("UPDATE source_veille SET url_version = :u, methode = :m, selecteur = :sel,"
                            " updated_at = now() WHERE source_id = :s"),
                       {"u": e["url"], "m": e["methode"], "sel": e.get("selecteur"), "s": sid})
        else:
            db.execute(text("INSERT INTO source_veille (source_id, url_version, methode, selecteur,"
                            " cadence_heures, actif) VALUES (:s, :u, :m, :sel, 24, true)"),
                       {"s": sid, "u": e["url"], "m": e["methode"], "sel": e.get("selecteur")})
            crees += 1
    return crees


def _ligne_neuf(row: dict, s: Sonde) -> str:
    """Une ligne du détail du digest pour une NOUVELLE version (formulation SENTINELLE-1 conservée)."""
    nom, servi, vu = row["source_nom"], row.get("servi"), (s.vu or "?")
    if row.get("methode") == "entete":     # pas de millésime lisible : « le fichier a changé »
        return f"• {nom} : le fichier amont a changé — à vérifier."
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
    return bool(creer_notification(
        db, kind="systeme", compte_id=None, source="Veille sources",
        titre=titre, detail="\n".join(lignes), lien="/sources",
        dedup="sentinelle-digest:" + sig, permanent=True))
