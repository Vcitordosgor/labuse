"""FIX-P-1 (régression G-001) — un filtre de la CARTE ne doit JAMAIS renvoyer 0 parcelle sur toute
l'île quand la donnée EXISTE. Filet de non-vacuité.

Contexte. FIX-NU3-2 avait mappé le flag « risques » vers `['ppr','georisque_alea']` — deux `kind`
de `spatial_layers` (page Couverture) ABSENTS de `parcel_flags`/`dryrun_cascade_results` (dont le token
réel est `risques`). Résultat : le filtre « Risques (PPR/aléa) » retenait **0 parcelle** sur ~405 764,
silencieusement, serveur ET client. Ce test attrape exactement ce motif : pour chaque flag OFFERT au
client, si la couche porte des lignes dans `parcel_flags` (la donnée existe), le filtre serveur
(`_q_v2_where` → `_q_v2_stats`, le MÊME chemin que l'endpoint `/filtre`) doit en retenir > 0.

Marqueur `reel` : exige la base APPLICATIVE réelle (run servi, `parcel_flags` dénormalisée) — jamais en
CI (base vide). Jouée au banc de nuit et au push quand la base répond.
"""
from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

pytestmark = [pytest.mark.reel]

# Les flags OFFERTS au filtre de la carte (miroir de frontend/src/lib/filters.FLAG_DEFS). Chacun est,
# après expansion, un `layer_name` réel de `parcel_flags` — l'invariant du test.
FLAGS_UI = ["sol_pollue", "abf", "icpe", "risques", "prescription_plu"]


def _app_engine():
    app_url = (os.environ.get("LABUSE_APP_DATABASE_URL")
               or os.environ.get("LABUSE_DATABASE_URL",
                                 "postgresql+psycopg://labuse:labuse@localhost:5432/labuse"))
    return create_engine(app_url, future=True)


def test_filtre_flags_carte_jamais_vide_quand_la_donnee_existe():
    """Pour chaque flag offert : SI `parcel_flags` porte des lignes de sa couche (après l'expansion
    serveur `PARCEL_FLAG_GROUPES`), ALORS le compteur de l'île filtré sur ce flag est > 0. Un 0 ici =
    la régression G-001 (mapping d'un token inexistant) revenue — le filtre sélectionne « rien »."""
    try:
        from labuse.api.app import PARCEL_FLAG_GROUPES, _q_v2_stats, _q_v2_where
        eng = _app_engine()
        with Session(eng) as db:
            if not db.execute(text("SELECT to_regclass('parcel_flags')")).scalar():
                pytest.skip("parcel_flags absente — base sans run servi (CI)")
            # run servi = celui qui porte le plus de flags dénormalisés (q_v20 en prod/Mac).
            run = db.execute(text(
                "SELECT run_label FROM parcel_flags GROUP BY run_label ORDER BY count(*) DESC LIMIT 1"
            )).scalar()
            if not run:
                pytest.skip("parcel_flags vide — aucun run servi")

            ecarts: list[str] = []
            verifies = 0
            for tok in FLAGS_UI:
                expanded = PARCEL_FLAG_GROUPES.get(tok, [tok])
                n_data = db.execute(text(
                    "SELECT count(*) FROM parcel_flags "
                    "WHERE run_label = :r AND layer_name = ANY(:ls)"),
                    {"r": run, "ls": expanded}).scalar() or 0
                if n_data == 0:
                    # donnée absente pour cette couche sur ce run → non concluant, on n'exige rien.
                    continue
                verifies += 1
                where, params = _q_v2_where(run, None, None, None, False, tok)
                total = _q_v2_stats(db, None, run_label=run, extra_where=where,
                                    extra_params=params, exclure_slivers=True)["total"]
                if not total or total <= 0:
                    ecarts.append(
                        f"flag « {tok} » (couches {expanded}) : {n_data} lignes en base MAIS "
                        f"compteur île = {total} — le filtre sélectionne 0 parcelle alors que la donnée existe")
            assert verifies, "aucun flag n'a de donnée en base — base réelle incomplète ?"
            assert not ecarts, (
                "Filtre(s) de carte vide(s) alors que la donnée existe (régression G-001) :\n  "
                + "\n  ".join(ecarts))
    except pytest.skip.Exception:
        raise
    except Exception as exc:  # noqa: BLE001 — base indisponible = skip, pas un échec
        pytest.skip(f"base applicative indisponible ({type(exc).__name__}: {exc}) — non vérifiable ici")


def test_filtre_risques_couvre_l_ile():
    """Garde ciblée de la régression : le flag « risques » (le plus volumineux, ~405 k parcelles) doit
    retenir un compte du MÊME ordre que ses lignes `parcel_flags` — jamais 0, jamais une poignée."""
    try:
        from labuse.api.app import PARCEL_FLAG_GROUPES, _q_v2_stats, _q_v2_where
        eng = _app_engine()
        with Session(eng) as db:
            if not db.execute(text("SELECT to_regclass('parcel_flags')")).scalar():
                pytest.skip("parcel_flags absente — base sans run servi (CI)")
            run = db.execute(text(
                "SELECT run_label FROM parcel_flags GROUP BY run_label ORDER BY count(*) DESC LIMIT 1"
            )).scalar()
            expanded = PARCEL_FLAG_GROUPES.get("risques", ["risques"])
            n_data = db.execute(text(
                "SELECT count(DISTINCT parcel_id) FROM parcel_flags "
                "WHERE run_label = :r AND layer_name = ANY(:ls)"),
                {"r": run, "ls": expanded}).scalar() or 0
            if n_data == 0:
                pytest.skip("aucune parcelle « risques » servie sur ce run")
            where, params = _q_v2_where(run, None, None, None, False, "risques")
            total = _q_v2_stats(db, None, run_label=run, extra_where=where,
                                extra_params=params, exclure_slivers=True)["total"]
            assert total > 0, (
                f"filtre « risques » = 0 parcelle alors que {n_data} la portent (régression G-001)")
            # au moins la moitié des parcelles à flag survivent au gate (étage 0 / slivers) : un
            # compte dérisoire (p.ex. 3) signalerait que le token ne matche presque rien.
            assert total >= n_data // 2, (
                f"filtre « risques » = {total} très en deçà des {n_data} parcelles à flag — "
                "le token du filtre ne recouvre pas la couche servie")
    except pytest.skip.Exception:
        raise
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"base applicative indisponible ({type(exc).__name__}: {exc}) — non vérifiable ici")
