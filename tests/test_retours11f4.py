"""RETOURS-11F4 — gardes de la session F4 : découpe de Fiche.tsx en modules par section,
doublons F0 soldés (accès/école/permis/prix de sortie), fonds ortho « Actuelle » = Ortho Express 2025.

Gardes « marqueur dans le source » (pattern test_front_reliquats) + garde backend sur le routage
d'onglet (served_cascade._ONGLET), source unique écran + PDF.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FICHE_DIR = ROOT / "frontend/src/components/fiche"


def _read(name: str) -> str:
    return (FICHE_DIR / name).read_text(encoding="utf-8")


# ── Backend : routage d'onglet (doctrine F0 « un fait, une section ») ───────────────────────────
def test_onglet_acces_quitte_marche_pour_reseaux():
    from labuse.api.served_cascade import _ONGLET, _LAYER_ONGLET
    # accès : UN verdict, dans Réseaux — plus jamais dans Marché (doublon F0).
    assert "acces" not in _ONGLET["marche"]
    assert _LAYER_ONGLET["acces"] == "reseaux"


def test_onglet_sup_rejoint_risques():
    from labuse.api.served_cascade import _LAYER_ONGLET
    # SUP (PM1/AC1/I4/EL7…) rapatriées d'Urbanisme (défaut « regles ») vers Risques (F6).
    assert _LAYER_ONGLET["sup"] == "risques"


def test_onglet_friche_et_occupation_rapatriees_urbanisme():
    from labuse.api.served_cascade import _LAYER_ONGLET
    # occupation du sol / ZAN / friche quittent Marché → Urbanisme (F4/F7).
    assert _LAYER_ONGLET["friche"] == "regles"
    assert _LAYER_ONGLET["ocs_ge"] == "regles"
    # Marché ne porte plus que du prix (dvf/sitadel/amenites/potentiel_foncier_region).
    from labuse.api.served_cascade import _ONGLET
    assert "friche" not in _ONGLET["marche"] and "ocs_ge" not in _ONGLET["marche"]


# ── Fonds : « Actuelle » = Ortho Express RVB 2025 (millésime réel le plus récent au 974) ──────────
def test_fond_actuelle_est_ortho_express_2025():
    bm = (ROOT / "frontend/src/components/map/basemaps.ts").read_text(encoding="utf-8")
    # RETOURS-15 U1 — la couche Express est désormais servie par le PROXY backend (les tuiles
    # blanc-mer sont retirées côté serveur) : l'ID de couche IGN vit dans app.py, basemaps.ts
    # pointe le proxy. L'intention (Actuelle = Express 2025, pas BD ORTHO 2022) est INCHANGÉE.
    app = (ROOT / "src/labuse/api/app.py").read_text(encoding="utf-8")
    assert "ORTHOIMAGERY.ORTHOPHOTOS.ORTHO-EXPRESS.2025" in app
    assert "/map/tiles/ortho-express/" in bm
    assert "Actuelle · Ortho Express 2025" in bm
    # le libellé « BD ORTHO 2022 » nu ne subsiste plus comme « Actuelle ».
    assert "Actuelle · BD ORTHO 2022" not in bm


def test_solaire_libelle_ortho_2025_corrige():
    sol = (ROOT / "frontend/src/components/outils/ProspectionSolaire.tsx").read_text(encoding="utf-8")
    assert "Ortho Express RVB 20 cm 2025" in sol


# ── Découpe : un module par section + le shell les rend ──────────────────────────────────────────
def test_decoupe_un_module_par_section():
    for f in ("primitives.tsx", "constructibilite.tsx", "risques.tsx", "marche.tsx", "reseaux.tsx", "autour.tsx"):
        assert (FICHE_DIR / f).exists(), f
    fiche = _read("Fiche.tsx")
    for comp in ("ConstructibiliteSection", "RisquesSection", "MarcheSection", "ReseauxSection", "AutourSection"):
        assert f"<{comp} " in fiche, comp
    # Fiche ré-exporte les 2 symboles publics (EtudierBien / M22Programme / test les importent).
    assert "export { Calculette, FaisabiliteTab } from './constructibilite'" in fiche


# ── F5 Constructibilité : prix de sortie → Marché (renvoi) ────────────────────────────────────────
def test_f5_prix_de_sortie_renvoie_vers_marche():
    c = _read("constructibilite.tsx")
    assert "Prix de sortie retenu (bilan)" in c
    assert "« Marché et secteur »" in c
    # le fait vit dans Marché.
    assert "Prix de sortie — bâti secteur" in _read("marche.tsx")


# ── F6 Risques : vigilances d'abord + « sans objet » repliés ─────────────────────────────────────
def test_f6_vigilances_dabord_sans_objet_replies():
    r = _read("risques.tsx")
    assert "sans objet — déplier" in r
    assert "Vigilances" in r
    assert "l.onglet === 'risques'" in r


# ── F7 Marché : socio-éco parti (plus de MarcheSecteurBlock ici) ─────────────────────────────────
def test_f7_marche_ne_porte_plus_le_socio_eco():
    m = _read("marche.tsx")
    assert "MarcheSecteurBlock" not in m          # déménagé vers Autour
    assert "PermitsProximityBlock" not in m       # permis → Autour


# ── F8 Réseaux : 4 blocs, permis partis, un verdict d'accès ───────────────────────────────────────
def test_f8_reseaux_quatre_blocs_sans_permis():
    r = _read("reseaux.tsx")
    assert "PermitsProximityBlock" not in r        # permis → Autour
    assert "data-bloc-acces" in r                  # bloc Accès
    assert "Axes et nuisances" in r


# ── F9 Autour : permis + socio-éco réunis ici (un moteur, un tableau) ─────────────────────────────
def test_f9_autour_reunit_equipements_permis_socioeco():
    a = _read("autour.tsx")
    assert "PermitsProximityBlock" in a
    assert "MarcheSecteurBlock" in a
    # Filosofi = Sourcé (carreau INSEE), pas « estimé ».
    assert "sourcé" in _read("MarcheSecteurBlock.tsx").lower()
