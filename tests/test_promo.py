"""PROMO-1 — garde du référentiel programmes : table (P1), extraction anti-invention (P2), score de
rattachement (P3). Doctrine : FAITS + LIEN seulement, jamais un texte/visuel ni un champ inventé.
"""
from __future__ import annotations

import pytest

from labuse.promo import rattachement as R
from labuse.promo.collecte import _Extracteur, _json_liste, extraire_programmes, fetch_texte


# ── P3 — score de rattachement (constante + proximité de période) ──────────────────────────────────

def test_score_siren_commune_sous_seuil_sans_annee():
    """SIREN + commune valent 0,6 — SOUS le seuil auto (0,7) : sans année, c'est toujours l'admin qui lie."""
    assert R.score(None, 2025) == R.BASE_SIREN_COMMUNE == 0.6
    assert R.BASE_SIREN_COMMUNE < R.SEUIL_RATTACHEMENT_AUTO


def test_score_annee_identique_maximal():
    assert R.score(2025, 2025) == 1.0                       # même année → +0,4
    assert R.score(2025, 2025) >= R.SEUIL_RATTACHEMENT_AUTO


def test_score_periode_degressive_puis_nulle():
    assert R.score(2025, 2023) == pytest.approx(0.6 + 0.4 * (1 - 2 / 5))   # 2 ans d'écart
    assert R.score(2025, 2018) == R.BASE_SIREN_COMMUNE       # ≥ 5 ans → proximité nulle


# ── P2 — extraction JSON anti-invention ────────────────────────────────────────────────────────────

def test_json_liste_tolere_bloc_markdown():
    assert _json_liste('```json\n{"programmes": [{"nom": "X"}]}\n```') == [{"nom": "X"}]
    assert _json_liste("aucun json ici") is None            # rien de parsable → None (jamais réparé)


def test_extraire_ne_garde_que_les_4_faits_et_borne(monkeypatch):
    """Le modèle renvoie un descriptif + une URL bidon + une année absurde → seuls nom/commune/url(http)/
    annee(bornée) sont retenus ; le descriptif est JETÉ (doctrine : jamais un texte)."""
    from labuse.ai import core

    def _fake_complete(*a, **k):
        return core.IAResult(text='{"programmes": [{"nom": "Les Alizés", "commune": "Saint-Paul", '
                             '"url": "pas-une-url", "annee": 3000, "description": "vue mer imprenable"}]}',
                             model="x", degraded=False)
    monkeypatch.setattr(core, "complete", _fake_complete)
    out = extraire_programmes(None, "texte", ["Les Alizés → https://promo.re/alizes"])
    assert out["ok"] and len(out["programmes"]) == 1
    p = out["programmes"][0]
    assert p == {"nom": "Les Alizés", "commune": "Saint-Paul", "url": None, "annee": None}
    assert "description" not in p                            # aucun descriptif conservé


def test_extraire_degrade_ne_fabrique_rien(monkeypatch):
    from labuse.ai import core
    monkeypatch.setattr(core, "complete", lambda *a, **k: core.IAResult(text="", model="x", degraded=True, reason="no_key"))
    out = extraire_programmes(None, "t", [])
    assert out["ok"] is False and "programmes" not in out


# ── P2 — le parseur HTML stdlib (zéro dépendance externe) ──────────────────────────────────────────

def test_extracteur_stdlib_texte_et_liens():
    p = _Extracteur()
    p.feed('<html><style>x{}</style><body><h1>Nos programmes</h1>'
           '<a href="/prog/1">Résidence Bengali</a><script>evil()</script></body></html>')
    assert "Nos programmes" in "\n".join(p.textes)
    assert "evil()" not in "\n".join(p.textes)              # script jamais lu
    assert p.liens == [("Résidence Bengali", "/prog/1")]


def test_fetch_url_invalide():
    _t, _l, motif = fetch_texte("pas une url")
    assert motif and "URL invalide" in motif


# ── P1 — la table programmes ne porte AUCUNE colonne de texte/photo ────────────────────────────────

def test_schema_programmes_sans_texte_ni_photo():
    import re

    from labuse.promo.tables import DDL
    # on regarde les DÉFINITIONS DE COLONNES seules (commentaires -- retirés : ils citent la doctrine).
    sans_comm = "\n".join(re.sub(r"--.*$", "", ligne) for ligne in DDL.lower().splitlines())
    for interdit in ("description", "descriptif", "photo", "image", "texte", "resume", "accroche"):
        assert interdit not in sans_comm, f"colonne interdite (doctrine droit d'auteur) : {interdit}"
    for attendu in ("promoteur_nom", "nom", "commune", "url", "source", "date_releve"):
        assert attendu in sans_comm
