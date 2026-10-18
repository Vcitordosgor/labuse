"""FIX-PRIX-ET-OPPORTUNITES (lot 1) — toute valeur de parcelle ESTIMÉE s'affiche en fourchette avec
une mention d'incertitude mesurée, jamais en chiffre sec. On vérifie :

  · le point de calcul unique `estimation_prix` (math de la fourchette + mention fondée sur le backtest) ;
  · le rendu réel (bloc réhabilitation, dossier PDF) sort une fourchette + la mention, pas un montant nu ;
  · le câblage des surfaces (fiche React, Copilote, bilan) — anti-régression vers un chiffre sec.
"""
from __future__ import annotations

from pathlib import Path

from labuse import estimation_prix

RACINE = Path(__file__).resolve().parents[1]


# ── 1. Point de calcul unique ─────────────────────────────────────────────────────────────────────
def test_fourchette_demi_largeur_30pct():
    fr = estimation_prix.fourchette(400_000)
    assert fr["centre"] == 400_000
    assert fr["bas"] == 280_000 and fr["haut"] == 520_000      # ±30 %, bornes rondes
    assert fr["demi_largeur_pct"] == 30


def test_fourchette_bornes_arrondies_lisibles():
    # 569 831 ± 30 % = 398 882 – 740 780 → arrondi lisible 390 000 – 750 000 (encadre, ne resserre pas).
    fr = estimation_prix.fourchette(569_831)
    assert fr["bas"] == 390_000 and fr["haut"] == 750_000
    assert fr["bas"] <= 569_831 * 0.7 and fr["haut"] >= 569_831 * 1.3   # jamais resserré


def test_fourchette_absence_jamais_fabriquee():
    assert estimation_prix.fourchette(None) is None
    assert estimation_prix.fourchette_libelle(None) is None


def test_fourchette_bornes_ordonnees_meme_si_negatif():
    fr = estimation_prix.fourchette(-10_000)
    assert fr["bas"] <= fr["haut"]


def test_mention_fondee_sur_chiffres_mesures():
    # la mention CITE les chiffres du backtest VERITE-TERRAIN-2 (27 %, ±20 %) — pas un ressenti.
    assert "27 %" in estimation_prix.MENTION
    assert "±20 %" in estimation_prix.MENTION or "20 %" in estimation_prix.MENTION
    assert "vénale" in estimation_prix.MENTION           # dit que ce n'est PAS une valeur vénale


def test_libelle_est_une_fourchette():
    lib = estimation_prix.fourchette_libelle(400_000)
    # insensible au type d'espace (l'app groupe en espace fine insécable  )
    nospace = lib.replace(" ", "").replace(" ", "")
    assert "–" in lib and "280000" in nospace and "520000" in nospace


# ── 2. Rendu réel : le bloc réhabilitation sort une fourchette, pas un chiffre sec ─────────────────
def test_rehab_bloc_rend_la_fourchette_et_la_mention():
    from labuse.api.blocs_documents import rehab_bloc
    fr = estimation_prix.fourchette(63_000)
    mode_b = {"disponible": True, "terrain_nu": {
        "valeur_eur": 63_000, "valeur_libelle": "63 000 €",
        "valeur_fourchette_libelle": f"{fr['bas']:,} € – {fr['haut']:,} €".replace(",", " "),
        "incertitude": estimation_prix.MENTION, "prix_m2": 150, "surface_m2": 420}}
    textes = " ".join(t for _, t in rehab_bloc(mode_b)["lignes"])
    bas = f"{fr['bas']:,}".replace(",", " ")      # 63 000 ± 30 % arrondi = 44 000 – 82 000
    haut = f"{fr['haut']:,}".replace(",", " ")
    assert "fourchette ±30 %" in textes
    assert bas in textes and haut in textes
    assert "27 %" in textes                               # la mention mesurée accompagne la valeur
    assert "63 000 €" not in textes                       # plus le chiffre sec seul


def test_rehab_bloc_repli_si_pas_de_fourchette():
    # robustesse : un vieux payload sans fourchette retombe sur le libellé simple (jamais une erreur).
    from labuse.api.blocs_documents import rehab_bloc
    mode_b = {"disponible": True, "terrain_nu": {"valeur_libelle": "63 000 €", "prix_m2": 150, "surface_m2": 420}}
    textes = " ".join(t for _, t in rehab_bloc(mode_b)["lignes"])
    assert "63 000" in textes


# ── 3. Câblage des surfaces (anti-régression vers un chiffre sec) ──────────────────────────────────
def _lire(rel: str) -> str:
    return (RACINE / rel).read_text()


def test_bilan_sert_la_fourchette_avec_la_valeur_terrain():
    src = _lire("src/labuse/faisabilite/bilan.py")
    assert "valeur_fourchette_libelle" in src and "incertitude" in src
    assert "from ..estimation_prix import" in src


def test_fiche_react_affiche_une_fourchette():
    m = _lire("frontend/src/components/fiche/marche.tsx")
    # la valeur au prix du secteur passe par le point unique `fourchette`, plus un fmtInt nu.
    assert "fourchette(f.dvf_parcelle.valeur_terrain_secteur_eur)" in m
    assert "lib/fourchette" in m


def test_copilote_projette_une_fourchette():
    src = _lire("src/labuse/copilote_v2/missions_lourdes.py")
    assert "from ..estimation_prix import" in src
    assert "une fourchette de" in src


def test_pdf_blocs_servent_la_fourchette():
    for rel in ("src/labuse/exports/blocs/marche.py", "src/labuse/exports/blocs/financier.py"):
        src = _lire(rel)
        assert "valeur_fourchette_libelle" in src
        assert "incertitude" in src


# ── 4. (d) le « ± 12 % » non mesuré du prix de sortie neuf → remplacé par la marge mesurée ──────────
def test_prix_sortie_neuf_plus_de_fausse_precision_12pct():
    from labuse.ingestion import dvf_prix_neuf as dp
    from labuse.ingestion import score_e as se
    from labuse.faisabilite import bilan
    assert "± 12" not in dp.niveau_prix_label("ile_validee")
    assert "27 %" in dp.niveau_prix_label("ile_validee")
    assert "± 12" not in se.niveau_label("ile_validee")
    assert "27 %" in se.niveau_label("ile_validee")
    raisons = bilan._fiabilite_prix_neuf("ile_validee")[1]
    assert raisons and "± 12" not in raisons[0] and "27 %" in raisons[0]


# ── 5. (e) la commune affichée vient de l'INSEE officiel, pas d'un parcels.commune erroné ───────────
def test_nom_commune_officiel_depuis_idu():
    from labuse import communes
    assert communes.nom_officiel("97404000AW0099") == "L'Étang-Salé"   # 97404, jamais « Saint-Denis »
    assert communes.nom_officiel("97411") == "Saint-Denis"
    assert communes.nom_officiel(None) is None
    assert communes.nom_officiel("00000000000000") is None             # hors des 24 communes


def test_copilote_nomme_la_commune_officielle():
    # les 3 points d'émission du Copilote dérivent la commune de l'INSEE (anti « L'Étang-Salé → St-Denis »).
    for rel in ("src/labuse/copilote_v2/missions_lourdes.py",
                "src/labuse/copilote_v2/resume_fiche.py",
                "src/labuse/copilote_v2/heros.py"):
        assert "nom_officiel" in _lire(rel), rel
