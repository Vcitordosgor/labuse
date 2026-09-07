"""SOURCES-1 lot 5 — gardes : la valeur (Arcep, REI, ORT, loyers OLL/DHUP, coût construction).

Tests purs (parsing, bascules, invariants du circuit) — les mesures sur base réelle vivent
au compte-rendu. Épinglages des fiches de règle (exemple_temoin)."""
from __future__ import annotations


# ───────────────────────── loyers : bascule OLL/DHUP ─────────────────────────

def test_loyer_bascule_oll_dhup():
    """Le choix de la bascule est structurel : oll_commune rend None pour une commune
    multi-zones (repli DHUP) et une valeur pour une mono-zone — calcul refait à la main sur
    le zonage réel lu le 07/09/2026 : Bras-Panon (97402) = zone 5 seule → OLL ; Saint-Denis
    (97411) = 6 zones → None → DHUP."""
    from labuse.ingestion.oll_loyers import _zone_of
    assert _zone_of("") == 0                      # agglomération
    assert _zone_of("L9740.1.05") == 5
    assert _zone_of("L9740.1.01") == 1
    assert _zone_of("n'importe quoi") is None      # jamais deviné


def test_oll_decodage_mixte():
    """Base_OP en latin-1, zonage en UTF-8 BOM (mesuré) — le lecteur replie sans rien perdre."""
    import io
    import zipfile
    from labuse.ingestion.oll_loyers import _texte
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("latin.csv", "Réunion".encode("latin-1"))
        zf.writestr("utf8.csv", "﻿Réunion".encode("utf8"))
    zf = zipfile.ZipFile(buf)
    assert _texte(zf, "latin.csv").read() == "Réunion"
    assert _texte(zf, "utf8.csv").read() == "Réunion"


# ───────────────────────── coût de construction ─────────────────────────

def test_cout_construction_reference():
    """La ligne SERVIE = les anciennes constantes (2 300-2 800) → aucun bilan ne bouge ;
    l'EPTB 2024 est une ligne de CONTEXTE jamais servie."""
    from labuse.ingestion.cout_construction import LIGNES
    servies = [l for l in LIGNES if l["servi"]]
    assert len(servies) == 1 and servies[0]["id"] == "labuse_promotion"
    assert (servies[0]["bas"], servies[0]["haut"]) == (2300, 2800)
    ctx = next(l for l in LIGNES if l["id"] == "eptb_2024_maison")
    assert not ctx["servi"] and "145 500" in ctx["source"]


def test_hypotheses_repli_sans_table():
    """Sans base (cache vidé, session_scope indisponible ou table absente), charger() sert
    les défauts du dataclass — jamais un bilan cassé."""
    from labuse.faisabilite import engine as eng
    old = eng._COUTS_REF_CACHE
    try:
        eng._COUTS_REF_CACHE = ()      # simule « lu, table absente »
        h = eng.Hypotheses.charger(None)
        assert (h.cout_construction_m2_bas, h.cout_construction_m2_haut) == (2300.0, 2800.0)
    finally:
        eng._COUTS_REF_CACHE = old


# ───────────────────────── REI ─────────────────────────

def test_rei_taux_passe_plat():
    """Calcul refait à la main sur la ligne 974 lue le 07/09/2026 : Les Avirons E12=29.55."""
    from labuse.ingestion.rei import _num
    assert _num("29.55000") == 29.55
    assert _num("") is None and _num(None) is None


# ───────────────────────── ORT / Denormandie ─────────────────────────

def test_ort_statut_et_denormandie():
    """L'attendu fiche 10 est un CONTRÔLE (jamais imposé) : la constante liste les 5 ACV
    attendues dont Saint-Louis — l'écart mesuré (absent de la table DGALN) vit au filtre."""
    from labuse.ingestion.ort import ACV_ATTENDUES
    assert ACV_ATTENDUES["97414"] == "Saint-Louis"
    assert len(ACV_ATTENDUES) == 5


# ───────────────────────── fibre Arcep ─────────────────────────

def test_fibre_block_absent_sans_table():
    """_fibre_block rend None si la table n'existe pas (source non ingérée) — le front omet."""
    from labuse.api.app import _fibre_block

    class _S:
        def execute(self, *a, **k):
            raise RuntimeError("no table")

        def rollback(self):
            pass
    assert _fibre_block(_S(), "97411000XX0001") is None


# ───────────────────────── circuit : catalogue, filtres, registre ─────────────────────────

def test_catalogue_lot5():
    from labuse.ingestion.seed_sources import SOURCES, verifier_catalogue
    noms = {r["name"] for r in SOURCES}
    for n in ("Fibre Arcep — Ma connexion internet (immeuble)",
              "Taux de taxe foncière — fichier REI (DGFiP)",
              "ACV / PVD / ORT (DGALN — liste des communes)",
              "Loyers OLL — ADIL Réunion / AGORAH (réseau des observatoires)",
              "Loyers DHUP — carte des loyers (annonces)",
              "Coût de construction (EPTB SDES + choix LABUSE)"):
        assert n in noms, n
    assert verifier_catalogue() == []


def test_filtres_lot5_enregistres():
    from labuse.filtres.sources import FILTRES_RICHES
    for cle in ("arcep_fibre", "dgfip_rei", "anct_ort", "loyers_oll",
                "cout_construction", "loyers_dhup"):
        assert cle in FILTRES_RICHES, cle
    assert FILTRES_RICHES["loyers_dhup"].a_job is False


def test_registre_lot5():
    from labuse.registre.couverture import FICHE_PARCELLE_CLES
    from labuse.registre.donnees import DONNEES
    for cid in ("fibre_parcelle", "tfpb_taux_pct", "ort_statut",
                "cout_construction_ref_eur_m2"):
        assert cid in DONNEES, cid
    d = DONNEES["loyer_median_eur_m2"]
    assert "loyers_oll" in d.reservoirs and "loyers_dhup" in d.reservoirs
    assert "fibre" in FICHE_PARCELLE_CLES


def test_vanne_lot5():
    from labuse import filtres
    labels = {e.get("label") for e in filtres.sources_a_job()}
    assert {"arcep_fibre", "dgfip_rei", "anct_ort", "loyers_oll", "cout_construction"} <= labels


def test_fiches_de_regle_lot5():
    import labuse.regles as regles
    fiches = regles.charger()
    for d in ("loyer_median_eur_m2", "tfpb_taux_pct", "ort_statut",
              "cout_construction_ref_eur_m2"):
        assert d in fiches, d
    assert fiches["tfpb_taux_pct"].reference is not None
    assert "E12" in fiches["tfpb_taux_pct"].reference.extrait
