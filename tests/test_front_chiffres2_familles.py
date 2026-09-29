"""FRONT-CHIFFRES-2 — gardes par famille (une valeur, un seul point de vérité).

Chaque famille remontée/déclarée pose ici son garde : le front ne code plus le chiffre, le back
le sert depuis la source unique. Grep de code (sans framework JS), sur le modèle de
test_front_chiffres_orphelins.py. Une régression (retour du littéral au front) fait échouer.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "frontend" / "src"


def test_f04_financier_bornes_hors_marche_servies():
    """F04 — les bornes du garde « hors marché » (20000/8000/12000 €/m²) ne sont plus codées au
    front : elles sont servies (hors_marche_bornes) depuis la SOURCE UNIQUE faisabilite/engine.py,
    lue par financier_bilan (garde PDF) ET par le questionnaire (garde client) — un seul point."""
    # 1) la source unique porte bien les trois bornes
    from labuse.faisabilite.engine import (
        MAX_COUT_CONSTRUCTION_M2, MAX_PRIX_BAILLEUR_M2, MAX_PRIX_SORTIE_M2)
    assert (MAX_PRIX_SORTIE_M2, MAX_COUT_CONSTRUCTION_M2, MAX_PRIX_BAILLEUR_M2) == (20_000.0, 8_000.0, 12_000.0)

    # 2) le garde du PDF lit la source unique (inchangé, on le verrouille)
    from labuse.exports.financier_bilan import _hors_marche
    assert _hors_marche(MAX_PRIX_SORTIE_M2 + 1, None, None) is not None   # au-dessus → hors marché
    assert _hors_marche(MAX_PRIX_SORTIE_M2 - 1, None, None) is None        # en dessous → dans le marché

    # 3) l'endpoint sert les bornes depuis les constantes du moteur (pas de littéral)
    app = (ROOT / "src/labuse/api/app.py").read_text(encoding="utf-8")
    assert '"hors_marche_bornes"' in app
    assert "from ..faisabilite.engine import" in app and "MAX_PRIX_SORTIE_M2" in app

    # 4) le front NE code plus les bornes : il lit hors_marche_bornes
    fq = (SRC / "components/fiche/FinancierQuestionnaire.tsx").read_text(encoding="utf-8")
    assert "hors_marche_bornes" in fq and "bornes.prix_sortie_saisi_eur_m2" in fq
    for littéral in ("20000", "8000", "12000", "MAX_PRIX_SORTIE_M2", "MAX_COUT_M2", "MAX_BAILLEUR_M2"):
        assert littéral not in fq, f"borne codée en dur revenue au front : {littéral}"


def test_f14_radar_badges_nouveau_et_vente_longue_servis():
    """F14 — les badges « Nouveau » (< 2 j) et « En vente longue » (> 90 j) ne sont plus décidés au
    front : `nouveau` est servi à plat (seuil back SEUIL_NOUVEAU_J) et « en vente longue » se lit sur
    le `statut` du cycle back (SEUIL_VENTE_LONGUE_J) — un seul point de vérité, base Réunion."""
    from labuse.pige.cycle import SEUIL_NOUVEAU_J, SEUIL_VENTE_LONGUE_J
    assert (SEUIL_NOUVEAU_J, SEUIL_VENTE_LONGUE_J) == (2, 90)

    # le back sert `nouveau` à plat, avec le seuil interpolé (pas de littéral détaché)
    from labuse.pige import client
    assert "AS nouveau" in client._SELECT and f"- {SEUIL_NOUVEAU_J}) AS nouveau" in client._SELECT
    src_client = (ROOT / "src/labuse/pige/client.py").read_text(encoding="utf-8")
    assert '"nouveau": bool(r.get("nouveau"))' in src_client

    # le front LIT les décisions servies, ne recalcule plus j<2 / j>90
    re_ = (SRC / "components/radar/RadarEcran.tsx").read_text(encoding="utf-8")
    assert "const nouveau = b.nouveau" in re_
    assert "b.statut === 'en_vente_longue'" in re_
    assert "j < 2" not in re_ and "j > 90" not in re_, "seuil de badge recalculé au front (F14)"


def test_f31_blocb_zan_horizon_sans_defaut_fabrique():
    """F31 — la ligne ZAN ne fabrique plus un horizon d'épuisement de 99 ans quand il est absent
    (`?? 99`) : un horizon ABSENT est neutre (ton mint), jamais faussement « > 5 ans » via un 99
    inventé. Le palier de COULEUR (< 5 ans) reste de la présentation d'une valeur servie."""
    bb = (SRC / "components/outils/blocB.tsx").read_text(encoding="utf-8")
    assert "?? 99" not in bb, "défaut 99 fabriqué revenu (F31)"
    assert "horizon != null && horizon < 5" in bb


def test_f25_radar_corpus_jeune_servi():
    """F25 — le bandeau « corpus jeune » n'est plus décidé au front (`corpus_total < 40`) : le back
    sert le flag `corpus_jeune` (seuil SEUIL_CORPUS_JEUNE), le front le lit."""
    from labuse.pige.marche import SEUIL_CORPUS_JEUNE
    assert SEUIL_CORPUS_JEUNE == 40
    src = (ROOT / "src/labuse/pige/marche.py").read_text(encoding="utf-8")
    assert '"corpus_jeune": corpus_total < SEUIL_CORPUS_JEUNE' in src
    rm = (SRC / "components/outils/RadarMarche.tsx").read_text(encoding="utf-8")
    assert "const jeune = data.corpus_jeune" in rm
    assert "corpus_total < 40" not in rm, "seuil corpus recalculé au front (F25)"


def test_f01a_constructibilite_zone_servie_par_la_cascade():
    """F01a (réglementaire) — le verdict de constructibilité NEUVE n'est plus dérivé par regex front
    sur le libellé de zone : il vient de la CASCADE (moteur zone_servie, famille via
    labuse_zone_famille sur le subtype GPU), servi dans reglement_plu (zone_famille + constructible_neuf).
    Même valeur que le Pré-dossier et la garde SDP résiduelle — une seule vérité."""
    app = (ROOT / "src/labuse/api/app.py").read_text(encoding="utf-8")
    assert "from ..faisabilite.zone_servie import zone_dominante" in app
    assert '"constructible_neuf"' in app and '"zone_famille"' in app

    # front : lit constructible_neuf, plus de regex de zone pour le verdict
    fiche = (SRC / "components/fiche/Fiche.tsx").read_text(encoding="utf-8")
    constr = (SRC / "components/fiche/constructibilite.tsx").read_text(encoding="utf-8")
    for f in (fiche, constr):
        assert "constructible_neuf === false" in f
        assert "/^(A(?!U)|N)/i.test(reglesZone)" not in f, "regex de zone (verdict) revenue au front"
    assert "/^(A|N)/i.test(reglesZone)" not in fiche, "regex bugguée /^(A|N)/ (AU flaggé) revenue"
    assert "zoneFamille === 'A'" in fiche and "zoneFamille === 'N'" in fiche  # libellés agricole/naturelle servis


def test_f13_f29_paliers_da_servis():
    """F13/F29 — la pastille (Projets) et le badge (Outils) ne codent plus la correspondance
    palier→couleur : le back sert, par palier, le jeton DA + le ton + le libellé (source unique
    scoring/tiers_client, endpoint /vocabulaire/paliers). À la bascule q_v15 (bandes A/B/C/D), seul
    le back change ; pastille et badge suivent, une seule source."""
    from labuse.scoring.tiers_client import DOMAINE_PALIERS, PALIER_DA, paliers_da
    # chaque palier du domaine porte un jeton + un ton
    for code in DOMAINE_PALIERS:
        assert code in PALIER_DA and PALIER_DA[code]["jeton"] and PALIER_DA[code]["ton"]
    m = paliers_da()
    assert m["a_suivre"]["ton"] == "ambre" and m["sans_signal"]["ton"] == "neutre"
    assert m["a_suivre"]["chip"] == "À suivre"
    # l'endpoint existe
    app = (ROOT / "src/labuse/api/app.py").read_text(encoding="utf-8")
    assert '@app.get("/vocabulaire/paliers")' in app

    # F29 : le badge lit le ton servi, plus de correspondance hex→ton (tonDeCouleur supprimée)
    tb = (SRC / "components/outils/TierBadge.tsx").read_text(encoding="utf-8")
    assert "usePaliersDA" in tb and "servi?.ton" in tb
    assert "tonDeCouleur" not in tb, "correspondance hex→ton codée revenue au front (F29)"
    # F13 : la pastille lit le jeton servi, plus de TIER_DOT en dur
    pk = (SRC / "components/projets/ProjetKanban.tsx").read_text(encoding="utf-8")
    assert "palierDe(tier, paliers)" in pk
    assert "TIER_DOT" not in pk, "correspondance tier→couleur codée revenue au front (F13)"
