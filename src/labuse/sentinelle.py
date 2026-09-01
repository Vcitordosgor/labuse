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
           "       v.dernier_entete, v.dernier_vu, d.name AS source_nom, d.source_millesime AS servi"
           " FROM source_veille v JOIN data_sources d ON d.id = v.source_id"
           " WHERE " + " AND ".join(where) + " ORDER BY d.name")
    return [dict(r) for r in db.execute(text(sql), params).mappings()]


def passer(db, *, source_ids=None, forcer: bool = False, http=None, notifier: bool = True,
           delai_s: float | None = None) -> dict:
    """UN passage de la sentinelle (W3). Parcourt les lignes échues, sonde SÉQUENTIELLEMENT avec un
    délai, écrit le résultat dans `source_veille` (JAMAIS dans `data_sources`), et — à la PREMIÈRE
    détection d'une nouvelle version — dépose UNE notification admin dédupliquée par (source, millésime).

    Retourne un récap {sondees, nouvelles, injoignables, illisibles, notifs, details:[…]}. `http`/`delai_s`
    sont des points d'injection pour les tests (réseau stubé, délai nul)."""
    lignes = _lignes_a_sonder(db, source_ids=source_ids, forcer=forcer)
    delai = DELAI_ENTRE_SOURCES_S if delai_s is None else delai_s
    recap = {"sondees": 0, "nouvelles": 0, "injoignables": 0, "illisibles": 0, "notifs": 0, "details": []}
    for i, row in enumerate(lignes):
        if i and delai:
            time.sleep(delai)   # on n'enchaîne pas les appels sans respirer (serveur public)
        s = sonder_ligne(row, row.get("servi"), http=http)
        recap["sondees"] += 1
        # entete : on ne mémorise l'en-tête que quand on en a un (baseline ou changement).
        nouvel_entete = s.entete if s.entete is not None else row.get("dernier_entete")
        db.execute(text(
            "UPDATE source_veille SET dernier_passage_at = now(), dernier_vu = :vu,"
            "  dernier_statut = :st, dernier_message = :msg, dernier_entete = :ent, updated_at = now()"
            " WHERE id = :id"),
            {"vu": s.vu, "st": s.statut, "msg": s.message, "ent": nouvel_entete, "id": row["id"]})
        if s.statut == "nouvelle_version":
            recap["nouvelles"] += 1
            if notifier and _notifier_nouvelle(db, row, s):
                recap["notifs"] += 1
        elif s.statut == "injoignable":
            recap["injoignables"] += 1
        elif s.statut == "illisible":
            recap["illisibles"] += 1
        recap["details"].append({"source": row["source_nom"], "statut": s.statut,
                                 "vu": s.vu, "servi": row.get("servi"), "message": s.message})
    return recap


# ─────────────────────────────── W5 · peuplement de la table ───────────────────────────────
# Une entrée = (nom EXACT de la source en base) → méthode + URL amont RÉELLE (déjà portée par
# data_sources, jamais inventée) + sélecteur. Choix conservateur (W5.3 : une URL non vérifiée est
# pire qu'une absence). On privilégie `entete` (aucun sélecteur à deviner) pour les fichiers versionnés,
# `page` pour l'index DVF (cas phare du mandat), `api` seulement quand le champ de date est un contrat
# documenté et stable. Les sources absentes d'ici restent NON surveillées (état normal) — cf. compte-rendu.
SEED: list[dict] = [
    # DVF — cas phare (« DVF : 2026-S1 publié — vous servez 2025-S2 »). L'index géo-DVF liste les
    # millésimes annuels ; on garde le plus récent (max). Reprise de sentinelle-dvf-cadastre (moitié DVF).
    {"name": "DVF / valeurs foncières", "methode": "page",
     "url": "https://files.data.gouv.fr/geo-dvf/latest/csv/", "selecteur": r"20\d{2}"},
    # Cadastre Etalab — moitié « cadastre » de la reprise. Le fichier /latest/ change de Last-Modified
    # à chaque nouveau millésime DGFiP : `entete` le capte sans nommer de version (doctrine W2.3).
    {"name": "Cadastre Etalab (bulk DGFiP/Etalab)", "methode": "entete",
     "url": "https://cadastre.data.gouv.fr/data/etalab-cadastre/latest/geojson/communes/974/97415/cadastre-97415-parcelles.json.gz",
     "selecteur": None},
    # Fichiers ZIP horodatés : Last-Modified avance à la publication d'un nouveau millésime.
    {"name": "BPE INSEE", "methode": "entete",
     "url": "https://www.insee.fr/fr/statistiques/fichier/8217525/BPE25.zip", "selecteur": None},
    {"name": "QPV 2024 (ANCT)", "methode": "entete",
     "url": "https://static.data.gouv.fr/resources/quartiers-prioritaires-de-la-politique-de-la-ville-qpv/20260115-204323/qpv-2024-geojson.zip",
     "selecteur": None},
    # DPE ADEME — flux continu : la sentinelle vérifie que le flux RÉPOND et remonte sa date de MAJ.
    # `dataUpdatedAt` est un champ documenté et stable de l'API data-fair (métadonnées du dataset).
    {"name": "DPE ADEME (logements existants)", "methode": "api",
     "url": "https://data.ademe.fr/data-fair/api/v1/datasets/dpe03existant", "selecteur": "dataUpdatedAt"},
    # BODACC — Opendatasoft v2.1 : `dataset.metas.default.modified` (date de dernière modif du jeu).
    {"name": "BODACC (procédures collectives)", "methode": "api",
     "url": "https://bodacc-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/annonces-commerciales",
     "selecteur": "dataset.metas.default.modified"},
]


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


def _notifier_nouvelle(db, row: dict, s: Sonde) -> bool:
    """Notification admin (cloche, feed systeme compte_id NULL), DÉDUPLIQUÉE par (source, millésime) —
    UNE notif par source et par millésime constaté, jamais un rappel quotidien (W4.1). `permanent=True`
    → NOT EXISTS toutes dates. Formulation : « DVF : 2026-S1 est publié — vous servez 2025-S2 »."""
    from .api.events import creer_notification
    nom = row["source_nom"]
    servi = row.get("servi")
    vu = s.vu or "?"
    if row.get("methode") == "entete":     # pas de millésime lisible : on dit « le fichier a changé »
        titre = f"{nom} : le fichier amont a changé — à vérifier"
        detail = s.message or "ETag/Last-Modified différent du dernier passage."
    else:
        titre = f"{nom} : {vu} est publié" + (f" — vous servez {servi}" if servi else "")
        detail = (s.message or "") + " — geste supervisé : Vic déclenche l'ingestion (rien n'entre sans validation)."
    return bool(creer_notification(
        db, kind="systeme", compte_id=None, source="Veille sources",
        titre=titre, detail=detail.strip(), lien="/sources",
        dedup=f"sentinelle:{row['source_id']}:{vu}", permanent=True))
