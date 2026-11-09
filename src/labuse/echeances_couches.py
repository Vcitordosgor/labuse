"""VERIF-FIX-1 (Q2 — fraîcheur) — l'ÉCHÉANCE de mise à jour des couches de la carte.

Constat de l'audit VERIF-2 : la machinerie de fraîcheur est INERTE pour les couches carte
(toutes `sans_echeance`), et la fraîcheur servie à l'admin se mesure sur la date de dernière
SYNCHRO, pas sur l'âge RÉEL de la donnée. Une couche re-synchronisée récemment mais dont la
géométrie date de 2020 (lignes HTA EDF) paraît donc « à jour ».

Ce module pose, pour chaque source qui alimente la carte, une ÉCHÉANCE ancrée sur la date RÉELLE
de la donnée (son millésime), pas sur la synchro. Au-delà d'une fenêtre de revue (24 mois), la
source remonte « à vérifier » dans la page Données (admin) et chez John, avec l'amont à surveiller.
CÔTÉ CLIENT, RIEN NE CHANGE : aucune échéance ni millésime n'est affiché à l'utilisateur final
(décision PAGE-SOURCES-1) — ce module ne nourrit que l'admin et John.

Aucune échéance n'est inventée : on ne marque « à vérifier » que là où on connaît la vraie date de
la donnée (millésime curé ou lisible). Une source sans date lisible, ou une archive figée (cadastre
1877, SCAN 50 de 1950…), ne porte PAS d'échéance et ne clignote jamais.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone

#: Fenêtre de revue : au-delà de 24 mois après la date réelle de la donnée, on invite à vérifier
#: l'amont (une nouvelle édition existe peut-être). Plancher commun aux couches de référence servies.
REVUE_JOURS = 730

#: Dates RÉELLES de la donnée (millésime), curées depuis l'audit VERIF-2 là où le texte du millésime
#: ne les porte pas lisiblement ou induit en erreur (EDF : « publié 2025 » mais géométrie de 2020).
#: Clé = fragment du NOM de la source (ILIKE). Ces assertions l'emportent sur tout texte amont.
HORIZONS_CURES: dict[str, date] = {
    "Ravines — domaine public fluvial": date(2006, 8, 21),   # DPF, arrêté 06-3077
    "GéoLittoral": date(2018, 1, 1),                          # trait de côte / érosion (Cerema)
    "EDF Réunion — lignes moyenne tension": date(2020, 2, 1),  # HTA — géométrie 02/2020 (≠ publication 2025)
    "Parc National de La Réunion": date(2021, 1, 1),
    "cartes de bruit stratégiques": date(2022, 1, 1),         # CBS
    "Zones humides — inventaires DEAL": date(2019, 1, 1),     # dernier inventaire du lot
    "OCS GE": date(2022, 1, 1),                               # occupation du sol (édition 2022)
    "Classement sonore": date(2023, 12, 1),                   # arrêtés déc. 2023
}

#: Archives FIGÉES (aucune nouvelle édition amont attendue) : jamais d'échéance.
_ARCHIVE_RE = re.compile(r"géoréf|cadastre 18|historique|scan 50|edugéo|\b1950\b|\b1980\b", re.IGNORECASE)
_ANNEE_RE = re.compile(r"(19\d{2}|20\d{2})")


def _aujourdhui() -> date:
    return datetime.now(tz=timezone.utc).date()


def _annee_max(texte: str | None) -> int | None:
    """Le millésime (année) le PLUS RÉCENT lisible dans le texte, ou None."""
    annees = [int(a) for a in _ANNEE_RE.findall(texte or "")]
    return max(annees) if annees else None


def horizon_reel(nom: str, millesime: str | None, source_horizon_at: date | None) -> date | None:
    """La date RÉELLE de la donnée : assertion curée d'abord, puis l'horizon amont écrit par
    l'ingester, puis l'année lisible du millésime (ancrée au 31/12 — hypothèse optimiste « au plus
    tard dans l'année »). Une archive figée → None (jamais d'échéance)."""
    for frag, d in HORIZONS_CURES.items():
        if frag.lower() in (nom or "").lower():
            return d
    if _ARCHIVE_RE.search(millesime or ""):
        return None
    if source_horizon_at is not None:
        return source_horizon_at
    an = _annee_max(millesime)
    return date(an, 12, 31) if an else None


def echeance_de(horizon: date | None) -> date | None:
    """L'échéance de revue = date réelle + fenêtre de revue (24 mois)."""
    return horizon + timedelta(days=REVUE_JOURS) if horizon is not None else None


def a_verifier(echeance: date | None, aujourdhui: date | None = None) -> bool:
    """Vrai si l'échéance de revue est DÉPASSÉE (la donnée est plus vieille que sa fenêtre de revue)."""
    return echeance is not None and echeance < (aujourdhui or _aujourdhui())


def echeance_pour(nom: str, millesime: str | None, source_horizon_at: date | None,
                  aujourdhui: date | None = None) -> dict:
    """Tout en un pour les lecteurs (admin, John) : horizon réel, échéance, drapeau « à vérifier »."""
    h = horizon_reel(nom, millesime, source_horizon_at)
    e = echeance_de(h)
    return {"horizon": h, "echeance": e, "a_verifier": a_verifier(e, aujourdhui)}


def ensure_echeances_couches(engine) -> dict:
    """Persiste `source_horizon_at` (où NULL) et `prochain_millesime_at` (l'échéance) pour les sources
    qui alimentent la carte. Idempotent, sûr à rejouer. Lit le millésime courant → se recale à chaque
    passage (ingester/sentinelle peuvent l'avoir rafraîchi). Rendu : compte des sources à vérifier."""
    from sqlalchemy import text
    poses = a_verif = 0
    with engine.begin() as c:
        rows = c.execute(text(
            "SELECT d.id, d.name, d.source_millesime, d.source_horizon_at "
            "FROM data_sources d WHERE d.id IN "
            "(SELECT DISTINCT data_source_id FROM spatial_layers WHERE data_source_id IS NOT NULL)")
        ).mappings().all()
        for r in rows:
            h = horizon_reel(r["name"], r["source_millesime"], r["source_horizon_at"])
            if h is None:
                continue
            e = echeance_de(h)
            # source_horizon_at : posé seulement s'il manque (ne jamais écraser un horizon d'ingester) ;
            # prochain_millesime_at : toujours recalé (dérive de l'horizon courant).
            c.execute(text(
                "UPDATE data_sources SET "
                "  source_horizon_at = COALESCE(source_horizon_at, :h), "
                "  prochain_millesime_at = :e WHERE id = :id"),
                {"h": h, "e": e, "id": r["id"]})
            poses += 1
            if a_verifier(e):
                a_verif += 1
    return {"sources_couches": poses, "a_verifier": a_verif}
