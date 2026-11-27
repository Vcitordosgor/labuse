"""PHASE A cycle 2, volet 2 (badge) — « PC caducs ».

Table ADDITIVE `pc_caducs`, dérivée en LECTURE de Sitadel. Ne touche JAMAIS les tables servies
(p_model_permits + sitadel_permits + parcels). OUTIL-PERMIS-FIX-8 (LOT 3) : l'achèvement vient
désormais de `sitadel_permits.raw->>'daact'` (plus de `m10_permit_delais`, décommissionnée). Signal
parcellaire et horodaté :
# M44 Lot 0 (constaté sur pièces) : pc_caducs NE dépend d'AUCUN run — `_SELECT_RAW` lit les permis
# et l'univers `parcels`, pas `parcel_p_score_v2`. La mention M31 « run servi q_v7_defisc » était une
# note fausse (doctrine : une note n'est pas une source). Aligner un run ici est SANS OBJET (0 effet).
la parcelle et ses dates, JAMAIS le demandeur (personne physique possible) ni un jugement du propriétaire.

Doctrine (cf. A1_PC_CADUCS_CADRAGE.md) : un PC OCTROYÉ jamais réalisé porte une constructibilité prouvée
et une intention abandonnée → propension de revente ×1,6 vs PC réalisé comparable (backtest, seed 974).
Signal RÉTROSPECTIF (l'arène le juge de plein droit).

Définition parcelle (état Sitadel — la DOC/ouverture de chantier n'existe pas dans les données ; la
contre-vérif bâti est inopérante, cf. cadrage §3.2) :
  - réalisé = ≥1 PC achevé (etat=6 OU DAACT présent) OU travaux commencés (etat=5 : la constructibilité
    a été non seulement prouvée mais mise en œuvre → ce n'est pas « jamais commencé ») ;
  - caduc   = OCTROYÉ (etat∈{2 autorisé, 5 commencés, 6 achevés}) MAIS aucun réalisé → en pratique un
    PC AUTORISÉ (etat=2) jamais commencé ni achevé ;
  - ÉCHÉANCE DÉPASSÉE : la validité légale de l'autorisation est écoulée à la date de référence
    (cf. OUTIL-PERMIS-FIX-13 ci-dessous : calcul par DATE, plus par année).
Autorisation = Sourcé (Sitadel) ; caducité = Estimé (inférée).

ORACLE-FIX-1 (Lot C) — un permis ANNULÉ (etat=4, cf. ingestion/permits.ETAT_LABELS) ne prouve AUCUNE
constructibilité : il SORT de la preuve et de toute surcote. La définition doctrinale « octroyé » =
autorisé/commencé/achevé {2,5,6}, jamais annulé.

OUTIL-PERMIS-FIX-13 (contre-audit ASTRA-7) — DEUX corrections :
  (LOT 2) la reconstruction lit la DATE D'AUTORISATION SOURCE `sitadel_permits.date` (via l'explosion
          directe de `idu_codes`), PLUS la table dérivée `p_model_permits.date_autorisation` qui était
          PÉRIMÉE (elle portait parfois la date de dépôt brute — ex. 97415000DP0016 : 28/08/2023 au lieu
          du 26/02/2020 réel) et incomplète (couples PC/parcelle manquants). Zéro intermédiaire → zéro
          décalage ni oubli.
  (LOT 1) l'échéance de validité est calculée par DATE d'autorisation (`_echeance`), avec sa BASE LÉGALE :
          droit commun 3 ans (art. R.424-17 du Code de l'urbanisme) ; décret n° 2025-461 du 26/05/2025
          (prorogation exceptionnelle, autorisations encore valides à son entrée en vigueur le 28/05/2025) :
          validité portée à 5 ANS par son ARTICLE 1er pour les autorisations délivrées du 28/05/2022 au
          28/05/2024, et +1 an (→ 4 ans) par son ARTICLE 2 pour celles du 01/01/2021 au 27/05/2022 (LOT 3
          FIX-14 : la prorogation d'un an relève de l'art. 2, pas de l'art. 1er). Caduc probable = échéance STRICTEMENT dépassée
          à la date de référence. Les prorogations « sur demande » (2×1 an) ne sont pas supposées (invisibles
          dans Sitadel). La contre-vérif bâti n'est PAS consultée : le libellé le dit (« sur les seules
          données Sitadel ») et l'infobulle ne parle plus de croisement bâti.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import text
from sqlalchemy.orm import Session

DEFAULT_REF_YEAR = 2026        # repli si ref_date non fournie (cf. build_pc_caducs)

# CHASSE-FIX-3 (C3-06) — VERSION DE LA RÈGLE. À incrémenter dès qu'on touche la définition
# « octroyé / réalisé / caduc » OU le calcul d'échéance. Gravée dans `fraicheur_etat` au rebuild ;
# le contrôle de fraîcheur (fraicheur_caches._etat_derives_regle) signale « à reconstruire » quand la
# version du CODE a bougé sans rebuild.
RULE_VERSION = "fix16:octroye{2,5,6}+realise{5,6|daact}+echeance-date(R424-17/decret-2025-461:art1=5ans,art2=+1an,art3=valide-le-27052025)+src-sitadel.date"

# ── OUTIL-PERMIS-FIX-13 (LOT 1) — ÉCHÉANCE DE VALIDITÉ par DATE d'autorisation, avec base légale ──
_DECRET_P1 = (dt.date(2022, 5, 28), dt.date(2024, 5, 28))   # 5 ans (décret 2025-461)
_DECRET_P2 = (dt.date(2021, 1, 1), dt.date(2022, 5, 27))    # 3 + 1 an (décret 2025-461)
# OUTIL-PERMIS-FIX-16 (LOT 2) — ARTICLE 3 du décret : le bénéfice des articles 1er et 2 est réservé
# aux autorisations ENCORE VALIDES à la date de publication (27/05/2025). Une autorisation dont la
# validité de DROIT COMMUN (3 ans) était déjà écoulée à cette date reste régie par le droit commun.
_DECRET_VALIDE_LE = dt.date(2025, 5, 27)                    # jour de publication au JO (art. 3)
_BASE_DROIT_COMMUN = "validité 3 ans (droit commun, art. R.424-17 du Code de l'urbanisme)"
# OUTIL-PERMIS-FIX-16 (LOT 2) — autorisation DANS une fenêtre du décret mais déjà caduque au 27/05/2025 :
# droit commun maintenu, art. 3 cité pour expliquer pourquoi la prorogation ne s'applique pas.
_BASE_HORS_DECRET = ("validité 3 ans (droit commun, art. R.424-17) — autorisation déjà caduque le "
                     "27/05/2025, hors du bénéfice du décret n° 2025-461 (art. 3)")
_BASE_P1 = ("validité 5 ans (décret n° 2025-461 du 26/05/2025, art. 1er, autorisations délivrées du "
            "28/05/2022 au 28/05/2024, non prorogeable)")
# OUTIL-PERMIS-FIX-14 (LOT 3) — la prorogation d'un an relève de l'ARTICLE 2 du décret (le 5 ans de
# l'art. 1er concerne la seule fenêtre 28/05/2022→28/05/2024) : citation corrigée.
_BASE_P2 = ("validité 4 ans (3 ans de droit commun + 1 an, décret n° 2025-461 du 26/05/2025, art. 2, "
            "autorisations délivrées du 01/01/2021 au 27/05/2022)")


def _plus_annees(d: dt.date, n: int) -> dt.date:
    """d + n années (gère le 29 février → 28 février)."""
    try:
        return d.replace(year=d.year + n)
    except ValueError:
        return d.replace(year=d.year + n, day=28)


def _echeance(d_aut: dt.date) -> tuple[dt.date, str]:
    """Échéance de validité d'une autorisation de construire + sa base légale, à partir de SA DATE.

    OUTIL-PERMIS-FIX-16 (LOT 2) — ARTICLE 3 du décret n° 2025-461 : la prorogation (5 ans art. 1er ;
    +1 an art. 2) ne profite QU'aux autorisations encore valides le 27/05/2025. Une autorisation dont
    la validité de droit commun (3 ans) était déjà écoulée à cette date garde son échéance de 3 ans —
    le décret, publié après sa caducité, ne la ressuscite pas. Ex. 97406000AV1068 (04/01/2021) :
    échéance de droit commun 04/01/2024 < 27/05/2025 → PAS d'art. 2, échéance 04/01/2024 (pas 2025)."""
    commun = _plus_annees(d_aut, 3)
    # art. 3 : la prorogation du décret n'est ouverte que si l'autorisation est encore valide le 27/05/2025.
    if commun >= _DECRET_VALIDE_LE:
        if _DECRET_P1[0] <= d_aut <= _DECRET_P1[1]:
            return _plus_annees(d_aut, 5), _BASE_P1
        if _DECRET_P2[0] <= d_aut <= _DECRET_P2[1]:
            return _plus_annees(d_aut, 4), _BASE_P2
        return commun, _BASE_DROIT_COMMUN
    # validité de droit commun déjà écoulée au 27/05/2025 : art. 3 → droit commun maintenu.
    # (fenêtre du décret = union P2∪P1 = 01/01/2021→28/05/2024 ; seules des autorisations de la
    #  fenêtre P2 tombent ici, celles de P1 étant toujours encore valides au 27/05/2025.)
    if _DECRET_P2[0] <= d_aut <= _DECRET_P1[1]:
        return commun, _BASE_HORS_DECRET
    return commun, _BASE_DROIT_COMMUN


DDL = """
CREATE TABLE IF NOT EXISTS pc_caducs (
  idu                 varchar(14) PRIMARY KEY REFERENCES parcels (idu),
  pc_annee            int  NOT NULL,       -- année de la plus ancienne autorisation OCTROYÉE (Sourcé, Sitadel)
  caduc_depuis        int  NOT NULL,       -- année de l'ÉCHÉANCE de validité calculée (Estimé)
  n_pc_octroyes       int  NOT NULL,       -- nb de PC octroyés sur la parcelle
  statut_autorisation text NOT NULL DEFAULT 'Sourcé',
  statut_caducite     text NOT NULL DEFAULT 'Estimé',
  libelle_court       text NOT NULL,       -- « PC autorisé le JJ/MM/AAAA · … · caducité probable depuis … »
  detail              text NOT NULL,       -- survol : échéance + base légale + « sur les seules données Sitadel »
  -- OUTIL-PERMIS-FIX-16 (LOT 1) — base légale + date d'autorisation + échéance servies À PART, pour que
  -- l'historique de fiche réunisse la PREUVE au même endroit que le signal (sans la phrase marketing).
  base_legale         text,                -- « validité N ans (… art. …) »
  date_autorisation   date,                -- date d'autorisation de la plus ancienne octroyée (Sourcé)
  echeance            date,                -- échéance de validité calculée (Estimé)
  updated_at          timestamptz DEFAULT now()
);
"""

# Caduc = octroyé jamais réalisé, échéance de validité dépassée. Une parcelle = plusieurs PC → agrégation.
# OUTIL-PERMIS-FIX-13 (LOT 2) — lecture DIRECTE de sitadel_permits : date d'autorisation SOURCE
# (`sp.date`) et explosion directe de `idu_codes` ; plus AUCUNE dépendance à la table dérivée
# `p_model_permits` (périmée : date de dépôt brute en date_autorisation + couples manquants).
# L'échéance est calculée en Python (`_row`/`_echeance`) à partir de `d_octroye` (la plus ancienne date
# d'autorisation octroyée) — le filtre « échéance dépassée » vit là, pas dans ce SELECT.
_SELECT_RAW = """
WITH pc AS (
  SELECT j.idu, sp.date::date AS d_aut,
         (sp.raw->>'etat') AS etat,
         -- `IS TRUE` : un daact ABSENT (regex sur NULL = NULL) devient false, jamais NULL — sinon
         -- `bool_or(... )`/`NOT realized` propagerait le NULL et un caduc réel serait exclu à tort.
         (sp.raw->>'daact' ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}' IS TRUE) AS daact
  FROM sitadel_permits sp
  JOIN LATERAL jsonb_array_elements_text(sp.idu_codes) j(idu) ON true
  WHERE sp.type = 'PC' AND sp.date IS NOT NULL),
parc AS (
  SELECT idu,
         -- ORACLE-FIX-1 : octroyé = autorisé/commencé/achevé {2,5,6} (JAMAIS annulé=4) ;
         -- réalisé = achevé/DAACT OU travaux commencés (5) → exclut le « jamais commencé ».
         min(d_aut) FILTER (WHERE etat IN ('2','5','6')) AS d_octroye,
         bool_or(daact OR etat IN ('5','6')) AS realized,
         bool_or(etat IN ('2','5','6'))      AS granted,
         count(*) FILTER (WHERE etat IN ('2','5','6')) AS n_octroyes
  FROM pc GROUP BY idu)
SELECT parc.idu, parc.d_octroye, parc.n_octroyes
FROM parc
JOIN parcels p ON p.idu = parc.idu          -- univers servi uniquement (FK + périmètre)
WHERE parc.granted AND NOT parc.realized;
"""

_INSERT = """
INSERT INTO pc_caducs
  (idu, pc_annee, caduc_depuis, n_pc_octroyes, statut_autorisation, statut_caducite,
   libelle_court, detail, base_legale, date_autorisation, echeance, updated_at)
VALUES
  (:idu, :y, :caduc_depuis, :n, 'Sourcé', 'Estimé', :court, :detail, :base, :d_aut, :echeance, now())
ON CONFLICT (idu) DO UPDATE SET
  pc_annee = EXCLUDED.pc_annee, caduc_depuis = EXCLUDED.caduc_depuis,
  n_pc_octroyes = EXCLUDED.n_pc_octroyes, libelle_court = EXCLUDED.libelle_court,
  detail = EXCLUDED.detail, base_legale = EXCLUDED.base_legale,
  date_autorisation = EXCLUDED.date_autorisation, echeance = EXCLUDED.echeance, updated_at = now();
"""


def _row(idu: str, d_octroye: dt.date, n: int, ref_date: dt.date) -> dict | None:
    """Ligne pc_caducs pour une parcelle octroyée-non-réalisée, OU None si elle n'est PAS caduc (échéance
    de validité non encore dépassée à `ref_date`). OUTIL-PERMIS-FIX-13 (LOT 1) : échéance par DATE."""
    echeance, base = _echeance(d_octroye)
    if echeance >= ref_date:
        return None                       # autorisation encore valide → PAS caduc (sort du signal)
    d_txt, e_txt = d_octroye.isoformat(), echeance.isoformat()
    # OUTIL-PERMIS-FIX-16 (LOT 1) — « aucun commencement déclaré » dit mieux la PREUVE disponible que
    # « jamais commencé » : Sitadel ne porte que des autorisations, on constate l'ABSENCE de déclaration
    # (DAACT / ouverture de chantier), jamais qu'il ne s'est rien passé.
    court = f"PC autorisé le {d_txt} · aucun commencement déclaré · caducité probable depuis le {e_txt}"
    detail = (
        f"Permis de construire autorisé le {d_txt} (Sitadel, Sourcé), aucun commencement déclaré ni "
        f"achèvement. {base} → échéance le {e_txt} ; caducité probable depuis cette date (Estimé, sur les "
        f"seules données Sitadel). Profil « constructibilité prouvée par l'instruction, projet non mené » — "
        f"revend ×1,6 plus qu'un PC réalisé comparable (backtest apparié, seed 974). Faits datés uniquement : "
        f"aucun jugement du propriétaire, aucune date de vente, aucune personne. À vérifier en mairie."
    )
    return {"idu": idu, "y": d_octroye.year, "caduc_depuis": echeance.year, "n": n,
            "court": court, "detail": detail, "base": base,
            "d_aut": d_octroye.isoformat(), "echeance": echeance.isoformat()}


def build_pc_caducs(session: Session, *, ref_date: dt.date | None = None, ref_year: int | None = None,
                    commit: bool = True, log=lambda *_: None) -> dict:
    """Construit/rafraîchit `pc_caducs` (rebuild complet idempotent). Lecture seule des sources.
    `ref_date` = date de référence du « probablement caduc » (défaut : aujourd'hui) ; `ref_year` legacy
    → 25/11 de l'année. `commit=False` pour les tests transactionnels. Renvoie {'total': n}."""
    if ref_date is None:
        ref_date = dt.date(ref_year, 11, 25) if ref_year else dt.date.today()
    # M-O P2-59 — rebuild NON BLOQUANT (table lue en direct par l'API : badges projet_parcelles) :
    # le SELECT + INSERT se fait hors-ligne dans une shadow, puis swap ~ms (cf. _rebuild).
    from ._rebuild import rebuild_swap

    def _populate(target: str) -> dict:
        raw = session.execute(text(_SELECT_RAW)).mappings().all()
        rows = [r for r in (_row(x["idu"], x["d_octroye"], int(x["n_octroyes"]), ref_date) for x in raw)
                if r is not None]
        ins = text(_INSERT.replace("INTO pc_caducs", f'INTO "{target}"', 1))
        for r in rows:
            session.execute(ins, r)
        return {"total": len(rows)}

    out = rebuild_swap(session, "pc_caducs", DDL, _populate, commit=commit)
    # CHASSE-FIX-3 (C3-06) — grave la version de règle courante : le contrôle de fraîcheur la
    # confrontera au code pour signaler « à reconstruire » si la règle bouge sans rebuild.
    from ..fraicheur_caches import marquer_regle_derivee
    marquer_regle_derivee(session, "pc_caducs")
    if commit:
        session.commit()
    log(f"pc_caducs : {out['total']} parcelles caduc probable (PC octroyé jamais réalisé, échéance de "
        f"validité dépassée au {ref_date.isoformat()})")
    return out
