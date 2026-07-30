"""Statut d'OUVERTURE des zones AU (mandat AU-OUVERTURE, Vic 30/07/2026).

Une zone « À Urbaniser » (AU) n'est constructible que si son règlement l'a OUVERTE à
l'urbanisation (Art. 1/2 : caractère de la zone, subordination à une modification/OAP). Les
calibrateurs PLU ont extrait les règles DIMENSIONNELLES (hauteur, emprise, reculs) sans TOUJOURS
lire l'article d'ouverture. Résultat : des parcelles servies en tête de liste sur une zone dont le
statut d'ouverture n'a JAMAIS été lu — la 2AUd brûlante du 29/07, à l'échelle (dette #7).

Ce module classe une zone AU en deux catégories de RISQUE (les seules marquées) :

* **générique** — la zone n'est PAS calibrée (`resolve_zone` retombe sur l'estimation générique).
  Statut PUR inconnu : ni règles, ni ouverture. → DÉCLASSÉE `declasse_au_statut_inconnu`.
* **dimensions_seules** — la zone EST calibrée (règles de construction extraites) mais AUCUNE note
  d'ouverture n'a été gravée. Vraisemblablement ouverte (on a lu son règlement de construction),
  mais non confirmé. → RESTE servie, avec une mention de fiche (jamais un tier de tête retiré).

Ne SONT PAS marquées : les zones DOCUMENTÉES — soit fermées au règlement (`constructible_neuf`
False → déjà traitées en A `declasse_zone_fermee`), soit portant une note d'ouverture explicite.

Le classifieur lit `resolve_zone(zone_lib, commune)` — la MÊME source que la faisabilité et la
cascade (jamais un préfixe de libellé isolé : garde-fou 21 077, cf. constructibilite.py). La marque
est cachée dans `parcel_au_statut` (clé = parcel_id, INDÉPENDANTE du run servi → survit à la
bascule, comme `parcel_constructibilite`), horodatée pour la péremption (un déclassement temporaire
sans date devient permanent par oubli — exigence Vic)."""
from __future__ import annotations

import json
import re

from sqlalchemy import text
from sqlalchemy.orm import Session

from .plu_rules import resolve_zone

#: catégorie 'générique' → tier `declasse_au_statut_inconnu`
CLASSE_GENERIQUE = "générique"
#: catégorie 'dimensions_seules' → reste servie, mention de fiche seule
CLASSE_DIMENSIONS_SEULES = "dimensions_seules"

# Péremption (arbitrage Vic 30/07, option B) — un déclassement TEMPORAIRE qui vieillit devient une
# DETTE : le temps écoulé mesure NOTRE oubli (règlement non lu), jamais la parcelle. Deux seuils :
#: en-dessous : simple compteur. Au-delà : WARN visible (surface qui « dit la vérité »).
SEUIL_WARN_JOURS = 90
#: au-delà : BLOCAGE — la bascule refuse de servir sans `--peremption-ack` humain et tracé. Ne
#: DURCIT jamais la parcelle (pas d'escalade vers ecartee : ce serait l'option A) : cible l'oubli.
SEUIL_BLOCAGE_JOURS = 180

STATUT_OK, STATUT_WARN, STATUT_BLOCAGE = "ok", "warn", "blocage"


def statut_peremption(jours_plus_ancien: int) -> str:
    """Classe l'âge du plus ancien déclassement : ok < 90 j ≤ warn < 180 j ≤ blocage."""
    if jours_plus_ancien >= SEUIL_BLOCAGE_JOURS:
        return STATUT_BLOCAGE
    if jours_plus_ancien >= SEUIL_WARN_JOURS:
        return STATUT_WARN
    return STATUT_OK

#: Un signal d'OUVERTURE dans les notes/brut de la zone calibrée = zone DOCUMENTÉE (non marquée).
#: Mots-clés du caractère de zone AU (Art. 1/2) et de la subordination à ouverture / modification.
_OUVERTURE_KW = re.compile(
    r"caract[èe]re|ouvert|urbanisation|OAP|op[ée]rations? d.ensemble|modification"
    r"|1AU|2AU|AU ?1|AU ?2|subordonn|transition|gel", re.I)

#: Motif de fiche — 313 génériques DÉCLASSÉES (étiquette « Absent », jamais « Estimé »).
MOTIF_GENERIQUE = (
    "Zone à urbaniser — ouverture à l'urbanisation NON VÉRIFIÉE, statut inconnu. Le règlement de "
    "cette zone n'a pas été lu. Déclassement TEMPORAIRE jusqu'à vérification de l'article "
    "d'ouverture.")
#: Mention de fiche — 107 dimensions-seules SERVIES + mention (texte imposé Vic, « Absent »).
MENTION_DIMENSIONS_SEULES = (
    "Zone à urbaniser — ouverture non vérifiée. Le règlement fixe des règles de construction pour "
    "cette zone, mais son ouverture à l'urbanisation n'a pas été confirmée. Vérifiez auprès de la "
    "commune avant tout engagement.")


def classify_au_statut(zone_lib: str | None, commune: str | None) -> tuple[str | None, str]:
    """Classe une zone AU en (classe, motif). Renvoie (None, "") pour une zone qui n'est PAS un
    risque d'ouverture non lue : non-AU, hors-YAML pur non-AU, zone fermée au règlement (déjà A),
    ou zone documentée (note d'ouverture présente).

    La logique reproduit EXACTEMENT la mesure du 30/07 (420 têtes = 313 génériques + 107
    dimensions-seules) : elle ne s'appuie QUE sur `resolve_zone`, jamais sur le préfixe brut."""
    if not zone_lib:
        return None, ""
    r = resolve_zone(zone_lib, commune)
    if r is None:
        return None, ""                       # hors YAML strict (non-AU géré en amont par le filtre)
    if not r.constructible_neuf:
        return None, ""                       # zone FERMÉE au règlement → déjà A (declasse_zone_fermee)
    # zone calibrée portant une note d'ouverture explicite → DOCUMENTÉE, non marquée.
    blob = json.dumps(getattr(r, "raw", {}) or {}, ensure_ascii=False) + " " + " ".join(r.notes or [])
    if r.calibree and _OUVERTURE_KW.search(blob):
        return None, ""
    if r.calibree:
        return CLASSE_DIMENSIONS_SEULES, MENTION_DIMENSIONS_SEULES
    return CLASSE_GENERIQUE, MOTIF_GENERIQUE


def build_au_statut_batch(session: Session, idus: list[str]) -> int:
    """Classe un lot de parcelles (par IDU) et upsert `parcel_au_statut`. Ne marque QUE les
    parcelles en zone AU générique/dimensions-seules ; PURGE la marque des IDUs du lot qui ne
    sont plus un risque (zone re-calibrée, ouverture lue) → idempotent, réversible, auto-nettoyant.
    Renvoie le nombre de parcelles marquées dans ce lot."""
    if not idus:
        return 0
    rows = session.execute(text("""
        SELECT p.id AS parcel_id, p.idu, p.commune, z.zone_lib
        FROM parcels p
        JOIN parcel_zone_plu z ON z.idu = p.idu
        WHERE p.idu = ANY(:idus)
          AND (z.zone_fam = 'AU' OR z.zone_lib ~ '^[0-9]?AU')
    """), {"idus": idus}).mappings().all()

    marques, a_purger = [], []
    vus = set()
    for r in rows:
        vus.add(r["idu"])
        classe, motif = classify_au_statut(r["zone_lib"], r["commune"])
        if classe is None:
            a_purger.append(r["parcel_id"])
        else:
            marques.append({"pid": r["parcel_id"], "idu": r["idu"], "classe": classe,
                            "zl": r["zone_lib"], "motif": motif})
    # les IDUs du lot HORS zone AU (pas dans `rows`) doivent aussi voir leur marque éventuelle purgée
    a_purger += [pid for (pid,) in session.execute(text(
        "SELECT parcel_id FROM parcel_au_statut a JOIN parcels p ON p.id = a.parcel_id "
        "WHERE p.idu = ANY(:idus) AND p.idu <> ALL(:vus)"),
        {"idus": idus, "vus": list(vus) or [""]}).all()]

    if a_purger:
        session.execute(text("DELETE FROM parcel_au_statut WHERE parcel_id = ANY(:ids)"),
                        {"ids": a_purger})
    for m in marques:
        # upsert : re-pose l'horodatage `computed_at` SEULEMENT à l'insertion (une re-classification
        # identique ne rajeunit pas la marque → le compteur de péremption mesure l'âge RÉEL du doute).
        session.execute(text("""
            INSERT INTO parcel_au_statut (parcel_id, idu, classe, zone_lib, motif)
            VALUES (:pid, :idu, :classe, :zl, :motif)
            ON CONFLICT (parcel_id) DO UPDATE SET
              classe = EXCLUDED.classe, zone_lib = EXCLUDED.zone_lib, motif = EXCLUDED.motif
        """), m)
    return len(marques)


def au_statut_peremption(session: Session) -> dict:
    """Compteur de PÉREMPTION (exigence Vic 30/07 : « un déclassement temporaire sans date devient
    permanent par oubli »). Renvoie le nombre de parcelles en attente de vérification et depuis
    combien de jours (la plus ancienne + l'âge médian), par classe. Lecture seule."""
    row = session.execute(text("""
        SELECT classe,
               count(*)                                                        AS n,
               floor(EXTRACT(EPOCH FROM (now() - min(computed_at))) / 86400)   AS jours_max,
               floor(percentile_cont(0.5) WITHIN GROUP (
                     ORDER BY EXTRACT(EPOCH FROM (now() - computed_at)) / 86400)) AS jours_median
        FROM parcel_au_statut GROUP BY classe
    """)).mappings().all()
    par_classe = {r["classe"]: {"n": int(r["n"]),
                                "jours_plus_ancien": int(r["jours_max"] or 0),
                                "jours_median": int(r["jours_median"] or 0)} for r in row}
    jours_plus_ancien = max((v["jours_plus_ancien"] for v in par_classe.values()), default=0)
    return {"par_classe": par_classe,
            "total_en_attente": sum(v["n"] for v in par_classe.values()),
            "declassees": par_classe.get(CLASSE_GENERIQUE, {}).get("n", 0),
            "servies_avec_mention": par_classe.get(CLASSE_DIMENSIONS_SEULES, {}).get("n", 0),
            "jours_plus_ancien": jours_plus_ancien,
            "statut": statut_peremption(jours_plus_ancien)}


def declassees_perimees(session: Session, seuil_jours: int = SEUIL_BLOCAGE_JOURS) -> int:
    """Nombre de parcelles DÉCLASSÉES (génériques) dont la marque dépasse `seuil_jours`. C'est le
    compte que la garde de bascule bloque (les dimensions-seules servies ne bloquent pas : elles
    ne sont pas retirées du produit, seulement mentionnées). Lecture seule."""
    return int(session.execute(text("""
        SELECT count(*) FROM parcel_au_statut
        WHERE classe = :g AND now() - computed_at >= make_interval(days => :j)
    """), {"g": CLASSE_GENERIQUE, "j": seuil_jours}).scalar() or 0)


def journalise_peremption_ack(session: Session, *, acked_by: str, n_parcels: int,
                              seuil_jours: int, motif: str) -> None:
    """Trace un contournement `--peremption-ack` (exigence Vic : bavard, pas silencieux — QUI,
    QUAND, COMBIEN, consultable après coup). Un contournement tracé reste un contournement."""
    session.execute(text(
        "CREATE TABLE IF NOT EXISTS au_statut_ack_journal ("
        " id serial PRIMARY KEY, acked_by text NOT NULL, acked_at timestamptz NOT NULL DEFAULT now(),"
        " n_parcels integer NOT NULL, seuil_jours integer NOT NULL, motif text NOT NULL)"))
    session.execute(text(
        "INSERT INTO au_statut_ack_journal (acked_by, n_parcels, seuil_jours, motif) "
        "VALUES (:by, :n, :j, :m)"),
        {"by": acked_by, "n": n_parcels, "j": seuil_jours, "m": motif})
