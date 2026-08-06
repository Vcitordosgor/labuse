"""Résumé « business » de la fiche (Phase 2) — lecture promoteur en cinq lignes.

M34 (dette #14) : le statut du résumé est la TRADUCTION du tier servi (`verdict_servi`),
transmise dans le dict `verdict` — plus jamais le rail cascade legacy. Les signaux
non-francs de la cascade (accès, pente, surface, bâti partiel) restent des points de
VIGILANCE informatifs : ils nuancent, ils ne contredisent plus le classement.

Dérive UNIQUEMENT de signaux DÉJÀ calculés (verdict traduit, cascade, bilan, prospection) :
aucune nouvelle donnée, aucun nouveau scoring, aucun seuil touché. Vocabulaire prudent
IMPOSÉ — jamais « constructible », « rentable », « garanti », « propriétaire trouvé ».
Cœur pur, testable, sans DB. Servi dans le payload fiche ET repris dans les exports.
"""
from __future__ import annotations

from ..verdict_servi import TIER_LABELS

# Seuil d'AFFICHAGE « micro-opportunité » (présentation pure). Une parcelle servie en tier
# haut (brûlante/chaude) ≤ 500 m² est NUANCÉE : son intérêt promoteur dépend surtout de
# l'assemblage ou d'une micro-opération. Ce drapeau N'AFFECTE NI le verdict NI les scores.
# Le badge nuance, il ne déclasse pas.
MICRO_OPPORTUNITE_MAX_M2 = 500.0

#: tiers hauts — l'équivalent de l'ancienne « opportunité » pour les nuances d'affichage.
_TIERS_HAUTS = ("brulante", "chaude")


def is_micro_opportunite(status: str | None, surface_m2: float | None) -> bool:
    """Vrai si la parcelle servie en tier haut est de petite surface (badge d'affichage).

    Pure : ne dépend que du tier traduit et de la surface cadastrale. Ne modifie rien."""
    return status in _TIERS_HAUTS and surface_m2 is not None and surface_m2 <= MICRO_OPPORTUNITE_MAX_M2


# Raisons POSITIVES sûres par couche (jamais « constructible »).
_POSITIVE_LABEL = {
    "zonage_plu_gpu": "Zonage favorable (zone urbaine / à urbaniser)",
    "surface": "Surface mobilisable",
    "acces": "Accès direct à la voirie",
}

# Points de VIGILANCE sûrs par couche contraignante (SOFT_FLAG/HARD_EXCLUDE).
_VIGILANCE_LABEL = {
    "risques": "Périmètre PPR — prescriptions à vérifier",
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
    if any(c.get("layer_name") == "sar" and c.get("result") == "PASS"
           and "compatible" in (c.get("detail") or "") for c in cascade):
        out.append("Vocation SAR compatible (à croiser)")
    if bilan.get("fiable") and bilan.get("fiabilite") == "fiable":
        out.append("Prix de marché fiable (DVF)")
    return out[:3]


def _vigilance(verdict: dict, cascade: list[dict], bilan: dict, prospection: dict,
               bati: dict | None = None, piscine: dict | None = None) -> list[str]:
    out: list[str] = []
    # M39 (dette #13) — signal PISCINE détectée, informatif : sur un tier haut, une piscine
    # matérialisée (90,7 %) qui occupe ≥ 15 % de la parcelle ET y est contenue (centroïde dans +
    # ratio ≥ 0,7) nuance l'intérêt (usage installé → mutation moins probable). N'affecte NI le tier
    # NI le verdict ici ; c'est la RÈGLE produit (piscine_signal.yaml) exposée en fiche AVANT sa
    # bascule gardée. Prioritaire → insérée en tête.
    from ..faisabilite.piscine_signal import signal_actif, vigilance_texte
    pisc = piscine or {}
    if signal_actif(pisc.get("surface_m2"), verdict.get("status"), pisc.get("parcel_surface_m2"),
                    pisc.get("ratio_dans"), pisc.get("centroide_dans")):
        out.append(vigilance_texte())
    # M34 : les signaux non-francs de la cascade legacy (accès, pente, surface, bâti partiel)
    # sont des VIGILANCES — jamais un déclassement du verdict.
    dg = verdict.get("downgrade_reason")
    if dg:
        out.append(dg)
    # Bâti léger (5-15 %, non déclassant — correctif R1) : signalé en vigilance.
    if bati and bati.get("code") == "peu_bati":
        out.append(f"Présence de bâti à vérifier ({bati.get('ratio_pct')} % de la surface)")
    for want in ("HARD_EXCLUDE", "SOFT_FLAG"):
        for c in cascade:
            if c.get("result") != want:
                continue
            if want == "SOFT_FLAG" and c.get("severity") not in (None, "fort"):
                continue
            if c.get("layer_name") == "prescription_plu":
                txt = _clean(c.get("detail")).split(" — ")[0].strip()
                if txt and txt not in out:
                    out.append(txt)
                continue
            lbl = _VIGILANCE_LABEL.get(c.get("layer_name"))
            if lbl and lbl not in out:
                out.append(lbl)
    if any(c.get("layer_name") == "sar" and (c.get("detail") or "").startswith("⚠ proxy SAR divergent")
           and "zone AU" in (c.get("detail") or "") for c in cascade):
        out.append("Proxy SAR divergent du PLU (zone AU) — ouverture à l'urbanisation moins probable")
    if bilan.get("fiabilite") == "fragile":
        out.append("Prix de marché fragile (échantillon limité)")
    # Propriétaire : toujours à identifier tant qu'aucun contact n'a été saisi (parcelles servies).
    if verdict.get("servable") and not prospection.get("has_manual_contact"):
        out.append("Propriétaire à identifier")
    return out[:3]


def _clean(detail: str | None) -> str:
    """Retire les préfixes techniques (« Exclue : », « Déclassée … ») pour une phrase lisible."""
    s = (detail or "").strip()
    for pref in ("Exclue : ", "Exclue: "):
        if s.startswith(pref):
            s = s[len(pref):]
    return s.rstrip(". ")


def _label(verdict: dict) -> str:
    st = verdict.get("status")
    return verdict.get("label") or TIER_LABELS.get(st, st or "Non évaluée")


def _synthese(status: str, positifs: list[str], vigilance: list[str],
              verdict: dict, cascade: list[dict]) -> str:
    lbl = _label(verdict)
    badge = verdict.get("badge_division_libelle")
    motif = verdict.get("motif")
    if status in _TIERS_HAUTS or status == "reserve_fonciere":
        rang = verdict.get("rang")
        p = ", ".join(positifs).lower() if positifs else "ses signaux au classement servi"
        phrase = f"Classée {lbl} au classement servi"
        if rang and status in _TIERS_HAUTS:
            phrase += f" (rang {rang})"
        phrase += f", portée par {p}"
        if badge:
            phrase += f" — {badge}"
        if vigilance:
            phrase += f". À vérifier avant de démarcher : {' ; '.join(vigilance)}"
        return phrase + "."
    if status == "a_creuser":
        base = "Parcelle à creuser : potentiel présent"
        if motif:  # exception du registre servi (ex. piscine) — motif tracé, prioritaire
            return f"{base} ; au registre servi : {_clean(motif)}."
        return (f"{base} ; à lever d'abord : {' ; '.join(vigilance)}." if vigilance
                else f"{base}, à confirmer.")
    if status and status.startswith("declasse_"):
        m = _clean(motif) if motif else lbl.split("— ", 1)[-1]
        return f"Parcelle déclassée : {m}."
    if status == "ecartee":
        hard = next((c["detail"] for c in cascade if c.get("result") == "HARD_EXCLUDE"), None)
        return f"Parcelle écartée : {_clean(hard) or (vigilance[0] if vigilance else 'contrainte rédhibitoire')}."
    return "Parcelle non évaluée au run servi."


def _prochaine_action(status: str, vigilance: list[str], prospection: dict) -> str:
    manual = (prospection.get("data") or {}).get("prochaine_action")
    if manual:
        return manual
    if status in _TIERS_HAUTS:
        return "Vérifier le PLU/CU, croiser PPR/SAR, puis identifier le propriétaire avant de démarcher."
    if status == "reserve_fonciere":
        return "Suivre la parcelle — potentiel réel à horizon plus lointain ; vérifier PLU et contraintes."
    if status == "a_creuser":
        lever = vigilance[0] if vigilance else "la contrainte identifiée"
        return f"Lever d'abord : {lever} (vérification PLU/PPR/SAR ou terrain)."
    if status and status.startswith("declasse_"):
        return "Écarter, ou vérifier sur le terrain si le motif de déclassement semble erroné."
    if status == "ecartee":
        return "Écarter — contrainte rédhibitoire identifiée."
    return "—"


def build_resume(verdict: dict, cascade: list[dict],
                 faisabilite: dict | None, prospection: dict | None,
                 bati: dict | None = None, piscine: dict | None = None) -> dict:
    """Bloc « Résumé opportunité » : statut traduit, synthèse, ≤3 positifs, ≤3 vigilances, action."""
    cascade = cascade or []
    prospection = prospection or {}
    bilan = _bilan(faisabilite)
    status = verdict.get("status") or "non_evaluee"
    positifs = _positifs(cascade, bilan)
    vigilance = _vigilance(verdict, cascade, bilan, prospection, bati, piscine)
    return {
        "statut": status,
        "statut_label": _label(verdict),
        "synthese": _synthese(status, positifs, vigilance, verdict, cascade),
        "positifs": positifs,
        "vigilance": vigilance,
        "prochaine_action": _prochaine_action(status, vigilance, prospection),
    }
