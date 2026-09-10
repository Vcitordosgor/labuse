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
# RECETTE-2 (S3, décision Vic) — on ne garde QUE les questions dont la réponse change le
# document. QUATRE champs RETIRÉS car leur valeur n'apparaît nulle part dans le bilan : le TYPE de
# stationnement (le bilan chiffre un coût par place, jamais le type), le « prix déjà refusé »
# (purement informatif), la « commission d'apporteur » (aucun poste du bilan ne la porte), et
# l'« apport » (le document renvoie explicitement le plan de financement à l'établissement prêteur).
ECRANS: list[tuple[str, tuple[str, ...]]] = [
    # RECETTE-10 T2b (recette) — `scenario_saisi` RETIRÉ de la saisie ET du document : le bilan chiffre
    # TOUJOURS une reconstruction (W3), le champ ne changeait rien et n'était jamais rempli. Plus une
    # question, plus une ligne imprimée (avant : masqué au front mais toujours servi à l'étape 1 et
    # imprimé au PDF — un demi-retrait, corrigé ici en retrait franc).
    ("Votre projet", ("logements_vises_saisi", "typologie_moyenne_saisi",
                      "part_sociale_saisi_pct")),
    ("Le foncier", ("prix_demande_saisi_eur", "frais_acquisition_saisi_pct",
                    "bilan_demolition_eur", "bilan_depollution_eur")),
    ("Vos coûts", ("cout_construction_saisi_eur_m2", "honoraires_techniques_saisi_pct",
                   "vrd_saisi_eur_m2", "cout_place_stationnement_saisi_eur", "aleas_saisi_pct",
                   "taxe_amenagement_saisi_eur")),
    ("Vos conditions", ("prix_sortie_saisi_eur_m2", "prix_vente_bailleur_saisi_eur_m2",
                        "marge_visee_saisi_pct", "regime_tva_saisi", "duree_portage_saisi_mois",
                        "taux_apport_saisi_pct")),
]

# RECETTE-6 (E5) — ÉCRAN 0 « Que voulez-vous chiffrer ? ». Le bilan à rebours (construction neuve)
# reste le SEUL moteur ; les autres usages n'ouvrent QUE ce qui se calcule déjà proprement. Un parcours
# qu'on ne sait pas servir honnêtement apparaît GRISÉ avec sa raison — jamais un formulaire qui rend un
# bilan faux. Le questionnaire des ECRANS ci-dessus EST le parcours « construction ».
# RECETTE-8 W13bis (C3) — l'écran du parcours « Revente en l'état » : pas de bilan à rebours, un
# calcul SIMPLE et direct (achat → frais → travaux → portage → revente ⇒ marge, taux de marge).
REVENTE_ECRANS: list[tuple[str, tuple[str, ...]]] = [
    ("La revente en l'état", ("prix_achat_revente_saisi_eur", "frais_acquisition_saisi_pct",
                              "travaux_revente_saisi_eur", "duree_portage_saisi_mois",
                              "taux_apport_saisi_pct", "prix_revente_saisi_eur")),
]

USAGES: list[dict] = [
    {"key": "construction", "label": "Construction neuve", "servi": True,
     "sous": "Le bilan à rebours : ce que l'opération peut supporter comme charge foncière."},
    # RECETTE-8 W13bis (C3) — le parcours « Revente en l'état » est désormais SERVI (calcul simple
    # marge/taux de marge ; pas de bilan à rebours, pas de moteur lourd).
    {"key": "revente", "label": "Revente en l'état", "servi": True,
     "sous": "Le calcul de marge : prix d'achat, frais, travaux, portage → prix de revente ⇒ marge."},
    {"key": "division", "label": "Division parcellaire", "servi": False,
     "raison": "Le découpage en lots et la valorisation lot par lot ne sont pas encore servis proprement."},
    {"key": "renovation", "label": "Rénovation-revente", "servi": False,
     "raison": "Le chiffrage travaux + revente demande un poste travaux dédié, pas encore servi."},
    {"key": "portage", "label": "Portage locatif", "servi": False,
     "raison": "Le rendement locatif (loyers, charges, fiscalité de détention) n'est pas encore servi."},
]

# RECETTE-2 (S3) — LIBELLÉS CLIENT du questionnaire, en français clair (les libellés du registre
# portent des suffixes de traçabilité « (saisi) / (bilan) / (saisi, %) » — jargon interne à ne
# jamais montrer au porteur). L'unité est ajoutée par le front (« (€/m²) »…) : le libellé ne la
# répète pas. Un id absent de cette carte retombe sur le libellé registre (garde).
LIBELLES_CLIENT: dict[str, str] = {
    "scenario_saisi": "Scénario du projet",
    "logements_vises_saisi": "Nombre de logements visés",
    "typologie_moyenne_saisi": "Typologie moyenne (T2, T3…)",
    "part_sociale_saisi_pct": "Part de logement social ou intermédiaire",
    "prix_demande_saisi_eur": "Prix demandé pour le terrain",
    "frais_acquisition_saisi_pct": "Frais d'acquisition (notaire, droits)",
    "bilan_demolition_eur": "Coût de démolition",
    "bilan_depollution_eur": "Dépollution et étude de sol",
    "cout_construction_saisi_eur_m2": "Coût de construction",
    "honoraires_techniques_saisi_pct": "Honoraires techniques (architecte, bureaux d'études)",
    "vrd_saisi_eur_m2": "VRD et raccordements",
    "cout_place_stationnement_saisi_eur": "Coût par place de stationnement",
    "aleas_saisi_pct": "Provision pour aléas",
    "taxe_amenagement_saisi_eur": "Taxe d'aménagement",
    "prix_sortie_saisi_eur_m2": "Prix de vente prévu des logements",
    "prix_vente_bailleur_saisi_eur_m2": "Prix de vente au bailleur social",
    "marge_visee_saisi_pct": "Marge visée",
    "regime_tva_saisi": "Régime de TVA",
    "duree_portage_saisi_mois": "Durée de portage",
    "taux_apport_saisi_pct": "Taux d'emprunt",
    # RECETTE-8 W13bis (C3) — parcours revente
    "prix_achat_revente_saisi_eur": "Prix d'achat du bien",
    "travaux_revente_saisi_eur": "Travaux éventuels avant revente",
    "prix_revente_saisi_eur": "Prix de revente visé",
}

#: tous les ids de champ, dans l'ordre des écrans (construction + revente, sans doublon).
CHAMPS: tuple[str, ...] = tuple(dict.fromkeys(
    cid for _, ids in (ECRANS + REVENTE_ECRANS) for cid in ids))

# RECETTE-10 T2b — LE TRI DES QUESTIONS (décision de recette). Deux verdicts actifs :
#   • garder    — le porteur DOIT (obligatoire) ou VEUT la toucher : elle pilote le résultat.
#   • affiner   — pré-remplie d'une valeur sourcée d'usage ; ne bouge le bilan qu'à la marge →
#                 repliée derrière « Affiner les hypothèses » (fermé par défaut), plus les 4 écrans.
#   (« supprimer » n'est plus un état de champ servi : le seul candidat, `scenario_saisi`, a été
#    RETIRÉ franchement des écrans ET du document — voir ECRANS et exports/blocs/financier._HYP_CLES.
#    Le front ignore par prudence tout `tri === 'supprimer'` résiduel.)
TRI: dict[str, str] = {
    "logements_vises_saisi": "garder", "typologie_moyenne_saisi": "garder",
    "prix_demande_saisi_eur": "garder", "cout_construction_saisi_eur_m2": "garder",
    "prix_sortie_saisi_eur_m2": "garder", "prix_vente_bailleur_saisi_eur_m2": "affiner",
    "marge_visee_saisi_pct": "garder", "regime_tva_saisi": "garder",
    "part_sociale_saisi_pct": "affiner", "frais_acquisition_saisi_pct": "affiner",
    "bilan_demolition_eur": "affiner", "bilan_depollution_eur": "affiner",
    "honoraires_techniques_saisi_pct": "affiner", "vrd_saisi_eur_m2": "affiner",
    "cout_place_stationnement_saisi_eur": "affiner", "aleas_saisi_pct": "affiner",
    "taxe_amenagement_saisi_eur": "affiner", "duree_portage_saisi_mois": "affiner",
    "taux_apport_saisi_pct": "affiner",
    # revente
    "prix_achat_revente_saisi_eur": "garder", "prix_revente_saisi_eur": "garder",
    "travaux_revente_saisi_eur": "affiner",
}


def tri_champ(fid: str) -> str:
    """Verdict de tri d'un champ (« garder »/« affiner »/« supprimer »). Défaut prudent : « affiner »."""
    return TRI.get(fid, "affiner")

#: RECETTE-5 (V19, décision Vic) — les champs INDISPENSABLES AU CALCUL de la charge foncière : sans
#: eux, `charge` est None et le bilan ne peut pas être établi. Ils bloquent la génération tant qu'ils
#: sont vides (les autres champs ont un pré-remplissage sourcé ou sont facultatifs). Deux champs :
#:   • prix_sortie_saisi_eur_m2 — le prix de vente prévu (pas de pré-remplissage : personne ne peut
#:     le deviner à la place du porteur) ; c'est le chiffre d'affaires du bilan à rebours ;
#:   • regime_tva_saisi — décide si le bilan est HT ou TTC (règle 3).
#: (Le PROGRAMME constructible — surface vendable — est aussi indispensable mais vient du POTENTIEL de
#: la parcelle, pas du questionnaire ; son absence est signalée à part par `manques`.)
OBLIGATOIRES: frozenset[str] = frozenset({"prix_sortie_saisi_eur_m2", "regime_tva_saisi"})

#: RECETTE-5 (V19) — l'AIDE de chaque champ (le « i ») : ce qu'on attend comme valeur. Servie au front.
AIDES: dict[str, str] = {
    "scenario_saisi": "Reconstruction ou surélévation — le scénario dominant du potentiel LABUSE est pré-rempli.",
    "logements_vises_saisi": "Un nombre entier de logements que vous visez (ex. 8).",
    "typologie_moyenne_saisi": "La typologie moyenne du programme : T2, T3, T4… (sert à estimer la surface vendable si le potentiel ne la donne pas).",
    "part_sociale_saisi_pct": "Un pourcentage (0 à 100) — la part de logement social ou intermédiaire du programme.",
    "prix_demande_saisi_eur": "Un montant en euros — le prix demandé pour le terrain (sert à confronter la charge foncière supportable ; laissez vide si vous ne l'avez pas).",
    "frais_acquisition_saisi_pct": "Un pourcentage — notaire et droits de mutation (usage 7 à 8 %). Pré-rempli à 7 %.",
    "bilan_demolition_eur": "Un montant en euros — coût de démolition de l'existant (0 sur un terrain nu).",
    "bilan_depollution_eur": "Un montant en euros — dépollution et étude de sol si le terrain le requiert.",
    "cout_construction_saisi_eur_m2": "Un coût en €/m² de plancher (usage 2 300 à 2 800 à La Réunion). Pré-rempli à la médiane régionale.",
    "honoraires_techniques_saisi_pct": "Un pourcentage du coût travaux (architecte, BET, contrôle — usage ~12 %). Pré-rempli.",
    "vrd_saisi_eur_m2": "Un coût en €/m² — voirie et réseaux divers. Pré-rempli.",
    "cout_place_stationnement_saisi_eur": "Un montant en euros par place de stationnement.",
    "aleas_saisi_pct": "Un pourcentage — provision pour aléas de chantier (usage 3 à 5 %). Pré-rempli à 4 %.",
    "taxe_amenagement_saisi_eur": "Un montant en euros — la taxe d'aménagement. Pré-remplie depuis le calcul LABUSE si disponible.",
    "prix_sortie_saisi_eur_m2": "INDISPENSABLE — le prix de vente prévu des logements, en €/m² habitable. Sans lui, la charge foncière ne peut pas être calculée.",
    "prix_vente_bailleur_saisi_eur_m2": "Un prix en €/m² — la vente au bailleur social (utile si le programme porte une part sociale).",
    "marge_visee_saisi_pct": "Un pourcentage du chiffre d'affaires (marge cible promoteur, usage ~9 %). Pré-rempli.",
    "regime_tva_saisi": "INDISPENSABLE — le régime de TVA (assujetti avec récupération / TVA sur marge / autre). Il décide si le bilan travaille HT ou TTC.",
    "duree_portage_saisi_mois": "Une durée en mois (instruction + chantier). Pré-remplie à 29 mois.",
    "taux_apport_saisi_pct": "Un taux en pourcentage — le taux d'emprunt du portage.",
    # RECETTE-8 W13bis (C3) — parcours revente
    "prix_achat_revente_saisi_eur": "INDISPENSABLE — le prix d'achat du bien, en euros. Sans lui, la marge ne peut pas être calculée.",
    "travaux_revente_saisi_eur": "Un montant en euros — travaux éventuels avant la revente (0 si aucun).",
    "prix_revente_saisi_eur": "INDISPENSABLE — le prix de revente visé, en euros. Sans lui, la marge ne peut pas être calculée.",
}


def programme_depuis_potentiel(pot: dict | None) -> bool:
    """RECETTE-9 T1 — le potentiel de la parcelle chiffre-t-il SEUL le programme constructible ?
    Vrai si `capacite_estimee` signale une capacité (parcelle en sous-densité) : `_financier_contexte`
    pré-remplit alors le programme et le bilan s'établit SANS que le porteur décrive quoi que ce soit.
    Faux (parcelle à sa densité, potentiel nul/faible) : la surface vendable n'existe que si le porteur
    saisit un nombre de logements — qui devient dès lors INDISPENSABLE (défaut n°1/n°2 de la recette :
    le champ qui débloque « Programme constructible » n'était pas marqué et le blocage tombait « à
    l'arrivée » du document au lieu d'au moment de la saisie)."""
    return bool((pot or {}).get("capacite_estimee"))


def obligatoires_programme(pot: dict | None) -> set[str]:
    """Les champs du questionnaire construction que le potentiel absent rend INDISPENSABLES."""
    return set() if programme_depuis_potentiel(pot) else {"logements_vises_saisi"}


def manques(resolved: dict, program: dict) -> list[dict]:
    """RECETTE-5 (V18/V19) — la liste des éléments INDISPENSABLES qui manquent pour ÉTABLIR le bilan
    (charge foncière). Vide ⇒ le document Financier peut se générer. Deux familles :
      • le PROGRAMME constructible (surface vendable) — vient du potentiel de la parcelle ou, à défaut,
        de « logements visés × typologie » ; s'il reste nul, aucun bilan n'est chiffrable ;
      • les CHAMPS OBLIGATOIRES du questionnaire (prix de sortie, régime de TVA).
    `program` est le programme FINAL (après le repli logements × typologie du builder)."""
    out: list[dict] = []
    if not program.get("surface_vendable"):
        out.append({"champ": None, "libelle": "Programme constructible",
                    "raison": "cette parcelle n'a pas de surface vendable chiffrable — renseignez un nombre de logements visés et une typologie, ou vérifiez le potentiel de la parcelle."})
    for fid in ("prix_sortie_saisi_eur_m2", "regime_tva_saisi"):
        if (resolved.get(fid) or {}).get("valeur") in (None, ""):
            out.append({"champ": fid, "libelle": LIBELLES_CLIENT.get(fid, fid),
                        "raison": "indispensable au calcul de la charge foncière."})
    return out


#: RECETTE-8 W13bis (C3) — les champs indispensables au calcul de MARGE (revente en l'état).
OBLIGATOIRES_REVENTE: frozenset[str] = frozenset(
    {"prix_achat_revente_saisi_eur", "prix_revente_saisi_eur"})


def manques_revente(resolved: dict) -> list[dict]:
    """Les éléments INDISPENSABLES au calcul de la marge de revente (prix d'achat, prix de revente).
    Vide ⇒ le Financier « revente » peut se générer. Pas de programme constructible ici (revente en
    l'état : ni construction, ni SDP)."""
    out: list[dict] = []
    for fid in OBLIGATOIRES_REVENTE:
        if (resolved.get(fid) or {}).get("valeur") in (None, ""):
            out.append({"champ": fid, "libelle": LIBELLES_CLIENT.get(fid, fid),
                        "raison": "indispensable au calcul de la marge de revente."})
    return out

#: phrase d'explication + renvoi expert-comptable, servie sous le champ régime de TVA (règle 3).
TVA_EXPLICATION = (
    "Le régime de TVA décide si le bilan travaille HT ou TTC. À La Réunion la TVA sur le logement "
    "neuf est de 8,5 %. Le régime réel dépend du montage (TVA sur marge à l'acquisition, "
    "récupération sur les coûts, taux réduit en accession sociale) : à confirmer avec votre "
    "expert-comptable."
)

def _cout_construction_median() -> int:
    """Défaut de coût de construction DÉRIVÉ de la source unique (`hypotheses_faisabilite` du YAML
    — mandat hypothèses bilan, décision Vic 28/07/2026) : milieu de la fourchette auditée. Plus
    jamais une constante autonome ici (un coût dupliqué = re-création du bug 2100)."""
    from .faisabilite.engine import Hypotheses
    h = Hypotheses.charger()
    return round((h.cout_construction_m2_bas + h.cout_construction_m2_haut) / 2)


#: pré-remplissages À SOURCE CONSTANTE (règle 1 : jamais une valeur sans sa source).
_PREFILL_CONST: dict[str, tuple] = {
    "frais_acquisition_saisi_pct": (7, "usage standard : notaire et droits de mutation (7 à 8 %)"),
    "honoraires_techniques_saisi_pct": (12, "usage promoteur : maîtrise d'œuvre, BET, contrôle technique"),
    "aleas_saisi_pct": (4, "usage chantier : provision pour aléas (3 à 5 %)"),
    "marge_visee_saisi_pct": (9, "usage promoteur : marge cible sur le chiffre d'affaires"),
    "cout_construction_saisi_eur_m2": (
        _cout_construction_median(),
        "médiane régionale 2021-2025, EPTB 2024 / dataset CDC (2 300 à 2 800 €/m²)"),
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
        # RECETTE-8 W3 — le bilan du Financier chiffre TOUJOURS une reconstruction (SDP créée en table
        # rase). RECETTE-10 T2b — le champ « scénario » n'est donc plus ni saisi ni pré-rempli ni
        # imprimé (il ne changeait rien) ; seul le nombre de logements est pré-rempli depuis le potentiel.
        cap = pot.get("capacite_estimee")
        if cap:
            out["logements_vises_saisi"] = {"valeur": cap, "source": "fourchette de logements du potentiel LABUSE"}
    # RECETTE-8 W2 — la taxe d'aménagement n'est plus pré-remplie depuis la fiche (elle n'y porte
    # plus aucun montant : pas de projet, pas de taxe). Elle est pré-calculée AU FINANCIER, sur la
    # SDP du projet réellement retenu (`exports.builder._financier_contexte`), où le programme est
    # connu — jamais sur un scénario de fiche que personne n'a choisi.
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


def usage_choisi(reponses: dict) -> str:
    """RECETTE-8 W13bis — le parcours choisi (méta-clé `_usage`), « construction » par défaut."""
    u = (reponses or {}).get("_usage")
    return u if u in ("construction", "revente") else "construction"


def est_complet(reponses: dict) -> bool:
    """Règle 3 : complet ssi tous les champs obligatoires du PARCOURS choisi sont saisis non vides.
    Construction : prix de sortie + régime de TVA. Revente (W13bis) : prix d'achat + prix de revente."""
    obligs = OBLIGATOIRES_REVENTE if usage_choisi(reponses) == "revente" else OBLIGATOIRES
    return all(reponses.get(fid) not in (None, "") for fid in obligs)


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
    # RECETTE-8 W13bis — on garde les CHAMPS + la méta-clé `_usage` (le parcours choisi), jamais
    # d'autre clé étrangère (garde). Le parcours pilote quels champs sont obligatoires (est_complet).
    propres = {k: v for k, v in (reponses or {}).items() if k in CHAMPS or k == "_usage"}
    complet = est_complet(propres)
    db.execute(text(
        "INSERT INTO questionnaire_financier (compte_id, idu, projet_id, reponses, complet, updated_at) "
        "VALUES (:c, :i, :p, CAST(:r AS jsonb), :k, now()) "
        "ON CONFLICT (compte_id, idu) DO UPDATE SET reponses = EXCLUDED.reponses, "
        "complet = EXCLUDED.complet, projet_id = EXCLUDED.projet_id, updated_at = now()"),
        {"c": compte_id, "i": idu, "p": projet_id, "r": json.dumps(propres, ensure_ascii=False), "k": complet})
    return {"reponses": propres, "complet": complet, "existe": True}
