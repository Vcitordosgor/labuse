"""FRAICHEUR-FIX-1 (point 6) — le CONTRÔLE DE MILLÉSIME : prouver « à jour », sinon « à vérifier ».

Le thème du mandat (FRAICHEUR-1 §7) : la sonde projetait « à jour » côté LABUSE pour tout ce qui
n'était pas explicitement `nouvelle_version`, alors qu'elle lisait un signal qui N'EST PAS le millésime
réellement servi (Last-Modified d'un fichier legacy figé, `last_update` d'un dataset dont le job
d'ingestion ne tourne pas, mtime/année d'une page). Un retard amont restait donc invisible.

Ici, pour les sources qui ont un vrai AXE DE MILLÉSIME (un « dernier publié » et un « réellement
ingéré » comparables), on tranche par PREUVE :
  · le DERNIER PUBLIÉ      — lu par la sentinelle (`source_veille.dernier_vu`), rendu par une sonde qui
                             lit le bon signal (DVF : le dernier fichier `full-AAAA-sN` ; SITADEL : le
                             dernier mois de données ; RP : le millésime du recensement) ;
  · le RÉELLEMENT INGÉRÉ   — lu DANS LA DONNÉE (`data_sources.source_horizon_at`, calculé par
                             `fraicheur.persist_millesime` depuis la table SERVIE), ou un lecteur dédié.
Verdict :
  · `a_jour`     — ingéré ≥ publié (PROUVÉ) ;
  · `en_retard`  — publié strictement plus récent que l'ingéré (décrochage prouvé) ;
  · `a_verifier` — publié connu mais ingéré inconnu/illisible → on ne PEUT PAS prouver « à jour ».
Une source sans contrôle (continu/figé/événementiel, ou dont le signal publié n'est pas un millésime)
retourne `None` → l'état normal d'`etats_sources` s'applique (jamais de faux « à vérifier »).

Granularité : ANNÉE × MOIS (`AAAAMM`) — assez fine pour SITADEL (mensuel) comme pour DVF (semestriel,
S1 = juin / S2 = décembre). Module PUR côté comparaison ; `verdict` reçoit une connexion pour les
lecteurs d'ingéré dédiés.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Callable

_ANNEE = re.compile(r"\b(19|20)\d{2}\b")


def periode(x) -> int | None:
    """Normalise un millésime hétérogène en entier COMPARABLE `AAAAMM` (mois 1-12). None si illisible.

    Reconnaît : date/datetime ; « 2026-S1 »/« 2026-s2 » (semestre → juin/décembre) ; « 2026-09 » ;
    une date ISO/française dans une chaîne ; une année nue ou « RP2023 » (→ décembre de l'année).
    Une année seule vaut DÉCEMBRE : un fichier annuel couvre jusqu'à la fin de l'année."""
    if x is None:
        return None
    if isinstance(x, (date, datetime)):
        return x.year * 100 + x.month
    s = str(x).strip()
    if not s:
        return None
    # « 2026-S1 » / « 2026 S2 » — le semestre d'abord (sinon capté comme année nue)
    m = re.search(r"(20\d{2})[\s_-]*[Ss]([12])\b", s)
    if m:
        return int(m.group(1)) * 100 + (6 if m.group(2) == "1" else 12)
    # « 2026-09 » / « 2026/09 » / ISO « 2026-09-30 » / timestamp « 2026-09-30T… » — année-mois
    m = re.search(r"\b(19|20)(\d{2})[-/](0[1-9]|1[0-2])\b", s)
    if m:
        return (int(m.group(1) + m.group(2))) * 100 + int(m.group(3))
    # année nue / « RP2023 » (collée à des lettres) / « millésime 2023 » → décembre de l'année la
    # plus récente citée. Lookarounds de CHIFFRES (pas `\b`) : « RP2023 » doit matcher, « 12345 » non.
    annees = [int(a) for a in re.findall(r"(?<!\d)(?:19|20)\d{2}(?!\d)", s)]
    if annees:
        return max(annees) * 100 + 12
    return None


@dataclass(frozen=True)
class Controle:
    """Comment lire les deux côtés de l'axe d'une source sous contrôle de millésime."""
    nom: str
    cadence: str
    #: lecteur du DERNIER PUBLIÉ depuis la ligne (défaut : `dernier_vu` de la sentinelle).
    lire_publie: Callable[[dict], object] = lambda row: row.get("veille_statut_vu") or row.get("dernier_vu")
    #: lecteur du RÉELLEMENT INGÉRÉ (défaut : horizon calculé dans la donnée). Reçoit (conn, row).
    lire_ingere: Callable[[object, dict], object] = lambda conn, row: row.get("source_horizon_at")


# ─────────────────────────── le registre des sources sous contrôle ───────────────────────────
# On n'inscrit QUE les sources à vrai axe de millésime, dont la sonde publie le bon signal (sinon on
# laisserait passer un faux « à vérifier »). DVF est le cas prouvé de bout en bout (FRAICHEUR-FIX-1
# point 1). SITADEL (point 2), RP EGOUL + IRIS (point 4) sont inscrits quand leur sonde lit le millésime.
CONTROLES: dict[str, Controle] = {
    "DVF / valeurs foncières": Controle(
        nom="DVF / valeurs foncières", cadence="semestriel (avril / octobre)"),
    # SITADEL (point 2) — publié = dernier mois couvert (sonde `temporal_coverage.end`), ingéré =
    # dernier mois en base (source_horizon_at = max(date) sitadel_permits, posé par l'ingestion).
    "SITADEL (autorisations d'urbanisme)": Controle(
        nom="SITADEL (autorisations d'urbanisme)", cadence="mensuel"),
    # RP IRIS (point 4) — recensement INSEE. Publié = année RP lue par la sonde `page` (insee.fr,
    # « Logement en AAAA ») ; ingéré = millésime RP RÉELLEMENT en base (`iris_rp.millesime`, ex.
    # « RP2022 … »). Tant que l'édition servie == l'édition publiée → à jour ; RP2023 publié mais pas
    # encore ingéré → en retard (la bascule se fait en passant les URLs RP2023 à `ingest-iris-rp`).
    "INSEE RP2022 — bases IRIS (logement, population)": Controle(
        nom="INSEE RP2022 — bases IRIS (logement, population)", cadence="annuel (recensement)",
        # on extrait l'ANNÉE RP (« RP2022 »), jamais la date de parution qui traîne dans le libellé.
        lire_ingere=lambda conn, row: _lire_scalaire(
            conn, r"SELECT max(substring(millesime from 'RP ?([0-9]{4})')) FROM iris_rp")),
}


def _lire_scalaire(conn, sql: str):
    """Lit un scalaire (millésime ingéré) ; None si la table est absente ou vide — jamais une exception
    (une base partielle → ingéré inconnu → « à vérifier », pas un 500)."""
    from sqlalchemy import text as _t
    try:
        return conn.execute(_t(sql)).scalar()
    except Exception:  # noqa: BLE001
        return None


def verdict(conn, row: dict) -> dict | None:
    """Verdict de millésime d'une source. `row` porte `name`, `dernier_vu`, `source_horizon_at`.
    Retourne None si la source n'est pas sous contrôle (état normal préservé)."""
    ctrl = CONTROLES.get(row.get("name"))
    if ctrl is None:
        return None
    pub = periode(ctrl.lire_publie(row))
    if pub is None:
        # le dernier publié n'est pas (encore) un millésime lisible → pas de contrôle actionnable.
        return None
    ing = periode(ctrl.lire_ingere(conn, row))
    publie_lbl = _mmaa(pub)
    ingere_lbl = _mmaa(ing) if ing is not None else None
    if ing is None:
        return {"etat": "a_verifier", "publie": publie_lbl, "ingere": None,
                "phrase_admin": (f"À VÉRIFIER — dernier publié {publie_lbl}, millésime ingéré "
                                 "introuvable dans la donnée : « à jour » non prouvé."),
                "phrase_client": "Vérification de fraîcheur en cours."}
    if pub > ing:
        return {"etat": "en_retard", "publie": publie_lbl, "ingere": ingere_lbl,
                "phrase_admin": (f"EN RETARD — l'amont publie {publie_lbl}, LABUSE sert {ingere_lbl}. "
                                 f"Source : {ctrl.nom}."),
                "phrase_client": "Mise à jour en cours."}
    return {"etat": "a_jour", "publie": publie_lbl, "ingere": ingere_lbl,
            "phrase_admin": f"À jour — ingéré {ingere_lbl} ≥ publié {publie_lbl} (prouvé)."
                            if ing != pub else f"À jour — millésime {ingere_lbl} (prouvé).",
            "phrase_client": "À jour."}


def _mmaa(p: int | None) -> str | None:
    """`AAAAMM` → libellé court « MM/AAAA » (ou « AAAA » si décembre = année pleine)."""
    if p is None:
        return None
    an, mois = divmod(p, 100)
    return str(an) if mois == 12 else f"{mois:02d}/{an}"


# ─────────────── FRAICHEUR-FIX-1 (point 7) — le rejeu nocturne du tableau des sources ───────────────

_DDL_SNAPSHOT = """
CREATE TABLE IF NOT EXISTS fraicheur_controle_nuit (
  name             text PRIMARY KEY,
  etat             text NOT NULL,        -- en_retard | a_verifier | a_jour | …
  millesime_publie text,
  millesime_ingere text,
  phrase_admin     text,
  verdict_at       timestamptz NOT NULL DEFAULT now()
)
"""


def rejouer_nuit(db) -> dict:
    """Rejoue le TABLEAU des sources (verdicts de fraîcheur, contrôle de millésime inclus) et écrit un
    INSTANTANÉ (`fraicheur_controle_nuit`, lu par la page Données / le rapport). Retourne les sources
    EN RETARD (décrochage prouvé) et À VÉRIFIER (non prouvé). Lecture seule hormis l'instantané."""
    from sqlalchemy import text as _t

    from . import etats_sources
    db.execute(_t(_DDL_SNAPSHOT))
    etats = etats_sources.lister_etats(db)
    db.execute(_t("DELETE FROM fraicheur_controle_nuit"))
    for e in etats:
        db.execute(_t(
            "INSERT INTO fraicheur_controle_nuit (name, etat, millesime_publie, millesime_ingere, "
            " phrase_admin) VALUES (:n, :e, :mp, :mi, :pa)"),
            {"n": e["name"], "e": e["etat"], "mp": e.get("millesime_publie"),
             "mi": e.get("millesime_ingere"), "pa": e.get("phrase_admin")})
    retards = [e for e in etats if e["etat"] == "en_retard"]
    verifs = [e for e in etats if e["etat"] == "a_verifier"]
    return {"total": len(etats), "retards": retards, "a_verifier": verifs}
