"""BLOC B (B3) — LE RADAR DES SOURCES : surveillance universelle, ingestion sélective.

Pour chaque source de `data_sources`, une SONDE périodique détecte une nouvelle publication
SANS RIEN TÉLÉCHARGER (HEAD → Last-Modified/ETag, ou un champ de métadonnées JSON de qq Ko).
L'état vit dans `source_radar` ; la page Sources l'affiche ; /healthz/crons le résume.

Doctrine : le radar SIGNALE, l'humain DÉCIDE — JAMAIS d'auto-ingestion des couches de la
cascade gelée (GPU/Géorisques : détection seule, décision J+2 fraîcheur). Les seuls flux
auto restent les crons vivants (bodacc/dvf/dpe/sitadel/ban/catnat), et même eux ne passent
pas par ici : le radar est un THERMOMÈTRE, pas un déclencheur.

Types de sonde :
  head     — HEAD sur un artefact stable (fichier « latest ») : Last-Modified/ETag.
  json     — GET d'une métadonnée légère (API catalogue) : un champ daté (qq Ko max).
  (repli)  — HEAD sur endpoint_url de data_sources ; sans signal exploitable → non_sondable
             (constat honnête, jamais une date inventée).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

log = logging.getLogger("labuse.radar")

_TIMEOUT = httpx.Timeout(12.0)
_UA = {"User-Agent": "labuse-radar/1.0 (surveillance de publication ; HEAD/metadonnees uniquement)"}

# ── Sondes CURÉES (motif ILIKE sur data_sources.name → sonde fiable, issue des connecteurs) ──
# mode 'auto'    : un cron vivant ingère déjà (le radar confirme la publication amont).
# mode 'manuel'  : couche de la cascade GELÉE ou grande passe — le radar signale, on décide.
SONDES: dict[str, dict] = {
    "Cadastre Etalab%": {
        "kind": "head", "mode": "manuel", "cadence": "semestriel (millésime Etalab)",
        "url": "https://cadastre.data.gouv.fr/data/etalab-cadastre/latest/geojson/communes/974/97415/cadastre-97415-parcelles.json.gz"},
    "DVF%": {
        "kind": "head", "mode": "auto", "cadence": "cron hebdo (mer. 05:00)",
        "url": "https://files.data.gouv.fr/geo-dvf/latest/csv/2024/departements/974.csv.gz"},
    "Base Adresse Nationale": {
        "kind": "head", "mode": "auto", "cadence": "cron mensuel (le 5)",
        "url": "https://adresse.data.gouv.fr/data/ban/adresses/latest/csv/adresses-974.csv.gz"},
    "BODACC%": {
        "kind": "json", "mode": "auto", "cadence": "cron quotidien (04:30)",
        "url": ("https://bodacc-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/"
                "annonces-commerciales/records?select=dateparution&order_by=dateparution%20desc&limit=1"),
        "champ": ("results", 0, "dateparution")},
    "DPE ADEME%": {
        "kind": "json", "mode": "auto", "cadence": "cron hebdo (mar. 05:20)",
        "url": "https://data.ademe.fr/data-fair/api/v1/datasets/dpe03existant",
        "champ": ("dataUpdatedAt",)},
    "SITADEL%": {
        "kind": "json", "mode": "auto", "cadence": "cron quotidien (04:15)",
        "url": ("https://data.statistiques.developpement-durable.gouv.fr/dido/api/v1/"
                "datasets?text=sitadel&page=1&pageSize=10"),
        "champ": ("data", 0, "last_modified")},
}


def _valeur_sonde(s: dict) -> tuple[str | None, str | None]:
    """(valeur détectée, détail d'erreur) — zéro téléchargement de données."""
    try:
        with httpx.Client(timeout=_TIMEOUT, headers=_UA, follow_redirects=True) as c:
            if s["kind"] == "head":
                r = c.head(s["url"])
                # sonde de REPLI (endpoint API) : seul Last-Modified fait foi — un ETag
                # faible (W/…) d'endpoint dynamique change à chaque réponse = fausse
                # « publication » en boucle (constaté sur API Carto à la 2e passe).
                v = r.headers.get("last-modified")
                if not v and not s.get("repli"):
                    v = r.headers.get("etag")
                return (v, None) if v else (None, f"HEAD {r.status_code} sans Last-Modified stable")
            r = c.get(s["url"])
            r.raise_for_status()
            node = r.json()
            for k in s["champ"]:
                node = node[k]
            return (str(node), None)
    except Exception as e:  # noqa: BLE001 — la sonde enregistre l'échec, jamais d'exception sortante
        return None, f"{type(e).__name__}: {e}"[:180]


def ensure_table(db: Session) -> None:
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS source_radar (
            source_name text PRIMARY KEY,
            mode text NOT NULL,            -- auto (cron vivant) | manuel (grande passe / cascade gelée)
            cadence text,
            sonde text NOT NULL,           -- head | json | endpoint | aucune
            url text,
            valeur text,                   -- Last-Modified / ETag / champ daté observé
            premiere_vue timestamptz,
            derniere_verif timestamptz,
            dernier_changement timestamptz,
            statut text NOT NULL,          -- a_jour | nouvelle_publication | non_sondable | erreur
            detail text
        )"""))


def _sonde_pour(name: str, endpoint_url: str | None) -> dict | None:
    from fnmatch import fnmatch
    for motif, s in SONDES.items():
        if fnmatch(name.lower(), motif.lower().replace("%", "*")):
            return dict(s)
    if endpoint_url and endpoint_url.startswith("http"):
        return {"kind": "head", "mode": "manuel", "cadence": "grande passe (à la décision)",
                "url": endpoint_url, "repli": True}
    return None


def run_radar(db: Session) -> dict:
    """Passe de sonde sur TOUTES les sources — écrit source_radar, renvoie le résumé."""
    ensure_table(db)
    rows = db.execute(text("SELECT name, endpoint_url FROM data_sources ORDER BY id")).mappings().all()
    now = datetime.now(timezone.utc)
    resume = {"sondees": 0, "changements": [], "non_sondables": 0, "erreurs": 0}
    for r in rows:
        name = r["name"]
        s = _sonde_pour(name, r["endpoint_url"])
        prev = db.execute(text("SELECT valeur, premiere_vue, dernier_changement FROM source_radar"
                               " WHERE source_name = :n"), {"n": name}).mappings().first()
        if s is None:
            db.execute(text("""
                INSERT INTO source_radar (source_name, mode, cadence, sonde, statut, detail, derniere_verif)
                VALUES (:n, 'manuel', 'grande passe (à la décision)', 'aucune', 'non_sondable',
                        'aucune URL sondable (accès manuel/convention)', :t)
                ON CONFLICT (source_name) DO UPDATE SET derniere_verif = :t"""),
                       {"n": name, "t": now})
            resume["non_sondables"] += 1
            continue
        valeur, err = _valeur_sonde(s)
        resume["sondees"] += 1
        if valeur is None:
            statut = "non_sondable" if (err or "").startswith("HEAD") else "erreur"
            if statut == "erreur":
                resume["erreurs"] += 1
            else:
                resume["non_sondables"] += 1
            db.execute(text("""
                INSERT INTO source_radar (source_name, mode, cadence, sonde, url, statut, detail, derniere_verif)
                VALUES (:n, :m, :c, :k, :u, :s, :d, :t)
                ON CONFLICT (source_name) DO UPDATE SET
                    mode = :m, cadence = :c, sonde = :k, url = :u, statut = :s, detail = :d, derniere_verif = :t"""),
                {"n": name, "m": s["mode"], "c": s["cadence"],
                 "k": "endpoint" if s.get("repli") else s["kind"], "u": s["url"],
                 "s": statut, "d": err, "t": now})
            continue
        change = bool(prev and prev["valeur"] and prev["valeur"] != valeur)
        statut = "nouvelle_publication" if change else "a_jour"
        if change:
            resume["changements"].append({"source": name, "avant": prev["valeur"], "apres": valeur})
            log.info("radar : %s a publié (%s → %s)", name, prev["valeur"], valeur)
        db.execute(text("""
            INSERT INTO source_radar (source_name, mode, cadence, sonde, url, valeur,
                                      premiere_vue, derniere_verif, dernier_changement, statut, detail)
            VALUES (:n, :m, :c, :k, :u, :v, :t, :t, NULL, 'a_jour', NULL)
            ON CONFLICT (source_name) DO UPDATE SET
                mode = :m, cadence = :c, sonde = :k, url = :u, valeur = :v, derniere_verif = :t,
                dernier_changement = CASE WHEN :chg THEN :t ELSE source_radar.dernier_changement END,
                statut = :s, detail = NULL"""),
            {"n": name, "m": s["mode"], "c": s["cadence"],
             "k": "endpoint" if s.get("repli") else s["kind"], "u": s["url"], "v": valeur,
             "t": now, "chg": change, "s": statut})
    db.commit()
    return resume


def etat_radar(db: Session) -> list[dict]:
    """Lecture seule pour l'API — [] si la table n'existe pas encore (radar jamais lancé)."""
    if not db.execute(text("SELECT to_regclass('source_radar')")).scalar():
        return []
    return [dict(r) for r in db.execute(text(
        "SELECT source_name, mode, cadence, sonde, valeur, derniere_verif,"
        "       dernier_changement, statut, detail FROM source_radar")).mappings().all()]
