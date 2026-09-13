"""Ingestion DPE ADEME (Vague C2, réparée SOURCES-2 lot 0) → table `dpe_records`  [data pure].

Un DPE par logement (dédup `numero_dpe`), sur les TROIS jeux post-2021 : `dpe03existant`,
`dpe02neuf`, `dpe01tertiaire` (colonne `jeu`). Rattachement parcelle 100 % LOCAL (mandat 11/07 :
« géocodage = table adresses locale », plus aucun appel api-adresse), en cascade :
  1. `identifiant_ban` ADEME → `adresses.id_ban` (IDU déjà rattaché par ban_adresses)  → 'ban_locale'
  2. point BAN natif EPSG:2975 (`coordonnee_cartographique_x/y_ban`) → ST_Contains     → 'point_ban'
  3. `adresse_brut` normalisée (numéro + voie) → `adresses` de la commune              → 'adresse_locale'
  4. sinon 'aucun' (un « aucun » honnête vaut mieux qu'un rattachement faux).
Puis rattachement BÂTIMENT (SOURCES-2) : `rnb_id` par la clé BAN dans `rnb_batiments.adresses`,
sinon par contenance géométrique du point local dans `shape_2975` — l'ID-RNB devient la clé de
jointure DPE ↔ RPLS ↔ BAN.

⚠ CONTAMINATION MÉTROPOLE (mesuré live 09/08/2026, re-mesuré 13/09/2026, SOURCES-2 lot 0).
Le filtre amont `code_insee_ban:974*` rend ~914 lignes pour l'île — mais **900 d'entre elles
portent un CP BRUT métropolitain** (ex. 62200 Boulogne-sur-Mer, 34200 Sète, 67300 Schiltigheim) :
le géocodeur BAN de l'ADEME rabat massivement des logements de métropole sur des codes INSEE 974,
avec un `identifiant_ban` d'allure réunionnaise (`97415_1330_00038`). Ce faux id_ban matche la
table `adresses` locale en passe 1 → le logement métropolitain se voit ÉPINGLÉ sur une vraie
parcelle réunionnaise (coordonnées valides mais FAUSSES). Il n'existe AUCUN champ « INSEE brut »
au schéma ADEME : filtrer par INSEE ne répare rien. On tranche sur le CP BRUT (saisi par le
diagnostiqueur d'après le bien, fiable), JAMAIS sur le géocodage BAN : cf. `is_reunion_authentic`
— PUIS on exige la corroboration locale contre l'homonymie (cf. `ingest_jeu`). Gisement mesuré
13/09/2026 : 93 lignes au CP brut 974 (16 existants + 75 neufs + 2 tertiaires), dont 16
RÉUNIONNAISES corroborées (14 + 0 + 2) — les 77 autres sont métropolitaines (homonymie/typo CP).

Signal « positif quand présent », JAMAIS exhaustif. La donnée d'abord, le scoring ensuite : ce
module PEUPLE `dpe_records` ; le signal est branché par le Score V (famille E) et v_passoire_thermique.
"""
from __future__ import annotations

import json
import re
import unicodedata
from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..connectors.dpe import DpeConnector

SOURCE_NAME = "DPE ADEME (logements existants)"


def _to_int(v) -> int | None:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def _to_float(v) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _to_date(v) -> date | None:
    try:
        return date.fromisoformat(str(v)[:10])
    except (TypeError, ValueError):
        return None


def _cp_reunion(cp) -> bool:
    """CP réunionnais : 97400–97490 (97600 = Mayotte, 977xx/978xx = Antilles françaises)."""
    n = _to_int(cp)
    return n is not None and 97400 <= n <= 97490


def is_reunion_authentic(rec: dict) -> bool:
    """Vrai si l'enregistrement est un logement RÉUNIONNAIS d'après le CP BRUT (saisi par le
    diagnostiqueur d'après le bien — fiable), et JAMAIS d'après le géocodage BAN de l'ADEME
    (faux à ~98 % au 974 : il rabat des logements métropolitains sur des codes INSEE 974).

    Règle : on rejette une ligne dont le CP brut CONTREDIT La Réunion. CP brut absent → on laisse
    passer (0 cas mesuré sur les 913 lignes 974 au 09/08/2026 ; la cascade locale reste seul juge).
    """
    cp = rec.get("code_postal_brut")
    if cp in (None, ""):
        return True
    return _cp_reunion(cp)


def parse_record(rec: dict, jeu: str = "existant") -> dict | None:
    """Enregistrement /lines → dict DPE normalisé. None si pas de `numero_dpe` (dédup impossible).

    M71 B1 — TROU DU FILTRE corrigé (audit M66-B : 2 lignes code_insee 34172/59350 en base).
    Cas orphelin (inverse de la contamination documentée en tête de module) : CP BRUT réunionnais
    mais géocodage BAN MÉTROPOLITAIN. Le logement est réunionnais authentique, mais TOUTE son
    identité BAN (code_insee_ban, code_postal_ban, identifiant_ban, x/y, score) est un mensonge :
    on la PURGE au parse — sinon dpe_records stocke un code_insee hors département et les passes
    1-2 du rattachement peuvent épingler une fausse parcelle via le faux id_ban.

    SOURCES-2 : `jeu` ∈ existant|neuf|tertiaire. Le tertiaire n'a NI type_batiment NI surface
    habitable (sa `surface_utile` reste dans raw, jamais maquillée en habitable) : type='tertiaire'.
    """
    numero = rec.get("numero_dpe")
    if not numero:
        return None
    ban_ment = (_cp_reunion(rec.get("code_postal_brut"))
                and not str(rec.get("code_insee_ban") or "").startswith("974"))

    def _cp_str(v) -> str | None:  # le CP brut ADEME arrive parfois en ENTIER (97490)
        return str(v) if v not in (None, "") else None

    return {
        "numero_dpe": str(numero),
        "jeu": jeu,
        "etiquette_dpe": rec.get("etiquette_dpe"),
        "etiquette_ges": rec.get("etiquette_ges"),
        "type_batiment": "tertiaire" if jeu == "tertiaire" else rec.get("type_batiment"),
        "surface_habitable": (None if jeu == "tertiaire"
                              else _to_float(rec.get("surface_habitable_logement"))),
        "annee_construction": _to_int(rec.get("annee_construction")),
        "adresse": (rec.get("adresse_brut") if ban_ment else
                    rec.get("adresse_ban") or rec.get("adresse_brut")),
        "adresse_brut": rec.get("adresse_brut"),
        "code_insee": None if ban_ment else rec.get("code_insee_ban"),
        "code_postal": _cp_str(rec.get("code_postal_brut") if ban_ment else
                               rec.get("code_postal_ban") or rec.get("code_postal_brut")),
        "date_etablissement": _to_date(rec.get("date_etablissement_dpe")),
        "id_ban": None if ban_ment else rec.get("identifiant_ban"),
        "score_ban": None if ban_ment else _to_float(rec.get("score_ban")),
        "x_ban": None if ban_ment else _to_float(rec.get("coordonnee_cartographique_x_ban")),
        "y_ban": None if ban_ment else _to_float(rec.get("coordonnee_cartographique_y_ban")),
    }


_UPSERT = text(
    "INSERT INTO dpe_records "
    " (numero_dpe, jeu, etiquette_dpe, etiquette_ges, type_batiment, surface_habitable, "
    "  annee_construction, adresse, code_insee, code_postal, date_etablissement, "
    "  lon, lat, geocode_score, parcelle_idu, rattachement, rnb_id, raw) "
    "VALUES (:num,:jeu,:ed,:eg,:tb,:surf,:ac,:adr,:ci,:cp,:de,:lon,:lat,:sc,:idu,:rat,:rnb, "
    "        CAST(:raw AS jsonb)) "
    "ON CONFLICT (numero_dpe) DO UPDATE SET "
    "  jeu=EXCLUDED.jeu, etiquette_dpe=EXCLUDED.etiquette_dpe, etiquette_ges=EXCLUDED.etiquette_ges, "
    "  type_batiment=EXCLUDED.type_batiment, surface_habitable=EXCLUDED.surface_habitable, "
    "  annee_construction=EXCLUDED.annee_construction, adresse=EXCLUDED.adresse, "
    "  code_insee=EXCLUDED.code_insee, code_postal=EXCLUDED.code_postal, "
    "  date_etablissement=EXCLUDED.date_etablissement, lon=EXCLUDED.lon, lat=EXCLUDED.lat, "
    "  geocode_score=EXCLUDED.geocode_score, parcelle_idu=EXCLUDED.parcelle_idu, "
    "  rattachement=EXCLUDED.rattachement, rnb_id=EXCLUDED.rnb_id, raw=EXCLUDED.raw, "
    "  ingested_at=now()")


def migrate_dpe_records(session: Session) -> None:
    """SOURCES-2 lot 0 — colonnes additives (idempotent) : `jeu` (les 3 jeux ADEME) et `rnb_id`
    (clé de jointure bâtiment). Les 17 lignes pré-existantes venaient toutes de dpe03existant."""
    session.execute(text(
        "ALTER TABLE dpe_records ADD COLUMN IF NOT EXISTS jeu varchar(12) NOT NULL DEFAULT 'existant'"))
    session.execute(text(
        "ALTER TABLE dpe_records ADD COLUMN IF NOT EXISTS rnb_id varchar(16)"))


# ───────────────────────── géocodage local (table `adresses`) ─────────────────────────

def _norm(s: str | None) -> str:
    """Normalisation adresse : minuscules, sans accents, ponctuation → espace, espaces réduits."""
    if not s:
        return ""
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


# « 12 bis rue des Lilas 97440 Saint-André » → numero='12', voie='rue des lilas' (coupe au CP 974xx).
_RE_BRUT = re.compile(r"^(?:(\d{1,5})\s*(?:bis|ter|quater|[a-z])?\s+)?(.+?)(?:\s+974\d\d\b.*)?$")


def _parse_brut(adresse: str | None) -> tuple[str | None, str] | None:
    m = _RE_BRUT.match(_norm(adresse))
    if not m or not m.group(2):
        return None
    return m.group(1), m.group(2)


def _index_adresses(session: Session, insee: str) -> dict:
    """Index (numero, voie) normalisés → liste (idu, lon, lat) des adresses rattachées de la commune."""
    idx: dict[tuple[str, str], list] = {}
    rows = session.execute(text(
        "SELECT numero, voie, idu, ST_X(geom), ST_Y(geom) FROM adresses "
        "WHERE insee = :i AND idu IS NOT NULL"), {"i": insee})
    for numero, voie, idu, lon, lat in rows:
        idx.setdefault((_norm(numero), _norm(voie)), []).append((idu, lon, lat))
    return idx


def _parcelle_at_2975(session: Session, x: float, y: float) -> tuple | None:
    """(idu, lon, lat) de la parcelle contenant le point BAN natif EPSG:2975. None si aucune."""
    return session.execute(text(
        "SELECT idu, ST_X(pt), ST_Y(pt) FROM parcels, LATERAL ("
        "  SELECT ST_Transform(ST_SetSRID(ST_Point(:x,:y),2975),4326) AS pt) q "
        "WHERE ST_Contains(geom_2975, ST_SetSRID(ST_Point(:x,:y),2975)) LIMIT 1"),
        {"x": x, "y": y}).first()


def _rattacher(session: Session, p: dict, idx_adresses: dict) -> dict:
    """Cascade locale id_ban → point BAN → adresse brute. Retourne lon/lat/score/idu/rattachement."""
    out = {"lon": None, "lat": None, "sc": p["score_ban"], "idu": None, "rat": "aucun"}
    # 1. clé BAN → table adresses (IDU déjà rattaché en 3 passes par ban_adresses)
    if p["id_ban"]:
        row = session.execute(text(
            "SELECT idu, ST_X(geom), ST_Y(geom) FROM adresses WHERE id_ban = :b AND idu IS NOT NULL"),
            {"b": p["id_ban"]}).first()
        if row:
            out.update(idu=row[0], lon=row[1], lat=row[2], rat="ban_locale")
            return out
    # 2. point BAN natif 2975 (aussi les identifiants niveau voie, absents de `adresses`)
    if p["x_ban"] and p["y_ban"]:
        row = _parcelle_at_2975(session, p["x_ban"], p["y_ban"])
        if row:
            out.update(idu=row[0], lon=row[1], lat=row[2], rat="point_ban")
            return out
    # 3. adresse brute normalisée contre les adresses de la commune (numéro + voie exacts,
    #    accepté seulement si toutes les candidates pointent la MÊME parcelle — pas de pari)
    parsed = _parse_brut(p["adresse_brut"] or p["adresse"])
    if parsed:
        cands = idx_adresses.get((parsed[0] or "", parsed[1]), [])
        if cands and len({c[0] for c in cands}) == 1:
            out.update(idu=cands[0][0], lon=cands[0][1], lat=cands[0][2], rat="adresse_locale")
    return out


def _rattacher_rnb(session: Session, p: dict, geo: dict) -> str | None:
    """SOURCES-2 — rnb_id du logement : clé BAN dans `rnb_batiments.adresses` (jsonb `id`),
    sinon contenance du point local dans `shape_2975`. None honnête si aucun bâtiment RNB
    (ou si le réservoir RNB n'existe pas — bases de test)."""
    if session.execute(text("SELECT to_regclass('rnb_batiments')")).scalar() is None:
        return None
    if p.get("id_ban"):
        row = session.execute(text(
            "SELECT rnb_id FROM rnb_batiments "
            "WHERE adresses @> CAST(:j AS jsonb) LIMIT 1"),
            {"j": json.dumps([{"id": p["id_ban"]}])}).first()
        if row:
            return row[0]
    if geo.get("lon") is not None and geo.get("lat") is not None:
        row = session.execute(text(
            "SELECT rnb_id FROM rnb_batiments "
            "WHERE ST_Contains(shape_2975, ST_Transform(ST_SetSRID(ST_Point(:x,:y),4326),2975)) "
            "LIMIT 1"), {"x": geo["lon"], "y": geo["lat"]}).first()
        if row:
            return row[0]
    return None


# ───────────────────────── ingestion ─────────────────────────

def _upsert(session: Session, rec: dict, p: dict, geo: dict, rnb_id: str | None = None) -> None:
    session.execute(_UPSERT, {
        "num": p["numero_dpe"], "jeu": p.get("jeu", "existant"),
        "ed": p["etiquette_dpe"], "eg": p["etiquette_ges"],
        "tb": p["type_batiment"], "surf": p["surface_habitable"], "ac": p["annee_construction"],
        "adr": p["adresse"], "ci": p["code_insee"], "cp": p["code_postal"],
        "de": p["date_etablissement"], "lon": geo["lon"], "lat": geo["lat"], "sc": geo["sc"],
        "idu": geo["idu"], "rat": geo["rat"], "rnb": rnb_id,
        "raw": json.dumps(rec, ensure_ascii=False)})


def ingest_jeu(session: Session, jeu: str, connector: DpeConnector | None = None) -> dict:
    """SOURCES-2 lot 0 — LA moisson d'un jeu ADEME (existant|neuf|tertiaire) : toutes les lignes
    au CP BRUT réunionnais, quel que soit le géocodage BAN (orphelins compris — 0 ligne 974 sans
    CP brut, mesuré 13/09/2026 sur les 3 jeux).

    ⚠ HOMONYMIE (SOURCES-2, mesuré 13/09/2026) : le CP brut lui-même peut mentir — 75 DPE neufs
    « ST LEU, CP 97436 » sont en réalité UN programme de Saint-Leu-la-FORÊT (Val-d'Oise, BAN
    95563 score 0,97 ; « rue de Paris »/« rue du Rû » absentes des adresses du Saint-Leu
    réunionnais), et 2 existants « 97490/97434 » sont à Montpellier et Lille. Règle : une ligne
    dont le géocodage BAN est réunionnais (cohérent avec le CP brut) est gardée ; une ligne dont
    le BAN CONTREDIT le CP brut (ou manque) n'est gardée QUE si son adresse brute se corrobore
    dans la table `adresses` locale (passe 3) — sinon rejetée : mieux vaut une absence honnête
    qu'un logement de métropole épinglé sur l'île.

    MIROIR : les lignes du jeu disparues chez l'ADEME (DPE remplacé/retiré) ou plus corroborées
    sont SUPPRIMÉES en fin de moisson — la table reflète le producteur, pas son histoire.

    Idempotent (upsert `numero_dpe`). ⚠ ÉCRIT + APPELS RÉSEAU (data-fair uniquement).
    Rattachement parcelle en cascade locale + bâtiment `rnb_id` (BAN puis géométrie)."""
    connector = connector or DpeConnector(jeu=jeu)
    migrate_dpe_records(session)
    idx_par_commune: dict[str, dict] = {}
    gardes: list[str] = []
    n_rat = n_rnb = n_rejetes = 0
    for rec in connector.fetch_reunion_authentiques():
        p = parse_record(rec, jeu=jeu)
        if p is None or not is_reunion_authentic(rec):
            continue
        coherent = bool(p["code_insee"])   # BAN réunionnais, cohérent avec le CP brut
        geo = {"lon": None, "lat": None, "sc": p["score_ban"], "idu": None, "rat": "aucun"}
        insees = ([p["code_insee"]] if coherent else [r[0] for r in session.execute(
            text("SELECT DISTINCT insee FROM adresses WHERE code_postal = :cp"),
            {"cp": p["code_postal"]}).all()] if p["code_postal"] else [])
        for insee in insees:
            if insee not in idx_par_commune:
                idx_par_commune[insee] = _index_adresses(session, insee)
            geo = _rattacher(session, p, idx_par_commune[insee])
            if geo["idu"]:
                p["code_insee"] = insee
                break
        if not coherent and not geo["idu"]:
            # BAN contradictoire ou absent, ET aucune corroboration locale → homonymie probable.
            n_rejetes += 1
            continue
        # SOURCES-3 lot 4 — GARDE-FOU 974 COMMUN (belt-and-braces après la logique DPE) : croise
        # CP + commune + coordonnées BAN. Un rejet ici est journalisé avec ses trois valeurs.
        from .garde_974 import journaliser_rejet, verifier_974
        from .run_all import REUNION_COMMUNES
        _commune_nom = next((nom for ins, nom in REUNION_COMMUNES if ins == p.get("code_insee")), None)
        _v = verifier_974(cp=p.get("code_postal"), commune=_commune_nom,
                          lon=geo.get("lon"), lat=geo.get("lat"))
        if not _v.ok:
            journaliser_rejet(session, "dpe_ademe", _v, cle=p.get("numero_dpe"))
            n_rejetes += 1
            continue
        rnb_id = _rattacher_rnb(session, p, geo)
        n_rat += 1 if geo["idu"] else 0
        n_rnb += 1 if rnb_id else 0
        _upsert(session, rec, p, geo, rnb_id)
        gardes.append(p["numero_dpe"])
    session.execute(text(
        "DELETE FROM dpe_records WHERE jeu = :jeu AND numero_dpe <> ALL(:gardes)"),
        {"jeu": jeu, "gardes": gardes})
    _touch_source(session)
    session.flush()
    return {"jeu": jeu, "dpe": len(gardes), "rattaches_parcelle": n_rat,
            "rattaches_rnb": n_rnb, "rejetes_homonymie": n_rejetes}


def ingest_commune(session: Session, insee: str, commune: str,
                   connector: DpeConnector | None = None) -> dict:
    """Ingère les DPE d'une commune dans `dpe_records` (rattachement 100 % local, cf. module).

    Idempotent (upsert sur `numero_dpe`). ⚠ ÉCRIT + APPELS RÉSEAU (data-fair uniquement).
    Retourne des compteurs. Ne touche PAS au score (recalcul Score V séparé).
    """
    connector = connector or DpeConnector()
    migrate_dpe_records(session)
    idx_adresses: dict | None = None
    n = n_geo = n_rat = n_hors = 0
    for rec in connector.fetch_commune(insee):
        p = parse_record(rec)
        if not p:
            continue
        if not is_reunion_authentic(rec):
            # logement métropolitain rabattu sur un INSEE 974 par le géocodeur BAN : on ne
            # l'épingle PAS sur une parcelle réunionnaise (cf. docstring module).
            n_hors += 1
            continue
        if idx_adresses is None:
            idx_adresses = _index_adresses(session, insee)
        geo = _rattacher(session, p, idx_adresses)
        n_geo += 1 if geo["lon"] is not None else 0
        n_rat += 1 if geo["idu"] else 0
        _upsert(session, rec, p, geo, _rattacher_rnb(session, p, geo))
        n += 1
    _touch_source(session)
    session.flush()
    return {"dpe": n, "geocodes": n_geo, "rattaches_parcelle": n_rat, "hors_reunion": n_hors}


def ingest_orphelins(session: Session, connector: DpeConnector | None = None) -> dict:
    """DPE réunionnais SANS géocodage BAN (CP brut 974xx) — invisibles du filtre commune.

    La commune est déduite du CP brut via `adresses` ; le rattachement retombe sur la passe 3
    (adresse brute). code_insee reste NULL si le CP couvre plusieurs communes sans match adresse.
    """
    connector = connector or DpeConnector()
    migrate_dpe_records(session)
    n = n_rat = n_hors = 0
    for rec in connector.fetch_orphelins_974():
        p = parse_record(rec)
        if not p:
            continue
        if not is_reunion_authentic(rec):  # ceinture-bretelles : le filtre amont est déjà CP brut 974xx
            n_hors += 1
            continue
        geo = {"lon": None, "lat": None, "sc": None, "idu": None, "rat": "aucun"}
        insees = [r[0] for r in session.execute(text(
            "SELECT DISTINCT insee FROM adresses WHERE code_postal = :cp"),
            {"cp": p["code_postal"]}).all()] if p["code_postal"] else []
        for insee in insees:
            geo = _rattacher(session, p, _index_adresses(session, insee))
            if geo["idu"]:
                p["code_insee"] = insee
                break
        if p["code_insee"] is None and len(insees) == 1:
            p["code_insee"] = insees[0]
        n_rat += 1 if geo["idu"] else 0
        _upsert(session, rec, p, geo, _rattacher_rnb(session, p, geo))
        n += 1
    session.flush()
    return {"dpe": n, "rattaches_parcelle": n_rat, "hors_reunion": n_hors}


def sample_report(session: Session, insee: str) -> dict:
    """Rapport (commune) depuis dpe_records DÉJÀ ingérée — sans réseau."""
    etiq = {r[0]: r[1] for r in session.execute(text(
        "SELECT etiquette_dpe, count(*) FROM dpe_records WHERE code_insee=:c GROUP BY 1 ORDER BY 1"),
        {"c": insee}).all()}
    total = int(session.execute(text("SELECT count(*) FROM dpe_records WHERE code_insee=:c"),
                                {"c": insee}).scalar() or 0)
    maisons_fg = int(session.execute(text(
        "SELECT count(*) FROM dpe_records WHERE code_insee=:c AND type_batiment='maison' "
        "AND etiquette_dpe IN ('F','G')"), {"c": insee}).scalar() or 0)
    parcelles = int(session.execute(text(
        "SELECT count(DISTINCT parcelle_idu) FROM dpe_records WHERE code_insee=:c "
        "AND parcelle_idu IS NOT NULL"), {"c": insee}).scalar() or 0)
    passoires_parc = int(session.execute(text(
        "SELECT count(*) FROM v_passoire_thermique WHERE code_insee=:c"), {"c": insee}).scalar() or 0)
    ex = [dict(r) for r in session.execute(text(
        "SELECT etiquette_dpe, adresse, surface_habitable, date_etablissement, parcelle_idu "
        "FROM dpe_records WHERE code_insee=:c AND type_batiment='maison' "
        "AND etiquette_dpe IN ('F','G') AND parcelle_idu IS NOT NULL "
        "ORDER BY date_etablissement DESC LIMIT 5"), {"c": insee}).mappings().all()]
    return {"insee": insee, "dpe": total, "distribution_etiquette": etiq,
            "maisons_fg": maisons_fg, "parcelles_rattachees": parcelles,
            "parcelles_passoire": passoires_parc, "exemples": ex}


def _touch_source(session: Session) -> None:
    session.execute(
        text("UPDATE data_sources SET last_sync_at = now() WHERE name = :n"), {"n": SOURCE_NAME})
