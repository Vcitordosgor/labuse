"""M44 — SORTIE LOCATIVE du mode B : point de calcul UNIQUE (loyer plafond Sourcé ou marché Estimé).

RÈGLE FISCALE (arbitrage Vic) : on sert un BILAN AU PLAFOND réglementaire Sourcé, DISPOSITIF-
AGNOSTIQUE — jamais un badge d'éligibilité. Paramètres millésimés `config/calibrage/defisc_<annee>.yaml`
(source + date par entrée), lint qui refuse l'incomplet (modèle M41). Héritage d'étiquette M33 : le
prix d'achat max intègre le coût travaux (Estimé) → il est TOUJOURS Estimé, même au plafond Sourcé.

Sources : BOFiP BOI-BAREME-000017-20260310 (plafonds 2026) + CGI (coefficient de surface).
"""
from __future__ import annotations

from ..config import load_yaml_config

ANNEE_ACTIVE = 2026   # bascule annuelle (loi de finances) : pointer le defisc_<annee>.yaml courant


def _config() -> dict:
    return load_yaml_config(f"calibrage/defisc_{ANNEE_ACTIVE}") or {}


# ─────────────────────────────── LINT (schéma strict, modèle M41) ───────────────────────────────

def lint(cfg: dict | None = None) -> list[str]:
    """Refuse toute config incomplète : chaque plafond/coef porte valeur + source + date ; rendement
    cible complet. Retourne la liste des erreurs (vide = OK). Un défaut incomplet ne doit pas servir."""
    cfg = cfg if cfg is not None else _config()
    errs: list[str] = []
    if not cfg:
        return [f"config defisc_{ANNEE_ACTIVE}.yaml absente ou vide"]
    if not cfg.get("mention_conseil_fiscal"):
        errs.append("mention_conseil_fiscal obligatoire (dossier avocat)")
    plaf = cfg.get("plafonds_loyer") or {}
    for regime in ("base", "intermediaire"):
        p = plaf.get(regime) or {}
        for k in ("valeur_eur_m2_mois", "source", "date"):
            if not p.get(k):
                errs.append(f"plafonds_loyer.{regime}.{k} manquant")
    if cfg.get("defaut_regime") not in plaf:
        errs.append(f"defaut_regime « {cfg.get('defaut_regime')} » absent des plafonds")
    cs = cfg.get("coef_surface") or {}
    for k in ("constante", "numerateur", "plafond_max", "source", "date"):
        if cs.get(k) is None:
            errs.append(f"coef_surface.{k} manquant")
    rc = cfg.get("rendement_cible") or {}
    for k in ("defaut_pct", "bornes_pct", "etiquette", "justification"):
        if rc.get(k) in (None, ""):
            errs.append(f"rendement_cible.{k} manquant (défaut doit être justifié, pas sorti du chapeau)")
    return errs


def mention_fiscale() -> str:
    return _config().get("mention_conseil_fiscal", "") or ""


def dispositifs_non_couverts() -> list[str]:
    return list(_config().get("dispositifs_non_couverts") or [])


def message_non_couvert() -> str:
    return _config().get("message_non_couvert", "Dispositif non couvert à ce jour.") or ""


# ─────────────────────────── coefficient de surface (pur, testable) ───────────────────────────

def coef_surface(shab_m2: float, cfg: dict | None = None) -> float:
    """Coefficient réglementaire = constante + numerateur/S, plafonné à `plafond_max`. Le cap mord
    pour les PETITES surfaces (≤ 38 m² au barème 2026), descend vers `constante` pour les grandes.
    Pur : point de calcul unique, testé aux bornes."""
    cs = (cfg or _config()).get("coef_surface") or {}
    k, num, cap = float(cs.get("constante", 0.7)), float(cs.get("numerateur", 19.0)), float(cs.get("plafond_max", 1.2))
    if not shab_m2 or shab_m2 <= 0:
        return cap
    return round(min(k + num / float(shab_m2), cap), 4)


def _rendement_defaut(cfg: dict) -> float:
    return float((cfg.get("rendement_cible") or {}).get("defaut_pct", 6.0))


def sortie_locative(shab_m2: float, cout_travaux_eur: float, *,
                    regime: str | None = None, loyer_marche_m2: float | None = None,
                    rendement_cible_pct: float | None = None) -> dict | None:
    """Bilan de SORTIE LOCATIVE d'une parcelle mode B. Point de calcul UNIQUE.

    Loyer retenu : plafond réglementaire (Sourcé BOFiP, `regime` base/intermédiaire) × coef surface,
    OU `loyer_marche_m2` (paramètre CLIENT, Estimé — pas de coef réglementaire). Retourne loyer
    mensuel/annuel + PRIX D'ACHAT MAX à rendement cible (= loyer annuel / rendement − coût travaux).
    Étiquette de l'achat max : TOUJOURS Estimé (contient les travaux Estimé, héritage M33)."""
    cfg = _config()
    if not shab_m2 or shab_m2 <= 0:
        return None
    plaf = cfg.get("plafonds_loyer") or {}
    coef = coef_surface(shab_m2, cfg)
    if loyer_marche_m2 is not None:   # voie (b) — marché, paramètre client, Estimé, PAS de coef réglementaire
        loyer_m2_eff = float(loyer_marche_m2)
        loyer_regime, loyer_etiquette = "marche", "Estimé (loyer de marché, paramètre client)"
        loyer_source, loyer_date, plafond_brut = "paramètre client", None, None
    else:                              # voie (a) — plafond réglementaire Sourcé (défaut = le plus prudent)
        regime = regime or cfg.get("defaut_regime", "base")
        p = plaf.get(regime) or plaf.get("base") or {}
        plafond_brut = float(p.get("valeur_eur_m2_mois", 0))
        loyer_m2_eff = round(plafond_brut * coef, 2)
        loyer_regime = regime
        loyer_etiquette = f"Sourcé ({p.get('source')} · {p.get('date')})"
        loyer_source, loyer_date = p.get("source"), p.get("date")

    rc = rendement_cible_pct if rendement_cible_pct is not None else _rendement_defaut(cfg)
    _bornes = (cfg.get("rendement_cible") or {}).get("bornes_pct", [3.0, 12.0])
    rc = min(max(float(rc), float(_bornes[0])), float(_bornes[1]))
    loyer_mensuel = loyer_m2_eff * float(shab_m2)
    loyer_annuel = loyer_mensuel * 12.0
    investissement_cible = loyer_annuel / (rc / 100.0) if rc > 0 else 0.0
    achat_max = investissement_cible - float(cout_travaux_eur or 0)

    return {
        "disponible": True,
        "loyer": {
            "m2_mois_effectif": round(loyer_m2_eff, 2),
            "plafond_brut_m2": round(plafond_brut, 2) if plafond_brut else None,
            "coef_surface": coef if loyer_regime != "marche" else None,
            "regime": loyer_regime,
            "mensuel_eur": round(loyer_mensuel),
            "annuel_eur": round(loyer_annuel),
            "etiquette": loyer_etiquette, "source": loyer_source, "date": loyer_date,
        },
        "rendement_cible_pct": round(rc, 1),
        "rendement_cible_etiquette": "Estimé (paramètre client)",
        # HÉRITAGE M33 : contient les travaux (Estimé) → l'ensemble est Estimé, même au plafond Sourcé.
        "etiquette": "Estimé",
        "achat_max_eur": round(achat_max),
        "achat_max_libelle": _eur_k(achat_max),
        "negatif": achat_max <= 0,
        "message_negatif": ("bilan locatif négatif au rendement cible et coût travaux courants — "
                            "le loyer plafonné n'absorbe pas l'investissement" if achat_max <= 0 else None),
        "formule": (f"prix d'achat max locatif = loyer annuel / rendement cible − coût travaux "
                    f"= {round(loyer_annuel)} / {round(rc, 1)}% − {round(float(cout_travaux_eur or 0))}"),
        "mention_fiscale": mention_fiscale(),
    }


def _eur_k(x: float) -> str:
    """Format k€ (un Estimé à l'euro près contredit son étiquette) — même esprit que le mode B M33."""
    if x is None:
        return "—"
    if abs(x) >= 1000:
        return f"{x/1000:.0f} k€"
    return f"{round(x)} €"
