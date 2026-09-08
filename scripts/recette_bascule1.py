"""BASCULE-1 — recette REPRODUCTIBLE des deux issues de la commande (bac à sable).

On ne bascule JAMAIS pour de vrai : tous les pointeurs sont redirigés sur un dossier temporaire,
la base est une FAUSSE db (aucune écriture), et les collaborateurs lourds (run complet, purge des
caches, cohérence, journal) sont neutralisés. Seul le cœur ÉCRITURE → RELECTURE → CONFIRMATION est
exercé — la forme de sortie est identique à celle de l'alias `labuse golden promote <run>`.

    PYTHONPATH=src python scripts/recette_bascule1.py

La 3ᵉ issue (bascule IMPOSSIBLE : run inconnu) se joue en RÉEL, sans effet de bord :
    PYTHONPATH=src labuse golden promote __run_inexistant__
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from labuse import bascule_flux, circuit_journal, coherence_flux, golden_ops, manifeste, runs


class _FakeResult:
    rowcount = 0

    def mappings(self):
        return self

    def first(self):
        return None

    def all(self):
        return []

    def scalar(self):
        return None


class _FakeDB:
    """Aucune écriture réelle : toute requête rend un résultat vide."""

    def execute(self, *a, **k):
        return _FakeResult()


def _sandbox(tmp: Path) -> None:
    manifeste._FICHIER = tmp / "served_manifest.json"
    runs._SERVED_FILE = tmp / "served_run.txt"
    runs._PRECEDENT_FILE = tmp / "run_precedent.txt"
    bascule_flux._RUN_PRECEDENT_FILE = tmp / "run_precedent.txt"
    golden_ops._SERVED_FILE = tmp / "served_run.txt"
    bascule_flux._run_complet = lambda db, run: (True, "sandbox : complet")
    bascule_flux.purger_caches_run = lambda: ["(sandbox : aucun cache réel)"]
    coherence_flux.verifier = lambda db, run: {"ok": True}
    circuit_journal.journaliser = lambda *a, **k: None

    def _fake_promote(run: str) -> dict:
        ancien = runs.current()
        (tmp / "served_run.txt").write_text(run + "\n", encoding="utf-8")
        runs.invalidate()
        return {"ok": True, "ancien": ancien, "nouveau": run}
    golden_ops.promote = _fake_promote

    manifeste.ecrire({"scoring_run": "q_old", "residuel_run_seq": None, "mvt_run": "q_old",
                      "division_run": "q_old", "promoted_at": None, "par": "recette",
                      "precedent": {"scoring_run": "q_older", "residuel_run_seq": None,
                                    "mvt_run": "q_older", "division_run": "q_older"}})
    (tmp / "served_run.txt").write_text("q_old\n", encoding="utf-8")
    (tmp / "run_precedent.txt").write_text("q_older\n", encoding="utf-8")
    runs.invalidate()


def _echo_cli(res: dict, run: str) -> None:
    """Reproduit exactement ce qu'affiche l'alias CLI golden promote."""
    if res.get("ok"):
        print(f"✓ Run servi = {run} (ancien : {res.get('ancien')}, sens : {res.get('sens')}).")
        print(f"  manifeste (fait foi) : {res.get('manifeste_path')}")
        print(f"  arbre servi          : {res.get('arbre')}")
        print(f"  runs.current() relu  : {res.get('current_apres')}")
        print("  exit = 0")
    else:
        etat = "NON confirmée" if res.get("verifie") is False else "refusée"
        print(f"✗ Bascule {etat} : {res.get('motif')}")
        if res.get("manifeste_path"):
            print(f"  écrit : {res.get('manifeste_path')} (arbre {res.get('arbre')}) — "
                  f"fait foi : runs.current() = {res.get('current_apres')}")
        print("  exit = 1")


def main() -> None:
    db = _FakeDB()

    print("═══ 1) BASCULE RÉUSSIE (le manifeste bouge, runs.current() suit) ═══")
    with tempfile.TemporaryDirectory() as d:
        _sandbox(Path(d))
        print(f"runs.current() AVANT : {runs.current()}")
        res = bascule_flux.basculer(db, "q_new", par="recette")
        _echo_cli(res, "q_new")
        print(f"runs.current() APRÈS : {runs.current()}")

    print()
    print("═══ 2) BASCULE NON CONFIRMÉE (l'écrit ne prend pas effet → refus de mentir) ═══")
    with tempfile.TemporaryDirectory() as d:
        _sandbox(Path(d))
        manifeste.ecrire = lambda m: None          # le point de vérité refuse de bouger
        print(f"runs.current() AVANT : {runs.current()}")
        res = bascule_flux.basculer(db, "q_new", par="recette")
        _echo_cli(res, "q_new")
        print(f"runs.current() APRÈS : {runs.current()}  (inchangé — aucun mensonge)")


if __name__ == "__main__":
    main()
