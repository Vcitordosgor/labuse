"""RADAR P1 · V3 — endpoints ADMIN de la page Radar (réservés au compte pilote, comme le reste).

Câble les fonctions V2 (extraction/intake) : dépôt d'une capture, file d'extraction (brouillons),
validation, file de re-vérification priorisée à deux niveaux, arbre de check quotidien. Aucune
donnée d'annonce republiée : on sert des FAITS + le lien sortant, jamais photo/titre/texte.
"""
from __future__ import annotations

import base64

from fastapi import APIRouter, Request
from pydantic import BaseModel
from sqlalchemy import text

from ..db import engine, session_scope
from . import intake
from .tables import EV_BAISSE_PRIX, EV_STATUT_CHANGE, journaliser

router = APIRouter(tags=["radar"])

# seuils de cycle (mandat V0 §4) — repris ici pour la priorisation de la file.
SEUIL_VENTE_LONGUE_J = 90


class DeposerIn(BaseModel):
    lien: str
    image_b64: str
    media_type: str = "image/jpeg"


class DeposerHtmlIn(BaseModel):
    html: str
    nom_fichier: str | None = None


class ValiderIn(BaseModel):
    bien_id: int
    faits: dict = {}


class BienIn(BaseModel):
    bien_id: int


class PrixIn(BaseModel):
    bien_id: int
    prix: int


@router.post("/admin/radar/deposer")
def radar_deposer(body: DeposerIn, request: Request) -> dict:
    """Saisie du jour : une capture (base64) + son lien → extraction, contrôle commune, dédoublonnage,
    brouillon. Retour immédiat sur doublon d'URL / commune hors périmètre (rien de validé)."""
    from ..api.auth import exiger_admin
    exiger_admin(request)
    try:
        image = base64.b64decode(body.image_b64, validate=True)
    except Exception:  # noqa: BLE001
        return {"statut": "echec_extraction", "motif": "image base64 illisible"}
    with session_scope() as db:
        return intake.deposer(db, image, body.media_type, body.lien.strip())


@router.post("/admin/radar/deposer-html")
def radar_deposer_html(body: DeposerHtmlIn, request: Request) -> dict:
    """RADAR-HTML (Lot 1) — dépôt d'une PAGE DE RÉSULTATS HTML enregistrée par Vic (Cmd+S). Remplace la
    capture d'écran + l'agent vision : la page porte les données structurées __NEXT_DATA__. Idempotent
    par list_id (re-déposer ne duplique rien). Échoue BRUYAMMENT si __NEXT_DATA__ est absent/altéré."""
    from ..api.auth import exiger_admin
    from . import html_ingest, html_next
    exiger_admin(request)
    with session_scope() as db:
        try:
            return {"ok": True, **html_ingest.ingester(db, body.html, body.nom_fichier)}
        except html_next.NextDataError as exc:
            # échec bruyant, mais rendu proprement à l'écran admin (pas un 500 muet) — RIEN en base.
            return {"ok": False, "erreur": "next_data", "motif": str(exc)}
        except html_ingest.DepotStockageError as exc:
            # RADAR-RECETTE-1 D4 — échec d'ÉCRITURE disque : le message nomme le chemin (jamais « réseau »).
            return {"ok": False, "erreur": "stockage",
                    "motif": f"archivage impossible : {exc} — créer le répertoire ou donner les droits "
                             "(ou définir LABUSE_PIGE_DEPOTS_DIR). Rien n'a été enregistré."}


@router.post("/admin/radar/valider")
def radar_valider(body: ValiderIn, request: Request) -> dict:
    from ..api.auth import exiger_admin
    exiger_admin(request)
    with session_scope() as db:
        try:
            return intake.valider(db, body.bien_id, body.faits, valide_par=None)
        except ValueError as exc:   # RD-502 — correction hostile refusée proprement (jamais un 500)
            return {"ok": False, "valide": False, "motif": f"correction refusée : {exc}"}


@router.get("/admin/radar/extraction")
def radar_extraction(request: Request) -> dict:
    """File d'extraction : les brouillons (valide_at NULL), du plus récent au plus ancien."""
    from ..api.auth import exiger_admin
    exiger_admin(request)
    with engine().begin() as c:
        rows = [dict(r) for r in c.execute(text(
            """SELECT b.bien_id, b.commune, b.type_bien, b.rattachement_niveau, f.prix,
                      f.surface_hab, f.surface_terrain, f.dpe_classe, f.pieces, f.particulier_pro,
                      f.etiquettes, f.a_verifier, a.portail, a.url_sortante,
                      b.created_at
               FROM pige_biens b JOIN pige_faits f ON f.bien_id = b.bien_id
               LEFT JOIN pige_annonces a ON a.bien_id = b.bien_id
               WHERE f.valide_at IS NULL
               ORDER BY b.created_at DESC LIMIT 100""")).mappings()]
    for r in rows:
        r["created_at"] = r["created_at"].isoformat() if r["created_at"] else None
    return {"file": rows, "n": len(rows)}


@router.get("/admin/radar/reverif")
def radar_reverif(request: Request) -> dict:
    """File de re-vérification PRIORISÉE : plus anciennes non confirmées d'abord, puis proches du
    seuil de vente longue (90 j), puis suivies par un client (watched_parcels sur l'idu rattaché)."""
    from ..api.auth import exiger_admin
    exiger_admin(request)
    with engine().begin() as c:
        rows = [dict(r) for r in c.execute(text(
            f"""SELECT b.bien_id, b.commune, b.type_bien, b.statut, f.prix, a.portail, a.url_sortante,
                      b.date_derniere_confirmation, b.date_publication,
                      EXISTS (SELECT 1 FROM watched_parcels w WHERE w.idu = b.idu) AS suivi_client,
                      (b.date_publication IS NOT NULL
                       AND b.date_publication <= current_date - {SEUIL_VENTE_LONGUE_J}) AS proche_longue
               FROM pige_biens b JOIN pige_faits f ON f.bien_id = b.bien_id
               LEFT JOIN pige_annonces a ON a.bien_id = b.bien_id
               WHERE f.valide_at IS NOT NULL AND b.statut IN ('active','en_vente_longue','a_reverifier')
               ORDER BY suivi_client DESC, proche_longue DESC, b.date_derniere_confirmation ASC
               LIMIT 200""")).mappings()]
    for r in rows:
        for k in ("date_derniere_confirmation", "date_publication"):
            r[k] = r[k].isoformat() if r[k] else None
    return {"file": rows, "n": len(rows)}


@router.post("/admin/radar/toujours-en-ligne")
def radar_toujours(body: BienIn, request: Request) -> dict:
    """Passage LÉGER : confirme qu'une annonce est toujours en ligne (bump date de confirmation)."""
    from ..api.auth import exiger_admin
    exiger_admin(request)
    with session_scope() as db:
        db.execute(text("UPDATE pige_biens SET date_derniere_confirmation = now(), statut = 'active' "
                        "WHERE bien_id = :b"), {"b": body.bien_id})
        db.commit()
    return {"ok": True, "bien_id": body.bien_id}


@router.post("/admin/radar/prix")
def radar_prix(body: PrixIn, request: Request) -> dict:
    """Passage ATTENTIF : prix modifié → historique + drapeau baisse."""
    from ..api.auth import exiger_admin
    exiger_admin(request)
    with session_scope() as db:
        ancien = db.execute(text("SELECT prix FROM pige_faits WHERE bien_id = :b"),
                            {"b": body.bien_id}).scalar()
        db.execute(text("UPDATE pige_faits SET prix = :p, updated_at = now() WHERE bien_id = :b"),
                   {"p": body.prix, "b": body.bien_id})
        db.execute(text("UPDATE pige_biens SET date_derniere_confirmation = now() WHERE bien_id = :b"),
                   {"b": body.bien_id})
        if ancien is not None and body.prix != ancien:
            db.execute(text("INSERT INTO pige_prix_historique (bien_id, ancien_prix, nouveau_prix) "
                            "VALUES (:b, :a, :n)"), {"b": body.bien_id, "a": ancien, "n": body.prix})
            if body.prix < ancien:
                journaliser(db, EV_BAISSE_PRIX, f"Baisse de prix — bien #{body.bien_id}",
                            detail=f"{ancien} € → {body.prix} €",
                            dedup=f"pige:baisse:{body.bien_id}:{body.prix}")
        db.commit()
    return {"ok": True, "bien_id": body.bien_id, "prix": body.prix}


@router.post("/admin/radar/retiree")
def radar_retiree(body: BienIn, request: Request) -> dict:
    """Vic marque une annonce retirée (clic humain). Un lien mort = `retiree`, jamais `retiree_sans_vente`."""
    from ..api.auth import exiger_admin
    exiger_admin(request)
    with session_scope() as db:
        # retiree_le horodate le retrait (base de retiree_sans_vente D2 — jamais déduit d'un lien mort).
        db.execute(text("UPDATE pige_biens SET statut = 'retiree', retiree_le = now() WHERE bien_id = :b"),
                   {"b": body.bien_id})
        journaliser(db, EV_STATUT_CHANGE, f"Bien retiré — #{body.bien_id}",
                    detail="marqué retiré (file de re-vérif)", dedup=f"pige:retiree:{body.bien_id}")
        db.commit()
    return {"ok": True, "bien_id": body.bien_id, "statut": "retiree"}


@router.get("/admin/radar/check")
def radar_check(request: Request) -> dict:
    """Arbre de check quotidien : compteurs du rituel + drapeau intake vide depuis 48 h."""
    from ..api.auth import exiger_admin
    exiger_admin(request)
    with engine().begin() as c:
        q = lambda s: c.execute(text(s)).scalar() or 0
        file_extraction = q("SELECT count(*) FROM pige_faits WHERE valide_at IS NULL")
        nouveautes = q("SELECT count(*) FROM pige_biens WHERE date_premiere_saisie::date = current_date")
        en_vente_longue = q("SELECT count(*) FROM pige_biens WHERE statut = 'en_vente_longue'")
        baisses = q("SELECT count(*) FROM event_log WHERE kind = 'pige.baisse_prix' "
                    "AND ts::date = current_date")
        # CONNEXIONS-2 Lot 3 (KO-4) : le compteur lit la table UNIQUE `signalements` (fiche + annonce),
        # non traités — plus l'event_log du jour seul. L'admin les voit et les traite au dashboard.
        signalements = q("SELECT count(*) FROM signalements WHERE statut = 'nouveau'")
        derniere = c.execute(text("SELECT max(date_saisie) FROM pige_annonces")).scalar()
    from datetime import datetime, timedelta, timezone
    vide_48h = derniere is None or derniere < datetime.now(tz=timezone.utc) - timedelta(hours=48)
    # RV2-V1 — état du répertoire de captures (écriture) exposé à l'admin : le défaut prod se voit
    # AVANT le premier dépôt, avec le chemin fautif nommé.
    from .tables import captures_dir_writable
    cap_ok, cap_detail = captures_dir_writable()
    return {
        "cible_minutes": 15,
        "file_extraction": file_extraction,
        "reverif_du_jour": nouveautes,            # cadence quotidienne du rituel
        "signalements_en_attente": signalements,
        "compteurs": {"nouveautes": nouveautes, "en_vente_longue": en_vente_longue, "baisses": baisses},
        "intake_vide_48h": bool(vide_48h),
        "derniere_saisie": derniere.isoformat() if derniere else None,
        "captures_dir_ok": cap_ok,
        "captures_dir": cap_detail,
    }

# ══════════════ RADAR P3 · C1 — endpoints CLIENT (lecture : faits + lien, jamais le contenu) ══════════════
# Un client authentifié (pas admin) voit les biens VALIDÉS. La carte n'affiche que les rattachés ;
# le listing montre tout avec une pastille. Chaque clic SORTANT est logué dans pige_clics.

class ClicIn(BaseModel):
    bien_id: int
    annonce_id: int | None = None


class SignalerIn(BaseModel):
    bien_id: int
    motif: str = ""


@router.get("/radar/biens")
def radar_biens(request: Request,
                commune: str | None = None, type_bien: str | None = None,
                prix_min: int | None = None, prix_max: int | None = None,
                surface_hab_min: float | None = None, surface_hab_max: float | None = None,
                surface_terrain_min: float | None = None, surface_terrain_max: float | None = None,
                particulier_pro: str | None = None, statuts: str | None = None,
                statut: str | None = None, a_qualifier: str | None = None,
                periode_debut: str | None = None, periode_fin: str | None = None,
                rattache: str | None = None, sous_marche: str | None = None, tri: str = "recentes",
                page: int = 1, taille: int | None = None, limit: int | None = None) -> dict:
    """Liste filtrée des biens VALIDÉS pour un client.

    RADAR-RECETTE-1 D2 — les paramètres sont HONORÉS et la troncature est explicite :
      · `statut` (singulier) ET `statuts` (CSV) acceptés (défaut active+en_vente_longue) ;
      · `limit` alias de `taille` (défaut 50, borné au plafond serveur) ;
      · `a_qualifier` = oui|non ; `rattache` = oui|non ;
      · réponse : n_total (filtre) · n_servi · plafond · tronquee · n_rattaches (pins carte)."""
    from . import client
    # `statut` singulier fusionné dans la liste ; `limit` alias de `taille` (le 1er non-None gagne).
    statuts_liste = [s for s in ((statuts or "") + "," + (statut or "")).split(",") if s] or None
    taille_eff = taille if taille is not None else (limit if limit is not None else 50)
    filtres = {
        "commune": commune, "type_bien": type_bien, "prix_min": prix_min, "prix_max": prix_max,
        "surface_hab_min": surface_hab_min, "surface_hab_max": surface_hab_max,
        "surface_terrain_min": surface_terrain_min, "surface_terrain_max": surface_terrain_max,
        "particulier_pro": particulier_pro,
        "statuts": statuts_liste,
        "a_qualifier": a_qualifier if a_qualifier in ("oui", "non") else None,
        "periode_debut": periode_debut, "periode_fin": periode_fin,
        "rattache": rattache if rattache in ("oui", "non") else None,
        # RADAR-DEPOT-2 D4 — badge « sous le marché » filtrable (paramètre API + bouton front).
        "sous_marche": sous_marche if sous_marche in ("oui", "non") else None,
    }
    with session_scope() as db:
        return client.lister(db, filtres=filtres, tri=tri, page=page, taille=taille_eff)


@router.get("/radar/biens/{bien_id}")
def radar_bien_detail(bien_id: int, request: Request) -> dict:
    from . import client
    with session_scope() as db:
        d = client.detail(db, bien_id)
    if d is None:
        return {}
    return d


@router.post("/radar/clic")
def radar_clic(body: ClicIn, request: Request) -> dict:
    """Loggue un clic SORTANT (vers le portail source). Le front ouvre le portail (nouvel onglet,
    rel=noopener) ; on n'ouvre RIEN côté serveur — on trace l'usage."""
    from ..api.tenant import current_compte
    from . import client
    with session_scope() as db:
        cid = client.enregistrer_clic(db, compte_id=current_compte(request),
                                      bien_id=body.bien_id, annonce_id=body.annonce_id)
        db.commit()
    return {"ok": True, "clic_id": cid}


@router.get("/admin/radar/a-instruire")
def radar_a_instruire(request: Request) -> dict:
    """RADAR-DEPOT-2 (D3) — file d'INSTRUCTION admin : les biens en PISTE (plusieurs candidates possibles),
    non encore tranchés à la main. C'est là que l'admin rattache — jamais le client. Priorise les biens
    suivis par un client (watched_parcels) puis les plus récents."""
    from ..api.auth import exiger_admin
    exiger_admin(request)
    with engine().begin() as c:
        rows = [dict(r) for r in c.execute(text(
            """SELECT b.bien_id, b.commune, b.type_bien, f.prix, f.surface_terrain, f.surface_hab,
                      f.declaratif, a.portail, a.url_sortante,
                      COALESCE(jsonb_array_length(b.rattachement_pistes), 0) AS n_candidates
               FROM pige_biens b JOIN pige_faits f ON f.bien_id = b.bien_id
               LEFT JOIN pige_annonces a ON a.bien_id = b.bien_id
               WHERE f.valide_at IS NOT NULL AND b.rattachement_etat = 'piste'
                 AND b.rattachement_humain = false AND b.a_qualifier = false
               ORDER BY b.date_premiere_saisie DESC LIMIT 100""")).mappings()]
    return {"file": rows, "n": len(rows)}


@router.post("/admin/radar/instruire")
def radar_instruire(body: BienIn, request: Request) -> dict:
    """RADAR-DEPOT-2 (D3) — « Instruire cette annonce » est désormais un geste ADMIN SEULEMENT : un
    rattachement client erroné serait un faux fait servi à tous. Relance la cascade À LA DEMANDE et rend
    les candidates ENRICHIES — pour chacune, sa VUE ORTHO (`ortho_url`) et l'état de CHAQUE critère
    (convergent/divergent). L'admin compare les toits et tranche. Aucun automatisme n'en part (ni
    courrier, ni « vendue », ni stat parcellaire). Un bien déjà rattaché À LA MAIN n'est pas ré-instruit."""
    import json as _json

    from sqlalchemy import text as _t

    from ..api.auth import exiger_admin
    from . import rattachement_html
    exiger_admin(request)
    with session_scope() as db:
        rec = db.execute(_t(
            "SELECT b.bien_id, b.commune, b.type_bien AS type, b.est_copro, b.lat, b.lng, "
            "       b.source_position, b.rattachement_humain, f.surface_terrain, f.surface_hab, "
            "       f.annee_construction, f.dpe_classe "
            "FROM pige_biens b JOIN pige_faits f ON f.bien_id = b.bien_id WHERE b.bien_id = :b"),
            {"b": body.bien_id}).mappings().first()
        if not rec:
            return {"ok": False, "motif": "bien inconnu"}
        if rec["rattachement_humain"]:
            return {"ok": True, "bien_id": body.bien_id, "etat": "rattachee", "humain": True,
                    "candidates": [], "motif": "rattachement tranché à la main — fait foi"}
        ratt = rattachement_html.rattacher(db, dict(rec))
        # enrichit chaque candidate : critères convergents/divergents + URL ortho.
        candidates = []
        for p in ratt.get("pistes", []):
            idu = p.get("idu")
            candidates.append({**p, "ortho_url": f"/admin/radar/ortho/{idu}" if idu else None,
                               "criteres_detail": rattachement_html.criteres_pour_idu(db, dict(rec), idu) if idu else []})
        # ré-écrit UNIQUEMENT l'état/pistes/critères (jamais la position ni le statut).
        db.execute(_t(
            "UPDATE pige_biens SET rattachement_etat = :e, rattachement_niveau = :n, idu = :idu, "
            " rattachement_confiance = :c, rattachement_pistes = CAST(:p AS jsonb), "
            " rattachement_criteres = CAST(:cr AS jsonb) "
            "WHERE bien_id = :b AND rattachement_humain = false"),
            {"e": ratt["etat"], "n": ratt["niveau"], "idu": ratt.get("idu"),
             "c": ratt.get("confiance"), "p": _json.dumps(ratt.get("pistes") or []),
             "cr": _json.dumps(ratt.get("criteres") or []), "b": body.bien_id})
        db.commit()
    return {"ok": True, "bien_id": body.bien_id, "etat": ratt["etat"], "humain": False,
            "candidates": candidates, "criteres": ratt.get("criteres", []), "motif": ratt.get("motif")}


@router.get("/admin/radar/ortho/{idu}")
def radar_ortho(idu: str, request: Request):
    """RATTACHEMENT-V2 (Lot 2) — vignette ORTHO (BD ORTHO 20 cm IGN) d'une parcelle candidate, servie à
    l'écran d'instruction ADMIN (D3). PNG ou 204 si indisponible (parcelle inconnue / WMS injoignable)."""
    from fastapi import Response

    from ..api.auth import exiger_admin
    from ..ingestion.ortho_tiles import ortho_png_parcelle
    exiger_admin(request)
    with session_scope() as db:
        png = ortho_png_parcelle(db, idu)
    if not png:
        return Response(status_code=204)
    return Response(content=png, media_type="image/png",
                    headers={"Cache-Control": "public, max-age=86400"})


class RattacherHumainIn(BaseModel):
    bien_id: int
    idu: str


@router.post("/admin/radar/rattacher-humain")
def radar_rattacher_humain(body: RattacherHumainIn, request: Request) -> dict:
    """RADAR-DEPOT-2 (D3) — l'ADMIN a tranché via l'ortho : le bien passe RATTACHÉE, rattachement HUMAIN
    (fait foi, jamais écrasé par une republication — acquis du mandat V2). On vérifie que l'idu est une
    parcelle réelle de la commune du bien (pas d'idu arbitraire injecté). RÉSERVÉ ADMIN : un rattachement
    client erroné serait un faux fait servi à tous."""
    from sqlalchemy import text as _t

    from ..api.auth import exiger_admin
    exiger_admin(request)
    with session_scope() as db:
        b = db.execute(_t("SELECT commune, a_qualifier FROM pige_biens WHERE bien_id = :b"),
                       {"b": body.bien_id}).mappings().first()
        if not b:
            return {"ok": False, "motif": "bien inconnu"}
        if b["a_qualifier"]:
            return {"ok": False, "motif": "bien à qualifier — rattachement interdit (acquis mandat précédent)"}
        ok = db.execute(_t("SELECT 1 FROM parcels WHERE idu = :i AND commune = :c"),
                        {"i": body.idu, "c": b["commune"]}).scalar()
        if not ok:
            return {"ok": False, "motif": f"parcelle {body.idu} hors de la commune {b['commune']}"}
        db.execute(_t(
            "UPDATE pige_biens SET idu = :i, rattachement_etat = 'rattachee', rattachement_niveau = 'source', "
            " rattachement_confiance = 1.0, rattachement_humain = true, "
            " rattachement_criteres = CAST(:cr AS jsonb) WHERE bien_id = :b"),
            {"i": body.idu, "b": body.bien_id,
             "cr": __import__("json").dumps([{"critere": "humain", "valeur": "tranché par le client via l'ortho"}])})
        db.commit()
    return {"ok": True, "bien_id": body.bien_id, "idu": body.idu, "etat": "rattachee", "humain": True}


@router.get("/radar/signaux/{commune}")
def radar_signaux(commune: str, request: Request) -> dict:
    """RADAR-HTML (Lot 4) — signaux croisés d'UNE commune : écart demandé/acté (terrain + bâti) et
    annonces actives. Écarts CONSTATÉS entre deux sources datées, aucun verdict de valeur."""
    from . import signaux
    with session_scope() as db:
        return signaux.annonces_actives_zone(db, commune)


@router.post("/radar/signaler")
def radar_signaler(body: SignalerIn, request: Request) -> dict:
    """Signalement client (annonce retirée / erreur) → alerte Vic, JAMAIS un changement de statut."""
    from ..api.tenant import current_compte
    from . import client
    with session_scope() as db:
        ev = client.signaler(db, compte_id=current_compte(request), bien_id=body.bien_id, motif=body.motif)
        db.commit()
    return {"ok": True, "event_id": ev}


# ══════════════ RADAR P4 · D1 — veille Radar (critères client) ══════════════

class VeilleIn(BaseModel):
    commune: str | None = None
    type_bien: str | None = None
    prix_min: int | None = None          # RADAR-CATÉGORIE (T4) — le prix rejoint les critères de veille
    prix_max: int | None = None
    surface_terrain_min: float | None = None
    surface_hab_min: float | None = None
    particulier_only: bool = False
    # RADAR-VEILLE-1 (V3) — plus de filtre d'événement : une veille notifie sur TOUT événement d'un bien
    # correspondant (nouvelle annonce, baisse, retour). Le mail (template 13) dit lequel a déclenché.


@router.post("/radar/veille")
def radar_veille_creer(body: VeilleIn, request: Request) -> dict:
    """Le client crée une veille Radar (ses critères). Alimente l'ALERTE veille de fin de journée."""
    from ..api.tenant import current_compte
    from . import veille
    crit = {k: v for k, v in body.model_dump().items() if v not in (None, [], False)}
    with session_scope() as db:
        vid = veille.creer(db, compte_id=current_compte(request), criteria=crit)
        db.commit()
    return {"ok": True, "veille_id": vid}


@router.get("/radar/veille")
def radar_veille_lister(request: Request) -> dict:
    from ..api.tenant import current_compte
    from . import veille
    with session_scope() as db:
        return {"veilles": veille.lister(db, current_compte(request))}


@router.delete("/radar/veille/{veille_id}")
def radar_veille_supprimer(veille_id: int, request: Request) -> dict:
    from ..api.tenant import current_compte
    from . import veille
    with session_scope() as db:
        ok = veille.supprimer(db, current_compte(request), veille_id)
        db.commit()
    return {"ok": ok}


# ══════════════ RADAR P6 · D3 — onglet Marché (stats par commune, honnêteté statistique) ══════════════

@router.get("/radar/marche")
def radar_marche(request: Request) -> dict:
    """Statistiques Radar par commune (24 + total île). Chaque mesure porte son n ; < 5 = insuffisant."""
    from . import marche
    with session_scope() as db:
        return marche.stats(db)


# ══════════════ RADAR-VEILLE-1 (R3) — DÉPÔT AGENCE « Publier une annonce » (derrière drapeau) ══════════════
# Tout le parcours est FERMÉ par défaut (config.radar_depot_agence_actif) : question Hoguet en attente chez
# l'avocat de Vic. Drapeau OFF → 404 partout, rien ne s'ouvre. Admin seulement pour le dépôt.

def _porte_depot_agence() -> None:
    from ..config import get_settings
    if not get_settings().radar_depot_agence_actif:
        from fastapi import HTTPException
        raise HTTPException(404, "dépôt agence désactivé (question Hoguet en attente)")


def _est_admin(request: Request) -> bool:
    from ..api.auth import exiger_admin
    try:
        exiger_admin(request)
        return True
    except Exception:  # noqa: BLE001
        return False


def _depot_admin_ou_ouvert(request: Request) -> None:
    """SECTEUR-2b (U2) — le parcours de dépôt est accessible à l'ADMIN (toujours, drapeau fermé compris,
    pour tester) OU à N'IMPORTE QUEL client quand le DRAPEAU EST OUVERT. Drapeau fermé + non-admin → 404
    (le client ne voit rien tant que le drapeau est fermé)."""
    if _est_admin(request):
        return
    _porte_depot_agence()   # non-admin : 404 si le drapeau est fermé


class DepotAnalyserIn(BaseModel):
    html: str


# RETOURS-3 R3 (Vic 31/08) — l'agence colle SON URL d'annonce. Le champ détecte une URL http(s) et
# bascule sur une lecture serveur ONE-SHOT (une seule requête, headers navigateur, timeout court, AUCUN
# retry, aucune boucle). Si le portail refuse (Datadome/403/timeout/page sans __NEXT_DATA__), on rend un
# message HONNÊTE + le repli guidé Cmd+S — jamais l'erreur __NEXT_DATA__ brute face à une URL.
import re as _re

_URL_RE = _re.compile(r"^\s*https?://", _re.I)
_BROWSER_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}
_DEPOT_REPLI = ("Enregistrez la page de l'annonce en « page web complète » (Cmd+S / Ctrl+S), "
                "puis collez ici le HTML.")


def _fetch_page_oneshot(url: str) -> str:
    """Lecture ONE-SHOT d'une URL d'annonce : une seule requête, headers navigateur, timeout court,
    AUCUN retry. Lève RuntimeError (message court) si le portail refuse — l'appelant en fait un motif
    honnête. Ne suit qu'un nombre borné de redirections (requests par défaut)."""
    import requests
    try:
        r = requests.get(url, headers=_BROWSER_HEADERS, timeout=8, allow_redirects=True)
    except requests.RequestException as exc:  # DNS, timeout, connexion refusée…
        raise RuntimeError(f"le portail n'a pas répondu ({type(exc).__name__})") from exc
    corps = r.text or ""
    if r.status_code in (401, 403, 429) or "datadome" in corps[:8000].lower():
        raise RuntimeError(f"le portail bloque la lecture automatique (HTTP {r.status_code})")
    if r.status_code >= 400 or len(corps) < 500:
        raise RuntimeError(f"page illisible (HTTP {r.status_code})")
    return corps


class DepotPublierIn(BaseModel):
    rec: dict
    idu: str
    lon: float | None = None
    lat: float | None = None
    adresse_exacte: str
    agence_nom: str


class InteresseIn(BaseModel):
    bien_id: int


@router.get("/admin/radar/depot-agence/etat")
def radar_depot_agence_etat(request: Request) -> dict:
    """SECTEUR-1 (S5) — l'endpoint est ADMIN (`exiger_admin`) : s'il répond, l'appelant EST admin →
    `admin: true`. Le parcours « Publier une annonce » est TOUJOURS montré à l'admin (pour tester sans
    toucher la config), avec la mention « drapeau fermé » quand `actif` est false ; les CLIENTS, eux, ne
    voient rien tant que le drapeau est fermé (leur propre porte `radar_interesse`)."""
    from ..api.auth import exiger_admin
    from ..config import get_settings
    exiger_admin(request)
    return {"actif": bool(get_settings().radar_depot_agence_actif), "admin": True}


@router.get("/radar/depot-agence/ouvert")
def radar_depot_agence_ouvert() -> dict:
    """SECTEUR-2b (U2) — état PUBLIC du drapeau, lisible par TOUS (sans garde admin) : l'écran Radar de
    l'app décide d'afficher ou non le bouton « Publier une annonce » aux CLIENTS. Ne révèle QUE le
    booléen d'ouverture (aucune donnée)."""
    from ..config import get_settings
    return {"ouvert": bool(get_settings().radar_depot_agence_actif)}


@router.post("/admin/radar/depot-agence/analyser")
def radar_depot_agence_analyser(body: DepotAnalyserIn, request: Request) -> dict:
    """ÉTAPE 1-2 — l'agence colle sa page (HTML) OU l'URL de son annonce ; le parseur RADAR-DEPOT-2
    reconstruit les champs pré-remplis. RETOURS-3 R3 — une URL bascule sur une lecture serveur one-shot."""
    from . import depot_agence, html_next
    _depot_admin_ou_ouvert(request)   # SECTEUR-2b (U2) — admin toujours, client si drapeau ouvert
    src = body.html or ""
    if _URL_RE.match(src):
        # chemin URL : fetch one-shot, puis parseur existant. Toute panne → message honnête + repli Cmd+S.
        try:
            page = _fetch_page_oneshot(src.strip())
        except RuntimeError as exc:
            return {"ok": False, "erreur": "url_bloquee",
                    "motif": f"Le portail refuse la lecture automatique de cette adresse — {exc}. {_DEPOT_REPLI}"}
        try:
            return {"ok": True, "records": depot_agence.analyser(page)}
        except html_next.NextDataError:
            # jamais l'erreur __NEXT_DATA__ brute face à une URL : la page est récupérée mais illisible.
            return {"ok": False, "erreur": "url_illisible",
                    "motif": ("La page a bien été récupérée, mais son contenu n'est pas exploitable "
                              f"automatiquement (protégé ou format inattendu). {_DEPOT_REPLI}")}
    # chemin HTML collé — inchangé (le motif __NEXT_DATA__ y reste pertinent : page incomplète/tronquée).
    try:
        return {"ok": True, "records": depot_agence.analyser(body.html)}
    except html_next.NextDataError as exc:
        return {"ok": False, "erreur": "next_data", "motif": str(exc)}


@router.post("/admin/radar/depot-agence/publier")
def radar_depot_agence_publier(body: DepotPublierIn, request: Request) -> dict:
    """ÉTAPE 3-4 — publier l'annonce déposée : rattachement CERTAIN depuis l'adresse, contenu confié."""
    from . import depot_agence
    _depot_admin_ou_ouvert(request)   # SECTEUR-2b (U2) — admin toujours, client si drapeau ouvert
    with session_scope() as db:
        try:
            out = depot_agence.publier(
                db, rec=body.rec, idu=body.idu, lon=body.lon, lat=body.lat,
                adresse_exacte=body.adresse_exacte, agence_nom=body.agence_nom)
            db.commit()
            return {"ok": True, **out}
        except ValueError as exc:
            return {"ok": False, "motif": str(exc)}


@router.post("/radar/interesse")
def radar_interesse(body: InteresseIn, request: Request) -> dict:
    """L'abonné clique « Intéressé » : ses coordonnées sont transmises à l'agence (LABUSE ne s'interpose
    pas). Gardé derrière le drapeau — rien ne s'ouvre au client tant qu'il est fermé."""
    from ..api.tenant import current_compte
    from . import depot_agence
    _porte_depot_agence()
    with session_scope() as db:
        try:
            out = depot_agence.enregistrer_interet(db, bien_id=body.bien_id, compte_id=current_compte(request))
            db.commit()
            return out
        except ValueError as exc:
            return {"ok": False, "motif": str(exc)}
