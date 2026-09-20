"""PLU-CALIBRAGE-1 lot 4 — la revue : valider / corriger / rejeter, sur une copie de fichier.
Prouve les trois gestes + que la source (article/page/citation) survit à une correction et que
`valider` fait passer `propose` → `valide` (matière du verrou V6a)."""
from __future__ import annotations

import shutil
from pathlib import Path

import yaml

from labuse.plu import destinations as D
from labuse.plu import revue as R


def _prep(tmp_path) -> Path:
    src = D._DEST_DIR / "97411_saint_denis.yaml"
    dst = tmp_path / "97411_saint_denis.yaml"
    shutil.copy(src, dst)
    return dst


def test_revue_valide_corrige_rejette(tmp_path, monkeypatch):
    dst = _prep(tmp_path)
    monkeypatch.setattr(D, "_fichier_commune", lambda insee: dst)
    monkeypatch.setattr(D, "_doc", lambda commune: D._load_yaml(str(dst)))
    D._load_yaml.cache_clear()

    # on cible des feuilles réellement présentes en `propose` sur Saint-Denis
    avant = {r["chemin"]: r for r in D.regles_commune("97411") if r["zone"] == "Ud"}
    assert avant, "Ud doit porter des propositions (lot 3)"
    cible_valide = "mixite" if "mixite" in avant else next(iter(avant))
    cible_corrige = "emprise_sol.ces" if "emprise_sol.ces" in avant else None

    decisions = {"Ud": {cible_valide: {"geste": "valider"}}}
    if cible_corrige:
        decisions["Ud"][cible_corrige] = {"geste": "corriger", "valeur": {"pct": 55}}
    # rejeter une feuille hauteur si présente
    cible_rejet = next((c for c in avant if c.startswith("hauteur")), None)
    if cible_rejet:
        decisions["Ud"][cible_rejet] = {"geste": "rejeter"}

    compte = R.appliquer("97411", decisions)
    D._load_yaml.cache_clear()
    apres = {r["chemin"]: r for r in D.regles_commune("97411") if r["zone"] == "Ud"}

    # valider : statut valide, source intacte
    assert apres[cible_valide]["statut"] == "valide"
    assert apres[cible_valide]["article"] and apres[cible_valide]["page_pdf"] and apres[cible_valide]["citation"]
    assert compte["valide"] >= 1
    # corriger : valeur remplacée, source conservée, statut valide
    if cible_corrige:
        assert apres[cible_corrige]["pct"] == 55
        assert apres[cible_corrige]["statut"] == "valide"
        assert apres[cible_corrige]["citation"] == avant[cible_corrige]["citation"]
    # rejeter : la feuille a disparu
    if cible_rejet:
        assert cible_rejet not in apres
        assert compte["rejete"] == 1

    # le fichier reste un YAML valide, sous_destinations intacts
    doc = yaml.safe_load(dst.read_text(encoding="utf-8"))
    assert doc["zones"]["Ud"]["sous_destinations"]
