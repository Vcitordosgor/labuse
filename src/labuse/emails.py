"""Textes des e-mails LABUSE (M21) — CENTRALISÉS ici pour que Vic les réécrive sans toucher au code.

C'est la voix de LABUSE vers ses clients. Chaque fonction retourne `(sujet, corps_texte)`.
Le corps est en texte brut (sobre, français). L'avis Chatel a une VALEUR LÉGALE : formulation
précise, sans ambiguïté.
"""
from __future__ import annotations

from datetime import date, timedelta

_SIGNATURE = "\n\n— LABUSE\ncontact@labuse.immo"


def _fr(d: date) -> str:
    mois = ["", "janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
            "septembre", "octobre", "novembre", "décembre"]
    return f"{d.day} {mois[d.month]} {d.year}"


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


# ── B2 · avis d'échéance loi Chatel (VALEUR LÉGALE) ──────────────────────────
def avis_echeance(echeance_iso: str, lien_espace: str) -> tuple[str, str]:
    ech = date.fromisoformat(echeance_iso)
    limite = ech - timedelta(days=30)  # dénonciation au plus tard 1 mois avant l'échéance
    sujet = f"LABUSE — votre abonnement se reconduit le {_fr(ech)}"
    corps = (
        "Bonjour,\n\n"
        "Conformément à l'article L. 215-1 du code de la consommation (loi Chatel), nous vous "
        "informons que votre abonnement LABUSE arrive à échéance le "
        f"{_fr(ech)}.\n\n"
        "Sauf dénonciation de votre part, il sera reconduit tacitement pour une nouvelle période "
        "de douze (12) mois, aux conditions en vigueur.\n\n"
        "Vous pouvez choisir de NE PAS reconduire cet abonnement. Pour cela, informez-nous de votre "
        "décision au plus tard UN (1) MOIS avant l'échéance, soit avant le "
        f"{_fr(limite)}, par e-mail à contact@labuse.immo ou depuis votre espace :\n\n"
        f"{lien_espace}\n\n"
        "Si vous ne nous avez pas informés de votre faculté de non-reconduction dans ce délai, vous "
        "pourrez mettre gratuitement un terme à la reconduction et, le cas échéant, être remboursé "
        "des sommes versées d'avance après la date de reconduction (art. L. 215-1, al. 3)."
        + _SIGNATURE
    )
    return sujet, corps


# ── B3 · digest de notifications ─────────────────────────────────────────────
def digest_notifications(evenements: list[dict], lien_desabo: str, *,
                         periode: str = "cette semaine", base_url: str = "",
                         marche: dict | None = None, lien_prefs: str = "") -> tuple[str, str]:
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
        bloc = (f"Voici le point sur vos parcelles suivies et vos veilles pour {periode} "
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
        + "\n\n— — —\n"
        "Vous recevez cet e-mail parce que vous suivez des parcelles, avez enregistré des veilles, "
        "ou êtes abonné au résumé de marché LABUSE.\n"
        + prefs_ligne
        + "Pour ne plus rien recevoir par e-mail :\n"
        f"{lien_desabo}"
        + _SIGNATURE
    )
    return sujet, corps


# ── M85 · gabarit HTML du digest — style TRANSACTIONNEL (boîte Principale, pas Promotions) ──
def digest_html_email(evenements: list[dict], marche: dict | None, top_chaudes: list[dict],
                      lien_desabo: str, lien_prefs: str, *, base_url: str = "",
                      periode: str = "aujourd'hui") -> str:
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
    top = ""
    if top_chaudes:
        items = "".join(f"<p style='margin:0 0 4px'>{(t.get('idu') or '')[8:]} — "
                        f"{t.get('commune') or ''}, {round(t.get('surface_m2') or 0)} m²</p>"
                        for t in top_chaudes[:5])
        top = f"<p style='margin:16px 0 6px;font-weight:600'>Les plus chaudes</p>{items}"
    return (f"<!doctype html><html><body style=\"margin:0;background:#ffffff;color:#1a1a1a;"
            f"font:14px/1.55 -apple-system,Segoe UI,Roboto,sans-serif\">"
            f"<div style=\"max-width:600px;padding:20px\">"
            f"<p style=\"margin:0 0 14px;color:#666;font-size:13px\">LABUSE — votre point du jour</p>"
            f"{corps}{top}"
            f"<p style=\"margin:22px 0 0;color:#888;font-size:12px\">"
            f"<a href=\"{lien_prefs}\" style=\"color:{V}\">Préférences</a> — choisir ce que vous recevez.<br>"
            f"<a href=\"{lien_desabo}\" style=\"color:#888\">Se désinscrire des e-mails</a>.</p>"
            f"</div></body></html>")
