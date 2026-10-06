"""BILAN-1 Lot 1 — le catalogue des postes = le modèle de la promotrice.

Le nombre de postes, leur ordre et leurs libellés sont vérifiés EN LES COMPTANT
depuis le xlsx (jamais en dur). Le xlsx n'est pas commité (gitignoré) : si absent
(CI), le test se saute proprement.
"""

from __future__ import annotations

import io
import pathlib
import re
import zipfile

import pytest

from labuse.bilan import charger_catalogue

_RACINE = pathlib.Path(__file__).resolve().parents[1]
_XLSX = _RACINE / "docs" / "audit-2026-10" / "bilan-1" / "modele-promotrice.xlsx"

# Nom de société présent dans le modèle (lignes 122/128) — jamais dans un poste,
# mais on neutralise par sécurité pour la comparaison des libellés.
_SOCIETE = re.compile(r"\boc[ée]anis\b", re.IGNORECASE)

# Titres de blocs et lignes de total à exclure du balayage des postes.
_TITRES = {
    "TERRAIN",
    "CONSTRUCTION & HONORAIRES TECHNIQUES",
    "GESTION",
    "FRAIS DE VENTE",
    "CHIFFRE D'AFFAIRES",
    "RATIOS",
}


def _est_total(s: str) -> bool:
    u = s.strip().upper()
    return (
        u.startswith("TOTAL")
        or u.startswith("FRAIS BRUTS")
        or u.startswith("DEPENSES")
        or u.startswith("DÉPENSES")
        or u.startswith("RESULTAT")
        or u.startswith("RÉSULTAT")
        or u.startswith("TVA RESIDUELLE")
        or u.startswith("CASH FLOW")
    )


def _neutralise(s: str) -> str:
    return _SOCIETE.sub("", s).strip()


def _charger_feuille_bilan():
    """Ouvre la feuille BILAN en neutralisant les `definedNames` cassés (#N/A)
    du modèle, qui font planter openpyxl à l'ouverture directe."""
    openpyxl = pytest.importorskip("openpyxl")
    brut = _XLSX.read_bytes()
    tampon = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(brut)) as zin, zipfile.ZipFile(
        tampon, "w", zipfile.ZIP_DEFLATED
    ) as zout:
        for item in zin.namelist():
            data = zin.read(item)
            if item == "xl/workbook.xml":
                txt = data.decode("utf-8")
                txt = re.sub(r"<definedNames>.*?</definedNames>", "", txt, flags=re.S)
                data = txt.encode("utf-8")
            zout.writestr(item, data)
    tampon.seek(0)
    wb = openpyxl.load_workbook(tampon, data_only=False)
    return wb["BILAN"]


def _postes_du_modele(ws) -> list[tuple[int, str]]:
    """Balayage indépendant : les lignes-postes du modèle (règle déterministe)."""
    postes = []
    for r in range(43, 107):
        a = ws.cell(r, 1).value
        if not isinstance(a, str) or not a.strip():
            continue
        if a.strip() in _TITRES or _est_total(a):
            continue
        has = any(ws.cell(r, c).value is not None for c in (3, 4, 5, 7))  # C,D,E,G
        if not has:
            continue
        postes.append((r, a.strip()))
    return postes


pytestmark = pytest.mark.skipif(
    not _XLSX.exists(), reason="modèle de la promotrice absent (gitignoré)"
)


def test_catalogue_charge():
    cat = charger_catalogue()
    assert cat.version == 1
    assert [b.id for b in cat.blocs] == ["T", "C", "G", "V"]


def test_nombre_et_ordre_egalent_le_modele():
    ws = _charger_feuille_bilan()
    modele = _postes_du_modele(ws)
    cat = charger_catalogue()
    postes = cat.postes()

    # 1) même nombre de postes que le modèle (45), comptés depuis le xlsx
    assert len(postes) == len(modele), (
        f"catalogue {len(postes)} postes vs modèle {len(modele)}"
    )
    assert len(postes) == 45

    # 2) même ensemble de lignes-modèle, dans le même ordre
    lignes_cat = [p.ligne_modele for p in postes]
    lignes_mod = [r for r, _ in modele]
    assert lignes_cat == lignes_mod, "ordre/sélection des lignes ≠ modèle"
    assert lignes_cat == sorted(lignes_cat), "lignes non strictement croissantes"
    assert len(set(lignes_cat)) == len(lignes_cat), "ligne-modèle en double"


def test_libelles_proviennent_du_modele():
    ws = _charger_feuille_bilan()
    cat = charger_catalogue()
    for p in cat.postes():
        cellule = ws.cell(p.ligne_modele, 1).value or ""
        assert _neutralise(str(cellule)) == _neutralise(p.libelle_modele), (
            f"poste {p.id} ligne {p.ligne_modele}: "
            f"xlsx={cellule!r} vs yaml={p.libelle_modele!r}"
        )


def test_blocs_couvrent_les_quatre_sections():
    cat = charger_catalogue()
    tailles = {b.id: len(b.postes) for b in cat.blocs}
    assert tailles == {"T": 18, "C": 10, "G": 10, "V": 7}


def test_aucun_nom_de_societe_dans_les_libelles():
    cat = charger_catalogue()
    for p in cat.postes():
        assert not _SOCIETE.search(p.libelle)
        assert not _SOCIETE.search(p.libelle_modele)
