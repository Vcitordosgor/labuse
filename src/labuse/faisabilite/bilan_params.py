"""Paramètres du bilan promoteur (1.C) — registre unique + résolution par SECTEUR.

Objectif : rendre la calibration FACILE (Vic fournit les vraies valeurs réunionnaises). Tous les
paramètres du bilan sont déclarés ici une seule fois (libellé, groupe, unité, défaut, placeholder),
éditables en UI et persistés par secteur (bassin PLU). Le code n'invente AUCUNE valeur : les params
non calibrés sont marqués `is_placeholder` et signalés « non calibré » dans la fiche.

Résolution : défaut registre ← override global (secteur='*') ← override secteur. Un override
CONFIRMÉ (saisi/sourcé par Vic) n'est plus « placeholder » ; un override de provenance
« estimee » RESTE placeholder tant qu'il n'est pas confirmé (mandat hypothèses bilan,
décision Vic 28/07/2026 — le 2100 provisoire du 14/06 était devenu invisible aux bandeaux).

PRÉSÉANCE DU COÛT DE CONSTRUCTION (gravée au mandat hypothèses bilan, Vic 28/07/2026) :
  1. source unique = fourchette `hypotheses_faisabilite` du YAML PLU (auditée O2 : 2300-2800
     €/m² de plancher) — le défaut registre de `cout_construction_m2_sdp` vaut 0, qui signifie
     « repli fourchette YAML » dans `compute_bilan` ;
  2. un override SECTORIEL justifié et sourcé peut re-piloter le coût (table, provenance) ;
  3. JAMAIS de défaut codé silencieux — le test-verrou anti-constante de coût l'atteste.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

SECTEUR_GLOBAL = "*"

# key, libellé, groupe, unité, défaut, is_placeholder, critique
# `critique` = sans calibration, le bilan affiche un bandeau « non fiable ».
PARAMS: list[tuple[str, str, str, str, float, bool, bool]] = [
    # Recettes
    ("prix_m2_neuf", "Prix de vente neuf (override ; 0 = DVF du secteur)", "Recettes", "€/m²", 0.0, True, False),
    ("prix_m2_lls", "Prix de sortie logement aidé (LLS)", "Recettes", "€/m²", 0.0, True, False),
    # `ratio_vendable` RETIRÉ (décision Vic 28/07/2026, mandat calibration estimées §3) : aucun
    # moteur ne le lisait (le rendement SDP→habitable est `coef_rendement` des hypothèses YAML) —
    # un curseur qui ne calibre rien trompe l'utilisateur. Le re-brancher = décision explicite
    # avec mesure d'impact. Idem `bonus_vue_mer_pct` (ligne orpheline en base, jamais au registre).
    # Coûts
    ("cout_construction_m2_sdp", "Coût de construction (0 = fourchette YAML auditée)", "Coûts", "€/m² SDP", 0.0, False, True),
    ("cout_vrd_base", "VRD / viabilisation de base", "Coûts", "€/m² terrain", 0.0, True, False),
    ("majoration_vrd_pente_pct", "Majoration VRD — pente forte", "Coûts", "%", 0.0, True, False),
    ("majoration_vrd_assainissement_pct", "Majoration VRD — assainissement autonome", "Coûts", "%", 0.0, True, False),
    # Frais & marge
    ("honoraires_pct", "Honoraires + commercialisation", "Frais & marge", "% du CA", 12.0, False, False),
    ("frais_financiers_pct", "Frais financiers", "Frais & marge", "% du CA", 0.0, True, False),
    ("marge_cible_pct", "Marge cible promoteur", "Frais & marge", "% du CA", 9.0, False, False),
]
_BY_KEY = {p[0]: p for p in PARAMS}
CRITIQUES = [p[0] for p in PARAMS if p[6]]


def defaults() -> dict[str, float]:
    return {p[0]: p[4] for p in PARAMS}


def registry() -> list[dict]:
    """Description des paramètres pour l'UI (groupés, dans l'ordre)."""
    return [{"key": k, "label": lbl, "groupe": grp, "unite": u,
             "defaut": d, "is_placeholder_defaut": ph, "critique": crit}
            for (k, lbl, grp, u, d, ph, crit) in PARAMS]


def resolve(session: Session, secteur: str | None) -> dict[str, dict]:
    """Params effectifs pour un secteur : {key: {value, is_placeholder, source, provenance}}.
    défaut ← override global ← override secteur. Un override saisi n'est plus placeholder ;
    `provenance` (sourcee|estimee|None) distingue une valeur sourcée d'une estimée à affiner."""
    out: dict[str, dict] = {
        k: {"value": v[4], "is_placeholder": v[5], "source": "défaut", "provenance": None}
        for k, v in _BY_KEY.items()}
    rows = session.execute(text(
        "SELECT secteur, param, value, provenance FROM bilan_params WHERE secteur IN ('*', :s)"),
        {"s": secteur or "*"}).all()
    # appliquer global puis secteur (le secteur prime)
    for sect_target in (SECTEUR_GLOBAL, secteur):
        for sect, param, value, prov in rows:
            if sect == sect_target and param in out:
                # Une valeur ESTIMÉE non confirmée RESTE placeholder (visible aux bandeaux) —
                # c'est le verrou anti-« provisoire devenu permanent » (décision Vic 28/07/2026).
                out[param] = {"value": float(value), "is_placeholder": prov == "estimee",
                              "source": "global" if sect == SECTEUR_GLOBAL else "secteur",
                              "provenance": prov}
    return out


def values(session: Session, secteur: str | None) -> dict[str, float]:
    return {k: r["value"] for k, r in resolve(session, secteur).items()}


def uncalibrated_critical(resolved: dict[str, dict]) -> list[str]:
    """Libellés des paramètres CRITIQUES encore SANS valeur (→ bandeau « non fiable » DUR)."""
    return [_BY_KEY[k][1] for k in CRITIQUES if resolved.get(k, {}).get("is_placeholder", True)]


# Paramètres dont l'affinage par un vrai promoteur change le plus le bilan (cf rapport).
REFINE_KEYS = list(dict.fromkeys(CRITIQUES + ["marge_cible_pct"]))


def estimated_to_refine(resolved: dict[str, dict]) -> list[str]:
    """Libellés des paramètres clés RENSEIGNÉS mais ESTIMÉS (→ sous-bandeau « à affiner », pas dur)."""
    return [_BY_KEY[k][1] for k in REFINE_KEYS
            if resolved.get(k, {}).get("provenance") == "estimee"]


def estimees_non_confirmees(session: Session, jours: int = 30) -> list[dict]:
    """Contrôle anti-« provisoire devenu permanent » (décision Vic 28/07/2026) : liste les
    overrides de provenance « estimee » jamais confirmés depuis plus de `jours` jours —
    le scénario du 2100 (estimation du 14/06 restée 6 semaines en base) ne doit pas se
    reproduire en silence. Confirmation = re-saisie par Vic (gabarit CSV ou UI) qui pose
    provenance sourcée/NULL. Exposé par `labuse bilan-params-perimes`."""
    rows = session.execute(text(
        "SELECT secteur, param, value, updated_at, "
        "       extract(day FROM now() - updated_at)::int AS age_jours "
        "FROM bilan_params WHERE provenance = 'estimee' AND now() - updated_at > make_interval(days => :j) "
        "ORDER BY updated_at, secteur, param"), {"j": jours}).mappings().all()
    return [{"secteur": r["secteur"], "param": r["param"], "value": float(r["value"]),
             "age_jours": r["age_jours"],
             "libelle": _BY_KEY.get(r["param"], (None, r["param"]))[1]} for r in rows]


def save(session: Session, secteur: str, param: str, value: float | None) -> None:
    """Enregistre (ou efface si value=None) un override de param pour un secteur."""
    if param not in _BY_KEY:
        raise ValueError(f"paramètre inconnu : {param}")
    if value is None:
        session.execute(text("DELETE FROM bilan_params WHERE secteur=:s AND param=:p"),
                        {"s": secteur, "p": param})
        return
    session.execute(text(
        """INSERT INTO bilan_params (secteur, param, value, is_placeholder, updated_at)
           VALUES (:s,:p,:v, false, now())
           ON CONFLICT (secteur, param) DO UPDATE SET value=EXCLUDED.value,
             is_placeholder=false, updated_at=now()"""),
        {"s": secteur, "p": param, "v": float(value)})


# ── Injection du gabarit de calibration rempli par Vic (config/bilan_calibration_vic.csv) ──
def read_calibration_csv(path: str) -> list[dict]:
    """Lit le gabarit CSV. Ignore les lignes « # » et celles dont « valeur » est vide.

    N'exige que les colonnes secteur/param/valeur/source ; les colonnes-repères sont ignorées.
    """
    import csv

    out: list[dict] = []
    with open(path, encoding="utf-8") as fh:
        reader = csv.DictReader(ln for ln in fh if not ln.lstrip().startswith("#"))
        for row in reader:
            val = (row.get("valeur") or "").strip()
            if not val:
                continue   # ligne non renseignée → on garde l'estimation actuelle
            out.append({
                "secteur": (row.get("secteur") or "").strip(),
                "param": (row.get("param") or "").strip(),
                "valeur": val,
                "source": (row.get("source") or "").strip(),
            })
    return out


def apply_calibration(session: Session, rows: list[dict], dry_run: bool = False) -> dict:
    """Applique les lignes de calibration (upsert par secteur). Ne touche pas aux lignes absentes.

    Une valeur saisie par Vic devient `provenance='sourcee'` si une source est fournie (sinon NULL,
    mais jamais « estimee ») et `is_placeholder=false` → le sous-bandeau « à affiner » disparaît
    pour ce paramètre. Retour : {applied: [...], errors: [(secteur, param, msg)]}.
    """
    applied: list[dict] = []
    errors: list[tuple[str, str, str]] = []
    for r in rows:
        secteur, param = r.get("secteur", ""), r.get("param", "")
        if param not in _BY_KEY:
            errors.append((secteur, param, "paramètre inconnu"))
            continue
        if not secteur:
            errors.append((secteur, param, "secteur vide"))
            continue
        try:
            value = float(str(r["valeur"]).replace(",", ".").strip())
        except (ValueError, KeyError):
            errors.append((secteur, param, f"valeur non numérique : {r.get('valeur')!r}"))
            continue
        prov = "sourcee" if r.get("source") else None
        if not dry_run:
            session.execute(text(
                """INSERT INTO bilan_params (secteur, param, value, is_placeholder, provenance, updated_at)
                   VALUES (:s,:p,:v, false, :pr, now())
                   ON CONFLICT (secteur, param) DO UPDATE SET value=EXCLUDED.value,
                     is_placeholder=false, provenance=EXCLUDED.provenance, updated_at=now()"""),
                {"s": secteur, "p": param, "v": value, "pr": prov})
        applied.append({"secteur": secteur, "param": param, "value": value,
                        "provenance": prov, "source": r.get("source", "")})
    return {"applied": applied, "errors": errors}
