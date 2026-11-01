"""FIX-FINAL-1 — VERROU de la régression NU-E-055 / NU-D-001.

Une parcelle au RNU ou en zone rouge renvoie le refus « hors périmètre ». Le correctif de refus
servait `terrain = None` ; les enrichissements aval (`_attach_contraintes_signalees`,
`_attach_zone_gabarit`) faisaient `payload.setdefault("terrain", {})[...] = …` → comme `terrain`
EXISTE et vaut None, `setdefault` renvoie None et `None[...] = …` lève `TypeError` ressorti en
HTTP 500 — à l'écran ET au PDF — dès qu'une parcelle hors périmètre portait AU MOINS un aléa / DPU
(le cas des parcelles RNU/PPR, les plus consultées).

Ces tests reproduisent EXACTEMENT ce chemin (terrain=None + un aléa présent) SANS base : le refus
doit traverser l'enrichissement sans planter, et le PDF de refus doit se rendre (jamais un 500).
"""
from __future__ import annotations

import labuse.api.app as app_mod
import labuse.api.modules as modules
from labuse.exports import etude_faisabilite as ef


def _payload_refus() -> dict:
    """Forme réelle du payload servi par `service._payload_hors_perimetre` pour un refus RNU."""
    return {
        "moteur": {"livrable": "IMPLANTATION-2"},
        "entrees": {"idus": ["97417000BI0076"], "commune": "Saint-Philippe",
                    "insee": "97417", "zone": None, "type_projet": "collectif", "objectif": "equilibre"},
        "regles": {"zone": None, "insee": "97417", "commune": "Saint-Philippe", "lignes": []},
        "terrain": None,            # ← le piège : terrain présent ET None (cas réel du refus d'avant le fix)
        "study_id": "EF-DEADBEEF",
        "statut_global": "hors périmètre",
        "verdict": "Étude hors périmètre",
        "message": "Commune au règlement national d'urbanisme — aucune zone PLU opposable.",
        "hors_perimetre": True,
        "motif_hors_perimetre": "rnu",
        "scenarios": [], "variantes": [], "capacite_maximale": None,
        "facteurs_limitants": [], "facteur_limitant": None,
    }


def _mock_aleas(monkeypatch):
    """Au moins un aléa + un DPU ⇒ `items` non vide ⇒ déclencheur exact du 500 d'origine."""
    monkeypatch.setattr(app_mod, "_aleas_block", lambda db, idu: {
        "liste": [{"nature": "inondation", "niveau": "fort"},
                  {"nature": "mouvement_terrain", "niveau": "fort"}]})
    monkeypatch.setattr(app_mod, "_dispositifs_block", lambda db, idu: {"dpu": True})


def test_contraintes_signalees_ne_plante_pas_sur_terrain_none(monkeypatch):
    _mock_aleas(monkeypatch)
    payload = _payload_refus()
    idus = payload["entrees"]["idus"]
    # Avant le fix : TypeError 'NoneType' object does not support item assignment → 500.
    modules._attach_contraintes_signalees(db=None, payload=payload, idus=idus)
    t = payload["terrain"]
    assert isinstance(t, dict)                      # terrain get-or-créé, jamais None
    contr = t.get("contraintes_signalees") or []
    assert any("inondation" in c for c in contr)    # les contraintes sont bien portées
    assert any("Droit de préemption" in c for c in contr)
    # le refus reste un refus : aucune étude n'est née de l'enrichissement
    assert payload["hors_perimetre"] is True and payload["verdict"] == "Étude hors périmètre"


def test_zone_gabarit_ne_plante_pas_sur_terrain_none(monkeypatch):
    # _attach_zone_gabarit s'appuie sur le Gabarit (collecte) ; indisponible → ne doit jamais planter,
    # et surtout ne jamais faire `None[...] = …`. On passe un payload terrain=None mono-parcelle.
    payload = _payload_refus()
    modules._attach_zone_gabarit(db=None, payload=payload, idus=payload["entrees"]["idus"])
    # pas d'exception ; terrain reste exploitable (dict ou None toléré, jamais un crash)
    assert payload["hors_perimetre"] is True


def test_pdf_refus_hors_perimetre_se_rend(monkeypatch):
    _mock_aleas(monkeypatch)
    payload = _payload_refus()
    modules._attach_contraintes_signalees(db=None, payload=payload, idus=payload["entrees"]["idus"])
    rendu = ef.rendu_hors_perimetre(payload, genere_le="01/11/2026")
    html = rendu["html"]
    assert rendu["retenu_ref"] == "hors_perimetre"
    assert "Étude hors périmètre" in html
    assert "Saint-Philippe" in html
    assert "glement national" in html   # « règlement national d'urbanisme » (apostrophe échappée par esc)
    # les contraintes signalées figurent dans le document de refus
    assert "inondation" in html
    # le refus ne chiffre AUCUN programme : pas de capacité/logements fabriqués
    assert "logement" not in html.lower()
    # les seuls nombres du corps (hors pied « Données LABUSE au » et n° de doc, structurels dans les 8
    # documents) sortent du payload : aucune capacité inventée. On vérifie le libellé de refus, pas le
    # pied structurel (couvert par le verrou nombres_hors_payload sur les PDF réels de la suite).
    assert "Aucun programme" in html
