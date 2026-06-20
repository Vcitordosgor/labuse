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
