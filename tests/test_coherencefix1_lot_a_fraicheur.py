"""COHERENCE-FIX-1 (lot A) — la fraîcheur des caches : une clé, un geste, un contrôle.

- l'empreinte attendue porte TOUTES les dépendances (run servi, cascade, résiduel servi,
  millésimes des sources, version du code) et bouge quand l'une bouge ;
- le prédicat de péremption des tuiles est UNIQUE (`tiles.tuiles_etat`) et attrape les trois
  causes : run ≠ servi, résiduel ≠ servi (la clé, pas les dates), amont recalculé ;
- `labuse rebuild --dry-run` (fumée du déploiement) échoue si un cache est périmé — testé au
  niveau de `fraicheur_caches.etat` (la commande n'en est qu'un mince appelant).
"""
from __future__ import annotations

from labuse import fraicheur_caches, runs


def test_empreinte_bouge_avec_le_run(monkeypatch):
    monkeypatch.setattr(runs, "current", lambda: "q_run_a")
    monkeypatch.setattr(runs, "cascade", lambda: "q_run_a")
    monkeypatch.setattr(fraicheur_caches, "residuel_seq_servi", lambda db: 10)
    monkeypatch.setattr(fraicheur_caches, "millesimes_hash", lambda db: "m1")
    monkeypatch.setattr(fraicheur_caches, "code_sha", lambda: "abc")
    a = fraicheur_caches.empreinte_attendue(None)
    monkeypatch.setattr(runs, "current", lambda: "q_run_b")
    b = fraicheur_caches.empreinte_attendue(None)
    assert a != b and "q_run_a" in a and "q_run_b" in b


def test_empreinte_bouge_avec_le_residuel_les_sources_et_le_code(monkeypatch):
    monkeypatch.setattr(runs, "current", lambda: "q")
    monkeypatch.setattr(runs, "cascade", lambda: "q")
    monkeypatch.setattr(fraicheur_caches, "residuel_seq_servi", lambda db: 10)
    monkeypatch.setattr(fraicheur_caches, "millesimes_hash", lambda db: "m1")
    monkeypatch.setattr(fraicheur_caches, "code_sha", lambda: "abc")
    base = fraicheur_caches.empreinte_attendue(None)
    monkeypatch.setattr(fraicheur_caches, "residuel_seq_servi", lambda db: 11)
    assert fraicheur_caches.empreinte_attendue(None) != base, "residuel-serve doit invalider"
    monkeypatch.setattr(fraicheur_caches, "residuel_seq_servi", lambda db: 10)
    monkeypatch.setattr(fraicheur_caches, "millesimes_hash", lambda db: "m2")
    assert fraicheur_caches.empreinte_attendue(None) != base, "un millésime doit invalider"
    monkeypatch.setattr(fraicheur_caches, "millesimes_hash", lambda db: "m1")
    monkeypatch.setattr(fraicheur_caches, "code_sha", lambda: "def")
    assert fraicheur_caches.empreinte_attendue(None) != base, "un déploiement doit invalider"
    monkeypatch.setattr(fraicheur_caches, "code_sha", lambda: "abc")
    assert fraicheur_caches.empreinte_attendue(None) == base, "rien n'a bougé → même clé"


def test_code_sha_ne_crashe_jamais():
    sha = fraicheur_caches.code_sha()
    assert isinstance(sha, str) and sha, "toujours une valeur (git / deploiement.json / 'inconnu')"


class _FakeDB:
    """Assez de SQLAlchemy pour tuiles_etat : execute(...).scalar()/.mappings().first()."""

    def __init__(self, reponses):
        self.reponses = reponses      # fragment de SQL → valeur

    def execute(self, clause, *a, **k):
        sql = str(clause)
        for frag, val in self.reponses.items():
            if frag in sql:
                return _Res(val)
        return _Res(None)


class _Res:
    def __init__(self, val):
        self.val = val

    def scalar(self):
        return self.val

    def mappings(self):
        return self

    def first(self):
        return self.val


def _db_tuiles(run_carte, seq_carte, run_servi_dt, amont=None):
    import datetime
    carte_le = datetime.datetime(2026, 9, 20, tzinfo=datetime.timezone.utc)
    return _FakeDB({
        "to_regclass('mvt_meta')": True,
        "key = 'run_label'": {"value": run_carte, "updated_at": carte_le},
        "key = 'residuel_seq'": seq_carte,
        "parcel_p_score_v2": run_servi_dt,
        "parcel_residuel": amont,
    })


def test_tuiles_etat_perime_si_run_different(monkeypatch):
    from labuse.api import tiles
    monkeypatch.setattr(runs, "current", lambda: "q_nouveau")
    monkeypatch.setattr(fraicheur_caches, "residuel_seq_servi", lambda db: 10)
    et = tiles.tuiles_etat(_db_tuiles("q_ancien", "10", None))
    assert et["perime"] and et["motif"] == "run"


def test_tuiles_etat_perime_si_residuel_servi_a_bouge_sans_les_dates(monkeypatch):
    """Le cas que les DATES ne voient pas : residuel-serve vers un run aux computed_at ANCIENS.
    La clé (seq au build ≠ seq servi) l'attrape — c'est la raison d'être du stamp residuel_seq."""
    from labuse.api import tiles
    monkeypatch.setattr(runs, "current", lambda: "q_v11_m137")
    monkeypatch.setattr(fraicheur_caches, "residuel_seq_servi", lambda db: 8)
    et = tiles.tuiles_etat(_db_tuiles("q_v11_m137", "10", None))
    assert et["perime"] and et["motif"] == "residuel"
    assert "seq 10" in et["motif_detail"] and "seq 8" in et["motif_detail"]


def test_tuiles_etat_a_jour(monkeypatch):
    from labuse.api import tiles
    monkeypatch.setattr(runs, "current", lambda: "q_v11_m137")
    monkeypatch.setattr(fraicheur_caches, "residuel_seq_servi", lambda db: 10)
    et = tiles.tuiles_etat(_db_tuiles("q_v11_m137", "10", None))
    assert not et["perime"] and et["motif"] is None


def test_tuiles_etat_perime_si_amont_recalcule(monkeypatch):
    import datetime
    from labuse.api import tiles
    monkeypatch.setattr(runs, "current", lambda: "q_v11_m137")
    monkeypatch.setattr(fraicheur_caches, "residuel_seq_servi", lambda db: 10)
    apres = datetime.datetime(2026, 9, 25, tzinfo=datetime.timezone.utc)
    et = tiles.tuiles_etat(_db_tuiles("q_v11_m137", "10", None, amont=apres))
    assert et["perime"] and et["motif"] == "amont"


def test_etat_liste_les_perimes(monkeypatch):
    """`etat()` agrège : la liste `perimes` alimente le --dry-run (exit 1) et la page Données."""
    monkeypatch.setattr(fraicheur_caches, "empreinte_attendue", lambda db: "E")
    monkeypatch.setattr(fraicheur_caches, "empreinte_courte", lambda db: "e")
    monkeypatch.setattr(fraicheur_caches, "_etat_commune_cache",
                        lambda db, a: {"cache": "commune_contexte_cache", "perime": True})
    monkeypatch.setattr(fraicheur_caches, "_etat_tuiles",
                        lambda db: {"cache": "mvt_parcels (tuiles carte)", "perime": False})
    monkeypatch.setattr(fraicheur_caches, "_etat_tile_cache",
                        lambda db: {"cache": "mvt_tile_cache", "perime": False})
    monkeypatch.setattr(fraicheur_caches, "_etat_spatial_sub",
                        lambda db: {"cache": "spatial_layers_sub", "perime": False})
    monkeypatch.setattr(fraicheur_caches, "_etat_ia_cache",
                        lambda db, c: {"cache": "ia_cache", "perime": False})
    # PRE-DEPLOY-1 (lot C/D) — deux contrôles ajoutés : manifeste (bloquant si menteur) + intersections
    # (informatif, jamais bloquant). Ici les deux sont « à jour » : la liste des périmés ne change pas.
    monkeypatch.setattr(fraicheur_caches, "_etat_manifeste",
                        lambda db: {"cache": "served_manifest.json (pointeur servi)", "perime": False})
    monkeypatch.setattr(fraicheur_caches, "_etat_intersections",
                        lambda db: {"cache": "parcel_couche_intersection (servitudes)", "perime": False})
    # CALCULS-FIX-1 (lot C) — contrôle ajouté : barème de défiscalisation (config millésimée). Ici
    # « à jour » (le geste annuel est fait) → la liste des périmés ne change pas. Monkeypatché pour
    # rester déterministe quelle que soit l'année de la CI (sinon il périmerait au 1er janvier suivant).
    monkeypatch.setattr(fraicheur_caches, "_etat_defisc_bareme",
                        lambda: {"cache": "barème défiscalisation (config millésimée)", "perime": False})
    e = fraicheur_caches.etat(None)
    assert e["perimes"] == ["commune_contexte_cache"]
    assert len(e["caches"]) == 8


# ── PRE-DEPLOY-1 (lot C) — le manifeste ne peut plus mentir ──────────────────────────────────

class _DBManifeste:
    """Assez de SQLAlchemy pour _etat_manifeste : is_served + existence d'un run_seq."""

    def __init__(self, is_served, runs_presents):
        self.is_served = is_served          # seq servi (residuel_runs.is_served)
        self.runs_presents = set(runs_presents)
        self._params = None

    def execute(self, clause, params=None):
        self._sql, self._params = str(clause), params or {}
        return self

    def scalar(self):
        if "is_served" in self._sql:
            return self.is_served
        if "run_seq = :s" in self._sql:
            return 1 if self._params.get("s") in self.runs_presents else None
        return None


def test_manifeste_menteur_est_perime(monkeypatch):
    """Le bug fondateur (7ae2c2b7) : manifeste seq 8 alors que is_served = 10, LES DEUX présents en
    base → PÉRIMÉ (rouge page Données, échec `rebuild --dry-run`, échec V6b)."""
    from labuse import manifeste
    monkeypatch.setattr(manifeste, "lire", lambda: {
        "scoring_run": "q_v11_m137", "residuel_run_seq": 8,
        "mvt_run": "q_v11_m137", "division_run": "q_v11_m137"})
    monkeypatch.setattr(runs, "_lire_fichier", lambda: "q_v11_m137")   # scoring aligné
    r = fraicheur_caches._etat_manifeste(_DBManifeste(is_served=10, runs_presents={8, 10}))
    assert r["perime"], "manifeste seq 8 ≠ is_served 10 doit être périmé"
    assert "8" in r["detail"] and "10" in r["detail"]


def test_manifeste_aligne_nest_pas_perime(monkeypatch):
    """Manifeste = servi en base (seq 10 == is_served 10, scoring == served_run.txt) → à jour."""
    from labuse import manifeste
    monkeypatch.setattr(manifeste, "lire", lambda: {
        "scoring_run": "q_v11_m137", "residuel_run_seq": 10,
        "mvt_run": "q_v11_m137", "division_run": "q_v11_m137"})
    monkeypatch.setattr(runs, "_lire_fichier", lambda: "q_v11_m137")
    r = fraicheur_caches._etat_manifeste(_DBManifeste(is_served=10, runs_presents={8, 10}))
    assert not r["perime"]


def test_manifeste_run_absent_ne_crie_pas(monkeypatch):
    """Base de test/dev : le manifeste pointe un run de prod absent de cette base → on ne compare
    pas (rien à comparer), jamais un faux positif qui casserait la suite sur une petite base."""
    from labuse import manifeste
    monkeypatch.setattr(manifeste, "lire", lambda: {
        "scoring_run": "q_v11_m137", "residuel_run_seq": 999,
        "mvt_run": "q_v11_m137", "division_run": "q_v11_m137"})
    monkeypatch.setattr(runs, "_lire_fichier", lambda: "q_v11_m137")
    r = fraicheur_caches._etat_manifeste(_DBManifeste(is_served=1, runs_presents={1, 2}))
    assert not r["perime"]


def test_manifeste_absent_est_perime(monkeypatch):
    """Aucun manifeste posé = le run servi n'est pas traçable → périmé (fumée du déploiement)."""
    from labuse import manifeste
    monkeypatch.setattr(manifeste, "lire", lambda: None)
    r = fraicheur_caches._etat_manifeste(_DBManifeste(is_served=10, runs_presents={10}))
    assert r["perime"] and "absent" in r["detail"].lower()
