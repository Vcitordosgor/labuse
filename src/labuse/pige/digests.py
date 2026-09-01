"""RADAR-DIGESTS — les DEUX digests de fin de journée (heure Réunion), sur DEUX templates Brevo distincts.

(12) DIGEST quotidien  → tous les clients actifs, les nouveautés du jour (clé Brevo `radar_digest`).
(13) ALERTE de veille  → un mail PAR VEILLE déclenchée, aux clients dont une veille matche (`radar_alerte`).
Un client concerné reçoit LES DEUX (décision Vic) — envois distincts, jamais groupés, jamais dédupliqués.

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
from .tables import EV_DIGEST, journaliser

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

def _biens_du_jour(db: Session) -> list[dict]:
    """Biens VALIDÉS saisis AUJOURD'HUI (heure Réunion), statuts vivants, enrichis pour la carte :
    portail + lien + date de relevé (dernière annonce), baisse de prix (dernier constat à la baisse)."""
    rows = db.execute(text(
        """SELECT b.bien_id, b.commune, b.type_bien, b.est_copro, b.idu,
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
             AND b.date_premiere_saisie AT TIME ZONE 'Indian/Reunion'
                 >= (now() AT TIME ZONE 'Indian/Reunion')::date
           ORDER BY b.bien_id DESC""")).mappings().all()
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
    connus = {"commune", "type_bien", "prix_min", "prix_max", "surface_terrain_min",
              "surface_hab_min", "particulier_only", "nom"}
    bits: list[str] = []
    if criteria.get("type_bien"):
        bits.append(str(criteria["type_bien"]).capitalize())
    if criteria.get("commune"):
        bits.append(str(criteria["commune"]))
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

def _deja_envoye(db: Session, dedup: str) -> bool:
    """Idempotence : cet envoi (dedup du jour) a-t-il déjà été journalisé ? Évite le double-envoi
    quand le cron est rejoué le même jour."""
    return db.execute(text("SELECT 1 FROM event_log WHERE dedup = :d LIMIT 1"), {"d": dedup}).first() is not None


def _envoyer(db: Session, *, compte_id, email: str, template_key: str, dedup: str,
             params: dict, n_biens: int, cartes_html_str: str, type_envoi: str,
             dry_run: bool, dry_dir: Path | None, rapport: list) -> str:
    """UN envoi (digest ou alerte). Idempotent (dedup), jamais vide (garanti par l'appelant), échec
    BRUYANT. Retourne 'simule' | 'envoye' | 'deja' | 'echec'."""
    if not dry_run and _deja_envoye(db, dedup):
        rapport.append({"compte_id": compte_id, "type_envoi": type_envoi, "n": n_biens, "statut": "deja"})
        return "deja"
    if dry_run:
        if dry_dir is not None:
            dry_dir.mkdir(parents=True, exist_ok=True)
            (dry_dir / f"{type_envoi}_compte{compte_id}.html").write_text(cartes_html_str, encoding="utf-8")
        rapport.append({"compte_id": compte_id, "type_envoi": type_envoi, "n": n_biens, "statut": "simule"})
        return "simule"
    res = mail.envoyer_template(email, template_key, params)
    if res.get("envoye"):
        journaliser(db, EV_DIGEST, f"Radar — {type_envoi} envoyé ({n_biens})",
                    detail=f"{type_envoi} · {n_biens} bien(s)", compte_id=compte_id, dedup=dedup)
        rapport.append({"compte_id": compte_id, "type_envoi": type_envoi, "n": n_biens, "statut": "envoye"})
        return "envoye"
    # ÉCHEC BRUYANT (RV-013) — jamais silencieux : log.error + event système visible au dashboard.
    raison = res.get("raison", "inconnue")
    log.error("RADAR %s NON ENVOYÉ à compte=%s : %s", type_envoi, compte_id, raison)
    try:
        creer_notification(db, kind="systeme", compte_id=None, source="Radar",
                           titre=f"Échec envoi Radar ({type_envoi})",
                           detail=f"Compte {compte_id} : {raison}. Templates Brevo 12 et 13 montés ?",
                           dedup=f"pige:digest-echec:{type_envoi}:{today_reunion().isoformat()}")
    except Exception:  # noqa: BLE001 — la trace ne doit pas masquer l'échec d'origine
        pass
    rapport.append({"compte_id": compte_id, "type_envoi": type_envoi, "n": n_biens,
                    "statut": "echec", "raison": raison})
    return "echec"


def _clients_actifs(db: Session) -> list[dict]:
    """Comptes ACTIFS + e-mail/prénom du titulaire. (RD-503 : `comptes.prenoms` n'existe pas → `c.nom`.)"""
    return [dict(r) for r in db.execute(text(
        "SELECT c.id AS compte_id, c.nom AS prenom, "
        " min(u.email) FILTER (WHERE u.role='titulaire') AS email "
        "FROM comptes c LEFT JOIN utilisateurs u ON u.compte_id = c.id "
        "WHERE c.statut = 'actif' GROUP BY c.id, c.nom ORDER BY c.id")).mappings()]


def envoyer(db: Session, *, base_url: str = "", dry_run: bool = False,
            dry_dir: str | None = None) -> dict:
    """Les DEUX envois de fin de journée (template 12 digest + 13 alerte). Idempotent, jamais vide.
    Retourne le rapport (envoyes/echecs/simules/deja par type)."""
    jour = today_reunion()
    date_fr = _fmt_date_fr(jour)
    lien_radar = _lien_radar(base_url)
    ddir = Path(dry_dir) if dry_dir else None
    biens = _biens_du_jour(db)
    clients = _clients_actifs(db)
    rapport: list = []

    # (a) DIGEST quotidien (template 12) — tous les clients actifs, SI des nouveautés (jamais vide).
    if biens:
        cartes = cartes_html(biens, base_url)
        for c in clients:
            if not c.get("email"):
                continue
            params = {"PRENOM": c.get("prenom") or "", "DATE": date_fr, "NB_BIENS": len(biens),
                      "LIEN_RADAR": lien_radar, "CARTES": cartes}
            _envoyer(db, compte_id=c["compte_id"], email=c["email"], template_key="radar_digest",
                     dedup=f"pige:digest:{c['compte_id']}:{jour.isoformat()}", params=params,
                     n_biens=len(biens), cartes_html_str=cartes, type_envoi="digest",
                     dry_run=dry_run, dry_dir=ddir, rapport=rapport)

    # (b) ALERTE de veille (template 13) — UN MAIL PAR VEILLE déclenchée (jamais groupé, jamais vide).
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
