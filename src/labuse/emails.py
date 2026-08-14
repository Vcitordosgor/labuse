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
    # Sujet : reflète le contenu réel (perso prioritaire, sinon marché).
    if n:
        sujet = f"LABUSE — {n} nouveauté{'s' if n > 1 else ''} sur vos parcelles ({periode})"
    else:
        sujet = f"LABUSE — {m_total} mouvement{'s' if m_total > 1 else ''} de marché ({periode})"
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


# ── M85 · gabarit HTML du digest (DA LABUSE : vert print #1E9E58 sur blanc, sobre) ──
def digest_html_email(evenements: list[dict], marche: dict | None, top_chaudes: list[dict],
                      lien_desabo: str, lien_prefs: str, *, base_url: str = "",
                      periode: str = "aujourd'hui") -> str:
    """Alternative HTML du digest. DA LABUSE : vert #1E9E58 sur blanc, wordmark (aucune image externe
    → zéro tracking, rendu fiable partout ; le logo SVG est mal supporté en e-mail). Le texte reste
    le repli (multipart/alternative)."""
    V = "#1E9E58"
    ev_rows = "".join(
        f"<tr><td style='padding:10px 16px;border-bottom:1px solid #eef2f0;font:14px sans-serif;color:#1a2b22'>"
        f"<b>{(e.get('titre') or '')}</b>"
        f"<div style='color:#667;font-size:12px;margin-top:2px'>{(e.get('detail') or '')}</div></td></tr>"
        for e in evenements) or ("<tr><td style='padding:14px 16px;font:14px sans-serif;color:#667'>"
                                 "Rien de nouveau sur vos parcelles suivies.</td></tr>")
    mr = marche or {}
    marche_row = ""
    if mr.get("total"):
        cadre = (f", dont {mr['dans_vos_communes']} dans vos communes"
                 if mr.get("dans_vos_communes") is not None else " sur l'île")
        marche_row = (f"<tr><td style='padding:10px 16px;border-bottom:1px solid #eef2f0;"
                      f"font:14px sans-serif;color:#1a2b22'>{mr['total']} mouvement(s) de marché{cadre}."
                      f"<div style='color:#667;font-size:12px'>Le détail est dans la cloche.</div></td></tr>")
    top_rows = "".join(
        f"<tr><td style='padding:6px 16px;font:600 13px monospace;color:#1a2b22'>{(t.get('idu') or '')[8:]}</td>"
        f"<td style='padding:6px;font:13px sans-serif;color:#445'>{t.get('commune') or ''} · "
        f"{round(t.get('surface_m2') or 0)} m²</td></tr>"
        for t in (top_chaudes or [])[:5])
    top_bloc = (f"<p style='font:600 13px sans-serif;color:{V};margin:18px 16px 4px'>Les plus chaudes</p>"
                f"<table style='width:100%;border-collapse:collapse'>{top_rows}</table>" if top_rows else "")
    return (f"<!doctype html><html><body style=\"margin:0;background:#f4f7f5;padding:24px 0\">"
            f"<table width=\"600\" align=\"center\" style=\"background:#fff;border-radius:14px;"
            f"overflow:hidden;margin:auto;box-shadow:0 1px 4px rgba(0,0,0,.06)\">"
            f"<tr><td style=\"padding:20px 24px;border-bottom:3px solid {V}\">"
            f"<span style=\"font:800 18px sans-serif;color:{V};letter-spacing:.5px\">LABUSE</span>"
            f"<span style=\"float:right;color:#889;font:12px sans-serif;padding-top:4px\">"
            f"Votre point — {periode}</span></td></tr>"
            f"<tr><td style=\"padding:14px 0 4px\"><table style=\"width:100%;border-collapse:collapse\">"
            f"{ev_rows}{marche_row}</table>{top_bloc}</td></tr>"
            f"<tr><td style=\"padding:16px 24px;border-top:1px solid #eef2f0;font:12px sans-serif;color:#889\">"
            f"Vous recevez ce résumé parce que vous suivez des parcelles ou avez des veilles sur LABUSE.<br>"
            f"<a href=\"{lien_prefs}\" style=\"color:{V}\">Régler mes préférences</a> · "
            f"<a href=\"{lien_desabo}\" style=\"color:#889\">Me désinscrire</a></td></tr>"
            f"</table></body></html>")
