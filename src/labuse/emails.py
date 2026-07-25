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
                         periode: str = "cette semaine", base_url: str = "") -> tuple[str, str]:
    """`evenements` : liste de dicts {kind, titre, detail, idu}. `lien_desabo` : lien de désinscription."""
    n = len(evenements)
    sujet = f"LABUSE — {n} nouveauté{'s' if n > 1 else ''} sur vos parcelles ({periode})"
    lignes = []
    for e in evenements:
        idu = e.get("idu") or ""
        lien = f"{base_url}/socle/#parcelle={idu}" if (idu and base_url) else (f"parcelle {idu}" if idu else "")
        detail = (e.get("detail") or "").strip()
        lignes.append(f"• {e.get('titre', '')}" + (f"\n  {detail}" if detail else "") + (f"\n  {lien}" if lien else ""))
    corps = (
        "Bonjour,\n\n"
        f"Voici le point sur vos parcelles suivies et vos veilles pour {periode} "
        f"({n} événement{'s' if n > 1 else ''}) :\n\n"
        + "\n\n".join(lignes)
        + "\n\n— — —\n"
        "Vous recevez cet e-mail parce que vous suivez des parcelles ou avez enregistré des veilles "
        "sur LABUSE. Pour ne plus recevoir ce résumé :\n"
        f"{lien_desabo}"
        + _SIGNATURE
    )
    return sujet, corps
