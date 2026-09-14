"""SOURCES-1 lot 5 — coût de construction : la constante d'engine.py devient une ligne SOURCÉE.

État réel mesuré 07/09/2026 :
· L'EPTB (SDES) publie bien La Réunion — « Les prix du terrain et du bâti pour les maisons
  individuelles de La Réunion en 2024 » (dreal.statistiques.developpement-durable.gouv.fr,
  lu) : coût moyen de construction d'une MAISON INDIVIDUELLE 145 500 € pour 96 m² (−4 % sur
  un an) ≈ 1 516 €/m² habitable. C'est la référence OBSERVÉE du segment maison individuelle
  (CCMI/autoconstruction) — PAS le coût de revient d'une opération de PROMOTION en SDP.
· Le « jeu CDC » du mandat est INTROUVABLE (aucun jeu data.gouv/SDES identifiable — dit au
  compte-rendu). Le jeu data.gouv « Prix des Terrains à batir en France » (2020) ne couvre
  pas les DOM (vérifié : régions métropole seules).

La fourchette promotion 2 300–2 800 €/m² SDP reste donc un CHOIX LABUSE — mais elle sort du
code : table `cout_construction_ref`, lignes datées et sourcées (le choix servi + la
référence EPTB en contexte), lue par `Hypotheses.charger` avec REPLI sur les anciennes
constantes si la table est vide (jamais un bilan cassé). Fiche de règle :
regles/cout_construction_ref.py.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

SOURCE_NAME = "Coût de construction (EPTB SDES + choix LABUSE)"
MILLESIME = "EPTB 2024 Réunion (SDES, publication annuelle) ; choix promotion 2026"

DDL = """
CREATE TABLE IF NOT EXISTS cout_construction_ref (
    id          varchar(32) PRIMARY KEY,
    segment     varchar(48)  NOT NULL,
    cout_bas_eur_m2  numeric(8,0),
    cout_haut_eur_m2 numeric(8,0),
    unite       varchar(24)  NOT NULL,
    source      text         NOT NULL,
    millesime   varchar(64)  NOT NULL,
    servi       boolean      NOT NULL DEFAULT false,
    note        text,
    maj_at      timestamptz  NOT NULL DEFAULT now()
)
"""

#: lignes de référence — seedées par l'ingestion (idempotent, upsert par id)
LIGNES = [
    dict(id="labuse_promotion", segment="promotion collective (SDP)",
         bas=2300, haut=2800, unite="€/m² SDP", servi=True,
         source="Choix LABUSE (ex-constante faisabilite/engine.py, M-Q P1-16) — coûts de "
                "revient promoteurs non publiés, référence attendue : conventions/appels "
                "d'offres locaux",
         millesime="choix 2026 — inchangé depuis M-Q",
         note="SERVIE par Hypotheses.charger (bornes basse/haute du bilan promoteur)"),
    dict(id="eptb_2024_maison", segment="maison individuelle — bâti (habitable)",
         bas=1516, haut=1516, unite="€/m² habitable", servi=False,
         source="EPTB (SDES) — « Les prix du terrain et du bâti pour les maisons "
                "individuelles de La Réunion en 2024 » : coût moyen du bâti hors terrain "
                "145 500 € pour 96 m² moyens → ≈ 1 516 €/m² (calcul LABUSE dit)",
         millesime="EPTB 2024 (publication SDES 2026)",
         note="CONTEXTE (segment maison individuelle ≠ promotion) — jamais servie au bilan ; "
              "coût total d'une opération AVEC achat de terrain = 281 700 € "
              "(117 100 € terrain + 164 600 € bâti) ; 1 430 projets, 32 % avec achat de terrain"),
    # SOURCES-5 #11 — la publication EPTB Réunion COMPLÈTE : au-delà du seul coût du bâti, le PRIX
    # DU TERRAIN à bâtir (source dreal.statistiques…/eptb/2024/la_reunion). Contexte (jamais servi).
    dict(id="eptb_2024_terrain", segment="terrain à bâtir (maison individuelle)",
         bas=244, haut=244, unite="€/m² terrain", servi=False,
         source="EPTB (SDES) — publication Réunion 2024 : prix moyen d'achat du terrain "
                "117 100 € (métropole 94 500 €), soit 244 €/m² de terrain",
         millesime="EPTB 2024 (publication SDES 2026)",
         note="CONTEXTE — prix du terrain à bâtir : +2 % sur un an, +22 % depuis 2019 ; "
              "jamais servi au bilan (référence de marché, distincte du choix promotion)"),
]


def ensure_tables(engine) -> None:
    with engine.begin() as cx:
        cx.execute(text(DDL))


def ingest_cout_construction(session: Session, log=print) -> dict:
    """Seed/upsert des lignes de référence. Rend {"n", "servie"}."""
    for l in LIGNES:
        session.execute(text(
            "INSERT INTO cout_construction_ref (id, segment, cout_bas_eur_m2, cout_haut_eur_m2, "
            " unite, source, millesime, servi, note, maj_at) "
            "VALUES (:id, :segment, :bas, :haut, :unite, :source, :millesime, :servi, :note, now()) "
            "ON CONFLICT (id) DO UPDATE SET segment = :segment, cout_bas_eur_m2 = :bas, "
            " cout_haut_eur_m2 = :haut, unite = :unite, source = :source, millesime = :millesime, "
            " servi = :servi, note = :note, maj_at = now()"), l)
    session.flush()
    servie = session.execute(text(
        "SELECT cout_bas_eur_m2 || '-' || cout_haut_eur_m2 FROM cout_construction_ref "
        "WHERE servi")).scalar()
    log(f"  coût construction : {len(LIGNES)} lignes de référence, servie = {servie} €/m² SDP")
    return {"n": len(LIGNES), "servie": servie}


def couts_servis(session: Session) -> tuple[float, float, str] | None:
    """(bas, haut, millesime) de la ligne SERVIE — None si table absente/vide (l'appelant
    replie sur les constantes d'engine.py, jamais un bilan cassé)."""
    try:
        row = session.execute(text(
            "SELECT cout_bas_eur_m2, cout_haut_eur_m2, millesime FROM cout_construction_ref "
            "WHERE servi LIMIT 1")).first()
    except Exception:  # noqa: BLE001 — table absente = source non ingérée
        session.rollback()
        return None
    if row is None or row[0] is None or row[1] is None:
        return None
    return float(row[0]), float(row[1]), row[2]
