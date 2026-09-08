"""EXPORTS-2 lot 3 — le Résumé (document « Résumé », gabarit maquette-pdf-resume.html).

Mêmes ids que le Dossier, sélection courte, en-tête compact (pas de page de garde). Ajouts
RELECTURE : la ligne du prix d'achat (D-a) et le renvoi « version complète : Dossier · Financier ».
Une donnée absente → ligne OMISE (aucun ◌). Préfixe RE-.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml

from labuse.exports import builder

from test_exports2_lot2 import FICHE, _FakeDB  # même fiche fixture (une seule vérité)

MOTS = yaml.safe_load((Path(__file__).resolve().parents[1] / "config" / "mots_interdits.yaml").read_text())["mots"]


def _resume(fiche=FICHE):
    return builder.construire(_FakeDB(), "97415000BO0852", "resume", fiche=fiche, jour=date(2026, 9, 5))


def test_prefixe_re_et_entete_compacte():
    res = _resume()
    assert res.numero == "RE-20260905-0852"
    assert 'class="cover"' not in res.html           # pas de page de garde pleine (au fil)
    assert "97415000BO0852" in res.html              # IDU entier dans la ligne d'identité
    assert "Fiche parcelle — résumé" in res.html


def test_selection_courte_et_renvoi():
    html = _resume().html
    assert "Ce que le règlement permet" in html and "Marché" in html
    assert "maille IRIS" in html                      # §7 : maille réelle même au résumé
    assert "Version complète : Dossier parcelle · Bilan chiffré : Financier" in html
    # D-a : ligne de prix d'achat servie quand la mutation existe (le libellé est échappé en HTML)
    fiche = dict(FICHE, dvf_parcelle={"derniere_mutation": {"valeur": 180000}})
    h = _resume(fiche).html
    assert "achat de la parcelle" in h and "180" in h


def test_aucun_ocro_aucun_mot_interdit():
    html = _resume().html
    assert "◌" not in html
    assert [m for m in MOTS if m in html] == []


def test_non_constructible_prime_au_resume():
    fiche = dict(FICHE)
    fiche["reglement_plu"] = {"zones": [{"zone": "N", "regles_valeurs": [], "destinations": {}}]}
    fiche["potentiel_transformation"] = dict(FICHE["potentiel_transformation"],
                                             cause="zone_non_constructible", libelle="Fort potentiel")
    html = builder.construire(_FakeDB(), "IDU", "resume", fiche=fiche, jour=date(2026, 9, 5)).html
    assert "non constructible" in html and "Fort potentiel" not in html


def test_omission_si_fiche_pauvre():
    html = builder.construire(_FakeDB(), "IDU", "resume",
                              fiche={"surface_m2": 500, "commune": "X", "adresse": "rue X"},
                              jour=date(2026, 9, 5)).html
    assert "◌" not in html and "non chiffré" not in html
    assert "Ce que le règlement permet" not in html   # pas de règlement → section omise
