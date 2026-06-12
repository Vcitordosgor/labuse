"""Résumé « business » de la fiche (Phase 2) — lecture promoteur en cinq lignes.

Dérive UNIQUEMENT de signaux DÉJÀ calculés (verdict, cascade, bilan, prospection) :
aucune nouvelle donnée, aucun nouveau scoring, aucun seuil touché. Vocabulaire prudent
IMPOSÉ — jamais « constructible », « rentable », « garanti », « propriétaire trouvé ».
Cœur pur, testable, sans DB. Servi dans le payload fiche ET repris dans les exports.
"""
from __future__ import annotations

STATUT_LABEL = {
    "opportunite": "Opportunité vérifiée",
    "a_creuser": "À creuser",
    "faux_positif_probable": "Faux positif probable",
    "exclue": "Exclue",
}

# Raisons POSITIVES sûres par couche (jamais « constructible »).
_POSITIVE_LABEL = {
    "zonage_plu_gpu": "Zonage favorable (zone urbaine / à urbaniser)",
    "surface": "Surface mobilisable",
    "acces": "Accès direct à la voirie",
}

# Points de VIGILANCE sûrs par couche contraignante (SOFT_FLAG/HARD_EXCLUDE).
_VIGILANCE_LABEL = {
    "risques": "Périmètre PPR — prescriptions à vérifier",
    "sar": "Contrainte SAR possible à vérifier",
    "foret_publique": "Forêt publique — emprise à vérifier",
    "trait_de_cote": "Recul du trait de côte à vérifier",
    "safer": "Zonage SAFER — préemption possible",
    "parc_national": "Aire d'adhésion du Parc national",
    "eau": "Hydrographie en bordure",
    "ens": "Espace naturel sensible à proximité",
    "abf": "Périmètre ABF (avis architecte)",
}


def _bilan(faisabilite: dict | None) -> dict:
    return ((faisabilite or {}).get("bilan")) or {}


def _positifs(cascade: list[dict], bilan: dict) -> list[str]:
    out: list[str] = []
    for c in cascade:
        if c.get("result") == "POSITIVE":
            lbl = _POSITIVE_LABEL.get(c.get("layer_name"))
            if lbl and lbl not in out:
                out.append(lbl)
    # SAR : vocation compatible (PASS explicite) — signal favorable prudent.
    if any(c.get("layer_name") == "sar" and c.get("result") == "PASS"
           and "compatible" in (c.get("detail") or "") for c in cascade):
        out.append("Vocation SAR compatible (à croiser)")
    # Prix de SORTIE de marché fiable (DVF) — on qualifie le prix, jamais le bilan complet.
    if bilan.get("fiable") and bilan.get("fiabilite") == "fiable":
        out.append("Prix de marché fiable (DVF)")
    return out[:3]


def _vigilance(verdict: dict, cascade: list[dict], bilan: dict, prospection: dict,
               bati: dict | None = None) -> list[str]:
    out: list[str] = []
    dg = verdict.get("downgrade_reason")
    if dg:
        out.append(dg)  # motif de déclassement, déjà prudent (« parking sur 82 % », « pente 103 % »)
    # Bâti léger (5-15 %, non déclassant — correctif R1) : signalé en vigilance.
    if bati and bati.get("code") == "peu_bati":
        out.append(f"Présence de bâti à vérifier ({bati.get('ratio_pct')} % de la surface)")
    # Contraintes franches : HARD_EXCLUDE d'abord, puis SOFT_FLAG fort.
    for want in ("HARD_EXCLUDE", "SOFT_FLAG"):
        for c in cascade:
            if c.get("result") != want:
                continue
            if want == "SOFT_FLAG" and c.get("severity") not in (None, "fort"):
                continue
            lbl = _VIGILANCE_LABEL.get(c.get("layer_name"))
            if lbl and lbl not in out:
                out.append(lbl)
    # Prix de sortie fragile (échantillon DVF limité).
    if bilan.get("fiabilite") == "fragile":
        out.append("Prix de marché fragile (échantillon limité)")
    # Propriétaire : toujours à identifier tant qu'aucun contact n'a été saisi manuellement.
    status = verdict.get("status")
    if status in ("opportunite", "a_creuser") and not prospection.get("has_manual_contact"):
        out.append("Propriétaire à identifier")
    return out[:3]


def _clean(detail: str | None) -> str:
    """Retire les préfixes techniques (« Exclue : », « Déclassée … ») pour une phrase lisible."""
    s = (detail or "").strip()
    for pref in ("Exclue : ", "Exclue: "):
        if s.startswith(pref):
            s = s[len(pref):]
    return s.rstrip(". ")


def _synthese(status: str, positifs: list[str], vigilance: list[str],
              verdict: dict, cascade: list[dict]) -> str:
    dg = verdict.get("downgrade_reason")
    if status == "faux_positif_probable":
        return f"Parcelle déclassée : {_clean(dg) or (vigilance[0] if vigilance else 'signal terrain contradictoire')}."
    if status == "exclue":
        hard = next((c["detail"] for c in cascade if c.get("result") == "HARD_EXCLUDE"), None)
        return f"Parcelle écartée : {_clean(hard) or (vigilance[0] if vigilance else 'contrainte rédhibitoire')}."
    if status == "a_creuser":
        base = "Parcelle à creuser : potentiel présent"
        # Construction en liste après deux-points : reste lisible quels que soient les
        # libellés injectés (« surface réduite 106 m² », « Périmètre PPR… »).
        return f"{base} ; à lever d'abord : {' ; '.join(vigilance)}." if vigilance else f"{base}, à confirmer."
    if status == "opportunite":
        p = ", ".join(positifs).lower() if positifs else "ses signaux favorables"
        phrase = f"Ressort comme opportunité vérifiée par {p}"
        if vigilance:
            phrase += f". À vérifier avant de démarcher : {' ; '.join(vigilance)}"
        return phrase + "."
    return "Parcelle non évaluée."


def _prochaine_action(status: str, vigilance: list[str], prospection: dict) -> str:
    # Si une action manuelle a été saisie au pipeline, on la met en avant.
    manual = (prospection.get("data") or {}).get("prochaine_action")
    if manual:
        return manual
    if status == "opportunite":
        return "Vérifier le PLU/CU, croiser PPR/SAR, puis identifier le propriétaire avant de démarcher."
    if status == "a_creuser":
        lever = vigilance[0] if vigilance else "la contrainte identifiée"
        return f"Lever d'abord : {lever} (vérification PLU/PPR/SAR ou terrain)."
    if status == "faux_positif_probable":
        return "Écarter, ou vérifier sur le terrain si le signal semble erroné."
    if status == "exclue":
        return "Écarter — contrainte rédhibitoire identifiée."
    return "—"


def build_resume(verdict: dict, cascade: list[dict],
                 faisabilite: dict | None, prospection: dict | None,
                 bati: dict | None = None) -> dict:
    """Bloc « Résumé opportunité » : statut, synthèse, ≤3 positifs, ≤3 vigilances, action."""
    cascade = cascade or []
    prospection = prospection or {}
    bilan = _bilan(faisabilite)
    status = verdict.get("status") or "inconnu"
    positifs = _positifs(cascade, bilan)
    vigilance = _vigilance(verdict, cascade, bilan, prospection, bati)
    return {
        "statut": status,
        "statut_label": STATUT_LABEL.get(status, "Non évaluée"),
        "synthese": _synthese(status, positifs, vigilance, verdict, cascade),
        "positifs": positifs,
        "vigilance": vigilance,
        "prochaine_action": _prochaine_action(status, vigilance, prospection),
    }
