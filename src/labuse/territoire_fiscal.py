"""M106 P3 — DISPOSITIFS FISCAUX TERRITORIAUX servis comme ATTRIBUTS DE COMMUNE (patron M95).

Deux faits territoriaux, échelle commune, sourcés et datés. M134 (arbitrage Vic) : on
CITE les taux LÉGAUX du dispositif (un fait du décret/CGI, doctrine Sourcé) — jamais un
calcul d'avantage PERSONNALISÉ (« vous économiserez X € »), qui relève du fiscaliste.

· ZFANG (art. 44 quaterdecies CGI) : régime de plein droit dans les DOM ; le décret
  n° 2026-421 du 29 mai 2026 crée un régime RENFORCÉ pour six communes de l'Est de
  La Réunion (Bras-Panon, La Plaine-des-Palmistes, Saint-André, Saint-Benoît,
  Sainte-Rose, Salazie).
· FRR ex-ZRR (art. 44 quindecies A CGI, en vigueur 01/07/2024) : les communes de
  La Réunion sont classées via la ZONE SPÉCIALE D'ACTION RURALE (décret n° 78-690,
  les Hauts) dont la délimitation est INFRA-COMMUNALE — mesuré sur le jeu Région
  Réunion (ZRR 2017) : 3 communes classées EN TOTALITÉ (Cilaos, Salazie, La
  Plaine-des-Palmistes), 20 EN PARTIE, Le Port HORS zone. On sert l'état honnête
  (« en partie » ≠ « classée »), jamais une conclusion parcellaire.

« Un seul endroit » : la liste des communes vient du SEED versionné
data/fiscal/territoire_fiscal.csv — JAMAIS en dur dans le service (patron M95).
"""
from __future__ import annotations

import csv
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

#: millésimes AMONT (dates des textes, pas de l'ingestion) — voyagent vers data_sources.
ZFANG_MILLESIME = "Décret n° 2026-421 du 29 mai 2026 (LF 2026, art. 18)"
#: contrainte data_sources.source_millesime = varchar(64) — version courte ici, le détail
#: complet vit dans les libellés servis et technical_notes du catalogue.
FRR_MILLESIME = "ZSAR 1978 · FRR 01/07/2024 · réf. ZRR 2017 (Région)"
#: liens vers les textes (vérifiés) — servis à l'écran, l'utilisateur va au texte.
ZFANG_LIEN = "https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000054153903"
FRR_LIEN = "https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000049746820"

#: la garde — servie avec chaque attribut. M134 : on CITE les taux légaux (fait du décret/CGI),
#: jamais un calcul d'avantage personnalisé.
AVERTISSEMENT = ("Fait territorial sourcé et daté. Les taux cités sont les taux LÉGAUX du "
                 "dispositif (décret / CGI), pas un calcul de votre avantage : l'éligibilité et "
                 "l'effet réel relèvent de votre expert-comptable ou avocat fiscaliste.")

_ZFANG_LIBELLE = {
    # M134 (arbitrage Vic, option b) : le taux statutaire EST un fait du décret 2026-421.
    "renforce": "Régime renforcé (commune de l'Est, décret n° 2026-421 du 29 mai 2026) — "
                "abattements majorés : 80 % sur les bénéfices et la taxe foncière bâtie, 100 % "
                "sur la CFE, jusqu'en 2030.",
    "standard": "Régime standard — dispositif de plein droit dans les DOM (art. 44 quaterdecies "
                "CGI) : abattement d'environ 50 % sur les bénéfices.",
}
_FRR_LIBELLE = {
    "totalite": "Commune classée en totalité (zone spéciale d'action rurale — décret n° 78-690 ; "
                "FRR depuis le 1er juillet 2024).",
    "partie": "Commune classée en partie seulement — la zone spéciale d'action rurale (les Hauts) "
              "est infra-communale : la situation dépend de la localisation exacte du terrain.",
    "hors": "Commune hors zone (non classée).",
}

SEED = "territoire_fiscal.csv"
DDL = """
CREATE TABLE IF NOT EXISTS territoire_fiscal_commune (
  insee varchar(5) PRIMARY KEY,
  commune text NOT NULL,
  zfang_regime text NOT NULL CHECK (zfang_regime IN ('standard', 'renforce')),
  frr_classement text NOT NULL CHECK (frr_classement IN ('totalite', 'partie', 'hors')),
  updated_at timestamptz DEFAULT now()
)
"""


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_territoire_fiscal(session: Session) -> dict:
    """Matérialise le seed (idempotent) et renseigne les millésimes dans data_sources
    (fraîcheur = date des textes amont, jamais l'ingestion — doctrine M95/M86)."""
    session.execute(text(DDL))
    seed = _repo_root() / "data" / "fiscal" / SEED
    n = 0
    with seed.open(encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter=";"):
            if not row.get("insee"):
                continue
            session.execute(text(
                "INSERT INTO territoire_fiscal_commune (insee, commune, zfang_regime, frr_classement) "
                "VALUES (:i, :c, :z, :f) ON CONFLICT (insee) DO UPDATE SET commune = EXCLUDED.commune, "
                "zfang_regime = EXCLUDED.zfang_regime, frr_classement = EXCLUDED.frr_classement, "
                "updated_at = now()"),
                {"i": row["insee"], "c": row["commune"], "z": row["zfang_regime"],
                 "f": row["frr_classement"]})
            n += 1
    for name, mill in (("ZFANG — zone franche d'activité nouvelle génération (Légifrance)", ZFANG_MILLESIME),
                       ("FRR ex-ZRR — zone spéciale d'action rurale (Légifrance)", FRR_MILLESIME)):
        session.execute(text("UPDATE data_sources SET source_millesime = :m WHERE name = :n"),
                        {"m": mill, "n": name})
    session.commit()
    renforcees = session.execute(text(
        "SELECT count(*) FROM territoire_fiscal_commune WHERE zfang_regime = 'renforce'")).scalar()
    return {"communes": n, "zfang_renforcees": int(renforcees)}


def attributs_commune(db: Session, insee: str) -> dict | None:
    """LE point de service (un critère = un seul endroit). `insee` = 5 premiers caractères
    de l'IDU. Table absente ou commune inconnue → None (l'absence s'affiche, ne casse pas)."""
    try:
        row = db.execute(text(
            "SELECT commune, zfang_regime, frr_classement FROM territoire_fiscal_commune "
            "WHERE insee = :i"), {"i": insee}).mappings().first()
    except Exception:
        db.rollback()
        return None
    if not row:
        return None
    return {
        "commune": row["commune"],
        "zfang": {"regime": row["zfang_regime"], "libelle": _ZFANG_LIBELLE[row["zfang_regime"]],
                  "source_ref": ZFANG_MILLESIME, "lien": ZFANG_LIEN},
        "frr": {"classement": row["frr_classement"], "libelle": _FRR_LIBELLE[row["frr_classement"]],
                "source_ref": FRR_MILLESIME, "lien": FRR_LIEN},
        "avertissement": AVERTISSEMENT,
    }
