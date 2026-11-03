"""JOHN-TAYLOR-1 — le CARNET DE BORD, en base, lu au début de chaque conversation.

Le mandat : « Carnet de bord en base, lu au début de chaque conversation : décisions de Vic, incidents
passés avec cause et correction, doctrines (classes A/B, rien d'inventé). Une décision prise dans le
chat devient une ligne PROPOSÉE ; elle n'entre qu'après l'accord de Vic. »

Trois types de lignes (`type`) : `decision` (un choix de Vic), `incident` (un incident passé avec sa
cause et sa correction), `doctrine` (une règle permanente). Trois états (`statut`) :
  · `actif`   — la ligne fait foi (lue dans le contexte de chaque conversation) ;
  · `propose` — John l'a proposée depuis le chat ; elle ATTEND l'accord de Vic (pas encore dans le contexte) ;
  · `rejete`  — Vic l'a refusée (gardée pour mémoire, jamais relue dans le contexte).

Le carnet est SEMÉ au premier usage avec les décisions et doctrines déjà connues (idempotent par `cle`).
"""
from __future__ import annotations

from sqlalchemy import text

DDL = """
CREATE TABLE IF NOT EXISTS john_carnet (
  id       bigserial PRIMARY KEY,
  cle      varchar(80) UNIQUE,              -- clé stable (idempotence du seed + anti-doublon)
  type     varchar(16) NOT NULL,            -- decision | incident | doctrine
  titre    text NOT NULL,
  corps    text NOT NULL,
  statut   varchar(12) NOT NULL DEFAULT 'actif',  -- actif | propose | rejete
  par      varchar(120),                    -- qui a posé / proposé la ligne
  cree_at  timestamptz NOT NULL DEFAULT now(),
  valide_at timestamptz
)
"""

#: Les décisions et doctrines DÉJÀ connues (mémoire LABUSE), semées au premier usage. `actif` d'emblée
#: (ce sont des faits établis, pas des propositions). Clé stable → le seed est idempotent.
SEED: list[dict] = [
    # ——— Décisions de Vic ———
    {"cle": "dec-bdnb-retiree", "type": "decision", "titre": "BDNB retirée",
     "corps": "La BDNB est retirée : elle ne nourrit ni l'emprise ni la hauteur servies et la "
              "couverture 974 n'est pas confirmée. Son injection ne changerait aucun chiffre servi."},
    {"cle": "dec-priorite-masquee", "type": "decision", "titre": "« Priorité » masqué",
     "corps": "La colonne/tuile « Priorité » est masquée côté client (le tri se fait d'abord par la "
              "bande de qualité, pas par une probabilité de vente affichée)."},
    {"cle": "dec-noms-non-masques", "type": "decision", "titre": "Noms de particuliers non masqués avant le premier client",
     "corps": "Les patronymes (successions/indivisions) ne sont PAS masqués tant qu'il n'y a pas de "
              "premier client payant. Décision assumée, à rouvrir avant mise en marché."},
    {"cle": "dec-7j-grace", "type": "decision", "titre": "7 jours de grâce au paiement",
     "corps": "Un paiement refusé laisse 7 jours de grâce (bandeau) PUIS lecture seule (402 en écriture) ; "
              "le login reste possible."},
    {"cle": "dec-calcul-nuit-serveur", "type": "decision", "titre": "Le calcul de nuit tourne sur le serveur",
     "corps": "Le calcul de nuit tourne sur le SERVEUR (plus sur le Mac), dans la fenêtre 01h–05h "
              "Réunion, sous nice/ionice et plafond mémoire."},
    {"cle": "dec-q_v21-sous-oeil", "type": "decision", "titre": "Première promotion de q_v21 sous les yeux de Vic",
     "corps": "La toute PREMIÈRE mise en service (promotion) de q_v21 se fait sous l'œil de Vic "
              "(gate LABUSE_CALCUL_NUIT_PROMEUT=0 la 1ʳᵉ nuit : calcule + contrôle + mail, pas de bascule)."},
    # ——— Doctrines ———
    {"cle": "doc-classes-ab", "type": "doctrine", "titre": "Classes de sources A / B",
     "corps": "A = référence à faible risque : s'injecte seule la nuit avec contrôles + retour arrière. "
              "B = structurant (scoring/cascade/zonage/marché/propriété) : attend le clic de Vic. Le "
              "DÉFAUT est B (dans le doute, un humain décide)."},
    {"cle": "doc-rien-invente", "type": "doctrine", "titre": "Rien d'inventé",
     "corps": "Aucune affirmation sans donnée. Chaque affirmation cite la donnée d'où elle vient ; en "
              "cas de doute, John dit « je ne sais pas ». Même verrou que le Copilote."},
    {"cle": "doc-sur-proteger", "type": "doctrine", "titre": "Sur-protéger est bénin, sous-protéger est le bug",
     "corps": "Un contrôle qui ne peut pas conclure est un ÉCHEC : on ne promeut pas, on n'injecte pas. "
              "Jamais un vert par vacuité."},
    {"cle": "doc-liste-fermee", "type": "doctrine", "titre": "John agit dans une liste fermée, sur ordre de Vic",
     "corps": "John n'agit JAMAIS de sa propre initiative. Liste fermée : injecter une source (A/B), "
              "relancer un job, lancer une sauvegarde, accepter un écart/incident, promouvoir un run aux "
              "contrôles verts, retirer une source. Promouvoir un run et retirer une source demandent "
              "d'abord « tu confirmes ? ». Hors liste, John refuse et explique."},
]


def ensure(db) -> None:
    db.execute(text(DDL))


def semer(db) -> int:
    """Sème les lignes connues (idempotent par `cle`). Retourne le nombre de lignes neuves."""
    ensure(db)
    neuves = 0
    for e in SEED:
        r = db.execute(text(
            "INSERT INTO john_carnet (cle, type, titre, corps, statut, par, valide_at) "
            "VALUES (:cle, :t, :ti, :co, 'actif', 'mémoire', now()) "
            "ON CONFLICT (cle) DO NOTHING"),
            {"cle": e["cle"], "t": e["type"], "ti": e["titre"], "co": e["corps"]})
        neuves += r.rowcount or 0
    return neuves


def lignes_actives(db) -> list[dict]:
    """Les lignes `actif` — CE QUE JOHN LIT au début de chaque conversation (le contexte du carnet)."""
    ensure(db)
    rows = db.execute(text(
        "SELECT cle, type, titre, corps, par, cree_at FROM john_carnet "
        "WHERE statut = 'actif' ORDER BY type, cree_at")).mappings().all()
    return [{"cle": r["cle"], "type": r["type"], "titre": r["titre"], "corps": r["corps"],
             "par": r["par"], "cree_at": r["cree_at"].isoformat()} for r in rows]


def proposees(db) -> list[dict]:
    """Les lignes `propose` — en attente de l'accord de Vic (affichées à part dans l'onglet)."""
    ensure(db)
    rows = db.execute(text(
        "SELECT id, cle, type, titre, corps, par, cree_at FROM john_carnet "
        "WHERE statut = 'propose' ORDER BY cree_at DESC")).mappings().all()
    return [{"id": r["id"], "cle": r["cle"], "type": r["type"], "titre": r["titre"],
             "corps": r["corps"], "par": r["par"], "cree_at": r["cree_at"].isoformat()} for r in rows]


def proposer(db, *, type: str, titre: str, corps: str, par: str, cle: str | None = None) -> int:
    """John PROPOSE une ligne depuis le chat : elle entre en `propose` (PAS dans le contexte tant que
    Vic n'a pas validé). Retourne l'id. `type` est borné aux trois valeurs connues (sinon `decision`)."""
    ensure(db)
    t = type if type in ("decision", "incident", "doctrine") else "decision"
    row = db.execute(text(
        "INSERT INTO john_carnet (cle, type, titre, corps, statut, par) "
        "VALUES (:cle, :t, :ti, :co, 'propose', :par) RETURNING id"),
        {"cle": cle, "t": t, "ti": titre, "co": corps, "par": par[:120]}).scalar()
    return int(row)


def valider(db, ligne_id: int) -> bool:
    """Vic accepte une ligne proposée → elle devient `actif` (lue dès la prochaine conversation)."""
    ensure(db)
    n = db.execute(text(
        "UPDATE john_carnet SET statut = 'actif', valide_at = now() "
        "WHERE id = :i AND statut = 'propose'"), {"i": ligne_id}).rowcount
    return bool(n)


def rejeter(db, ligne_id: int) -> bool:
    """Vic refuse une ligne proposée → `rejete` (gardée pour mémoire, jamais relue dans le contexte)."""
    ensure(db)
    n = db.execute(text(
        "UPDATE john_carnet SET statut = 'rejete' WHERE id = :i AND statut = 'propose'"),
        {"i": ligne_id}).rowcount
    return bool(n)


def noter_incident(db, *, cle: str, titre: str, cause: str, correction: str) -> None:
    """Ajoute (ou met à jour) un incident passé au carnet, `actif` (fait établi). Idempotent par `cle`."""
    ensure(db)
    corps = f"Cause : {cause}\nCorrection : {correction}"
    db.execute(text(
        "INSERT INTO john_carnet (cle, type, titre, corps, statut, par, valide_at) "
        "VALUES (:cle, 'incident', :ti, :co, 'actif', 'john', now()) "
        "ON CONFLICT (cle) DO UPDATE SET titre = EXCLUDED.titre, corps = EXCLUDED.corps"),
        {"cle": cle, "ti": titre, "co": corps})
