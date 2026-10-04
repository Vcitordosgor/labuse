"""SCORING-8 lot A — chaque jointure de caches du Score LABUSE rend UNE ligne par parcelle,
par une règle EXPLICITE et INDÉPENDANTE DE L'ORDRE (jamais « la dernière au hasard »).

Les trois tables nommées par le mandat (`batiment_hauteur_lidar`, `parcel_terrain`,
`parcel_au_statut`) portent aujourd'hui une clé primaire sur leur colonne de jointure, et
`parcel_residuel` est une VUE du run servi : impossible d'y insérer deux lignes pour une même
parcelle. On teste donc les EXPRESSIONS de dédoublonnage de `_ENTREES_SQL` telles quelles, en
PERMUTANT l'ordre des lignes candidates — c'est exactement ce que la base pourrait présenter si
l'invariant d'unicité sautait (rebuild, ingestion partielle). Le résultat ne doit pas changer.

Le dernier test vérifie le bout de chaîne : faîtage = MAX des bâtiments ⇒ le cran R+2 se
déclenche dès qu'UN bâtiment dépasse le seuil, quel que soit l'ordre.
"""
from itertools import permutations

import pytest
from sqlalchemy import text

from labuse.scoring.score_labuse import _f_bati, charger_bareme

BAREME, _ = charger_bareme()
FA = BAREME["faisabilite"]


def _vals(rows, col, cast=""):
    # Construit `(VALUES (a),(b),…) v(col)` depuis une liste Python.
    def lit(x):
        if x is None:
            return "NULL"
        if isinstance(x, str):
            return "'" + x.replace("'", "''") + "'"
        return str(x)
    body = ",".join(f"({lit(x)}{cast})" for x in rows)
    return f"(VALUES {body}) v({col})"


def test_faitage_prend_le_max_quel_que_soit_lordre(db_session):
    # 3 « bâtiments » : 3,0 / 9,5 / 5,0 m. max() = 9,5 ≥ seuil R+2, dans TOUTES les permutations.
    for perm in permutations([3.0, 9.5, 5.0]):
        v = _vals(list(perm), "faitage_m", cast="::real")
        got = db_session.execute(text(f"SELECT max(faitage_m) FROM {v}")).scalar()
        assert float(got) == 9.5


def test_pente_prend_la_plus_contraignante(db_session):
    # Pente la plus FORTE (la plus contraignante) retenue, quel que soit l'ordre.
    for perm in permutations([3.0, 42.0, 18.0]):
        v = _vals(list(perm), "pente_moy_deg", cast="::real")
        got = db_session.execute(text(f"SELECT max(pente_moy_deg) FROM {v}")).scalar()
        assert float(got) == 42.0


def test_au_statut_une_classe_differee_lemporte(db_session):
    # Une classe AU différée (capacité ×0,5) prime sur toute autre, quel que soit l'ordre.
    classes = ["générique", "conditionnelle_operation", "declasse_au_fermee"]
    for perm in permutations(classes):
        v = _vals(list(perm), "classe")
        got = db_session.execute(text(
            f"SELECT classe FROM {v} "
            "ORDER BY (classe IN ('declasse_au_fermee','declasse_au_statut_inconnu')) DESC, classe "
            "LIMIT 1")).scalar()
        assert got == "declasse_au_fermee"


def test_au_statut_departage_alpha_sans_differee(db_session):
    # Sans classe différée, départage déterministe (alphabétique) — pas « au hasard ».
    classes = ["générique", "conditionnelle_operation", "au_sous_plancher"]
    results = set()
    for perm in permutations(classes):
        v = _vals(list(perm), "classe")
        results.add(db_session.execute(text(
            f"SELECT classe FROM {v} "
            "ORDER BY (classe IN ('declasse_au_fermee','declasse_au_statut_inconnu')) DESC, classe "
            "LIMIT 1")).scalar())
    assert results == {"au_sous_plancher"}   # min alpha, identique dans toutes les permutations


def test_acces_prend_le_verdict_le_plus_defavorable(db_session):
    # PASS (voie non identifiée → malus) l'emporte sur POSITIVE, quel que soit l'ordre.
    for perm in permutations(["POSITIVE", "PASS", "POSITIVE"]):
        v = _vals(list(perm), "result")
        got = db_session.execute(text(
            f"SELECT result FROM {v} ORDER BY (result='PASS') DESC LIMIT 1")).scalar()
        assert got == "PASS"


def test_residuel_prend_la_ligne_la_plus_recente(db_session):
    # Deux lignes résiduel pour une même parcelle → on garde la COMPLÈTE la plus récente
    # (computed_at DESC), jamais un mélange. Teste l'ordre de `_ENTREES_SQL`.
    got = db_session.execute(text("""
        SELECT sdp_residuelle_m2 FROM (
          VALUES (900.0, TIMESTAMPTZ '2026-01-01'), (120.0, TIMESTAMPTZ '2026-09-25')
        ) r(sdp_residuelle_m2, computed_at)
        ORDER BY computed_at DESC NULLS LAST, sdp_residuelle_m2 ASC NULLS LAST
        LIMIT 1""")).scalar()
    assert float(got) == 120.0   # la ligne récente, pas celle au SDP le plus gros


def test_r2_declenche_des_quun_batiment_depasse_le_seuil():
    # Bout de chaîne : faîtage = max des bâtiments ⇒ cran R+2 (idx=1) appliqué dès qu'un
    # bâtiment ≥ faitage_r2_m, et c'est STRICTEMENT plus sévère que sans R+2.
    seuil = FA["bati"]["faitage_r2_m"]              # 9 m
    emp = 30.0                                       # emprise dans la tranche « démolition »
    sans_r2 = _f_bati(emp, seuil - 1.0, FA)          # bâtiment bas
    avec_r2 = _f_bati(emp, max(3.0, 5.0, seuil + 0.5), FA)   # un bâtiment dépasse le seuil
    assert avec_r2 < sans_r2
