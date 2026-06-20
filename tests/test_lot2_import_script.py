"""Sécurité du script LOT 2 (scripts/lot2_import_saint_paul.py) — JAMAIS d'exécution réelle ici.

On vérifie statiquement et par injection que le script est sûr par défaut : dry-run, double
garde-fou pour l'exécution réelle, refus si backup absent / état inattendu, commune figée à
Saint-Paul, et aucun accès base en dry-run.
"""
from __future__ import annotations

import importlib.util
import pathlib

_SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "lot2_import_saint_paul.py"


def _load():
    spec = importlib.util.spec_from_file_location("lot2_import_saint_paul", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


lot2 = _load()


# ── Mode par défaut & double garde-fou ──────────────────────────────────────────────────────
def test_dry_run_par_defaut():
    assert lot2.real_mode(lot2.parse_args([])) is False


def test_execution_reelle_exige_execute_ET_confirmation_exacte():
    assert lot2.real_mode(lot2.parse_args(["--execute"])) is False                       # confirm manquant
    assert lot2.real_mode(lot2.parse_args(["--execute", "--confirm", "WRONG"])) is False  # mauvaise phrase
    assert lot2.real_mode(lot2.parse_args(["--confirm", "IMPORT_SAINT_PAUL_COMPLET"])) is False  # --execute manquant
    assert lot2.real_mode(lot2.parse_args(["--execute", "--confirm", "IMPORT_SAINT_PAUL_COMPLET"])) is True


def test_main_refuse_execute_sans_confirmation(capsys):
    # main() refuse AVANT toute connexion base (retour 2) — testable sans DB.
    assert lot2.main(["--execute"]) == 2
    assert lot2.main(["--execute", "--confirm", "PAS_LA_BONNE"]) == 2
    assert "REFUS" in capsys.readouterr().out


# ── Garde-fou backup ────────────────────────────────────────────────────────────────────────
def test_refuse_si_backup_absent():
    ok, msg = lot2.verify_backup("/nimporte/quoi/inexistant.dump")
    assert ok is False and "ABSENT" in msg


def test_backup_checksum(tmp_path):
    import hashlib
    f = tmp_path / "b.dump"
    f.write_bytes(b"contenu de test")
    digest = hashlib.sha256(b"contenu de test").hexdigest()
    # checksum correct → OK
    (tmp_path / "b.dump.sha256").write_text(f"{digest}  b.dump\n")
    ok, msg = lot2.verify_backup(str(f))
    assert ok is True and "checksum vérifié" in msg
    # checksum faux → refus
    (tmp_path / "b.dump.sha256").write_text("0" * 64 + "  b.dump\n")
    ok, msg = lot2.verify_backup(str(f))
    assert ok is False and "NON conforme" in msg


# ── Garde-fou état de départ ────────────────────────────────────────────────────────────────
def test_etat_depart_doit_etre_3000():
    assert lot2.parcels_state_ok(3000) is True
    assert lot2.parcels_state_ok(51129) is False   # déjà importé → on refuse de rejouer
    assert lot2.parcels_state_ok(0) is False
    assert lot2.parcels_state_ok(None) is False


# ── Commune figée : jamais une autre que Saint-Paul ─────────────────────────────────────────
def test_commune_figee_saint_paul():
    assert lot2.COMMUNE == "Saint-Paul"
    assert lot2.INSEE == "97415"
    # aucun argument ne permet de changer de commune
    args = lot2.parse_args([])
    assert not hasattr(args, "commune") and not hasattr(args, "insee")


def test_source_jamais_destructif_sur_parcels_ni_autre_commune():
    src = _SCRIPT.read_text(encoding="utf-8")
    assert "DELETE FROM parcels" not in src           # ne supprime JAMAIS de parcelle
    assert "reset_demo" not in src and "TRUNCATE" not in src and "--reset" not in src
    # les seules suppressions sont des couches SCOPÉES par paramètre commune
    assert src.count("DELETE FROM spatial_layers WHERE commune = :c") == 1
    assert src.count("DELETE FROM dvf_mutations  WHERE commune = :c") == 1
    # aucune autre commune réunionnaise en dur dans une opération
    for autre in ("Saint-Denis", "Le Tampon", "Saint-Pierre", "Saint-Leu"):
        assert autre not in src


# ── Dry-run : AUCUN accès base (les étapes mutantes ne touchent pas la connexion) ────────────
class _Tripwire:
    """Toute utilisation de la connexion lève → prouve qu'en dry-run la base n'est pas touchée."""
    def __getattr__(self, name):
        raise AssertionError(f"accès base INTERDIT en dry-run via .{name}")

    def __call__(self, *a, **k):
        raise AssertionError("appel base INTERDIT en dry-run")


def test_dry_run_ne_touche_pas_la_base():
    tw = _Tripwire()
    # Aucune de ces étapes ne doit accéder à `eng` en dry-run.
    assert lot2.step_import_parcels(tw, dry_run=True) == {"dry_run": True}
    assert lot2.step_layers(tw, dry_run=True, run_id=None) == {"dry_run": True}
    assert lot2.step_cascade(tw, dry_run=True) == {"dry_run": True}


def test_dry_run_n_ecrit_pas_de_rapport(capsys):
    lot2.write_report(dry_run=True, lines=["ne doit pas être écrit"])
    out = capsys.readouterr().out
    assert "DRY-RUN" in out and "non créé" in out
    assert not pathlib.Path(lot2.RESULTS_DOC).exists() or "ne doit pas être écrit" not in \
        pathlib.Path(lot2.RESULTS_DOC).read_text(encoding="utf-8")


# ── #1 Détection stricte des erreurs de couches ─────────────────────────────────────────────
def test_layers_errors_detection():
    counts = {"plu_gpu_zone": 7000, "batiment": "ERREUR Timeout: x", "ppr": 4,
              "abf": "ERREUR HTTPError: 503"}
    assert lot2.layers_errors(counts) == ["abf", "batiment"]
    assert lot2.layers_errors({}) == [] and lot2.layers_errors(None) == []


def test_classify_critique_vs_non_critique():
    crit, noncrit = lot2.classify_layer_failures(["batiment", "abf", "ppr"])
    assert crit == ["batiment"]                       # couche CRITIQUE → rollback
    assert set(noncrit) == {"abf", "ppr"}             # non critiques → re-fetch


# ── #2 Décision finale & code retour ────────────────────────────────────────────────────────
def test_final_decision_succes():
    code, verdict = lot2.final_decision([("x", True, True, "")], [], [], crashed=False)
    assert code == lot2.EXIT_OK and "SUCCÈS" in verdict


def test_final_decision_couche_critique_rollback():
    code, verdict = lot2.final_decision([], ["batiment"], [], crashed=False)
    assert code == lot2.EXIT_ROLLBACK and "ROLLBACK RECOMMANDÉ" in verdict


def test_final_decision_couche_non_critique_refetch():
    code, verdict = lot2.final_decision([], [], ["abf"], crashed=False)
    assert code == lot2.EXIT_REFETCH and "RE-FETCH COUCHE REQUIS" in verdict
    assert code != 0


def test_final_decision_postcheck_critique_ko_non_zero():
    code, verdict = lot2.final_decision([("zonage", False, True, "80 %")], [], [], crashed=False)
    assert code != lot2.EXIT_OK and "ROLLBACK RECOMMANDÉ" in verdict


def test_final_decision_crash():
    code, verdict = lot2.final_decision([], [], [], crashed=True)
    assert code == lot2.EXIT_ROLLBACK and "ROLLBACK LOT 1 À ENVISAGER" in verdict


# ── #3 Conservation pipeline / feedback / alertes réellement comparée ───────────────────────
def test_preservation_detecte_une_baisse():
    base = {"pipeline": 4, "feedback": 1, "alertes": 12}
    # une baisse de pipeline (4→3) = perte de donnée → check critique en échec
    res = lot2.preservation_results(base, {"pipeline": 3, "feedback": 1, "alertes": 12})
    pipeline_check = next(r for r in res if r[0].startswith("pipeline"))
    assert pipeline_check[1] is False and pipeline_check[2] is True   # ok=False, critique=True
    code, _ = lot2.final_decision(res, [], [], crashed=False)
    assert code == lot2.EXIT_ROLLBACK
    # aucune baisse → tout OK
    res_ok = lot2.preservation_results(base, base)
    assert all(ok for (_, ok, _, _) in res_ok)


# ── Post-checks de couverture (seuils) ──────────────────────────────────────────────────────
def test_coverage_results_seuils():
    bon = lot2.coverage_results(
        {"zonage_pct": 99.5, "bati_after": 50000, "ppr": 4, "ravine": 98,
         "plu_gpu_prescription": 117, "dup_groups": 0}, [], bati_before=11285)
    d = {name: (ok, crit) for (name, ok, crit, _) in bon}
    assert d["zonage PLU ≥ 99 %"][0] is True
    assert d["bâti re-fetché (> état pilote)"][0] is True
    assert d["aucune duplication de couche"][0] is True
    # dégradé : zonage bas + bâti non augmenté + doublons → checks critiques en échec
    mauvais = lot2.coverage_results(
        {"zonage_pct": 80.0, "bati_after": 11000, "ppr": 4, "ravine": 0,
         "plu_gpu_prescription": 0, "dup_groups": 7}, [], bati_before=11285)
    dm = {name: ok for (name, ok, _, _) in mauvais}
    assert dm["zonage PLU ≥ 99 %"] is False
    assert dm["bâti re-fetché (> état pilote)"] is False
    assert dm["aucune duplication de couche"] is False
    code, _ = lot2.final_decision(mauvais, [], [], crashed=False)
    assert code == lot2.EXIT_ROLLBACK            # contrôles critiques KO → rollback


# ── #4 Crash pendant une étape mutante → rapport d'échec + code ≠ 0 (sans base réelle) ───────
class _DummyConn:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _DummyEngine:
    def connect(self):
        return _DummyConn()


def test_crash_etape_mutante_produit_rapport_echec(monkeypatch):
    monkeypatch.setattr(lot2, "_engine", lambda: _DummyEngine())
    monkeypatch.setattr(lot2, "prechecks", lambda eng, b, u: [
        ("backup LOT 1 + checksum", True, "ok"), ("PostGIS actif", True, "ok"),
        ("tables critiques présentes", True, "ok"),
        ("Saint-Paul = 3000 parcelles", True, "ok"), ("0 doublon IDU (Saint-Paul)", True, "ok")])
    monkeypatch.setattr(lot2, "snapshot_state",
                        lambda c: {"pipeline": 0, "feedback": 0, "alertes": 0, "bati": 11285})
    monkeypatch.setattr(lot2, "snapshot_idus", lambda eng: set())

    def boom(eng, dry_run):
        raise RuntimeError("réseau coupé")
    monkeypatch.setattr(lot2, "step_import_parcels", boom)
    captured = {}
    monkeypatch.setattr(lot2, "write_report", lambda dry, lines: captured.update(dry=dry, lines=lines))

    code = lot2.main(["--execute", "--confirm", "IMPORT_SAINT_PAUL_COMPLET"])
    assert code == lot2.EXIT_ROLLBACK                       # jamais présenté comme succès
    assert captured["dry"] is False                         # rapport d'échec écrit (réel)
    assert any("ROLLBACK LOT 1" in line for line in captured["lines"])
