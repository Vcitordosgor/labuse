"""Textes des e-mails LABUSE (M21) — CENTRALISÉS ici pour que Vic les réécrive sans toucher au code.

C'est la voix de LABUSE vers ses clients. Chaque fonction retourne `(sujet, corps_texte)`.
Le corps est en texte brut (sobre, français).
"""
from __future__ import annotations

_SIGNATURE = "\n\n— LABUSE\ncontact@labuse.immo"


# ── B1 · réinitialisation de mot de passe ────────────────────────────────────
def reset_password(lien: str) -> tuple[str, str]:
    sujet = "LABUSE — réinitialisation de votre mot de passe"
    corps = (
        "Bonjour,\n\n"
        "Une réinitialisation du mot de passe de votre compte LABUSE a été demandée. "
        "Pour choisir un nouveau mot de passe, ouvrez le lien ci-dessous :\n\n"
        f"{lien}\n\n"
        "Ce lien est valable 1 heure. Passé ce délai, il faudra en redemander un.\n\n"
        "Si vous n'êtes pas à l'origine de cette demande, ignorez simplement cet e-mail : "
        "votre mot de passe reste inchangé et votre compte n'est pas modifié."
        + _SIGNATURE
    )
    return sujet, corps


# ── B2 · avis d'échéance loi Chatel : RETIRÉ le 27/08/2026 — Intégral est mensuel SANS
#        engagement, la loi Chatel (contrats à durée déterminée reconductibles) est sans objet. ──


# ── B3 · digest de notifications ─────────────────────────────────────────────
def digest_notifications(evenements: list[dict], lien_desabo: str, *,
                         periode: str = "cette semaine", base_url: str = "",
                         marche: dict | None = None, lien_prefs: str = "",
                         secteurs_ligne: str = "") -> tuple[str, str]:
    """`evenements` : liste PERSONNELLE {kind, titre, detail, idu} (parcelles suivies + veilles).
    `marche` (M-T V2) : RÉSUMÉ BORNÉ du marché {total, dans_vos_communes} — jamais une liste
    exhaustive. `lien_desabo` : lien de désinscription (obligatoire)."""
    n = len(evenements)
    marche = marche or {}
    m_total = marche.get("total") or 0
    m_com = marche.get("dans_vos_communes")
    # Résumé marché BORNÉ (jamais la liste). « dont M dans vos communes » si le compte a des
    # parcelles suivies ; sinon le total seul (dans_vos_communes=None).
    if m_total:
        cadre = (f", dont {m_com} dans vos communes" if m_com is not None else " sur l'île")
        marche_txt = (f"Marché ({periode}) : {m_total} mouvement{'s' if m_total > 1 else ''} "
                      f"(bascules de statut, procédures BODACC, matchs){cadre}. "
                      "Le détail est dans la cloche de l'application.")
    else:
        marche_txt = ""
    # Sujet FACTUEL / transactionnel (pas marketing : ni « nouveautés », ni parenthèse newsletter) —
    # « 3 changements sur vos suivis » se lit comme une notification, pas comme une campagne.
    if n:
        sujet = f"LABUSE — {n} changement{'s' if n > 1 else ''} sur vos suivis"
    else:
        sujet = f"LABUSE — {m_total} mouvement{'s' if m_total > 1 else ''} de marché"
    lignes = []
    for e in evenements:
        idu = e.get("idu") or ""
        lien = f"{base_url}/socle/#parcelle={idu}" if (idu and base_url) else (f"parcelle {idu}" if idu else "")
        detail = (e.get("detail") or "").strip()
        lignes.append(f"• {e.get('titre', '')}" + (f"\n  {detail}" if detail else "") + (f"\n  {lien}" if lien else ""))
    if n:
        bloc = (f"Voici le point sur vos parcelles suivies, vos secteurs et vos critères pour {periode} "
                f"({n} événement{'s' if n > 1 else ''}) :\n\n" + "\n\n".join(lignes))
        if marche_txt:
            bloc += "\n\n— — —\n" + marche_txt
    else:
        # Aucun événement personnel : le RÉSUMÉ MARCHÉ suffit à déclencher le digest (fin du
        # « digest vide à vie »). L'appelant a déjà vérifié qu'il y a du contenu.
        bloc = marche_txt
    prefs_ligne = (f"Régler vos préférences (par type, cloche ou e-mail) :\n{lien_prefs}\n"
                   if lien_prefs else "")
    corps = (
        "Bonjour,\n\n"
        + bloc
        + (("\n\n" + secteurs_ligne) if secteurs_ligne else "")   # M85 P3 — « depuis hier sur vos secteurs »
        + "\n\n— — —\n"
        "Vous recevez cet e-mail parce que vous suivez des parcelles, surveillez des secteurs ou des critères, "
        "ou êtes abonné au résumé de marché LABUSE.\n"
        + prefs_ligne
        + "Pour ne plus rien recevoir par e-mail :\n"
        f"{lien_desabo}"
        + _SIGNATURE
    )
    return sujet, corps


# ── M85-B · annonce produit (chaîne 3) — sobre, transactionnel, désinscription (désactivable) ──
def annonce_email(titre: str, corps: str, *, lien: str | None = None, lien_desabo: str = "",
                  lien_prefs: str = "") -> tuple[str, str]:
    """Annonce LABUSE (nouveauté, source). Texte sobre ; désinscription obligatoire (type désactivable)."""
    sujet = f"LABUSE — {titre}"
    lignes = corps.strip()
    if lien:
        lignes += f"\n\n{lien}"
    pieds = []
    if lien_prefs:
        pieds.append(f"Vos préférences : {lien_prefs}")
    if lien_desabo:
        pieds.append(f"Ne plus recevoir les annonces : {lien_desabo}")
    corps_txt = "Bonjour,\n\n" + lignes + ("\n\n— — —\n" + "\n".join(pieds) if pieds else "") + _SIGNATURE
    return sujet, corps_txt


def annonce_html(titre: str, corps: str, *, lien: str | None = None, lien_desabo: str = "",
                 lien_prefs: str = "") -> str:
    V = "#1E9E58"
    lien_html = (f"<p style='margin:14px 0 0'><a href='{lien}' style='color:{V}'>{lien}</a></p>" if lien else "")
    pied = " · ".join(x for x in (
        (f"<a href='{lien_prefs}' style='color:{V}'>Préférences</a>" if lien_prefs else ""),
        (f"<a href='{lien_desabo}' style='color:#888'>Se désinscrire des annonces</a>" if lien_desabo else "")) if x)
    return (f"<!doctype html><html><body style=\"margin:0;background:#fff;color:#1a1a1a;"
            f"font:14px/1.55 -apple-system,Segoe UI,sans-serif\"><div style=\"max-width:600px;padding:20px\">"
            f"<p style=\"margin:0 0 12px;color:{V};font-weight:600\">LABUSE — {titre}</p>"
            f"<div style=\"white-space:pre-line\">{corps.strip()}</div>{lien_html}"
            f"<p style=\"margin:22px 0 0;color:#888;font-size:12px\">{pied}</p></div></body></html>")


# ── M85-B · maintenance (chaîne 3) — gabarit DISTINCT : dates et durée de coupure EN ÉVIDENCE,
#    NON désactivable (conséquences réelles) → aucun lien de désinscription. ──
def maintenance_email(titre: str, corps: str, *, debut: str = "", fin: str = "",
                      duree: str = "") -> tuple[str, str, str]:
    """Retourne (sujet, texte, html). Fenêtre de coupure MISE EN AVANT. Pas de désinscription."""
    sujet = f"LABUSE — maintenance programmée : {titre}"
    fenetre = ""
    if debut or fin or duree:
        parts = []
        if debut:
            parts.append(f"début {debut}")
        if fin:
            parts.append(f"fin {fin}")
        if duree:
            parts.append(f"durée estimée {duree}")
        fenetre = "Fenêtre de coupure : " + ", ".join(parts) + "."
    txt = ("Bonjour,\n\n" + (fenetre + "\n\n" if fenetre else "") + corps.strip()
           + "\n\nCe message concerne le fonctionnement de votre service — il n'est pas désactivable."
           + _SIGNATURE)
    V = "#1E9E58"
    fenetre_html = (f"<p style='margin:0 0 12px;padding:10px 12px;background:#fff6e8;border-left:3px solid #E8B44C;"
                    f"font-weight:600'>{fenetre}</p>" if fenetre else "")
    html = (f"<!doctype html><html><body style=\"margin:0;background:#fff;color:#1a1a1a;"
            f"font:14px/1.55 -apple-system,Segoe UI,sans-serif\"><div style=\"max-width:600px;padding:20px\">"
            f"<p style=\"margin:0 0 12px;color:{V};font-weight:600\">LABUSE — maintenance programmée</p>"
            f"{fenetre_html}<p style=\"margin:0 0 8px;font-weight:600\">{titre}</p>"
            f"<div style=\"white-space:pre-line\">{corps.strip()}</div>"
            f"<p style=\"margin:20px 0 0;color:#888;font-size:12px\">Ce message concerne le fonctionnement "
            f"de votre service — il n'est pas désactivable.</p></div></body></html>")
    return sujet, txt, html


# ── M85 · gabarit HTML du digest — style TRANSACTIONNEL (boîte Principale, pas Promotions) ──
def digest_html_email(evenements: list[dict], marche: dict | None, top_chaudes: list[dict],
                      lien_desabo: str, lien_prefs: str, *, base_url: str = "",
                      periode: str = "aujourd'hui", secteurs_ligne: str = "") -> str:
    """Alternative HTML du digest, volontairement SOBRE pour ressembler à une notification, pas à une
    newsletter (Gmail classe le décoratif en Promotions) : texte dense, UNE colonne, aucune carte, aucun
    gros bouton, pas d'en-tête coloré, une action par ligne. Aucune image externe (zéro tracking). Le
    vert #1E9E58 ne sert QUE d'accent de lien. Le texte brut reste le repli (multipart/alternative)."""
    V = "#1E9E58"

    def _ligne(titre: str, detail: str = "") -> str:
        d = f" <span style='color:#555'>— {detail}</span>" if detail else ""
        return f"<p style='margin:0 0 8px'>{titre}{d}</p>"

    corps = "".join(_ligne(e.get("titre") or "", (e.get("detail") or "").replace("\n", " ").strip())
                    for e in evenements)
    mr = marche or {}
    if mr.get("total"):
        cadre = (f", dont {mr['dans_vos_communes']} dans vos communes"
                 if mr.get("dans_vos_communes") is not None else "")
        corps += _ligne(f"{mr['total']} mouvement(s) de marché{cadre}", "détail dans l'application")
    if not corps:
        corps = "<p style='margin:0'>Rien de nouveau sur vos suivis.</p>"
    if secteurs_ligne:                                   # M85 P3 — « depuis hier sur vos secteurs »
        corps += f"<p style='margin:12px 0 0;color:#333'>{secteurs_ligne}</p>"
    top = ""
    if top_chaudes:
        items = "".join(f"<p style='margin:0 0 4px'>{(t.get('idu') or '')[8:]} — "
                        f"{t.get('commune') or ''}, {round(t.get('surface_m2') or 0)} m²</p>"
                        for t in top_chaudes[:5])
        top = f"<p style='margin:16px 0 6px;font-weight:600'>Les priorités</p>{items}"
    return (f"<!doctype html><html><body style=\"margin:0;background:#ffffff;color:#1a1a1a;"
            f"font:14px/1.55 -apple-system,Segoe UI,Roboto,sans-serif\">"
            f"<div style=\"max-width:600px;padding:20px\">"
            f"<p style=\"margin:0 0 14px;color:#666;font-size:13px\">LABUSE — votre point du jour</p>"
            f"{corps}{top}"
            f"<p style=\"margin:22px 0 0;color:#888;font-size:12px\">"
            f"<a href=\"{lien_prefs}\" style=\"color:{V}\">Préférences</a> — choisir ce que vous recevez.<br>"
            f"<a href=\"{lien_desabo}\" style=\"color:#888\">Se désinscrire des e-mails</a>.</p>"
            f"</div></body></html>")
