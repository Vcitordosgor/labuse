"""SOURCES-5 #7 — Annuaire de l'administration (DILA) : TOUS les services publics de La Réunion.

L'ingestion `mairies.py` (K2) ne captait que les 24 MAIRIES. Ce module ingère l'annuaire COMPLET
de la DILA pour le 974 — préfecture, sous-préfectures, tribunaux (point_justice), gendarmeries,
France Services, France Travail, CCAS, CAF, CPAM, impôts (SIP), trésoreries, missions locales,
ARS/DEAL/DRARI/CCI… — soit ~436 services au 14/09/2026.

Source : api-lannuaire.service-public.fr (ODS Explore v2.1, dataset `api-lannuaire-administration`,
Licence Ouverte / Etalab 2.0). GARDE 974 : `startswith(code_insee_commune, "974")` côté API (filtre
au plus tôt — l'INSEE 974xx = La Réunion seule) PUIS vérification par ligne à l'ingestion.

Tout champ publié conservé : les 44 champs du record dans `raw` (jsonb) ; les plus utiles promus en
colonnes pour le tri/la lecture. Idempotent : upsert par `id` DILA, purge des `id` disparus du 974.
"""
from __future__ import annotations

import json
import logging

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from .garde_974 import _cp_prefixe_974

log = logging.getLogger("labuse.annuaire_services")

_API = ("https://api-lannuaire.service-public.fr/api/explore/v2.1/catalog/datasets/"
        "api-lannuaire-administration/records")
_WHERE_974 = 'startswith(code_insee_commune,"974")'
SOURCE = "Annuaire de l'administration (service-public.fr)"


def ensure_table(db: Session) -> None:
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS annuaire_services (
            id text PRIMARY KEY,
            nom text,
            pivot_type text,
            sigle text,
            categorie text,
            type_organisme text,
            insee text,
            commune text,
            code_postal text,
            adresse text,
            telephone text,
            email text,
            site_internet text,
            url_service_public text,
            mission text,
            date_modification text,
            raw jsonb NOT NULL,
            source text NOT NULL,
            date_import timestamptz NOT NULL DEFAULT now()
        )"""))
    db.execute(text("CREATE INDEX IF NOT EXISTS ix_annuaire_services_insee ON annuaire_services (insee)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS ix_annuaire_services_pivot ON annuaire_services (pivot_type)"))
    db.commit()


def _premier(champ, cle: str = "valeur") -> str | None:
    """1re valeur d'un champ tableau JSON de l'annuaire (téléphone/site sont des tableaux)."""
    if not champ:
        return None
    try:
        arr = json.loads(champ) if isinstance(champ, str) else champ
    except (ValueError, TypeError):
        return None
    for it in arr if isinstance(arr, list) else []:
        v = (it.get(cle) or "").strip() if isinstance(it, dict) else (str(it).strip() if it else "")
        if v:
            return v
    return None


def _adresse_physique(champ) -> tuple[str | None, str | None]:
    """(rue, code_postal) de l'adresse PHYSIQUE (type « Adresse », pas l'adresse postale/CS)."""
    if not champ:
        return None, None
    try:
        arr = json.loads(champ) if isinstance(champ, str) else champ
    except (ValueError, TypeError):
        return None, None
    if not isinstance(arr, list):
        return None, None
    physiques = [a for a in arr if isinstance(a, dict) and a.get("type_adresse") == "Adresse"]
    a = (physiques or [x for x in arr if isinstance(x, dict)] or [None])[0]
    if not a:
        return None, None
    rue = " ".join(p for p in [a.get("numero_voie"), a.get("complement1")] if p and str(p).strip()).strip() or None
    return rue, (a.get("code_postal") or None)


def _pivot_type(champ) -> str | None:
    """type_service_local/public du 1er pivot (tribunal → point_justice, mairie, gendarmerie…)."""
    if not champ:
        return None
    try:
        arr = json.loads(champ) if isinstance(champ, str) else champ
    except (ValueError, TypeError):
        return None
    for it in arr if isinstance(arr, list) else []:
        if isinstance(it, dict):
            t = it.get("type_service_local") or it.get("type_service_public")
            if t:
                return t
    return None


def _communes_974(db: Session) -> dict[str, str]:
    """{insee: commune} des 24 communes — pour étiqueter chaque service (jamais un INSEE en dur)."""
    return {i: c for i, c in db.execute(text(
        "SELECT DISTINCT insee, commune FROM commune_insee_logement")).all()}


def ingest(db: Session, timeout_s: float = 60.0) -> dict:
    """Ingère tous les services publics du 974 (upsert par id, purge des disparus). Récap {trouves,…}."""
    ensure_table(db)
    communes = _communes_974(db)
    vus: set[str] = set()
    rejets_974 = 0
    offset, page = 0, 100
    with httpx.Client(timeout=timeout_s, follow_redirects=True) as c:
        while True:
            r = c.get(_API, params={"where": _WHERE_974, "limit": page, "offset": offset})
            r.raise_for_status()
            res = r.json().get("results") or []
            if not res:
                break
            for rec in res:
                insee = (rec.get("code_insee_commune") or "").strip()
                # GARDE 974 par ligne (le filtre API porte déjà startswith 974 ; on re-vérifie).
                if not insee.startswith("974"):
                    rejets_974 += 1
                    continue
                sid = rec.get("id") or rec.get("itm_identifiant")
                if not sid:
                    continue
                rue, cp = _adresse_physique(rec.get("adresse"))
                # GARDE 974 sur la COLONNE servie code_postal : la DILA porte des CP erronés
                # (93200 Seine-St-Denis, 97250 Martinique sur des antennes mal saisies) ET des CEDEX
                # 978xx. Une colonne à maille adresse doit passer le garde (974/977, V4e) ; sinon on
                # laisse la colonne NULL (l'INSEE 974 fait foi) — le CP brut reste dans `raw`.
                if not _cp_prefixe_974(cp):
                    cp = None
                db.execute(text("""
                    INSERT INTO annuaire_services (id, nom, pivot_type, sigle, categorie, type_organisme,
                        insee, commune, code_postal, adresse, telephone, email, site_internet,
                        url_service_public, mission, date_modification, raw, source, date_import)
                    VALUES (:id, :nom, :pivot_type, :sigle, :categorie, :type_organisme, :insee, :commune,
                        :code_postal, :adresse, :telephone, :email, :site_internet, :url_service_public,
                        :mission, :date_modification, CAST(:raw AS jsonb), :source, now())
                    ON CONFLICT (id) DO UPDATE SET
                        nom=EXCLUDED.nom, pivot_type=EXCLUDED.pivot_type, sigle=EXCLUDED.sigle,
                        categorie=EXCLUDED.categorie, type_organisme=EXCLUDED.type_organisme,
                        insee=EXCLUDED.insee, commune=EXCLUDED.commune, code_postal=EXCLUDED.code_postal,
                        adresse=EXCLUDED.adresse, telephone=EXCLUDED.telephone, email=EXCLUDED.email,
                        site_internet=EXCLUDED.site_internet, url_service_public=EXCLUDED.url_service_public,
                        mission=EXCLUDED.mission, date_modification=EXCLUDED.date_modification,
                        raw=EXCLUDED.raw, source=EXCLUDED.source, date_import=now()"""),
                    {"id": sid, "nom": rec.get("nom"), "pivot_type": _pivot_type(rec.get("pivot")),
                     "sigle": rec.get("sigle"), "categorie": rec.get("categorie"),
                     "type_organisme": rec.get("type_organisme"), "insee": insee,
                     "commune": communes.get(insee), "code_postal": cp, "adresse": rue,
                     "telephone": _premier(rec.get("telephone")),
                     "email": (rec.get("adresse_courriel") or None),
                     "site_internet": _premier(rec.get("site_internet")),
                     "url_service_public": (rec.get("url_service_public") or None),
                     "mission": rec.get("mission"),
                     "date_modification": rec.get("date_modification"),
                     "raw": json.dumps(rec, ensure_ascii=False), "source": SOURCE})
                vus.add(sid)
            offset += page
            if offset > 5000:                       # garde-fou anti-boucle (974 ≈ 436)
                break
    # purge des services disparus du 974 (upsert idempotent complet)
    supprimes = 0
    if vus:
        supprimes = db.execute(text(
            "DELETE FROM annuaire_services WHERE id <> ALL(:ids)"), {"ids": list(vus)}).rowcount
    db.commit()
    return {"trouves": len(vus), "supprimes": supprimes, "rejets_974": rejets_974}


def services_974(db: Session) -> list[dict]:
    """Tous les services publics du 974, triés par commune puis type — pour l'écran Contacts."""
    rows = db.execute(text(
        "SELECT id, nom, pivot_type, sigle, categorie, type_organisme, insee, commune, code_postal, "
        "       adresse, telephone, email, site_internet, url_service_public, mission, date_modification "
        "FROM annuaire_services ORDER BY commune NULLS LAST, pivot_type NULLS LAST, nom")).mappings().all()
    return [dict(r) for r in rows]
