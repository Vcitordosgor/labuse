"""Dette #9 fermée en SIGNAL (arbitrage Vic 05/08) — cache `parcel_entree_tete`.

Pour chaque parcelle ACTUELLEMENT en tête (brûlante/chaude du run servi), la dernière ENTRÉE
en tête tracée par la chaîne d'archives de bascule, avec sa nature :
  - « signal inchangé » (héritage de place : contrib_d identique — seul le seuil a bougé)
  - « signal en progression » (mérite : contrib_d en hausse)
Libellé FICTUEL, sans jugement (arbitrage). AUCUN effet de classement — fiche seulement.
Sourcé : contrib_d + rang persistés par run (archives de bascule). Une parcelle entrée avant
la première archive connue n'a PAS de signal (absence honnête, jamais inventé).
À recalculer AU GESTE de chaque bascule (comparaison à l'archive du geste).
"""
from __future__ import annotations

from sqlalchemy import text

#: chaîne chronologique des gestes archivés : (archive_avant, run_apres, date, libellé geste)
CHAINE_GESTES = [
    ("q_v8_calibre_pre_pond",  "q_v8_calibre_pre_regle", "2026-08-04", "pondération AU"),
    ("q_v8_calibre_pre_regle", "q_v8_calibre_pre_m28",   "2026-08-04", "règle bâtie révélée"),
    ("q_v8_calibre_pre_m28",   "q_v8_calibre",           "2026-08-05", "filtre bâti + départage (M28)"),
]
EPS = 1e-9


def build_parcel_entree_tete(session, run_servi: str = "q_v8_calibre") -> dict:
    """(Re)peuple `parcel_entree_tete` : dernière entrée en tête par parcelle de la tête
    ACTUELLE, datée et qualifiée. Idempotent."""
    session.execute(text("""
        CREATE TABLE IF NOT EXISTS parcel_entree_tete (
          idu varchar(14) PRIMARY KEY,
          entree_le date NOT NULL,
          geste text NOT NULL,
          nature varchar(24) NOT NULL,     -- 'signal_inchange' | 'signal_en_progression'
          contrib_d_avant double precision,
          contrib_d_apres double precision,
          computed_at timestamptz NOT NULL DEFAULT now())"""))
    session.execute(text("TRUNCATE parcel_entree_tete"))
    for avant, apres, date_g, geste in CHAINE_GESTES:
        # entrants de CE geste, encore en tête du run servi aujourd'hui → upsert (le geste le
        # plus récent gagne : la chaîne est parcourue dans l'ordre chronologique).
        session.execute(text(f"""
            INSERT INTO parcel_entree_tete (idu, entree_le, geste, nature,
                                            contrib_d_avant, contrib_d_apres)
            SELECT b.parcelle_id, :d, :g,
                   CASE WHEN b.contrib_d > a.contrib_d + {EPS}
                        THEN 'signal_en_progression' ELSE 'signal_inchange' END,
                   a.contrib_d, b.contrib_d
            FROM parcel_p_score_v2 b
            JOIN parcel_p_score_v2 a ON a.parcelle_id = b.parcelle_id AND a.run_id = :avant
            JOIN parcel_p_score_v2 srv ON srv.parcelle_id = b.parcelle_id AND srv.run_id = :servi
            WHERE b.run_id = :apres
              AND b.tier IN ('brulante','chaude') AND a.tier NOT IN ('brulante','chaude')
              AND srv.tier IN ('brulante','chaude')
            ON CONFLICT (idu) DO UPDATE SET entree_le=EXCLUDED.entree_le, geste=EXCLUDED.geste,
              nature=EXCLUDED.nature, contrib_d_avant=EXCLUDED.contrib_d_avant,
              contrib_d_apres=EXCLUDED.contrib_d_apres, computed_at=now()"""),
            {"d": date_g, "g": geste, "avant": avant, "apres": apres, "servi": run_servi})
    n = dict(session.execute(text(
        "SELECT nature, count(*) FROM parcel_entree_tete GROUP BY nature")).all())
    return {"inchange": n.get("signal_inchange", 0), "progression": n.get("signal_en_progression", 0)}


def build_parcel_acquerabilite(session) -> dict:
    """Dette #11 fermée en SIGNAL (arbitrage Vic 05/08) — cache `parcel_acquerabilite` pour
    les au_sous_plancher à voisine(s) contiguë(s) de même zone. Libellés FACTUELS arbitrés :
    'meme_proprietaire_pm' / 'proprietaires_distincts_pm' / 'propriete_non_determinable'.
    Millésime amont : champ prévu ; sync DGFiP non tracée → étiquette Estimé (spec millésime
    en attente). Part PP : dette maintenue (source inexistante en open data)."""
    session.execute(text("""
        CREATE TABLE IF NOT EXISTS parcel_acquerabilite (
          idu varchar(14) PRIMARY KEY,
          classe varchar(32) NOT NULL,
          n_meme_siren int NOT NULL, n_siren_distincts int NOT NULL, n_indetermine int NOT NULL,
          source text NOT NULL DEFAULT 'DGFiP / Cerema (fichiers fonciers, via ODS Région)',
          source_millesime text,            -- NULL tant que la sync amont n'est pas tracée
          etiquette varchar(8) NOT NULL DEFAULT 'Estimé',
          computed_at timestamptz NOT NULL DEFAULT now())"""))
    session.execute(text("TRUNCATE parcel_acquerabilite"))
    session.execute(text("""
        INSERT INTO parcel_acquerabilite (idu, classe, n_meme_siren, n_siren_distincts, n_indetermine)
        WITH sp AS (SELECT a.idu, a.zone_lib, p.geom_2975 g
          FROM parcel_au_statut a JOIN parcels p ON p.id=a.parcel_id
          WHERE a.classe='au_sous_plancher')
        SELECT sp.idu,
          CASE WHEN count(*) FILTER (WHERE pmv.siren IS NOT NULL AND pms.siren IS NOT NULL
                                       AND pmv.siren=pms.siren) > 0 THEN 'meme_proprietaire_pm'
               WHEN count(*) FILTER (WHERE pmv.siren IS NOT NULL AND pms.siren IS NOT NULL
                                       AND pmv.siren<>pms.siren) > 0 THEN 'proprietaires_distincts_pm'
               ELSE 'propriete_non_determinable' END,
          count(*) FILTER (WHERE pmv.siren IS NOT NULL AND pms.siren IS NOT NULL AND pmv.siren=pms.siren),
          count(*) FILTER (WHERE pmv.siren IS NOT NULL AND pms.siren IS NOT NULL AND pmv.siren<>pms.siren),
          count(*) FILTER (WHERE pmv.siren IS NULL OR pms.siren IS NULL)
        FROM sp
        JOIN parcel_zone_plu vz ON vz.zone_lib=sp.zone_lib
        JOIN parcels v ON v.idu=vz.idu AND v.idu<>sp.idu
          AND ST_Length(ST_CollectionExtract(ST_Intersection(v.geom_2975, sp.g),2)) >= 3.0
        LEFT JOIN (SELECT DISTINCT ON (idu) idu, siren FROM parcelle_personne_morale) pmv ON pmv.idu=v.idu
        LEFT JOIN (SELECT DISTINCT ON (idu) idu, siren FROM parcelle_personne_morale) pms ON pms.idu=sp.idu
        GROUP BY sp.idu"""))
    n = dict(session.execute(text(
        "SELECT classe, count(*) FROM parcel_acquerabilite GROUP BY classe")).all())
    return n
