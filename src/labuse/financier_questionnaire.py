"""EXPORTS-2 lot 4 — LE QUESTIONNAIRE DU FINANCIER : 4 écrans, ~20 champs, persistés dans le
Projet de l'utilisateur (table `questionnaire_financier`, cloison par compte). Chaque champ est un
id de portée `projet` du registre.

Trois règles (décisions Vic) :
  1. Chaque pré-remplissage porte SA SOURCE (une ligne). Un pré-remplissage sans source n'est PAS
     émis (un chiffre pré-rempli sans source serait inventé aux yeux du client).
  2. Un champ vidé par le client reste vide et s'imprime « non chiffré » — jamais un retour
     silencieux au défaut. On distingue « jamais saisi » (→ pré-remplissage) de « vidé » (→ null).
  3. Le régime de TVA est OBLIGATOIRE : sans lui le questionnaire n'est pas complet (c'est le
     champ qui décide si le bilan est HT ou TTC).
"""
from __future__ import annotations

import json

from sqlalchemy import text

# ── les 4 écrans : (titre, [ids de champ du registre]) ───────────────────────────────────────
ECRANS: list[tuple[str, tuple[str, ...]]] = [
    ("Votre projet", ("scenario_saisi", "logements_vises_saisi", "typologie_moyenne_saisi",
                      "part_sociale_saisi_pct", "stationnement_type_saisi")),
    ("Le foncier", ("prix_demande_saisi_eur", "prix_refuse_saisi_eur", "frais_acquisition_saisi_pct",
                    "commission_apporteur_saisi_eur", "bilan_demolition_eur", "bilan_depollution_eur")),
    ("Vos coûts", ("cout_construction_saisi_eur_m2", "honoraires_techniques_saisi_pct",
                   "vrd_saisi_eur_m2", "cout_place_stationnement_saisi_eur", "aleas_saisi_pct",
                   "taxe_amenagement_saisi_eur")),
    ("Vos conditions", ("prix_sortie_saisi_eur_m2", "prix_vente_bailleur_saisi_eur_m2",
                        "marge_visee_saisi_pct", "regime_tva_saisi", "duree_portage_saisi_mois",
                        "apport_saisi_eur", "taux_apport_saisi_pct")),
]

#: tous les ids de champ, dans l'ordre des écrans.
CHAMPS: tuple[str, ...] = tuple(cid for _, ids in ECRANS for cid in ids)

#: champ(s) obligatoire(s) — le régime de TVA décide de la vérité du bilan (règle 3).
OBLIGATOIRES: frozenset[str] = frozenset({"regime_tva_saisi"})

#: phrase d'explication + renvoi expert-comptable, servie sous le champ régime de TVA (règle 3).
TVA_EXPLICATION = (
    "Le régime de TVA décide si le bilan travaille HT ou TTC. À La Réunion la TVA sur le logement "
    "neuf est de 8,5 %. Le régime réel dépend du montage (TVA sur marge à l'acquisition, "
    "récupération sur les coûts, taux réduit en accession sociale) : à confirmer avec votre "
    "expert-comptable."
)

#: pré-remplissages À SOURCE CONSTANTE (règle 1 : jamais une valeur sans sa source).
_PREFILL_CONST: dict[str, tuple] = {
    "frais_acquisition_saisi_pct": (7, "usage standard : notaire et droits de mutation (7 à 8 %)"),
    "honoraires_techniques_saisi_pct": (12, "usage promoteur : maîtrise d'œuvre, BET, contrôle technique"),
    "aleas_saisi_pct": (4, "usage chantier : provision pour aléas (3 à 5 %)"),
    "marge_visee_saisi_pct": (9, "usage promoteur : marge cible sur le chiffre d'affaires"),
    "cout_construction_saisi_eur_m2": (
        2550, "médiane régionale 2021-2025, EPTB 2024 / dataset CDC (2 300 à 2 800 €/m²)"),
    "vrd_saisi_eur_m2": (90, "base VRD des hypothèses LABUSE, modulée par la viabilisation"),
    "duree_portage_saisi_mois": (29, "délai d'instruction médian (~9 mois) + 20 mois de chantier"),
}


DDL = """
CREATE TABLE IF NOT EXISTS questionnaire_financier (
  id serial PRIMARY KEY,
  compte_id int,
  idu varchar(20) NOT NULL,
  projet_id int,
  reponses jsonb NOT NULL DEFAULT '{}',
  complet boolean NOT NULL DEFAULT false,
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (compte_id, idu)
);
"""


def ensure(db) -> None:
    for stmt in DDL.split(";"):
        if stmt.strip():
            db.execute(text(stmt))


def prefill(fiche: dict | None) -> dict[str, dict]:
    """{id → {valeur, source}} des champs PRÉ-REMPLIS, chacun AVEC sa source (règle 1). Un champ
    sans source défendable n'est pas émis (prix demandé, démolition, dépollution, régime TVA…)."""
    f = fiche or {}
    out: dict[str, dict] = {fid: {"valeur": v, "source": s} for fid, (v, s) in _PREFILL_CONST.items()}
    pot = f.get("potentiel_transformation") or {}
    if pot:
        scen = "surelevation" if pot.get("surelevation_possible") else "reconstruction"
        out["scenario_saisi"] = {"valeur": scen, "source": "scénario dominant du potentiel LABUSE"}
        cap = pot.get("capacite_estimee")
        if cap:
            out["logements_vises_saisi"] = {"valeur": cap, "source": "fourchette de logements du potentiel LABUSE"}
    ta = f.get("taxe_amenagement") or {}
    if ta.get("total_eur"):
        out["taxe_amenagement_saisi_eur"] = {
            "valeur": round(float(ta["total_eur"])),
            "source": "calcul de la taxe d'aménagement (config datée, service-public.gouv.fr)"}
    return out


def resoudre(reponses: dict, prefill_map: dict) -> dict[str, dict]:
    """Pour chaque champ : {valeur, origine ∈ saisi|prefill|non_chiffre, source?}.
    Règle 2 : un champ présent dans `reponses` à null a été VIDÉ → non_chiffre (jamais le
    pré-remplissage) ; un champ absent de `reponses` prend le pré-remplissage s'il en a un."""
    out: dict[str, dict] = {}
    for fid in CHAMPS:
        if fid in reponses:
            v = reponses[fid]
            if v in (None, ""):
                out[fid] = {"valeur": None, "origine": "non_chiffre"}
            else:
                out[fid] = {"valeur": v, "origine": "saisi"}
        elif fid in prefill_map:
            out[fid] = {"valeur": prefill_map[fid]["valeur"], "origine": "prefill",
                        "source": prefill_map[fid]["source"]}
        else:
            out[fid] = {"valeur": None, "origine": "non_chiffre"}
    return out


def est_complet(reponses: dict) -> bool:
    """Règle 3 : complet ssi tous les champs obligatoires sont saisis non vides (régime de TVA)."""
    return all(reponses.get(fid) not in (None, "") for fid in OBLIGATOIRES)


def charger(db, idu: str, compte_id: int | None) -> dict:
    """Le questionnaire persisté pour (compte, idu), ou vide. Rend {reponses, complet, existe}."""
    ensure(db)
    row = db.execute(text(
        "SELECT reponses, complet FROM questionnaire_financier "
        "WHERE idu = :i AND compte_id IS NOT DISTINCT FROM :c"),
        {"i": idu, "c": compte_id}).mappings().first()
    if not row:
        return {"reponses": {}, "complet": False, "existe": False}
    rep = row["reponses"] if isinstance(row["reponses"], dict) else json.loads(row["reponses"] or "{}")
    return {"reponses": rep, "complet": bool(row["complet"]), "existe": True}


def enregistrer(db, idu: str, compte_id: int | None, reponses: dict, projet_id: int | None = None) -> dict:
    """UPSERT du questionnaire. `reponses` = {id_champ: valeur|null} — null = champ vidé (règle 2),
    stocké tel quel ; les champs inconnus du registre sont ignorés (garde). `complet` recalculé."""
    ensure(db)
    propres = {k: v for k, v in (reponses or {}).items() if k in CHAMPS}
    complet = est_complet(propres)
    db.execute(text(
        "INSERT INTO questionnaire_financier (compte_id, idu, projet_id, reponses, complet, updated_at) "
        "VALUES (:c, :i, :p, CAST(:r AS jsonb), :k, now()) "
        "ON CONFLICT (compte_id, idu) DO UPDATE SET reponses = EXCLUDED.reponses, "
        "complet = EXCLUDED.complet, projet_id = EXCLUDED.projet_id, updated_at = now()"),
        {"c": compte_id, "i": idu, "p": projet_id, "r": json.dumps(propres, ensure_ascii=False), "k": complet})
    return {"reponses": propres, "complet": complet, "existe": True}
