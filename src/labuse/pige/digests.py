"""RADAR-DIGESTS — l'alerte de veille de fin de journée (heure Réunion), template Brevo `radar_alerte`.

VEILLE-FIX-1 (lot 2) — RADAR SELON LES CRITÈRES : un client ne reçoit un mail QUE si une de ses veilles
Radar matche au moins une annonce du jour, avec SEULEMENT ces annonces-là. Aucune veille qui matche →
aucun mail. Le digest « à tous les comptes actifs » (ancien template 12 `radar_digest`) est RETIRÉ.

(13) ALERTE de veille → un mail PAR VEILLE déclenchée, aux clients dont une veille matche (`radar_alerte`).

CONTRAINTES BREVO (constatées en test réel) :
 1. AUCUNE boucle {% for %} dans un template — l'éditeur Brevo casse les balises Jinja qui enjambent des
    lignes de tableau. Donc le HTML des cartes est CONSTRUIT PAR LE CODE et passé dans un seul param
    `CARTES`, rendu avec | safe.
 2. Rendu sans échappement ⇒ CHAQUE valeur venant d'une annonce (commune, portail, prix, lien, libellé
    de veille) est ÉCHAPPÉE CÔTÉ SERVEUR avant d'entrer dans le HTML (donnée de portails tiers).

Jamais de mail vide (aucun bien ⇒ aucun envoi). Plafond 10 cartes + « et N autres ». Idempotent sur la
journée (ne ré-envoie pas le même digest/alerte). Échec BRUYANT (log.error + event système, dashboard).
Mode dry-run : construit tout, n'envoie rien, écrit le HTML produit dans un fichier pour inspection.
"""
from __future__ import annotations

import html as _html
import logging
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import mail   # CONNEXIONS-2 Lot 9.1 (KO-12) — façade unique (mail.envoyer_template → Brevo)
from ..api.events import creer_notification
from ..tz import today_reunion
from . import portails, veille as veille_mod

log = logging.getLogger("labuse.pige.digests")

INK, GREY, GREEN = "#1c1917", "#78716c", "#16A34A"
_MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
         "septembre", "octobre", "novembre", "décembre"]
CAP = 10          # plafond de cartes par mail (au-delà : « et N autres »)


def _esc(v) -> str:
    """Échappement HTML systématique (contrainte 2) — texte ET attribut (guillemets inclus)."""
    return _html.escape("" if v is None else str(v), quote=True)


def _fmt_prix(n: int | None, suffixe: str = "€") -> str | None:
    return f"{n:,} {suffixe}".replace(",", " ") if n is not None else None


def _fmt_date_fr(d) -> str:
    return f"{d.day} {_MOIS[d.month - 1]} {d.year}"


def _lien_radar(base_url: str) -> str:
    return f"{(base_url or '').rstrip('/')}/socle/#m=radar"


# ── données ──────────────────────────────────────────────────────────────────────────────

def _biens_du_jour(db: Session, depuis=None) -> list[dict]:
    """Biens VALIDÉS saisis DEPUIS `depuis` (timestamptz), statuts vivants, enrichis pour la carte :
    portail + lien + date de relevé (dernière annonce), baisse de prix (dernier constat à la baisse).

    VEILLE-FIX-2 (Lot A) — `depuis=None` garde le comportement historique « du jour » (début de journée
    Réunion). `radar-cloche` passe désormais le HORODATAGE DU DERNIER PASSAGE du job : une annonce
    déposée à 21 h–minuit (capture du soir) est ainsi vue le lendemain matin, alors qu'elle échappait à
    la fenêtre « aujourd'hui »."""
    borne = ("((now() AT TIME ZONE 'Indian/Reunion')::date AT TIME ZONE 'Indian/Reunion')"
             if depuis is None else ":depuis")
    rows = db.execute(text(
        f"""SELECT b.bien_id, b.commune, b.type_bien, b.est_copro, b.idu,
                  f.prix, f.surface_hab, f.surface_terrain, f.particulier_pro,
                  a.portail, a.url_sortante, coalesce(a.date_saisie, b.date_premiere_saisie) AS date_releve,
                  ph.ancien_prix, ph.nouveau_prix
           FROM pige_biens b JOIN pige_faits f ON f.bien_id = b.bien_id
           LEFT JOIN LATERAL (SELECT portail, url_sortante, date_saisie FROM pige_annonces
                              WHERE bien_id = b.bien_id ORDER BY date_saisie DESC LIMIT 1) a ON true
           LEFT JOIN LATERAL (SELECT ancien_prix, nouveau_prix FROM pige_prix_historique
                              WHERE bien_id = b.bien_id AND nouveau_prix < ancien_prix
                              ORDER BY date_constat DESC LIMIT 1) ph ON true
           WHERE f.valide_at IS NOT NULL AND b.statut IN ('active','en_vente_longue')
             -- RADAR-RECETTE-1 D1c — un bien À QUALIFIER (incohérent) n'entre NI dans les digests NI
             -- dans les veilles (matche() est appelé sur cette même liste). Jamais un fait faux notifié.
             AND b.a_qualifier = false
             -- RADAR-DEPOT-2 D5 — les copropriétés (appartements) sont embasées mais JAMAIS servies comme
             -- annonces : absentes des digests ET des alertes de veille (matche() lit cette même liste).
             AND b.est_copro = false
             AND b.date_premiere_saisie >= {borne}
           ORDER BY b.bien_id DESC"""),
        ({"depuis": depuis} if depuis is not None else {})).mappings().all()
    # `faits` (sous-dict) pour `veille.matche` (contrat partagé) + champs plats pour la carte.
    out = []
    for r in rows:
        d = dict(r)
        d["faits"] = {"prix": r["prix"],
                      "surface_hab": float(r["surface_hab"]) if r["surface_hab"] is not None else None,
                      "surface_terrain": float(r["surface_terrain"]) if r["surface_terrain"] is not None else None,
                      "particulier_pro": r["particulier_pro"]}
        out.append(d)
    # RADAR-DEPOT-2 D4 — badge « sous le marché » attaché à chaque bien (référentiel une fois par
    # commune×famille). Il apparaît sur la carte mail QUAND le bien le porte — jamais un mail dédié.
    from . import signaux
    badges = signaux.badges_pour_biens(db, [
        {"bien_id": d["bien_id"], "commune": d["commune"], "type_bien": d["type_bien"],
         "a_qualifier": False, "prix": d["prix"], "idu": d.get("idu"),   # C5 — médiane locale si rattaché (mails)
         "surface_hab": d["faits"]["surface_hab"], "surface_terrain": d["faits"]["surface_terrain"]}
        for d in out])
    for d in out:
        bd = badges.get(d["bien_id"])
        d["sous_le_marche"] = bd if (bd and bd.get("calculable") and bd.get("sous_le_marche")) else None
    return out


def _carte_item(base_url: str, r: dict) -> dict:
    """Valeurs DÉJÀ FORMATÉES d'une carte (non échappées — l'échappement est fait au rendu HTML).
    La date est celle du RELEVÉ, jamais la date d'envoi ; un bien non rattaché le DIT."""
    type_label = (r.get("type_bien") or "bien").capitalize()
    if r.get("est_copro") or r.get("type_bien") == "appartement":
        type_label += " (copro)"
    surf_h, surf_t = r.get("surface_hab"), r.get("surface_terrain")
    surface = (f"{float(surf_h):.0f} m² hab." if surf_h else
               f"{float(surf_t):.0f} m² terrain" if surf_t else None)
    base_surf = float(surf_h) if surf_h else float(surf_t) if surf_t else None
    prix_m2 = (_fmt_prix(round(r["prix"] / base_surf), "€/m²") if r.get("prix") and base_surf else None)
    baisse = (_fmt_prix(r["ancien_prix"] - r["nouveau_prix"]) if r.get("ancien_prix") and r.get("nouveau_prix")
              and r["ancien_prix"] > r["nouveau_prix"] else None)
    d = r.get("date_releve")
    slm = r.get("sous_le_marche")
    sous_marche = None
    if slm and slm.get("sous_le_marche"):
        # « Sous le marché · −X % » + la référence de zone utilisée (avec son millésime + périmètre).
        ref = f"réf. {slm['perimetre']} {slm['referentiel_eur_m2']} €/m²"
        if slm.get("millesime_dvf"):
            ref += f" ({slm['millesime_dvf']})"
        sous_marche = {"pct": abs(slm["ecart_pct"]), "ref": ref}
    return {
        "titre": f"{type_label} — {r['commune']}",
        "prix": _fmt_prix(r.get("prix")) or "—",
        "prix_m2": prix_m2, "surface": surface,
        "baisse": ("−" + baisse) if baisse else None,
        "sous_marche": sous_marche,
        "parcelle": (f"Parcelle {r['idu']}" if r.get("idu") else "Non rattaché à une parcelle"),
        "date_releve": _fmt_date_fr(d.date() if hasattr(d, "date") else d) if d else "—",
        "portail": portails.nom(r["portail"]) if r.get("portail") else "le portail",
        "url": r.get("url_sortante") or _lien_radar(base_url),
        "_baisse_val": (r["ancien_prix"] - r["nouveau_prix"]) if (r.get("ancien_prix") and r.get("nouveau_prix")) else 0,
        "_bien_id": r["bien_id"],
    }


def carte_html(it: dict) -> str:
    """Le HTML d'UNE carte — CONSTRUIT PAR LE CODE (pas de boucle template). Chaque valeur échappée."""
    prix_bits = [f'<span style="color:{INK}">{_esc(it["prix"])}</span>']
    if it.get("prix_m2"):
        prix_bits.append(f'<span style="color:{GREY}">{_esc(it["prix_m2"])}</span>')
    if it.get("surface"):
        prix_bits.append(f'<span style="color:{GREY}">{_esc(it["surface"])}</span>')
    baisse = (f'<div style="font-size:13px;color:{GREEN};margin-top:2px">Baisse de prix — '
              f'{_esc(it["baisse"])}</div>') if it.get("baisse") else ""
    # RADAR-DEPOT-2 D4 — la ligne du badge « sous le marché » n'apparaît QUE quand l'annonce le porte
    # (attribut, pas un canal de notification). Écart constaté daté, avec la référence de zone utilisée.
    sm = it.get("sous_marche")
    sous_marche = (f'<div style="font-size:13px;color:{GREEN};margin-top:2px">'
                   f'Sous le marché · −{_esc(sm["pct"])} % <span style="color:{GREY}">'
                   f'· {_esc(sm["ref"])}</span></div>') if sm else ""
    return (
        f'<div style="border:1px solid #e7e5e4;border-radius:8px;padding:12px 14px;margin-bottom:10px;'
        f'font-family:Arial,Helvetica,sans-serif">'
        f'<div style="font-weight:bold;font-size:15px;color:{INK}">{_esc(it["titre"])}</div>'
        f'<div style="font-size:13px;margin-top:3px">{" · ".join(prix_bits)}</div>'
        f'{baisse}'
        f'{sous_marche}'
        f'<div style="font-size:12px;color:{GREY};margin-top:4px">{_esc(it["parcelle"])} · '
        f'Repéré le {_esc(it["date_releve"])} sur {_esc(it["portail"])}</div>'
        f'<div style="margin-top:6px"><a href="{_esc(it["url"])}" '
        f'style="color:{GREEN};font-weight:bold;text-decoration:none">'
        f'Voir l\'annonce sur {_esc(it["portail"])} →</a></div>'
        f'</div>')


def _ordonner(items: list[dict]) -> list[dict]:
    """Ordre des cartes : BAISSE DE PRIX d'abord (signal actionnable daté), puis récence (bien_id desc)."""
    return sorted(items, key=lambda x: (-(x["_baisse_val"] > 0), -x["_baisse_val"], -x["_bien_id"]))


def cartes_html(items: list[dict], base_url: str) -> str:
    """HTML de toutes les cartes, plafonné à CAP + ligne « et N autres sur le Radar »."""
    ordonnes = _ordonner([_carte_item(base_url, r) for r in items])
    haut = ordonnes[:CAP]
    html = "".join(carte_html(it) for it in haut)
    reste = len(ordonnes) - len(haut)
    if reste > 0:
        html += (f'<div style="font-size:13px;color:{GREY};font-family:Arial,sans-serif;margin:4px 0 10px">'
                 f'et {reste} autre{"s" if reste > 1 else ""} sur le Radar</div>')
    return html


# ── libellé & critères de veille (LOT 3) ────────────────────────────────────────────────

def _criteres_texte(criteria: dict) -> str:
    """Reconstruit un texte lisible depuis les critères RÉELLEMENT enregistrés (jamais un résumé
    approximatif). Un critère qui ne sait pas se dire est affiché tel quel plutôt qu'omis."""
    connus = {"commune", "communes", "type_bien", "prix_min", "prix_max", "surface_min", "surface_max",
              "surface_terrain_min", "surface_hab_min", "particulier_only", "nom"}
    bits: list[str] = []
    if criteria.get("type_bien"):
        bits.append(str(criteria["type_bien"]).capitalize())
    # VEILLE-2 (Lot 2) — commune(s) : liste `communes` (jointes par « ou ») ou `commune` seule.
    if criteria.get("communes"):
        bits.append(" ou ".join(str(c) for c in criteria["communes"]))
    elif criteria.get("commune"):
        bits.append(str(criteria["commune"]))
    # surface min/max (modèle VEILLE-2) — sur la surface pertinente du bien.
    smin, smax = criteria.get("surface_min"), criteria.get("surface_max")
    if smin and smax:
        bits.append(f"de {_fmt_prix(int(smin), 'm²')} à {_fmt_prix(int(smax), 'm²')}")
    elif smin:
        bits.append(f"plus de {_fmt_prix(int(smin), 'm²')}")
    elif smax:
        bits.append(f"moins de {_fmt_prix(int(smax), 'm²')}")
    if criteria.get("surface_terrain_min"):
        bits.append(f"plus de {_fmt_prix(int(criteria['surface_terrain_min']), 'm²')} de terrain")
    if criteria.get("surface_hab_min"):
        bits.append(f"plus de {_fmt_prix(int(criteria['surface_hab_min']), 'm²')} habitables")
    if criteria.get("prix_min"):
        bits.append(f"plus de {_fmt_prix(int(criteria['prix_min']))}")
    if criteria.get("prix_max"):
        bits.append(f"moins de {_fmt_prix(int(criteria['prix_max']))}")
    if criteria.get("particulier_only"):
        bits.append("de particulier")
    # critères inconnus : affichés tels quels, jamais silencieusement omis
    for k, v in criteria.items():
        if k not in connus:
            bits.append(f"{k} : {v}")
    return " · ".join(bits) if bits else "tous les biens"


def _libelle_veille(v: dict) -> str:
    """Libellé de la veille : celui donné par le client (`criteria.nom`) sinon dérivé des critères."""
    cr = v.get("criteria") or {}
    return cr.get("nom") or _criteres_texte(cr)


# ── envoi (idempotent, bruyant) ─────────────────────────────────────────────────────────

def _envoyer(db: Session, *, compte_id, email: str, template_key: str, dedup: str,
             params: dict, n_biens: int, cartes_html_str: str, type_envoi: str,
             dry_run: bool, dry_dir: Path | None, rapport: list) -> str:
    """UN envoi (alerte de veille). VEILLE-FIX-1 (lot 5) — passe par mail_queue COMME LES AUTRES mails
    (template Brevo 13). Idempotent (dedup mail_queue par jour), jamais vide (garanti par l'appelant),
    échec BRUYANT. Dry-run : une ligne écrite `en_attente`, RIEN envoyé. Retourne
    'simule' | 'envoye' | 'deja' | 'echec'."""
    from ..db import engine as _eng
    from ..mailfile import ensure_tables as _mq_ens, envoyer_mail as _q_envoyer
    _mq_ens(_eng())
    if dry_run and dry_dir is not None:
        dry_dir.mkdir(parents=True, exist_ok=True)
        (dry_dir / f"{type_envoi}_compte{compte_id}.html").write_text(cartes_html_str, encoding="utf-8")
    ligne = _q_envoyer(_eng(), key=template_key, to=email, params=params, compte_id=compte_id,
                       demandeur="job:radar-digests", dedup=dedup, fenetre_doublon_s=20 * 3600,
                       dry_run=dry_run)
    if dry_run:
        rapport.append({"compte_id": compte_id, "type_envoi": type_envoi, "n": n_biens, "statut": "simule"})
        return "simule"
    if ligne.get("doublon"):
        rapport.append({"compte_id": compte_id, "type_envoi": type_envoi, "n": n_biens, "statut": "deja"})
        return "deja"
    if ligne.get("etat") in ("recu", "parti"):
        rapport.append({"compte_id": compte_id, "type_envoi": type_envoi, "n": n_biens, "statut": "envoye"})
        return "envoye"
    # ÉCHEC BRUYANT (RV-013) — jamais silencieux : log.error + event système visible au dashboard.
    raison = ligne.get("erreur") or ligne.get("etat") or "inconnue"
    log.error("RADAR %s NON ENVOYÉ à compte=%s : %s", type_envoi, compte_id, raison)
    try:
        creer_notification(db, kind="systeme", compte_id=None, source="Radar",
                           titre=f"Échec envoi Radar ({type_envoi})",
                           detail=f"Compte {compte_id} : {raison}. Template Brevo 13 monté ?",
                           dedup=f"pige:digest-echec:{type_envoi}:{today_reunion().isoformat()}")
    except Exception:  # noqa: BLE001 — la trace ne doit pas masquer l'échec d'origine
        pass
    rapport.append({"compte_id": compte_id, "type_envoi": type_envoi, "n": n_biens,
                    "statut": "echec", "raison": raison})
    return "echec"


def _clients_actifs(db: Session) -> list[dict]:
    """Comptes ACTIFS + e-mail/prénom du titulaire. (RD-503 : `comptes.prenoms` n'existe pas → `c.nom`.)
    VEILLE-FIX-1 (lot 3) — un ESSAI EXPIRÉ (`essai_expire_at` passé) ne reçoit plus rien, même resté
    `actif` (la coupure ne dépend plus d'une bascule de statut par la facturation)."""
    return [dict(r) for r in db.execute(text(
        "SELECT c.id AS compte_id, c.nom AS prenom, "
        " min(u.email) FILTER (WHERE u.role='titulaire') AS email "
        "FROM comptes c LEFT JOIN utilisateurs u ON u.compte_id = c.id "
        "WHERE c.statut = 'actif' AND (c.essai_expire_at IS NULL OR c.essai_expire_at > now()) "
        "GROUP BY c.id, c.nom ORDER BY c.id")).mappings()]


# VEILLE-FIX-2 (Lot A) — HORODATAGE du dernier passage de `radar-cloche`, persistant. La fenêtre du job
# n'est plus « aujourd'hui » mais « depuis le dernier passage » (repli J-1 au premier passage) : la
# capture du soir (21 h–minuit) est vue le lendemain matin.
_WATERMARK_RADAR = "radar-cloche"


def _ensure_watermark(db: Session) -> None:
    db.execute(text("CREATE TABLE IF NOT EXISTS pige_watermark ("
                    " nom text PRIMARY KEY, ts timestamptz NOT NULL)"))


def _watermark_get(db: Session, nom: str):
    return db.execute(text("SELECT ts FROM pige_watermark WHERE nom = :n"), {"n": nom}).scalar()


def _watermark_set(db: Session, nom: str, ts) -> None:
    db.execute(text("INSERT INTO pige_watermark (nom, ts) VALUES (:n, :t) "
                    "ON CONFLICT (nom) DO UPDATE SET ts = EXCLUDED.ts"), {"n": nom, "t": ts})


def _avec_faits(r: dict) -> dict:
    """Attache le sous-dict `faits` (contrat de `veille.matche`) à une ligne de bien."""
    d = dict(r)
    d["faits"] = {"prix": r.get("prix"),
                  "surface_hab": float(r["surface_hab"]) if r.get("surface_hab") is not None else None,
                  "surface_terrain": float(r["surface_terrain"]) if r.get("surface_terrain") is not None else None,
                  "particulier_pro": r.get("particulier_pro")}
    return d


def _biens_baisses_depuis(db: Session, depuis) -> list[dict]:
    """VEILLE-FIX-2 (Lot B) — biens vivants dont une BAISSE de prix (constat le plus récent) tombe DEPUIS
    `depuis`. Matchables (mêmes filtres que _biens_du_jour). Porte ancien/nouveau prix."""
    rows = db.execute(text(
        """SELECT b.bien_id, b.commune, b.type_bien, b.idu,
                  f.prix, f.surface_hab, f.surface_terrain, f.particulier_pro,
                  a.url_sortante, ph.ancien_prix, ph.nouveau_prix
           FROM pige_biens b JOIN pige_faits f ON f.bien_id = b.bien_id
           JOIN LATERAL (SELECT ancien_prix, nouveau_prix, date_constat FROM pige_prix_historique
                         WHERE bien_id = b.bien_id AND nouveau_prix < ancien_prix
                         ORDER BY date_constat DESC LIMIT 1) ph ON true
           LEFT JOIN LATERAL (SELECT url_sortante FROM pige_annonces WHERE bien_id = b.bien_id
                              ORDER BY date_saisie DESC LIMIT 1) a ON true
           WHERE f.valide_at IS NOT NULL AND b.statut IN ('active','en_vente_longue')
             AND b.a_qualifier = false AND b.est_copro = false AND ph.date_constat >= :depuis
           ORDER BY b.bien_id DESC"""), {"depuis": depuis}).mappings().all()
    return [_avec_faits(r) for r in rows]


def _biens_retires_depuis(db: Session, depuis) -> list[dict]:
    """VEILLE-FIX-2 (Lot B) — biens RETIRÉS (retrait confirmé) depuis `depuis`, restés matchables (faits
    présents). Un retrait confirmé = statut `retiree`/`retiree_sans_vente` avec `retiree_le` renseigné."""
    rows = db.execute(text(
        """SELECT b.bien_id, b.commune, b.type_bien, b.idu, b.retiree_le,
                  f.prix, f.surface_hab, f.surface_terrain, f.particulier_pro, a.url_sortante
           FROM pige_biens b JOIN pige_faits f ON f.bien_id = b.bien_id
           LEFT JOIN LATERAL (SELECT url_sortante FROM pige_annonces WHERE bien_id = b.bien_id
                              ORDER BY date_saisie DESC LIMIT 1) a ON true
           WHERE f.valide_at IS NOT NULL AND b.statut IN ('retiree','retiree_sans_vente')
             AND b.a_qualifier = false AND b.est_copro = false
             AND b.retiree_le IS NOT NULL AND b.retiree_le >= :depuis
           ORDER BY b.bien_id DESC"""), {"depuis": depuis}).mappings().all()
    return [_avec_faits(r) for r in rows]


def _idus_suivis(db: Session) -> dict:
    """{idu: [compte_id, …]} des parcelles SUIVIES par un compte ACTIF (essai non expiré). Les suivis
    « pilote » (compte_id NULL) sont exclus (le JOIN comptes les écarte)."""
    rows = db.execute(text(
        "SELECT w.idu, w.compte_id FROM watched_parcels w JOIN comptes c ON c.id = w.compte_id "
        "WHERE w.idu IS NOT NULL AND c.statut = 'actif' "
        "AND (c.essai_expire_at IS NULL OR c.essai_expire_at > now())")).all()
    out: dict[str, list[int]] = {}
    for idu, cid in rows:
        out.setdefault(idu, []).append(cid)
    return out


def _mises_en_vente(db: Session, biens: list[dict], suivis: dict, jour) -> int:
    """VEILLE-FIX-2 (Lot B) — MISE EN VENTE d'une parcelle SUIVIE. Règle retenue : rattachement STRICT
    par `idu` (jamais « quartier » : sur un point flouté, trop de faux positifs). Une nouvelle annonce
    dont l'idu correspond à une parcelle suivie → événement PRIORITAIRE (kind `parcelle_en_vente`, cloche
    en tête) + MAIL IMMÉDIAT (grille), UNE FOIS par annonce/compte (dédup sur l'événement ET sur le mail)."""
    if not suivis:
        return 0
    from .. import config, emails, mail, mailfile
    from ..api.events import _notif_token, creer_notification
    base_url = config.get_settings().public_base_url or ""
    dry = not mail.mail_configured()
    n = 0
    for b in biens:
        idu = b.get("idu")
        if not idu or idu not in suivis:
            continue
        court = idu[8:] if len(idu) > 8 else idu
        type_label = (b.get("type_bien") or "bien").capitalize()
        prix = _fmt_prix(b["faits"].get("prix")) or "—"
        url = b.get("url_sortante") or _lien_radar(base_url)
        for cid in suivis[idu]:
            cree = creer_notification(
                db, kind="parcelle_en_vente", compte_id=cid, source="Radar", idu=idu,
                titre=f"Votre parcelle {court} est mise en vente",
                detail=f"{type_label} à {b['commune']} · {prix}", lien=url,
                dedup=f"parcelle_en_vente:{cid}:{b['bien_id']}", permanent=True)
            if not cree:
                continue                                    # déjà notifié → pas de 2ᵉ mail
        n += 1
        # mail IMMÉDIAT par compte suiveur (une fois par annonce/compte — dédup mail_queue)
        for cid in suivis[idu]:
            email = db.execute(text(
                "SELECT min(email) FILTER (WHERE role='titulaire') FROM utilisateurs WHERE compte_id=:c"),
                {"c": cid}).scalar()
            if not email:
                continue
            tok = _notif_token(db, cid)
            ld = f"{base_url}/events/desabonner?c={cid}&t={tok}"
            lp = f"{base_url}/events/preferences?c={cid}&t={tok}"
            sujet, txt, html = emails.mise_en_vente_email(court, b["commune"], type_label, prix,
                                                          lien=url, lien_desabo=ld, lien_prefs=lp)
            raw = {"sujet": sujet, "texte": txt, "html": html, "nom": "Mise en vente"}
            mailfile.envoyer_mail(db.get_bind(), key="mise_en_vente", to=email, params={"__raw": raw},
                                  compte_id=cid, demandeur="job:radar-cloche",
                                  dedup=f"mise_en_vente:{cid}:{b['bien_id']}",
                                  fenetre_doublon_s=90 * 24 * 3600, dry_run=dry)
    return n


def mise_en_vente_immediate(db: Session, bien_id: int) -> int:
    """RADAR-2 (Lot 2) — un rattachement MANUEL (« C'est cette parcelle », admin) vers une parcelle SUIVIE
    déclenche TOUT DE SUITE le mail « parcelle suivie mise en vente », par le MÊME chemin que le digest
    (`_mises_en_vente`) et sa dédup — jamais un doublon avec la cloche du soir. Renvoie le nombre de
    parcelles-suivies notifiées (0 si le bien n'a pas d'idu, n'est pas vivant, ou n'est suivi par personne)."""
    row = db.execute(text(
        "SELECT b.bien_id, b.commune, b.type_bien, b.idu, "
        "       f.prix, f.surface_hab, f.surface_terrain, f.particulier_pro, "
        "       a.portail, a.url_sortante "
        "FROM pige_biens b JOIN pige_faits f ON f.bien_id = b.bien_id "
        "LEFT JOIN LATERAL (SELECT portail, url_sortante FROM pige_annonces WHERE bien_id = b.bien_id "
        "                   ORDER BY date_saisie DESC LIMIT 1) a ON true "
        "WHERE b.bien_id = :b AND f.valide_at IS NOT NULL AND b.a_qualifier = false "
        "  AND b.statut IN ('active','en_vente_longue')"), {"b": bien_id}).mappings().first()
    if not row or not row["idu"]:
        return 0
    return _mises_en_vente(db, [_avec_faits(row)], _idus_suivis(db), None)


def evaluer_radar_cloche(db: Session) -> dict:
    """VEILLE-2 (Lot 3) / VEILLE-FIX-2 (Lots A+B) — pose à la CLOCHE (compte-scopé) les événements Radar
    des annonces vues DEPUIS LE DERNIER PASSAGE qui matchent une veille du client :
      · `radar`             — nouvelle annonce → clic vers l'annonce ;
      · `radar_baisse`      — baisse de prix (ancien → nouveau) sur une annonce qui matche ;
      · `radar_retrait`     — annonce retirée (confirmée) qui matchait ;
      · `parcelle_en_vente` — mise en vente d'une parcelle SUIVIE (prioritaire + MAIL IMMÉDIAT).
    Producteur des événements Radar que le digest du matin reprend (nouvelle/baisse/retrait) ; la mise en
    vente part EN PLUS tout de suite (grille : `mail: immediat`). Zéro mail de digest ici. Idempotent
    (dédup). Un ESSAI EXPIRÉ ne reçoit rien (`_clients_actifs` filtre déjà).

    VEILLE-FIX-2 (Lot A) — fenêtre « depuis le dernier passage » (watermark, repli début d'hier)."""
    from datetime import datetime, time, timedelta, timezone

    from ..api.events import creer_notification
    _ensure_watermark(db)
    debut = datetime.now(timezone.utc)
    jour = today_reunion()
    # repli au 1er passage = DÉBUT D'HIER (00:00 heure Réunion) — robuste : capte tout le dépôt du soir,
    # jamais un « now − 24 h » glissant qui raterait une annonce déposée à 22 h la veille.
    repli = datetime.combine(jour - timedelta(days=1), time(0, 0), tzinfo=timezone(timedelta(hours=4)))
    depuis = _watermark_get(db, _WATERMARK_RADAR) or repli
    biens = _biens_du_jour(db, depuis)
    baisses = _biens_baisses_depuis(db, depuis)
    retraits = _biens_retires_depuis(db, depuis)
    suivis = _idus_suivis(db)
    out = {"radar": 0, "radar_baisse": 0, "radar_retrait": 0, "parcelle_en_vente": 0}
    for c in _clients_actifs(db):
        for v in veille_mod.lister(db, c["compte_id"]):
            cr = v.get("criteria") or {}
            for b in (x for x in biens if veille_mod.matche(cr, x)):
                type_label = (b.get("type_bien") or "bien").capitalize()
                prix = _fmt_prix(b["faits"].get("prix")) or "—"
                out["radar"] += 1 if creer_notification(
                    db, kind="radar", compte_id=c["compte_id"], source="Radar", idu=None,
                    titre=f"Nouvelle annonce pour votre veille — {type_label} à {b['commune']}",
                    detail=f"{prix} · {_libelle_veille(v)}",
                    lien=b.get("url_sortante") or _lien_radar(""),
                    dedup=f"radar:{c['compte_id']}:{b['bien_id']}:{jour.isoformat()}") else 0
            for b in (x for x in baisses if veille_mod.matche(cr, x)):
                type_label = (b.get("type_bien") or "bien").capitalize()
                anc, nouv = _fmt_prix(b.get("ancien_prix")), _fmt_prix(b.get("nouveau_prix"))
                out["radar_baisse"] += 1 if creer_notification(
                    db, kind="radar_baisse", compte_id=c["compte_id"], source="Radar", idu=None,
                    titre=f"Baisse de prix — {type_label} à {b['commune']}",
                    detail=f"{anc} → {nouv} · {_libelle_veille(v)}",
                    lien=b.get("url_sortante") or _lien_radar(""),
                    dedup=f"radar_baisse:{c['compte_id']}:{b['bien_id']}:{b.get('nouveau_prix')}",
                    permanent=True) else 0
            for b in (x for x in retraits if veille_mod.matche(cr, x)):
                type_label = (b.get("type_bien") or "bien").capitalize()
                quand = _fmt_date_fr(b["retiree_le"].date()) if b.get("retiree_le") else "récemment"
                out["radar_retrait"] += 1 if creer_notification(
                    db, kind="radar_retrait", compte_id=c["compte_id"], source="Radar", idu=None,
                    titre=f"Annonce retirée — {type_label} à {b['commune']}",
                    detail=f"retirée le {quand} · {_libelle_veille(v)}",
                    lien=b.get("url_sortante") or _lien_radar(""),
                    dedup=f"radar_retrait:{c['compte_id']}:{b['bien_id']}", permanent=True) else 0
    out["parcelle_en_vente"] = _mises_en_vente(db, biens, suivis, jour)
    _watermark_set(db, _WATERMARK_RADAR, debut)             # borne haute = début du passage (aucun trou)
    db.commit()
    return out


def envoyer(db: Session, *, base_url: str = "", dry_run: bool = False,
            dry_dir: str | None = None) -> dict:
    """Les DEUX envois de fin de journée (template 12 digest + 13 alerte). Idempotent, jamais vide.
    Retourne le rapport (envoyes/echecs/simules/deja par type)."""
    jour = today_reunion()
    lien_radar = _lien_radar(base_url)
    ddir = Path(dry_dir) if dry_dir else None
    biens = _biens_du_jour(db)
    clients = _clients_actifs(db)
    rapport: list = []

    # VEILLE-FIX-1 (lot 2) — RADAR SELON LES CRITÈRES. Le digest « à tous les comptes actifs » (ancien
    # bloc a, template 12) est RETIRÉ : un client ne reçoit un mail QUE si une de ses veilles Radar
    # matche au moins une annonce du jour, et avec SEULEMENT ces annonces-là. Aucune veille qui matche
    # → aucun mail. Ne reste que l'ALERTE de veille (template 13), déjà filtrée par veille.

    # ALERTE de veille (template 13) — UN MAIL PAR VEILLE déclenchée (jamais groupé, jamais vide).
    for c in clients:
        if not c.get("email"):
            continue
        for v in veille_mod.lister(db, c["compte_id"]):
            cr = v.get("criteria") or {}
            matches = [b for b in biens if veille_mod.matche(cr, b)]
            if not matches:
                continue
            cartes = cartes_html(matches, base_url)
            params = {"PRENOM": c.get("prenom") or "", "VEILLE": _libelle_veille(v),
                      "NB_BIENS": len(matches), "CRITERES": _criteres_texte(cr), "CARTES": cartes,
                      "LIEN_RADAR": lien_radar, "LIEN_VEILLE": f"{lien_radar}&veille={v['id']}"}
            _envoyer(db, compte_id=c["compte_id"], email=c["email"], template_key="radar_alerte",
                     dedup=f"pige:alerte:{c['compte_id']}:{v['id']}:{jour.isoformat()}", params=params,
                     n_biens=len(matches), cartes_html_str=cartes, type_envoi="alerte",
                     dry_run=dry_run, dry_dir=ddir, rapport=rapport)

    if not dry_run:
        db.commit()
    def _c(st): return sum(1 for r in rapport if r["statut"] == st)
    return {"n_biens_du_jour": len(biens), "envoyes": _c("envoye"), "echecs": _c("echec"),
            "simules": _c("simule"), "deja": _c("deja"), "dry_run": dry_run, "details": rapport}
