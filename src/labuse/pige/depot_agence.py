"""RADAR-VEILLE-1 (R3) — DÉPÔT AGENCE : « Publier une annonce ».

Le renversement du problème : au lieu de deviner l'adresse depuis les portails, faire venir ceux qui
l'ont. L'agence colle SA propre annonce, le parseur RADAR-DEPOT-2 reconstruit tout (aucun nouveau code
d'extraction), elle n'ajoute que l'adresse exacte → rattachement CERTAIN (source déclarée, pas de
cascade). L'annonce entre au Radar « déposée par l'agence ».

Différences avec le collecté (doctrine) :
  · contenu confié ≠ contenu collecté — photos et description S'AFFICHENT (l'agence nous en confie
    l'affichage) ; le collecté reste « faits + lien seulement » ;
  · l'adresse exacte est visible des SEULS abonnés, jamais publique ;
  · chaque dépôt écrit la mémoire foncière de la parcelle.

TOUT ce parcours est derrière le drapeau `radar_depot_agence_actif` (OFF par défaut, admin seulement) —
question Hoguet en attente chez l'avocat de Vic. La porte d'entrée (les endpoints) refuse tant qu'il est
fermé ; ce module ne suppose jamais le drapeau ouvert.
"""
from __future__ import annotations

import json

from sqlalchemy import text
from sqlalchemy.orm import Session

from . import html_next, portails
from .intake import resoudre_commune
from .tables import EV_NOUVELLE, journaliser


def analyser(html: str) -> list[dict]:
    """ÉTAPE 1-2 — reconstruire les champs depuis la page confiée par l'agence, avec le parseur EXISTANT
    (RADAR-DEPOT-2 `html_next.analyser`). Aucun nouveau code d'extraction. Retourne les enregistrements
    pré-remplis (type, prix, surfaces, description, photos, référence, url) ; l'agence vérifie et corrige."""
    return html_next.analyser(html).get("records", [])


def publier(db: Session, *, rec: dict, idu: str, lon: float | None, lat: float | None,
            adresse_exacte: str, agence_nom: str) -> dict:
    """ÉTAPE 3-4 — publier l'annonce déposée. `rec` = les champs (vérifiés/corrigés par l'agence) ; `idu`
    = la parcelle identifiée depuis l'adresse exacte (rattachement CERTAIN, source déclarée). On écrit le
    bien « déposé par l'agence » (photos + description confiées, adresse abonnés-seuls), et la mémoire
    foncière de la parcelle. Rattachement `source`/`rattachee`, critère « adresse déclarée par l'agence »
    — jamais la cascade (elle sert le collecté, pas le déposé)."""
    resolu = resoudre_commune(rec.get("commune"))
    if not resolu:
        raise ValueError("commune hors périmètre (les 24 communes)")
    commune, _insee = resolu
    if not idu:
        raise ValueError("adresse non résolue à une parcelle — l'idu est requis pour un dépôt certain")

    criteres = [{"critere": "adresse déclarée par l'agence", "valeur": adresse_exacte}]
    bien_id = db.execute(text("""
        INSERT INTO pige_biens
          (commune, type_bien, statut, idu, lat, lng, source_position,
           rattachement_etat, rattachement_niveau, rattachement_confiance, rattachement_humain,
           rattachement_criteres, depose_par_agence, agence_nom, adresse_exacte, date_publication)
        VALUES (:c, :t, 'active', :idu, :lat, :lng, 'address',
                'rattachee', 'source', 1.0, false, CAST(:crit AS jsonb), true, :agence, :adr, now()::date)
        RETURNING bien_id"""),
        {"c": commune, "t": rec.get("type"), "idu": idu, "lat": lat, "lng": lon,
         "crit": json.dumps(criteres, ensure_ascii=False), "agence": agence_nom,
         "adr": adresse_exacte}).scalar()

    url = rec.get("url") or ""
    db.execute(text(
        "INSERT INTO pige_annonces (bien_id, portail, url_sortante, list_id) "
        "VALUES (:b, :p, :u, :l) ON CONFLICT (url_sortante) DO NOTHING"),
        {"b": bien_id, "p": portails.slug_pour_url(url) or "agence",
         "u": url or f"agence:bien:{bien_id}", "l": rec.get("list_id")})

    # FAITS validés d'emblée (contenu confié par l'agence, pas une extraction à vérifier). Photos et
    # description sont STOCKÉES et affichées — la doctrine « faits + lien » ne vaut que pour le collecté.
    photos = rec.get("photos") or []
    etiquettes = {k: "source" for k in ("prix", "surface_hab", "surface_terrain", "pieces") if rec.get(k) is not None}
    db.execute(text("""
        INSERT INTO pige_faits
          (bien_id, prix, type_bien, pieces, surface_hab, surface_terrain, photos, description,
           provenance, etiquettes, valide_at)
        VALUES (:b, :prix, :t, :pieces, :sh, :st, CAST(:photos AS jsonb), :descr,
                'json_riche', CAST(:et AS jsonb), now())"""),
        {"b": bien_id, "prix": rec.get("prix"), "t": rec.get("type"), "pieces": rec.get("pieces"),
         "sh": rec.get("surface_hab"), "st": rec.get("surface_terrain"),
         "photos": json.dumps(photos, ensure_ascii=False), "descr": rec.get("description"),
         "et": json.dumps(etiquettes, ensure_ascii=False)})

    # MÉMOIRE FONCIÈRE — chaque dépôt écrit l'histoire de la parcelle (le collecté ne l'écrit que sur les
    # rattachées ; le déposé, toujours, puisque le rattachement est certain).
    journaliser(db, EV_NOUVELLE, f"Annonce déposée par l'agence — {commune}",
                detail=f"bien #{bien_id} ({rec.get('type') or '?'}) · {agence_nom} · déposé",
                idu=idu, lien=url or None, dedup=f"pige:depot-agence:{bien_id}")
    return {"bien_id": bien_id, "commune": commune, "idu": idu}


def enregistrer_interet(db: Session, *, bien_id: int, compte_id: int | None) -> dict:
    """ÉTAPE 4 (côté abonné) — « Intéressé » : on transmet les coordonnées de l'abonné à l'agence. LABUSE
    ne s'interpose pas (pas de commission, pas d'intermédiation cachée) : on trace le geste, l'envoi du
    contact à l'agence est prod. Refuse un bien qui n'est pas un dépôt agence."""
    row = db.execute(text(
        "SELECT depose_par_agence, agence_nom FROM pige_biens WHERE bien_id = :b"),
        {"b": bien_id}).mappings().first()
    if not row or not row["depose_par_agence"]:
        raise ValueError("ce bien n'est pas une annonce déposée par une agence")
    db.execute(text(
        "INSERT INTO pige_interets_agence (bien_id, compte_id) VALUES (:b, :c)"),
        {"b": bien_id, "c": compte_id})
    return {"ok": True, "agence": row["agence_nom"]}
