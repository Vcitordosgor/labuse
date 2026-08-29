"""RADAR P3 · C1 — lecture CÔTÉ CLIENT du Radar. Faits + lien, jamais le contenu de l'annonce.

Un client ne voit QUE des biens VALIDÉS (`pige_faits.valide_at IS NOT NULL`) — les brouillons de
l'intake admin n'existent pas pour lui. Statuts montrés par défaut : `active` + `en_vente_longue` ;
les autres restent accessibles en filtre. Le rattachement (P2) est servi tel quel (Sourcé/Estimé/Absent),
jamais un pin faussement sûr. Chaque clic SORTANT est logué dans `pige_clics` (usage dashboard Produit).
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from .tables import EV_SIGNALEMENT, journaliser

STATUTS_DEFAUT = ("active", "en_vente_longue")
PLAFOND_PAGE = 200          # RADAR-RECETTE-1 D2 — plafond DUR par page (borne `taille`/`limit`), explicite
TRIS = {
    "recentes": "b.date_premiere_saisie DESC",
    "prix_asc": "f.prix ASC NULLS LAST",
    "prix_desc": "f.prix DESC NULLS LAST",
    "anciennete": "COALESCE(b.date_publication, b.date_premiere_saisie::date) ASC",
    "baisses": "baisse DESC, b.date_premiere_saisie DESC",
}


def _where(filtres: dict) -> tuple[str, dict]:
    """Construit le WHERE client. VALIDÉ obligatoire ; statuts par défaut si non filtrés."""
    conds = ["f.valide_at IS NOT NULL"]
    p: dict = {}
    statuts = filtres.get("statuts") or list(STATUTS_DEFAUT)
    conds.append("b.statut = ANY(:statuts)")
    p["statuts"] = list(statuts)
    if filtres.get("commune"):
        conds.append("b.commune = :commune"); p["commune"] = filtres["commune"]
    if filtres.get("type_bien"):
        conds.append("b.type_bien = :type_bien"); p["type_bien"] = filtres["type_bien"]
    if filtres.get("prix_min") is not None:
        conds.append("f.prix >= :prix_min"); p["prix_min"] = filtres["prix_min"]
    if filtres.get("prix_max") is not None:
        conds.append("f.prix <= :prix_max"); p["prix_max"] = filtres["prix_max"]
    if filtres.get("surface_hab_min") is not None:
        conds.append("f.surface_hab >= :sh_min"); p["sh_min"] = filtres["surface_hab_min"]
    if filtres.get("surface_hab_max") is not None:
        conds.append("f.surface_hab <= :sh_max"); p["sh_max"] = filtres["surface_hab_max"]
    if filtres.get("surface_terrain_min") is not None:
        conds.append("f.surface_terrain >= :st_min"); p["st_min"] = filtres["surface_terrain_min"]
    if filtres.get("surface_terrain_max") is not None:
        conds.append("f.surface_terrain <= :st_max"); p["st_max"] = filtres["surface_terrain_max"]
    if filtres.get("particulier_pro"):
        conds.append("f.particulier_pro = :pp"); p["pp"] = filtres["particulier_pro"]
    if filtres.get("periode_debut"):
        conds.append("COALESCE(b.date_publication, b.date_premiere_saisie::date) >= :pdeb")
        p["pdeb"] = filtres["periode_debut"]
    if filtres.get("periode_fin"):
        conds.append("COALESCE(b.date_publication, b.date_premiere_saisie::date) <= :pfin")
        p["pfin"] = filtres["periode_fin"]
    ratt = filtres.get("rattache")            # 'oui' | 'non' | None (indifférent)
    if ratt == "oui":
        conds.append("b.idu IS NOT NULL")
    elif ratt == "non":
        conds.append("b.idu IS NULL")
    # RADAR-RECETTE-1 D2/D1c — filtre à-qualifier ('oui'|'non') : permet de lister les biens marqués
    # (ou de les exclure). Ils restent VISIBLES par défaut dans le flux, mais avec leur mention.
    aq = filtres.get("a_qualifier")
    if aq == "oui":
        conds.append("b.a_qualifier = true")
    elif aq == "non":
        conds.append("b.a_qualifier = false")
    return " AND ".join(conds), p


_SELECT = """
SELECT b.bien_id, b.commune, b.type_bien, b.est_copro, b.statut, b.idu,
       b.rattachement_niveau, b.rattachement_confiance, b.rattachement_etat, b.rattachement_pistes,
       b.rattachement_criteres, b.rattachement_humain,
       b.a_qualifier, b.a_qualifier_motifs,
       b.date_publication, b.date_premiere_saisie, b.date_derniere_confirmation,
       f.prix, f.pieces, f.surface_hab, f.surface_terrain, f.dpe_classe, f.dpe_conso, f.dpe_ges,
       f.particulier_pro, f.fraicheur_source, f.etiquettes,
       a.portail, a.url_sortante, a.annonce_id,
       EXISTS (SELECT 1 FROM pige_prix_historique h
               WHERE h.bien_id = b.bien_id AND h.nouveau_prix < h.ancien_prix) AS baisse,
       ST_X(p.centroid) AS lon, ST_Y(p.centroid) AS lat
FROM pige_biens b
JOIN pige_faits f ON f.bien_id = b.bien_id
LEFT JOIN LATERAL (SELECT portail, url_sortante, annonce_id FROM pige_annonces
                   WHERE bien_id = b.bien_id ORDER BY date_saisie DESC LIMIT 1) a ON true
LEFT JOIN parcels p ON p.idu = b.idu
"""


def _bien_row(r: dict) -> dict:
    """Un bien servi au client : faits + étiquettes + rattachement + lien. JAMAIS de contenu d'annonce."""
    rattache = r["idu"] is not None
    return {
        "bien_id": r["bien_id"], "commune": r["commune"], "type_bien": r["type_bien"],
        "est_copro": r["est_copro"], "statut": r["statut"],
        # RADAR-RECETTE-1 D1c — un bien incohérent reste VISIBLE dans le flux mais MARQUÉ (mention +
        # motifs consultables) ; il n'est jamais rattaché (idu NULL, cf. html_ingest).
        "a_qualifier": bool(r["a_qualifier"]), "a_qualifier_motifs": r["a_qualifier_motifs"] or [],
        "rattachement": ({"niveau": r["rattachement_niveau"], "idu": r["idu"],
                          "confiance": float(r["rattachement_confiance"]) if r["rattachement_confiance"] is not None else None}
                         if rattache else {"niveau": "absent", "idu": None, "confiance": None}),
        "coords": ([round(r["lon"], 6), round(r["lat"], 6)] if rattache and r["lon"] is not None else None),
        "faits": {"prix": r["prix"], "pieces": r["pieces"], "surface_hab": _num(r["surface_hab"]),
                  "surface_terrain": _num(r["surface_terrain"]), "dpe_classe": r["dpe_classe"],
                  "dpe_conso": r["dpe_conso"], "dpe_ges": r["dpe_ges"], "particulier_pro": r["particulier_pro"]},
        "etiquettes": r["etiquettes"] or {},
        "fraicheur_source": r["fraicheur_source"],
        "date_publication": r["date_publication"].isoformat() if r["date_publication"] else None,
        "date_saisie": r["date_premiere_saisie"].isoformat() if r["date_premiere_saisie"] else None,
        "date_derniere_confirmation": r["date_derniere_confirmation"].isoformat() if r["date_derniere_confirmation"] else None,
        "portail": r["portail"], "url_sortante": r["url_sortante"], "annonce_id": r["annonce_id"],
        "baisse": bool(r["baisse"]),
    }


def _num(v):
    return float(v) if v is not None else None


def lister(db: Session, *, filtres: dict, tri: str = "recentes", page: int = 1, taille: int = 50) -> dict:
    where, p = _where(filtres or {})
    order = TRIS.get(tri, TRIS["recentes"])
    n_total = db.execute(text(
        f"SELECT count(*) FROM pige_biens b JOIN pige_faits f ON f.bien_id=b.bien_id WHERE {where}"),
        p).scalar() or 0
    # « carte = rattachés seulement » : compteur explicite pour l'UI (pins).
    n_rattaches = db.execute(text(
        f"SELECT count(*) FROM pige_biens b JOIN pige_faits f ON f.bien_id=b.bien_id "
        f"WHERE {where} AND b.idu IS NOT NULL"), p).scalar() or 0
    # RADAR-RECETTE-1 D2 — le plafond par page est EXPLICITE (jamais un « 50 » muet) : `taille` demandée
    # est bornée à PLAFOND_PAGE, et la réponse dit combien de biens existent (n_total) vs combien sont
    # servis (n_servi), plus un drapeau `tronquee` pour qu'un appelant SACHE qu'il n'a pas tout.
    taille = max(1, min(PLAFOND_PAGE, taille))
    offset = max(0, (page - 1) * taille)
    rows = db.execute(text(f"{_SELECT} WHERE {where} ORDER BY {order} LIMIT :lim OFFSET :off"),
                      {**p, "lim": taille, "off": offset}).mappings().all()
    n_servi = len(rows)
    return {"biens": [_bien_row(dict(r)) for r in rows], "n_total": n_total,
            "n_servi": n_servi, "n_rattaches": n_rattaches, "page": page, "taille": taille,
            "plafond": PLAFOND_PAGE, "tronquee": (offset + n_servi) < n_total, "tri": tri}


def detail(db: Session, bien_id: int) -> dict | None:
    """Détail d'un bien VALIDÉ : faits + historique de prix + candidates (si Estimé). None sinon."""
    r = db.execute(text(f"{_SELECT} WHERE b.bien_id = :b AND f.valide_at IS NOT NULL"),
                   {"b": bien_id}).mappings().first()
    if not r:
        return None
    bien = _bien_row(dict(r))
    bien["historique_prix"] = [
        {"date": h["date_constat"].isoformat() if h["date_constat"] else None,
         "ancien": h["ancien_prix"], "nouveau": h["nouveau_prix"]}
        for h in db.execute(text(
            "SELECT date_constat, ancien_prix, nouveau_prix FROM pige_prix_historique "
            "WHERE bien_id = :b ORDER BY date_constat, id"), {"b": bien_id}).mappings()]
    # RADAR-HTML (Lot 3) — l'état de rattachement (rattachee|piste|non_rattachee) et les candidates
    # de PISTE sont servis au DÉTAIL (la carte, elle, ne pinne que les rattachés — cf. _bien_row).
    # C'est ce qui allume le bouton « Instruire cette annonce » sur une piste, sans automatisme.
    bien["rattachement_etat"] = r["rattachement_etat"] or ("rattachee" if r["idu"] else "non_rattachee")
    bien["pistes"] = r["rattachement_pistes"] or []
    # RATTACHEMENT-V2 — les critères convergents (pourquoi RATTACHÉE) + le drapeau « rattaché à la main ».
    bien["rattachement_criteres"] = r["rattachement_criteres"] or []
    bien["rattachement_humain"] = bool(r["rattachement_humain"])
    return bien


def enregistrer_clic(db: Session, *, compte_id: int | None, bien_id: int,
                     annonce_id: int | None = None) -> int:
    """Loggue un clic SORTANT (vers le portail) dans pige_clics → « usage par outil » du dashboard
    Produit. `annonce_id` déduit du bien si absent. Retourne l'id du clic."""
    portail = db.execute(text(
        "SELECT portail, annonce_id FROM pige_annonces WHERE "
        "(annonce_id = :aid OR :aid IS NULL) AND bien_id = :b ORDER BY date_saisie DESC LIMIT 1"),
        {"aid": annonce_id, "b": bien_id}).mappings().first()
    return db.execute(text(
        "INSERT INTO pige_clics (compte_id, bien_id, annonce_id, portail) "
        "VALUES (:c, :b, :a, :p) RETURNING id"),
        {"c": compte_id, "b": bien_id,
         "a": annonce_id or (portail["annonce_id"] if portail else None),
         "p": portail["portail"] if portail else None}).scalar() or 0


def signaler(db: Session, *, compte_id: int | None, bien_id: int, motif: str = "") -> int:
    """Signalement client (« annonce retirée / erreur ») → événement `pige.signalement_client` qui
    remonte le bien en TÊTE de la file de re-vérif admin. NE change JAMAIS le statut (anti-abus) :
    il alerte Vic, c'est tout. Retourne l'id de l'événement."""
    commune = db.execute(text("SELECT commune FROM pige_biens WHERE bien_id = :b"),
                         {"b": bien_id}).scalar()
    return journaliser(
        db, EV_SIGNALEMENT, f"Signalement client — bien #{bien_id} ({commune or '?'})",
        detail=(motif or "annonce retirée / erreur")[:200], compte_id=None,
        dedup=f"pige:signalement:{bien_id}:{compte_id or 'anon'}")
