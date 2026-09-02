"""RADAR P1 · V2 — INTAKE : contrôle commune, dédoublonnage, dépôt d'un brouillon, validation.

Rien n'entre en base VALIDÉE avant le clic « Valider » de Vic : le dépôt crée un brouillon
(`pige_faits.valide_at = NULL`) ; `valider()` le promeut (statut `active`, événement `pige.nouvelle`).
Contrôle commune ∈ 24 (sinon rejet motivé, rien en base). Dédoublonnage selon V0 §3. Après extraction,
le rattachement de P2 est réutilisé (`rattachement.rattacher`), jamais réécrit.
"""
from __future__ import annotations

import hashlib
import unicodedata

from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import communes
from . import extraction, portails, rattachement
from .tables import EV_BAISSE_PRIX, EV_NOUVELLE, captures_dir, enregistrer_fraicheur, journaliser

# tolérances de dédoublonnage inter-portails (mandat V0 §3).
TOL_PRIX = 0.02          # ± 2 %
TOL_SURFACE = 0.05       # ± 5 %


def _norm(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", (s or "").strip().lower())
                   if unicodedata.category(c) != "Mn")


_COMMUNE_PAR_NORME = {_norm(nom): nom for nom in communes._OFFICIAL_BY_NAME}


def resoudre_commune(nom: str | None) -> tuple[str, str] | None:
    """Nom de commune (tel qu'extrait) → (nom officiel, insee) si ∈ 24, sinon None. Insensible casse/accents."""
    officiel = _COMMUNE_PAR_NORME.get(_norm(nom or ""))
    if not officiel:
        return None
    return officiel, communes._OFFICIAL_BY_NAME[officiel]


def _bien_jumeau(db: Session, commune: str, prix, surface_hab, surface_terrain) -> int | None:
    """V0 §3 — même commune ∧ prix ±2 % ∧ (surface_hab ±5 % ∨ surface_terrain ±5 %) → même bien."""
    if prix is None or (surface_hab is None and surface_terrain is None):
        return None
    return db.execute(text(
        """SELECT b.bien_id FROM pige_biens b JOIN pige_faits f ON f.bien_id = b.bien_id
           WHERE b.commune = :c AND f.prix IS NOT NULL
             AND abs(f.prix - :p) <= :tolp * :p
             AND ( (CAST(:sh AS numeric) IS NOT NULL AND f.surface_hab IS NOT NULL
                    AND abs(f.surface_hab - :sh) <= :tols * :sh)
                OR (CAST(:st AS numeric) IS NOT NULL AND f.surface_terrain IS NOT NULL
                    AND abs(f.surface_terrain - :st) <= :tols * :st) )
           ORDER BY b.bien_id LIMIT 1"""),
        {"c": commune, "p": prix, "tolp": TOL_PRIX, "tols": TOL_SURFACE,
         "sh": surface_hab, "st": surface_terrain}).scalar()


def _stocker_capture(image: bytes, media_type: str) -> tuple[str, str]:
    """Écrit la capture dans le répertoire PRIVÉ (jamais servi par le web). Retourne (chemin, hash)."""
    h = hashlib.sha256(image).hexdigest()
    ext = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}.get(
        media_type, ".bin")
    d = captures_dir()
    d.mkdir(parents=True, exist_ok=True)
    chemin = d / f"{h}{ext}"
    if not chemin.exists():
        chemin.write_bytes(image)
    return str(chemin), h


def _lien_valide(lien: str) -> bool:
    """RD-504 (chasse) — le lien sortant doit être une URL http(s) propre : il devient le bouton
    « Voir l'annonce » servi aux CLIENTS (rendu en <a href>). On refuse vide/malformé/`javascript:`/
    `data:` (vecteur XSS) et les URLs déraisonnablement longues."""
    u = (lien or "").strip()
    return (u[:7] == "http://" or u[:8] == "https://") and " " not in u and "\n" not in u and len(u) <= 2000


def _clamp_date_publication(faits: dict) -> None:
    """RD-506 (chasse) — une date de publication dans le FUTUR est une lecture impossible (anti-invention) :
    on la remet à null plutôt que d'écrire une date fausse en base."""
    from datetime import date
    from ..tz import today_reunion
    dp = faits.get("date_publication")
    if isinstance(dp, str) and dp:
        try:
            if date.fromisoformat(dp[:10]) > today_reunion():
                faits["date_publication"] = None
        except ValueError:
            faits["date_publication"] = None   # date illisible → null, jamais devinée


def deposer(db: Session, image: bytes, media_type: str, lien: str, *, geocode=None) -> dict:
    """Extraction → contrôle commune → dédoublonnage → brouillon + capture + rattachement (P2).
    Retourne un PROPOSITION (jamais validée). `statut` ∈ echec_extraction | rejet_lien | rejet_commune |
    doublon_url | echec_stockage | a_valider (avec fusion_proposee éventuelle)."""
    lien = (lien or "").strip()
    if not _lien_valide(lien):
        return {"statut": "rejet_lien", "motif": "lien invalide — une URL http(s) est requise", "portail": "autre"}
    ex = extraction.extraire(db, image, media_type, lien)
    if not ex["ok"]:
        return {"statut": "echec_extraction", "motif": ex["motif"], "portail": ex["portail"]}

    faits = ex["faits"]
    _clamp_date_publication(faits)
    resolu = resoudre_commune(faits.get("commune"))
    if not resolu:
        # hors des 24 communes → rejet à l'intake, RIEN n'entre en base.
        return {"statut": "rejet_commune",
                "motif": f"commune « {faits.get('commune') or '?'} » hors des 24 communes du périmètre",
                "portail": ex["portail"]}
    commune, insee = resolu

    # URL déjà connue → proposer une mise à jour de prix, PAS une création.
    connue = db.execute(text(
        "SELECT a.bien_id, f.prix FROM pige_annonces a JOIN pige_faits f ON f.bien_id = a.bien_id "
        "WHERE a.url_sortante = :u LIMIT 1"), {"u": lien}).mappings().first()
    if connue:
        return {"statut": "doublon_url", "bien_id": connue["bien_id"], "propose": "maj_prix",
                "prix_ancien": connue["prix"], "prix_nouveau": faits.get("prix"), "portail": ex["portail"]}

    jumeau = _bien_jumeau(db, commune, faits.get("prix"), faits.get("surface_hab"),
                          faits.get("surface_terrain"))

    # RD-501 (chasse) — la capture est stockée AVANT toute écriture en base : si le répertoire privé est
    # inaccessible (droits, disque plein, montage read-only), on refuse PROPREMENT et RIEN n'entre en base
    # (l'ancien ordre laissait un bien SANS capture committé par le session_scope de l'endpoint).
    try:
        chemin, h = _stocker_capture(image, media_type)
    except OSError as exc:
        # RV2-V1 — le motif NOMME le chemin fautif (plus de « répertoire privé inaccessible » générique) :
        # un admin doit lire QUEL répertoire créer/chown, pas deviner.
        return {"statut": "echec_stockage",
                "motif": f"capture non stockée : le répertoire privé {captures_dir()} est inaccessible "
                         "en écriture — rien enregistré (créer le répertoire + droits, voir EXPLOITATION)",
                "detail": str(exc)[:160], "portail": ex["portail"]}

    est_copro = faits.get("type") == "appartement"
    ratt = rattachement.rattacher(
        db, commune=commune, commune_insee=insee,
        surface_hab=faits.get("surface_hab"), surface_terrain=faits.get("surface_terrain"),
        dpe_classe=faits.get("dpe_classe"), dpe_conso=faits.get("dpe_conso"),
        piscine=None, adresse=None, geocode=geocode)

    bien_id = db.execute(text(
        "INSERT INTO pige_biens (commune, type_bien, est_copro, idu, rattachement_niveau, "
        " rattachement_confiance, statut, date_publication) "
        "VALUES (:c, :t, :cp, :idu, :niv, :conf, 'active', :dp) RETURNING bien_id"),
        {"c": commune, "t": faits.get("type"), "cp": est_copro, "idu": ratt.get("idu"),
         "niv": ratt["niveau"], "conf": ratt.get("confiance"),
         "dp": faits.get("date_publication")}).scalar()
    db.execute(text(
        "INSERT INTO pige_annonces (bien_id, portail, url_sortante) VALUES (:b, :p, :u)"),
        {"b": bien_id, "p": ex["portail"], "u": lien})
    # étiquettes Sourcé/Estimé/Absent par champ : présent = Sourcé (lu sur la capture) sinon Absent.
    etiquettes = {c: ("source" if faits[c] is not None else "absent") for c in extraction.CHAMPS}
    fraicheur = "publication" if faits.get("date_publication") else "saisie"
    import json as _json
    db.execute(text(
        "INSERT INTO pige_faits (bien_id, prix, type_bien, pieces, surface_hab, surface_terrain, "
        " dpe_classe, dpe_conso, dpe_ges, particulier_pro, fraicheur_source, etiquettes, a_verifier) "
        "VALUES (:b,:prix,:t,:pi,:sh,:st,:dc,:dco,:dg,:pp,:fr, CAST(:et AS jsonb), CAST(:av AS jsonb))"),
        {"b": bien_id, "prix": faits.get("prix"), "t": faits.get("type"), "pi": faits.get("pieces"),
         "sh": faits.get("surface_hab"), "st": faits.get("surface_terrain"),
         "dc": faits.get("dpe_classe"), "dco": faits.get("dpe_conso"), "dg": faits.get("dpe_ges"),
         "pp": faits.get("particulier_pro"), "fr": fraicheur,
         "et": _json.dumps(etiquettes), "av": _json.dumps(ex["champs_a_verifier"])})
    db.execute(text(
        "INSERT INTO pige_captures (bien_id, chemin_prive, hash) VALUES (:b, :c, :h)"),
        {"b": bien_id, "c": chemin, "h": h})
    enregistrer_fraicheur(db)   # D4 — la collecte met à jour la fraîcheur du Radar au registre
    db.commit()
    return {"statut": "a_valider", "bien_id": bien_id, "faits": faits,
            "confiances": ex["confiances"], "champs_a_verifier": ex["champs_a_verifier"],
            "rattachement": ratt, "portail": ex["portail"], "portail_inconnu": ex["portail_inconnu"],
            "fusion_proposee": jumeau}


_TYPES_BIEN_OK = {"maison", "terrain", "appartement", "immeuble"}


def valider_corrections(corr: dict) -> dict:
    """RD-502 (chasse) — VALIDE les corrections manuelles avant écriture. Un champ hors bornes/type est
    REFUSÉ proprement (ValueError, message honnête) plutôt qu'écrit faux en base OU crashé en 500 par le
    type SQL. Retourne un dict nettoyé (None = champ effacé). Anti-invention : on ne devine rien."""
    out: dict = {}

    def entier(k, v, lo, hi):
        if v is None:
            return None
        if isinstance(v, bool) or not isinstance(v, (int, float)) or (isinstance(v, float) and v != int(v)):
            raise ValueError(f"{k} : entier attendu")
        iv = int(v)
        if not (lo <= iv <= hi):
            raise ValueError(f"{k} : hors bornes ({lo}–{hi})")
        return iv

    def nombre(k, v, lo, hi):
        if v is None:
            return None
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise ValueError(f"{k} : nombre attendu")
        if not (lo <= v <= hi):
            raise ValueError(f"{k} : hors bornes ({lo}–{hi})")
        return v

    for k in corr:
        v = corr[k]
        if k == "prix":
            out[k] = entier("prix", v, 1, 100_000_000)
        elif k == "pieces":
            out[k] = entier("pieces", v, 0, 100)
        elif k in ("dpe_conso", "dpe_ges"):
            out[k] = entier(k, v, 0, 100_000)
        elif k in ("surface_hab", "surface_terrain"):
            out[k] = nombre(k, v, 0, 10_000_000)
        elif k == "dpe_classe":
            out[k] = None if v in (None, "") else (v.upper() if isinstance(v, str) and v.upper() in set("ABCDEFG") else _raise(f"dpe_classe : lettre A–G attendue"))
        elif k == "particulier_pro":
            out[k] = None if v in (None, "") else (v if v in ("particulier", "pro") else _raise("particulier_pro : « particulier » ou « pro »"))
        elif k == "type":
            out[k] = None if v in (None, "") else (v if v in _TYPES_BIEN_OK else _raise(f"type : un de {sorted(_TYPES_BIEN_OK)}"))
        else:
            out[k] = v   # champs non gérés (ex. date_publication) passent tels quels
    return out


def _raise(msg: str):
    raise ValueError(msg)


def _proposer_rattachement(db: Session, bien_id: int) -> None:
    """RADAR S5 — à la validation, calcule une PROPOSITION de rattachement (best-effort) et l'écrit
    comme rattachement_etat + rattachement_pistes. DOCTRINE : jamais d'idu automatique — un rattachement
    ne s'engage que par un clic HUMAIN (Instruire → « C'est cette parcelle »). Cette proposition sert
    seulement à trier la file (« à rattacher d'abord ») et à montrer les candidates. Best-effort :
    tout accident (géocodage, DB) laisse l'état inchangé plutôt que de casser la validation.

    Position : on prend les coordonnées déjà portées par le bien (géoloc du portail, html_next) ; sinon,
    SI le fait porte une adresse exploitable, on la géocode (BAN). Sans coordonnée dérivable, la cascade
    rend honnêtement 'non_rattachee' (commune seule) — on n'invente aucune parcelle."""
    from . import rattachement_html
    rec = db.execute(text(
        "SELECT b.bien_id, b.commune, b.type_bien AS type, b.est_copro, b.lat, b.lng, "
        "       f.surface_terrain, f.surface_hab, f.annee_construction "
        "FROM pige_biens b JOIN pige_faits f ON f.bien_id = b.bien_id WHERE b.bien_id = :b"),
        {"b": bien_id}).mappings().first()
    if not rec:
        return
    rec = dict(rec)
    if rec.get("lng") is None or rec.get("lat") is None:
        # pas de géoloc portail : on tente l'adresse si le fait en porte une (aucune ne l'est aujourd'hui,
        # mais le point reste ouvert). Sans coordonnée, rattacher() rend 'non_rattachee' proprement.
        adresse = _adresse_du_bien(db, bien_id)
        if adresse:
            try:
                from ..geocode import geocode_ban
                g = geocode_ban(adresse)
                rec["lng"], rec["lat"] = g["lon"], g["lat"]
            except Exception:  # noqa: BLE001 — BAN KO / adresse introuvable : on n'invente pas de position
                pass
    ratt = rattachement_html.rattacher(db, rec)
    # on n'écrit QUE l'état + les pistes (candidates) : jamais l'idu (le lien reste un clic humain).
    import json as _json
    db.execute(text(
        "UPDATE pige_biens SET rattachement_etat = :e, rattachement_pistes = CAST(:p AS jsonb) "
        "WHERE bien_id = :b AND rattachement_humain = false AND idu IS NULL"),
        {"e": ratt.get("etat", "non_rattachee"),
         "p": _json.dumps(ratt.get("pistes") or []), "b": bien_id})


def _adresse_du_bien(db: Session, bien_id: int) -> str | None:
    """RADAR S5 — cherche une adresse exploitable dans les faits (source_brute JSON). Retourne None si
    aucune : on ne devine pas d'adresse à partir d'une commune seule (ce serait un faux point)."""
    import json as _json
    sb = db.execute(text("SELECT source_brute FROM pige_faits WHERE bien_id = :b"), {"b": bien_id}).scalar()
    if not sb:
        return None
    try:
        d = sb if isinstance(sb, dict) else _json.loads(sb)
    except (TypeError, ValueError):
        return None
    for k in ("adresse", "address", "street_address", "rue", "localisation"):
        v = d.get(k) if isinstance(d, dict) else None
        if isinstance(v, str) and len(v.strip()) >= 5:
            return v.strip()
    return None


def valider(db: Session, bien_id: int, faits_corriges: dict, *, valide_par: int | None = None) -> dict:
    """Clic « Valider » de Vic : applique les corrections (VALIDÉES, RD-502), promeut le brouillon
    (valide_at), statut active, journalise `pige.nouvelle`. Un prix plus bas → `pige.baisse_prix`."""
    faits_corriges = valider_corrections(faits_corriges or {})
    ancien = db.execute(text("SELECT prix FROM pige_faits WHERE bien_id = :b"), {"b": bien_id}).scalar()
    cols = {k: faits_corriges[k] for k in
            ("prix", "pieces", "surface_hab", "surface_terrain", "dpe_classe", "dpe_conso",
             "dpe_ges", "particulier_pro") if k in faits_corriges}
    if "type" in faits_corriges:
        cols["type_bien"] = faits_corriges["type"]
    if cols:
        sets = ", ".join(f"{k} = :{k}" for k in cols)
        db.execute(text(f"UPDATE pige_faits SET {sets}, valide_at = now(), valide_par = :vp, "
                        f"updated_at = now() WHERE bien_id = :b"), {**cols, "vp": valide_par, "b": bien_id})
    else:
        db.execute(text("UPDATE pige_faits SET valide_at = now(), valide_par = :vp WHERE bien_id = :b"),
                   {"vp": valide_par, "b": bien_id})
    nouveau = faits_corriges.get("prix", ancien)
    if ancien is not None and nouveau is not None and nouveau != ancien:
        db.execute(text("INSERT INTO pige_prix_historique (bien_id, ancien_prix, nouveau_prix) "
                        "VALUES (:b, :a, :n)"), {"b": bien_id, "a": ancien, "n": nouveau})
        if nouveau < ancien:
            journaliser(db, EV_BAISSE_PRIX, f"Baisse de prix — bien #{bien_id}",
                        detail=f"{ancien} € → {nouveau} €", dedup=f"pige:baisse:{bien_id}:{nouveau}")
    db.execute(text("UPDATE pige_biens SET statut = 'active', date_derniere_confirmation = now() "
                    "WHERE bien_id = :b"), {"b": bien_id})
    # RADAR S5 — proposition de rattachement best-effort (JAMAIS d'idu auto : le lien reste un clic humain).
    # Enveloppée : un accident (géocodage, DB) ne casse jamais la validation d'un bien.
    try:
        _proposer_rattachement(db, bien_id)
    except Exception:  # noqa: BLE001
        pass
    commune = db.execute(text("SELECT commune FROM pige_biens WHERE bien_id = :b"),
                         {"b": bien_id}).scalar()
    journaliser(db, EV_NOUVELLE, f"Nouveau bien Radar — {commune}",
                detail=f"bien #{bien_id} validé", dedup=f"pige:nouvelle:{bien_id}")
    db.commit()
    return {"bien_id": bien_id, "statut": "active", "valide": True}
