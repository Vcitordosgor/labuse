"""fix/saint-leu-1 — la cascade ne bloque plus en tissu dense (Saint-Leu).

DEUX correctifs, tous deux à RÉSULTAT IDENTIQUE (vérifié hors-test sur 500 parcelles Saint-Leu :
0 écart de score/statut, 23 549 verdicts identiques), qui SUPPRIMENT le coût dominant mesuré :

  1. `cascade_intersection_kinds` — le prime() spatial ne calcule l'intersection QUE des kinds
     réellement lus par `ctx.intersections()` (YAML ∪ littéraux du code). Les kinds présents en base
     mais jamais lus (batiment_cosia ~37 k pièces/Saint-Leu, piscine_cosia, transport_*…) ne paient
     plus d'intersection pour rien.
  2. `union_coverage` / `union_coverage_interdit` — le `ST_Area(ST_Union(ST_Intersection(...)))` PAR
     PARCELLE (couverture PPR rouge unionnée) lit le cache SUBDIVISÉ `spatial_layers_sub` quand il
     existe (pièces ≤256 sommets + GiST) au lieu de la géométrie BRUTE (PPR/aléa jusqu'à ~221 906
     sommets). C'était 96 s sur 97 s de cascade pour 100 parcelles Saint-Leu (~87 % multi-rouges ×
     ~1,1 s/appel) → ~6 ms/appel. Repli sur la géométrie brute si le cache est absent.

Tests PURS (sans base) : la fidélité des aires est garantie par la subdivision (partition exacte)
et vérifiée en recette ; ici on verrouille le CÂBLAGE (quels kinds, quelle table lue).
"""
from __future__ import annotations

from labuse.cascade.cablage import cascade_intersection_kinds
from labuse.cascade.context import EvalContext


# ─────────────────────────── 1. allowlist des kinds du prime() ───────────────────────────

def test_cascade_intersection_kinds_capte_yaml_et_litteraux():
    kinds = cascade_intersection_kinds()
    # kinds lus via `intersections()` et portés par le YAML (spatial_kind) :
    for k in ("ppr", "sup", "plu_gpu_zone", "georisque_alea", "mvt"):
        assert k in kinds, f"{k} doit rester dans l'allowlist (lu par la cascade)"
    # LITTÉRAL dans le code (phase1 : `ctx.intersections(parcel.id, "pente")`), ABSENT du YAML :
    # s'il tombait de l'allowlist, la couche pente ne verrait plus aucune intersection.
    assert "pente" in kinds, "le kind littéral 'pente' doit être capté depuis le code des couches"


def test_cascade_intersection_kinds_exclut_les_kinds_hors_cascade():
    kinds = cascade_intersection_kinds()
    # Présents en base, JAMAIS lus par `intersections()` — les plus DENSES en ville ; les exclure du
    # prime() est une partie du gain Saint-Leu (et ne change aucun verdict : personne ne les lit).
    for k in ("batiment_cosia", "piscine_cosia", "transport_arret", "iris_insee", "artificialisation"):
        assert k not in kinds, f"{k} n'est lu par aucune couche — il ne doit pas être intersecté"


# ─────────────────────── 2. union_coverage lit le cache subdivisé ───────────────────────

class _Rec:
    def __init__(self, val):
        self.val = val

    def scalar(self):
        return self.val

    def first(self):
        return self.val


class _StubSession:
    """Session minimale : enregistre le SQL, répond au `to_regclass` (présence du cache) et rend une
    aire unionnée fixe (100) sur une parcelle de 200 m² → fraction 0,5."""

    def __init__(self, sub_present: bool):
        self.sub_present = sub_present
        self.sqls: list[str] = []

    def execute(self, stmt, params=None):
        sql = str(getattr(stmt, "text", stmt))
        self.sqls.append(sql)
        if "to_regclass" in sql:
            return _Rec(self.sub_present)
        return _Rec((100.0, 200.0))

    def _union_sql(self) -> str:
        return next(q for q in self.sqls if "ST_Union" in q)


def test_union_coverage_interdit_lit_le_cache_subdivise_si_present():
    s = _StubSession(sub_present=True)
    frac, area = EvalContext(s).union_coverage_interdit(1, "ppr")
    assert (frac, area) == (0.5, 100.0)
    q = s._union_sql()
    assert "spatial_layers_sub" in q          # le cache subdivisé, pas la géométrie brute
    assert "z.g" in q and "&&" in q           # intersection sur les pièces + bbox (GiST)


def test_union_coverage_interdit_repli_sur_geometrie_brute_si_cache_absent():
    s = _StubSession(sub_present=False)
    frac, area = EvalContext(s).union_coverage_interdit(1, "ppr")
    assert (frac, area) == (0.5, 100.0)        # résultat identique
    q = s._union_sql()
    assert "spatial_layers_sub" not in q
    assert "z.geom_2975" in q                  # repli sur la géométrie entière


def test_union_coverage_subtypes_route_aussi_vers_le_cache():
    s = _StubSession(sub_present=True)
    frac, _ = EvalContext(s).union_coverage(1, "ppr", ["ROUGE", "R"])
    assert frac == 0.5
    assert "spatial_layers_sub" in s._union_sql()


def test_presence_cache_memoisee_un_seul_to_regclass():
    """`_spatial_sub_present` ne doit interroger `to_regclass` qu'UNE fois par contexte."""
    s = _StubSession(sub_present=True)
    ctx = EvalContext(s)
    ctx.union_coverage_interdit(1, "ppr")
    ctx.union_coverage_interdit(2, "ppr")
    assert sum("to_regclass" in q for q in s.sqls) == 1
