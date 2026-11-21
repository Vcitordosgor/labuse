"""MISE-EN-LIGNE-3 — un module tiers importé par src/labuse est soit SERVI (et le selftest du
déploiement l'importe — un manque bloque le déploiement), soit HORS_PROD avec un motif. Le
balayage est par AST, imports à l'intérieur des fonctions compris : la panne openpyxl (extra
jamais installé en prod → 500 au clic d'un client sur le Bilan Excel) ne peut plus se reproduire
en silence."""
import ast
import pathlib
import sys

from labuse.deps_servies import HORS_PROD, MODULES_TIERS_SERVIS, manquants

RACINE = pathlib.Path(__file__).resolve().parents[1] / "src" / "labuse"


def _imports_tiers() -> set[str]:
    stdlib = set(sys.stdlib_module_names)
    noms: set[str] = set()
    for p in RACINE.rglob("*.py"):
        tree = ast.parse(p.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                noms.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                noms.add(node.module.split(".")[0])
    return {n for n in noms if n not in stdlib and n != "labuse"}


def test_tout_import_tiers_est_classe():
    """Balayage AST complet : tout module tiers est déclaré servi OU hors-prod (motivé).
    Un nouvel import tiers non classé fait échouer ce test — on décide alors de sa liste."""
    inventaire = _imports_tiers()
    classes = set(MODULES_TIERS_SERVIS) | set(HORS_PROD)
    non_classes = sorted(inventaire - classes)
    assert not non_classes, (
        f"imports tiers non classés dans labuse.deps_servies : {non_classes} — "
        "ajoute-les à MODULES_TIERS_SERVIS (et aux dépendances de série) s'ils sont sur un "
        "chemin servi, sinon à HORS_PROD avec le motif.")
    fantomes = sorted(classes - inventaire)
    assert not fantomes, f"déclarés mais plus importés nulle part : {fantomes} — à retirer."


def test_hors_prod_motive_et_disjoint():
    assert all(HORS_PROD.values()), "chaque module HORS_PROD doit porter son motif"
    assert not set(HORS_PROD) & set(MODULES_TIERS_SERVIS), "un module ne peut pas être les deux"


def test_modules_servis_presents_ici():
    """Dans l'environnement de test (venv complet), aucun module servi ne manque."""
    assert manquants() == []


def test_selftest_bloque_sur_module_absent(monkeypatch):
    """Le contrôle 5 du selftest transforme un paquet manquant en refus de déploiement."""
    from labuse import deps_servies, jobs
    monkeypatch.setattr(deps_servies, "MODULES_TIERS_SERVIS",
                        ("module_inexistant_ml3",) + deps_servies.MODULES_TIERS_SERVIS)
    ok, problemes = jobs.selftest()
    assert not ok
    assert any("module_inexistant_ml3" in p for p in problemes)
