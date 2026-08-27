"""K2 (rattrapage KelFoncier) — coordonnées des 24 mairies.

Source : Annuaire de l'administration (data ouvertes, api-lannuaire.service-public.fr). 24 communes,
volume trivial. On INGÈRE ce que l'annuaire donne ; un champ absent reste NULL (affiché « Absent »,
jamais inventé). La date de récupération est stockée par ligne (fraîcheur = date source amont).

Rafraîchissement : `labuse ingest-mairies` (les coordonnées changent ; déclaré dans EXPLOITATION-CRON.md,
non automatisé — 24 lignes, lancé à la main).
"""
from __future__ import annotations

import json
import logging

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

log = logging.getLogger("labuse.mairies")

_API = ("https://api-lannuaire.service-public.fr/api/explore/v2.1/catalog/datasets/"
        "api-lannuaire-administration/records")
SOURCE = "Annuaire de l'administration (service-public.fr)"


def ensure_table(db: Session) -> None:
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS mairies (
            insee text PRIMARY KEY,
            commune text NOT NULL,
            nom text,
            adresse text,
            code_postal text,
            telephone text,
            email text,
            site_officiel text,
            url_annuaire text,
            source text NOT NULL,
            date_import timestamptz NOT NULL DEFAULT now()
        )"""))
    db.commit()


def _insee_map(db: Session) -> list[tuple[str, str]]:
    """(insee, commune) des 24 communes — depuis la base (jamais un INSEE écrit à la main)."""
    return [(i, c) for i, c in db.execute(text(
        "SELECT DISTINCT insee, commune FROM commune_insee_logement ORDER BY commune")).all()]


def _premier(champ_json: str | None, cle: str = "valeur") -> str | None:
    """Extrait la 1re valeur d'un champ JSON de l'annuaire (téléphone/site sont des tableaux JSON)."""
    if not champ_json:
        return None
    try:
        arr = json.loads(champ_json)
    except (ValueError, TypeError):
        return None
    for it in arr if isinstance(arr, list) else []:
        v = (it.get(cle) or "").strip() if isinstance(it, dict) else ""
        if v:
            return v
    return None


def _adresse_physique(champ_json: str | None) -> tuple[str | None, str | None]:
    """(rue, code_postal) de l'adresse PHYSIQUE (type « Adresse », pas l'adresse postale/CS)."""
    if not champ_json:
        return None, None
    try:
        arr = json.loads(champ_json)
    except (ValueError, TypeError):
        return None, None
    physiques = [a for a in arr if isinstance(a, dict) and a.get("type_adresse") == "Adresse"]
    a = (physiques or [x for x in arr if isinstance(x, dict)] or [None])[0]
    if not a:
        return None, None
    rue = " ".join(p for p in [a.get("complement1"), a.get("numero_voie")] if p and p.strip()).strip() or None
    return rue, (a.get("code_postal") or None)


def fetch_une(insee: str, timeout_s: float = 20.0) -> dict | None:
    """Interroge l'annuaire pour LA mairie d'une commune (par INSEE). None si absente."""
    params = {"where": f'code_insee_commune="{insee}" and pivot like "mairie"', "limit": 1,
              "select": "nom,adresse,telephone,adresse_courriel,site_internet,url_service_public"}
    r = httpx.get(_API, params=params, timeout=timeout_s, follow_redirects=True)
    r.raise_for_status()
    res = r.json().get("results") or []
    if not res:
        return None
    rec = res[0]
    rue, cp = _adresse_physique(rec.get("adresse"))
    return {
        "nom": rec.get("nom"),
        "adresse": rue,
        "code_postal": cp,
        "telephone": _premier(rec.get("telephone")),
        "email": (rec.get("adresse_courriel") or None),
        "site_officiel": _premier(rec.get("site_internet")),
        "url_annuaire": (rec.get("url_service_public") or None),
    }


def ingest(db: Session, timeout_s: float = 20.0) -> dict:
    """Ingère les 24 mairies (upsert par INSEE). Retourne un récap {communes, trouvees, absentes}."""
    ensure_table(db)
    communes = _insee_map(db)
    trouvees, absentes = 0, []
    for insee, commune in communes:
        try:
            data = fetch_une(insee, timeout_s=timeout_s)
        except Exception as e:  # noqa: BLE001 — une commune injoignable ne casse pas les 23 autres
            log.warning("mairie %s (%s) : échec annuaire — %s", commune, insee, e)
            absentes.append(commune)
            continue
        if data is None:
            log.info("mairie %s (%s) : absente de l'annuaire", commune, insee)
            absentes.append(commune)
            continue
        db.execute(text("""
            INSERT INTO mairies (insee, commune, nom, adresse, code_postal, telephone, email,
                                 site_officiel, url_annuaire, source, date_import)
            VALUES (:insee, :commune, :nom, :adresse, :code_postal, :telephone, :email,
                    :site_officiel, :url_annuaire, :source, now())
            ON CONFLICT (insee) DO UPDATE SET
                commune=EXCLUDED.commune, nom=EXCLUDED.nom, adresse=EXCLUDED.adresse,
                code_postal=EXCLUDED.code_postal, telephone=EXCLUDED.telephone, email=EXCLUDED.email,
                site_officiel=EXCLUDED.site_officiel, url_annuaire=EXCLUDED.url_annuaire,
                source=EXCLUDED.source, date_import=now()"""),
            {"insee": insee, "commune": commune, "source": SOURCE, **data})
        trouvees += 1
    db.commit()
    return {"communes": len(communes), "trouvees": trouvees, "absentes": absentes}


def mairie_de(db: Session, commune: str) -> dict | None:
    """Coordonnées d'une commune (par nom) pour la fiche — champs absents = None (→ « Absent »)."""
    row = db.execute(text(
        "SELECT commune, nom, adresse, code_postal, telephone, email, site_officiel, url_annuaire,"
        " source, date_import FROM mairies WHERE commune = :c"), {"c": commune}).mappings().first()
    if not row:
        return None
    d = dict(row)
    d["date_import"] = d["date_import"].date().isoformat() if d.get("date_import") else None
    return d
