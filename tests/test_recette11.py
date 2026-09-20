"""RECETTE-11 — verrous sans base : le §3 potentiel n'imprime aucun verdict de surélévation (A6),
la date de survol accompagne la mesure LiDAR (A3), et un permis postérieur au survol est signalé (A4).

Le rendu du bloc lit un `potentiel_verdict` (le dict servi par l'API). On le fabrique de toutes pièces
et on vérifie le HTML produit — mécanique, aucune base."""
from __future__ import annotations

from labuse.exports.blocs import potentiel
from labuse.faisabilite.hauteur_lidar import survol_libelle
from labuse.registre.valeur import Valeur


def _V(cid, valeur, **kw):
    return Valeur(valeur=valeur, chiffre_id=cid, version_def="x", run=kw.pop("run", None), **kw)


def _valeurs(**pv):
    base = {"niveau": "faible", "libelle": "Potentiel faible", "hauteur_nature": "sourcé",
            "hauteur_base": "faîtage mesuré (LiDAR HD)", "hauteur_faitage_lidar_m": 6.9,
            "hauteur_egout_lidar_m": 3.0, "hauteur_marge_m": 3.1, "hauteur_contrainte": "faîtage",
            "hauteur_contraintes": [
                {"base": "égout", "mesure_m": 3.0, "regle_m": 7.0, "marge_m": 4.0},
                {"base": "faîtage", "mesure_m": 6.9, "regle_m": 10.0, "marge_m": 3.1}],
            "hauteur_survol": "septembre 2023", "sdp_residuelle_m2": 97, "pct_consomme": 79}
    base.update(pv)
    return {"potentiel_verdict": _V("potentiel_verdict", base)}


def test_a6_aucun_verdict_de_surelevation():
    """A6 — plus de « surélévation possible »/« pas de marge »/« non identifiée » : que la marge,
    la règle, la contrainte qui mord."""
    html = potentiel.rendu(_valeurs())
    bas = html.lower()
    for interdit in ("surélévation possible", "non identifiée", "pas de marge de surélévation",
                     "surélévation à confirmer"):
        assert interdit not in bas, interdit
    # ce qui DOIT rester : marge + contrainte + les deux calculs mesurés (égout ET faîtage).
    # TESTS-1 lot 2 (B) — RECETTE-12 D3 (c5dc44e1, 13/09/2026, arbitrage Q7) : la phrase tient sur
    # UNE ligne « Égout X mesuré (règle Y, marge Z) · Faîtage … — contrainte qui mord : … » ; le
    # « X sous la hauteur réglementaire » du LiDAR a été RETIRÉ exprès (il ne doit pas revenir).
    assert "sous la hauteur réglementaire" not in bas
    assert "contrainte qui mord : le faîtage" in bas
    assert bas.count("mesuré (règle") == 2 and bas.count("marge") >= 2


def test_a3_date_de_survol_avec_la_mesure():
    """A3 — la mesure LiDAR HD ne s'affiche jamais sans sa date de survol."""
    html = potentiel.rendu(_valeurs())
    assert "mesuré au LiDAR HD, survol de septembre 2023" in html
    # TESTS-1 lot 2 (B) — RECETTE-12 D3 (c5dc44e1, 13/09/2026) : la date de survol UNE SEULE fois
    # (sur la ligne de mesure), et la source LiDAR HD est citée dans les SOURCES (§10, sources.py),
    # plus dans le §3 (elle y apparaissait 4 fois).
    assert html.count("septembre 2023") == 1
    assert "IGN / Géoplateforme" not in html   # le §3 ne re-cite plus la source (§10 le fait)


def test_a4_permis_posterieur_signale():
    """A4 — un permis autorisé APRÈS le survol : la mesure le dit ; comparé à la date de survol."""
    sans = potentiel.rendu(_valeurs())
    assert "possiblement dépassée" not in sans
    avec = potentiel.rendu(_valeurs(hauteur_permis_posterieur="15/03/2024"))
    assert "mesure antérieure au permis du 15/03/2024, possiblement dépassée" in avec


def test_a2_survol_libelle_mois_annee():
    """A2 — la date de survol est formatée « mois année » depuis la métadonnée, None si absente."""
    from datetime import date
    assert survol_libelle(date(2023, 9, 3)) == "septembre 2023"
    assert survol_libelle(date(2023, 8, 14)) == "août 2023"
    assert survol_libelle(None) is None


def test_a5_sentinelle_lidar_974():
    """A5 — la veille LiDAR HD surveille le CANAL RÉELLEMENT INGÉRÉ (grille de dalles WFS IGN) borné à
    la Réunion, par témoin sur la dernière édition ; une nouvelle diffusion 974 est détectée."""
    import json as _json
    from labuse import sentinelle
    entree = next(e for e in sentinelle.SEED if e["name"] == "LiDAR HD — MNH 50 cm (IGN)")
    assert entree["methode"] == "temoin"
    assert "data.geopf.fr/wfs" in entree["url"] and "IGNF_LIDAR-HD_METADONNEE" in entree["url"]
    # borné à l'emprise Réunion (pas national) + lit la dernière édition
    assert "BBOX=-21.40,55.20,-20.80,55.85" in entree["url"]
    assert entree["selecteur"] == "features.0.properties.date_edition"

    # sonde mécanique, sans réseau : baseline puis changement d'édition → « la donnée amont a changé »
    def http_faux(url, *, methode_http="GET"):
        corps = _json.dumps({"numberMatched": 2665,
                             "features": [{"properties": {"date_edition": "2025-03-13Z"}}]})
        return 200, {}, corps
    row = {"methode": "temoin", "url_version": entree["url"], "selecteur": entree["selecteur"],
           "dernier_entete": None}
    base = sentinelle.sonder_ligne(row, None, http=http_faux)
    assert base.statut == "ok" and base.vu == "2025-03-13Z"
    change = sentinelle.sonder_ligne({**row, "dernier_entete": "2024-01-01"}, None, http=http_faux)
    assert change.statut == "nouvelle_version"


# ── Lot B — le Financier : la garde vit dans le questionnaire ──────────────────────────────────

def test_b2_garde_bailleur_dans_le_questionnaire():
    """B2 — bailleur social > prix libre : le garde du questionnaire mord, nomme l'écran (Vos
    conditions) et le champ replié sous « Affiner » ; coherent → rien."""
    from labuse import financier_questionnaire as qf
    hm = qf.valider_hors_marche(
        {"_usage": "construction", "prix_sortie_saisi_eur_m2": 4500,
         "prix_vente_bailleur_saisi_eur_m2": 5500}, {})
    assert hm and hm["champ_id"] == "prix_vente_bailleur_saisi_eur_m2"
    assert hm["ecran"] == 0 and hm["affiner"] is True
    assert "prix de vente libre" in hm["message"]
    # coherent : bailleur sous le libre → le bilan peut s'établir
    assert qf.valider_hors_marche(
        {"prix_sortie_saisi_eur_m2": 4500, "prix_vente_bailleur_saisi_eur_m2": 3800}, {}) is None


def test_b2_prix_total_saisi():
    """B2 — un prix TOTAL saisi à la place d'un €/m² (borne absolue) est refusé, écran nommé."""
    from labuse import financier_questionnaire as qf
    hm = qf.valider_hors_marche({"prix_sortie_saisi_eur_m2": 250000}, {})
    assert hm and hm["champ_id"] == "prix_sortie_saisi_eur_m2" and hm["ecran"] == 0


def test_b3_hypotheses_listent_tous_les_champs():
    """B3 — l'encart « Hypothèses du porteur » liste TOUS les champs du bilan, y compris ceux
    d'« Affiner » (bailleur, aléas, VRD, honoraires, frais, dépollution, portage…)."""
    from labuse.exports.blocs.financier import _HYP_CLES
    ids = {fid for fid, _ in _HYP_CLES}
    for attendu in ("prix_vente_bailleur_saisi_eur_m2", "aleas_saisi_pct", "vrd_saisi_eur_m2",
                    "honoraires_techniques_saisi_pct", "frais_acquisition_saisi_pct",
                    "bilan_depollution_eur", "duree_portage_saisi_mois", "taxe_amenagement_saisi_eur"):
        assert attendu in ids, attendu


def test_b4_prefill_toujours_source():
    """B4 — pré-remplissage honnête : toute valeur pré-remplie porte une source ; aucune valeur sans
    source n'est pré-remplie (le garde B2 assure la cohérence bailleur<libre, pas un défaut fixe)."""
    from labuse import financier_questionnaire as qf
    pf = qf.prefill({})
    assert pf and all(v.get("source") for v in pf.values())
    # ni le prix libre ni le prix bailleur ne sont pré-remplis (un défaut bailleur ne peut être
    # cohérent avec un prix libre inconnu → laissé au porteur, borné par le garde).
    assert "prix_sortie_saisi_eur_m2" not in pf and "prix_vente_bailleur_saisi_eur_m2" not in pf


# ── Lot D — Dossier & Apporteur ────────────────────────────────────────────────────────────────

def test_d3_frr_libelle_tranche_a_la_parcelle():
    """D3 — commune FRR « en partie » : on tranche dedans/hors à la parcelle, « non déterminé » si
    le périmètre manque — jamais « dépend de la localisation exacte »."""
    from labuse.territoire_fiscal import frr_libelle_partie
    assert "DANS la zone" in frr_libelle_partie("dans")
    assert "HORS de la zone" in frr_libelle_partie("hors")
    assert "non déterminée" in frr_libelle_partie(None)
    for lib in (frr_libelle_partie("dans"), frr_libelle_partie("hors"), frr_libelle_partie(None)):
        assert "dépend de la localisation exacte" not in lib


def test_d4_non_reglemente_avec_article_est_source():
    """D4 — « non réglementé » AVEC un article cité (etat 'absent' + référence) est SOURCÉ, pas estimé."""
    from labuse.exports.blocs.zonage import _chip_regle
    assert "sourcé" in _chip_regle("absent", has_ref=True)
    assert "estimé" in _chip_regle("absent", has_ref=False)
    assert "sourcé" in _chip_regle("chiffre")


def test_d7_ce_qui_gene_reprend_mouvement_de_terrain():
    """D7 — « Ce qui gêne » reprend la description du Dossier §4 : un PPR « inondation ET mouvement de
    terrain » n'est plus réduit à « Inondation »."""
    from labuse.exports.blocs.apporteur import _contraintes
    valeurs = {"aleas_parcelle_liste": _V("aleas_parcelle_liste", [
        {"nature": "Inondation", "libelle": "Zone bleue PPR inondation et mouvement de terrain — "
         "constructible SOUS PRESCRIPTIONS (règlement DEAL)."}])}
    out = _contraintes(valeurs)
    assert "mouvement de terrain" in out.lower() and "inondation" in out.lower()
