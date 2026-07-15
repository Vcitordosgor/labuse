"""M11 · SURFACE B1 — validation SÉMANTIQUE des filtres de /ia/search (pas juste le schéma).

Le schéma (FILTER_SCHEMA) garantit qu'un filtre a une clé/valeur valide, PAS qu'il correspond au SENS
de la requête. Deux bugs de crédibilité constatés (audit AUDIT-SURFACE-B) :
  1. MISTRADUCTION : « passoire thermique G » → flags:[risques] (contresens, schéma-valide, faux servi).
  2. DROP SILENCIEUX : « propriétaire personne morale » → avalé sans le dire.

Boussole (Vic) : signaler > refuser > appliquer un filtre douteux. Jamais un filtre dont le sens n'est
pas sûr. Ce module, PUR et déterministe (aucun appel IA), applique deux garde-fous après le schéma :
  A. FILTRES GATÉS PAR MOT-CLÉ : un filtre catégoriel (flags, vueMer, evenement, veille) n'est gardé que
     si un mot de la requête le justifie → un filtre non demandé/mistraduit est RETIRÉ (jamais appliqué).
  B. FAMILLES NON SUPPORTÉES : les critères présents dans la requête que les 14 champs ne savent PAS
     traiter (DPE, propriétaire, zonage, viabilisation…) sont LISTÉS (`criteres_non_appliques`) → jamais avalés.
"""
from __future__ import annotations

import re

# ── A. Familles de critères NON couvertes par /ia/search → signalées au client ──
# NB (M11 B2) : « propriétaire personne morale » et « zonage PLU » NE SONT PLUS ici — ils sont
# désormais SUPPORTÉS (filtres personneMorale + zonage) → ils sortent de criteres_non_appliques.
_UNSUPPORTED: list[tuple[re.Pattern, str]] = [
    (re.compile(r"passoire|\bdpe\b|classe[s]?\s*[ée]nerg|[ée]nerg[ée]tique|thermique|[ée]tiquette\s*[ée]nerg", re.I),
     "DPE / classe énergétique"),
    (re.compile(r"dirigeant|g[ée]rant|[âa]g[ée]|succession|h[ée]riti|retrait[ée]", re.I),
     "profil du propriétaire (âge / succession)"),
    (re.compile(r"liquidation|redressement|\bbodacc\b|proc[ée]dure\s+collective|faillite|cessation", re.I),
     "état juridique du propriétaire (BODACC)"),
    (re.compile(r"assainissement|tout\s*[àa]\s*l['’ ]?[ée]gout|raccord|viabilis|\banc\b|eaux\s+us[ée]es", re.I),
     "viabilisation / assainissement"),
    (re.compile(r"piscine", re.I), "piscine"),
    (re.compile(r"jardin", re.I), "jardin (surface non bâtie)"),
    (re.compile(r"pente|d[ée]nivel|terrain\s+plat|en\s+pente", re.I), "pente du terrain"),
    (re.compile(r"amiante", re.I), "amiante / bâti ancien"),
    (re.compile(r"canop[ée]e|v[ée]g[ée]tation|arbres?|ombrage", re.I), "végétation / canopée"),
    (re.compile(r"solaire|photovolta|panneau", re.I), "potentiel solaire"),
]

# ── B. Mots-clés justifiant chaque filtre CATÉGORIEL (anti-mistraduction : sans mot → filtre retiré) ──
_FLAG_KW: dict[str, re.Pattern] = {
    "risques": re.compile(r"risque|inondation|inondable|\bppr\b|al[ée]a|mouvement\s+de\s+terrain|submersion|s[ée]isme|glissement|liquefaction|volcan", re.I),
    "sol_pollue": re.compile(r"pollu|\bsis\b|basol|basias|contamin", re.I),
    "abf": re.compile(r"\babf\b|monument|b[âa]timent[s]?\s+de\s+france|site\s+class|abords|patrimoine|class[ée]", re.I),
    "icpe": re.compile(r"\bicpe\b|installation[s]?\s+class|industriel", re.I),
    "prescription_plu": re.compile(r"prescription|emplacement[s]?\s+r[ée]serv|\ber\b|\bebc\b|espace[s]?\s+bois", re.I),
}
# booléens catégoriels (même logique de garde par mot-clé)
_BOOL_KW: dict[str, re.Pattern] = {
    "vueMer": re.compile(r"vue\s*mer|mer|littoral|oc[ée]an|c[ôo]ti[èe]", re.I),
    "evenement": re.compile(r"[ée]v[ée]nement|bodacc|cession|liquidation|redressement|permis|d[ée]p[ôo]t", re.I),
    "veille": re.compile(r"veille|succession|dirigeant|dormante", re.I),
    "horsCopro": re.compile(r"copro|hors\s*copro|copropri[ée]t", re.I),
    # M11 B2 : propriétaire personne morale (DGFiP public) — justifié par SCI/société/SIREN/…
    "personneMorale": re.compile(r"personne\s*morale|soci[ée]t[ée]|\bsci\b|\bsarl\b|\bsas[u]?\b|siren|entreprise|d[ée]tenu", re.I),
}
# M11 B2 : zonage PLU par famille — chaque famille produite doit être justifiée (anti-mistraduction)
_ZONE_KW: dict[str, re.Pattern] = {
    "U": re.compile(r"zone\s*u\b|constructible|urbaine?s?\b|urbanis[ée]", re.I),
    "AU": re.compile(r"zone\s*au\b|[àa]\s*urbaniser|urbaniser", re.I),
    "A": re.compile(r"zone\s*a\b|agricole", re.I),
    "N": re.compile(r"zone\s*n\b|naturel", re.I),
}


def check_semantics(query: str, filters: dict) -> tuple[dict, list[str]]:
    """Valide le SENS des filtres vs la requête. Retourne (filtres_nettoyés, criteres_non_appliques).

    - Retire tout filtre catégoriel (flags/flagsExclus/zonage/vueMer/evenement/veille/horsCopro/
      personneMorale) NON justifié par un mot de la requête → un filtre mistraduit n'est JAMAIS appliqué.
    - Liste les familles de critères présentes dans la requête mais non couvertes par les 14 champs.
    """
    q = query or ""
    out = dict(filters or {})

    # A. filtres à énumération — chaque valeur doit être justifiée par un mot de la requête
    for key, kw in (("flags", _FLAG_KW), ("flagsExclus", _FLAG_KW), ("zonage", _ZONE_KW)):
        vals = out.get(key)
        if isinstance(vals, list):
            kept = [v for v in vals if v not in kw or kw[v].search(q)]
            if kept:
                out[key] = kept
            else:
                out.pop(key, None)

    # B. booléens catégoriels — retirés si non justifiés (jamais un filtre « vue mer » non demandé)
    for key, pat in _BOOL_KW.items():
        if out.get(key) is True and not pat.search(q):
            out.pop(key, None)

    # C. familles non supportées présentes dans la requête → signalées (dédup, ordre stable)
    non_appliques: list[str] = []
    seen: set[str] = set()
    for pat, label in _UNSUPPORTED:
        if pat.search(q) and label not in seen:
            non_appliques.append(label)
            seen.add(label)

    return out, non_appliques
