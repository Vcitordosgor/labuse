"""M78 · 1b — BOÎTE À OUTILS QUESTION.

Chaque outil APPELLE le point de calcul EXISTANT (jamais un SQL de scoring/marché réécrit) et renvoie
un `ToolResult` avec source + millésime. Import PARESSEUX des symboles d'`api.app`/`api.modules`
(motif `ia.py`) pour éviter le cycle app→router→outils→app. Interdit : `requete_libre(sql)`.

Preuve de non-recréation (RAPPORT_M78 §1b) : les comptages passent par `filtre()` (facette canonique,
égalité validée à l'oracle indépendant) ; le marché par `build_marche_commune` ; la fiche par
`_q_v2_fiche` ; les stats par `commune_contexte` ; les délais par `velocite` (réserve Sitadel citée
mot pour mot) ; le patrimoine par `patrimoine`. Le tier/verdict est LU du run servi, jamais recalculé.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from ..scoring.score_v_constants import Q_A_RUN_LABEL as RUN


@dataclass
class ToolResult:
    tool: str
    ok: bool = True
    valeur: Any = None                       # le chiffre principal (pour l'anti-invention)
    data: dict[str, Any] = field(default_factory=dict)
    source: str | None = None
    millesime: str | None = None
    partiel: bool = False                     # couverture partielle → la réserve DOIT être dite
    reserve: str | None = None                # texte de réserve (cité mot pour mot depuis le point de calcul)
    refus: str | None = None                  # motif de refus si l'outil ne peut pas répondre


# ───────────────────────── compter_parcelles ─────────────────────────
_TIER_ALIAS = {"opportunites": "brulante,chaude", "opportunité": "brulante,chaude",
               "brulante": "brulante", "brûlante": "brulante", "chaude": "chaude",
               "reserve": "reserve", "a_creuser": "a_creuser"}


def compter_parcelles(db: Session, *, commune: str | None = None, surface_min: int | None = None,
                      surface_max: int | None = None, tier: str | None = None,
                      personne_morale: bool = False) -> ToolResult:
    """Compte via la FACETTE canonique `filtre()` (mêmes chiffres que la recherche à l'écran)."""
    from ..api.app import FiltreCriteres, filtre
    tiers = _TIER_ALIAS.get((tier or "").lower().strip()) if tier else None
    fc = FiltreCriteres(source=RUN, commune=commune,
                        surface_min=int(surface_min) if surface_min is not None else None,
                        surface_max=int(surface_max) if surface_max is not None else None,
                        tiers=tiers, personne_morale=bool(personne_morale))
    out = filtre(c=fc, limit=0, offset=0, sort=None, idus=0, groupes=0, db=db)
    n = out.get("compte")
    crit = {k: v for k, v in {"commune": commune, "surface_min": surface_min,
            "surface_max": surface_max, "tier": tiers, "personne_morale": personne_morale or None}.items()
            if v is not None}
    return ToolResult("compter_parcelles", valeur=n, data={"compte": n, "criteres": crit},
                      source="Recherche à facettes LABUSE (run servi)", millesime=RUN)


# ───────────────────────── parcelles_par_entreprise ─────────────────────────
_FOLD = ("translate({c}, 'àâäáéèêëíìîïóòôöúùûüçÀÂÄÁÉÈÊËÍÌÎÏÓÒÔÖÚÙÛÜÇ',"
         "'aaaaeeeeiiiioooouuuucAAAAEEEEIIIIOOOOUUUUC')")
_ACCENTS = str.maketrans("àâäáéèêëíìîïóòôöúùûüçÀÂÄÁÉÈÊËÍÌÎÏÓÒÔÖÚÙÛÜÇ",
                         "aaaaeeeeiiiioooouuuucAAAAEEEEIIIIOOOOUUUUC")


def _fold_py(s: str) -> str:
    return s.translate(_ACCENTS)


def parcelles_par_entreprise(db: Session, *, q: str) -> ToolResult:
    """Patrimoine d'une personne morale (nom ou SIREN) via `patrimoine` (DGFiP open data). Résolution
    nom→SIREN accent-INSENSIBLE (le client tape « Société », la base stocke « SOCIETE »)."""
    from sqlalchemy import text as _text

    from ..api.modules import patrimoine
    q = (q or "").strip()
    siren = q if q.isdigit() and len(q) >= 9 else None
    if siren is None:
        # matching par TOKENS : chaque mot significatif du nom doit être présent (accent-insensible),
        # robuste aux mots de liaison (« du », « de la ») que la dénomination DGFiP n'a pas.
        _stop = {"de", "du", "la", "le", "les", "des", "et", "au", "aux", "sci", "sarl", "sas"}
        toks = [t for t in q.replace("'", " ").replace("-", " ").lower().split()
                if len(t) >= 3 and t not in _stop]
        if not toks:
            return ToolResult("parcelles_par_entreprise", ok=False, refus=f"nom trop court : « {q} »")
        conds = " AND ".join(f"lower({_FOLD.format(c='denomination')}) LIKE :t{i}" for i in range(len(toks)))
        params = {f"t{i}": f"%{_fold_py(t)}%" for i, t in enumerate(toks)}
        row = db.execute(_text(
            f"SELECT siren FROM parcelle_personne_morale WHERE siren IS NOT NULL AND {conds} "
            f"GROUP BY siren ORDER BY count(*) DESC LIMIT 1"), params).first()
        if not row:
            return ToolResult("parcelles_par_entreprise", ok=False,
                              refus=f"aucune personne morale trouvée pour « {q} »")
        siren = row[0]
    res = patrimoine(siren=siren, db=db)
    return ToolResult("parcelles_par_entreprise", valeur=res["n_parcelles"],
                      data={"siren": siren, "nom": res["nom"], "n_parcelles": res["n_parcelles"],
                            "sdp_totale_m2": res["sdp_totale_m2"],
                            "bodacc": res.get("bodacc")},
                      source="DGFiP — parcelles de personnes morales (SIREN public)")


# ───────────────────────── fiche_parcelle ─────────────────────────
def fiche_parcelle(db: Session, *, idu: str) -> ToolResult:
    """Données d'UNE parcelle via `_q_v2_fiche` (verdict/zonage/risques LUS, jamais recalculés)."""
    from ..api.app import _q_v2_fiche
    f = _q_v2_fiche(db, idu, run_label=RUN)
    if not f or f.get("commune") is None:
        return ToolResult("fiche_parcelle", ok=False, refus=f"parcelle {idu} introuvable")
    sv2 = f.get("score_v2") or {}
    reg = (f.get("reglement_plu") or {}).get("zones") or []
    data = {"idu": idu, "commune": f.get("commune"), "surface_m2": f.get("surface_m2"),
            "zone": (reg[0].get("zone") if reg else None),
            "verdict": sv2.get("verdict") or sv2.get("libelle") or sv2.get("tier"),
            "etage0": f.get("etage0")}
    return ToolResult("fiche_parcelle", valeur=f.get("surface_m2"), data=data,
                      source="Fiche parcelle LABUSE (run servi)", millesime=RUN)


# ───────────────────────── stats_commune ─────────────────────────
def stats_commune(db: Session, *, commune: str) -> ToolResult:
    """Contexte commune via `commune_contexte` (SRU + INSEE logement — chaque bloc sa source)."""
    from ..api.app import commune_contexte
    c = commune_contexte(commune, db=db)
    sru = c.get("sru") or {}
    marche = c.get("marche") or {}
    if not sru and not marche:
        return ToolResult("stats_commune", ok=False, refus=f"commune {commune} inconnue au contexte")
    data = {"commune": commune, "taux_lls": sru.get("taux_lls"), "sru_statut": sru.get("statut"),
            "objectif_pct": sru.get("objectif_pct"), "logements": marche.get("logements"),
            "proprietaires_pct": marche.get("proprietaires_pct")}
    return ToolResult("stats_commune", data=data, source="INSEE (logement) · Inventaire SRU",
                      millesime=sru.get("millesime") or marche.get("millesime"))


# ───────────────────────── delais_instruction ─────────────────────────
def delais_instruction(db: Session, *, commune: str) -> ToolResult:
    """Délai médian d'instruction via `velocite` — la RÉSERVE Sitadel est CITÉE mot pour mot."""
    from ..api.modules import velocite
    v = velocite(fmt="json", nature=None, db=db)
    row = next((r for r in v["communes"] if r["commune"] == commune), None)
    if not row or row.get("delai_median_mois") is None:
        return ToolResult("delais_instruction", ok=False, refus=f"aucun délai mesurable à {commune}")
    n_mur = row.get("n_mur")
    # Réserve = censure (accordés seulement) + disclaimer (historique) + limite type/service, mot pour mot.
    reserve = (v["censure"] + " " + v["disclaimer"]
               + " Je n'ai pas le détail par type de dossier ni par service.")
    if n_mur is not None and n_mur < 30:
        reserve += f" Échantillon faible ({n_mur} permis) — à prendre avec prudence."
    data = {"commune": commune, "delai_median_mois": row["delai_median_mois"], "n_mur": n_mur,
            "n_permis_accordes": row.get("n_valide"), "tendance": row.get("tendance")}
    return ToolResult("delais_instruction", valeur=row["delai_median_mois"], data=data,
                      source="Sitadel — délais d'instruction (dossiers accordés)",
                      millesime=v.get("cohortes"), partiel=True, reserve=reserve)


# ───────────────────────── marche ─────────────────────────
def marche(db: Session, *, commune: str) -> ToolResult:
    """Marché commune via `build_marche_commune` (point de calcul unique, terrain nu M79 inclus)."""
    from ..faisabilite.marche_commune import build_marche_commune
    m = build_marche_commune(db, commune)
    lignes = [{"cle": l.get("cle") or l.get("libelle"), "valeur": l.get("valeur"),
               "source": l.get("source"), "millesime": l.get("millesime")}
              for l in (m.get("lignes") or []) if isinstance(l, dict)]
    return ToolResult("marche", data={"commune": commune, "lignes": lignes},
                      source="Marché commune LABUSE (DVF, Sitadel, DHUP — terrain nu M79)",
                      millesime="par ligne (fraîcheur = source amont)")


# Registre nom → fonction (l'exécuteur du serveur ; le modèle choisit le NOM, jamais le SQL).
OUTILS = {
    "compter_parcelles": compter_parcelles,
    "parcelles_par_entreprise": parcelles_par_entreprise,
    "fiche_parcelle": fiche_parcelle,
    "stats_commune": stats_commune,
    "delais_instruction": delais_instruction,
    "marche": marche,
}
