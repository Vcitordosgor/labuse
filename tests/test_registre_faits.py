"""M102-B3 — le registre de faits du fil : extraction pure + verrou anti-invention étendu.

Tests PURS (aucune base) : l'oracle de la reprise inter-tours est le registre — un nombre
absent du tour courant ET du registre n'est jamais servi (le verrou retombe sur le gabarit)."""
from __future__ import annotations

from dataclasses import dataclass, field

from labuse.copilote_v2 import registre_faits
from labuse.copilote_v2.answering import _anti_invention


@dataclass
class _Res:
    tool: str = "compter_parcelles"
    valeur: object = 51129
    data: dict = field(default_factory=lambda: {
        "compte": 51129, "criteres": {"surface_min": 300}, "bool_pas_un_fait": True,
        "liste": [{"n": 12}]})
    source: str = "cadastre"
    millesime: str = "Etalab 2026-06"
    partiel: bool = False
    reserve: str | None = None


def test_extraire_faits_feuilles_numeriques_dedup_et_bool_exclus():
    faits = registre_faits.extraire_faits(_Res())
    cles = {(f["cle"], f["valeur"]) for f in faits}
    assert ("valeur", 51129.0) in cles
    assert ("criteres.surface_min", 300.0) in cles
    assert ("liste.0.n", 12.0) in cles
    # bool exclu ; le compte dupliqué de `valeur` n'apparaît qu'une fois par (clé, valeur)
    assert not any("bool" in c for c, _ in cles)
    assert all(f["source"] == "cadastre" and f["millesime"] == "Etalab 2026-06" for f in faits)


def test_verrou_reprise_fil_autorisee_et_refusee():
    res_tour = _Res(valeur=7, data={"delai_median_mois": 7})   # le tour courant ne connaît QUE 7
    fil = [{"cle": "compte", "valeur": 51129.0, "source": "cadastre", "millesime": "Etalab 2026-06"}]
    vals = registre_faits.valeurs(fil)
    # reprise LÉGITIME : 51 129 vient du registre → autorisé
    assert _anti_invention("7 mois, et je vous rappelle les 51 129 parcelles.", res_tour, vals)
    # reprise ILLÉGITIME : 99 999 n'est ni du tour ni du registre → bloqué (pas servi)
    assert not _anti_invention("99 999 parcelles environ.", res_tour, vals)
    # sans registre : l'ancien comportement est INCHANGÉ (51 129 bloqué)
    assert not _anti_invention("51 129 parcelles.", res_tour, None)
