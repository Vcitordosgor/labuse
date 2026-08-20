"""3.A — Assistant de fiche en langage naturel (API Anthropic) + synthèse règles hors-ligne.

« Expliquer cette parcelle » → une synthèse française des forces/faiblesses, produite **STRICTEMENT**
à partir des données réelles de la fiche.

Deux modes, jamais d'invention :
  - AVEC clé `ANTHROPIC_API_KEY` : synthèse en prose par le modèle, bridée par un prompt système strict
    (liste blanche de faits, provenance imposée, refus si données insuffisantes).
  - SANS clé : `rules_summary()` — une synthèse DÉTERMINISTE en 5 blocs, dérivée UNIQUEMENT des faits
    de la fiche (aucun LLM, aucune invention). Le bloc reste premium et utile en démo.

Anti-hallucination : le seul contenu transmis au modèle est `assistant_facts` (liste blanche). Le
modèle REFORMULE, il n'ajoute aucun chiffre, prix, propriétaire, servitude, règlement ni contrainte.
Clé API : variable d'environnement **ANTHROPIC_API_KEY** (jamais en clair, jamais commitée). Absente
→ synthèse règles + message clair, AUCUN crash. Modèle surchargeable via LABUSE_ASSISTANT_MODEL.
"""
from __future__ import annotations

import os
from typing import Any

# M11 socle 0 : plus de client httpx propre ici — l'appel modèle passe par labuse.ai.core.
from ..ai.core import ENV_KEY  # noqa: F401 — nom de la variable d'env (source unique = core ; rétro-compat)

ENV_MODEL = "LABUSE_ASSISTANT_MODEL"  # surcharge de modèle éventuelle (rétro-compat)

# Prompt système STRICT (chantiers « sécuriser » + « prompt 5 blocs »). Tout est imposé ici : la
# structure, la provenance, le refus de conclure et l'interdiction d'inventer.
SYSTEM = (
    "Tu es l'assistant foncier EXPERT de LA BUSE (préqualification foncière, La Réunion). À partir "
    "UNIQUEMENT du JSON de données fourni, tu rédiges pour un promoteur une synthèse COURTE, "
    "structurée et actionnable.\n\n"
    "STRUCTURE IMPOSÉE — au plus 5 blocs courts, dans cet ordre, chaque titre en gras :\n"
    "1. **Potentiel** — statut du classement servi (et rang s'il est fourni), zone PLU, capacité "
    "constructible ESTIMÉE (surface de plancher, logements) si présente.\n"
    "2. **Contraintes** — signaux bloquants / de vigilance RÉELS du JSON ; s'il n'y en a pas, écris "
    "« aucune contrainte bloquante dans les données disponibles » (ne déduis jamais une absence de "
    "risque d'une donnée manquante).\n"
    "3. **Bâti / libre** — occupation au sol (BD TOPO) : libre, partiellement bâti, déjà bâti ; si la "
    "couche est absente, dis « occupation non vérifiée ».\n"
    "4. **Économie indicative** — bilan promoteur (charge foncière) TOUJOURS qualifié d'INDICATIF / "
    "ESTIMÉ ; précise si le prix de sortie est fiable ou fragile. Si un bloc `mode_b` est présent "
    "(réhabilitation), tu peux le citer UNIQUEMENT comme ESTIMÉ, en rappelant l'hypothèse travaux "
    "€/m² ; s'il est absent, tu n'en parles JAMAIS.\n"
    "5. **Recommandation** — la prochaine action concrète (ex. vérifier PLU/CU, identifier le "
    "propriétaire, étudier l'assemblage, écarter).\n\n"
    "RÈGLES ABSOLUES (anti-hallucination) :\n"
    "- Tu n'utilises QUE les valeurs du JSON. Tu n'inventes AUCUN chiffre, prix, propriétaire, "
    "servitude, règlement, risque ni contrainte qui ne figure pas explicitement dans le JSON.\n"
    "- PROVENANCE : distingue toujours SOURCÉ (donnée réelle : prix DVF, zonage, occupation bâtie), "
    "ESTIMÉ (capacité constructible, coûts et charge foncière du bilan) et ABSENT / À VÉRIFIER (champ "
    "nul ou source muette). Appuie-toi sur le bloc `niveaux_fiabilite`.\n"
    "- Ne déclare JAMAIS une parcelle « constructible » de façon certaine : parle de « zone X, "
    "capacité ESTIMÉE » et renvoie à la vérification PLU/CU.\n"
    "- Si les données sont insuffisantes (sources muettes nombreuses, bilan non fiable), tu "
    "REFUSES de conclure et tu le dis clairement — mieux vaut « à vérifier » qu'une fausse certitude.\n"
    "- Termine TOUJOURS par une ligne **Fiabilité** (niveau global) et une ligne **Données manquantes** "
    "(liste des sources muettes / champs absents).\n"
    "- Aucune garantie réglementaire, de propriété ni de rentabilité.\n"
    "Ton : expert foncier prudent. Très concis, phrases courtes ; listes à puces autorisées."
)


def _num(x: Any) -> Any:
    return x if isinstance(x, (int, float)) and not isinstance(x, bool) else None


def is_configured() -> bool:
    """Vrai si la clé API Anthropic est présente → l'assistant LLM peut être activé côté UI.
    M11 socle 0 : source unique = core.has_key (plus de lecture d'env dupliquée)."""
    from ..ai import core
    return core.has_key()



def _niveaux_fiabilite(fiche: dict, *, fa: dict, bil: dict, occ: dict, v: dict) -> dict[str, Any]:
    """Carte de PROVENANCE déterministe (sourcé / estimé / absent) — dérivée des faits, jamais inventée.

    Donne au modèle (et à la synthèse règles) de quoi qualifier honnêtement chaque information."""
    source = []
    if fa.get("zone"):
        source.append("zonage PLU")
    if occ.get("disponible"):
        source.append("occupation bâtie (BD TOPO)")
    if (bil or {}).get("fiable"):
        source.append("prix de sortie (DVF)")
    estime = []
    if fa.get("constructible") is not None:
        estime.append("capacité constructible (réglementaire)")
    if bil:
        estime.append("coûts & charge foncière (bilan)")
    return {
        "sourcé": source or list(fiche.get("sources_responded") or []),
        "estimé": estime,
        "absent_ou_a_verifier": list(fiche.get("sources_silent") or []),
        # M36 Lot B : completude_sur_100/completude_niveau RETIRÉS (3 valeurs sur le parc —
        # n'informe pas ; M35 D3). La fiabilité se dit par les sources muettes, listées.
        "prix_bilan_fiable": (bil or {}).get("fiable"),
    }


def assistant_facts(fiche: dict) -> dict[str, Any]:
    """Liste BLANCHE des faits réels de la fiche → unique contenu du prompt (anti-hallucination).

    On ne transmet QUE des valeurs déjà calculées/sourcées : aucune reformulation, aucun ajout.
    `occupation_bati` et `niveaux_fiabilite` sont DÉRIVÉS de la fiche (toujours à partir du réel)."""
    p = fiche.get("parcel") or {}
    v = fiche.get("verdict") or {}
    fa = fiche.get("faisabilite") or {}
    fr = (fa.get("fourchette") or {}) if fa else {}
    bil = (fa.get("bilan") or {}) if fa else {}
    v3 = (fa.get("volume3d") or {}) if fa else {}
    occ = fiche.get("bati") or {}
    contraintes = [
        {"type": r.get("result"), "regle": r.get("layer_name"), "motif": r.get("detail")}
        for r in (fiche.get("cascade") or [])
        if r.get("result") in ("HARD_EXCLUDE", "SOFT_FLAG", "POSITIVE")
    ]
    return {
        "parcelle": {"idu": p.get("idu"), "commune": p.get("commune"),
                     "surface_m2": _num(p.get("surface_m2"))},
        # M34 (dette #14) : statut = TRADUCTION du tier servi (verdict_servi). Le motif legacy
        # (`signaux_vigilance`) est un signal non-franc informatif, plus jamais un déclassement.
        # M36 Lot B : score_opportunite/score_completude RETIRÉS des faits (l'IA cite les
        # faits — un score décorrélé du tier ne doit plus pouvoir être cité au client).
        "verdict": {"statut": v.get("status"),
                    "libelle": v.get("label"),
                    # M36 Lot C (Q3) : rang cité sur brûlante/chaude uniquement
                    "rang_servi": v.get("rang") if v.get("status") in ("brulante", "chaude") else None,
                    "badge_division": v.get("badge_division_libelle"),
                    "motif_servi": v.get("motif"),
                    "micro_opportunite": v.get("micro_opportunite"),
                    "signaux_vigilance": v.get("downgrade_reason")},
        "faisabilite": ({
            "zone_plu": fa.get("zone"), "constructible": fa.get("constructible"),
            "synthese": fa.get("verdict"),
            "niveaux": fr.get("niveaux"), "surface_plancher_m2": fr.get("surface_plancher_m2"),
            "logements_au_sol": fr.get("logements_au_sol"),
            "hauteur_m": fr.get("hauteur_m"), "volume_enveloppe_m3": v3.get("volume_m3"),
        } if fa else None),
        "bilan_promoteur": ({
            "verdict": bil.get("verdict"), "charge_fonciere": bil.get("charge_fonciere"),
            "fiable": bil.get("fiable"),
        } if bil else None),
        "occupation_bati": ({
            "label": occ.get("label"), "code": occ.get("code"),
            "ratio_bati_pct": _num(occ.get("ratio_pct")), "disponible": occ.get("disponible"),
        } if occ else None),
        # M33 — mode B : cité UNIQUEMENT avec son étiquette (Estimé + hypothèse travaux) ;
        # absent des faits hors population → l'IA ne peut pas l'inventer.
        "mode_b": ({
            "sortie_revente": {
                "prix_achat_max_rehab_eur": mb.get("achat_max_eur"),
                "prix_achat_max_rehab_libelle": mb.get("achat_max_libelle"),
                "etiquette": "Estimé", "negatif": mb.get("negatif"),
                "message_negatif": mb.get("message_negatif"),
            },
            # M44 — SORTIE LOCATIVE (côte à côte, jamais fusionnée) : loyer au plafond réglementaire
            # Sourcé (ou marché Estimé) ; prix d'achat max à rendement cible. Mention conseil-fiscal.
            "sortie_locative": ({
                "loyer_annuel_eur": (sl.get("loyer") or {}).get("annuel_eur"),
                "loyer_etiquette": (sl.get("loyer") or {}).get("etiquette"),
                "prix_achat_max_eur": sl.get("achat_max_eur"),
                "prix_achat_max_libelle": sl.get("achat_max_libelle"),
                "rendement_cible_pct": sl.get("rendement_cible_pct"),
                "etiquette": "Estimé", "negatif": sl.get("negatif"),
                "mention_conseil_fiscal": sl.get("mention_fiscale"),
            } if (sl := (mb.get("sortie_locative") or {})) else None),
            "travaux_hypothese_m2": ((mb.get("composantes") or {}).get("travaux") or {}).get("hypothese_m2"),
            "avertissement": mb.get("avertissement"),
        } if (mb := (fiche.get("mode_b") or {})).get("disponible") else None),
        "contraintes_et_signaux": contraintes,
        "completude": {
            "sources_ayant_repondu": fiche.get("sources_responded"),
            "sources_muettes_donnee_manquante": fiche.get("sources_silent"),
        },
        "niveaux_fiabilite": _niveaux_fiabilite(fiche, fa=fa, bil=bil, occ=occ, v=v),
        "resume_metier": fiche.get("resume"),
    }


# ── Synthèse DÉTERMINISTE (sans clé) — 5 blocs, dérivée UNIQUEMENT des faits ──────────────────────
# M135 — échelle d'action, mapping CANONIQUE unique (tiers_client) ; clés internes inchangées.
from ..scoring.tiers_client import TIERS_CLIENT as _TC, long as _tier_long
_STATUT_PHRASE = {k: v[1] for k, v in _TC.items()}
_STATUT_PHRASE["non_evaluee"] = "Non évaluée au run servi"


def _statut_phrase(statut: str | None, libelle: str | None) -> str:
    if statut and statut.startswith("declasse_"):
        return _tier_long(statut) or "Peu de potentiel"
    return _STATUT_PHRASE.get(statut, "Statut non évalué")


def _fmt_eur(x: Any) -> str:
    n = _num(x)
    if n is None:
        return "non chiffrée"
    ax = abs(n)
    if ax >= 1_000_000:
        return f"~{n / 1_000_000:.1f} M€"
    if ax >= 1_000:
        return f"~{n / 1_000:.0f} k€"
    return f"~{n:.0f} €"


def rules_summary(facts: dict) -> str:
    """Synthèse déterministe en 5 blocs (markdown), SANS LLM — ne fait que reformuler les faits.

    Anti-hallucination par construction : aucune valeur n'est produite, seulement restituée ; tout
    champ absent devient « donnée manquante / à vérifier ». Utilisée en démo quand la clé est absente,
    et comme aperçu quand elle est présente."""
    v = facts.get("verdict") or {}
    fa = facts.get("faisabilite") or {}
    bil = facts.get("bilan_promoteur") or {}
    occ = facts.get("occupation_bati") or {}
    fia = facts.get("niveaux_fiabilite") or {}
    contraintes = facts.get("contraintes_et_signaux") or []

    statut = v.get("statut")
    lignes: list[str] = []

    # 1. Potentiel
    pot = _statut_phrase(statut, v.get("libelle"))
    if v.get("rang_servi") and statut in ("brulante", "chaude"):
        pot += f" · rang {v['rang_servi']}"
    if v.get("badge_division"):
        pot += f" · {v['badge_division']}"
    if v.get("micro_opportunite"):
        pot += " · micro-opportunité (≤ 500 m²)"
    cap = ""
    if fa.get("zone_plu"):
        cap = f" Zone {fa['zone_plu']}"
        if fa.get("surface_plancher_m2"):
            logts = fa.get("logements_au_sol")
            # M36 Lot C (Q2) : bornes identiques → valeur unique (« 2 logements », pas « 2–2 »)
            lg = ""
            if isinstance(logts, list) and len(logts) == 2:
                lg = (f", {logts[0]} logements" if logts[0] == logts[1]
                      else f", {logts[0]}–{logts[1]} logements")
            cap += f", capacité ESTIMÉE ~{round(fa['surface_plancher_m2'])} m² de plancher{lg}"
        cap += "."
    lignes.append(f"**Potentiel** — {pot}.{cap}")

    # 2. Contraintes
    blk = [c for c in contraintes if c.get("type") in ("HARD_EXCLUDE", "SOFT_FLAG")]
    if statut and statut.startswith("declasse_") and v.get("motif_servi"):
        lignes.append(f"**Contraintes** — Déclassement (run servi) : {v['motif_servi']}.")
    elif v.get("signaux_vigilance"):
        lignes.append(f"**Contraintes** — À vérifier (signal non-franc) : {v['signaux_vigilance']}.")
    elif blk:
        items = "; ".join(f"{c.get('motif')}" for c in blk[:4] if c.get("motif"))
        lignes.append(f"**Contraintes** — {items}.")
    else:
        lignes.append("**Contraintes** — Aucune contrainte bloquante dans les données disponibles "
                      "(une donnée manquante n'est pas une absence de risque).")

    # 3. Bâti / libre
    if occ.get("disponible") and occ.get("label"):
        r = occ.get("ratio_bati_pct")
        lignes.append(f"**Bâti / libre** — {occ['label']}"
                      + (f" ({r} % bâti, BD TOPO)." if r is not None else " (BD TOPO)."))
    else:
        lignes.append("**Bâti / libre** — Occupation non vérifiée (couche bâtiments non disponible).")

    # 4. Économie indicative
    if bil:
        cf = bil.get("charge_fonciere")
        cf_val = cf.get("central") if isinstance(cf, dict) else cf
        fiable = bil.get("fiable")
        qual = "prix de sortie fiable" if fiable else "prix de sortie fragile — ordre de grandeur"
        lignes.append(f"**Économie indicative** — Charge foncière INDICATIVE {_fmt_eur(cf_val)} "
                      f"({qual} ; coûts estimés).")
    else:
        lignes.append("**Économie indicative** — Non chiffrée (prix DVF insuffisant — pas de bilan inventé).")
    # M33 — mode B : cité UNIQUEMENT si présent, toujours ESTIMÉ avec son hypothèse travaux.
    mb = facts.get("mode_b") or {}
    if mb:
        rev = mb.get("sortie_revente") or {}
        if rev.get("negatif"):
            # M59-P1 (Q5) « mode B » retiré de l'affichage · (Q1) plus de « prix d'achat max » seul.
            lignes.append(f"**Réhabilitation · revente** — {rev.get('message_negatif')} (ESTIMÉ).")
        else:
            lignes.append(f"**Réhabilitation · revente** — ce que la réhabilitation du bâti justifie "
                          f"~{rev.get('prix_achat_max_rehab_libelle')} (ESTIMÉ, hors valeur du terrain) "
                          f"— hypothèse travaux ~{mb.get('travaux_hypothese_m2')} €/m², à ajuster.")
        # M44 — sortie LOCATIVE, côte à côte, jamais fusionnée ; mention conseil-fiscal.
        sl = mb.get("sortie_locative") or {}
        if sl:
            lignes.append(f"**Réhabilitation · locatif** — loyer ~{sl.get('loyer_annuel_eur')} €/an "
                          f"[{sl.get('loyer_etiquette')}], prix d'achat max ~{sl.get('prix_achat_max_libelle')} "
                          f"(ESTIMÉ) à rendement cible {sl.get('rendement_cible_pct')} %. "
                          "Hypothèses fiscales indicatives — à valider avec un conseil fiscal.")

    # 5. Recommandation
    reco = (facts.get("resume_metier") or {}).get("prochaine_action")
    if not reco:
        if statut and statut.startswith("declasse_"):
            reco = "Écarter, ou vérifier sur le terrain si le motif de déclassement semble erroné."
        else:
            reco = {
                "brulante": "Vérifier le PLU/CU, croiser PPR/SAR, puis identifier le propriétaire avant de démarcher.",
                "chaude": "Vérifier le PLU/CU, croiser PPR/SAR, puis identifier le propriétaire avant de démarcher.",
                "reserve_fonciere": "Suivre la parcelle — potentiel réel à horizon plus lointain ; vérifier PLU et contraintes.",
                "a_creuser": "Compléter les données manquantes (risques, pente, propriétaire) avant d'investir du temps.",
                "ecartee": "Ne pas prospecter : hors classement servi.",
            }.get(statut, "Vérifier les données avant toute décision.")
    if v.get("micro_opportunite"):
        reco += " Petite parcelle : étudier l'assemblage avec les voisines."
    lignes.append(f"**Recommandation** — {reco}")

    # Mentions obligatoires : fiabilité globale + données manquantes.
    # M36 Lot B : plus de « complétude N/100 » (quasi-constante) — la fiabilité se dit par
    # les sources muettes, comptées ici et LISTÉES au bloc suivant.
    manq_n = len(fia.get("absent_ou_a_verifier") or [])
    lignes.append("**Fiabilité** — "
                  + (f"{manq_n} source(s) muette(s) sur cette parcelle"
                     if manq_n else "toutes les sources interrogées ont répondu")
                  + (".  Bilan : prix de sortie fragile." if bil and bil.get("fiable") is False else "."))
    manq = fia.get("absent_ou_a_verifier") or []
    lignes.append("**Données manquantes** — " + (", ".join(manq) if manq else "aucune source muette signalée."))
    return "\n".join(lignes)


def _no_key(facts: dict) -> dict[str, Any]:
    """Réponse sans clé : état PREMIER propre + synthèse règles déterministe (jamais « cassé »)."""
    return {"available": False, "reason": "no_key", "facts": facts,
            "rules_summary": rules_summary(facts),
            "message": "Analyse IA enrichie disponible sur activation (clé API). Ci-dessous, la "
                       "synthèse automatique dérivée des seules données de la fiche."}


def explain_parcel(fiche: dict, *, timeout: float = 25.0) -> dict[str, Any]:
    """Synthèse en prose via l'API Anthropic. Dégrade PROPREMENT : clé absente / réseau / timeout
    → `available=False` + synthèse règles + message clair, jamais d'exception remontée à l'endpoint."""
    from ..ai import core  # M11 socle 0 : client IA unique (plus de httpx propre ici)
    facts = assistant_facts(fiche)
    if not core.has_key():
        return _no_key(facts)
    model = os.environ.get(ENV_MODEL, "").strip() or core.MODEL_REASONING
    # M-T V1 — couche 2 (ancrage mécanique des chiffres). Le contexte devient STRUCTURÉ (dict `facts`)
    # car validate=True l'exige ; le SYSTEM impose déjà « UNIQUEMENT du JSON fourni ». require_sources
    # =False (ce prompt n'émet pas de marqueurs ⟨src:…⟩) ; seule la couche 2 s'applique.
    res = core.complete(
        None, kind="explain", model=model, max_tokens=700, timeout=timeout, system=SYSTEM,
        context=facts, validate=True, require_sources=False, strict_numbers=True)
    # Au moindre doute — clé/réseau/timeout/API (degraded), chiffre non ancré (rejected), ou vide —
    # on NE sert JAMAIS « indisponible » : on sert la synthèse règles DÉTERMINISTE (le stub), flaggée.
    if res.degraded or res.rejected or not res.text:
        motif = ("chiffre non ancré" if res.rejected
                 else "vide" if not res.text else (res.reason or "error"))
        return {"available": False, "stub": True, "reason": motif, "facts": facts,
                "rules_summary": rules_summary(facts),
                "message": "Synthèse automatique dérivée des seules données de la fiche "
                           "(analyse IA enrichie non servie : " + motif + ")."}
    return {"available": True, "explanation": res.text, "model": res.model}
