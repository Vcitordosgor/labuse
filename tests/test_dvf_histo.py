"""Tests parsing dvf_histo (M3.5 lot A) — sans base, sur échantillons fabriqués."""
import pytest

from labuse.ingestion.dvf_histo import (
    _ENTETE_ATTENDUE, _assigner_id_mutation, parse_fichier)

_L = ("|||||||000001|06/01/2014|Vente|230000,00|3||ALL|0962|MONTPLAISIR|97400|"
      "SAINT DENIS|974|11||DL|120||||||||||||0|1|Maison||86|4|S||456")
_L_AUTRE_DEP = _L.replace("|974|11|", "|973|11|")
_L_2015 = _L.replace("06/01/2014", "06/01/2015")


def _ecrire(tmp_path, entete, lignes):
    p = tmp_path / "vf.txt"
    p.write_text("\n".join([entete, *lignes]) + "\n", encoding="utf-8")
    return p


def test_parse_ligne_complete(tmp_path):
    lignes, stats = parse_fichier(_ecrire(tmp_path, _ENTETE_ATTENDUE, [_L]), 2014)
    assert stats == {"lignes": 1, "hors_annee": 0}
    lg = lignes[0]
    assert lg["id_parcelle"] == "97411000DL0120"
    assert lg["code_commune"] == "97411"
    assert lg["valeur_fonciere"] == 230000.0
    assert lg["nature_culture"] == "sols"
    assert lg["type_local"] == "Maison"


def test_filtre_departement_et_annee(tmp_path):
    p = _ecrire(tmp_path, _ENTETE_ATTENDUE, [_L, _L_AUTRE_DEP, _L_2015])
    lignes, stats = parse_fichier(p, 2014)
    assert len(lignes) == 1 and stats["hors_annee"] == 1  # 973 ignoré, 2015 écarté


def test_entete_divergente_levee(tmp_path):
    p = _ecrire(tmp_path, _ENTETE_ATTENDUE.replace("Surface terrain", "Surface"), [_L])
    with pytest.raises(RuntimeError, match="entête divergente"):
        parse_fichier(p, 2014)


def test_entete_variante_identifiant_document(tmp_path):
    entete = "Identifiant de document|" + _ENTETE_ATTENDUE.split("|", 1)[1]
    lignes, _ = parse_fichier(_ecrire(tmp_path, entete, [_L]), 2014)
    assert len(lignes) == 1


def test_id_mutation_regroupe_meme_disposition(tmp_path):
    autre_parcelle = _L.replace("|DL|120|", "|DL|121|")
    autre_vente = _L.replace("230000,00", "99000,00")
    p = _ecrire(tmp_path, _ENTETE_ATTENDUE, [_L, autre_parcelle, autre_vente])
    lignes, _ = parse_fichier(p, 2014)
    n = _assigner_id_mutation(lignes, 2014)
    assert n == 2  # même (date, dispo, valeur) → même mutation ; valeur ≠ → autre
    ids = {lg["id_mutation"] for lg in lignes}
    assert ids == {"H2014-000001", "H2014-000002"}
