"""M129-B — LA MATRICE EST MORTE : le contrat testé est le REFUS explicite (jamais un
calcul fantôme). L'historique du module vit dans git ; les statuts servis = cascade + tier v2."""
import pytest

from labuse.scoring.dryrun import compute_matrice


def test_matrice_morte_refuse_explicitement():
    with pytest.raises(RuntimeError, match="MORTE"):
        compute_matrice(None, "q_v10_m129", "97415")
