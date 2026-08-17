"""M109 — le miscompte muet : un critère lâché est TOUJOURS dit, jamais le sous-total muet.

Tests DÉTERMINISTES (aucun appel modèle) : on force le chemin gabarit de `_formuler`
(core.complete dégradé) et on vérifie que l'avertissement des critères non appliqués est
présent — le chiffre n'est jamais servi seul quand un critère a été abandonné.
"""
from __future__ import annotations

from labuse.copilote_v2 import answering
from labuse.copilote_v2.outils import ToolResult


class _Degraded:
    text = ""
    degraded = True
    reason = "no_key"


def test_avert_cna_nomme_le_critere_et_marque_l_absence():
    a = answering._avert_cna(["renouvellement urbain"])
    assert "renouvellement urbain" in a
    assert "pas encore interrogeable" in a.lower()
    assert answering._avert_cna([]) == ""            # rien à signaler → rien


def test_formuler_sert_le_chiffre_AVEC_l_avertissement(monkeypatch):
    # chemin gabarit forcé (pas de modèle) : le sous-total 1970 est servi, MAIS le critère lâché est dit.
    monkeypatch.setattr(answering.core, "complete", lambda *a, **k: _Degraded())
    res = ToolResult("compter_parcelles", valeur=1970,
                     data={"compte": 1970, "criteres": {"commune": "Saint-Denis", "surface_min": 5000}},
                     source="cadastre", millesime="Etalab 2026-06",
                     criteres_non_appliques=["renouvellement urbain"])
    txt = answering._formuler(None, "combien de grandes parcelles en renouvellement urbain à Saint-Denis", res)
    assert "1970" in txt                                    # le sous-compte appliqué est servi
    assert "renouvellement urbain" in txt.lower()           # le critère lâché est NOMMÉ
    assert "pas encore interrogeable" in txt.lower()        # marqueur d'absence déterministe


def test_formuler_sans_critere_lache_reste_nu(monkeypatch):
    monkeypatch.setattr(answering.core, "complete", lambda *a, **k: _Degraded())
    res = ToolResult("compter_parcelles", valeur=25, data={"compte": 25}, source="cadastre",
                     millesime="Etalab 2026-06", criteres_non_appliques=[])
    txt = answering._formuler(None, "combien de parcelles brûlantes à Saint-Paul", res)
    assert "25" in txt
    assert "interrogeable" not in txt.lower()               # aucun avertissement parasite


def test_verrou_juger_cna(monkeypatch):
    # le juge de la gate (verifs) valide le nouveau motif : chiffre appliqué + critère lâché dit.
    from labuse.copilote_v2.verifs import juger
    item = {"cat": "cna", "manque": ["renouvellement"]}
    bon = {"text": "1970 parcelles ≥ 5000 m² à Saint-Denis. ⚠️ Le critère « renouvellement urbain » "
                   "n'est pas encore interrogeable ici."}
    ok, _ = juger(item, bon, 1970)
    assert ok
    # muet : le sous-total sans dire le critère lâché → ÉCHEC
    muet = {"text": "Il y a 1970 parcelles en renouvellement urbain à Saint-Denis."}
    ok2, _ = juger(item, muet, 1970)
    assert not ok2
