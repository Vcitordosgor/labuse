"""M55-D stage 6 — SIGNAUX DE VIE : pré-calcul des signaux lourds (parcel_signaux_vie).

Trois des huit signaux filtrables exigeraient une jointure lourde à CHAQUE appel /filtre
(mesure phase 1) — ils sont donc PRÉ-CALCULÉS ici, au build, en table plate interrogée par
un EXISTS indexé :
  · permis_actif   — PC accordé < 3 ans, non repéré caduc (parse JSON Sitadel `idu_codes`) ;
  · friche         — parcelle intersectant une friche Cartofriches (jointure spatiale) ;
  · assemblage_pm  — propriétaire société PRIVÉE (groupe MAJIC 0) détenant ≥ 3 parcelles.

Les cinq autres (procédure collective, permis caduc, sortie de défisc, nu-société, cession
de fonds) restent des EXISTS légers calculés en direct dans /filtre (tables minuscules ou
indexées). AUCUN lien avec le scoring : signaux d'ÉVÉNEMENTS sourcés, pas des jugements.

Idempotent : chaque signal est reconstruit par DELETE + INSERT dans la même transaction —
rejouer le build ne change rien (test tests/test_signaux_vie.py). ⚠ nommage : la table
`parcel_signals` (offre C, scoring) est UNE AUTRE table — ne pas confondre.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

#: signaux pré-calculés (la LISTE FERMÉE de cette table — le reste vit en direct dans /filtre)
SIGNAUX_PRECALCULES = ("permis_actif", "friche", "assemblage_pm")

#: seuil « assemblage » VALIDÉ Vic (phase 1) : société privée détenant ≥ 3 parcelles
ASSEMBLAGE_MIN_PARCELLES = 3

#: fenêtre « permis actif » : PC accordé depuis moins de 3 ans (au moment du build)
PERMIS_ACTIF_ANNEES = 3


def ensure_table(session: Session) -> None:
    session.execute(text(
        """CREATE TABLE IF NOT EXISTS parcel_signaux_vie (
             idu varchar(14) NOT NULL,
             signal varchar(24) NOT NULL,
             updated_at timestamptz NOT NULL DEFAULT now(),
             PRIMARY KEY (idu, signal))"""))
    session.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_signaux_vie_signal ON parcel_signaux_vie (signal, idu)"))


def build_signaux_vie(session: Session) -> dict[str, int]:
    """(Re)construit les trois signaux pré-calculés. Renvoie {signal: n}."""
    ensure_table(session)
    counts: dict[str, int] = {}

    # ── permis_actif : PC < 3 ans (Sitadel), rattachement idu déclaré au permis, hors caducs ──
    session.execute(text("DELETE FROM parcel_signaux_vie WHERE signal = 'permis_actif'"))
    counts["permis_actif"] = session.execute(text(
        """INSERT INTO parcel_signaux_vie (idu, signal)
           SELECT DISTINCT pc.idu, 'permis_actif'
           FROM (SELECT jsonb_array_elements_text(idu_codes::jsonb) AS idu
                 FROM sitadel_permits
                 WHERE type = 'PC' AND idu_codes IS NOT NULL
                   AND date >= now() - make_interval(years => :annees)) pc
           JOIN parcels p ON p.idu = pc.idu
           WHERE NOT EXISTS (SELECT 1 FROM pc_caducs c WHERE c.idu = pc.idu)
           ON CONFLICT DO NOTHING"""), {"annees": PERMIS_ACTIF_ANNEES}).rowcount

    # ── friche : intersection Cartofriches (spatial, GiST) — le POURQUOI du pré-calcul ──
    session.execute(text("DELETE FROM parcel_signaux_vie WHERE signal = 'friche'"))
    counts["friche"] = session.execute(text(
        """INSERT INTO parcel_signaux_vie (idu, signal)
           SELECT DISTINCT p.idu, 'friche'
           FROM parcels p
           JOIN spatial_layers f ON f.kind = 'friche'
             AND p.geom_2975 && f.geom_2975 AND ST_Intersects(p.geom_2975, f.geom_2975)
           ON CONFLICT DO NOTHING""")).rowcount

    # ── assemblage_pm : société PRIVÉE (groupe 0) détenant ≥ 3 parcelles sur l'île ──
    session.execute(text("DELETE FROM parcel_signaux_vie WHERE signal = 'assemblage_pm'"))
    counts["assemblage_pm"] = session.execute(text(
        """INSERT INTO parcel_signaux_vie (idu, signal)
           SELECT DISTINCT pm.idu, 'assemblage_pm'
           FROM parcelle_personne_morale pm
           JOIN (SELECT siren FROM parcelle_personne_morale
                 WHERE groupe = 0 AND siren IS NOT NULL
                 GROUP BY siren HAVING count(DISTINCT idu) >= :seuil) own
             ON own.siren = pm.siren
           WHERE pm.groupe = 0
           ON CONFLICT DO NOTHING"""), {"seuil": ASSEMBLAGE_MIN_PARCELLES}).rowcount

    session.flush()
    return counts
