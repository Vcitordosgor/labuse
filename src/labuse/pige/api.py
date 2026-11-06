"""RADAR P1 · V3 — endpoints ADMIN de la page Radar (réservés au compte pilote, comme le reste).

Câble les fonctions V2 (extraction/intake) : dépôt d'une capture, file d'extraction (brouillons),
validation, file de re-vérification priorisée à deux niveaux, arbre de check quotidien. Aucune
donnée d'annonce republiée : on sert des FAITS + le lien sortant, jamais photo/titre/texte.
"""
from __future__ import annotations

import base64
import logging
import math

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel
from sqlalchemy import text

from ..db import engine, session_scope
from . import intake
from .tables import EV_BAISSE_PRIX, EV_STATUT_CHANGE, journaliser

router = APIRouter(tags=["radar"])
log = logging.getLogger("labuse.pige.api")

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


# ══════════════ RADAR-AUTO-1 (Lot A) — capture AUTOMATIQUE par l'extension (Mac de Vic) ══════════════
# Le navigateur de Vic fait ce que Vic fait, à rythme humain. Ces trois endpoints portent un jeton DÉDIÉ
# (en-tête X-Radar-Token = LABUSE_RADAR_TOKEN), JAMAIS le mot de passe admin — un secret révocable qui
# n'ouvre aucune session. Une session admin valide passe aussi (pour tester depuis le dashboard).

import hmac as _hmac


def _radar_token_ok(request: Request) -> bool:
    """Vrai si l'appel porte le jeton Radar (X-Radar-Token) OU une session admin. Fail-closed : sans
    jeton configuré (LABUSE_RADAR_TOKEN vide) et sans session admin, on refuse."""
    from ..config import get_settings
    attendu = (get_settings().radar_token or "").strip()
    fourni = (request.headers.get("x-radar-token") or "").strip()
    if attendu and fourni and _hmac.compare_digest(fourni, attendu):
        return True
    return _est_admin(request)   # session admin (pilote/admin) autorisée pour les tests


def _exiger_radar(request: Request) -> None:
    if not _radar_token_ok(request):
        from fastapi import HTTPException
        raise HTTPException(401, "jeton Radar requis (en-tête X-Radar-Token) ou session administrateur")


_PASSES = ("nouvelles", "relecture", "confirmation")


class CaptureIn(BaseModel):
    passe: str
    url: str = ""
    page: int = 1
    html: str
    captured_at: str
    # RADAR-FIX-2 (Lot A) — déclencheur de la soirée : auto (alarme) | manuel (bouton) | test (recette).
    source: str = "auto"


class ConfirmationIn(BaseModel):
    list_id: int
    verdict: str
    # RADAR-FIX-3 — PREUVE POSITIVE du retrait. Un bien n'est retiré que sur preuve :
    #   « expiree »   = page « cette annonce n'est plus disponible / supprimée / désactivée » reconnue ;
    #   « http_404 »  = vraie page d'erreur « page introuvable » du portail.
    # Toute autre valeur (None, « bloquee », « vide », « redirige »…) = PAS une preuve → non vérifiée.
    preuve: str | None = None
    url: str = ""
    http_status: int | None = None


class ConfirmationBatchIn(BaseModel):
    """Toute une PASSE de confirmation en un envoi : c'est l'unité sur laquelle s'applique le garde-fou
    des 30 %. L'extension ouvre chaque lien, classe la page, puis dépose le lot entier."""
    items: list[ConfirmationIn]
    captured_at: str | None = None   # défaut = jour Réunion (clé d'idempotence de la passe)


class JournalIn(BaseModel):
    """RADAR-FIX-NU3-4 (K-RAD-04) — COMPTE-RENDU de fin de soirée posté par l'extension (succès, échec,
    ou veille du Mac détectée). Jusqu'ici le journal de passe ne vivait que dans le `chrome.storage` du
    navigateur : une nuit RATÉE ne laissait aucune trace active côté serveur. Désormais chaque soirée,
    même échouée, dépose son compte-rendu — lisible dans l'admin Radar."""
    captured_at: str
    statut: str = "ok"            # ok | echec
    source: str = "auto"          # auto | manuel | test
    resume: str = ""              # la ligne lisible (identique au popup de l'extension)
    veille_minutes: int = 0       # > 0 = le Mac a dormi pendant la fenêtre (durée estimée)


_SOURCES = ("auto", "manuel", "test")

# RADAR-FIX-3 — un retrait EXIGE une de ces preuves positives. Sans preuve, on ne retire jamais :
# page bloquée, vide, illisible ou redirigée = « non vérifiée », comptée à part, zéro écriture de statut.
PREUVES_RETRAIT = ("expiree", "http_404")
# Garde-fou : une passe qui veut retirer PLUS de 30 % des biens qu'elle a vérifiés n'écrit AUCUN retrait
# et se signale en anomalie (c'est la signature d'un blocage/captcha pris pour des suppressions de masse :
# 60/60 le 28/10, 107/107 le 26/09). Plancher : en-dessous de 5 liens vérifiés le ratio ne déclenche pas
# (une petite passe « tout expiré » prouvé reste légitime).
SEUIL_ANOMALIE_RETRAIT = 0.30
PLANCHER_PASSE_GARDE = 5


def _upsert_passe(db, passe: str, captured_at: str, source: str = "auto", **inc) -> None:
    """Agrège une passe (nouvelles|relecture|confirmation) au fil des pages, idempotent sur
    (passe, captured_at) : +1 page et cumul des compteurs fournis. `source` (RADAR-FIX-2) grave le
    déclencheur de la soirée (auto|manuel|test) ; toutes les pages d'un même run le partagent, donc
    la 1ʳᵉ page pose la valeur et le conflit ne l'écrase pas."""
    src = source if source in _SOURCES else "auto"
    cols = ("n_pages", "n_nouvelles", "n_maj", "n_prix_modifies", "n_supprimees",
            "n_hors_perimetre", "n_non_verifiees")
    vals = {c: int(inc.get(c, 0)) for c in cols}
    set_sql = ", ".join(f"{c} = pige_passes.{c} + EXCLUDED.{c}" for c in cols)
    db.execute(text(
        f"INSERT INTO pige_passes (passe, captured_at, source, {', '.join(cols)}) "
        f"VALUES (:p, CAST(:ca AS timestamptz), :src, {', '.join(':'+c for c in cols)}) "
        f"ON CONFLICT (passe, captured_at) DO UPDATE SET {set_sql}, updated_at = now()"),
        {"p": passe, "ca": captured_at, "src": src, **vals})


@router.post("/admin/radar/capture")
def radar_capture(body: CaptureIn, request: Request) -> dict:
    """Une PAGE de résultats capturée par l'extension. Même tuyau que /deposer-html (html_ingest), plus
    l'agrégation de la PASSE (une ligne de journal par passe, rafraîchie) et — passe « nouvelles » — la
    fraîcheur de la source + son mode `auto_quotidien`. Repli dégradé accepté et DIT (provenance)."""
    from . import html_ingest, html_next
    from .tables import journaliser_passe
    _exiger_radar(request)
    passe = body.passe if body.passe in _PASSES else None
    if passe not in ("nouvelles", "relecture"):
        return {"ok": False, "motif": f"passe « {body.passe} » invalide pour /capture (nouvelles|relecture)"}
    with session_scope() as db:
        try:
            r = html_ingest.ingester(db, body.html, nom_fichier=f"{passe} · page {body.page}")
        except html_next.NextDataError as exc:
            return {"ok": False, "erreur": "next_data", "motif": str(exc)}
        except html_ingest.DepotStockageError as exc:
            return {"ok": False, "erreur": "stockage", "motif": str(exc)}
        prix_mod = int(db.execute(text(
            "SELECT count(*) FROM event_log WHERE kind IN ('pige.baisse_prix','pige.hausse_prix') "
            "AND ts >= CAST(:ca AS timestamptz)"), {"ca": body.captured_at}).scalar() or 0)
        _upsert_passe(db, passe, body.captured_at, source=body.source, n_pages=1,
                      n_nouvelles=r["nb_nouvelles"], n_maj=r["nb_maj"], n_hors_perimetre=r["nb_hors_perimetre"])
        p = db.execute(text(
            "SELECT n_pages, n_nouvelles, n_maj, n_hors_perimetre FROM pige_passes "
            "WHERE passe = :p AND captured_at = CAST(:ca AS timestamptz)"),
            {"p": passe, "ca": body.captured_at}).mappings().first() or {}
        if passe == "nouvelles":
            titre = f"Radar — nouvelles · {p.get('n_pages',1)} page(s)"
            detail = (f"{p.get('n_nouvelles',0)} annonce(s) nouvelle(s), {p.get('n_maj',0)} remontée(s)"
                      + (f", {p.get('n_hors_perimetre',0)} hors périmètre" if p.get('n_hors_perimetre') else ""))
            # source en mode auto_quotidien + fraîcheur (enregistrer_fraicheur l'a déjà posée à l'ingestion).
            db.execute(text("UPDATE data_sources SET mode_remplissage = 'auto_quotidien', "
                            "cadence_attendue_jours = 1 WHERE name = 'Radar (pige d''annonces)'"))
        else:
            titre = f"Radar — relecture · {p.get('n_pages',1)} page(s)"
            detail = f"{p.get('n_maj',0)} annonce(s) revue(s), {prix_mod} prix modifié(s) aujourd'hui"
        # RADAR-FIX-2 (Lot A) — la SIGNATURE du déclencheur dans le journal : une capture « auto » est
        # partie seule (l'alarme du soir), « manuel » = bouton, « test » = recette. C'est ce que l'audit
        # cherchait et ne trouvait pas.
        src = body.source if body.source in _SOURCES else "auto"
        detail = f"{detail} · déclenchée {src}"
        journaliser_passe(db, passe, titre, detail, dedup=f"pige:passe:{passe}:{body.captured_at}")
        db.commit()
    return {"ok": True, "passe": passe, "page": body.page, **{k: r[k] for k in
            ("nb_annonces", "nb_nouvelles", "nb_maj", "nb_hors_perimetre", "nb_a_qualifier",
             "provenance", "mode")}}


@router.get("/admin/radar/etat")
def radar_etat(request: Request) -> dict:
    """État servi à l'extension : dernière capture, les annonces ACTIVES (list_id, prix, last_seen_at)
    pour comparer, et les annonces À CONFIRMER (actives non vues depuis 8 j) avec leur lien."""
    _exiger_radar(request)
    with engine().begin() as c:
        derniere = c.execute(text("SELECT max(captured_at) FROM pige_passes")).scalar()
        if derniere is None:
            derniere = c.execute(text("SELECT max(last_seen_at) FROM pige_biens")).scalar()
        actives = [dict(r) for r in c.execute(text(
            "SELECT b.bien_id, a.list_id, f.prix, b.last_seen_at "
            "FROM pige_biens b JOIN pige_faits f ON f.bien_id = b.bien_id "
            "LEFT JOIN pige_annonces a ON a.bien_id = b.bien_id "
            "WHERE b.statut IN ('active','en_vente_longue') AND f.valide_at IS NOT NULL "
            "ORDER BY b.last_seen_at ASC NULLS FIRST LIMIT 5000")).mappings()]
        # NU5-FIX-1 (D-F1) — les biens « à revérifier » (`a_reverifier`) sont AUSSI servis à la passe
        # de confirmation, SANS condition d'ancienneté : c'est le chemin par lequel les 88 biens
        # retirés à tort le 26/09 (remis en `a_reverifier` par le geste prod) seront re-vérifiés un à
        # un — présents → réactivés (`active`), vraiment partis → retirés sous la garde des 30 %.
        a_confirmer = [dict(r) for r in c.execute(text(
            "SELECT a.list_id, a.url_sortante AS url FROM pige_biens b "
            "JOIN pige_annonces a ON a.bien_id = b.bien_id "
            "WHERE b.statut = 'a_reverifier' "
            "   OR (b.statut IN ('active','en_vente_longue') "
            "       AND (b.last_seen_at IS NULL OR b.last_seen_at < now() - interval '8 days')) "
            "ORDER BY (b.statut = 'a_reverifier') DESC, b.last_seen_at ASC NULLS FIRST LIMIT 500")).mappings()]
    for r in actives:
        r["last_seen_at"] = r["last_seen_at"].isoformat() if r["last_seen_at"] else None
    return {"derniere_capture_at": derniere.isoformat() if derniere else None,
            "actives": actives, "a_confirmer": a_confirmer}


def _classer_confirmation(item: ConfirmationIn) -> str:
    """Classe UN lien vérifié, côté serveur, sans jamais faire confiance au seul mot « supprimee » :
      · « presente »    → l'annonce est toujours là (re-vue) ;
      · « retrait »     → suppression PROUVÉE (verdict supprimee ET preuve positive) — le SEUL cas qui retire ;
      · « non_verifiee » → tout le reste : supprimee sans preuve, inconnue, page bloquée/vide/illisible/redirigée.
    C'est la règle gravée par RADAR-FIX-3 : on ne retire JAMAIS sur une page qu'on n'a pas pu lire."""
    if item.verdict == "presente":
        return "presente"
    if item.verdict == "supprimee" and item.preuve in PREUVES_RETRAIT:
        return "retrait"
    return "non_verifiee"


def _appliquer_confirmations(db, items: list[ConfirmationIn], jour: str,
                             *, autoriser_retrait: bool) -> dict:
    """Applique une passe de confirmation en UNE transaction. Preuve positive exigée pour retirer,
    garde-fou des 30 % sur l'ensemble de la passe, comptage séparé des « non vérifiées »."""
    from .tables import EV_STATUT_CHANGE, journaliser, journaliser_passe

    # Résolution des list_id → bien_id (on ignore proprement les inconnus, sans jamais rien écrire pour eux).
    classes: list[tuple[ConfirmationIn, str, dict]] = []
    inconnus = 0
    for it in items:
        bien = db.execute(text(
            "SELECT b.bien_id, b.commune, b.statut FROM pige_biens b "
            "JOIN pige_annonces a ON a.bien_id = b.bien_id WHERE a.list_id = :l LIMIT 1"),
            {"l": it.list_id}).mappings().first()
        if not bien:
            inconnus += 1
            continue
        classes.append((it, _classer_confirmation(it), dict(bien)))

    n_verifies = len(classes)
    retraits = [(it, b) for it, c, b in classes if c == "retrait"]
    presentes = [(it, b) for it, c, b in classes if c == "presente"]
    n_non_verifiees = sum(1 for _it, c, _b in classes if c == "non_verifiee")

    # Voie historique (un appel = un lien) : PAS de garde-fou possible → elle ne retire JAMAIS.
    # Un retrait prouvé arrivé par là est compté « non vérifiée » (il faudra une PASSE pour l'écrire).
    if not autoriser_retrait:
        n_non_verifiees += len(retraits)
        retraits = []

    # Garde-fou RADAR-FIX-3 : > 30 % de retraits sur la passe = anomalie → on n'écrit AUCUN retrait.
    taux = (len(retraits) / n_verifies) if n_verifies else 0.0
    anomalie = (autoriser_retrait and n_verifies >= PLANCHER_PASSE_GARDE
                and taux > SEUIL_ANOMALIE_RETRAIT)
    ecrire_retraits = autoriser_retrait and not anomalie

    # Les annonces TOUJOURS LÀ sont confirmées dans tous les cas (même en anomalie : c'est sans risque).
    for _it, bien in presentes:
        db.execute(text(
            "UPDATE pige_biens SET last_seen_at = now(), date_derniere_confirmation = now(), "
            "statut = CASE WHEN statut IN ('a_reverifier','en_vente_longue') THEN 'active' ELSE statut END "
            "WHERE bien_id = :b AND statut NOT IN ('retiree','vendue','retiree_sans_vente')"),
            {"b": bien["bien_id"]})

    n_retires = 0
    n_gardes_multi = 0
    if ecrire_retraits:
        for it, bien in retraits:
            bid = bien["bien_id"]
            # OPS-URGENCE-2 (mandat Vic) — GARDE MULTI-ANNONCES. Un bien listé sur plusieurs portails
            # (ou ré-listé) ne doit PAS être retiré parce qu'UNE de ses annonces a disparu : l'audit a
            # trouvé 18 biens « retiree » ayant pourtant une annonce RE-VUE après le retrait (ex.
            # #141/#146/#147 le 04/11 — annonce leboncoin partie, annonce bienici toujours active). Si
            # une AUTRE annonce du bien a été revue récemment, seule CETTE annonce est partie : on ne
            # retire pas le bien (il reste en vente). Un vrai retrait total sera confirmé quand TOUTES
            # ses annonces auront disparu.
            autre = db.execute(text(
                "SELECT 1 FROM pige_annonces WHERE bien_id = :b AND list_id <> :l "
                "  AND date_saisie > now() - interval '14 days' LIMIT 1"),
                {"b": bid, "l": it.list_id}).first()
            if autre:
                n_gardes_multi += 1
                continue
            db.execute(text("UPDATE pige_biens SET statut = 'retiree', retiree_le = COALESCE(retiree_le, now()) "
                            "WHERE bien_id = :b AND statut NOT IN ('vendue','retiree_sans_vente')"), {"b": bid})
            journaliser(db, EV_STATUT_CHANGE, f"Bien retiré (preuve positive) — #{bid} ({bien['commune']})",
                        detail=f"annonce {it.list_id} — preuve « {it.preuve} » (HTTP {it.http_status})",
                        dedup=f"pige:retiree:{bid}")
            n_retires += 1

    # Les retraits REFUSÉS par l'anomalie ne sont ni retirés ni comptés comme « non vérifiées » :
    # ils restent actifs et seront re-vérifiés à la passe suivante une fois le blocage passé.
    _upsert_passe(db, "confirmation", jour, n_pages=n_verifies, n_supprimees=n_retires,
                  n_non_verifiees=n_non_verifiees)
    p = db.execute(text("SELECT n_pages, n_supprimees, n_non_verifiees FROM pige_passes "
                        "WHERE passe = 'confirmation' AND captured_at = CAST(:ca AS timestamptz)"),
                   {"ca": jour}).mappings().first() or {}
    detail = (f"{p.get('n_supprimees',0)} retirée(s) sur preuve, "
              f"{p.get('n_non_verifiees',0)} non vérifiée(s)")
    if anomalie:
        detail += (f" · ANOMALIE : {len(retraits)}/{n_verifies} ({taux:.0%}) > "
                   f"{SEUIL_ANOMALIE_RETRAIT:.0%} — aucun retrait écrit (blocage probable)")
        journaliser(db, EV_STATUT_CHANGE,
                    f"Radar — passe de confirmation SUSPECTE ({taux:.0%} de retraits)",
                    detail=f"{len(retraits)}/{n_verifies} liens vus comme retirés — rien écrit, à re-vérifier",
                    dedup=f"pige:anomalie:confirmation:{jour}")
        # NU5-FIX-1 (D-F3) — la garde protège des faux retraits, mais si elle bloque 3 NUITS de suite,
        # les VRAIS retraits ne sont plus captés : on alerte l'exploitation ([URGENT] admin, une fois +
        # rappel/jour via l'incident), signe d'un blocage portail (DataDome/captcha) à lever.
        nuits_bloquees = db.execute(text(
            "SELECT count(DISTINCT (ts AT TIME ZONE 'Indian/Reunion')::date) "
            "FROM event_log WHERE dedup LIKE 'pige:anomalie:confirmation:%' "
            "  AND ts > now() - interval '3 days'")).scalar() or 0
        if nuits_bloquees >= 3:
            try:
                from .. import ops_alertes
                ops_alertes.signaler(
                    db, "radar:confirmation-bloquee",
                    f"Radar — confirmation des retraits bloquée {nuits_bloquees} nuits de suite",
                    f"La garde des 30 % refuse tout retrait depuis {nuits_bloquees} nuits "
                    f"(dernière passe : {len(retraits)}/{n_verifies} liens vus retirés, {taux:.0%}). "
                    "Les vrais retraits ne sont plus captés — vérifier l'accès aux portails "
                    "(blocage DataDome / captcha probable).", lien="/admin")
            except Exception:  # noqa: BLE001 — l'alerte qui rate ne casse pas la passe
                log.warning("D-F3 : alerte « confirmation bloquée » impossible", exc_info=True)
    journaliser_passe(db, "confirmation",
                      f"Radar — confirmation · {p.get('n_pages',n_verifies)} lien(s) vérifié(s)",
                      detail, dedup=f"pige:passe:confirmation:{jour}")
    db.commit()
    return {"ok": True, "n_verifies": n_verifies, "n_retires": n_retires,
            "n_non_verifiees": n_non_verifiees, "list_id_inconnus": inconnus,
            "n_gardes_multi_annonces": n_gardes_multi,
            "anomalie": anomalie, "taux_retrait": round(taux, 4)}


@router.post("/admin/radar/confirmation")
def radar_confirmation(body: ConfirmationIn, request: Request) -> dict:
    """Verdict d'UN lien (voie historique, un appel = un lien). RADAR-FIX-3 : cette voie NE RETIRE PLUS
    rien — un retrait ne peut venir que d'une PASSE entière (/confirmation-batch) où s'applique le
    garde-fou des 30 %. `presente` confirme l'annonce active ; tout verdict de suppression est compté
    « non vérifiée » (voie sans garde-fou, donc jamais d'écriture de retrait). Le retrait HUMAIN reste
    `/admin/radar/retiree`."""
    from ..tz import today_reunion
    _exiger_radar(request)
    with session_scope() as db:
        if not db.execute(text(
                "SELECT 1 FROM pige_annonces WHERE list_id = :l LIMIT 1"),
                {"l": body.list_id}).first():
            return {"ok": False, "motif": "list_id inconnu"}
        res = _appliquer_confirmations(db, [body], today_reunion().isoformat(),
                                       autoriser_retrait=False)
    return {"ok": True, "list_id": body.list_id, "verdict": body.verdict,
            "retire": res["n_retires"] > 0, "non_verifiee": res["n_non_verifiees"] > 0}


@router.post("/admin/radar/confirmation-batch")
def radar_confirmation_batch(body: ConfirmationBatchIn, request: Request) -> dict:
    """La PASSE de confirmation en un envoi (l'extension). C'est l'unité du garde-fou des 30 % :
    si plus de 30 % des liens vérifiés sont vus comme retirés, AUCUN retrait n'est écrit et la passe
    est signalée en anomalie. Seuls les retraits PROUVÉS (preuve « expiree » ou « http_404 ») retirent."""
    from ..tz import today_reunion
    _exiger_radar(request)
    jour = body.captured_at or today_reunion().isoformat()
    with session_scope() as db:
        res = _appliquer_confirmations(db, body.items, jour, autoriser_retrait=True)
    return res


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
    """File de re-vérification PRIORISÉE : les NON RATTACHÉES d'abord (S5 — celles qui manquent encore
    leur parcelle, à rattacher en priorité), puis suivies par un client (watched_parcels sur l'idu
    rattaché), proches du seuil de vente longue (90 j), enfin les plus anciennes non confirmées."""
    from ..api.auth import exiger_admin
    exiger_admin(request)
    with engine().begin() as c:
        rows = [dict(r) for r in c.execute(text(
            f"""SELECT b.bien_id, b.commune, b.type_bien, b.statut, f.prix, a.portail, a.url_sortante,
                      b.date_derniere_confirmation, b.date_publication,
                      (b.idu IS NULL) AS non_rattachee,
                      EXISTS (SELECT 1 FROM watched_parcels w WHERE w.idu = b.idu) AS suivi_client,
                      (b.date_publication IS NOT NULL
                       AND b.date_publication <= current_date - {SEUIL_VENTE_LONGUE_J}) AS proche_longue
               FROM pige_biens b JOIN pige_faits f ON f.bien_id = b.bien_id
               LEFT JOIN pige_annonces a ON a.bien_id = b.bien_id
               WHERE f.valide_at IS NOT NULL AND b.statut IN ('active','en_vente_longue','a_reverifier')
               ORDER BY non_rattachee DESC, suivi_client DESC, proche_longue DESC,
                        b.date_derniere_confirmation ASC
               LIMIT 200""")).mappings()]
    for r in rows:
        for k in ("date_derniere_confirmation", "date_publication"):
            r[k] = r[k].isoformat() if r[k] else None
        # RADAR-4 — le rattachement AUTOMATIQUE est retiré (plus de cascade, de pistes ni de score de
        # confiance). Une annonce NON RATTACHÉE le reste jusqu'au geste admin « C'est cette parcelle »
        # (saisie manuelle de l'IDU, `/admin/radar/rattacher-humain`). Aucune suggestion automatique.
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


@router.post("/admin/radar/journal")
def radar_journal(body: JournalIn, request: Request) -> dict:
    """RADAR-FIX-NU3-4 (K-RAD-04) — reçoit le compte-rendu de la soirée de l'extension et le grave dans
    l'event_log (kind EV_CAPTURE, dedup `pige:soiree:<jour Réunion>` — UNE ligne par soir, rafraîchie, via
    `journaliser_passe`). Une soirée qui échoue ou tombe sur un Mac endormi laisse ainsi une trace active,
    servie par `/admin/radar/check` (`dernier_journal`). Même porte/jeton que les autres endpoints Radar."""
    from .tables import journaliser_passe
    _exiger_radar(request)
    statut = "echec" if (body.statut or "").strip() == "echec" else "ok"
    jour = (body.captured_at or "")[:10] or "?"
    titre = "Radar — compte-rendu de la soirée" + (" ⚠ échec" if statut == "echec" else "")
    detail = (body.resume or "").strip() or ("échec de la passe" if statut == "echec" else "passe terminée")
    if body.veille_minutes and body.veille_minutes > 0:
        detail += f" · Mac en veille ~{int(body.veille_minutes)} min"
    with session_scope() as db:
        journaliser_passe(db, "soiree", titre, detail, dedup=f"pige:soiree:{jour}")
        db.commit()
    return {"ok": True, "statut": statut, "jour": jour}


@router.get("/admin/radar/check")
def radar_check(request: Request) -> dict:
    """Arbre de check quotidien : compteurs du rituel + drapeau intake vide depuis 48 h."""
    from ..api.auth import exiger_admin
    exiger_admin(request)
    # CIRCUIT-2 lot 1.6 — la file d'extraction est comptée par le moteur nommé
    # `plateforme_compteurs` (id registre n_depots_a_verifier) : ce robinet appelle.
    from ..registre.moteurs.plateforme import depots_a_verifier
    with engine().begin() as c:
        q = lambda s: c.execute(text(s)).scalar() or 0
        file_extraction = depots_a_verifier(c)
        # RETOURS-8 (R5) — les deux chiffres de tête : annonces EN VIE (biens validés, actifs) et à
        # RATTACHER. RADAR-4 — « à rattacher » = biens validés, en vente, NON rattachés (idu NULL), à
        # rattacher À LA MAIN par l'admin (plus de pistes auto ni d'état « piste »). Comptés ici, servis
        # à l'en-tête des onglets Radar (même périmètre que la file /admin/radar/a-rattacher).
        annonces_en_vie = q(
            "SELECT count(*) FROM pige_biens b JOIN pige_faits f ON f.bien_id = b.bien_id "
            "WHERE f.valide_at IS NOT NULL AND b.statut IN ('active','en_vente_longue','a_reverifier')")
        a_rattacher = q(
            "SELECT count(*) FROM pige_biens b JOIN pige_faits f ON f.bien_id = b.bien_id "
            "WHERE f.valide_at IS NOT NULL AND b.idu IS NULL "
            "  AND b.statut IN ('active','en_vente_longue') "
            "  AND b.rattachement_humain = false AND b.a_qualifier = false")
        reverif_dues = q(
            "SELECT count(*) FROM pige_biens WHERE statut = 'a_reverifier'")
        nouveautes = q("SELECT count(*) FROM pige_biens WHERE date_premiere_saisie::date = current_date")
        en_vente_longue = q("SELECT count(*) FROM pige_biens WHERE statut = 'en_vente_longue'")
        baisses = q("SELECT count(*) FROM event_log WHERE kind = 'pige.baisse_prix' "
                    "AND ts::date = current_date")
        # CONNEXIONS-2 Lot 3 (KO-4) : le compteur lit la table UNIQUE `signalements` (fiche + annonce),
        # non traités — plus l'event_log du jour seul. L'admin les voit et les traite au dashboard.
        signalements = q("SELECT count(*) FROM signalements WHERE statut = 'nouveau'")
        derniere = c.execute(text("SELECT max(date_saisie) FROM pige_annonces")).scalar()
        # DASHBOARD-2 (Lot 4) — bilan du DERNIER dépôt (persistant, table pige_depots) : ce qui est
        # RÉELLEMENT stocké par dépôt (date, annonces lues, nouvelles, mises à jour, à qualifier).
        # La variante, les baisses de prix et le digest ne sont pas stockés par dépôt → non inventés.
        dep = c.execute(text(
            "SELECT date_depot, nom_fichier, nb_annonces, nb_nouvelles, nb_maj, nb_a_qualifier "
            "FROM pige_depots ORDER BY date_depot DESC LIMIT 1")).mappings().first()
        dernier_depot = None if not dep else {
            "date_depot": dep["date_depot"].isoformat() if dep["date_depot"] else None,
            "nom_fichier": dep["nom_fichier"], "nb_annonces": dep["nb_annonces"],
            "nb_nouvelles": dep["nb_nouvelles"], "nb_maj": dep["nb_maj"], "nb_a_qualifier": dep["nb_a_qualifier"],
        }
        # OPS-NUIT-2 — LE compteur canonique de la nuit, par portail (pige_annonces, vérité par portail) :
        # le MÊME chiffre que le Tableau de bord et le résumé du matin. Avant, `capture_auto.nouvelles`
        # sommait pige_passes.n_nouvelles sur TOUTES les sources → un nombre divergent du reste.
        from .comptage_nuit import comptage_nuit as _comptage_nuit
        _cn = _comptage_nuit(c)
        # RADAR-FIX-NU3-4 (K-RAD-04) — dernier COMPTE-RENDU de soirée déposé par l'extension (succès,
        # échec, ou veille du Mac). C'est la trace qui manquait à une nuit ratée (/admin/radar/journal).
        journal = c.execute(text(
            "SELECT ts, titre, detail FROM event_log WHERE dedup LIKE 'pige:soiree:%' "
            "ORDER BY ts DESC LIMIT 1")).mappings().first()
        # DASHBOARD-2 (Lot 4) — « Le flux » : rattachées / total biens / paires DVF / copros non servies.
        # rattachées & paires lisent la MÊME source que Pilotage/Circuit (pige_biens) — compteur unique.
        biens = q("SELECT count(*) FROM pige_biens")
        flux = {
            "en_vie": annonces_en_vie,
            "biens": biens,
            "rattachees": q("SELECT count(*) FROM pige_biens WHERE idu IS NOT NULL"),
            "paires": q("SELECT count(*) FROM pige_biens WHERE statut = 'vendue'"),
            "copros_non_servies": q("SELECT count(*) FROM pige_biens WHERE est_copro = true"),
        }
    from datetime import datetime, timedelta, timezone
    vide_48h = derniere is None or derniere < datetime.now(tz=timezone.utc) - timedelta(hours=48)
    # RADAR-FIX-1 (3) — « aucune capture automatique depuis 26 h » → la tâche « Déposer Radar » (le Mac de
    # Vic était éteint, ou l'extension bloquée). 26 h = un jour + la marge du jitter du soir (0-3 h).
    # OPS-NUIT-2 — « nouvelles » = le compteur canonique de la nuit (pige_annonces, par portail), identique
    # partout ; les PAGES lues restent à part (activité de capture, jamais additionnée aux annonces).
    _cap_at = _cn.get("captured_at")
    capture_auto = None if not _cap_at else {
        "captured_at": _cap_at,
        "pages": int(_cn.get("pages") or 0),
        "nouvelles": int(_cn.get("nouvelles") or 0),
        "par_portail": _cn.get("par_portail") or [],
        "jour": _cn.get("jour"),
    }
    try:
        _cap_at_dt = datetime.fromisoformat(_cap_at) if _cap_at else None
    except (ValueError, TypeError):
        _cap_at_dt = None
    capture_auto_en_retard = _cap_at_dt is None or _cap_at_dt < datetime.now(tz=timezone.utc) - timedelta(hours=26)
    # RV2-V1 — état du répertoire de captures (écriture) exposé à l'admin : le défaut prod se voit
    # AVANT le premier dépôt, avec le chemin fautif nommé.
    from .tables import captures_dir_writable
    cap_ok, cap_detail = captures_dir_writable()
    return {
        "cible_minutes": 15,
        "file_extraction": file_extraction,
        # RETOURS-8 (R5) — les 4 chiffres de tête des onglets Radar.
        "annonces_en_vie": annonces_en_vie,
        "a_rattacher": a_rattacher,
        "reverif_dues": reverif_dues,
        "reverif_du_jour": nouveautes,            # cadence quotidienne du rituel
        "signalements_en_attente": signalements,
        "compteurs": {"nouveautes": nouveautes, "en_vente_longue": en_vente_longue, "baisses": baisses},
        "intake_vide_48h": bool(vide_48h),
        "derniere_saisie": derniere.isoformat() if derniere else None,
        "captures_dir_ok": cap_ok,
        "captures_dir": cap_detail,
        # DASHBOARD-2 (Lot 4) — bilan du dernier dépôt + « Le flux ».
        "dernier_depot": dernier_depot,
        "flux": flux,
        # RADAR-FIX-1 (3) — dernière capture AUTOMATIQUE (extension) + drapeau « À faire : Déposer Radar ».
        "capture_auto": capture_auto,
        "capture_auto_en_retard": bool(capture_auto_en_retard),
        # RADAR-FIX-NU3-4 (K-RAD-04) — dernier compte-rendu de soirée (succès/échec/veille), lisible à l'écran.
        "dernier_journal": None if not journal else {
            "ts": journal["ts"].isoformat() if journal["ts"] else None,
            "titre": journal["titre"], "detail": journal["detail"],
        },
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


@router.get("/admin/radar/a-rattacher")
def radar_a_rattacher(request: Request) -> dict:
    """RADAR-4 — file « à rattacher » (admin) : les biens validés, en vente, NON rattachés à une parcelle.
    Le rattachement AUTOMATIQUE est retiré (décision Vic : trop peu d'annonces rattachables) — plus de
    pistes, de cascade ni de score de confiance. L'admin ouvre l'annonce, identifie la parcelle lui-même
    et saisit l'IDU via « C'est cette parcelle » (`/admin/radar/rattacher-humain`). Simple lecture : les
    plus récents d'abord."""
    from ..api.auth import exiger_admin
    exiger_admin(request)
    with engine().begin() as c:
        rows = [dict(r) for r in c.execute(text(
            """SELECT b.bien_id, b.commune, b.type_bien, f.prix, f.surface_terrain, f.surface_hab,
                      f.declaratif, a.portail, a.url_sortante, b.district
               FROM pige_biens b JOIN pige_faits f ON f.bien_id = b.bien_id
               LEFT JOIN pige_annonces a ON a.bien_id = b.bien_id
               WHERE f.valide_at IS NOT NULL AND b.idu IS NULL
                 AND b.rattachement_humain = false AND b.a_qualifier = false
               ORDER BY b.date_premiere_saisie DESC LIMIT 100""")).mappings()]
    return {"file": rows, "n": len(rows)}


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
        # RADAR-2 (Lot 2) — le rattachement manuel vers une parcelle SUIVIE déclenche le mail immédiat
        # « parcelle suivie mise en vente » (même chemin/dédup que le digest — jamais un doublon).
        from . import digests
        notifies = digests.mise_en_vente_immediate(db, body.bien_id)
        db.commit()
    return {"ok": True, "bien_id": body.bien_id, "idu": body.idu, "etat": "rattachee", "humain": True,
            "mises_en_vente_notifiees": notifies}


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
    communes: list[str] | None = None    # RADAR-2 — « M'alerter » depuis Radar peut porter plusieurs communes
    type_bien: str | None = None
    prix_min: int | None = None          # RADAR-CATÉGORIE (T4) — le prix rejoint les critères de veille
    prix_max: int | None = None
    surface_min: float | None = None     # RADAR-2 — surface pertinente (terrain/habitable), modèle VEILLE-2
    surface_max: float | None = None
    surface_terrain_min: float | None = None
    surface_hab_min: float | None = None
    particulier_only: bool = False
    # RADAR-VEILLE-1 (V3) — plus de filtre d'événement : une veille notifie sur TOUT événement d'un bien
    # correspondant (nouvelle annonce, baisse, retour). Le mail (template 13) dit lequel a déclenché.


@router.post("/radar/veille")
def radar_veille_creer(body: VeilleIn, request: Request) -> dict:
    """Le client crée une veille Radar (ses critères). Alimente l'ALERTE veille de fin de journée."""
    from fastapi import HTTPException
    from ..api.tenant import current_compte
    from . import veille
    crit = {k: v for k, v in body.model_dump().items() if v not in (None, [], False)}
    cid = current_compte(request)
    with session_scope() as db:
        # RADAR-2 (retouches 2) — une alerte IDENTIQUE à une existante est refusée (409), pas dupliquée.
        if veille.existe_identique(db, cid, crit):
            raise HTTPException(409, "Vous avez déjà une alerte avec ces critères.")
        vid = veille.creer(db, compte_id=cid, criteria=crit)
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


@router.put("/radar/veille/{veille_id}")
def radar_veille_modifier(veille_id: int, body: VeilleIn, request: Request) -> dict:
    """VEILLE-3 — « Modifier » une alerte : remplace ses critères EN PLACE (même formulaire que la création).
    Refuse (409) si les nouveaux critères dupliquent une AUTRE alerte du compte (dédup excluant soi-même)."""
    from fastapi import HTTPException
    from ..api.tenant import current_compte
    from . import veille
    crit = {k: v for k, v in body.model_dump().items() if v not in (None, [], False)}
    cid = current_compte(request)
    with session_scope() as db:
        if veille.existe_identique(db, cid, crit, sauf_id=veille_id):
            raise HTTPException(409, "Vous avez déjà une autre alerte avec ces critères.")
        ok = veille.modifier(db, cid, veille_id, crit)
        db.commit()
    return {"ok": ok}


class VeilleRenommerIn(BaseModel):
    nom: str = ""


@router.patch("/radar/veille/{veille_id}")
def radar_veille_renommer(veille_id: int, body: VeilleRenommerIn, request: Request) -> dict:
    """RETOURS-11 A7 — renomme une veille Radar du compte (garde IDOR = celle de la suppression)."""
    from ..api.tenant import current_compte
    from . import veille
    with session_scope() as db:
        ok = veille.renommer(db, current_compte(request), veille_id, body.nom)
        db.commit()
    return {"ok": ok}


class PauseIn(BaseModel):
    en_pause: bool = True


@router.post("/radar/veille/{veille_id}/pause")
def radar_veille_pause(veille_id: int, body: PauseIn, request: Request) -> dict:
    """RADAR-2 (Lot 4) — met une alerte EN PAUSE (ou la reprend). Compte-scopé (même garde IDOR)."""
    from ..api.tenant import current_compte
    from . import veille
    with session_scope() as db:
        ok = veille.basculer_pause(db, current_compte(request), veille_id, body.en_pause)
        db.commit()
    return {"ok": ok, "en_pause": body.en_pause}


@router.get("/radar/alertes")
def radar_alertes(request: Request) -> dict:
    """RADAR-2 (Lot 4) — les alertes du compte, chacune avec ses critères et son nombre de « nouveaux
    depuis hier » (0 si en pause). Réutilise `_biens_du_jour` + `matche` (contrat partagé avec le digest)."""
    from ..api.tenant import current_compte
    from . import veille
    with session_scope() as db:
        return veille.apercu(db, current_compte(request))


@router.get("/radar/apercu")
def radar_apercu(request: Request) -> dict:
    """RADAR-2 (Lot 1) — le résumé chiffré RÉEL des deux portes du hub Radar : biens en vente + date de la
    dernière capture (porte Radar) ; parcelles suivies + alertes + nouveaux (porte Veille). Aucun calcul
    neuf : biens = même filtre que le flux client, capture = pige_passes, suivis = watched_parcels,
    alertes = `veille.apercu`."""
    from ..api.tenant import current_compte
    from . import client, veille
    cid = current_compte(request)
    with session_scope() as db:
        biens = client.compter(db)   # RADAR-2 (recette) — nombre canonique (= porte = marché = liste)
        capture = db.execute(text("SELECT max(captured_at) FROM pige_passes")).scalar()
        if capture is None:
            capture = db.execute(text("SELECT max(last_seen_at) FROM pige_biens")).scalar()
        suivis = db.execute(text(
            "SELECT count(*) FROM watched_parcels WHERE compte_id IS NOT DISTINCT FROM :c"),
            {"c": cid}).scalar() or 0
        ap = veille.apercu(db, cid)
    return {"biens_en_vente": int(biens), "derniere_capture_at": capture.isoformat() if capture else None,
            "suivis_n": int(suivis), "alertes_n": len(ap["alertes"]), "nouveaux_total": ap["nouveaux_total"]}


# ══════════════ RADAR P6 · D3 — onglet Marché (stats par commune, honnêteté statistique) ══════════════

@router.get("/radar/marche")
def radar_marche(request: Request) -> dict:
    """Statistiques Radar par commune (24 + total île). Chaque mesure porte son n ; < 5 = insuffisant."""
    from . import marche
    with session_scope() as db:
        return marche.stats(db)


@router.get("/radar/marche-tableau")
def radar_marche_tableau(request: Request, commune: str | None = None) -> dict:
    """RADAR-2 (Lot 3) — LE MARCHÉ (colonne de droite du Radar) : 4 chiffres maisons (demandé Radar vs acté
    DVF, écart), table par type, mouvements 30 j, écart par commune. Prix acté = moteur fiche commune,
    jamais recalculé à part ; écart servi au-delà de 30 annonces sinon « sous le seuil »."""
    from . import marche
    with session_scope() as db:
        return marche.tableau(db, commune=commune or None)


@router.get("/radar/biens/{bien_id}/vs-marche")
def radar_bien_vs_marche(bien_id: int, request: Request) -> dict:
    """RADAR-2 (recette) — « Ce bien face à son marché » : €/m² du bien vs médianes demandée/actée de sa
    commune et son type, ancienneté vs médiane, historique de prix. Sous 30 → « sous le seuil »."""
    from . import marche
    with session_scope() as db:
        return marche.bien_vs_marche(db, bien_id) or {"bien_id": bien_id, "introuvable": True}


@router.get("/radar/stats")
def radar_stats_endpoint(request: Request, commune: str | None = None, type_bien: str | None = None) -> dict:
    """RADAR-AUTO-1 (Lot E) — chiffres Radar « prix DEMANDÉS » d'une commune (ou île) et d'un type (ou
    tous) : actives, médiane €/m² demandé, baisses/30 j, délai médian de retrait. Appartements INCLUS.
    Servi à côté du DVF (prix de vente) dans l'outil Communes et la fiche §Marché — jamais confondus."""
    from . import marche
    with session_scope() as db:
        return marche.radar_stats(db, commune=commune, type_bien=type_bien)


# ══════════════ RADAR-VEILLE-1 (R3) — DÉPÔT AGENCE « Publier une annonce » (derrière drapeau) ══════════════
# Tout le parcours est FERMÉ par défaut (config.radar_depot_agence_actif) : question Hoguet en attente chez
# l'avocat de Vic. Drapeau OFF → 404 partout, rien ne s'ouvre. Admin seulement pour le dépôt.

def _porte_depot_agence() -> None:
    # CONNEXIONS-2 Lot 7.1 (N2) — le drapeau est désormais éditable au dashboard (réglage EN BASE,
    # relu à chaud), plus figé dans l'env. `reglages.depot_agence_actif` prime, défaut = env (fermé).
    from .. import reglages
    if not reglages.depot_agence_actif():
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


def _domaines_autorises() -> set[str]:
    """URGENCE-1 (NU-F-007) — LISTE BLANCHE des domaines fetchables : les portails connus de
    `portails.py` qui portent un préfixe d'URL (leboncoin.fr, seloger.com, pap.fr, logic-immo.com,
    bienici.com). Les slugs « agence »/« autre » (préfixe None) ne sont PAS fetchables : un site
    d'agence se dépose par copier-coller du HTML (repli Cmd+S), jamais par une requête serveur."""
    from urllib.parse import urlparse
    from .portails import PORTAILS
    out: set[str] = set()
    for meta in PORTAILS.values():
        pref = meta.get("prefixe_url")
        if not pref:
            continue
        h = (urlparse(pref).hostname or "").lower()
        if h.startswith("www."):
            h = h[4:]
        if h:
            out.add(h)
    return out


def _hote_autorise(host: str) -> bool:
    """L'hôte est-il un portail de la liste blanche (domaine exact ou sous-domaine) ?"""
    host = (host or "").lower().rstrip(".")
    return any(host == d or host.endswith("." + d) for d in _domaines_autorises())


def _resout_public(host: str) -> bool:
    """L'hôte résout-il UNIQUEMENT vers des adresses publiques ? False si résolution impossible OU si
    une adresse privée/loopback/lien-local/réservée/multicast apparaît (anti-SSRF : jamais 169.254.x,
    127.0.0.1, 10/8, 192.168/16, ::1, fd00::/8, etc.)."""
    import ipaddress
    import socket
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return False
    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
        except ValueError:
            return False
        if (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
                or ip.is_multicast or ip.is_unspecified):
            return False
    return True


def _valider_cible(url: str) -> None:
    """Valide une URL AVANT toute requête (SSRF fermé) : schéma http(s), hôte d'une liste blanche de
    portails, et aucune résolution vers une adresse interne/privée. Lève RuntimeError sinon."""
    from urllib.parse import urlparse
    p = urlparse(url)
    if p.scheme not in ("http", "https"):
        raise RuntimeError("schéma d'URL non autorisé")
    host = (p.hostname or "").lower()
    if not _hote_autorise(host):
        raise RuntimeError("hôte non autorisé (hors portails connus)")
    if not _resout_public(host):
        raise RuntimeError("l'adresse pointe sur un hôte interne/privé")


def _fetch_page_oneshot(url: str) -> str:
    """Lecture ONE-SHOT d'une URL d'annonce : une seule requête, headers navigateur, timeout court,
    AUCUN retry, AUCUNE boucle. Lève RuntimeError (message court) si le portail refuse — l'appelant en
    fait un motif honnête.

    URGENCE-1 (NU-F-007, SSRF) — l'hôte est VALIDÉ contre une liste blanche de portails ET interdit de
    résoudre vers une adresse privée/interne AVANT la requête ; les redirections ne sont PAS suivies
    (`allow_redirects=False`) — un 3xx renvoie le message « bloqué » plutôt que d'échapper à la liste
    blanche ou de pointer vers un hôte interne."""
    import requests
    cible = (url or "").strip()
    _valider_cible(cible)
    try:
        r = requests.get(cible, headers=_BROWSER_HEADERS, timeout=8, allow_redirects=False)
    except requests.RequestException as exc:  # DNS, timeout, connexion refusée…
        raise RuntimeError(f"le portail n'a pas répondu ({type(exc).__name__})") from exc
    if 300 <= r.status_code < 400:
        raise RuntimeError(f"le portail redirige la lecture automatique (HTTP {r.status_code})")
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
    from .. import reglages
    exiger_admin(request)
    return {"actif": reglages.depot_agence_actif(), "admin": True}


class DepotToggleIn(BaseModel):
    actif: bool


@router.post("/admin/radar/depot-agence/toggle")
def radar_depot_agence_toggle(body: DepotToggleIn, request: Request) -> dict:
    """CONNEXIONS-2 Lot 7.1 (N2) — l'admin OUVRE / FERME le dépôt agence DEPUIS LE DASHBOARD (réglage en
    base, relu à chaud par /etat, /ouvert et tous les écrans). Défaut = fermé. Bascule → immédiate."""
    from ..api.auth import exiger_admin
    from .. import reglages
    exiger_admin(request)
    reglages.set_bool(reglages.CLE_DEPOT_AGENCE, body.actif)
    return {"ok": True, "actif": body.actif}


@router.get("/radar/depot-agence/ouvert")
def radar_depot_agence_ouvert() -> dict:
    """SECTEUR-2b (U2) — état PUBLIC du drapeau, lisible par TOUS (sans garde admin) : l'écran Radar de
    l'app décide d'afficher ou non le bouton « Publier une annonce » aux CLIENTS. Ne révèle QUE le
    booléen d'ouverture (aucune donnée)."""
    from .. import reglages
    return {"ouvert": reglages.depot_agence_actif()}


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


# ─────────────────── ANNONCE-1/2 — outil « Analyser une annonce » (entrée LIEN) ───────────────────
# ANNONCE-2 — toute URL d'annonce Leboncoin porte un IDENTIFIANT numérique (list_id). On le reconnaît sur
# les formes courantes (…/ventes_immobilieres/{id}.htm, …/ad/ventes_immobilieres/{id}, avec ou sans query
# ?… ni ancre #…) pour chercher le bien DÉJÀ relevé par le Radar AVANT tout appel réseau à Leboncoin.
_LBC_ID_RE = _re.compile(r"\d{5,}")


def _list_id_from_url(url: str) -> int | None:
    """Identifiant d'annonce Leboncoin (list_id) extrait de l'URL — query (?…) et ancre (#…) IGNORÉS. On
    lit le DERNIER segment de chemin (où vit l'id, avec ou sans suffixe .htm) ; à défaut (id non terminal),
    repli sur la plus longue suite de ≥ 8 chiffres du chemin. None si l'URL ne porte pas d'identifiant
    (page de recherche, lien malformé) → l'appelant bascule sur le fetch one-shot."""
    chemin = url.split("?", 1)[0].split("#", 1)[0].rstrip("/")
    m = _LBC_ID_RE.search(chemin.rsplit("/", 1)[-1])
    if m:
        return int(m.group())
    suites = _re.findall(r"\d{8,}", chemin)
    return int(max(suites, key=len)) if suites else None


def _marche_commune(db, commune, type_bien, prix, surface_hab, surface_terrain) -> dict | None:
    """Écart au REPÈRE COMMUNE du bon type (idu=None : aucun rattachement parcelle → médiane commune),
    d'où une fiabilité « limitée » assumée. Partagé par les DEUX voies de l'entrée LIEN (relevé Radar et
    fetch one-shot) : un SEUL moteur de prix, aucune divergence de calcul. None si pas de €/m² calculable
    ou commune absente."""
    from . import signaux
    if not commune:
        return None
    ref = signaux._referentiel(db, commune, type_bien, idu=None)
    try:
        terrain_ref = (signaux._dvf_terrain(db, commune) or {}).get("eur_m2")
    except Exception:
        terrain_ref = None
    badge = signaux._badge(prix, type_bien, surface_hab, surface_terrain, ref, terrain_ref)
    if badge is None:
        return None
    return {**badge, "fiabilite": "limitee", "repere_perimetre": ref.get("perimetre"),
            "periode": ref.get("periode"), "meme_type": bool(ref.get("meme_type"))}


def _annonce_depuis_radar(db, list_id: int, url: str) -> dict | None:
    """ANNONCE-2 (lookup Radar D'ABORD) — le bien correspondant à cet identifiant a-t-il DÉJÀ été relevé
    par le Radar ? Si oui, le rapport est construit depuis les tables EXISTANTES (pige_annonces → bien →
    faits), SANS aucun appel à Leboncoin, et `relevé le` = date de CAPTURE Radar (fuseau Réunion). None si
    l'identifiant est inconnu du Radar → l'appelant bascule sur le fetch one-shot (repli ANNONCE-1)."""
    from ..tz import REUNION_TZ
    row = db.execute(text(
        "SELECT b.commune, b.type_bien, b.lat, b.lng, "
        "       b.date_premiere_saisie, b.date_derniere_confirmation, "
        "       f.prix, f.pieces, f.surface_hab, f.surface_terrain, f.prix_m2 "
        "FROM pige_annonces a "
        "JOIN pige_biens b ON b.bien_id = a.bien_id "
        "JOIN pige_faits f ON f.bien_id = b.bien_id "
        "WHERE a.list_id = :lid ORDER BY a.date_saisie DESC LIMIT 1"),
        {"lid": list_id}).mappings().first()
    if not row:
        return None
    commune = row["commune"]
    type_bien = row["type_bien"]
    prix = row["prix"]
    surface_hab = float(row["surface_hab"]) if row["surface_hab"] is not None else None
    surface_terrain = float(row["surface_terrain"]) if row["surface_terrain"] is not None else None
    # VRAIE date de relevé = capture Radar (jamais today). Convertie EXPLICITEMENT au fuseau Réunion
    # (ORF-17) même si la session SQL rend déjà l'heure Réunion — jamais `date.today()` naïf.
    cap = row["date_derniere_confirmation"] or row["date_premiere_saisie"]
    annonce = {
        "titre": None,                       # le Radar ne conserve pas le contenu d'annonce (doctrine « faits + lien »)
        "type": type_bien,
        "prix": prix,
        "surface_hab": surface_hab,
        "surface_terrain": surface_terrain,
        "pieces": row["pieces"],
        "prix_m2": row["prix_m2"],
        "commune": commune,
        "url": url,
        "releve_le": cap.astimezone(REUNION_TZ).date().isoformat() if cap else None,
        # Position portail (centroïde de quartier/commune) — centre la carte sur la commune, jamais un
        # rattachement parcelle (pont V2 écarté par le mandat, idu=None pour le repère de prix).
        "lat": row["lat"], "lng": row["lng"],
    }
    marche = _marche_commune(db, commune, type_bien, prix, surface_hab, surface_terrain)
    return {"ok": True, "annonce": annonce, "marche": marche}


def _commune_canonique(db, nom: str | None) -> str | None:
    """ANNONCE-5 (correctif « commune vide » La Possession) — ramène un nom de commune À LA CASSE
    CANONIQUE stockée (référentiel communes), insensible à la casse/espaces. Le flux LIEN peut recevoir
    « la possession » (Leboncoin) quand la base porte « La Possession » : un lookup EXACT en aval
    (cache contexte commune) manquait alors et le bloc commune sortait VIDE. On normalise À LA SOURCE."""
    if not nom or not nom.strip():
        return nom
    n = nom.strip()
    try:
        r = db.execute(text("SELECT nom FROM communes_referentiel WHERE lower(nom) = lower(:n) LIMIT 1"),
                       {"n": n}).scalar()
        if r:
            return r
        r = db.execute(text("SELECT commune FROM parcels WHERE lower(commune) = lower(:n) LIMIT 1"),
                       {"n": n}).scalar()
        return r or n
    except Exception:  # noqa: BLE001 — référentiel absent : on garde le nom tel quel
        try:
            db.rollback()
        except Exception:  # noqa: BLE001
            pass
        return n


def rapport_lien(db, annonce: dict) -> dict:
    """ANNONCE-5 — le rapport LIEN complet (variante commune, 1 page) : POINT UNIQUE écran == PDF. À partir
    de l'annonce relevée (Radar d'abord, sinon fetch), compose : la commune CANONIQUE, les DEUX lectures
    (bâti : écart % au repère du type dans la commune ; foncière : terrain × terrain nu, en % du prix
    demandé, conclusion CHIFFRÉE) et le bloc commune COMPLET (ventes, médianes, évolution, PLU, aléas,
    permis 12 mois). Mêmes médianes partout (marche_commune_bloc) → aucune divergence lecture ↔ bloc."""
    from ..faisabilite.marche_commune import marche_commune_bloc
    a = dict(annonce or {})
    commune = _commune_canonique(db, a.get("commune"))
    a["commune"] = commune
    typ = a.get("type")
    prix = a.get("prix")
    prix_m2 = a.get("prix_m2")
    st = a.get("surface_terrain")
    bloc = None
    try:
        bloc = marche_commune_bloc(db, commune) if commune else None
    except Exception as exc:  # noqa: BLE001
        log.warning("rapport lien : marché commune %s indisponible (%s)", commune, exc)
    # lecture BÂTI : écart % au repère du TYPE de l'annonce dans la commune (même médiane que le bloc).
    bati = None
    if bloc and typ in ("maison", "appartement") and isinstance(prix_m2, (int, float)):
        ref = bloc.get("median_maison_eur_m2" if typ == "maison" else "median_appartement_eur_m2")
        nref = bloc.get("n_maison" if typ == "maison" else "n_appartement")
        if isinstance(ref, (int, float)) and ref > 0:
            bati = {"calculable": True, "ecart_pct": round((prix_m2 - ref) / ref * 100),
                    "referentiel_eur_m2": ref, "n": nref,
                    "type_label_pluriel": "maisons" if typ == "maison" else "appartements",
                    "periode": (bloc.get("serie_maison_5a") or [{}])[0].get("annee")}
    # lecture FONCIÈRE : terrain de l'annonce × terrain nu du secteur → valeur + % du prix + conclusion.
    fonciere = None
    tn = bloc.get("median_terrain_eur_m2") if bloc else None
    if isinstance(tn, (int, float)) and isinstance(st, (int, float)) and st > 0 and isinstance(prix, (int, float)) and prix > 0:
        val = _arrondi_mille(st * tn)          # ANNONCE-5-FIX-2 — arrondi au millier comme partout ailleurs
        pct = round(st * tn / prix * 100)      # % sur le produit exact (l'arrondi d'affichage ne biaise pas la part)
        if pct >= 75:
            concl = f"Le terrain seul vaut {pct} % du prix demandé : bien à valeur surtout foncière."
        elif pct >= 40:
            concl = f"Le terrain représente {pct} % du prix demandé : la valeur est partagée bâti / foncier."
        else:
            concl = f"Le terrain représente {pct} % du prix demandé : la valeur tient surtout au bâti."
        fonciere = {"terrain_m2": round(st), "terrain_eur_m2": tn, "valeur_eur": val,
                    "pct_du_prix": pct, "conclusion": concl}
    # PLU / aléas / parc national : contexte commune (servi). Best-effort — jamais un bloqueur.
    plu_statut = aleas = None
    parc_national = None
    try:
        from ..api.app import commune_contexte
        ctx = commune_contexte(commune, db=db) if commune else None
        if ctx:
            plu_statut = (ctx.get("plu_statut") or {}).get("statut")
            risq = ctx.get("risques") or {}
            aleas = _aleas_commune(risq)
            parc_national = risq.get("parc_national")
    except Exception as exc:  # noqa: BLE001
        log.warning("rapport lien : contexte commune %s indisponible (%s)", commune, exc)
    commune_bloc = dict(bloc or {})
    commune_bloc.update({"plu_statut": plu_statut, "aleas": aleas, "parc_national": parc_national})
    return {"annonce": a, "lectures": {"bati": bati, "fonciere": fonciere}, "commune": commune_bloc}


def _aleas_commune(risq: dict) -> list[str]:
    """Aléas principaux de la commune (miroir du calcul de l'écran) : inondation / mouvement de terrain /
    parc national, à partir du bloc risques servi."""
    out = []
    azi = risq.get("azi_tri") or {}
    if (risq.get("ppr_pct") or 0) > 0 or (azi.get("azi") or []) or (azi.get("tri") or []):
        out.append("inondation")
    if (risq.get("mouvement_terrain_pct") or 0) > 0:
        out.append("mouvement de terrain")
    return out


class AnnonceAnalyseIn(BaseModel):
    url: str


@router.post("/radar/annonce/analyser")
def radar_annonce_analyser(body: AnnonceAnalyseIn) -> dict:
    """ANNONCE-1/2 (entrée LIEN) — l'utilisateur colle un lien d'annonce Leboncoin.

    ANNONCE-2 — on lit D'ABORD ce que LABUSE a DÉJÀ relevé : le Radar capture chaque soir les annonces de
    toute l'île. On extrait l'identifiant (list_id) de l'URL et, si le bien est connu du Radar, le rapport
    est servi depuis les tables existantes SANS aucun appel à Leboncoin (date de relevé = capture Radar).
    URGENCE-1 (NU-F-004, SSRF) — PLUS DE REPLI fetch one-shot : un bien ABSENT du Radar renvoie le
    MESSAGE EXISTANT (`url_bloquee`, phrase imposée côté front) SANS AUCUNE REQUÊTE SORTANTE. La seule
    donnée d'annonce servie provient du Radar (relevé par l'extension) ; le serveur ne va jamais chercher
    un lien fourni par le client (fermeture de l'oracle de ports internes). Entrer l'adresse reste la voie
    pour un bien non relevé."""
    url = (body.url or "").strip()
    if not _URL_RE.match(url) or "leboncoin." not in url.lower():
        return {"ok": False, "erreur": "url_invalide",
                "motif": "Collez un lien d'annonce Leboncoin (https://www.leboncoin.fr/…)."}
    # 1 — LOOKUP RADAR D'ABORD : si le bien a déjà été relevé, rapport servi sans aucun appel Leboncoin.
    list_id = _list_id_from_url(url)
    if list_id is not None:
        with session_scope() as db:
            radar = _annonce_depuis_radar(db, list_id, url)
            if radar is not None:
                rep = rapport_lien(db, radar["annonce"])
                return {"ok": True, **rep, "marche": radar.get("marche")}
    # 2 — bien ABSENT du Radar : AUCUN fetch (SSRF fermé). On rend le message existant `url_bloquee`.
    log.info("radar/annonce/analyser — bien absent du Radar, aucun fetch (SSRF fermé) : %s", url)
    return {"ok": False, "erreur": "url_bloquee"}


@router.get("/radar/annonce/classement/{idu}")
def radar_annonce_classement(idu: str) -> dict:
    """ANNONCE-1-FIX (pt 1) — le « Classement LABUSE » d'une parcelle = la BANDE du run SERVI
    (table `score_labuse`, run courant) rendue avec le VOCABULAIRE CLIENT GRAVÉ — source unique
    `config/score_labuse.yaml` → `score_labuse.libelle_client_bande` (A·Excellente … 0·Non retenue,
    NC·Analyse incomplète + cause). On NE passe JAMAIS par le phrasé de percentile du Signal de
    mutation (`score_v2.verbal.mot`, « proche de la moyenne »), qui n'est pas un classement. Lecture
    seule du run servi — rien de servi touché."""
    with session_scope() as db:
        return _classement_bande(db, idu)


def _classement_bande(db, idu: str) -> dict:
    """Le classement (bande + libellé gravé) du run SERVI pour une parcelle, sur la session fournie —
    partagé par l'endpoint et par `rapport_parcelle` (un seul lecteur, une seule session)."""
    import os
    from ..scoring.score_labuse import charger_bareme, libelle_client_bande
    from .. import runs
    run = os.environ.get("LABUSE_SCORE_RUN") or runs.current()
    row = db.execute(text(
        "SELECT sl.bande, sl.cause FROM score_labuse sl JOIN parcels p ON p.id = sl.parcel_id "
        "WHERE p.idu = :idu AND sl.run_label = :run LIMIT 1"),
        {"idu": idu, "run": run}).mappings().first()
    if not row or not row.get("bande"):
        return {"idu": idu, "bande": None, "libelle": None}
    bareme, _ = charger_bareme()
    bande = str(row["bande"])
    return {"idu": idu, "bande": bande, "libelle": libelle_client_bande(bande, bareme, row.get("cause"))}


def _nature_parcelle(db, idu: str) -> str:
    """ANNONCE-3-FIX (suite) — la nature bâti/nu de la parcelle, lue de l'INDICATEUR DÉJÀ CALCULÉ pour
    le résiduel ET le scoring : `parcel_residuel.taux_emprise_pct` (part bâtie BD TOPO). MÊME logique
    que `_ETAT_BIEN_SQL` de la fiche (taux NULL → non mesuré ; < 5 % → nu ; sinon bâti — encore/max
    selon la SDP résiduelle). On lit la SOURCE et non le champ `etat_bien` de la fiche SERVIE : ce
    champ, pourtant calculé en direct, n'est PAS peuplé sur la base servie (0 parcelle le porte), alors
    que l'indicateur sous-jacent l'est pour ~254 000 parcelles (dont 27 700 nues)."""
    row = db.execute(text(
        "SELECT rb.taux_emprise_pct AS t, rb.sdp_residuelle_m2 AS s "
        "FROM parcels p LEFT JOIN parcel_residuel rb ON rb.parcel_id = p.id "
        "WHERE p.idu = :idu LIMIT 1"), {"idu": idu}).mappings().first()
    if not row or row["t"] is None:
        return "non_mesure"
    if row["t"] < 5:
        return "nu"
    return "bati_encore" if (row["s"] or 0) > 0 else "bati_max"


def _periode_fenetre(fenetre) -> str | None:
    """ANNONCE-3-FIX-2 — extrait la PÉRIODE (plage d'années) d'un libellé `fenetre` de
    `dvf_secteur_medianes` (« 2021-2025 (millésimes géo-DVF disponibles) » → « 2021–2025 »)."""
    if not isinstance(fenetre, str):
        return None
    m = _re.search(r"(\d{4})\s*[-–]\s*(\d{4})", fenetre)
    if m:
        return f"{m.group(1)}–{m.group(2)}"
    m = _re.search(r"\b(\d{4})\b", fenetre)
    return m.group(1) if m else None


def _terrain_repere(db, idu: str) -> dict | None:
    """Repère €/m² de TERRAIN NU du secteur (médiane + n + période) — lecteur DÉCLARÉ `_terrain_section`
    (api/mon_secteur, même méthode que le §Marché de la fiche). L'ANCRE FONCIÈRE, servie aussi pour une
    parcelle BÂTIE (« repère terrain nu, secteur »). None si le secteur est trop peu fourni."""
    try:
        from ..api.mon_secteur import _terrain_section
        t = _terrain_section(db, idu)
    except Exception as exc:  # noqa: BLE001 — le repère foncier est un plus, jamais un bloqueur
        log.warning("estimation %s : repère terrain nu indisponible (%s)", idu, exc)
        return None
    if t and t.get("eur_m2"):
        return {"eur_m2": t["eur_m2"], "n": t.get("n"),
                "perimetre": "secteur", "periode": _periode_fenetre(t.get("millesime"))}
    return None


# ESTIMER-2 (E-024) — la fiabilité n'est plus un ±% FIXE par segment (« ±28 % pour toute maison »). Elle
# est CALCULÉE pour CE bien à partir du nombre de comparables (n) et de leur DISPERSION (écart
# interquartile relatif, q3−q1 sur médiane), en bandes CALIBRÉES sur le banc rejoué sans fuite
# (docs/audit-2026-11/estimer-2). Règle : « Élevée » = beaucoup de comparables ET faible dispersion ;
# « Limitée » = peu de comparables OU forte dispersion OU repli commune ; sinon « Moyenne ». Le ±%
# SERVI est l'écart médian MESURÉ de la bande (honnête — « Élevée » tient ce qu'elle promet), pas la
# promesse. Seuils et ±% calibrés en fin de banc (cf. COMPTE-RENDU, section « bandes de fiabilité »).
# ESTIMER-PRECISION-1 — bandes de fiabilité RECALIBRÉES sur la MÉTHODE PONDÉRÉE et PAR SEGMENT, à partir
# de la grille (n × dispersion) du banc 2024-règle/2025-annonce (docs/audit-2026-11/estimer-precision-1).
# « Élevée » ne s'affiche que là où le banc 2025 TIENT la promesse ; le ±% servi EST l'écart médian
# mesuré de la bande (honnête). APPARTEMENT/copro : Élevée (n≥15, disp≤0,40) tient ~14 % < 15 %.
# MAISON (plancher donnée ~27 %, qu'aucune méthode ne franchit) : « Élevée » RÉSERVÉE aux secteurs denses
# ET homogènes (n≥40, disp≤0,25 → ~17-20 % mesuré) ; partout ailleurs « Moyenne » (±26 %) ou « Limitée »
# (±36 %), avec une fourchette large — on ne promet jamais une précision que la donnée ne permet pas.
_FIAB_SEG = {
    "appartement": {"n_elevee": 15, "disp_elevee": 0.40, "n_min": 8, "disp_lim": 0.75,
                    "ecart": {"fiable": 15, "moyen": 18, "limitee": 30}},
    "maison": {"n_elevee": 40, "disp_elevee": 0.25, "n_min": 8, "disp_lim": 0.75,
               "ecart": {"fiable": 20, "moyen": 26, "limitee": 36}},
}


def _fiab_seg(type_bien: str | None) -> str:
    """Les copropriétés et les biens de secteur dominé par l'appartement suivent les bandes APPARTEMENT ;
    tout le reste (maison, bâti mixte, type inconnu) suit les bandes MAISON, plus prudentes."""
    return "appartement" if type_bien == "appartement" else "maison"
# Terrain nu : logique inchangée (mandat §terrain non modifié) — ±% du segment, calibré banc 1/2.
_ECART_SEGMENT = {"terrain": 19}


def _arrondi_mille(n):
    """Montant en € arrondi au millier le plus proche (ordre de grandeur, jamais un faux calcul exact)."""
    return int(round(n / 1000.0)) * 1000 if isinstance(n, (int, float)) else None


def _fiabilite_segment(type_bien: str | None) -> tuple[str, int]:
    """Fiabilité PAR SEGMENT (terrain nu seulement, logique inchangée) : ±% mesuré → « Élevée » sous
    15 %, « Moyenne » sous 25 %, « Limitée » au-delà. Renvoie (niveau interne, écart % mesuré)."""
    ecart = _ECART_SEGMENT.get(type_bien or "terrain", 25)
    niveau = "fiable" if ecart < 15 else ("moyen" if ecart < 25 else "limitee")
    return niveau, ecart


def _fiabilite_bien(n, median, q1, q3, commune_fallback: bool,
                    type_bien: str | None = None) -> tuple[str, int]:
    """ESTIMER-PRECISION-1 (ex-E-024) — fiabilité d'une estimation bâtie, CALCULÉE pour CE bien et PAR
    SEGMENT : nombre de comparables `n` + DISPERSION (IQR relatif (q3−q1)/médiane), bandes recalibrées sur
    la méthode pondérée (banc 2025). Renvoie (niveau interne, ±% médian mesuré de la bande). « Élevée » ne
    sort que là où le banc le tient (maison : secteurs denses+homogènes seulement). Repli commune →
    « Limitée »."""
    cfg = _FIAB_SEG[_fiab_seg(type_bien)]
    if commune_fallback:
        return "limitee", cfg["ecart"]["limitee"]
    disp = None
    if isinstance(q1, (int, float)) and isinstance(q3, (int, float)) and isinstance(median, (int, float)) and median:
        disp = (q3 - q1) / median
    n = int(n or 0)
    if n < cfg["n_min"] or (disp is not None and disp > cfg["disp_lim"]):
        niveau = "limitee"
    elif n >= cfg["n_elevee"] and disp is not None and disp <= cfg["disp_elevee"]:
        niveau = "fiable"
    else:
        niveau = "moyen"
    return niveau, cfg["ecart"][niveau]


def _derniere_mutation_dvf(db, idu: str) -> dict | None:
    """ESTIMER-2 (E-022) — la DERNIÈRE mutation DVF de la parcelle (ventes « Vente » / « Vente terrain à
    bâtir »), avec la NATURE du bien VENDU (maison / appartement / terrain) et sa surface bâtie. La nature
    est lue sur la MUTATION, pas sur l'état actuel de la parcelle : un terrain vendu nu n'est plus
    valorisé comme une maison. None si aucune vente. Renvoie {date, nature, bati_m2, terrain_m2, valeur}."""
    row = db.execute(text(
        "WITH lm AS ("
        "  SELECT id_mutation, date_mutation FROM dvf_mutations_parcelle "
        "  WHERE id_parcelle = :idu AND date_mutation IS NOT NULL "
        "    AND nature_mutation IN ('Vente', 'Vente terrain à bâtir') "
        "  ORDER BY date_mutation DESC LIMIT 1) "
        "SELECT to_char(lm.date_mutation, 'YYYY-MM-DD') AS date, "
        "  COALESCE(sum(dm.surface_reelle_bati) FILTER "
        "    (WHERE dm.type_local IN ('Maison','Appartement')), 0) AS bati_m2, "
        "  count(*) FILTER (WHERE dm.type_local = 'Maison') AS n_maison, "
        "  count(*) FILTER (WHERE dm.type_local = 'Appartement') AS n_appart, "
        "  max(dm.surface_terrain) AS terrain_m2, max(dm.valeur_fonciere) AS valeur "
        "FROM lm JOIN dvf_mutations_parcelle dm "
        "  ON dm.id_parcelle = :idu AND dm.id_mutation = lm.id_mutation "
        "GROUP BY lm.date_mutation"), {"idu": idu}).mappings().first()
    if not row:
        return None
    n_m, n_a = int(row["n_maison"] or 0), int(row["n_appart"] or 0)
    if n_m or n_a:
        nature = "maison" if n_m >= n_a else "appartement"
    elif (row["terrain_m2"] or 0) > 0:
        nature = "terrain"
    else:
        nature = None
    return {"date": row["date"], "nature": nature, "bati_m2": float(row["bati_m2"] or 0),
            "terrain_m2": float(row["terrain_m2"] or 0), "valeur": row["valeur"]}


_RATIO_ASSISE_MIN = 20   # ESTIMER-2 — assise minimale (n ventes) pour servir le ratio surface/emprise


def _ratio_surf_emprise_commune(db, insee: str) -> tuple[float | None, int]:
    """ESTIMER-2 (E-021) — ratio médian (surface bâtie VENDUE / emprise au sol BD TOPO) sur les ventes de
    MAISONS de la commune, et son assise (n). Sert à estimer une surface habitable depuis l'emprise quand
    la parcelle n'a pas de vente DVF. (ratio, n) — (None, n) si l'assise est trop mince."""
    if not insee:
        return None, 0
    row = db.execute(text(
        "WITH v AS ("
        "  SELECT dm.id_parcelle, dm.id_mutation, sum(dm.surface_reelle_bati) AS surf "
        "  FROM dvf_mutations_parcelle dm "
        "  WHERE dm.code_commune = :insee AND dm.type_local = 'Maison' "
        "    AND dm.nature_mutation = 'Vente' AND dm.surface_reelle_bati > 0 "
        "  GROUP BY dm.id_parcelle, dm.id_mutation) "
        "SELECT count(*) AS n, "
        "  percentile_cont(0.5) WITHIN GROUP (ORDER BY v.surf / b.emprise_bati_m2) AS ratio "
        "FROM v JOIN p_model_bati b ON b.idu = v.id_parcelle AND b.emprise_bati_m2 > 0"),
        {"insee": insee}).mappings().first()
    n = int((row or {}).get("n") or 0)
    if not row or not row.get("ratio") or n < _RATIO_ASSISE_MIN:
        return None, n
    return round(float(row["ratio"]), 3), n


def _surface_pour_total(db, idu: str, emprise, mut: dict | None, insee: str,
                        surface_hab: float | None = None,
                        bati_mesure: bool = True) -> tuple[int | None, dict | None]:
    """ESTIMER-2 (D-009, E-021) — la surface du TOTAL indicatif d'un bien bâti, DANS CET ORDRE :
      0. ESTIMER-PRECISION-1 — la SURFACE HABITABLE SAISIE par l'utilisateur, si elle est fournie
         (champ facultatif de l'entrée par adresse) : le total la prend telle quelle, libellé « surface
         saisie ». C'est l'intrant le plus sûr (le bien réel), devant toute estimation.
      1. la surface bâtie de la DERNIÈRE VENTE DVF de la parcelle si elle existe ;
      2. sinon l'emprise au sol BD TOPO × le RATIO MÉDIAN (surface vendue / emprise) des ventes de
         maisons de la commune (ratio + assise JOURNALISÉS).
    Plus JAMAIS l'emprise brute × un prix habitable. Le libellé dit quelle surface a servi.
    Renvoie (surface_m2, source) ou (None, None) si aucune surface n'est disponible."""
    # FIX-NU3-2 (H-M01) — le garde testait le SIGNE (`> 0`) mais jamais la FINITUDE : `inf`/`1e309`
    # passaient `> 0` puis faisaient lever `round(inf)` (OverflowError → 500 brut). On exige désormais
    # une valeur FINIE (ceinture interne, en plus du bornage `Query(gt=0, le=100000)` des routes).
    if isinstance(surface_hab, (int, float)) and math.isfinite(surface_hab) and surface_hab > 0:
        s = round(surface_hab)
        return s, {"source": "surface_saisie",
                   "ligne": f"Surface habitable saisie ({s} m²)",
                   "note": "Surface habitable renseignée par l'utilisateur. Ordre de grandeur, "
                           "pas un calcul exact."}
    if mut and (mut.get("bati_m2") or 0) > 0:
        s = round(mut["bati_m2"])
        an = (mut.get("date") or "")[:4]
        return s, {"source": "dvf_vente",
                   "ligne": (f"Surface bâtie de la dernière vente DVF ({an}, {s} m²)" if an
                             else f"Surface bâtie de la dernière vente DVF ({s} m²)"),
                   "note": ("Surface bâtie de la dernière vente DVF de la parcelle. "
                            "Ordre de grandeur, pas un calcul exact.")}
    # FIX-FINAL-1 (NU-D-012) — bâti NON MESURÉ (taux d'emprise inconnu, aucune vente) : on ne FABRIQUE
    # PAS un total par emprise × ratio. « Non mesuré » et « voici le total » se contredisent ; sans
    # vente ni surface saisie, on ne sert aucune valeur indicative (le marché €/m² reste servi à côté).
    if not bati_mesure:
        return None, None
    if isinstance(emprise, (int, float)) and emprise > 0:
        ratio, assise = _ratio_surf_emprise_commune(db, insee)
        if ratio:
            s = round(emprise * ratio)
            log.info("estimation %s : surface habitable estimée = emprise %d m² × ratio %.3f "
                     "(médiane surface vendue / emprise sur %d ventes de maisons de la commune %s)",
                     idu, round(emprise), ratio, assise, insee)
            return s, {"source": "emprise_ratio",
                       "ligne": f"Surface habitable estimée d'après l'emprise au sol ({s} m²)",
                       "note": ("Surface habitable estimée d'après l'emprise au sol : total indicatif "
                                "(ratio médian surface vendue / emprise au sol des ventes de maisons de "
                                f"la commune : {('%.2f' % ratio).replace('.', ',')} sur "
                                f"{f'{assise:,}'.replace(',', ' ')} ventes).")}
    return None, None


# CHASSE-4-FIX (C4-001) — le MOT affiché de la fiabilité est décidé ICI, une seule fois, et servi tel
# quel. L'écran et le PDF l'AFFICHENT sans retraduire (plus de table de correspondance au front qui
# ratait `limitee` et remontait le niveau à « Moyenne »). Repli commune → toujours « Limitée ».
def _fiabilite_mot(niveau: str | None, commune_fallback: bool = False) -> str:
    if commune_fallback:
        return "Limitée"
    return {"fiable": "Élevée", "moyen": "Moyenne", "limitee": "Limitée"}.get(niveau or "", "Moyenne")


def _emprise_bati_fiche_m2(fiche: dict | None) -> int | None:
    """FIX-P-1 (P-03) — emprise au sol du bâti existant = la SEULE valeur de la fiche
    (`le_bien.emprise_batie_m2`, BD TOPO unionnée et CLIPPÉE à la parcelle, producteur unique
    `bati.emprise_bati_bdtopo_m2`, décision SDP-UNIQUE). Estimer NE recalcule PLUS l'emprise :
    l'ancien `p_model_bati.emprise_bati_m2` n'était pas clippé à la parcelle (empreintes entières)
    → 136 m² à l'Estimer là où le Dossier/la fiche servaient 105 m². Désormais écran == PDF == Dossier."""
    emp = ((fiche or {}).get("le_bien") or {}).get("emprise_batie_m2")
    return round(float(emp)) if emp and float(emp) > 0 else None


def _valeur_indicative(surface_m2, median, ecart_pct, *, source: dict | None = None) -> dict | None:
    """Valeur indicative = surface × €/m² — un ORDRE DE GRANDEUR (jamais un calcul exact). Montants
    arrondis au millier ; fourchette ÉLARGIE par l'écart mesuré du segment. `source` (ESTIMER-2) porte
    la PROVENANCE de la surface (vente DVF ou emprise×ratio), le LIBELLÉ et la NOTE servis à l'identique
    à l'écran et au PDF. None si surface ou médiane manquent (la ligne disparaît)."""
    if not isinstance(surface_m2, (int, float)) or not isinstance(median, (int, float)):
        return None
    central = surface_m2 * median
    out = {"surface_m2": round(surface_m2), "eur_m2": round(median), "valeur_eur": _arrondi_mille(central)}
    if isinstance(ecart_pct, (int, float)) and ecart_pct > 0:
        out["valeur_basse"] = _arrondi_mille(central * (1 - ecart_pct / 100.0))
        out["valeur_haute"] = _arrondi_mille(central * (1 + ecart_pct / 100.0))
    src = source or {}
    out["surface_source"] = src.get("source")   # 'dvf_vente' | 'emprise_ratio' | None
    out["ligne"] = src.get("ligne")              # libellé « quelle surface a servi » (écran == PDF)
    out["note"] = src.get("note")
    return out


def _lecture_fonciere_parcelle(surface_terrain_m2, repere_tn, valeur_bati_eur) -> dict | None:
    """Lecture FONCIÈRE d'une parcelle (comme la variante lien) : surface de la parcelle × repère terrain
    nu du secteur = valeur foncière (€, arrondie au millier), + la part qu'elle représente de l'ordre de
    grandeur bâti. None si la surface ou le repère manquent."""
    tn = (repere_tn or {}).get("eur_m2")
    if not isinstance(surface_terrain_m2, (int, float)) or not isinstance(tn, (int, float)):
        return None
    val = _arrondi_mille(surface_terrain_m2 * tn)
    out = {"surface_m2": round(surface_terrain_m2), "eur_m2": tn, "valeur_eur": val,
           "n": (repere_tn or {}).get("n"), "perimetre": (repere_tn or {}).get("perimetre")}
    if isinstance(valeur_bati_eur, (int, float)) and valeur_bati_eur > 0 and val:
        out["pct_du_bati"] = round(val / valeur_bati_eur * 100)
    return out


def estimation_annonce(db, idu: str, fiche: dict, surface_hab: float | None = None) -> dict:
    """ANNONCE-5 + NU5-FIX-1 (A-O3) — l'estimation du prix d'une parcelle, POINT UNIQUE écran == PDF,
    enrichie du VERDICT DE CONSTRUCTIBILITÉ. Estimer est un comparateur de SECTEUR honnête, mais sur
    une parcelle qui ne peut rien recevoir (N/A/AU fermée/habitat interdit/PPR rédhibitoire), un €/m²
    « bâti » + une fiabilité « Moyenne/Élevée » induisent en erreur. On ajoute donc `constructibilite`
    (lu via la MÊME fonction que la fiche, `potentiel_batir`) et, si inconstructible, un
    `avertissement_constructibilite` affiché à l'écran et dans le PDF."""
    res = _estimation_annonce_core(db, idu, fiche, surface_hab=surface_hab)
    try:
        pot = (fiche or {}).get("potentiel_a_batir")
        if not pot:
            from ..faisabilite.potentiel_batir import potentiel_batir
            pot = potentiel_batir(db, idu)
    except Exception:  # noqa: BLE001 — caches absents → pas de verdict, jamais une 500
        pot = None
    if isinstance(pot, dict):
        res["constructibilite"] = {
            "constructible": pot.get("constructible"),
            "rien_a_batir": pot.get("rien_a_batir"),
            "motif": pot.get("motif"),
            "zone_lib": pot.get("zone_lib"),
        }
        if pot.get("constructible") is False:
            res["avertissement_constructibilite"] = (
                (pot.get("motif") or "Parcelle non constructible")
                + " — ce prix est un repère de marché du secteur, pas une valeur à bâtir.")
    return res


def _estimation_annonce_core(db, idu: str, fiche: dict, surface_hab: float | None = None) -> dict:
    """ANNONCE-5 — l'estimation du prix d'une parcelle, POINT UNIQUE lu par l'écran (endpoint) ET par le
    PDF (builder) → mêmes chiffres, mêmes comparables, même valeur indicative, aucun recalcul divergent.

    · Parcelle NUE → repère €/m² de TERRAIN NU du secteur (`_terrain_repere`) + les 8 ventes de terrain nu
      les plus proches (`comparateur_terrain`) ; valeur indicative = surface × repère.
    · Parcelle BÂTIE → comparateur BÂTI UNIQUE `comparateur_bien` (agrégat + 8 proches + total).
      Valeur indicative = ORDRE DE GRANDEUR : SURFACE (surface bâtie de la dernière vente DVF, sinon
      emprise au sol × ratio médian surface/emprise de la commune — jamais l'emprise brute) × médiane
      €/m² habitable + lecture FONCIÈRE (surface × repère terrain nu, % du bâti).

    ESTIMER-2 — la NATURE est lue sur la dernière mutation DVF (E-022) ; la branche copropriété passe
    AVANT la branche terrain nu (E-026) ; une parcelle non mesurée reste « bâti non mesuré » (D-012) ;
    la fiabilité est calculée bien par bien (E-024). Montants arrondis au millier."""
    from .. import marche_service as _msvc
    # ESTIMER-2 (E-022) — nature du bien VENDU, lue sur la dernière mutation DVF ; à défaut, l'état de
    # la parcelle (emprise BD TOPO). Un terrain vendu nu n'est plus valorisé comme une maison.
    mut = _derniere_mutation_dvf(db, idu)
    nature_mut = mut.get("nature") if mut else None       # 'maison' | 'appartement' | 'terrain' | None
    nature_parc = _nature_parcelle(db, idu)               # 'nu' | 'non_mesure' | 'bati_encore' | 'bati_max'
    # CHASSE-4-FIX (C4-003) — flag copropriété du run servi (même indicateur que le verdict fiche).
    copro = bool(((fiche or {}).get("score_v2") or {}).get("copro"))
    repere_tn = _terrain_repere(db, idu)
    # FIX-FINAL-1 (NU-D-040) — surface du terrain CANONIQUE (doctrine CONTENANCE-1) : la CONTENANCE
    # cadastrale si on l'a (= ce que sert le Dossier/la fiche), le dessin seulement en repli. Avant,
    # Estimer lisait `surface_m2` (dessin) EN PREMIER → 630 m² ici là où le Dossier servait 625 m²
    # (contenance), deux surfaces pour le même bien. Une seule vérité, les documents concordent.
    surface_parc = ((fiche or {}).get("surface_terrain_m2")
                    or (fiche or {}).get("contenance_m2") or (fiche or {}).get("surface_m2"))
    insee = idu[:5]

    # 1 — COPROPRIÉTÉ (E-026) : la branche copropriété passe AVANT la branche terrain nu. Un lot de copro
    #     n'est ni un terrain ni une maison : comparateur APPARTEMENTS, pas d'ordre de grandeur bâti
    #     (aucun bien unique à valoriser), la lecture foncière reste.
    if copro:
        cb = _msvc.comparateur_bien(db, idu, type_bien="appartement")
        base = {"nature": "copropriete", "type_comparateur": "bati", "type_bien": "appartement",
                "repere_terrain_nu": repere_tn,
                "lecture_fonciere": _lecture_fonciere_parcelle(surface_parc, repere_tn, None)}
        if not cb or cb.get("median") is None:
            return {**base, "median": None, "comparables": [],
                    "fiabilite_mot": _fiabilite_mot("limitee", False),
                    "note": "Pas assez de ventes d'appartements comparables dans le secteur."}
        niveau, ecart = _fiabilite_bien(cb.get("n"), cb.get("median"), cb.get("q1"), cb.get("q3"),
                                        cb.get("commune_fallback"), type_bien="appartement")
        return {**base,
                "type_label_pluriel": cb.get("type_label_pluriel") or "appartements",
                "median": cb.get("median"), "q1": cb.get("q1"), "q3": cb.get("q3"), "n": cb.get("n"),
                "radius_m": cb.get("radius_m"), "periode": cb.get("periode"),
                "fiabilite": niveau, "precision_pct": ecart, "commune_fallback": cb.get("commune_fallback"),
                "fiabilite_mot": _fiabilite_mot(niveau, cb.get("commune_fallback")),
                "comparables": cb.get("comparables") or [], "n_total": cb.get("n_total"),
                "emprise_bati_m2": None, "valeur_indicative": None}

    # 2 — TERRAIN NU : la dernière vente DVF est un terrain (E-022) OU, à défaut de vente, la parcelle
    #     est nue (emprise < 5 %). Un terrain vendu nu n'est plus valorisé comme une maison.
    if (nature_mut == "terrain") or (nature_mut is None and nature_parc == "nu"):
        niveau, ecart = _fiabilite_segment("terrain")
        terr = _msvc.comparateur_terrain(db, idu)
        if repere_tn and repere_tn.get("eur_m2"):
            med = repere_tn["eur_m2"]
            return {"nature": "nue", "type_comparateur": "terrain_nu", "type_bien": "terrain",
                    "median": med, "n": repere_tn.get("n"), "periode": repere_tn.get("periode"),
                    "perimetre": repere_tn.get("perimetre"), "fiabilite": niveau, "precision_pct": ecart,
                    "commune_fallback": False, "fiabilite_mot": _fiabilite_mot(niveau, False),
                    "comparables": terr.get("comparables") or [], "n_total": terr.get("n_total"),
                    "comparables_periode": terr.get("periode"),
                    "comparables_radius_m": terr.get("radius_m"),   # C4-005 — rayon réel des comparables
                    "valeur_indicative": _valeur_indicative(surface_parc, med, ecart),
                    "repere_terrain_nu": repere_tn}
        return {"nature": "nue", "type_comparateur": "terrain_nu", "type_bien": "terrain",
                "median": None, "comparables": [], "repere_terrain_nu": repere_tn,
                "note": "Pas assez de ventes de terrain nu comparables dans le secteur."}

    # 3 — BÂTI : la dernière vente DVF est un bâti (type maison/appartement FORCÉ dans le comparateur,
    #     E-022) ; à défaut de vente, le comparateur déduit le type dominant du secteur. Une parcelle
    #     NON MESURÉE (taux d'emprise inconnu, aucune vente) reste « bâti non mesuré » (D-012).
    type_force = nature_mut if nature_mut in ("maison", "appartement") else None
    non_mesure = (nature_mut is None and nature_parc == "non_mesure")
    nature_out = "bati_non_mesure" if non_mesure else "batie"
    # ESTIMER-PRECISION-1 — surface du sujet pour PONDÉRER les comparables (surface saisie > surface de
    # la dernière vente DVF) et taille de terrain du sujet (contenance parcelle) pour les maisons.
    surf_poids = (surface_hab if (isinstance(surface_hab, (int, float)) and surface_hab > 0)
                  else ((mut or {}).get("bati_m2") or None))
    cb = _msvc.comparateur_bien(db, idu, type_bien=type_force,
                                surface_sujet=surf_poids, terrain_sujet=surface_parc)
    if not cb or cb.get("median") is None:
        return {"nature": nature_out, "type_comparateur": "bati",
                "type_bien": (cb or {}).get("type_bien") or (type_force or "bati"),
                "median": None, "comparables": [], "repere_terrain_nu": repere_tn,
                "note": "Pas assez de ventes comparables dans le secteur."}
    niveau, ecart = _fiabilite_bien(cb.get("n"), cb.get("median"), cb.get("q1"), cb.get("q3"),
                                    cb.get("commune_fallback"), type_bien=cb.get("type_bien"))
    emprise = _emprise_bati_fiche_m2(fiche)
    # ESTIMER-2 (D-009, E-021) — la SURFACE du total : surface bâtie de la dernière vente DVF si elle
    # existe, sinon emprise × ratio médian de la commune. Jamais l'emprise brute × un prix habitable.
    surface_tot, src_surf = _surface_pour_total(db, idu, emprise, mut, insee, surface_hab,
                                                 bati_mesure=not non_mesure)
    vi = _valeur_indicative(surface_tot, cb.get("median"), ecart, source=src_surf)
    # ESTIMER-PRECISION-1 — surface habitable de la dernière vente DVF, exposée pour PRÉREMPLIR le champ
    # facultatif « surface habitable » de l'écran (prérempli quand la dernière vente DVF la donne).
    surface_dvf = round(mut["bati_m2"]) if (mut and (mut.get("bati_m2") or 0) > 0) else None
    return {
        "nature": nature_out,
        "type_comparateur": "bati", "type_bien": cb.get("type_bien"),
        "type_label_pluriel": cb.get("type_label_pluriel"),
        "median": cb.get("median"), "q1": cb.get("q1"), "q3": cb.get("q3"), "n": cb.get("n"),
        "radius_m": cb.get("radius_m"), "periode": cb.get("periode"),
        "fiabilite": niveau, "precision_pct": ecart, "commune_fallback": cb.get("commune_fallback"),
        "fiabilite_mot": _fiabilite_mot(niveau, cb.get("commune_fallback")),
        "comparables": cb.get("comparables") or [], "n_total": cb.get("n_total"),
        "emprise_bati_m2": emprise, "surface_dvf_m2": surface_dvf,
        "valeur_indicative": vi,
        "lecture_fonciere": _lecture_fonciere_parcelle(surface_parc, repere_tn,
                                                        (vi or {}).get("valeur_eur")),
        "repere_terrain_nu": repere_tn,
    }


@router.get("/radar/annonce/estimation/{idu}")
def radar_annonce_estimation(
    idu: str,
    surface_hab: float | None = Query(None, gt=0, le=100000),
) -> dict:
    """ANNONCE-3-FIX — l'estimation du prix d'une parcelle, selon sa NATURE (nue → terrain nu, bâtie →
    bâti). Lit la fiche SERVIE (lecture seule) puis `estimation_annonce` (point unique). L'écran et le
    PDF lisent exactement ce rapport → mêmes chiffres, même règle."""
    from ..api.app import parcel_fiche
    with session_scope() as db:
        # NU5-FIX-1 (B-F1) — Analyser une annonce (outil) REFUSE une parcelle disparue du cadastre,
        # comme le document : jamais un prix estimé sur une parcelle sortie du cadastre.
        from .. import cadastre_disparue as _cd
        _disp = _cd.info_disparue(db, idu)
        if _disp:
            return {"idu": idu, "median": None, "type_comparateur": None,
                    "erreur": "parcelle_disparue", "note": _cd.phrase_disparue(_disp)}
        try:
            fiche = parcel_fiche(idu, db=db)
        except ValueError:
            return {"idu": idu, "median": None, "type_comparateur": None, "note": "Parcelle inconnue."}
        # CHASSE-4-FIX (C4-002) + NU-3-J#4 — nombre d'aléas = les familles d'aléas DISTINCTES
        # (`distinct_hazards`), compteur UNIQUE partagé par la tuile « Aléas » de la fiche (`aleas.n_hazards`)
        # et le PDF (`_risques_rows`, une ligne par hazard) : fiche == Estimer == PDF, fin de l'écart 6≠2.
        n_aleas = len(distinct_hazards(((fiche or {}).get("aleas") or {}).get("liste")))
        return {"idu": idu, "n_aleas": n_aleas,
                **estimation_annonce(db, idu, fiche, surface_hab=surface_hab)}


# ── ANNONCE-5 — le RAPPORT PARCELLE complet (variante adresse, 2 pages) : POINT UNIQUE écran == PDF ──
def _num(x) -> str | None:
    """Nombre affiché FR court : 7.0 → « 7 », 4.5 → « 4,5 ». None → None."""
    if not isinstance(x, (int, float)):
        return None
    return (f"{int(round(x))}" if float(x).is_integer() else f"{x:.1f}").replace(".", ",")


def _assiette_alea_deduite(db, idu: str) -> int | None:
    """Assiette constructible « aléa déduit » = surface de la parcelle en zone constructible (U/AU) MOINS
    la part en aléa FORT (PPR interdiction / zone rouge). Calculée sur les couches servies (spatial_layers,
    hors verrou de graphe). None si le calcul échoue (la ligne disparaît du rendu)."""
    try:
        row = db.execute(text(
            "WITH p AS (SELECT geom_2975 g FROM parcels WHERE idu = :i), "
            "cons AS (SELECT COALESCE(ST_Union(sl.geom_2975), ST_GeomFromText('POLYGON EMPTY',2975)) geom "
            "         FROM spatial_layers sl, p WHERE sl.kind='plu_gpu_zone' AND ST_Intersects(sl.geom_2975,p.g) "
            "           AND labuse_zone_famille(sl.subtype) IN ('U','AU')), "
            "ppr AS (SELECT COALESCE(ST_Union(sl.geom_2975), ST_GeomFromText('POLYGON EMPTY',2975)) geom "
            "        FROM spatial_layers sl, p WHERE sl.kind='ppr' AND sl.subtype='INTERDICTION' "
            "          AND ST_Intersects(sl.geom_2975,p.g)) "
            "SELECT round(ST_Area(ST_Difference(ST_Intersection(cons.geom,p.g), ppr.geom)))::int "
            "FROM p, cons, ppr"), {"i": idu}).scalar()
        return int(row) if row and row > 0 else None
    except Exception as exc:  # noqa: BLE001 — géométrie/fonction absente : ligne omise, jamais un 500
        try:
            db.rollback()
        except Exception:  # noqa: BLE001
            pass
        log.warning("assiette aléa-déduite %s indisponible (%s)", idu, exc)
        return None


def _regles_zone(zone: str | None, commune: str | None) -> list[dict]:
    """Règles de la zone PLU LUES DU CALIBRAGE (`resolve_zone`) : hauteur, emprise, reculs, stationnement.
    Chaque règle NON chiffrée (zone non calibrée) est OMISE — jamais un « à vérifier » brut imprimé."""
    if not zone:
        return []
    try:
        from ..faisabilite.zonage import resolve_zone
        zr = resolve_zone(zone, commune)
    except Exception:  # noqa: BLE001
        zr = None
    if not zr:
        return []
    out = []

    def _recul(m, alignement, formule):
        if alignement:
            return "à l'alignement"
        if isinstance(m, (int, float)):
            suff = " ou H/2" if formule and "h/2" in str(formule).lower() else ""
            return f"{_num(m)} m{suff}"
        return None
    if isinstance(zr.hf_m, (int, float)) or isinstance(zr.he_m, (int, float)):
        # POST-DEPLOY-1 — hauteur réglementaire UNIFORME « N m au faîtage · M m à l'égout » (même voix
        # que le Dossier / robinet_fiche via plu_reglement). Le document « Estimer un bien » ne tronque
        # plus l'égout : la fiche, l'écran et TOUS les documents disent la même hauteur (docs_coherence).
        _hparts = []
        if isinstance(zr.hf_m, (int, float)):
            _hparts.append(f"{_num(zr.hf_m)} m au faîtage")
        if isinstance(zr.he_m, (int, float)):
            _hparts.append(f"{_num(zr.he_m)} m à l'égout")
        out.append({"cle": "Hauteur maximale", "valeur": " · ".join(_hparts)})
    if isinstance(zr.emprise_sol_pct, (int, float)):
        out.append({"cle": "Emprise au sol maximale", "valeur": f"{_num(zr.emprise_sol_pct)} %"})
    rv = _recul(zr.recul_voirie_m, zr.recul_voirie_alignement, None)
    if rv:
        out.append({"cle": "Recul par rapport à la voie", "valeur": rv})
    rl = _recul(zr.recul_limites_sep_m, zr.recul_limites_alignement, zr.recul_limites_formule)
    if rl:
        out.append({"cle": "Recul par rapport aux limites", "valeur": rl})
    stat = getattr(zr, "stat_logement", None)
    if isinstance(stat, str) and stat and "vérif" not in stat.lower():
        out.append({"cle": "Stationnement", "valeur": stat})
    return out


def _parcelle_mesures(db, idu: str, fiche: dict) -> list[dict]:
    """Les mesures DE LA PARCELLE face aux règles : assiette (aléa déduit), emprise bâtie, hauteurs LiDAR
    (faîtage / égout) + date de survol, SDP restante. Chaque mesure absente est OMISE."""
    pot = (fiche or {}).get("potentiel_transformation") or {}
    out = []
    ass = _assiette_alea_deduite(db, idu)
    if ass:
        out.append({"cle": "Assiette constructible, aléa déduit", "valeur": f"{_fmt_m2_fr(ass)}"})
    emp = _emprise_bati_fiche_m2(fiche)   # FIX-P-1 (P-03) — emprise UNIQUE de la fiche (BD TOPO clippée)
    if emp:
        out.append({"cle": "Bâti existant, emprise", "valeur": f"{_fmt_m2_fr(emp)}"})
    hf, he = pot.get("hauteur_faitage_lidar_m"), pot.get("hauteur_egout_lidar_m")
    if isinstance(hf, (int, float)) and isinstance(he, (int, float)):
        out.append({"cle": "Hauteur mesurée, faîtage / égout", "valeur": f"{_num(hf)} m / {_num(he)} m"})
    elif isinstance(hf, (int, float)):
        out.append({"cle": "Hauteur mesurée, faîtage", "valeur": f"{_num(hf)} m"})
    survol = pot.get("hauteur_survol")
    if survol:
        out.append({"cle": "Survol LiDAR", "valeur": str(survol)})
    # ANNONCE-5-FIX — SDP restante = la valeur DU RUN SERVI (`parcel_residuel`, stable), PLUS le champ
    # `potentiel_transformation.sdp_residuelle_m2` qui, lui, est RECALCULÉ EN DIRECT et varie sur cache
    # froid (35 m² hier, 26 m² aujourd'hui). PDF, écran et fiche montrent ainsi le MÊME chiffre servi.
    # SDP-UNIQUE-1 (A-001) — une parcelle ÉCARTÉE (cause du résiduel OU hors_classement du scoring :
    # forêt publique inacquérable…) ne porte PAS de SDP positive ici non plus : l'écran, la fiche et
    # ce PDF disent « aucune SDP exploitable » de la même voix (une seule notion, une seule valeur).
    # score_labuse/mvt_meta peuvent manquer (fixture/base sans scoring) → repli sur la cause du run seul.
    try:
        srun = db.execute(text(
            "SELECT rb.sdp_residuelle_m2 AS s, rb.assiette_source AS a, rb.cause AS rc, sl.cause AS sc "
            "FROM parcel_residuel rb JOIN parcels p ON p.id = rb.parcel_id "
            "LEFT JOIN score_labuse sl ON sl.parcel_id = rb.parcel_id "
            "   AND sl.run_label = (SELECT value FROM mvt_meta WHERE key='run_label') "
            "WHERE p.idu = :i"), {"i": idu}).mappings().first()
    except Exception:  # noqa: BLE001 — scoring absent : on garde la cause du run résiduel seule
        db.rollback()
        srun = db.execute(text(
            "SELECT rb.sdp_residuelle_m2 AS s, rb.assiette_source AS a, rb.cause AS rc, NULL AS sc "
            "FROM parcel_residuel rb JOIN parcels p ON p.id = rb.parcel_id WHERE p.idu = :i"),
            {"i": idu}).mappings().first()
    ecartee = bool(srun) and (srun["rc"] is not None or srun["sc"] is not None)
    if srun and isinstance(srun["s"], (int, float)) and not ecartee:
        suff = " (estimation simplifiée)" if srun["a"] == "residuel_legacy" else ""
        out.append({"cle": "SDP restante estimée", "valeur": f"{_fmt_m2_fr(round(srun['s']))}{suff}"})
    return out


def _fmt_m2_fr(m2) -> str:
    """« 1 290 m² » (groupage FR par espace)."""
    return f"{int(round(m2)):,}".replace(",", " ") + " m²"


_HAZARDS = (("inondation", "Inondation"), ("mouvement", "Mouvement de terrain"),
            ("littoral", "Littoral / submersion"), ("submersion", "Littoral / submersion"),
            ("volcan", "Volcanique"), ("incendie", "Feux de forêt"), ("feux", "Feux de forêt"),
            ("houle", "Houle / recul du trait de côte"))


def distinct_hazards(aleas_liste: list[dict] | None) -> list[str]:
    """NU-3-J#4 / NU-G-014 — familles d'aléas DISTINCTES d'une liste `aleas.liste` : on FUSIONNE les
    entrées « Aléa X » (intensité Géorisques), « PPR — zone … » (règlement) et les niveaux multiples
    d'un même aléa → UN hazard compté une seule fois. Compteur d'aléas UNIQUE, partagé par la tuile
    « Aléas » de la fiche, l'outil « Estimer » et le PDF — plus jamais « 6 » d'un côté et « 2 » de l'autre."""
    out: list[str] = []
    for e in aleas_liste or []:
        txt = f"{e.get('nature') or ''} {e.get('libelle') or ''}".lower()
        for frag, lab in _HAZARDS:
            if frag in txt and lab not in out:
                out.append(lab)
    return out


def _risques_rows(fiche: dict, commune: str | None) -> list[dict]:
    """ANNONCE-5-FIX — table des risques : UNE LIGNE PAR ALÉA (inondation, mouvement de terrain…), sans
    doublon DEAL/PPR. Chaque ligne : niveau d'aléa (Géorisques), zone PPR + part de la parcelle, et
    l'implication (déduite de la zone). On FUSIONNE les entrées « Aléa X » (intensité Géorisques) et
    « PPR — zone rouge/bleue » (règlement) qui portaient jusqu'ici le MÊME aléa deux fois. Tiré de la
    fiche, jamais inventé ; un aléa non identifiable est omis."""
    aleas = (fiche or {}).get("aleas") or {}
    liste = aleas.get("liste") or []
    # 1) intensité Géorisques par aléa (entrées « Aléa X »).
    intensite: dict[str, dict] = {}
    # 2) zone PPR la plus contraignante touchant la parcelle (rouge > bleue) + part + document.
    ppr_zone = None   # "rouge" | "bleue"
    ppr_part = None
    ppr_doc = None
    hazards: list[str] = []

    def _noms(txt: str) -> list[str]:
        out = []
        for frag, lab in _HAZARDS:
            if frag in (txt or "").lower() and lab not in out:
                out.append(lab)
        return out

    for e in liste:
        nat = (e.get("nature") or "")
        natl = nat.lower()
        if natl.startswith("aléa") or natl.startswith("alea"):
            for lab in _noms(f"{nat} {e.get('libelle') or ''}"):
                if lab not in hazards:
                    hazards.append(lab)
                niv = e.get("niveau")
                intensite[lab] = {"niveau": str(niv).capitalize() if niv else None,
                                  "part_pct": e.get("part_pct")}
        elif "ppr" in natl:
            z = "rouge" if "rouge" in natl else ("bleue" if "bleu" in natl else None)
            if z == "rouge" or (z == "bleue" and ppr_zone != "rouge"):
                ppr_zone, ppr_part = z, e.get("part_pct")
                ppr_list = e.get("ppr") or []
                an = max((str(p.get("approbation") or "")[:4] for p in ppr_list if p.get("approbation")), default="")
                ppr_doc = (f"PPR {commune}".strip() + (f" ({an})" if an else "")) if (ppr_list or z) else None
            for lab in _noms(e.get("libelle") or ""):
                if lab not in hazards:
                    hazards.append(lab)
        else:
            for lab in _noms(f"{nat} {e.get('libelle') or ''}"):
                if lab not in hazards:
                    hazards.append(lab)

    def _implique(zone: str | None, doc: str | None) -> str:
        if zone == "rouge":
            return (f"Zone rouge du {doc} — secteur très contraint : construction neuve exclue, extension "
                    "sous prescriptions strictes (étude géotechnique)." if doc else
                    "Zone rouge du PPR — secteur très contraint, construction neuve exclue.")
        if zone == "bleue":
            return (f"Zone bleue du {doc} — constructible sous prescriptions (étude géotechnique, eaux "
                    "pluviales)." if doc else "Zone bleue du PPR — constructible sous prescriptions.")
        return "Aléa signalé (Géorisques), hors zonage PPR réglementaire sur la parcelle."

    # NU-3-J#4 — la LISTE des hazards vient du compteur UNIQUE `distinct_hazards` (même scan que la
    # tuile « Aléas » de la fiche `aleas.n_hazards`) : `len(_risques_rows) == aleas.n_hazards`, garanti.
    hazards = distinct_hazards(liste)
    rows = []
    for lab in hazards:
        it = intensite.get(lab) or {}
        niveau = it.get("niveau")
        if not niveau:
            niveau = {"rouge": "Fort", "bleue": "Modéré"}.get(ppr_zone or "", "Signalé")
        part = it.get("part_pct") if it.get("part_pct") is not None else ppr_part
        zone_part = None
        if ppr_zone:
            zone_part = f"Zone {ppr_zone}" + (f" · {int(part)} %" if isinstance(part, (int, float)) else "")
        elif isinstance(part, (int, float)):
            zone_part = f"{int(part)} %"
        rows.append({"alea": lab, "niveau": niveau, "zone_part": zone_part,
                     "implique": _implique(ppr_zone, ppr_doc)})
    return rows


def _contrainte_limitante(db, idu: str, fiche: dict, zone: str | None, commune: str | None) -> dict:
    """ANNONCE-5-FIX — LA règle qui limite la capacité, avec ses chiffres : hauteur (bâti existant au-delà
    du plafond), emprise (occupation proche du maximum), assiette (aléa fort déduit). Renvoie {"detail":…}
    (phrase chiffrée) ou {} si AUCUNE règle ne mord nettement. Jamais une phrase qui contredit le tableau."""
    try:
        from ..faisabilite.zonage import resolve_zone
        zr = resolve_zone(zone, commune) if zone else None
    except Exception:  # noqa: BLE001
        zr = None
    pot = (fiche or {}).get("potentiel_transformation") or {}
    surface = (fiche or {}).get("surface_m2") or (fiche or {}).get("contenance_m2")
    emprise = _emprise_bati_fiche_m2(fiche)   # FIX-P-1 (P-03) — emprise UNIQUE de la fiche (BD TOPO clippée)
    faitage = pot.get("hauteur_faitage_lidar_m")
    hf_max = getattr(zr, "hf_m", None) if zr else None
    emp_max = getattr(zr, "emprise_sol_pct", None) if zr else None
    # 1) hauteur : le bâti existant dépasse-t-il déjà le plafond ?
    if isinstance(faitage, (int, float)) and isinstance(hf_max, (int, float)) and faitage > hf_max + 0.5:
        return {"regle": "hauteur",
                "detail": (f"la hauteur limite : le bâti existant atteint un faîtage mesuré de {_num(faitage)} m "
                           f"pour {_num(hf_max)} m autorisés — pas de marge en surélévation.")}
    # 2) emprise : l'occupation au sol est-elle proche du maximum ?
    if (isinstance(emprise, (int, float)) and isinstance(surface, (int, float)) and surface > 0
            and isinstance(emp_max, (int, float))):
        used = emprise / surface * 100
        if used >= emp_max - 6:
            return {"regle": "emprise",
                    "detail": (f"l'emprise au sol limite : le bâti occupe déjà {_num(used)} % de la parcelle "
                               f"pour {_num(emp_max)} % autorisés.")}
    # 3) assiette : l'aléa fort réduit-il fortement la surface mobilisable ?
    ass = _assiette_alea_deduite(db, idu)
    if (isinstance(ass, (int, float)) and isinstance(surface, (int, float)) and surface > 0
            and ass < surface * 0.7):
        return {"regle": "assiette",
                "detail": (f"l'assiette constructible limite : l'aléa fort déduit ramène la surface "
                           f"mobilisable à {_fmt_m2_fr(ass)} sur {_fmt_m2_fr(round(surface))}.")}
    return {}


def _classement_phrase(bande: str | None, libelle: str | None, contrainte: dict | None) -> str | None:
    """ANNONCE-5-FIX — phrase du classement DÉRIVÉE DES RÈGLES : elle nomme la règle qui limite avec ses
    chiffres (via `_contrainte_limitante`), ou dit qu'aucune ne mord. Jamais une phrase qui contredit le
    tableau des règles au-dessus. None si pas de bande."""
    if not bande:
        return None
    tete = f"Classement {bande} · {libelle}" if libelle and libelle != bande else f"Classement {bande}"
    if str(bande) == "NC":
        return f"{tete} : analyse incomplète — une donnée réglementaire manque pour classer la parcelle."
    detail = (contrainte or {}).get("detail")
    if detail:
        return f"{tete} : {detail}"
    if str(bande) in ("A", "B"):
        return f"{tete} : aucune règle de la zone ne mord nettement — la marge constructible reste ouverte."
    return (f"{tete} : aucune règle réglementaire ne mord nettement ; la marge restante tient à la "
            "configuration de la parcelle (forme, accès, bâti en place).")


def _a_verifier(fiche: dict, nature: str, zone: str | None) -> list[str]:
    """« Ce qu'il reste à vérifier » — AU PLUS 3 points, DÉRIVÉS des données (aléa présent, bâti existant,
    état inconnu / viabilisation). Jamais un conseil générique hors données."""
    pts = []
    aleas = (fiche or {}).get("aleas") or {}
    batie = nature in ("bati_encore", "bati_max")
    if batie:
        pts.append("L'état du bâti et les travaux récents, non connus du modèle.")
        pts.append("La conformité du bâti existant (permis, déclarations) avant tout projet d'extension.")
    else:
        pts.append("La desserte et la viabilisation du terrain (eau, voirie, assainissement).")
    if (aleas.get("n") or 0) > 0:
        z = f" de la zone {zone}" if zone else ""
        pts.append(f"Le règlement écrit{z} pour les prescriptions du PPR (étude géotechnique, eaux pluviales).")
    elif not batie:
        pts.append("Les contraintes d'accès et de pente sur le terrain.")
    return pts[:3]


def rapport_parcelle(db, idu: str, fiche: dict | None = None, surface_hab: float | None = None) -> dict:
    """ANNONCE-5 — le rapport PARCELLE complet (variante adresse, 2 pages du PDF) : POINT UNIQUE lu par
    l'écran ET par le PDF → aucune divergence. Compose la fiche servie, l'estimation (comparables + valeur
    indicative), le foncier (règles calibrées face aux mesures de la parcelle), le classement (run servi +
    phrase gravée), les risques et le marché de la commune. Aucun recalcul de prix ici."""
    from ..api.app import parcel_fiche
    if fiche is None:
        fiche = parcel_fiche(idu, db=db)
    rp = (fiche or {}).get("reglement_plu") or {}
    zones = rp.get("zones") or []
    zone = (zones[0] or {}).get("zone") if zones and isinstance(zones[0], dict) else None
    commune = (fiche or {}).get("commune")
    nature = _nature_parcelle(db, idu)
    est = estimation_annonce(db, idu, fiche, surface_hab=surface_hab)
    try:
        cls = _classement_bande(db, idu)
    except Exception:  # noqa: BLE001
        cls = {}
    try:
        from ..api.app import parcel_exposition
        expo = (parcel_exposition(idu, db=db) or {}).get("orientation")
    except Exception:  # noqa: BLE001 — l'exposition est une tuile « plus », jamais un bloqueur
        expo = None
    type_bien = est.get("type_bien")
    # ESTIMER-2 — le libellé de nature suit le verdict de l'estimation (nature lue sur la dernière vente
    # DVF, E-022) : copropriété, terrain nu, bâti non mesuré (D-012 — jamais « bâtie, maison » sans
    # mesure), sinon « Parcelle bâtie » + type (maison/appartement).
    est_nat = est.get("nature")
    if est_nat == "copropriete":   # CHASSE-4-FIX (C4-003)
        nature_label = "Copropriété"
    elif est_nat == "nue":
        nature_label = "Parcelle nue"
    elif est_nat == "bati_non_mesure":   # D-012
        nature_label = "Bâti non mesuré"
    else:
        suff = {"maison": ", maison", "appartement": ", appartement"}.get(type_bien or "", "")
        nature_label = f"Parcelle bâtie{suff}"
    from ..faisabilite.marche_commune import marche_commune_bloc
    try:
        marche = marche_commune_bloc(db, commune) if commune else None
    except Exception as exc:  # noqa: BLE001
        log.warning("rapport parcelle %s : marché commune indisponible (%s)", idu, exc)
        marche = None
    contrainte = _contrainte_limitante(db, idu, fiche, zone, commune)
    # RECETTE-4 — « Dernière vente » (date + prix DVF de la parcelle), lue de la fiche (dvf_parcelle.
    # derniere_mutation) → MÊME source que l'écran. None = aucune mutation (le PDF affiche « aucune depuis 2014 »).
    _dm = ((fiche or {}).get("dvf_parcelle") or {}).get("derniere_mutation") or {}
    derniere_vente = ({"date": _dm.get("date_mutation"), "valeur": _dm.get("valeur")}
                      if _dm.get("date_mutation") else None)
    return {
        "idu": idu, "adresse": (fiche or {}).get("adresse"), "commune": commune,
        # NU-G-003 — surface de TERRAIN = contenance cadastrale (comme la fiche/Comparer : 907, pas le
        # dessin 913), repli dessin si la contenance manque. Une seule notion de surface entre écrans.
        "zone": zone, "surface_m2": ((fiche or {}).get("surface_terrain_m2")
                                     if (fiche or {}).get("surface_terrain_m2") is not None
                                     else (fiche or {}).get("surface_m2")), "nature_label": nature_label,
        "exposition": expo,
        "estimation": est,
        "derniere_vente": derniere_vente,
        "classement": {"bande": cls.get("bande"), "libelle": cls.get("libelle"),
                       "phrase": _classement_phrase(cls.get("bande"), cls.get("libelle"), contrainte)},
        "foncier": {"zone": zone, "commune": commune,
                    "regles": _regles_zone(zone, commune),
                    "parcelle": _parcelle_mesures(db, idu, fiche)},
        "risques": _risques_rows(fiche, commune),
        "marche": marche,
        "a_verifier": _a_verifier(fiche, nature, zone),
    }


@router.get("/radar/annonce/rapport/{idu}")
def radar_annonce_rapport(
    idu: str,
    surface_hab: float | None = Query(None, gt=0, le=100000),
) -> dict:
    """ANNONCE-5 — le rapport PARCELLE complet (adresse) servi à l'écran ET au PDF (même point).
    Lecture seule de la fiche servie. Parcelle inconnue → structure minimale, jamais un 500.
    ESTIMER-PRECISION-1 — `surface_hab` (facultatif) : surface habitable saisie → le total l'utilise."""
    from ..api.app import parcel_fiche
    with session_scope() as db:
        try:
            fiche = parcel_fiche(idu, db=db)
        except ValueError:
            return {"idu": idu, "introuvable": True}
        return rapport_parcelle(db, idu, fiche, surface_hab=surface_hab)


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
