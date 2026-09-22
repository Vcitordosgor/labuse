"""SCORING-6 — `--parcelles-fichier` : liste de parcelles pour un recalcul EN DELTA.

Pur (sans DB) : la résolution idu → id est stubbée par une fausse session. On verrouille
l'analyse du fichier (parcel_id/idu mêlés, commentaires, blancs, dédup ordonnée) et l'échec
BRUYANT (fichier absent, idu introuvable) — jamais un delta silencieusement tronqué.
"""
import pytest
import typer

from labuse.cli import _parcel_ids_from_file


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _Session:
    """Fausse session : ne renvoie QUE les idu connus (id, idu) — un idu inconnu ne remonte pas."""
    def __init__(self, mapping):
        self.mapping = mapping
        self.calls = 0

    def execute(self, _stmt):
        self.calls += 1
        return _Result([(pid, idu) for idu, pid in self.mapping.items()])


def test_parcel_ids_entiers_commentaires_blancs(tmp_path):
    f = tmp_path / "ids.txt"
    f.write_text("# delta à cheval\n63195\n\n100\n63195\n  200  \n", encoding="utf-8")
    # session None : aucun idu → execute jamais appelé ; dédup préserve l'ordre.
    assert _parcel_ids_from_file(None, str(f)) == [63195, 100, 200]


def test_resolution_idu_et_ordre(tmp_path):
    f = tmp_path / "mix.txt"
    f.write_text("97402000AB1117\n5\n97401000AD0660\n", encoding="utf-8")
    sess = _Session({"97402000AB1117": 63195, "97401000AD0660": 999})
    # entiers d'abord (5), puis idu dans l'ordre du fichier (63195, 999).
    assert _parcel_ids_from_file(sess, str(f)) == [5, 63195, 999]
    assert sess.calls == 1


def test_idu_introuvable_echoue_bruyamment(tmp_path):
    f = tmp_path / "bad.txt"
    f.write_text("97402000AB1117\n97499000ZZ9999\n", encoding="utf-8")
    sess = _Session({"97402000AB1117": 63195})
    with pytest.raises(typer.BadParameter):
        _parcel_ids_from_file(sess, str(f))


def test_fichier_absent_echoue(tmp_path):
    with pytest.raises(typer.BadParameter):
        _parcel_ids_from_file(None, str(tmp_path / "nope.txt"))
